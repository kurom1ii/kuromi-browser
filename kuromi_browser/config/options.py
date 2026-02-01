"""
Configuration options classes for kuromi-browser.

This module provides strongly-typed option classes for browser, session,
and page configuration with validation and type checking.
"""

from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .defaults import (
    DEFAULT_BROWSER_TYPE,
    DEFAULT_BYPASS_CSP,
    DEFAULT_CHROMIUM_ARGS,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_DEVICE_SCALE_FACTOR,
    DEFAULT_DEVTOOLS,
    DEFAULT_FOLLOW_REDIRECTS,
    DEFAULT_HAS_TOUCH,
    DEFAULT_HEADLESS,
    DEFAULT_HEADERS,
    DEFAULT_HTTP2,
    DEFAULT_IGNORE_ARGS,
    DEFAULT_IGNORE_HTTPS_ERRORS,
    DEFAULT_IS_MOBILE,
    DEFAULT_JAVASCRIPT_ENABLED,
    DEFAULT_KEEPALIVE_EXPIRY,
    DEFAULT_LOCALE,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_OFFLINE,
    DEFAULT_PAGE_MODE,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SESSION_TIMEOUT,
    DEFAULT_SLOW_MO,
    DEFAULT_STEALTH,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    DEFAULT_VERIFY_SSL,
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    DEFAULT_WAIT_UNTIL,
)


class BrowserType(str, Enum):
    """Supported browser engines."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"


class PageMode(str, Enum):
    """Page operation modes."""

    BROWSER = "browser"
    SESSION = "session"
    HYBRID = "hybrid"


class ProxyType(str, Enum):
    """Supported proxy types."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ColorScheme(str, Enum):
    """Color scheme preferences."""

    LIGHT = "light"
    DARK = "dark"
    NO_PREFERENCE = "no-preference"


class ReducedMotion(str, Enum):
    """Reduced motion preferences."""

    REDUCE = "reduce"
    NO_PREFERENCE = "no-preference"


class ForcedColors(str, Enum):
    """Forced colors preferences."""

    ACTIVE = "active"
    NONE = "none"


class WaitUntil(str, Enum):
    """Page load wait conditions."""

    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"
    COMMIT = "commit"


class ProxyOptions(BaseModel):
    """Proxy configuration options."""

    server: str = Field(..., description="Proxy server URL")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")
    bypass: list[str] = Field(default_factory=list, description="Hosts to bypass")
    proxy_type: ProxyType = Field(ProxyType.HTTP, description="Proxy protocol type")

    @classmethod
    def from_url(cls, url: str) -> "ProxyOptions":
        """Parse proxy from URL format.

        Supported formats:
        - http://host:port
        - http://user:pass@host:port
        - socks5://host:port
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme in ("socks5", "socks5h"):
            proxy_type = ProxyType.SOCKS5
        elif scheme == "socks4":
            proxy_type = ProxyType.SOCKS4
        elif scheme == "https":
            proxy_type = ProxyType.HTTPS
        else:
            proxy_type = ProxyType.HTTP

        server = f"{scheme}://{parsed.hostname}"
        if parsed.port:
            server += f":{parsed.port}"

        return cls(
            server=server,
            username=parsed.username,
            password=parsed.password,
            proxy_type=proxy_type,
        )

    def to_url(self, include_auth: bool = True) -> str:
        """Convert proxy options to URL format."""
        from urllib.parse import urlparse

        parsed = urlparse(self.server)
        scheme = parsed.scheme or self.proxy_type.value
        host = parsed.hostname or ""
        port = parsed.port

        if include_auth and self.username:
            auth = self.username
            if self.password:
                auth += f":{self.password}"
            auth += "@"
        else:
            auth = ""

        url = f"{scheme}://{auth}{host}"
        if port:
            url += f":{port}"

        return url


class ViewportOptions(BaseModel):
    """Viewport configuration options."""

    width: int = Field(DEFAULT_VIEWPORT_WIDTH, ge=320, description="Viewport width")
    height: int = Field(DEFAULT_VIEWPORT_HEIGHT, ge=240, description="Viewport height")


class GeolocationOptions(BaseModel):
    """Geolocation configuration options."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    accuracy: Optional[float] = Field(None, ge=0, description="Accuracy in meters")


