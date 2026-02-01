# Models Reference

Tai lieu tham khao cho cac data models trong Kuromi Browser.

## Enums

### BrowserType

Cac loai browser duoc ho tro.

```python
from kuromi_browser import BrowserType

BrowserType.CHROMIUM  # "chromium"
BrowserType.FIREFOX   # "firefox"
```

### PageMode

Cac che do hoat dong cua page.

```python
from kuromi_browser import PageMode

PageMode.BROWSER  # "browser" - Full browser via CDP
PageMode.SESSION  # "session" - HTTP session via curl_cffi
PageMode.HYBRID   # "hybrid" - Ket hop browser va session
```

## Configuration Models

### BrowserConfig

Cau hinh khoi tao browser.

```python
from kuromi_browser import BrowserConfig

config = BrowserConfig(
    browser_type=BrowserType.CHROMIUM,  # Loai browser
    headless=False,                      # Che do headless
    proxy="http://...",                  # Proxy URL hoac ProxyConfig
    user_data_dir="/path/to/profile",   # Thu muc profile
    executable_path="/path/to/chrome",  # Duong dan executable
    args=["--disable-gpu"],             # Chrome arguments
    ignore_default_args=["--enable-automation"],
    fingerprint=Fingerprint(),          # Fingerprint config
    stealth=True,                       # Bat stealth mode
    devtools=False,                     # Mo DevTools
    slow_mo=0,                          # Delay giua cac hanh dong (ms)
    timeout=30000,                      # Timeout mac dinh (ms)
    viewport_width=1920,                # Chieu rong viewport
    viewport_height=1080,               # Chieu cao viewport
    locale="en-US",                     # Locale
    timezone_id="America/New_York",     # Timezone
    geolocation={"latitude": 40.7, "longitude": -74.0},
    permissions=["geolocation"],        # Permissions
    color_scheme="light",               # Color scheme
    accept_downloads=True,              # Cho phep download
    downloads_path="/path/to/downloads",
    extra_http_headers={},              # Extra headers
    ignore_https_errors=False,          # Bo qua HTTPS errors
    java_script_enabled=True,           # Bat JavaScript
    bypass_csp=False,                   # Bypass CSP
    record_video=False,                 # Ghi video
    video_size={"width": 1280, "height": 720},
    video_dir="/path/to/videos",
)

# Lay launch args
args = config.get_launch_args()
```

### PageConfig

Cau hinh cho page.

```python
from kuromi_browser import PageConfig

config = PageConfig(
    mode=PageMode.BROWSER,       # Che do hoat dong
    timeout=30000,               # Timeout (ms)
    wait_until="load",           # Load state
    viewport={"width": 1920, "height": 1080},
    extra_http_headers={},       # Extra headers
    user_agent="...",            # Custom user agent
    bypass_csp=False,            # Bypass CSP
    java_script_enabled=True,    # JavaScript
    has_touch=False,             # Touch support
    is_mobile=False,             # Mobile mode
    device_scale_factor=1.0,     # DPI scale
    ignore_https_errors=False,   # HTTPS errors
    offline=False,               # Offline mode
)
```

### ProxyConfig

Cau hinh proxy.

```python
from kuromi_browser import ProxyConfig

# Tao tu URL
proxy = ProxyConfig.from_url("http://user:pass@proxy.com:8080")

# Tao truc tiep
proxy = ProxyConfig(
    server="http://proxy.com:8080",
    username="user",
    password="pass",
    bypass=["localhost", "*.internal.com"],
)
```

## Fingerprint Models

### Fingerprint

Fingerprint browser day du.

```python
from kuromi_browser import Fingerprint

fp = Fingerprint(
    user_agent="Mozilla/5.0 ...",
    navigator=NavigatorProperties(...),
    screen=ScreenProperties(...),
    webgl=WebGLProperties(...),
    audio=AudioProperties(...),
    canvas=CanvasProperties(...),
    timezone="America/New_York",
    timezone_offset=-300,
    locale="en-US",
    fonts=["Arial", "Times New Roman", ...],
    plugins=[...],
)

# Shortcuts
fp.platform       # navigator.platform
fp.vendor         # navigator.vendor
fp.screen_width   # screen.width
fp.screen_height  # screen.height
fp.webgl_vendor   # webgl.vendor
fp.webgl_renderer # webgl.renderer
```

### NavigatorProperties

Thuoc tinh Navigator API.

```python
from kuromi_browser import NavigatorProperties

props = NavigatorProperties(
    app_code_name="Mozilla",
    app_name="Netscape",
    app_version="5.0 (Windows NT 10.0; Win64; x64)...",
    platform="Win32",
    product="Gecko",
    product_sub="20030107",
    vendor="Google Inc.",
    vendor_sub="",
    language="en-US",
    languages=["en-US", "en"],
    hardware_concurrency=8,
    device_memory=8.0,
    max_touch_points=0,
    do_not_track=None,
    pdf_viewer_enabled=True,
    cookie_enabled=True,
    java_enabled=False,
)
```

### ScreenProperties

Thuoc tinh Screen API.

