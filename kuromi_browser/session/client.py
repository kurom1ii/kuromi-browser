"""
HTTP session client with TLS fingerprint spoofing.

Provides a lightweight HTTP client using curl_cffi for making requests
that appear to come from real browsers.
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from curl_cffi.requests import AsyncSession as CurlAsyncSession

from kuromi_browser.session.response import Response

if TYPE_CHECKING:
    from kuromi_browser.models import Fingerprint


class Session:
    """Async HTTP session with TLS fingerprint spoofing.

    Uses curl_cffi to impersonate browser TLS/JA3 fingerprints,
    making HTTP requests appear to come from real browsers.

    Example:
        async with Session(impersonate="chrome120") as session:
            response = await session.get("https://example.com")
            print(response.status_code)
            title = response.ele("title")
            print(title.text)
    """

    def __init__(
        self,
        fingerprint: Optional["Fingerprint"] = None,
        proxy: Optional[str] = None,
        impersonate: str = "chrome120",
        timeout: float = 30.0,
        verify: bool = True,
    ) -> None:
        """Initialize Session.

        Args:
            fingerprint: Optional fingerprint for TLS/JA3 spoofing.
            proxy: Optional proxy URL (e.g., "http://user:pass@host:port").
            impersonate: Browser to impersonate (e.g., "chrome120", "firefox").
            timeout: Default request timeout in seconds.
            verify: Whether to verify SSL certificates.
        """
        self._fingerprint = fingerprint
        self._proxy = proxy
        self._impersonate = impersonate
        self._timeout = timeout
        self._verify = verify
        self._cookies: dict[str, str] = {}
        self._headers: dict[str, str] = {}
        self._client: Optional[CurlAsyncSession] = None

        # Apply fingerprint user-agent if provided
        if fingerprint:
            self._headers["User-Agent"] = fingerprint.user_agent

    @property
    def cookies(self) -> dict[str, str]:
        """Get current session cookies."""
        return self._cookies.copy()

    @property
    def headers(self) -> dict[str, str]:
        """Get current session headers."""
        return self._headers.copy()

    async def _ensure_client(self) -> CurlAsyncSession:
        """Initialize the curl_cffi client if needed.

        Returns:
            The curl_cffi async session.
        """
        if self._client is None:
            self._client = CurlAsyncSession(
                impersonate=self._impersonate,
                proxy=self._proxy,
                timeout=self._timeout,
                verify=self._verify,
            )
            # Set initial cookies
            for name, value in self._cookies.items():
                self._client.cookies.set(name, value)
        return self._client

    def _merge_headers(
        self, headers: Optional[dict[str, str]] = None
    ) -> dict[str, str]:
        """Merge request headers with session headers.

        Args:
            headers: Optional request-specific headers.

        Returns:
            Merged headers dictionary.
        """
        merged = self._headers.copy()
        if headers:
            merged.update(headers)
        return merged

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, etc.).
            url: Target URL.
            params: URL query parameters.
            data: Request body (form data or raw).
            json: JSON request body (auto-serialized).
            headers: Request headers.
            cookies: Request cookies.
            timeout: Request timeout in seconds.
            allow_redirects: Whether to follow redirects.
            **kwargs: Additional arguments passed to curl_cffi.

        Returns:
            Response wrapper with HTML parsing capabilities.
        """
        client = await self._ensure_client()

        merged_headers = self._merge_headers(headers)
        merged_cookies = self._cookies.copy()
        if cookies:
            merged_cookies.update(cookies)

        raw_response = await client.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=merged_headers,
            cookies=merged_cookies,
            timeout=timeout or self._timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

        # Update session cookies from response
        self._cookies.update(dict(raw_response.cookies))

        return Response(raw_response)

    async def get(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a GET request.

        Args:
            url: Target URL.
            params: URL query parameters.
            headers: Request headers.
            cookies: Request cookies.
            timeout: Request timeout in seconds.
            allow_redirects: Whether to follow redirects.
            **kwargs: Additional arguments.

        Returns:
            Response wrapper.
        """
        return await self.request(
            "GET",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a POST request.

        Args:
            url: Target URL.
            data: Form data or raw body.
            json: JSON body (auto-serialized).
            params: URL query parameters.
            headers: Request headers.
            cookies: Request cookies.
            timeout: Request timeout in seconds.
            allow_redirects: Whether to follow redirects.
            **kwargs: Additional arguments.

        Returns:
            Response wrapper.
        """
        return await self.request(
            "POST",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a PUT request."""
        return await self.request(
            "PUT",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def patch(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a PATCH request."""
        return await self.request(
            "PATCH",
            url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a DELETE request."""
        return await self.request(
            "DELETE",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def head(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform a HEAD request."""
        return await self.request(
            "HEAD",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    async def options(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> Response:
        """Perform an OPTIONS request."""
        return await self.request(
            "OPTIONS",
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            allow_redirects=allow_redirects,
            **kwargs,
        )

    # Cookie management

    async def set_cookies(self, cookies: dict[str, str]) -> None:
        """Set session cookies.

        Args:
            cookies: Dictionary of cookie name-value pairs.
        """
        self._cookies.update(cookies)
        if self._client is not None:
            for name, value in cookies.items():
                self._client.cookies.set(name, value)

    def get_cookies(self) -> dict[str, str]:
        """Get current session cookies.

        Returns:
            Dictionary of cookie name-value pairs.
        """
        return self._cookies.copy()

    async def clear_cookies(self) -> None:
        """Clear all session cookies."""
        self._cookies.clear()
        if self._client is not None:
            self._client.cookies.clear()

    async def delete_cookie(self, name: str) -> None:
        """Delete a specific cookie.

        Args:
            name: Cookie name to delete.
        """
        self._cookies.pop(name, None)
        if self._client is not None:
            self._client.cookies.delete(name)

    # Browser session sync

    async def sync_cookies_from_browser(self, browser_page: Any) -> None:
        """Sync cookies from a browser page to this session.

        Args:
            browser_page: A browser page instance with get_cookies method.
        """
        browser_cookies = await browser_page.get_cookies()
        for cookie in browser_cookies:
            if hasattr(cookie, "name") and hasattr(cookie, "value"):
                self._cookies[cookie.name] = cookie.value
            elif isinstance(cookie, dict):
                self._cookies[cookie["name"]] = cookie["value"]

    async def sync_cookies_to_browser(self, browser_page: Any) -> None:
        """Sync cookies from this session to a browser page.

        Args:
            browser_page: A browser page instance with set_cookies method.
        """
        from kuromi_browser.models import Cookie

        cookies_to_set = [
            Cookie(
                name=name,
                value=value,
                domain="",  # Will be set by browser
                path="/",
            )
            for name, value in self._cookies.items()
        ]
        await browser_page.set_cookies(*cookies_to_set)

    # Header management

    def set_headers(self, headers: dict[str, str]) -> None:
        """Set default session headers.

        Args:
            headers: Dictionary of header name-value pairs.
        """
        self._headers.update(headers)

    def set_header(self, name: str, value: str) -> None:
        """Set a single header.

        Args:
            name: Header name.
            value: Header value.
        """
        self._headers[name] = value

    def remove_header(self, name: str) -> None:
        """Remove a header.

        Args:
            name: Header name to remove.
        """
        self._headers.pop(name, None)

    # Fingerprint management

    async def set_fingerprint(self, fingerprint: "Fingerprint") -> None:
        """Set the fingerprint for TLS/JA3 spoofing.

        Args:
            fingerprint: Fingerprint configuration.
        """
        self._fingerprint = fingerprint
        self._headers["User-Agent"] = fingerprint.user_agent

    # Proxy management

    async def set_proxy(self, proxy: Optional[str]) -> None:
        """Set the proxy for requests.

        Args:
            proxy: Proxy URL or None to disable proxy.
        """
        self._proxy = proxy
        # Need to recreate client with new proxy
        if self._client is not None:
            await self._client.close()
            self._client = None

    # Lifecycle

    async def close(self) -> None:
        """Close the session and release resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> "Session":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """String representation of the session."""
        return f"<Session impersonate={self._impersonate!r} proxy={self._proxy!r}>"
