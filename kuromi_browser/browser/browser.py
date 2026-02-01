"""
Browser class for kuromi-browser.

Main browser management class that orchestrates tabs, contexts,
profiles, and multi-instance support.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional
from weakref import WeakSet

from kuromi_browser.interfaces import BaseBrowser
from kuromi_browser.cdp.launcher import BrowserLaunchOptions, BrowserProcess
from kuromi_browser.cdp.connection import CDPConnection
from kuromi_browser.browser.tabs import TabManager
from kuromi_browser.browser.context import BrowserContext, ContextOptions, DefaultContext
from kuromi_browser.browser.profiles import BrowserProfile, ProfileManager

if TYPE_CHECKING:
    from kuromi_browser.interfaces import BaseBrowserContext, BasePage
    from kuromi_browser.models import BrowserConfig, Fingerprint, PageConfig

logger = logging.getLogger(__name__)


class BrowserState(str, Enum):
    """Browser lifecycle states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSING = "closing"


@dataclass
class BrowserEvents:
    """Event callbacks for browser lifecycle."""

    on_connected: list[Callable[[], Any]] = field(default_factory=list)
    on_disconnected: list[Callable[[], Any]] = field(default_factory=list)
    on_context_created: list[Callable[[BrowserContext], Any]] = field(default_factory=list)
    on_context_closed: list[Callable[[BrowserContext], Any]] = field(default_factory=list)
    on_page_created: list[Callable[["BasePage"], Any]] = field(default_factory=list)
    on_page_closed: list[Callable[["BasePage"], Any]] = field(default_factory=list)


# Global registry of browser instances
_browser_instances: WeakSet["Browser"] = WeakSet()


