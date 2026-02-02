# Stealth Guide

Huong dan su dung cac tinh nang anti-detection trong Kuromi Browser.

## Tong Quan

Kuromi Browser cung cap nhieu lop anti-detection de giup browser automation tranh bi phat hien:

1. **CDP Patches** - Patch cac API ma bot detectors kiem tra
2. **Patchright Techniques** - Input leak fix, Chrome stealth args
3. **Fingerprint Spoofing** - Gia lap fingerprint browser thuc
4. **TLS Impersonation** - Gia lap TLS/JA3 fingerprint
5. **Human-like Behavior** - Mo phong hanh vi nguoi dung

## Patchright Integration (NEW)

Kuromi Browser tich hop cac ky thuat tu [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) - phien ban Playwright undetected.

### Input Leak Fix

CDP input events co `pageX == screenX` - dieu nay khong xay ra voi browser thuc vi co offset tu toolbar. Patch nay sua loi do:

```python
from kuromi_browser.models import Fingerprint

fp = Fingerprint()
# Input leak protection mac dinh enabled
print(fp.input_leak.enabled)  # True
print(fp.input_leak.chrome_offset_y)  # 85 (toolbar height)
```

### Chrome Stealth Args

Su dung recommended Chrome flags de tranh detection:

```python
from kuromi_browser.stealth import (
    get_stealth_chromium_args,
    filter_automation_args,
    CHROMIUM_STEALTH_ARGS,
    CHROMIUM_ARGS_TO_REMOVE,
)

# Lay recommended args
args = get_stealth_chromium_args()
# ['--disable-blink-features=AutomationControlled', ...]

# Loc bo automation-revealing args
clean_args = filter_automation_args(your_args)
```

### Cac Args Quan Trong

**Them vao:**
- `--disable-blink-features=AutomationControlled` - Critical, an navigator.webdriver

**Loai bo:**
- `--enable-automation` - Lo navigator.webdriver
- `--disable-popup-blocking` - Unusual behavior
- `--disable-component-update` - Detection as stealth driver
- `--disable-extensions` - Unusual for real browser

### CoalescedEvents Emulation

CDP khong dispatch CoalescedEvents. Patch nay emulate de tranh detection:

```python
from kuromi_browser.stealth.cdp.patches import COALESCED_EVENTS_PATCH
```

## CDP Patches

### navigator.webdriver

Mac dinh, browser automation dat `navigator.webdriver = true`. Kuromi Browser patch de:

```javascript
// Truoc (phat hien)
navigator.webdriver  // true

// Sau (an)
navigator.webdriver  // undefined
```

### Chrome Runtime

Bot detectors kiem tra su hien dien cua `window.chrome`:

```python
from kuromi_browser import StealthPage

page = StealthPage()
await page.apply_stealth()

# window.chrome.runtime duoc them vao
# window.chrome.csi() hoat dong
# window.chrome.loadTimes() hoat dong
```

### Automation Traces

Cac traces bi xoa:
- `window.navigator.webdriver`
- `window.navigator.languages` (tro thanh mang thuc)
- `window.navigator.plugins` (them plugins gia)
- CDP-specific objects

### Su Dung

```python
from kuromi_browser import StealthPage, StealthConfig

config = StealthConfig(
    webdriver=True,         # Patch navigator.webdriver
    chrome_app=True,        # Them window.chrome.app
    chrome_csi=True,        # Them window.chrome.csi
    chrome_runtime=True,    # Them window.chrome.runtime
    iframe_content_window=True,  # Patch iframe.contentWindow
    media_codecs=True,      # Patch MediaRecorder
    navigator_permissions=True,  # Patch Permissions API
    navigator_plugins=True,      # Them fake plugins
    navigator_languages=True,    # Patch languages
    navigator_vendor=True,       # Patch vendor
)

page = StealthPage(config=config)
```

## Fingerprint Spoofing

### Fingerprint Model

