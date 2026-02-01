"""
Browser Context for kuromi-browser.

Provides isolated browsing contexts with separate cookies, storage,
and settings. Similar to Playwright's BrowserContext.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Union

from kuromi_browser.interfaces import BaseBrowserContext
from kuromi_browser.browser.tabs import Tab, TabManager

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPConnection
    from kuromi_browser.interfaces import BaseBrowser, BasePage
    from kuromi_browser.models import Cookie, Fingerprint, NetworkRequest, NetworkResponse, PageConfig

logger = logging.getLogger(__name__)


class ContextState(str, Enum):
    """Browser context lifecycle states."""

    CREATED = "created"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class ContextOptions:
    """Options for creating a browser context."""

    # Storage
    user_data_dir: Optional[str] = None
    """Path to user data directory for persistence."""

    accept_downloads: bool = True
    """Whether to automatically download files."""

    downloads_path: Optional[str] = None
    """Directory to save downloads."""

    # Viewport and display
    viewport_width: int = 1920
    """Viewport width in pixels."""

    viewport_height: int = 1080
    """Viewport height in pixels."""

    device_scale_factor: float = 1.0
    """Device scale factor (DPR)."""

    is_mobile: bool = False
    """Emulate mobile device."""

    has_touch: bool = False
    """Enable touch events."""

    # Locale and timezone
    locale: str = "en-US"
    """Browser locale."""

    timezone_id: Optional[str] = None
    """Timezone ID (e.g., 'America/New_York')."""

    # Geolocation
    geolocation: Optional[dict[str, float]] = None
    """Geolocation coordinates {latitude, longitude, accuracy}."""

    # Permissions
    permissions: list[str] = field(default_factory=list)
    """Granted permissions."""

    # Display settings
    color_scheme: Optional[str] = None
    """Preferred color scheme (light, dark, no-preference)."""

    reduced_motion: Optional[str] = None
    """Reduced motion preference."""

    forced_colors: Optional[str] = None
    """Forced colors mode."""

    # Network
    extra_http_headers: dict[str, str] = field(default_factory=dict)
    """Extra HTTP headers to send with every request."""

    offline: bool = False
    """Emulate offline mode."""

    http_credentials: Optional[dict[str, str]] = None
    """HTTP authentication credentials {username, password}."""

    ignore_https_errors: bool = False
    """Ignore HTTPS certificate errors."""

    proxy: Optional[str] = None
    """Proxy server URL."""

    # JavaScript
    java_script_enabled: bool = True
    """Enable JavaScript."""

    bypass_csp: bool = False
    """Bypass Content Security Policy."""

    # Recording
    record_video: bool = False
    """Record video of browser sessions."""

    video_size: Optional[dict[str, int]] = None
    """Video recording size {width, height}."""

    video_dir: Optional[str] = None
    """Directory to save videos."""

    record_har: bool = False
    """Record HAR file."""

    har_path: Optional[str] = None
    """Path to save HAR file."""

    # Service workers
    service_workers: str = "allow"
    """Service worker policy (allow, block)."""

    # Storage state
    storage_state: Optional[dict[str, Any]] = None
    """Initial storage state (cookies, localStorage)."""


@dataclass
class ContextInfo:
    """Information about a browser context."""

    context_id: str
    """CDP browser context ID."""

    state: ContextState = ContextState.CREATED
    """Context state."""

    user_data_dir: Optional[str] = None
    """User data directory path."""

    is_incognito: bool = False
    """Whether this is an incognito context."""

    is_default: bool = False
    """Whether this is the default context."""

    created_at: float = 0.0
    """Creation timestamp."""


class BrowserContext(BaseBrowserContext):
    """Isolated browser context with its own storage and settings.

    A BrowserContext is like an incognito browser profile. Pages within
    a context share cookies and storage, but are isolated from other contexts.

    Example:
        async with Browser() as browser:
            # Create isolated context
            context = await browser.new_context()

            # Create pages in context
            page1 = await context.new_page()
            page2 = await context.new_page()

            # Pages share cookies within context
            await page1.goto("https://example.com/login")
            # page2 will also be logged in

            # Close context and all its pages
            await context.close()
    """

    def __init__(
        self,
        browser: "BaseBrowser",
        connection: "CDPConnection",
        context_id: str,
        options: Optional[ContextOptions] = None,
    ) -> None:
        """Initialize browser context.

        Args:
            browser: Parent browser instance.
            connection: CDP connection.
            context_id: CDP browser context ID.
            options: Context options.
        """
        self._browser = browser
        self._connection = connection
        self._context_id = context_id
        self._options = options or ContextOptions()
        self._tabs = TabManager(connection, context_id)
        self._pages: list["BasePage"] = []
        self._init_scripts: list[str] = []
        self._exposed_functions: dict[str, Callable[..., Any]] = {}
        self._routes: list[tuple[Any, Callable[..., Any]]] = []
        self._state = ContextState.CREATED
        self._temp_dir: Optional[str] = None
        self._closed = False

    @property
    def browser(self) -> "BaseBrowser":
        """Parent browser."""
        return self._browser

    @property
    def pages(self) -> list["BasePage"]:
        """All pages in this context."""
        return list(self._pages)

    @property
    def context_id(self) -> str:
        """CDP browser context ID."""
        return self._context_id

    @property
    def tabs(self) -> TabManager:
        """Tab manager for this context."""
        return self._tabs

    @property
    def state(self) -> ContextState:
        """Context state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Whether context is closed."""
        return self._closed

    async def initialize(self) -> None:
        """Initialize the context with configured options.

        This applies viewport, locale, permissions, and other settings.
        """
        self._state = ContextState.ACTIVE

        # Enable target discovery for this context
        await self._tabs.enable_auto_attach()

        # Apply initial settings will be done per-page
        logger.debug(f"Context {self._context_id} initialized")

    async def new_page(
        self,
        *,
        config: Optional["PageConfig"] = None,
    ) -> "BasePage":
        """Create a new page in this context.

        Args:
            config: Optional page configuration.

        Returns:
            New page instance.
        """
        from kuromi_browser.page import Page

        # Create new tab
        tab = await self._tabs.new(activate=True)

        # Get page from tab
        page = await tab.get_page()

        # Apply context settings to page
        await self._apply_settings_to_page(page)

        # Apply init scripts
        for script in self._init_scripts:
            await page._cdp.send(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": script},
            )

        self._pages.append(page)
        return page

    async def _apply_settings_to_page(self, page: "BasePage") -> None:
        """Apply context settings to a page.

        Args:
            page: Page to configure.
        """
        from kuromi_browser.page import Page

        if not isinstance(page, Page):
            return

        cdp = page._cdp
        opts = self._options

        # Viewport
        await cdp.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": opts.viewport_width,
                "height": opts.viewport_height,
                "deviceScaleFactor": opts.device_scale_factor,
                "mobile": opts.is_mobile,
            },
        )

        # Touch emulation
        if opts.has_touch:
            await cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True})

        # Locale
        if opts.locale:
            await cdp.send(
                "Emulation.setLocaleOverride",
                {"locale": opts.locale},
            )

        # Timezone
        if opts.timezone_id:
            await cdp.send(
                "Emulation.setTimezoneOverride",
                {"timezoneId": opts.timezone_id},
            )

        # Geolocation
        if opts.geolocation:
            await cdp.send(
                "Emulation.setGeolocationOverride",
                {
                    "latitude": opts.geolocation.get("latitude", 0),
                    "longitude": opts.geolocation.get("longitude", 0),
                    "accuracy": opts.geolocation.get("accuracy", 1),
                },
            )

        # Color scheme
        if opts.color_scheme:
            await cdp.send(
                "Emulation.setEmulatedMedia",
                {
                    "features": [
                        {"name": "prefers-color-scheme", "value": opts.color_scheme}
                    ]
                },
            )

        # Reduced motion
        if opts.reduced_motion:
            await cdp.send(
                "Emulation.setEmulatedMedia",
                {
                    "features": [
                        {"name": "prefers-reduced-motion", "value": opts.reduced_motion}
                    ]
                },
            )

        # Extra headers
        if opts.extra_http_headers:
            await cdp.send(
                "Network.setExtraHTTPHeaders",
                {"headers": opts.extra_http_headers},
            )

        # Offline mode
        if opts.offline:
            await cdp.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": True,
                    "latency": 0,
                    "downloadThroughput": 0,
                    "uploadThroughput": 0,
                },
            )

        # Ignore HTTPS errors
        if opts.ignore_https_errors:
            await cdp.send(
                "Security.setIgnoreCertificateErrors",
                {"ignore": True},
            )

        # Bypass CSP
        if opts.bypass_csp:
            await cdp.send(
                "Page.setBypassCSP",
                {"enabled": True},
            )

        # JavaScript
        if not opts.java_script_enabled:
            await cdp.send(
                "Emulation.setScriptExecutionDisabled",
                {"value": True},
            )

    async def get_cookies(
        self,
        *urls: str,
    ) -> list["Cookie"]:
        """Get cookies for the context.

        Args:
            *urls: URLs to get cookies for.

        Returns:
            List of cookies.
        """
        from kuromi_browser.models import Cookie

        params: dict[str, Any] = {}
        if urls:
            params["urls"] = list(urls)

        if self._context_id:
            params["browserContextId"] = self._context_id

        result = await self._connection.send("Storage.getCookies", params)
        cookies = []

        for c in result.get("cookies", []):
            cookies.append(
                Cookie(
                    name=c["name"],
                    value=c["value"],
                    domain=c.get("domain", ""),
                    path=c.get("path", "/"),
                    expires=c.get("expires"),
                    http_only=c.get("httpOnly", False),
                    secure=c.get("secure", False),
                    same_site=c.get("sameSite", "Lax"),
                )
            )

        return cookies

    async def set_cookies(
        self,
        *cookies: "Cookie",
    ) -> None:
        """Set cookies for the context.

        Args:
            *cookies: Cookies to set.
        """
        cookie_list = []
        for cookie in cookies:
            cookie_list.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": cookie.secure,
                    "httpOnly": cookie.http_only,
                    "sameSite": cookie.same_site,
                }
            )

        params: dict[str, Any] = {"cookies": cookie_list}
        if self._context_id:
            params["browserContextId"] = self._context_id

        await self._connection.send("Storage.setCookies", params)

    async def clear_cookies(self) -> None:
        """Clear all cookies in the context."""
        params: dict[str, Any] = {}
        if self._context_id:
            params["browserContextId"] = self._context_id

        await self._connection.send("Storage.clearCookies", params)

    async def add_init_script(
        self,
        script: str,
    ) -> None:
        """Add a script to run on every new page.

        Args:
            script: JavaScript code to run.
        """
        self._init_scripts.append(script)

        # Apply to existing pages
        for page in self._pages:
            from kuromi_browser.page import Page

            if isinstance(page, Page):
                await page._cdp.send(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": script},
                )

    async def expose_function(
        self,
        name: str,
        callback: Callable[..., Any],
    ) -> None:
        """Expose a Python function to all pages in this context.

        Args:
            name: Function name in JavaScript.
            callback: Python callback function.
        """
        self._exposed_functions[name] = callback

        # Apply to existing pages
        for page in self._pages:
            await page.expose_function(name, callback)

    async def route(
        self,
        url: Union[str, Callable[[str], bool]],
        handler: Callable[["NetworkRequest"], Awaitable[Optional["NetworkResponse"]]],
    ) -> None:
        """Intercept network requests for all pages.

        Args:
            url: URL pattern or matcher function.
            handler: Request handler.
        """
        self._routes.append((url, handler))

        # Apply to existing pages
        for page in self._pages:
            await page.route(url, handler)

    async def unroute(
        self,
        url: Union[str, Callable[[str], bool]],
    ) -> None:
        """Remove a route handler.

        Args:
            url: URL pattern to remove.
        """
        self._routes = [(u, h) for u, h in self._routes if u != url]

        # Remove from existing pages
        for page in self._pages:
            await page.unroute(url)

    async def set_geolocation(
        self,
        latitude: float,
        longitude: float,
        *,
        accuracy: float = 0,
    ) -> None:
        """Set geolocation for the context.

        Args:
            latitude: Latitude.
            longitude: Longitude.
            accuracy: Accuracy in meters.
        """
        self._options.geolocation = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
        }

        # Apply to existing pages
        for page in self._pages:
            from kuromi_browser.page import Page

            if isinstance(page, Page):
                await page._cdp.send(
                    "Emulation.setGeolocationOverride",
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                        "accuracy": accuracy,
                    },
                )

    async def set_permissions(
        self,
        permissions: list[str],
        *,
        origin: Optional[str] = None,
    ) -> None:
        """Set permissions for the context.

        Args:
            permissions: List of permissions to grant.
            origin: Origin to grant permissions for.
        """
        self._options.permissions = permissions

        params: dict[str, Any] = {"permissions": permissions}
        if origin:
            params["origin"] = origin
        if self._context_id:
            params["browserContextId"] = self._context_id

        await self._connection.send("Browser.grantPermissions", params)

    async def clear_permissions(self) -> None:
        """Clear all granted permissions."""
        params: dict[str, Any] = {}
        if self._context_id:
            params["browserContextId"] = self._context_id

        await self._connection.send("Browser.resetPermissions", params)

    async def storage_state(self) -> dict[str, Any]:
        """Get storage state (cookies, localStorage).

        Returns:
            Storage state dictionary.
        """
        cookies = await self.get_cookies()

        return {
            "cookies": [
                {
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path,
                    "expires": c.expires,
                    "httpOnly": c.http_only,
                    "secure": c.secure,
                    "sameSite": c.same_site,
                }
                for c in cookies
            ],
            # Note: localStorage would require page evaluation
        }

    async def set_storage_state(self, state: dict[str, Any]) -> None:
        """Set storage state.

        Args:
            state: Storage state dictionary.
        """
        from kuromi_browser.models import Cookie

        cookies = state.get("cookies", [])
        cookie_objects = [
            Cookie(
                name=c["name"],
                value=c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
                expires=c.get("expires"),
                http_only=c.get("httpOnly", False),
                secure=c.get("secure", False),
                same_site=c.get("sameSite", "Lax"),
            )
            for c in cookies
        ]

        await self.set_cookies(*cookie_objects)

    async def close(self) -> None:
        """Close the context and all its pages."""
        if self._closed:
            return

        self._closed = True
        self._state = ContextState.CLOSED

        # Close all pages
        for page in self._pages:
            try:
                await page.close()
            except Exception:
                pass

        self._pages.clear()

        # Cleanup tabs
        await self._tabs.cleanup()

        # Dispose browser context if not default
        if self._context_id:
            try:
                await self._connection.send(
                    "Target.disposeBrowserContext",
                    {"browserContextId": self._context_id},
                )
            except Exception:
                pass

        # Cleanup temp directory
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass

        logger.debug(f"Context {self._context_id} closed")

    async def __aenter__(self) -> "BrowserContext":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


class DefaultContext(BrowserContext):
    """Default browser context.

    The default context shares storage with all pages that are not
    created in an explicit context. It cannot be closed.
    """

    def __init__(
        self,
        browser: "BaseBrowser",
        connection: "CDPConnection",
    ) -> None:
        """Initialize default context.

        Args:
            browser: Parent browser.
            connection: CDP connection.
        """
        super().__init__(browser, connection, "", ContextOptions())

    async def close(self) -> None:
        """Cannot close default context - only closes pages."""
        # Only close pages, not the context itself
        for page in self._pages:
            try:
                await page.close()
            except Exception:
                pass
        self._pages.clear()


__all__ = [
    "BrowserContext",
    "ContextInfo",
    "ContextOptions",
    "ContextState",
    "DefaultContext",
]
