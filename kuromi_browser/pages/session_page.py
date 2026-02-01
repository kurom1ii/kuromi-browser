"""
SessionPage - HTTP-only mode with TLS fingerprint spoofing.

Provides lightweight HTTP client capabilities using curl_cffi.
No JavaScript execution, but significantly faster than browser mode.
Ideal for API requests and scraping static content.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from kuromi_browser.models import PageMode
from kuromi_browser.session import Session, Response, SessionElement

if TYPE_CHECKING:
    from kuromi_browser.models import (
        Cookie,
        Fingerprint,
        NetworkResponse,
    )


class SessionPageElement:
    """Element wrapper for SessionPage that provides async interface.

    Wraps SessionElement (lxml-based) to provide an interface similar
    to BrowserElement, but without JavaScript execution capabilities.
    """

    def __init__(self, element: SessionElement) -> None:
        """Initialize SessionPageElement.

        Args:
            element: The underlying SessionElement to wrap.
        """
        self._element = element

    @property
    def tag_name(self) -> str:
        """Get tag name."""
        return self._element.tag

    async def get_attribute(self, name: str) -> Optional[str]:
        """Get element attribute."""
        return self._element.attr(name)

    async def get_property(self, name: str) -> Any:
        """Get element property (same as attribute in session mode)."""
        return self._element.attr(name)

    async def text_content(self) -> Optional[str]:
        """Get text content."""
        return self._element.text

    async def inner_text(self) -> str:
        """Get inner text."""
        return self._element.text

    async def inner_html(self) -> str:
        """Get inner HTML."""
        return self._element.inner_html

    async def outer_html(self) -> str:
        """Get outer HTML."""
        return self._element.html

    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Not available in session mode."""
        return None

    async def is_visible(self) -> bool:
        """Always True in session mode (no visibility info)."""
        return True

    async def is_enabled(self) -> bool:
        """Check if element is enabled (based on disabled attribute)."""
        return self._element.attr("disabled") is None

    async def is_checked(self) -> bool:
        """Check if checkbox is checked (based on checked attribute)."""
        return self._element.attr("checked") is not None

    async def click(self, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("click() not available in session mode - use browser mode")

    async def dblclick(self, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("dblclick() not available in session mode")

    async def hover(self, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("hover() not available in session mode")

    async def fill(self, value: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("fill() not available in session mode")

    async def type(self, text: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("type() not available in session mode")

    async def press(self, key: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("press() not available in session mode")

    async def select_option(self, *values: str, **kwargs: Any) -> list[str]:
        """Not available in session mode."""
        raise NotImplementedError("select_option() not available in session mode")

    async def check(self, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("check() not available in session mode")

    async def uncheck(self, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("uncheck() not available in session mode")

    async def focus(self) -> None:
        """Not available in session mode."""
        pass  # No-op

    async def scroll_into_view(self) -> None:
        """Not available in session mode."""
        pass  # No-op

    async def screenshot(self, **kwargs: Any) -> bytes:
        """Not available in session mode."""
        raise NotImplementedError("screenshot() not available in session mode")

    async def query_selector(self, selector: str) -> Optional["SessionPageElement"]:
        """Find child element."""
        elem = self._element.ele(selector)
        return SessionPageElement(elem) if elem else None

    async def query_selector_all(self, selector: str) -> list["SessionPageElement"]:
        """Find all child elements."""
        return [SessionPageElement(e) for e in self._element.eles(selector)]

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Not available in session mode."""
        raise NotImplementedError("evaluate() not available in session mode")

    @property
    def attrs(self) -> dict[str, str]:
        """Get all attributes."""
        return self._element.attrs

    @property
    def id(self) -> Optional[str]:
        """Get element ID."""
        return self._element.id

    @property
    def classes(self) -> list[str]:
        """Get element classes."""
        return self._element.classes

    def __repr__(self) -> str:
        return f"<SessionPageElement {self._element}>"


class SessionPage:
    """HTTP-only page mode using curl_cffi.

    Provides fast HTTP requests with TLS fingerprint spoofing.
    Does not support JavaScript execution but is much faster than
    browser mode for static content.

    Example:
        async with SessionPage(impersonate="chrome120") as page:
            response = await page.goto("https://example.com")
            title = await page.title
            links = await page.query_selector_all("a[href]")
    """

    def __init__(
        self,
        fingerprint: Optional["Fingerprint"] = None,
        proxy: Optional[str] = None,
        impersonate: str = "chrome120",
        timeout: float = 30.0,
        verify: bool = True,
    ) -> None:
        """Initialize SessionPage.

        Args:
            fingerprint: Optional fingerprint for TLS/JA3 spoofing.
            proxy: Optional proxy URL.
            impersonate: Browser to impersonate (e.g., "chrome120").
            timeout: Default request timeout in seconds.
            verify: Whether to verify SSL certificates.
        """
        self._session = Session(
            fingerprint=fingerprint,
            proxy=proxy,
            impersonate=impersonate,
            timeout=timeout,
            verify=verify,
        )
        self._fingerprint = fingerprint
        self._current_response: Optional[Response] = None
        self._url = ""
        self._history: list[str] = []
        self._history_index = -1

    @property
    def session(self) -> Session:
        """Get the underlying HTTP session."""
        return self._session

    @property
    def url(self) -> str:
        """Get current URL."""
        return self._url

    @property
    def title(self) -> str:
        """Get page title (from last response)."""
        if self._current_response:
            return self._current_response.title or ""
        return ""

    @property
    def mode(self) -> PageMode:
        return PageMode.SESSION

    @property
    def response(self) -> Optional[Response]:
        """Get the current HTTP response."""
        return self._current_response

    async def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
        method: str = "GET",
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Response:
        """Navigate to a URL (make HTTP request).

        Args:
            url: Target URL.
            timeout: Request timeout.
            wait_until: Ignored in session mode.
            referer: Referer header.
            method: HTTP method.
            data: Request body data.
            json: JSON request body.
            headers: Additional headers.

        Returns:
            HTTP Response object.
        """
        req_headers = headers or {}
        if referer:
            req_headers["Referer"] = referer

        self._current_response = await self._session.request(
            method,
            url,
            data=data,
            json=json,
            headers=req_headers if req_headers else None,
            timeout=timeout,
        )

        self._url = self._current_response.url

        # Update history
        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]
        self._history.append(self._url)
        self._history_index = len(self._history) - 1

        return self._current_response

    async def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Response:
        """Reload the current page."""
        if not self._url:
            raise RuntimeError("No URL to reload")
        return await self.goto(self._url, timeout=timeout)

    async def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional[Response]:
        """Navigate back in history."""
        if self._history_index > 0:
            self._history_index -= 1
            url = self._history[self._history_index]
            return await self.goto(url, timeout=timeout)
        return None

    async def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional[Response]:
        """Navigate forward in history."""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            url = self._history[self._history_index]
            return await self.goto(url, timeout=timeout)
        return None

    async def content(self) -> str:
        """Get page HTML content."""
        if self._current_response:
            return self._current_response.text
        return ""

    async def set_content(
        self,
        html: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Not supported in session mode."""
        raise NotImplementedError("set_content() not available in session mode")

    async def query_selector(self, selector: str) -> Optional[SessionPageElement]:
        """Find element by selector."""
        if not self._current_response:
            return None
        elem = self._current_response.ele(selector)
        return SessionPageElement(elem) if elem else None

    async def query_selector_all(self, selector: str) -> list[SessionPageElement]:
        """Find all elements matching selector."""
        if not self._current_response:
            return []
        return [SessionPageElement(e) for e in self._current_response.eles(selector)]

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[SessionPageElement]:
        """Find element (no actual waiting in session mode)."""
        return await self.query_selector(selector)

    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """No-op in session mode (content already loaded)."""
        pass

    async def wait_for_url(
        self,
        url: Union[str, Callable[[str], bool]],
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Check URL matches (no actual waiting)."""
        if callable(url):
            if not url(self._url):
                raise RuntimeError(f"URL {self._url} does not match predicate")
        elif self._url != url and url not in self._url:
            raise RuntimeError(f"URL {self._url} does not match {url}")

    async def wait_for_timeout(self, timeout: float) -> None:
        """Wait for specified milliseconds."""
        await asyncio.sleep(timeout / 1000)

    # HTTP convenience methods

    async def get(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """Make GET request."""
        return await self._session.get(
            url, params=params, headers=headers, timeout=timeout
        )

    async def post(
        self,
        url: str,
        *,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """Make POST request."""
        return await self._session.post(
            url, data=data, json=json, headers=headers, timeout=timeout
        )

    async def put(
        self,
        url: str,
        *,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """Make PUT request."""
        return await self._session.put(
            url, data=data, json=json, headers=headers, timeout=timeout
        )

    async def patch(
        self,
        url: str,
        *,
        data: Optional[Any] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """Make PATCH request."""
        return await self._session.patch(
            url, data=data, json=json, headers=headers, timeout=timeout
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """Make DELETE request."""
        return await self._session.delete(url, headers=headers, timeout=timeout)

    # Browser-like methods that are not supported

    async def click(self, selector: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("click() not available in session mode")

    async def dblclick(self, selector: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("dblclick() not available in session mode")

    async def fill(self, selector: str, value: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("fill() not available in session mode")

    async def type(self, selector: str, text: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("type() not available in session mode")

    async def press(self, selector: str, key: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("press() not available in session mode")

    async def hover(self, selector: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("hover() not available in session mode")

    async def select_option(self, selector: str, *values: str, **kwargs: Any) -> list[str]:
        """Not available in session mode."""
        raise NotImplementedError("select_option() not available in session mode")

    async def check(self, selector: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("check() not available in session mode")

    async def uncheck(self, selector: str, **kwargs: Any) -> None:
        """Not available in session mode."""
        raise NotImplementedError("uncheck() not available in session mode")

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Not available in session mode."""
        raise NotImplementedError("evaluate() not available in session mode")

    async def evaluate_handle(self, expression: str, *args: Any) -> Any:
        """Not available in session mode."""
        raise NotImplementedError("evaluate_handle() not available in session mode")

    async def add_script_tag(self, **kwargs: Any) -> Any:
        """Not available in session mode."""
        raise NotImplementedError("add_script_tag() not available in session mode")

    async def add_style_tag(self, **kwargs: Any) -> Any:
        """Not available in session mode."""
        raise NotImplementedError("add_style_tag() not available in session mode")

    async def screenshot(self, **kwargs: Any) -> bytes:
        """Not available in session mode."""
        raise NotImplementedError("screenshot() not available in session mode")

    async def pdf(self, **kwargs: Any) -> bytes:
        """Not available in session mode."""
        raise NotImplementedError("pdf() not available in session mode")

    # Cookie management

    async def get_cookies(self, *urls: str) -> list["Cookie"]:
        """Get cookies."""
        from kuromi_browser.models import Cookie

        session_cookies = self._session.get_cookies()
        return [
            Cookie(name=name, value=value, domain="", path="/")
            for name, value in session_cookies.items()
        ]

    async def set_cookies(self, *cookies: "Cookie") -> None:
        """Set cookies."""
        cookies_dict = {c.name: c.value for c in cookies}
        await self._session.set_cookies(cookies_dict)

    async def delete_cookies(self, *names: str) -> None:
        """Delete specific cookies."""
        for name in names:
            await self._session.delete_cookie(name)

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        await self._session.clear_cookies()

    async def set_extra_http_headers(self, headers: dict[str, str]) -> None:
        """Set default headers for all requests."""
        self._session.set_headers(headers)

    async def set_viewport(self, width: int, height: int, **kwargs: Any) -> None:
        """Not applicable in session mode."""
        pass  # No-op

    async def expose_function(self, name: str, callback: Callable[..., Any]) -> None:
        """Not available in session mode."""
        raise NotImplementedError("expose_function() not available in session mode")

    async def route(self, url: Union[str, Callable[[str], bool]], handler: Callable[..., Any]) -> None:
        """Not available in session mode."""
        raise NotImplementedError("route() not available in session mode")

    async def unroute(self, url: Union[str, Callable[[str], bool]]) -> None:
        """Not available in session mode."""
        raise NotImplementedError("unroute() not available in session mode")

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Not available in session mode."""
        pass  # No-op

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Not available in session mode."""
        pass  # No-op

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()

    # Proxy and fingerprint management

    async def set_proxy(self, proxy: Optional[str]) -> None:
        """Set proxy for requests."""
        await self._session.set_proxy(proxy)

    async def set_fingerprint(self, fingerprint: "Fingerprint") -> None:
        """Set fingerprint for TLS spoofing."""
        self._fingerprint = fingerprint
        await self._session.set_fingerprint(fingerprint)

    # Context manager

    async def __aenter__(self) -> "SessionPage":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        return f"<SessionPage url={self._url!r}>"