class HttpCredentials(BaseModel):
    """HTTP authentication credentials."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class VideoOptions(BaseModel):
    """Video recording options."""

    dir: str = Field(..., description="Directory for video files")
    size: Optional[ViewportOptions] = Field(None, description="Video size")


class RetryOptions(BaseModel):
    """Request retry options."""

    count: int = Field(DEFAULT_RETRY_COUNT, ge=0, description="Number of retries")
    backoff: float = Field(DEFAULT_RETRY_BACKOFF, ge=0, description="Backoff multiplier")
    statuses: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP statuses to retry",
    )
    exceptions: list[str] = Field(
        default_factory=lambda: ["ConnectionError", "TimeoutError"],
        description="Exception types to retry",
    )


class BrowserOptions(BaseModel):
    """Browser launch configuration options.

    This class provides all options for configuring browser launch behavior,
    including headless mode, proxy settings, viewport, and stealth features.
    """

    browser_type: BrowserType = Field(
        BrowserType.CHROMIUM, description="Browser engine type"
    )
    headless: bool = Field(DEFAULT_HEADLESS, description="Run in headless mode")
    proxy: Optional[Union[str, ProxyOptions]] = Field(
        None, description="Proxy configuration"
    )
    user_data_dir: Optional[str] = Field(
        None, description="User data directory path"
    )
    executable_path: Optional[str] = Field(
        None, description="Browser executable path"
    )
    args: list[str] = Field(
        default_factory=lambda: DEFAULT_CHROMIUM_ARGS.copy(),
        description="Additional browser arguments",
    )
    ignore_default_args: list[str] = Field(
        default_factory=lambda: DEFAULT_IGNORE_ARGS.copy(),
        description="Default arguments to ignore",
    )
    stealth: bool = Field(DEFAULT_STEALTH, description="Enable stealth mode")
    devtools: bool = Field(DEFAULT_DEVTOOLS, description="Open DevTools")
    slow_mo: int = Field(
        DEFAULT_SLOW_MO, ge=0, description="Slow down operations by ms"
    )
    timeout: int = Field(
        DEFAULT_TIMEOUT, ge=0, description="Default timeout in ms"
    )
    viewport: Optional[ViewportOptions] = Field(
        None, description="Viewport size"
    )
    locale: str = Field(DEFAULT_LOCALE, description="Browser locale")
    timezone_id: Optional[str] = Field(None, description="Timezone identifier")
    geolocation: Optional[GeolocationOptions] = Field(
        None, description="Geolocation override"
    )
    permissions: list[str] = Field(
        default_factory=list, description="Granted permissions"
    )
    color_scheme: Optional[ColorScheme] = Field(
        None, description="Preferred color scheme"
    )
    reduced_motion: Optional[ReducedMotion] = Field(
        None, description="Reduced motion preference"
    )
    forced_colors: Optional[ForcedColors] = Field(
        None, description="Forced colors mode"
    )
    accept_downloads: bool = Field(True, description="Accept downloads")
    downloads_path: Optional[str] = Field(
        None, description="Downloads directory"
    )
    extra_http_headers: dict[str, str] = Field(
        default_factory=dict, description="Extra HTTP headers"
    )
    offline: bool = Field(DEFAULT_OFFLINE, description="Emulate offline mode")
    http_credentials: Optional[HttpCredentials] = Field(
        None, description="HTTP authentication credentials"
    )
    ignore_https_errors: bool = Field(
        DEFAULT_IGNORE_HTTPS_ERRORS, description="Ignore HTTPS errors"
    )
    java_script_enabled: bool = Field(
        DEFAULT_JAVASCRIPT_ENABLED, description="Enable JavaScript"
    )
    bypass_csp: bool = Field(
        DEFAULT_BYPASS_CSP, description="Bypass Content Security Policy"
    )
    record_video: Optional[VideoOptions] = Field(
        None, description="Video recording options"
    )

    @field_validator("proxy", mode="before")
    @classmethod
    def parse_proxy(cls, v: Any) -> Optional[Union[str, ProxyOptions]]:
        """Parse proxy from string or dict."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return ProxyOptions(**v)
        return v

    @model_validator(mode="after")
    def set_default_viewport(self) -> "BrowserOptions":
        """Set default viewport if not specified."""
        if self.viewport is None:
            self.viewport = ViewportOptions()
        return self

    def get_proxy_options(self) -> Optional[ProxyOptions]:
        """Get proxy as ProxyOptions object."""
        if self.proxy is None:
            return None
        if isinstance(self.proxy, str):
            return ProxyOptions.from_url(self.proxy)
        return self.proxy

    def get_launch_args(self) -> list[str]:
        """Get combined launch arguments."""
        args = list(self.args)
        if self.headless:
            args.append("--headless=new")
        proxy_opts = self.get_proxy_options()
        if proxy_opts:
            args.append(f"--proxy-server={proxy_opts.server}")
        return args

    def merge(self, other: "BrowserOptions") -> "BrowserOptions":
        """Merge with another BrowserOptions, other takes precedence."""
        data = self.model_dump(exclude_none=True)
        other_data = other.model_dump(exclude_none=True)
        data.update(other_data)
        return BrowserOptions(**data)


