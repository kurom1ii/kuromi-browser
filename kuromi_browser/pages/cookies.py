"""
Cookie synchronization utilities for Dual-Mode System.

Provides cookie conversion and synchronization between browser (CDP) and
HTTP session modes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, Union
from urllib.parse import urlparse

if TYPE_CHECKING:
    from kuromi_browser.models import Cookie
    from kuromi_browser.cdp import CDPSession
    from kuromi_browser.session import Session


@dataclass
class CookieData:
    """Normalized cookie data for cross-mode synchronization."""

    name: str
    value: str
    domain: str = ""
    path: str = "/"
    expires: Optional[float] = None
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"
    priority: str = "Medium"

    def is_expired(self) -> bool:
        """Check if cookie has expired."""
        if self.expires is None:
            return False
        return datetime.now(timezone.utc).timestamp() > self.expires

    def matches_domain(self, domain: str) -> bool:
        """Check if cookie matches the given domain."""
        if not self.domain:
            return True
        cookie_domain = self.domain.lstrip(".")
        target_domain = domain.lstrip(".")
        return (
            target_domain == cookie_domain
            or target_domain.endswith(f".{cookie_domain}")
        )

    def matches_path(self, path: str) -> bool:
        """Check if cookie matches the given path."""
        if self.path == "/":
            return True
        return path.startswith(self.path)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        result: dict[str, Any] = {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
            "httpOnly": self.http_only,
            "secure": self.secure,
            "sameSite": self.same_site,
        }
        if self.expires is not None:
            result["expires"] = self.expires
        return result


class CookieConverter:
    """Convert cookies between different formats."""

    @staticmethod
    def from_cdp_cookie(cdp_cookie: dict[str, Any]) -> CookieData:
        """Convert CDP cookie format to CookieData.

        Args:
            cdp_cookie: Cookie dict from CDP Network.getCookies.

        Returns:
            Normalized CookieData.
        """
        return CookieData(
            name=cdp_cookie.get("name", ""),
            value=cdp_cookie.get("value", ""),
            domain=cdp_cookie.get("domain", ""),
            path=cdp_cookie.get("path", "/"),
            expires=cdp_cookie.get("expires"),
            http_only=cdp_cookie.get("httpOnly", False),
            secure=cdp_cookie.get("secure", False),
            same_site=cdp_cookie.get("sameSite", "Lax"),
            priority=cdp_cookie.get("priority", "Medium"),
        )

    @staticmethod
    def to_cdp_cookie(cookie: CookieData) -> dict[str, Any]:
        """Convert CookieData to CDP format for Network.setCookie.

        Args:
            cookie: Normalized cookie data.

        Returns:
            CDP cookie dict.
        """
        result: dict[str, Any] = {
            "name": cookie.name,
            "value": cookie.value,
            "path": cookie.path,
            "httpOnly": cookie.http_only,
            "secure": cookie.secure,
            "sameSite": cookie.same_site,
        }
        if cookie.domain:
            result["domain"] = cookie.domain
        if cookie.expires is not None:
            result["expires"] = cookie.expires
        return result

    @staticmethod
    def from_model_cookie(model_cookie: "Cookie") -> CookieData:
        """Convert kuromi_browser.models.Cookie to CookieData.

        Args:
            model_cookie: Cookie model instance.

        Returns:
            Normalized CookieData.
        """
        return CookieData(
            name=model_cookie.name,
            value=model_cookie.value,
            domain=model_cookie.domain,
            path=model_cookie.path,
            expires=model_cookie.expires,
            http_only=model_cookie.http_only,
            secure=model_cookie.secure,
            same_site=model_cookie.same_site,
            priority=model_cookie.priority,
        )

    @staticmethod
    def to_model_cookie(cookie: CookieData) -> "Cookie":
        """Convert CookieData to kuromi_browser.models.Cookie.

        Args:
            cookie: Normalized cookie data.

        Returns:
            Cookie model instance.
        """
        from kuromi_browser.models import Cookie

        return Cookie(
            name=cookie.name,
            value=cookie.value,
            domain=cookie.domain,
            path=cookie.path,
            expires=cookie.expires,
            http_only=cookie.http_only,
            secure=cookie.secure,
            same_site=cookie.same_site,
            priority=cookie.priority,
        )

    @staticmethod
    def from_curl_cffi_cookies(cookies: dict[str, str], domain: str = "") -> list[CookieData]:
        """Convert curl_cffi simple cookie dict to CookieData list.

        curl_cffi stores cookies as simple name=value pairs, so we need to
        provide domain information separately.

        Args:
            cookies: Dict of cookie name -> value.
            domain: Domain to associate with cookies.

        Returns:
            List of CookieData.
        """
        return [
            CookieData(name=name, value=value, domain=domain)
            for name, value in cookies.items()
        ]

    @staticmethod
    def to_curl_cffi_cookies(cookies: list[CookieData]) -> dict[str, str]:
        """Convert CookieData list to curl_cffi simple format.

        Args:
            cookies: List of normalized cookies.

        Returns:
            Simple name -> value dict.
        """
        return {cookie.name: cookie.value for cookie in cookies}


@dataclass
class CookieJar:
    """Thread-safe cookie storage for cross-mode synchronization.

    Maintains a unified cookie store that can be synced between browser
    and session modes.
    """

    _cookies: dict[str, CookieData] = field(default_factory=dict)
    _domain_index: dict[str, set[str]] = field(default_factory=dict)

    def _make_key(self, name: str, domain: str, path: str) -> str:
        """Create unique key for cookie."""
        return f"{domain}|{path}|{name}"

    def set(self, cookie: CookieData) -> None:
        """Add or update a cookie.

        Args:
            cookie: Cookie to store.
        """
        if cookie.is_expired():
            return

        key = self._make_key(cookie.name, cookie.domain, cookie.path)
        self._cookies[key] = cookie

        # Update domain index
        domain = cookie.domain.lstrip(".")
        if domain not in self._domain_index:
            self._domain_index[domain] = set()
        self._domain_index[domain].add(key)

    def get(self, name: str, domain: str = "", path: str = "/") -> Optional[CookieData]:
        """Get a specific cookie.

        Args:
            name: Cookie name.
            domain: Cookie domain.
            path: Cookie path.

        Returns:
            Cookie if found, None otherwise.
        """
        key = self._make_key(name, domain, path)
        cookie = self._cookies.get(key)
        if cookie and cookie.is_expired():
            self.delete(name, domain, path)
            return None
        return cookie

    def delete(self, name: str, domain: str = "", path: str = "/") -> bool:
        """Delete a specific cookie.

        Args:
            name: Cookie name.
            domain: Cookie domain.
            path: Cookie path.

        Returns:
            True if cookie was deleted, False if not found.
        """
        key = self._make_key(name, domain, path)
        if key in self._cookies:
            del self._cookies[key]
            domain_clean = domain.lstrip(".")
            if domain_clean in self._domain_index:
                self._domain_index[domain_clean].discard(key)
            return True
        return False

    def get_for_url(self, url: str) -> list[CookieData]:
        """Get all cookies that should be sent for a URL.

        Args:
            url: Target URL.

        Returns:
            List of applicable cookies.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.split(":")[0]  # Remove port
        path = parsed.path or "/"
        is_secure = parsed.scheme == "https"

        result = []
        self._cleanup_expired()

        for cookie in self._cookies.values():
            if not cookie.matches_domain(domain):
                continue
            if not cookie.matches_path(path):
                continue
            if cookie.secure and not is_secure:
                continue
            result.append(cookie)

        return result

    def get_for_domain(self, domain: str) -> list[CookieData]:
        """Get all cookies for a domain.

        Args:
            domain: Domain to get cookies for.

        Returns:
            List of cookies for the domain.
        """
        self._cleanup_expired()
        return [
            cookie for cookie in self._cookies.values()
            if cookie.matches_domain(domain)
        ]

    def get_all(self) -> list[CookieData]:
        """Get all cookies.

        Returns:
            List of all non-expired cookies.
        """
        self._cleanup_expired()
        return list(self._cookies.values())

    def clear(self, domain: Optional[str] = None) -> None:
        """Clear cookies.

        Args:
            domain: If provided, only clear cookies for this domain.
        """
        if domain is None:
            self._cookies.clear()
            self._domain_index.clear()
        else:
            domain_clean = domain.lstrip(".")
            if domain_clean in self._domain_index:
                for key in list(self._domain_index[domain_clean]):
                    self._cookies.pop(key, None)
                del self._domain_index[domain_clean]

    def _cleanup_expired(self) -> None:
        """Remove expired cookies."""
        expired_keys = [
            key for key, cookie in self._cookies.items()
            if cookie.is_expired()
        ]
        for key in expired_keys:
            cookie = self._cookies.pop(key)
            domain = cookie.domain.lstrip(".")
            if domain in self._domain_index:
                self._domain_index[domain].discard(key)

    def update_from_list(self, cookies: list[CookieData]) -> None:
        """Update jar from a list of cookies.

        Args:
            cookies: List of cookies to add/update.
        """
        for cookie in cookies:
            self.set(cookie)

    def __len__(self) -> int:
        """Return number of cookies."""
        return len(self._cookies)

    def __contains__(self, name: str) -> bool:
        """Check if cookie name exists (any domain)."""
        return any(
            cookie.name == name for cookie in self._cookies.values()
        )