class Browser(BaseBrowser):
    """Main browser controller for kuromi-browser.

    Manages browser process, CDP connection, tabs, contexts, and profiles.
    Supports both launching new browser instances and connecting to existing ones.

    Example:
        # Launch new browser
        async with Browser() as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")

        # With profile
        profile = await ProfileManager().create(ProfileConfig(name="Work"))
        async with Browser(profile=profile) as browser:
            # Data persists across sessions
            pass

        # Connect to existing browser
        browser = await Browser.connect("ws://localhost:9222/...")
        page = await browser.new_page()

        # Multiple contexts (like incognito)
        async with Browser() as browser:
            context1 = await browser.new_context()
            context2 = await browser.new_context()
            # Isolated storage
    """

    def __init__(
        self,
        config: Optional["BrowserConfig"] = None,
        profile: Optional[BrowserProfile] = None,
        launch_options: Optional[BrowserLaunchOptions] = None,
    ) -> None:
        """Initialize browser.

        Args:
            config: Browser configuration.
            profile: Browser profile to use.
            launch_options: Custom launch options.
        """
        self._config = config
        self._profile = profile
        self._launch_options = launch_options or BrowserLaunchOptions()

        self._process: Optional[BrowserProcess] = None
        self._connection: Optional[CDPConnection] = None
        self._state = BrowserState.DISCONNECTED

        self._default_context: Optional[DefaultContext] = None
        self._contexts: list[BrowserContext] = []
        self._tabs: Optional[TabManager] = None

        self._events = BrowserEvents()
        self._version_info: dict[str, Any] = {}
        self._ws_endpoint: Optional[str] = None

        # Register instance
        _browser_instances.add(self)

    @property
    def is_connected(self) -> bool:
        """Whether browser is connected."""
        return (
            self._state == BrowserState.CONNECTED
            and self._connection is not None
            and self._connection.is_connected
        )

    @property
    def contexts(self) -> list["BaseBrowserContext"]:
        """All browser contexts."""
        contexts: list["BaseBrowserContext"] = []
        if self._default_context:
            contexts.append(self._default_context)
        contexts.extend(self._contexts)
        return contexts

    @property
    def tabs(self) -> Optional[TabManager]:
        """Tab manager for default context."""
        return self._tabs

    @property
    def state(self) -> BrowserState:
        """Current browser state."""
        return self._state

    @property
    def profile(self) -> Optional[BrowserProfile]:
        """Active browser profile."""
        return self._profile

    @property
    def ws_endpoint(self) -> Optional[str]:
        """WebSocket debugger URL."""
        return self._ws_endpoint

    @property
    def connection(self) -> Optional[CDPConnection]:
        """CDP connection."""
        return self._connection

    async def launch(self) -> None:
        """Launch browser process and connect.

        Raises:
            RuntimeError: If already connected or launch fails.
        """
        if self.is_connected:
            raise RuntimeError("Browser is already connected")

        self._state = BrowserState.CONNECTING

        # Apply profile settings to launch options
        if self._profile:
            await self._profile.acquire_lock()
            self._launch_options.user_data_dir = self._profile.user_data_dir
            self._launch_options.args.extend(self._profile.get_launch_args())

        # Apply config to launch options
        if self._config:
            if self._config.headless:
                self._launch_options.headless = True
            if self._config.proxy:
                from kuromi_browser.models import ProxyConfig

                proxy = self._config.proxy
                if isinstance(proxy, ProxyConfig):
                    self._launch_options.proxy = proxy.server
                else:
                    self._launch_options.proxy = proxy
            if self._config.executable_path:
                self._launch_options.executable_path = self._config.executable_path
            if self._config.user_data_dir and not self._profile:
                self._launch_options.user_data_dir = self._config.user_data_dir
            if self._config.args:
                self._launch_options.args.extend(self._config.args)
            if self._config.ignore_default_args:
                self._launch_options.ignore_default_args.extend(
                    self._config.ignore_default_args
                )
            if self._config.devtools:
                self._launch_options.devtools = True

        # Launch browser process
        self._process = BrowserProcess(self._launch_options)
        ws_endpoint = await self._process.launch()
        self._ws_endpoint = ws_endpoint

        # Connect to browser
        await self._connect_to_endpoint(ws_endpoint)

    async def _connect_to_endpoint(self, ws_endpoint: str) -> None:
        """Connect to browser via WebSocket.

        Args:
            ws_endpoint: WebSocket debugger URL.
        """
        self._connection = CDPConnection(ws_endpoint)
        await self._connection.connect()

        # Get browser version
        try:
            self._version_info = await self._connection.send("Browser.getVersion")
        except Exception:
            pass

        # Create default context and tab manager
        self._default_context = DefaultContext(self, self._connection)
        self._tabs = TabManager(self._connection)

        # Enable target discovery
        await self._tabs.enable_auto_attach()

        # Refresh tabs list
        await self._tabs.refresh()

        self._state = BrowserState.CONNECTED

        # Fire connected event
        await self._emit_event("connected")

        logger.info(f"Browser connected: {ws_endpoint}")

    @classmethod
    async def connect(
        cls,
        ws_endpoint: str,
        config: Optional["BrowserConfig"] = None,
    ) -> "Browser":
        """Connect to an existing browser instance.

        Args:
            ws_endpoint: WebSocket debugger URL.
            config: Optional browser configuration.

        Returns:
            Connected browser instance.

        Example:
            browser = await Browser.connect("ws://localhost:9222/devtools/browser/...")
        """
        browser = cls(config=config)
        browser._ws_endpoint = ws_endpoint
        browser._state = BrowserState.CONNECTING

        await browser._connect_to_endpoint(ws_endpoint)
        return browser

    @classmethod
    async def connect_over_cdp(
        cls,
        endpoint_url: str,
        config: Optional["BrowserConfig"] = None,
    ) -> "Browser":
        """Connect to browser via CDP endpoint URL.

        Args:
            endpoint_url: HTTP endpoint (e.g., http://localhost:9222).
            config: Optional browser configuration.

        Returns:
            Connected browser instance.
        """
        import httpx

        # Get WebSocket URL from /json/version endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{endpoint_url}/json/version")
            data = response.json()
            ws_endpoint = data.get("webSocketDebuggerUrl")

        if not ws_endpoint:
            raise RuntimeError("Could not get WebSocket URL from CDP endpoint")

        return await cls.connect(ws_endpoint, config)

    async def new_context(
        self,
        *,
        config: Optional["PageConfig"] = None,
        fingerprint: Optional["Fingerprint"] = None,
        options: Optional[ContextOptions] = None,
    ) -> BrowserContext:
        """Create a new browser context (like incognito).

        Args:
            config: Optional page configuration.
            fingerprint: Optional fingerprint for context.
            options: Context options.

        Returns:
            New browser context.
        """
        if not self.is_connected or not self._connection:
            raise RuntimeError("Browser is not connected")

        # Create CDP browser context
        result = await self._connection.send("Target.createBrowserContext")
        context_id = result["browserContextId"]

        # Create context wrapper
        context = BrowserContext(
            self,
            self._connection,
            context_id,
            options,
        )

        await context.initialize()
        self._contexts.append(context)

        # Fire event
        await self._emit_event("context_created", context)

        logger.debug(f"Created browser context: {context_id}")
        return context

    async def new_page(
        self,
        *,
        config: Optional["PageConfig"] = None,
        fingerprint: Optional["Fingerprint"] = None,
    ) -> "BasePage":
        """Create a new page in the default context.

        Args:
            config: Optional page configuration.
            fingerprint: Optional fingerprint.

        Returns:
            New page instance.
        """
        if not self.is_connected or not self._default_context:
            raise RuntimeError("Browser is not connected")

        page = await self._default_context.new_page(config=config)

        # Apply fingerprint stealth if provided
        if fingerprint:
            from kuromi_browser.page import StealthPage, Page

            if isinstance(page, Page) and not isinstance(page, StealthPage):
                from kuromi_browser.stealth import apply_stealth

                await apply_stealth(page._cdp, fingerprint)

        # Fire event
        await self._emit_event("page_created", page)

        return page

    async def pages(self) -> list["BasePage"]:
        """Get all pages across all contexts.

        Returns:
            List of all pages.
        """
        all_pages: list["BasePage"] = []

        if self._default_context:
            all_pages.extend(self._default_context.pages)

        for context in self._contexts:
            all_pages.extend(context.pages)

        return all_pages

    async def close(self) -> None:
        """Close the browser."""
        if self._state == BrowserState.DISCONNECTED:
            return

        self._state = BrowserState.CLOSING

        # Close all contexts
        for context in self._contexts:
            try:
                await context.close()
            except Exception:
                pass
        self._contexts.clear()

        # Close default context pages
        if self._default_context:
            for page in self._default_context.pages:
                try:
                    await page.close()
                except Exception:
                    pass

        # Cleanup tabs
        if self._tabs:
            await self._tabs.cleanup()

        # Close connection
        if self._connection:
            await self._connection.close()
            self._connection = None

        # Close browser process
        if self._process:
            await self._process.close()
            self._process = None

        # Release profile lock
        if self._profile:
            await self._profile.release_lock()

        self._state = BrowserState.DISCONNECTED

        # Fire disconnected event
        await self._emit_event("disconnected")

        logger.info("Browser closed")

    async def version(self) -> str:
        """Get browser version string.

        Returns:
            Browser version.
        """
        if self._version_info:
            return self._version_info.get("product", "Unknown")

        if self.is_connected and self._connection:
            self._version_info = await self._connection.send("Browser.getVersion")
            return self._version_info.get("product", "Unknown")

        return "Unknown"

    async def user_agent(self) -> str:
        """Get browser user agent.

        Returns:
            User agent string.
        """
        if self._version_info:
            return self._version_info.get("userAgent", "")

        if self.is_connected and self._connection:
            self._version_info = await self._connection.send("Browser.getVersion")
            return self._version_info.get("userAgent", "")

        return ""

    async def new_cdp_session(self, target_id: str) -> Any:
        """Create a CDP session for a target.

        Args:
            target_id: Target ID.

        Returns:
            CDP session.
        """
        from kuromi_browser.cdp import CDPSession

        if not self.is_connected or not self._connection:
            raise RuntimeError("Browser is not connected")

        return await CDPSession.create(self._connection, target_id)

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Register event handler.

        Events:
            - connected: Browser connected
            - disconnected: Browser disconnected
            - context_created: New context created
            - context_closed: Context closed
            - page_created: New page created
            - page_closed: Page closed

        Args:
            event: Event name.
            handler: Handler function.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers is not None:
            handlers.append(handler)

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers and handler in handlers:
            handlers.remove(handler)

    async def _emit_event(self, event: str, *args: Any) -> None:
        """Emit an event to handlers."""
        handlers = getattr(self._events, f"on_{event}", [])
        for handler in handlers:
            try:
                result = handler(*args)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    async def __aenter__(self) -> "Browser":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        return f"Browser(state={self._state.value}, contexts={len(self._contexts)})"


