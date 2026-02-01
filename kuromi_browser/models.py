"""
Core data models for kuromi-browser.

This module defines the fundamental data structures used throughout the library,
including browser configuration, fingerprint profiles, and page modes.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BrowserType(str, Enum):
    """Supported browser engines."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"


class PageMode(str, Enum):
    """Page operation modes.

    - BROWSER: Full browser automation via CDP
    - SESSION: Lightweight HTTP session with curl_cffi
    - HYBRID: Combines browser and session for optimal performance
    """

    BROWSER = "browser"
    SESSION = "session"
    HYBRID = "hybrid"


class NavigatorProperties(BaseModel):
    """Navigator API properties for fingerprint spoofing."""

    app_code_name: str = "Mozilla"
    app_name: str = "Netscape"
    app_version: str = Field(default="")
    platform: str = Field(default="Linux x86_64")
    product: str = "Gecko"
    product_sub: str = "20030107"
    vendor: str = Field(default="Google Inc.")
    vendor_sub: str = ""
    language: str = "en-US"
    languages: list[str] = Field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = Field(default=8, ge=1, le=64)
    device_memory: Optional[float] = Field(default=8.0, ge=0.25, le=512)
    max_touch_points: int = Field(default=0, ge=0, le=10)
    do_not_track: Optional[str] = None
    pdf_viewer_enabled: bool = True
    cookie_enabled: bool = True
    java_enabled: bool = False


class ScreenProperties(BaseModel):
    """Screen API properties for fingerprint spoofing."""

    width: int = Field(default=1920, ge=320)
    height: int = Field(default=1080, ge=240)
    avail_width: int = Field(default=1920, ge=320)
    avail_height: int = Field(default=1040, ge=200)
    color_depth: int = Field(default=24, ge=1, le=48)
    pixel_depth: int = Field(default=24, ge=1, le=48)
    device_pixel_ratio: float = Field(default=1.0, ge=0.5, le=4.0)
    orientation_type: str = "landscape-primary"
    orientation_angle: int = 0


class WebGLProperties(BaseModel):
    """WebGL fingerprint properties."""

    vendor: Optional[str] = "Google Inc. (NVIDIA)"
    renderer: Optional[str] = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)"
    unmasked_vendor: Optional[str] = None
    unmasked_renderer: Optional[str] = None
    version: str = "WebGL 1.0 (OpenGL ES 2.0 Chromium)"
    shading_language_version: str = "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)"
    max_texture_size: int = 16384
    max_vertex_attribs: int = 16
    max_vertex_uniform_vectors: int = 4096
    max_varying_vectors: int = 30
    max_fragment_uniform_vectors: int = 4096
    aliased_line_width_range: tuple[float, float] = (1.0, 1.0)
    aliased_point_size_range: tuple[float, float] = (1.0, 1024.0)


class AudioProperties(BaseModel):
    """AudioContext fingerprint properties."""

    sample_rate: int = 44100
    max_channel_count: int = 2
    number_of_inputs: int = 1
    number_of_outputs: int = 1
    channel_count: int = 2
    channel_count_mode: str = "max"
    channel_interpretation: str = "speakers"
    state: str = "running"
    base_latency: float = 0.005
    output_latency: float = 0.0


class CanvasProperties(BaseModel):
    """Canvas fingerprint noise settings."""

    noise_enabled: bool = True
    noise_seed: Optional[int] = None
    noise_level: float = Field(default=0.1, ge=0.0, le=1.0)


