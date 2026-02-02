"""
TLS fingerprint impersonation using curl_cffi.

Wraps curl_cffi to provide TLS fingerprint impersonation
that matches real browser TLS signatures.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

try:
    from curl_cffi.requests import Session as CurlSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    CurlSession = None


class BrowserImpersonation(str, Enum):
    """Browser impersonation targets supported by curl_cffi."""

    # Chrome versions
    CHROME_99 = "chrome99"
    CHROME_100 = "chrome100"
    CHROME_101 = "chrome101"
    CHROME_104 = "chrome104"
    CHROME_107 = "chrome107"
    CHROME_110 = "chrome110"
    CHROME_116 = "chrome116"
    CHROME_119 = "chrome119"
    CHROME_120 = "chrome120"
    CHROME_123 = "chrome123"
    CHROME_124 = "chrome124"

    # Chrome Android
    CHROME_99_ANDROID = "chrome99_android"

    # Edge versions
    EDGE_99 = "edge99"
    EDGE_101 = "edge101"

    # Safari versions
    SAFARI_15_3 = "safari15_3"
    SAFARI_15_5 = "safari15_5"
    SAFARI_17_0 = "safari17_0"

    # Safari iOS
    SAFARI_IOS_15_5 = "safari_ios15_5"
    SAFARI_IOS_15_6 = "safari_ios15_6"
    SAFARI_IOS_16_0 = "safari_ios16_0"

    # Firefox
    FIREFOX_102 = "firefox102"
    FIREFOX_109 = "firefox109"
    FIREFOX_117 = "firefox117"


# Map browser types to available impersonations
BROWSER_IMPERSONATIONS = {
    "chrome": [
        BrowserImpersonation.CHROME_120,
        BrowserImpersonation.CHROME_123,
        BrowserImpersonation.CHROME_124,
        BrowserImpersonation.CHROME_119,
        BrowserImpersonation.CHROME_116,
    ],
    "firefox": [
        BrowserImpersonation.FIREFOX_117,
        BrowserImpersonation.FIREFOX_109,
        BrowserImpersonation.FIREFOX_102,
    ],
    "safari": [
        BrowserImpersonation.SAFARI_17_0,
        BrowserImpersonation.SAFARI_15_5,
        BrowserImpersonation.SAFARI_15_3,
    ],
    "edge": [
        BrowserImpersonation.EDGE_101,
        BrowserImpersonation.EDGE_99,
    ],
}


@dataclass
class TLSConfig:
    """Configuration for TLS client."""

    impersonate: Union[str, BrowserImpersonation] = BrowserImpersonation.CHROME_120
    timeout: float = 30.0
    verify: bool = True
    proxy: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    follow_redirects: bool = True
    max_redirects: int = 30

    def get_impersonate_string(self) -> str:
        """Get the impersonation string for curl_cffi."""
        if isinstance(self.impersonate, BrowserImpersonation):
            return self.impersonate.value
        return self.impersonate


class TLSClient:
    """TLS client with browser fingerprint impersonation.

    Wraps curl_cffi to make HTTP requests with TLS fingerprints
    that match real browsers, bypassing TLS fingerprinting detection.

    Example:
        client = TLSClient(browser="chrome")
        response = client.get("https://example.com")
        print(response.text)

        # Or with async
        async with TLSClient(browser="chrome").async_session() as session:
            response = await session.get("https://example.com")
    """

    def __init__(
        self,
        browser: str = "chrome",
        config: Optional[TLSConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize TLS client.

        Args:
            browser: Browser to impersonate ("chrome", "firefox", "safari", "edge")
            config: TLS configuration
            **kwargs: Additional arguments passed to TLSConfig
        """
        if not CURL_CFFI_AVAILABLE:
            raise ImportError(
                "curl_cffi is required for TLS impersonation. "
                "Install it with: pip install curl_cffi"
            )

        self._browser = browser.lower()

        if config:
            self._config = config
        else:
            # Select a random impersonation for the browser type
            impersonations = BROWSER_IMPERSONATIONS.get(
                self._browser,
                BROWSER_IMPERSONATIONS["chrome"],
            )
            impersonate = random.choice(impersonations)

            self._config = TLSConfig(
                impersonate=impersonate,
                **kwargs,
            )

        self._session: Optional[CurlSession] = None

    @property
    def config(self) -> TLSConfig:
        """Get the current configuration."""
        return self._config

    def _get_session(self) -> CurlSession:
        """Get or create a curl_cffi session."""
        if self._session is None:
            self._session = CurlSession(
                impersonate=self._config.get_impersonate_string(),
                verify=self._config.verify,
                timeout=self._config.timeout,
                proxies={"http": self._config.proxy, "https": self._config.proxy}
                if self._config.proxy
                else None,
                allow_redirects=self._config.follow_redirects,
                max_redirects=self._config.max_redirects,
            )

            # Set default headers
            if self._config.headers:
                self._session.headers.update(self._config.headers)

            # Set cookies
            if self._config.cookies:
                for name, value in self._config.cookies.items():
                    self._session.cookies.set(name, value)

        return self._session

    def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a GET request.

        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments for the request

        Returns:
            Response object
        """
        session = self._get_session()
        return session.get(url, params=params, headers=headers, **kwargs)

    def post(
        self,
        url: str,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a POST request.

        Args:
            url: URL to request
            data: Form data or raw body
            json: JSON data (will set Content-Type header)
            headers: Additional headers
            **kwargs: Additional arguments for the request

        Returns:
            Response object
        """
        session = self._get_session()
        return session.post(url, data=data, json=json, headers=headers, **kwargs)

    def put(
        self,
        url: str,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a PUT request."""
        session = self._get_session()
        return session.put(url, data=data, json=json, headers=headers, **kwargs)

    def patch(
        self,
        url: str,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a PATCH request."""
        session = self._get_session()
        return session.patch(url, data=data, json=json, headers=headers, **kwargs)

    def delete(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a DELETE request."""
        session = self._get_session()
        return session.delete(url, headers=headers, **kwargs)

    def head(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a HEAD request."""
        session = self._get_session()
        return session.head(url, headers=headers, **kwargs)

    def options(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make an OPTIONS request."""
        session = self._get_session()
        return session.options(url, headers=headers, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Make a request with any HTTP method.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional arguments for the request

        Returns:
            Response object
        """
        session = self._get_session()
        return session.request(method, url, **kwargs)

    def close(self) -> None:
        """Close the session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> "TLSClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> "TLSClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        self.close()

    # Async methods
    async def async_get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make an async GET request."""
        session = self._get_session()
        return await session.get(url, params=params, headers=headers, **kwargs)

    async def async_post(
        self,
        url: str,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Make an async POST request."""
        session = self._get_session()
        return await session.post(url, data=data, json=json, headers=headers, **kwargs)

    async def async_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Make an async request with any HTTP method."""
        session = self._get_session()
        return await session.request(method, url, **kwargs)


def create_tls_client(
    browser: str = "chrome",
    proxy: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
) -> TLSClient:
    """Create a TLS client with the specified configuration.

    This is a convenience function for creating a TLSClient.

    Args:
        browser: Browser to impersonate
        proxy: Proxy URL (http://host:port or http://user:pass@host:port)
        headers: Default headers
        timeout: Request timeout in seconds

    Returns:
        Configured TLSClient instance
    """
    config = TLSConfig(
        proxy=proxy,
        headers=headers or {},
        timeout=timeout,
    )

    return TLSClient(browser=browser, config=config)