async def sync_cookies_browser_to_session(
    cdp_session: "CDPSession",
    http_session: "Session",
    urls: Optional[list[str]] = None,
) -> int:
    """Sync cookies from browser (CDP) to HTTP session.

    Args:
        cdp_session: CDP session to get cookies from.
        http_session: HTTP session to set cookies in.
        urls: Optional list of URLs to get cookies for.
            If None, gets all cookies.

    Returns:
        Number of cookies synced.
    """
    params: dict[str, Any] = {}
    if urls:
        params["urls"] = urls

    result = await cdp_session.send("Network.getCookies", params)
    cdp_cookies = result.get("cookies", [])

    # Convert and set cookies
    cookies_dict: dict[str, str] = {}
    for cdp_cookie in cdp_cookies:
        cookie = CookieConverter.from_cdp_cookie(cdp_cookie)
        if not cookie.is_expired():
            cookies_dict[cookie.name] = cookie.value

    await http_session.set_cookies(cookies_dict)
    return len(cookies_dict)


async def sync_cookies_session_to_browser(
    http_session: "Session",
    cdp_session: "CDPSession",
    domain: str,
    url: Optional[str] = None,
) -> int:
    """Sync cookies from HTTP session to browser (CDP).

    Args:
        http_session: HTTP session to get cookies from.
        cdp_session: CDP session to set cookies in.
        domain: Domain to associate with cookies.
        url: Optional URL for cookie context.

    Returns:
        Number of cookies synced.
    """
    session_cookies = http_session.get_cookies()

    count = 0
    for name, value in session_cookies.items():
        cookie_params: dict[str, Any] = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
        }
        if url:
            cookie_params["url"] = url

        await cdp_session.send("Network.setCookie", cookie_params)
        count += 1

    return count