class SessionOptions(BaseModel):
    """HTTP session configuration options.

    This class provides options for configuring HTTP sessions with curl_cffi,
    including timeouts, SSL settings, and connection pooling.
    """

    timeout: float = Field(
        DEFAULT_SESSION_TIMEOUT, ge=0, description="Default request timeout"
    )
    connect_timeout: float = Field(
        DEFAULT_CONNECT_TIMEOUT, ge=0, description="Connection timeout"
    )
    read_timeout: float = Field(
        DEFAULT_READ_TIMEOUT, ge=0, description="Read timeout"
    )
    max_redirects: int = Field(
        DEFAULT_MAX_REDIRECTS, ge=0, description="Maximum redirects"
    )
    verify_ssl: bool = Field(DEFAULT_VERIFY_SSL, description="Verify SSL certificates")
    http2: bool = Field(DEFAULT_HTTP2, description="Enable HTTP/2")
    follow_redirects: bool = Field(
        DEFAULT_FOLLOW_REDIRECTS, description="Follow redirects"
    )
    max_connections: int = Field(
        DEFAULT_MAX_CONNECTIONS, ge=1, description="Max connections"
    )
    max_keepalive_connections: int = Field(
        DEFAULT_MAX_KEEPALIVE_CONNECTIONS, ge=0, description="Max keepalive connections"
    )
    keepalive_expiry: float = Field(
        DEFAULT_KEEPALIVE_EXPIRY, ge=0, description="Keepalive expiry seconds"
    )
    retry: Optional[RetryOptions] = Field(
        None, description="Retry configuration"
    )
    proxy: Optional[Union[str, ProxyOptions]] = Field(
        None, description="Proxy configuration"
    )
    headers: dict[str, str] = Field(
        default_factory=lambda: DEFAULT_HEADERS.copy(),
        description="Default request headers",
    )
    user_agent: str = Field(DEFAULT_USER_AGENT, description="User agent string")
    cookies: dict[str, str] = Field(
        default_factory=dict, description="Default cookies"
    )
    impersonate: Optional[str] = Field(
        None, description="Browser to impersonate (curl_cffi)"
    )
    ja3_string: Optional[str] = Field(None, description="Custom JA3 fingerprint")
    akamai_string: Optional[str] = Field(
        None, description="Custom Akamai fingerprint"
    )

    @field_validator("proxy", mode="before")
    @classmethod
    def parse_proxy(cls, v: Any) -> Optional[Union[str, ProxyOptions]]:
        """Parse proxy from string or dict."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return ProxyOptions(**v)
        return v

    @model_validator(mode="after")
    def set_default_retry(self) -> "SessionOptions":
        """Set default retry options if not specified."""
        if self.retry is None:
            self.retry = RetryOptions()
        return self

    def get_proxy_dict(self) -> Optional[dict[str, str]]:
        """Get proxy as curl_cffi format."""
        if self.proxy is None:
            return None
        if isinstance(self.proxy, str):
            return {"http": self.proxy, "https": self.proxy}
        return {"http": self.proxy.to_url(), "https": self.proxy.to_url()}

    def merge(self, other: "SessionOptions") -> "SessionOptions":
        """Merge with another SessionOptions, other takes precedence."""
        data = self.model_dump(exclude_none=True)
        other_data = other.model_dump(exclude_none=True)
        # Merge headers specially
        if "headers" in other_data:
            data["headers"] = {**data.get("headers", {}), **other_data["headers"]}
            del other_data["headers"]
        data.update(other_data)
        return SessionOptions(**data)


class PageOptions(BaseModel):
    """Page-specific configuration options.

    This class provides options for configuring individual page behavior,
    including mode, timeouts, and viewport settings.
    """

    mode: PageMode = Field(PageMode.BROWSER, description="Page operation mode")
    timeout: int = Field(DEFAULT_TIMEOUT, ge=0, description="Default timeout")
    wait_until: WaitUntil = Field(
        WaitUntil.LOAD, description="Page load wait condition"
    )
    viewport: Optional[ViewportOptions] = Field(
        None, description="Page viewport size"
    )
    extra_http_headers: dict[str, str] = Field(
        default_factory=dict, description="Extra HTTP headers"
    )
    user_agent: Optional[str] = Field(None, description="User agent override")
    bypass_csp: bool = Field(
        DEFAULT_BYPASS_CSP, description="Bypass Content Security Policy"
    )
    java_script_enabled: bool = Field(
        DEFAULT_JAVASCRIPT_ENABLED, description="Enable JavaScript"
    )
    has_touch: bool = Field(DEFAULT_HAS_TOUCH, description="Enable touch events")
    is_mobile: bool = Field(DEFAULT_IS_MOBILE, description="Emulate mobile device")
    device_scale_factor: float = Field(
        DEFAULT_DEVICE_SCALE_FACTOR,
        ge=0.5,
        le=4.0,
        description="Device scale factor",
    )
    ignore_https_errors: bool = Field(
        DEFAULT_IGNORE_HTTPS_ERRORS, description="Ignore HTTPS errors"
    )
    offline: bool = Field(DEFAULT_OFFLINE, description="Emulate offline mode")

    def merge(self, other: "PageOptions") -> "PageOptions":
        """Merge with another PageOptions, other takes precedence."""
        data = self.model_dump(exclude_none=True)
        other_data = other.model_dump(exclude_none=True)
        data.update(other_data)
        return PageOptions(**data)


class KuromiConfig(BaseModel):
    """Main configuration class combining all options.

    This class provides a unified configuration interface that combines
    browser, session, and page options with support for profiles and presets.
    """

    browser: BrowserOptions = Field(
        default_factory=BrowserOptions, description="Browser options"
    )
    session: SessionOptions = Field(
        default_factory=SessionOptions, description="Session options"
    )
    page: PageOptions = Field(
        default_factory=PageOptions, description="Page options"
    )
    profile: Optional[str] = Field(
        None, description="Configuration profile name"
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KuromiConfig":
        """Create configuration from dictionary."""
        return cls(**data)

    def merge(self, other: "KuromiConfig") -> "KuromiConfig":
        """Merge with another KuromiConfig, other takes precedence."""
        return KuromiConfig(
            browser=self.browser.merge(other.browser),
            session=self.session.merge(other.session),
            page=self.page.merge(other.page),
            profile=other.profile or self.profile,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(exclude_none=True)
