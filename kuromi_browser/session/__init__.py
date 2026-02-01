"""
HTTP session module for kuromi-browser.

This module provides lightweight HTTP client capabilities using curl_cffi:
- Session: Async HTTP client with TLS fingerprint spoofing
- SessionPool: Connection pooling for concurrent requests
- Response: HTTP response wrapper with HTML parsing
- SessionElement: DOM-like element wrapper for lxml

Example usage:
    from kuromi_browser.session import Session

    async with Session(impersonate="chrome120") as session:
        response = await session.get("https://example.com")
        print(response.status_code)

        # Parse HTML elements
        title = response.ele("title")
        print(title.text)

        # Find multiple elements
        links = response.eles("a[href]")
        for link in links:
            print(link.attr("href"))
"""

from typing import TYPE_CHECKING, Optional

from kuromi_browser.session.client import Session
from kuromi_browser.session.element import SessionElement
from kuromi_browser.session.response import HTTPError, Response

if TYPE_CHECKING:
    from kuromi_browser.models import Fingerprint


class SessionPool:
    """Pool of HTTP sessions for concurrent requests.

    Manages multiple sessions to avoid rate limiting and
    distribute load across different fingerprints.

    Example:
        pool = SessionPool(pool_size=5)
        session = await pool.acquire()
        try:
            response = await session.get("https://example.com")
        finally:
            await pool.release(session)
    """

    def __init__(
        self,
        pool_size: int = 10,
        fingerprints: Optional[list["Fingerprint"]] = None,
        proxies: Optional[list[str]] = None,
        impersonate: str = "chrome120",
    ) -> None:
        """Initialize SessionPool.

        Args:
            pool_size: Maximum number of sessions in the pool.
            fingerprints: Optional list of fingerprints to rotate.
            proxies: Optional list of proxy URLs to rotate.
            impersonate: Default browser to impersonate.
        """
        self._pool_size = pool_size
        self._fingerprints = fingerprints or []
        self._proxies = proxies or []
        self._impersonate = impersonate
        self._sessions: list[Session] = []
        self._available: list[Session] = []
        self._fingerprint_index = 0
        self._proxy_index = 0

    def _get_next_fingerprint(self) -> Optional["Fingerprint"]:
        """Get the next fingerprint in rotation."""
        if not self._fingerprints:
            return None
        fingerprint = self._fingerprints[self._fingerprint_index]
        self._fingerprint_index = (self._fingerprint_index + 1) % len(self._fingerprints)
        return fingerprint

    def _get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in rotation."""
        if not self._proxies:
            return None
        proxy = self._proxies[self._proxy_index]
        self._proxy_index = (self._proxy_index + 1) % len(self._proxies)
        return proxy

    async def acquire(self) -> Session:
        """Get a session from the pool.

        Creates a new session if the pool is not full and no
        sessions are available.

        Returns:
            An available Session instance.
        """
        # Try to get an available session
        if self._available:
            return self._available.pop()

        # Create new session if pool not full
        if len(self._sessions) < self._pool_size:
            session = Session(
                fingerprint=self._get_next_fingerprint(),
                proxy=self._get_next_proxy(),
                impersonate=self._impersonate,
            )
            self._sessions.append(session)
            return session

        # Pool is full and no available sessions
        # In a real implementation, this would wait for a session
        # For now, create a temporary session
        return Session(
            fingerprint=self._get_next_fingerprint(),
            proxy=self._get_next_proxy(),
            impersonate=self._impersonate,
        )

    async def release(self, session: Session) -> None:
        """Return a session to the pool.

        Args:
            session: The session to return.
        """
        if session in self._sessions and session not in self._available:
            self._available.append(session)

    async def close_all(self) -> None:
        """Close all sessions in the pool."""
        for session in self._sessions:
            await session.close()
        self._sessions.clear()
        self._available.clear()

    @property
    def size(self) -> int:
        """Get the current number of sessions in the pool."""
        return len(self._sessions)

    @property
    def available_count(self) -> int:
        """Get the number of available sessions."""
        return len(self._available)

    async def __aenter__(self) -> "SessionPool":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close_all()


__all__ = [
    "Session",
    "SessionPool",
    "Response",
    "SessionElement",
    "HTTPError",
]