class CookieSyncManager:
    """Manager for automatic cookie synchronization between modes.

    Tracks cookie changes and syncs them between browser and session
    modes as needed.
    """

    def __init__(
        self,
        jar: Optional[CookieJar] = None,
        auto_sync: bool = True,
    ) -> None:
        """Initialize CookieSyncManager.

        Args:
            jar: Cookie jar to use. Creates new one if None.
            auto_sync: Whether to automatically sync cookies.
        """
        self.jar = jar or CookieJar()
        self.auto_sync = auto_sync
        self._browser_dirty = False
        self._session_dirty = False

    async def sync_from_browser(
        self,
        cdp_session: "CDPSession",
        urls: Optional[list[str]] = None,
    ) -> int:
        """Sync cookies from browser to jar.

        Args:
            cdp_session: CDP session to get cookies from.
            urls: Optional URLs to get cookies for.

        Returns:
            Number of cookies synced.
        """
        params: dict[str, Any] = {}
        if urls:
            params["urls"] = urls

        result = await cdp_session.send("Network.getCookies", params)
        cdp_cookies = result.get("cookies", [])

        count = 0
        for cdp_cookie in cdp_cookies:
            cookie = CookieConverter.from_cdp_cookie(cdp_cookie)
            self.jar.set(cookie)
            count += 1

        self._browser_dirty = False
        self._session_dirty = True
        return count

    async def sync_from_session(
        self,
        http_session: "Session",
        domain: str = "",
    ) -> int:
        """Sync cookies from HTTP session to jar.

        Args:
            http_session: HTTP session to get cookies from.
            domain: Domain to associate with cookies.

        Returns:
            Number of cookies synced.
        """
        session_cookies = http_session.get_cookies()
        cookies = CookieConverter.from_curl_cffi_cookies(session_cookies, domain)
        self.jar.update_from_list(cookies)

        self._session_dirty = False
        self._browser_dirty = True
        return len(cookies)

    async def sync_to_browser(
        self,
        cdp_session: "CDPSession",
        domain: Optional[str] = None,
    ) -> int:
        """Sync cookies from jar to browser.

        Args:
            cdp_session: CDP session to set cookies in.
            domain: Optional domain to filter cookies.

        Returns:
            Number of cookies synced.
        """
        if domain:
            cookies = self.jar.get_for_domain(domain)
        else:
            cookies = self.jar.get_all()

        count = 0
        for cookie in cookies:
            cdp_cookie = CookieConverter.to_cdp_cookie(cookie)
            await cdp_session.send("Network.setCookie", cdp_cookie)
            count += 1

        self._browser_dirty = False
        return count

    async def sync_to_session(
        self,
        http_session: "Session",
        domain: Optional[str] = None,
    ) -> int:
        """Sync cookies from jar to HTTP session.

        Args:
            http_session: HTTP session to set cookies in.
            domain: Optional domain to filter cookies.

        Returns:
            Number of cookies synced.
        """
        if domain:
            cookies = self.jar.get_for_domain(domain)
        else:
            cookies = self.jar.get_all()

        cookies_dict = CookieConverter.to_curl_cffi_cookies(cookies)
        await http_session.set_cookies(cookies_dict)

        self._session_dirty = False
        return len(cookies_dict)

    async def ensure_browser_synced(
        self,
        cdp_session: "CDPSession",
        domain: Optional[str] = None,
    ) -> bool:
        """Ensure browser has latest cookies if needed.

        Args:
            cdp_session: CDP session.
            domain: Optional domain filter.

        Returns:
            True if sync was performed.
        """
        if self._browser_dirty and self.auto_sync:
            await self.sync_to_browser(cdp_session, domain)
            return True
        return False

    async def ensure_session_synced(
        self,
        http_session: "Session",
        domain: Optional[str] = None,
    ) -> bool:
        """Ensure session has latest cookies if needed.

        Args:
            http_session: HTTP session.
            domain: Optional domain filter.

        Returns:
            True if sync was performed.
        """
        if self._session_dirty and self.auto_sync:
            await self.sync_to_session(http_session, domain)
            return True
        return False