```python
from kuromi_browser import ScreenProperties

props = ScreenProperties(
    width=1920,
    height=1080,
    avail_width=1920,
    avail_height=1040,
    color_depth=24,
    pixel_depth=24,
    device_pixel_ratio=1.0,
    orientation_type="landscape-primary",
    orientation_angle=0,
)
```

### WebGLProperties

Thuoc tinh WebGL.

```python
from kuromi_browser import WebGLProperties

props = WebGLProperties(
    vendor="Google Inc. (NVIDIA)",
    renderer="ANGLE (NVIDIA, GeForce GTX 1080...)",
    unmasked_vendor=None,
    unmasked_renderer=None,
    version="WebGL 1.0 (OpenGL ES 2.0 Chromium)",
    shading_language_version="WebGL GLSL ES 1.0...",
    max_texture_size=16384,
    max_vertex_attribs=16,
    max_vertex_uniform_vectors=4096,
    max_varying_vectors=30,
    max_fragment_uniform_vectors=4096,
    aliased_line_width_range=(1.0, 1.0),
    aliased_point_size_range=(1.0, 1024.0),
)
```

### AudioProperties

Thuoc tinh AudioContext.

```python
from kuromi_browser.models import AudioProperties

props = AudioProperties(
    sample_rate=44100,
    max_channel_count=2,
    number_of_inputs=1,
    number_of_outputs=1,
    channel_count=2,
    channel_count_mode="max",
    channel_interpretation="speakers",
    state="running",
    base_latency=0.005,
    output_latency=0.0,
)
```

### CanvasProperties

Cau hinh Canvas fingerprint noise.

```python
from kuromi_browser.models import CanvasProperties

props = CanvasProperties(
    noise_enabled=True,
    noise_seed=None,      # None = random
    noise_level=0.1,      # 0.0 - 1.0
)
```

## Network Models

### Cookie

HTTP cookie.

```python
from kuromi_browser import Cookie

cookie = Cookie(
    name="session_id",
    value="abc123",
    domain="example.com",
    path="/",
    expires=1735689600.0,  # Unix timestamp
    http_only=True,
    secure=True,
    same_site="Lax",       # "Strict", "Lax", "None"
    priority="Medium",     # "Low", "Medium", "High"
    same_party=False,
    source_scheme="Secure",
    source_port=443,
)
```

### NetworkRequest

Du lieu network request.

```python
from kuromi_browser import NetworkRequest

request = NetworkRequest(
    request_id="123",
    url="https://example.com/api",
    method="POST",
    headers={"Content-Type": "application/json"},
    post_data='{"key": "value"}',
    resource_type="XHR",
    timestamp=1609459200.0,
)
```

### NetworkResponse

Du lieu network response.

```python
from kuromi_browser import NetworkResponse

response = NetworkResponse(
    request_id="123",
    url="https://example.com/api",
    status=200,
    status_text="OK",
    headers={"Content-Type": "application/json"},
    mime_type="application/json",
    remote_ip="93.184.216.34",
    remote_port=443,
    from_cache=False,
    from_service_worker=False,
    timestamp=1609459200.5,
    body=b'{"result": "success"}',
)
```

## Element Models

### ElementHandle

Reference den DOM element.

```python
from kuromi_browser.models import ElementHandle

handle = ElementHandle(
    object_id="123",
    backend_node_id=456,
    node_id=789,
    frame_id="main",
)
```

## Browser Models

### ConsoleMessage

Console message tu browser.

```python
from kuromi_browser.models import ConsoleMessage

msg = ConsoleMessage(
    type="log",           # "log", "warn", "error", "info"
    text="Hello World",
    url="https://example.com/script.js",
    line_number=42,
    column_number=10,
    timestamp=1609459200.0,
)
```

### DialogInfo

Thong tin browser dialog.

```python
from kuromi_browser.models import DialogInfo

dialog = DialogInfo(
    type="alert",         # "alert", "confirm", "prompt", "beforeunload"
    message="Are you sure?",
    default_prompt="",    # Chi cho prompt
)
```

### FrameInfo

Thong tin frame.

```python
from kuromi_browser.models import FrameInfo

frame = FrameInfo(
    frame_id="main",
    parent_frame_id=None,
    url="https://example.com",
    name="main_frame",
    security_origin="https://example.com",
    mime_type="text/html",
)
```

## Validation

Tat ca models su dung Pydantic de validation:

```python
from kuromi_browser import Fingerprint, ScreenProperties

# Validation tu dong
try:
    screen = ScreenProperties(
        width=-100,  # Invalid - phai >= 320
    )
except ValueError as e:
    print(f"Validation error: {e}")

# Validation thanh cong
screen = ScreenProperties(
    width=1920,
    height=1080,
)
```

## Serialization

Cac models ho tro JSON serialization:

```python
from kuromi_browser import Fingerprint

fp = Fingerprint()

# Chuyen sang dict
data = fp.model_dump()

# Chuyen sang JSON
json_str = fp.model_dump_json()

# Tao tu dict
fp2 = Fingerprint.model_validate(data)

# Tao tu JSON
fp3 = Fingerprint.model_validate_json(json_str)
```

## Tiep Theo

- [Page API](./page.md) - Page methods
- [Configuration](../configuration.md) - Cau hinh chi tiet
- [Stealth Guide](../stealth-guide.md) - Anti-detection
