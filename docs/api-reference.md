# API Reference

Trang tong hop tham khao API cho Kuromi Browser.

## Tong Quan

Kuromi Browser cung cap cac module chinh sau:

| Module | Mo ta | Import |
|--------|-------|--------|
| `Page` | Browser page control | `from kuromi_browser import Page` |
| `StealthPage` | Anti-detection page | `from kuromi_browser import StealthPage` |
| `HybridPage` | Browser + HTTP | `from kuromi_browser import HybridPage` |
| `Agent` | AI automation | `from kuromi_browser import Agent` |
| `Session` | HTTP client | `from kuromi_browser import Session` |
| `Fingerprint` | Browser fingerprint | `from kuromi_browser import Fingerprint` |

## Quick Links

### Core Classes
- [Page API](api/page.md) - Page, StealthPage, HybridPage
- [Element API](api/element.md) - DOM element interaction

### Stealth Module
- [Stealth Guide](stealth-guide.md) - Anti-detection full guide
- [FingerprintGenerator](#fingerprintgenerator) - Fingerprint creation
- [CDPPatches](#cdppatches) - JavaScript patches
- [HumanMouse](#humanmouse) - Mouse simulation
- [TLSClient](#tlsclient) - TLS impersonation

### AI Agent
- [Agent](#agent) - AI browser automation

---

## Page Classes

### Page

CDP-based browser page.

```python
from kuromi_browser import Page, CDPSession

cdp = await CDPSession.connect("http://localhost:9222")
page = Page(cdp)

await page.goto("https://example.com")
await page.click("#button")
text = await page.query_selector(".content").text_content()
await page.screenshot(path="screen.png")
```

**Xem chi tiet:** [Page API Reference](api/page.md)

### StealthPage

Page voi anti-detection features.

```python
from kuromi_browser import StealthPage, FingerprintGenerator

fp = FingerprintGenerator.generate(browser="chrome", os="windows")
page = StealthPage(cdp, fingerprint=fp)

await page.apply_stealth()
await page.goto("https://protected-site.com")
```

### HybridPage

Ket hop Browser va HTTP Session.

```python
from kuromi_browser import HybridPage, Session

page = HybridPage(cdp, Session())

# HTTP request nhanh
data = await page.fetch("https://api.example.com/data")

# Browser khi can JavaScript
await page.goto("https://example.com")
```

---

## Stealth Module

### FingerprintGenerator

Tao browser fingerprints thuc te.

```python
from kuromi_browser.stealth import FingerprintGenerator

# Random fingerprint
fp = FingerprintGenerator.generate()

# Custom fingerprint
fp = FingerprintGenerator.generate(
    browser="chrome",     # chrome, firefox, safari, edge
    os="windows",         # windows, macos, linux
    device="desktop",     # desktop, mobile, tablet
    locale="en-US",
    screen_width=1920,
    screen_height=1080,
)

# Consistent fingerprint (cung input = cung output)
fp = FingerprintGenerator.generate_consistent("user-id-123")

# Validate fingerprint
issues = FingerprintGenerator.validate(fp)
if issues:
    print("Warnings:", issues)
```

**Methods:**

| Method | Mo ta |
|--------|-------|
| `generate(**kwargs)` | Tao random fingerprint |
| `generate_consistent(id, **kwargs)` | Tao fingerprint nhat quan |
| `from_browserforge()` | Dung browserforge library |
| `validate(fp)` | Kiem tra tinh hop le |

### CDPPatches

JavaScript patches de an dau automation.

```python
from kuromi_browser.stealth import CDPPatches, apply_stealth

# Cach 1: Dung apply_stealth (khuyen nghi)
await apply_stealth(cdp_session, fingerprint)

# Cach 2: Dung CDPPatches truc tiep
patches = CDPPatches(fingerprint)
await patches.apply_to_page(cdp_session)

# Cach 3: Chi basic patches
await CDPPatches.apply_basic_patches(cdp_session)
```

**Patches co san:**

| Patch | Mo ta |
|-------|-------|
| `WEBDRIVER_PATCH` | An navigator.webdriver |
| `CHROME_PATCHES` | Gia lap chrome.runtime |
| `PERMISSIONS_PATCH` | Fix permissions API |
| `PLUGINS_PATCH` | Them fake plugins |
| `WEBGL_PATCH` | Spoof WebGL fingerprint |
| `CANVAS_NOISE_PATCH` | Noise cho canvas |
| `AUDIO_NOISE_PATCH` | Noise cho audio |
| `SCREEN_PATCH` | Override screen properties |
| `TIMEZONE_PATCH` | Override timezone |

### StealthConfig

Cau hinh cac stealth features.

```python
from kuromi_browser.stealth import StealthConfig

config = StealthConfig(
    webdriver=True,            # Patch navigator.webdriver
    chrome_app=True,           # Them chrome.app
    chrome_runtime=True,       # Them chrome.runtime
    navigator_plugins=True,    # Fake plugins
    navigator_languages=True,  # Override languages
    webgl_vendor=True,         # Spoof WebGL
    canvas_fingerprint=True,   # Canvas noise
    audio_fingerprint=True,    # Audio noise
    timezone=True,             # Override timezone
)
```

### HumanMouse

Mo phong mouse movement giong nguoi.

```python
from kuromi_browser.stealth.behavior import HumanMouse

# Tao path
path = HumanMouse.generate_path(
    start=(100, 100),
    end=(500, 300),
    speed=500,            # pixels/second
    with_overshoot=True,  # Vuot qua roi quay lai
)

# Di chuyen
await HumanMouse.move(cdp, (100, 100), (500, 300))

# Click
await HumanMouse.click(cdp, x=500, y=300)

# Scroll
await HumanMouse.scroll(cdp, x=500, y=300, delta_y=-300, steps=5)

# Drag
await HumanMouse.drag(cdp, start=(100, 100), end=(300, 300))
```

### HumanKeyboard

Mo phong go phim giong nguoi.

```python
from kuromi_browser.stealth.behavior import HumanKeyboard

await HumanKeyboard.type(
    cdp,
    "Hello World",
    delay_range=(50, 150),  # ms giua cac phim
)
```

### TLSClient

HTTP client voi TLS fingerprint impersonation.

```python
from kuromi_browser.stealth.tls import TLSClient, TLSConfig

# Basic usage
client = TLSClient(browser="chrome")
response = client.get("https://example.com")

# Voi config
config = TLSConfig(
    impersonate="chrome120",
    proxy="http://proxy:8080",
    timeout=30.0,
    headers={"Accept-Language": "en-US"},
)
client = TLSClient(config=config)

# Requests
response = client.get(url, params=params, headers=headers)
response = client.post(url, data=data, json=json_data)
response = client.put(url, data=data)
response = client.delete(url)

# Async
response = await client.async_get(url)
response = await client.async_post(url, json=data)
```

**Browsers ho tro:**

| Browser | Versions |
|---------|----------|
| Chrome | 99-124 |
| Firefox | 102-117 |
| Safari | 15.3-17.0 |
| Edge | 99-101 |

---

## Agent Module

### Agent

AI-powered browser automation.

```python
from kuromi_browser import Agent
from kuromi_browser.llm import OpenAI

# Setup
llm = OpenAI(api_key="sk-...")
agent = Agent(llm=llm, page=page)

# Chay task
result = await agent.run(
    "Tim kiem Python tutorials tren Google",
    max_steps=10,
)

if result.success:
    print("Result:", result.result)
else:
    print("Error:", result.error)

# Xem history
for step in result.history:
    action = step["action"]
    print(f"Step {step['step']}: {action['type']}")
```

**AgentResult:**

| Property | Type | Mo ta |
|----------|------|-------|
| `success` | bool | Task thanh cong? |
| `task` | str | Task description |
| `result` | Any | Ket qua (neu success) |
| `error` | str | Loi (neu fail) |
| `steps` | int | So buoc da thuc hien |
| `history` | list | Lich su hanh dong |

**Actions ho tro:**

| Action | Tham so | Mo ta |
|--------|---------|-------|
| `navigate` | `url` | Di chuyen den URL |
| `click` | `selector` | Click element |
| `type` | `selector`, `text` | Go text |
| `fill` | `selector`, `value` | Dien form |
| `scroll` | `direction`, `amount` | Cuon trang |
| `hover` | `selector` | Hover element |
| `press` | `key` | Nhan phim |
| `wait` | `ms` | Doi |
| `screenshot` | - | Chup man hinh |
| `extract` | `selector` | Lay text |
| `done` | `result` | Hoan thanh |
| `fail` | `reason` | That bai |

### LLM Providers

```python
from kuromi_browser.llm import OpenAI, Anthropic

# OpenAI
openai = OpenAI(
    api_key="sk-...",
    model="gpt-4-vision-preview",
)

# Anthropic Claude
anthropic = Anthropic(
    api_key="sk-ant-...",
    model="claude-3-opus-20240229",
)

# Chat
response = await llm.chat([
    {"role": "user", "content": "Hello!"}
])

# Chat with vision
response = await llm.chat_with_vision(
    messages=[{"role": "user", "content": "Mo ta anh nay"}],
    images=[screenshot_bytes],
)
```

---

## Data Models

### Fingerprint

```python
from kuromi_browser import (
    Fingerprint,
    NavigatorProperties,
    ScreenProperties,
    WebGLProperties,
    AudioProperties,
    CanvasProperties,
)

fp = Fingerprint(
    user_agent="Mozilla/5.0...",
    navigator=NavigatorProperties(
        platform="Win32",
        vendor="Google Inc.",
        language="en-US",
        languages=["en-US", "en"],
        hardware_concurrency=8,
        device_memory=8.0,
        max_touch_points=0,
    ),
    screen=ScreenProperties(
        width=1920,
        height=1080,
        avail_width=1920,
        avail_height=1040,
        color_depth=24,
        device_pixel_ratio=1.0,
    ),
    webgl=WebGLProperties(
        vendor="Google Inc. (NVIDIA)",
        renderer="ANGLE (NVIDIA, GeForce GTX 1080...)",
    ),
    audio=AudioProperties(
        sample_rate=44100,
        max_channel_count=2,
    ),
    canvas=CanvasProperties(
        noise_enabled=True,
        noise_seed=12345,
    ),
    timezone="America/New_York",
    timezone_offset=-300,
    locale="en-US",
)
```

### Cookie

```python
from kuromi_browser import Cookie

cookie = Cookie(
    name="session_id",
    value="abc123",
    domain="example.com",
    path="/",
    expires=1735689600,
    secure=True,
    http_only=True,
    same_site="Lax",  # "Strict", "Lax", "None"
)
```

### ProxyConfig

```python
from kuromi_browser import ProxyConfig

proxy = ProxyConfig(
    server="http://proxy.example.com:8080",
    username="user",
    password="pass",
    bypass=["localhost", "*.internal.com"],
)

# Tu URL
proxy = ProxyConfig.from_url("http://user:pass@proxy:8080")
```

### BrowserConfig

```python
from kuromi_browser import BrowserConfig, BrowserType

config = BrowserConfig(
    browser_type=BrowserType.CHROMIUM,
    headless=False,
    proxy=proxy_config,
    user_data_dir="/path/to/profile",
    executable_path="/usr/bin/chrome",
    args=["--disable-gpu"],
    stealth=True,
    timeout=30000,
    viewport_width=1920,
    viewport_height=1080,
    locale="en-US",
    timezone_id="America/New_York",
)
```

---

## Events

### EventBus

```python
from kuromi_browser.events import EventBus, EventType

bus = EventBus()

# Dang ky handler
@bus.on(EventType.PAGE_LOAD)
async def on_load(event):
    print(f"Page loaded: {event.data}")

# Emit event
await bus.emit(EventType.PAGE_LOAD, {"url": "https://example.com"})
```

### EventTypes

| Event | Mo ta |
|-------|-------|
| `PAGE_LOAD` | Trang tai xong |
| `PAGE_ERROR` | Loi trang |
| `REQUEST` | Network request |
| `RESPONSE` | Network response |
| `CONSOLE` | Console message |
| `DIALOG` | Alert/Confirm/Prompt |

---

## CDP Module

### CDPConnection

```python
from kuromi_browser.cdp import CDPConnection

conn = await CDPConnection.connect("ws://localhost:9222/...")

# Send command
result = await conn.send("Page.navigate", {"url": "https://example.com"})

# Listen events
conn.on("Page.loadEventFired", handler)
```

### CDPSession

```python
from kuromi_browser.cdp import CDPSession

session = CDPSession(connection, target_id)

await session.send("Page.enable")
await session.send("Network.enable")
await session.send("Runtime.enable")
```

### CDPLauncher

```python
from kuromi_browser.cdp import CDPLauncher

process = await CDPLauncher.launch(
    headless=True,
    args=["--no-sandbox"],
)

ws_url = await CDPLauncher.get_websocket_url(process)
```

---

## Network Module

### NetworkMonitor

```python
from kuromi_browser.network import NetworkMonitor

monitor = NetworkMonitor(cdp)
await monitor.start()

requests = monitor.get_requests()
api_requests = monitor.filter(url_pattern="*/api/*")
```

### NetworkInterceptor

```python
from kuromi_browser.network import NetworkInterceptor

interceptor = NetworkInterceptor(cdp)

@interceptor.on_request("**/api/**")
async def handle(request):
    request.headers["X-Custom"] = "value"
    return request
```

---

## Session Module

### Session

HTTP client voi TLS impersonation.

```python
from kuromi_browser import Session

session = Session(browser="chrome")

response = await session.get("https://example.com")
response = await session.post(url, json={"key": "value"})

# Cookies
session.cookies.set("name", "value", domain="example.com")
cookies = session.cookies.get_dict()
```

### SessionPool

Pool cua nhieu sessions.

```python
from kuromi_browser import SessionPool

pool = SessionPool(size=10, browser="chrome")

async with pool.acquire() as session:
    response = await session.get(url)
```

---

## Exceptions

```python
from kuromi_browser.exceptions import (
    TimeoutError,
    ElementNotFoundError,
    NavigationError,
    CDPError,
    StealthError,
)

try:
    await page.goto(url, timeout=5000)
except TimeoutError:
    print("Page load timeout")

try:
    await page.click("#nonexistent")
except ElementNotFoundError:
    print("Element not found")
```

---

## Tiep Theo

- [Getting Started](getting-started.md) - Huong dan bat dau
- [Architecture](architecture.md) - Kien truc project
- [Stealth Guide](stealth-guide.md) - Anti-detection chi tiet