class Fingerprint(BaseModel):
    """Complete browser fingerprint profile.

    Contains all the properties needed to spoof a consistent browser identity.
    """

    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    navigator: NavigatorProperties = Field(default_factory=NavigatorProperties)
    screen: ScreenProperties = Field(default_factory=ScreenProperties)
    webgl: WebGLProperties = Field(default_factory=WebGLProperties)
    audio: AudioProperties = Field(default_factory=AudioProperties)
    canvas: CanvasProperties = Field(default_factory=CanvasProperties)

    timezone: str = "America/New_York"
    timezone_offset: int = -300
    locale: str = "en-US"

    fonts: list[str] = Field(
        default_factory=lambda: [
            "Arial",
            "Arial Black",
            "Comic Sans MS",
            "Courier New",
            "Georgia",
            "Impact",
            "Times New Roman",
            "Trebuchet MS",
            "Verdana",
        ]
    )

    plugins: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {"name": "Chrome PDF Viewer", "filename": "internal-pdf-viewer"},
            {"name": "Chromium PDF Viewer", "filename": "internal-pdf-viewer"},
            {"name": "Microsoft Edge PDF Viewer", "filename": "internal-pdf-viewer"},
            {"name": "PDF Viewer", "filename": "internal-pdf-viewer"},
            {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer"},
        ]
    )

    @property
    def platform(self) -> str:
        """Shortcut to navigator platform."""
        return self.navigator.platform

    @property
    def vendor(self) -> str:
        """Shortcut to navigator vendor."""
        return self.navigator.vendor

    @property
    def screen_width(self) -> int:
        """Shortcut to screen width."""
        return self.screen.width

    @property
    def screen_height(self) -> int:
        """Shortcut to screen height."""
        return self.screen.height

    @property
    def webgl_vendor(self) -> Optional[str]:
        """Shortcut to WebGL vendor."""
        return self.webgl.vendor

    @property
    def webgl_renderer(self) -> Optional[str]:
        """Shortcut to WebGL renderer."""
        return self.webgl.renderer


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    bypass: list[str] = Field(default_factory=list)

    @classmethod
    def from_url(cls, url: str) -> "ProxyConfig":
        """Parse proxy from URL format (http://user:pass@host:port)."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        server = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            server += f":{parsed.port}"
        return cls(
            server=server,
            username=parsed.username,
            password=parsed.password,
        )


class BrowserConfig(BaseModel):
    """Browser launch configuration."""

    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = False
    proxy: Optional[str | ProxyConfig] = None
    user_data_dir: Optional[str] = None
    executable_path: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    ignore_default_args: list[str] = Field(default_factory=list)
    fingerprint: Optional[Fingerprint] = None
    stealth: bool = True
    devtools: bool = False
    slow_mo: int = 0
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "en-US"
    timezone_id: Optional[str] = None
    geolocation: Optional[dict[str, float]] = None
    permissions: list[str] = Field(default_factory=list)
    color_scheme: Optional[str] = None
    reduced_motion: Optional[str] = None
    forced_colors: Optional[str] = None
    accept_downloads: bool = True
    downloads_path: Optional[str] = None
    extra_http_headers: dict[str, str] = Field(default_factory=dict)
    offline: bool = False
    http_credentials: Optional[dict[str, str]] = None
    ignore_https_errors: bool = False
    java_script_enabled: bool = True
    bypass_csp: bool = False
    record_video: bool = False
    video_size: Optional[dict[str, int]] = None
    video_dir: Optional[str] = None

    def get_launch_args(self) -> list[str]:
        """Get combined launch arguments."""
        args = list(self.args)
        if self.headless:
            args.append("--headless=new")
        if self.proxy:
            proxy_server = (
                self.proxy.server if isinstance(self.proxy, ProxyConfig) else self.proxy
            )
            args.append(f"--proxy-server={proxy_server}")
        return args


class PageConfig(BaseModel):
    """Page-specific configuration."""

    mode: PageMode = PageMode.BROWSER
    timeout: int = 30000
    wait_until: str = "load"
    viewport: Optional[dict[str, int]] = None
    extra_http_headers: dict[str, str] = Field(default_factory=dict)
    user_agent: Optional[str] = None
    bypass_csp: bool = False
    java_script_enabled: bool = True
    has_touch: bool = False
    is_mobile: bool = False
    device_scale_factor: float = 1.0
    ignore_https_errors: bool = False
    offline: bool = False


class ElementHandle(BaseModel):
    """Reference to a DOM element."""

    object_id: str
    backend_node_id: Optional[int] = None
    node_id: Optional[int] = None
    frame_id: Optional[str] = None

    class Config:
        frozen = True


class Cookie(BaseModel):
    """HTTP cookie representation."""

    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"
    priority: str = "Medium"
    same_party: bool = False
    source_scheme: str = "Secure"
    source_port: int = 443


class NetworkRequest(BaseModel):
    """Network request data."""

    request_id: str
    url: str
    method: str
    headers: dict[str, str]
    post_data: Optional[str] = None
    resource_type: str = "Other"
    timestamp: float = 0.0


class NetworkResponse(BaseModel):
    """Network response data."""

    request_id: str
    url: str
    status: int
    status_text: str
    headers: dict[str, str]
    mime_type: str = ""
    remote_ip: Optional[str] = None
    remote_port: Optional[int] = None
    from_cache: bool = False
    from_service_worker: bool = False
    timestamp: float = 0.0
    body: Optional[bytes] = None


class ConsoleMessage(BaseModel):
    """Browser console message."""

    type: str
    text: str
    url: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    timestamp: float = 0.0


class DialogInfo(BaseModel):
    """Browser dialog information."""

    type: str
    message: str
    default_prompt: Optional[str] = None


class FrameInfo(BaseModel):
    """Frame information."""

    frame_id: str
    parent_frame_id: Optional[str] = None
    url: str
    name: Optional[str] = None
    security_origin: Optional[str] = None
    mime_type: str = "text/html"
