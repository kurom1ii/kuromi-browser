"""
HTTP session module for kuromi-browser.

This module provides lightweight HTTP client capabilities using curl_cffi:
- Session: Async HTTP client with TLS fingerprint spoofing
- SessionPool: Connection pooling for concurrent requests
- Request/Response wrappers
"""

from typing import TYPE_CHECKING, Any, Optional, Union

from kuromi_browser.interfaces import BaseSession

if TYPE_CHECKING:
    from kuromi_browser.models import Fingerprint, NetworkResponse


class Session(BaseSession):
    """Async HTTP session with TLS fingerprint spoofing.

    Uses curl_cffi to impersonate browser TLS/JA3 fingerprints,
    making HTTP requests appear to come from real browsers.
    """

    def __init__(
        self,
        fingerprint: Optional["Fingerprint"] = None,
        proxy: Optional[str] = None,
        impersonate: str = "chrome120",
        timeout: float = 30.0,
    ) -> None:
        self._fingerprint = fingerprint
        self._proxy = proxy
        self._impersonate = impersonate
        self._timeout = timeout
        self._cookies: dict[str, str] = {}
        self._headers: dict[str, str] = {}
        self._client: Any = None

    @property
    def cookies(self) -> dict[str, str]:
        return self._cookies.copy()

    async def _ensure_client(self) -> None:
        """Initialize the curl_cffi client if needed."""
        if self._client is None:
            from curl_cffi.requests import AsyncSession

            self._client = AsyncSession(
                impersonate=self._impersonate,
                proxy=self._proxy,
                timeout=self._timeout,
            )

    async def get(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def post(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def put(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def patch(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def head(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def options(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        raise NotImplementedError

    async def set_fingerprint(self, fingerprint: "Fingerprint") -> None:
        """Set the fingerprint for TLS/JA3 spoofing."""
        self._fingerprint = fingerprint
        self._headers["User-Agent"] = fingerprint.user_agent

    async def set_proxy(self, proxy: str) -> None:
        """Set the proxy for requests."""
        self._proxy = proxy
        self._client = None

    async def set_cookies(self, cookies: dict[str, str]) -> None:
        """Set session cookies."""
        self._cookies.update(cookies)

    async def clear_cookies(self) -> None:
        """Clear all session cookies."""
        self._cookies.clear()

    async def close(self) -> None:
        """Close the session."""
        if self._client is not None:
            await self._client.close()
            self._client = None


class SessionPool:
    """Pool of HTTP sessions for concurrent requests.

    Manages multiple sessions to avoid rate limiting and
    distribute load across different fingerprints.
    """

    def __init__(
        self,
        pool_size: int = 10,
        fingerprints: Optional[list["Fingerprint"]] = None,
        proxies: Optional[list[str]] = None,
    ) -> None:
        self._pool_size = pool_size
        self._fingerprints = fingerprints or []
        self._proxies = proxies or []
        self._sessions: list[Session] = []

    async def acquire(self) -> Session:
        """Get a session from the pool."""
        raise NotImplementedError

    async def release(self, session: Session) -> None:
        """Return a session to the pool."""
        raise NotImplementedError

    async def close_all(self) -> None:
        """Close all sessions in the pool."""
        for session in self._sessions:
            await session.close()
        self._sessions.clear()


__all__ = [
    "Session",
    "SessionPool",
]
