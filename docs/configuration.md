# Cau Hinh

Huong dan cau hinh Browser va Page trong Kuromi Browser.

## Browser Configuration

### BrowserConfig

```python
from kuromi_browser import BrowserConfig, BrowserType

config = BrowserConfig(
    # Loai browser (chromium hoac firefox)
    browser_type=BrowserType.CHROMIUM,

    # Che do headless
    headless=False,

    # Proxy
    proxy="http://user:pass@host:port",

    # Thu muc profile
    user_data_dir="/path/to/profile",

    # Duong dan browser executable
    executable_path="/usr/bin/google-chrome",

    # Chrome arguments
    args=["--disable-gpu", "--no-sandbox"],

    # Bo qua cac default args
    ignore_default_args=["--enable-automation"],

    # Stealth mode
    stealth=True,

    # DevTools
    devtools=False,

    # Slow motion (ms)
    slow_mo=0,

    # Timeout mac dinh (ms)
    timeout=30000,

    # Viewport
    viewport_width=1920,
    viewport_height=1080,

    # Locale
    locale="en-US",

    # Timezone
    timezone_id="America/New_York",

    # Geolocation
    geolocation={"latitude": 40.7128, "longitude": -74.0060},

    # Permissions
    permissions=["geolocation", "notifications"],

    # Color scheme
    color_scheme="dark",  # "light", "dark", "no-preference"

    # Downloads
    accept_downloads=True,
    downloads_path="/path/to/downloads",

    # HTTP headers
    extra_http_headers={"X-Custom-Header": "value"},

    # HTTPS
    ignore_https_errors=False,

    # JavaScript
    java_script_enabled=True,

    # Bypass CSP
    bypass_csp=False,

    # Video recording
    record_video=False,
    video_size={"width": 1280, "height": 720},
    video_dir="/path/to/videos",
)
```

### Su Dung BrowserConfig

```python
from kuromi_browser import Browser, BrowserConfig

async def main():
    config = BrowserConfig(
        headless=True,
        stealth=True,
        viewport_width=1920,
        viewport_height=1080,
    )

    async with Browser(config=config) as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
```

## Page Configuration

### PageConfig

```python
from kuromi_browser import PageConfig, PageMode

config = PageConfig(
    # Che do hoat dong
    mode=PageMode.BROWSER,  # BROWSER, SESSION, HYBRID

    # Timeout (ms)
    timeout=30000,

    # Wait until
    wait_until="load",  # "load", "domcontentloaded", "networkidle"

    # Viewport
    viewport={"width": 1920, "height": 1080},

    # HTTP headers
    extra_http_headers={"Accept-Language": "en-US"},

    # User agent
    user_agent="Mozilla/5.0 ...",

    # Bypass CSP
    bypass_csp=False,

    # JavaScript
    java_script_enabled=True,

    # Mobile emulation
    has_touch=False,
    is_mobile=False,
    device_scale_factor=1.0,

    # HTTPS
    ignore_https_errors=False,

    # Offline mode
    offline=False,
)
```

## Proxy Configuration

### ProxyConfig

```python
from kuromi_browser import ProxyConfig

# Tu URL
proxy = ProxyConfig.from_url("http://user:pass@proxy.example.com:8080")

# Tu cac tham so
proxy = ProxyConfig(
    server="http://proxy.example.com:8080",
    username="user",
    password="pass",
    bypass=["localhost", "*.internal.com"],
)
```

### Su Dung Proxy

```python
from kuromi_browser import Browser, BrowserConfig, ProxyConfig

config = BrowserConfig(
    proxy=ProxyConfig(
        server="http://proxy.example.com:8080",
        username="user",
        password="pass",
    )
)

async with Browser(config=config) as browser:
    page = await browser.new_page()
    await page.goto("https://example.com")
```

## Fingerprint Configuration

### Fingerprint Model

```python
from kuromi_browser import Fingerprint, NavigatorProperties, ScreenProperties

fingerprint = Fingerprint(
    # User Agent
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",

    # Navigator
    navigator=NavigatorProperties(
        platform="Win32",
        vendor="Google Inc.",
        language="en-US",
        languages=["en-US", "en"],
        hardware_concurrency=8,
        device_memory=8.0,
        max_touch_points=0,
    ),

    # Screen
    screen=ScreenProperties(
        width=1920,
        height=1080,
        avail_width=1920,
        avail_height=1040,
        color_depth=24,
        pixel_depth=24,
        device_pixel_ratio=1.0,
    ),

    # Timezone
    timezone="America/New_York",
    timezone_offset=-300,
    locale="en-US",
)
```

### Tao Fingerprint Tu Dong

```python
from kuromi_browser import FingerprintGenerator

# Tao fingerprint ngau nhien
fingerprint = FingerprintGenerator.generate()

# Tao fingerprint cho browser/OS cu the
fingerprint = FingerprintGenerator.generate(
    browser="chrome",
    os="windows",
    version=120,
)
```

## Environment Variables

Kuromi Browser ho tro cac bien moi truong sau:

| Bien | Mo ta | Mac dinh |
|------|-------|----------|
| `KUROMI_BROWSER_PATH` | Duong dan Chrome executable | Auto-detect |
| `KUROMI_HEADLESS` | Che do headless | `false` |
| `KUROMI_PROXY` | Proxy URL | None |
| `KUROMI_TIMEOUT` | Timeout mac dinh (ms) | `30000` |
| `KUROMI_STEALTH` | Bat stealth mode | `true` |
| `KUROMI_LOG_LEVEL` | Muc log | `INFO` |

## Tiep Theo

- [Page API](./api/page.md) - API day du cua Page
- [Stealth Guide](./stealth-guide.md) - Huong dan anti-detection
- [Fingerprint](./fingerprint.md) - Chi tiet ve fingerprint