```python
from kuromi_browser import Fingerprint, NavigatorProperties, ScreenProperties, WebGLProperties

fingerprint = Fingerprint(
    # User Agent
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

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
        device_pixel_ratio=1.0,
    ),

    # WebGL
    webgl=WebGLProperties(
        vendor="Google Inc. (NVIDIA)",
        renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0)",
    ),

    # Timezone
    timezone="America/New_York",
    timezone_offset=-300,
)
```

### Tu Dong Generate

```python
from kuromi_browser import FingerprintGenerator

# Random fingerprint
fp = FingerprintGenerator.generate()

# Fingerprint cho Windows + Chrome
fp = FingerprintGenerator.generate(
    browser="chrome",
    os="windows",
    version=120,
)

# Fingerprint cho Mac + Safari
fp = FingerprintGenerator.generate(
    browser="safari",
    os="macos",
)

# Fingerprint cho mobile
fp = FingerprintGenerator.generate(
    browser="chrome",
    os="android",
    is_mobile=True,
)
```

### Cac Thuoc Tinh Fingerprint

#### Navigator Properties

| Property | Mo ta | Vi du |
|----------|-------|-------|
| `platform` | OS platform | "Win32", "MacIntel", "Linux x86_64" |
| `vendor` | Browser vendor | "Google Inc.", "Apple Computer, Inc." |
| `language` | Primary language | "en-US", "vi-VN" |
| `languages` | Language list | ["en-US", "en"] |
| `hardware_concurrency` | CPU cores | 4, 8, 16 |
| `device_memory` | RAM (GB) | 4, 8, 16 |
| `max_touch_points` | Touch support | 0 (no touch), 5 (touch) |

#### Screen Properties

| Property | Mo ta | Vi du |
|----------|-------|-------|
| `width` | Screen width | 1920 |
| `height` | Screen height | 1080 |
| `avail_width` | Available width | 1920 |
| `avail_height` | Available height (tru taskbar) | 1040 |
| `color_depth` | Color depth | 24 |
| `pixel_depth` | Pixel depth | 24 |
| `device_pixel_ratio` | DPI scale | 1.0, 1.25, 2.0 |

#### WebGL Properties

| Property | Mo ta | Vi du |
|----------|-------|-------|
| `vendor` | WebGL vendor | "Google Inc. (NVIDIA)" |
| `renderer` | GPU renderer | "ANGLE (NVIDIA, GeForce GTX 1080)" |
| `version` | WebGL version | "WebGL 1.0" |

## TLS Impersonation

### JA3 Fingerprint

JA3 la fingerprint cua TLS handshake. Moi browser co JA3 dac trung.

```python
from kuromi_browser.stealth.tls import TLSClient, TLSProfile

# Su dung profile Chrome
client = TLSClient(profile=TLSProfile.CHROME_120)

# Su dung profile Firefox
client = TLSClient(profile=TLSProfile.FIREFOX_121)

# Su dung profile Safari
client = TLSClient(profile=TLSProfile.SAFARI_17)
```

### HTTP/2 Fingerprint

```python
from kuromi_browser.stealth.tls import HTTP2Config

config = HTTP2Config(
    # Header order
    header_order=[
        ":method",
        ":authority",
        ":scheme",
        ":path",
    ],
    # Settings frame
    settings={
        "HEADER_TABLE_SIZE": 65536,
        "MAX_CONCURRENT_STREAMS": 1000,
        "INITIAL_WINDOW_SIZE": 6291456,
    },
)
```

### Tich Hop voi curl_cffi

```python
from kuromi_browser.session import Session

session = Session(impersonate="chrome120")

response = await session.get("https://example.com")
```

## Human-like Behavior

### Mouse Movement

Kuromi Browser su dung Bezier curves de tao chuyen dong chuot tu nhien:

```python
from kuromi_browser.stealth.behavior import HumanMouse

mouse = HumanMouse(page)

# Di chuyen tu nhien den vi tri
await mouse.move_to(500, 300)

# Di chuyen den element
await mouse.move_to_element("#button")

# Click voi delay tu nhien
await mouse.click("#button", human_delay=True)
```

#### Cac Thuat Toan Di Chuyen

