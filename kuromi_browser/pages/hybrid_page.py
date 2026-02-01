"""
HybridPage - Intelligent combination of browser and session modes.

Provides the best of both worlds by using HTTP session for fast data
fetching and browser mode for JavaScript execution when needed.
Includes automatic mode switching and cookie synchronization.
"""

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional, Union
from urllib.parse import urlparse

from kuromi_browser.models import PageMode
from kuromi_browser.pages.browser_page import BrowserPage, BrowserElement
from kuromi_browser.pages.session_page import SessionPage, SessionPageElement
from kuromi_browser.pages.cookies import (
    CookieJar,
    CookieSyncManager,
    sync_cookies_browser_to_session,
    sync_cookies_session_to_browser,
)
from kuromi_browser.session import Response

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession
    from kuromi_browser.session import Session
    from kuromi_browser.models import (
        Cookie,
        Fingerprint,
        NetworkResponse,
    )


class HybridMode(str, Enum):
    """Current operating mode of HybridPage."""

    AUTO = "auto"  # Automatically choose based on operation
    BROWSER = "browser"  # Force browser mode
    SESSION = "session"  # Force session mode


class HybridPage:
    """Intelligent hybrid page combining browser and HTTP session modes.

    Automatically switches between modes based on the operation:
    - Uses SessionPage (HTTP) for fast data fetching, API calls
    - Uses BrowserPage (CDP) for JavaScript execution, user interactions

    Features:
    - Automatic cookie synchronization between modes
    - Intelligent mode selection based on URL and operation
    - Manual mode override when needed
    - Unified API for both modes

    Example:
        async with HybridPage(cdp_session, http_session) as page:
            # Uses session mode for fast fetch
            await page.goto("https://example.com")

            # Automatically switches to browser for JS
            await page.click("button.dynamic")

            # Force session mode for API call
            response = await page.fetch("https://api.example.com/data")
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        http_session: "Session",
        fingerprint: Optional["Fingerprint"] = None,
        auto_sync_cookies: bool = True,
        prefer_session: bool = True,
    ) -> None:
        """Initialize HybridPage.

        Args:
            cdp_session: CDP session for browser mode.
            http_session: HTTP session for session mode.
            fingerprint: Optional fingerprint configuration.
            auto_sync_cookies: Automatically sync cookies between modes.
            prefer_session: Prefer session mode when possible.
        """
        self._browser_page = BrowserPage(cdp_session, fingerprint=fingerprint)
        self._session_page = SessionPage.__new__(SessionPage)
        self._session_page._session = http_session
        self._session_page._fingerprint = fingerprint
        self._session_page._current_response = None
        self._session_page._url = ""
        self._session_page._history = []
        self._session_page._history_index = -1

        self._fingerprint = fingerprint
        self._auto_sync_cookies = auto_sync_cookies
        self._prefer_session = prefer_session

        self._current_mode = HybridMode.AUTO
        self._active_mode: Optional[PageMode] = None
        self._url = ""
        self._last_browser_url = ""
        self._last_session_url = ""

        # Cookie synchronization
        self._cookie_jar = CookieJar()
        self._cookie_manager = CookieSyncManager(
            jar=self._cookie_jar,
            auto_sync=auto_sync_cookies,
        )

        # Track which mode last modified cookies
        self._cookies_dirty_in: Optional[PageMode] = None

        # URLs that require browser mode (e.g., known JS-heavy sites)
        self._browser_required_patterns: list[str] = []

        # URLs that work well with session mode
        self._session_preferred_patterns: list[str] = [
            "/api/",
            ".json",
            ".xml",
            "/graphql",
        ]

    @property
    def browser_page(self) -> BrowserPage:
        """Get the underlying BrowserPage."""
        return self._browser_page

    @property
    def session_page(self) -> SessionPage:
        """Get the underlying SessionPage."""
        return self._session_page

    @property
    def url(self) -> str:
        """Get current URL."""
        return self._url

    @property
    def title(self) -> str:
        """Get page title."""
        if self._active_mode == PageMode.BROWSER:
            return self._browser_page.title
        elif self._active_mode == PageMode.SESSION:
            return self._session_page.title
        return ""

    @property
    def mode(self) -> PageMode:
        return PageMode.HYBRID

    @property
    def active_mode(self) -> Optional[PageMode]:
        """Get currently active mode (browser or session)."""
        return self._active_mode

    @property
    def current_mode_setting(self) -> HybridMode:
        """Get the current mode setting (auto/browser/session)."""
        return self._current_mode

    def set_mode(self, mode: HybridMode) -> None:
        """Set the operating mode.

        Args:
            mode: HybridMode.AUTO, HybridMode.BROWSER, or HybridMode.SESSION
        """
        self._current_mode = mode

    def add_browser_required_pattern(self, pattern: str) -> None:
        """Add URL pattern that requires browser mode.

        Args:
            pattern: URL pattern (substring match).
        """
        self._browser_required_patterns.append(pattern)

    def add_session_preferred_pattern(self, pattern: str) -> None:
        """Add URL pattern that prefers session mode.

        Args:
            pattern: URL pattern (substring match).
        """
        self._session_preferred_patterns.append(pattern)

    def _should_use_browser(self, url: str, operation: str = "navigate") -> bool:
        """Determine if browser mode should be used.

        Args:
            url: Target URL.
            operation: Type of operation (navigate, click, evaluate, etc.)

        Returns:
            True if browser mode should be used.
        """
        # Forced mode
        if self._current_mode == HybridMode.BROWSER:
            return True
        if self._current_mode == HybridMode.SESSION:
            return False

        # Operations that require browser
        browser_operations = {
            "click",
            "dblclick",
            "fill",
            "type",
            "press",
            "hover",
            "check",
            "uncheck",
            "select_option",
            "evaluate",
            "screenshot",
            "pdf",
            "expose_function",
            "route",
        }
        if operation in browser_operations:
            return True

        # Check URL patterns
        for pattern in self._browser_required_patterns:
            if pattern in url:
                return True

        # Prefer session for API-like URLs
        if self._prefer_session:
            for pattern in self._session_preferred_patterns:
                if pattern in url:
                    return False

        # Default: prefer session for navigation, browser for interactions
        if operation == "navigate":
            return not self._prefer_session

        return True

    async def _sync_cookies_if_needed(self, target_mode: PageMode) -> None:
        """Sync cookies to target mode if needed.

        Args:
            target_mode: Mode to sync cookies to.
        """
        if not self._auto_sync_cookies:
            return

        if self._cookies_dirty_in is None:
            return

        if self._cookies_dirty_in == target_mode:
            return

        # Sync from the dirty source to target
        if self._cookies_dirty_in == PageMode.BROWSER and target_mode == PageMode.SESSION:
            await self._cookie_manager.sync_from_browser(
                self._browser_page._cdp, urls=[self._url] if self._url else None
            )
            await self._cookie_manager.sync_to_session(
                self._session_page._session,
                domain=urlparse(self._url).netloc if self._url else None,
            )
        elif self._cookies_dirty_in == PageMode.SESSION and target_mode == PageMode.BROWSER:
            await self._cookie_manager.sync_from_session(
                self._session_page._session,
                domain=urlparse(self._url).netloc if self._url else "",
            )
            await self._cookie_manager.sync_to_browser(
                self._browser_page._cdp,
                domain=urlparse(self._url).netloc if self._url else None,
            )

        self._cookies_dirty_in = None

    async def _switch_to_browser(self) -> None:
        """Switch to browser mode."""
        await self._sync_cookies_if_needed(PageMode.BROWSER)

        # Navigate browser to current URL if different
        if self._url and self._url != self._last_browser_url:
            await self._browser_page.goto(self._url)
            self._last_browser_url = self._url

        self._active_mode = PageMode.BROWSER

    async def _switch_to_session(self) -> None:
        """Switch to session mode."""
        await self._sync_cookies_if_needed(PageMode.SESSION)
        self._active_mode = PageMode.SESSION

    async def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
        use_browser: Optional[bool] = None,
    ) -> Optional[Union["NetworkResponse", Response]]:
        """Navigate to a URL.

        Args:
            url: Target URL.
            timeout: Request/navigation timeout.
            wait_until: Load state to wait for (browser mode).
            referer: Referer header.
            use_browser: Force browser mode if True, session if False.

        Returns:
            Response in session mode, None in browser mode.
        """
        should_use_browser = (
            use_browser
            if use_browser is not None
            else self._should_use_browser(url, "navigate")
        )

        self._url = url

        if should_use_browser:
            await self._switch_to_browser()
            await self._browser_page.goto(
                url, timeout=timeout, wait_until=wait_until, referer=referer
            )
            self._last_browser_url = url
            self._cookies_dirty_in = PageMode.BROWSER
            return None
        else:
            await self._switch_to_session()
            response = await self._session_page.goto(
                url, timeout=timeout, referer=referer
            )
            self._last_session_url = url
            self._cookies_dirty_in = PageMode.SESSION
            return response

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: Optional[dict[str, str]] = None,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        use_browser_cookies: bool = True,
    ) -> Response:
        """Fetch URL using HTTP session (always uses session mode).

        This is a convenience method for fast HTTP requests that don't
        need browser rendering.

        Args:
            url: Target URL.
            method: HTTP method.
            headers: Request headers.
            data: Request body.
            json: JSON body.
            timeout: Request timeout.
            use_browser_cookies: Sync cookies from browser before request.

        Returns:
            HTTP Response.
        """
        if use_browser_cookies and self._cookies_dirty_in == PageMode.BROWSER:
            await self._sync_cookies_if_needed(PageMode.SESSION)

        return await self._session_page._session.request(
            method, url, headers=headers, data=data, json=json, timeout=timeout
        )

    async def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional[Union["NetworkResponse", Response]]:
        """Reload current page."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.reload(timeout=timeout, wait_until=wait_until)
        else:
            return await self._session_page.reload(timeout=timeout)

    async def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional[Union["NetworkResponse", Response]]:
        """Navigate back."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.go_back(timeout=timeout, wait_until=wait_until)
        else:
            return await self._session_page.go_back(timeout=timeout)

    async def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional[Union["NetworkResponse", Response]]:
        """Navigate forward."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.go_forward(timeout=timeout, wait_until=wait_until)
        else:
            return await self._session_page.go_forward(timeout=timeout)

    async def content(self) -> str:
        """Get page HTML content."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.content()
        else:
            return await self._session_page.content()

    async def set_content(
        self,
        html: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Set page content (browser mode only)."""
        await self._switch_to_browser()
        await self._browser_page.set_content(html, timeout=timeout, wait_until=wait_until)

    async def query_selector(
        self, selector: str
    ) -> Optional[Union[BrowserElement, SessionPageElement]]:
        """Find element by selector."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.query_selector(selector)
        else:
            return await self._session_page.query_selector(selector)

    async def query_selector_all(
        self, selector: str
    ) -> list[Union[BrowserElement, SessionPageElement]]:
        """Find all elements matching selector."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.query_selector_all(selector)
        else:
            return await self._session_page.query_selector_all(selector)

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[Union[BrowserElement, SessionPageElement]]:
        """Wait for element."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.wait_for_selector(
                selector, state=state, timeout=timeout
            )
        else:
            return await self._session_page.wait_for_selector(selector)

    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for load state."""
        if self._active_mode == PageMode.BROWSER:
            await self._browser_page.wait_for_load_state(state, timeout=timeout)

    async def wait_for_url(
        self,
        url: Union[str, Callable[[str], bool]],
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Wait for URL match."""
        if self._active_mode == PageMode.BROWSER:
            await self._browser_page.wait_for_url(url, timeout=timeout, wait_until=wait_until)
        else:
            await self._session_page.wait_for_url(url)

    async def wait_for_timeout(self, timeout: float) -> None:
        """Wait for specified milliseconds."""
        await asyncio.sleep(timeout / 1000)

    # Browser-only operations (auto-switch to browser)

    async def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click element (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.click(
            selector,
            button=button,
            click_count=click_count,
            delay=delay,
            force=force,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
        )
        self._cookies_dirty_in = PageMode.BROWSER

    async def dblclick(
        self,
        selector: str,
        *,
        button: str = "left",
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Double-click element (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.dblclick(
            selector,
            button=button,
            delay=delay,
            force=force,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
        )
        self._cookies_dirty_in = PageMode.BROWSER

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill input (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.fill(selector, value, force=force, timeout=timeout)

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.type(selector, text, delay=delay, timeout=timeout)

    async def press(
        self,
        selector: str,
        key: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Press key (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.press(selector, key, delay=delay, timeout=timeout)

    async def hover(
        self,
        selector: str,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over element (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.hover(
            selector, force=force, modifiers=modifiers, position=position, timeout=timeout
        )

    async def select_option(
        self,
        selector: str,
        *values: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.select_option(selector, *values, timeout=timeout)

    async def check(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Check checkbox (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.check(selector, force=force, timeout=timeout)

    async def uncheck(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Uncheck checkbox (switches to browser mode)."""
        await self._switch_to_browser()
        await self._browser_page.uncheck(selector, force=force, timeout=timeout)

    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.evaluate(expression, *args)

    async def evaluate_handle(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate and return handle (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.evaluate_handle(expression, *args)

    async def add_script_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
        type: str = "",
    ) -> BrowserElement:
        """Add script tag (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.add_script_tag(
            url=url, path=path, content=content, type=type
        )

    async def add_style_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
    ) -> BrowserElement:
        """Add style tag (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.add_style_tag(url=url, path=path, content=content)

    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict[str, float]] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take screenshot (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.screenshot(
            path=path,
            full_page=full_page,
            clip=clip,
            type=type,
            quality=quality,
            omit_background=omit_background,
        )

    async def pdf(
        self,
        *,
        path: Optional[str] = None,
        scale: float = 1,
        display_header_footer: bool = False,
        header_template: str = "",
        footer_template: str = "",
        print_background: bool = False,
        landscape: bool = False,
        page_ranges: str = "",
        format: str = "Letter",
        width: Optional[str] = None,
        height: Optional[str] = None,
        margin: Optional[dict[str, str]] = None,
        prefer_css_page_size: bool = False,
    ) -> bytes:
        """Generate PDF (switches to browser mode)."""
        await self._switch_to_browser()
        return await self._browser_page.pdf(
            path=path,
            scale=scale,
            display_header_footer=display_header_footer,
            header_template=header_template,
            footer_template=footer_template,
            print_background=print_background,
            landscape=landscape,
            page_ranges=page_ranges,
            format=format,
            width=width,
            height=height,
            margin=margin,
            prefer_css_page_size=prefer_css_page_size,
        )

    # Cookie management (unified across modes)

    async def get_cookies(self, *urls: str) -> list["Cookie"]:
        """Get cookies from active mode."""
        if self._active_mode == PageMode.BROWSER:
            return await self._browser_page.get_cookies(*urls)
        else:
            return await self._session_page.get_cookies(*urls)

    async def set_cookies(self, *cookies: "Cookie") -> None:
        """Set cookies in active mode."""
        if self._active_mode == PageMode.BROWSER:
            await self._browser_page.set_cookies(*cookies)
            self._cookies_dirty_in = PageMode.BROWSER
        else:
            await self._session_page.set_cookies(*cookies)
            self._cookies_dirty_in = PageMode.SESSION

    async def delete_cookies(self, *names: str) -> None:
        """Delete cookies."""
        if self._active_mode == PageMode.BROWSER:
            await self._browser_page.delete_cookies(*names)
        else:
            await self._session_page.delete_cookies(*names)

    async def clear_cookies(self) -> None:
        """Clear all cookies in both modes."""
        await self._browser_page.clear_cookies()
        await self._session_page.clear_cookies()
        self._cookie_jar.clear()
        self._cookies_dirty_in = None

    async def sync_cookies(self) -> None:
        """Force cookie synchronization between modes."""
        if self._active_mode == PageMode.BROWSER:
            await self._cookie_manager.sync_from_browser(
                self._browser_page._cdp, urls=[self._url] if self._url else None
            )
            await self._cookie_manager.sync_to_session(
                self._session_page._session,
                domain=urlparse(self._url).netloc if self._url else None,
            )
        else:
            await self._cookie_manager.sync_from_session(
                self._session_page._session,
                domain=urlparse(self._url).netloc if self._url else "",
            )
            await self._cookie_manager.sync_to_browser(
                self._browser_page._cdp,
                domain=urlparse(self._url).netloc if self._url else None,
            )
        self._cookies_dirty_in = None

    # Other browser page methods

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers in both modes."""
        await self._browser_page.set_extra_http_headers(headers)
        await self._session_page.set_extra_http_headers(headers)

    async def set_viewport(
        self,
        width: int,
        height: int,
        *,
        device_scale_factor: float = 1,
        is_mobile: bool = False,
        has_touch: bool = False,
    ) -> None:
        """Set viewport (browser mode)."""
        await self._browser_page.set_viewport(
            width, height,
            device_scale_factor=device_scale_factor,
            is_mobile=is_mobile,
            has_touch=has_touch,
        )

    async def expose_function(
        self,
        name: str,
        callback: Callable[..., Any],
    ) -> None:
        """Expose function to page (browser mode)."""
        await self._browser_page.expose_function(name, callback)

    async def route(
        self,
        url: Union[str, Callable[[str], bool]],
        handler: Callable[..., Any],
    ) -> None:
        """Set up request interception (browser mode)."""
        await self._browser_page.route(url, handler)

    async def unroute(
        self,
        url: Union[str, Callable[[str], bool]],
    ) -> None:
        """Remove request interception (browser mode)."""
        await self._browser_page.unroute(url)

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Register event handler (browser mode)."""
        self._browser_page.on(event, handler)

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove event handler (browser mode)."""
        self._browser_page.off(event, handler)

    async def close(self) -> None:
        """Close both browser and session."""
        await self._browser_page.close()
        await self._session_page.close()

    async def __aenter__(self) -> "HybridPage":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        return f"<HybridPage url={self._url!r} active_mode={self._active_mode}>"