class BrowserPool:
    """Pool of browser instances for concurrent automation.

    Manages multiple browser instances with automatic scaling
    and resource management.

    Example:
        async with BrowserPool(max_browsers=5) as pool:
            # Acquire browser from pool
            async with pool.acquire() as browser:
                page = await browser.new_page()
                await page.goto("https://example.com")
            # Browser returned to pool
    """

    def __init__(
        self,
        max_browsers: int = 5,
        config: Optional["BrowserConfig"] = None,
        launch_options: Optional[BrowserLaunchOptions] = None,
    ) -> None:
        """Initialize browser pool.

        Args:
            max_browsers: Maximum number of browsers.
            config: Default browser configuration.
            launch_options: Default launch options.
        """
        self._max_browsers = max_browsers
        self._config = config
        self._launch_options = launch_options

        self._available: asyncio.Queue[Browser] = asyncio.Queue()
        self._in_use: set[Browser] = set()
        self._all_browsers: list[Browser] = []
        self._lock = asyncio.Lock()
        self._closed = False

    @property
    def size(self) -> int:
        """Total number of browsers in pool."""
        return len(self._all_browsers)

    @property
    def available_count(self) -> int:
        """Number of available browsers."""
        return self._available.qsize()

    @property
    def in_use_count(self) -> int:
        """Number of browsers in use."""
        return len(self._in_use)

    async def _create_browser(self) -> Browser:
        """Create a new browser instance."""
        browser = Browser(
            config=self._config,
            launch_options=self._launch_options,
        )
        await browser.launch()
        self._all_browsers.append(browser)
        return browser

    async def acquire(self, timeout: Optional[float] = None) -> Browser:
        """Acquire a browser from the pool.

        Args:
            timeout: Maximum time to wait for a browser.

        Returns:
            Browser instance.

        Raises:
            asyncio.TimeoutError: If timeout waiting for browser.
        """
        if self._closed:
            raise RuntimeError("Pool is closed")

        async with self._lock:
            # Try to get existing browser
            try:
                browser = self._available.get_nowait()
                self._in_use.add(browser)
                return browser
            except asyncio.QueueEmpty:
                pass

            # Create new browser if under limit
            if len(self._all_browsers) < self._max_browsers:
                browser = await self._create_browser()
                self._in_use.add(browser)
                return browser

        # Wait for available browser
        if timeout:
            browser = await asyncio.wait_for(
                self._available.get(), timeout=timeout
            )
        else:
            browser = await self._available.get()

        self._in_use.add(browser)
        return browser

    async def release(self, browser: Browser) -> None:
        """Return a browser to the pool.

        Args:
            browser: Browser to return.
        """
        if browser in self._in_use:
            self._in_use.remove(browser)

            # Reset browser state
            if browser.is_connected:
                try:
                    # Close all pages
                    pages = await browser.pages()
                    for page in pages:
                        await page.close()

                    # Close extra contexts
                    for context in browser._contexts:
                        await context.close()
                    browser._contexts.clear()

                    await self._available.put(browser)
                except Exception:
                    # Browser unusable, close it
                    await browser.close()
                    self._all_browsers.remove(browser)

    async def close(self) -> None:
        """Close all browsers in the pool."""
        self._closed = True

        for browser in self._all_browsers:
            try:
                await browser.close()
            except Exception:
                pass

        self._all_browsers.clear()
        self._in_use.clear()

        # Clear queue
        while not self._available.empty():
            try:
                self._available.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def __aenter__(self) -> "BrowserPool":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


class BrowserAcquisition:
    """Context manager for acquiring browser from pool."""

    def __init__(self, pool: BrowserPool, timeout: Optional[float] = None) -> None:
        self._pool = pool
        self._timeout = timeout
        self._browser: Optional[Browser] = None

    async def __aenter__(self) -> Browser:
        self._browser = await self._pool.acquire(self._timeout)
        return self._browser

    async def __aexit__(self, *args: Any) -> None:
        if self._browser:
            await self._pool.release(self._browser)


# Add acquire context manager to pool
BrowserPool.acquire_context = lambda self, timeout=None: BrowserAcquisition(self, timeout)


def get_all_browsers() -> list[Browser]:
    """Get all active browser instances.

    Returns:
        List of active browsers.
    """
    return list(_browser_instances)


async def close_all_browsers() -> None:
    """Close all active browser instances."""
    for browser in list(_browser_instances):
        try:
            await browser.close()
        except Exception:
            pass


__all__ = [
    "Browser",
    "BrowserPool",
    "BrowserState",
    "close_all_browsers",
    "get_all_browsers",
]