1. **Bezier Curve**: Chuyen dong cong tu nhien
2. **Overshoot**: Di qua dich roi quay lai
3. **Jitter**: Rung nhe ngau nhien
4. **Variable Speed**: Toc do thay doi

```python
# Cau hinh mouse behavior
mouse = HumanMouse(
    page,
    min_speed=100,       # Pixel per second
    max_speed=500,
    overshoot=0.1,       # 10% overshoot
    jitter=2,            # 2px jitter
)
```

### Keyboard Typing

Mo phong go phim tu nhien:

```python
from kuromi_browser.stealth.behavior import HumanKeyboard

keyboard = HumanKeyboard(page)

# Go text voi delay tu nhien
await keyboard.type_human(
    "#input",
    "Hello World",
    wpm=60,              # Words per minute
    mistake_rate=0.02,   # 2% ty le loi
)
```

#### Cac Tinh Nang

1. **Variable Delay**: Delay khac nhau giua cac phim
2. **Typos**: Tao loi go va sua
3. **Pause**: Dung giua cac tu
4. **Realistic WPM**: Toc do go thuc te

### Scroll Behavior

```python
from kuromi_browser.stealth.behavior import HumanScroll

scroll = HumanScroll(page)

# Scroll xuong tu nhien
await scroll.scroll_down(
    distance=500,
    duration=1000,      # ms
    easing="ease_out",  # Easing function
)

# Scroll den element
await scroll.scroll_to_element("#target")
```

## Best Practices

### 1. Su Dung Fingerprint Nhat Quan

```python
# Tao fingerprint mot lan
fingerprint = FingerprintGenerator.generate(
    browser="chrome",
    os="windows",
)

# Su dung cho toan bo session
async with Browser(fingerprint=fingerprint) as browser:
    page = await browser.new_page()
    # ...
```

### 2. Match User Agent voi TLS

```python
# User agent phai khop voi TLS profile
fingerprint = Fingerprint(
    user_agent="...Chrome/120...",  # Chrome 120
)

session = Session(impersonate="chrome120")  # Cung Chrome 120
```

### 3. Thoi Gian Hop Ly

```python
# Khong lam qua nhanh
await page.wait_for_timeout(random.randint(1000, 3000))

# Delay giua cac actions
await element.click()
await page.wait_for_timeout(500)
await element2.type("text", delay=50)
```

### 4. Viewport Phu Hop

```python
# Viewport phai khop voi screen
fingerprint = Fingerprint(
    screen=ScreenProperties(width=1920, height=1080),
)

await page.set_viewport(1920, 1080)  # Khop voi screen
```

### 5. Timezone Nhat Quan

```python
fingerprint = Fingerprint(
    timezone="Asia/Ho_Chi_Minh",
    timezone_offset=-420,  # UTC+7
    locale="vi-VN",
)
```

## Kiem Tra Detection

### Cac Trang Test

1. **bot.sannysoft.com** - Kiem tra nhieu tinh nang
2. **browserleaks.com** - WebGL, Canvas, Audio fingerprint
3. **pixelscan.net** - Detection scan
4. **deviceinfo.me** - Device info

### Vi Du Kiem Tra

```python
from kuromi_browser import StealthPage, FingerprintGenerator

async def test_stealth():
    fp = FingerprintGenerator.generate()
    page = StealthPage(fingerprint=fp)

    await page.goto("https://bot.sannysoft.com")
    await page.screenshot(path="stealth_test.png")

    # Kiem tra ket qua
    results = await page.evaluate("""
        () => {
            const tests = document.querySelectorAll('tr');
            return Array.from(tests).map(row => ({
                name: row.cells[0]?.textContent,
                result: row.cells[1]?.textContent,
            }));
        }
    """)

    for test in results:
        print(f"{test['name']}: {test['result']}")
```

## Tiep Theo

- [Fingerprint](./fingerprint.md) - Chi tiet ve fingerprint
- [Agent Guide](./agent-guide.md) - AI automation
- [CDP Protocol](./advanced/cdp.md) - Low-level CDP
