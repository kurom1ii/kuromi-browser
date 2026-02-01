# Kien Truc Project

Tai lieu nay mo ta chi tiet cau truc va thiet ke cua Kuromi Browser.

## Tong Quan

Kuromi Browser duoc thiet ke theo kien truc module, cho phep su dung linh hoat cac thanh phan rieng le hoac ket hop chung voi nhau.

```
kuromi_browser/
├── __init__.py          # Main exports va public API
├── models.py            # Data models (Pydantic)
├── interfaces.py        # Abstract base classes
├── page.py              # Page implementations
│
├── cdp/                 # Chrome DevTools Protocol
│   ├── __init__.py
│   ├── connection.py    # WebSocket connection
│   ├── launcher.py      # Chrome launcher
│   └── session.py       # CDP session management
│
├── dom/                 # DOM Service
│   ├── __init__.py
│   ├── element.py       # DOM element wrapper
│   ├── locator.py       # Element locators
│   └── service.py       # DOM query service
│
├── session/             # HTTP Mode
│   ├── __init__.py
│   ├── client.py        # HTTP client
│   ├── response.py      # Response wrapper
│   └── element.py       # HTML element parser
│
├── events/              # Event System
│   ├── __init__.py
│   ├── bus.py           # Event bus implementation
│   └── types.py         # Event type definitions
│
├── stealth/             # Anti-Detection
│   ├── __init__.py
│   ├── cdp/             # CDP Patches
│   │   ├── __init__.py
│   │   └── patches.py   # JavaScript patches
│   ├── fingerprint/     # Fingerprint Generation
│   │   └── __init__.py
│   ├── behavior/        # Human-like Behavior
│   │   ├── __init__.py
│   │   ├── mouse.py     # Mouse movement
│   │   └── keyboard.py  # Typing patterns
│   └── tls/             # TLS Impersonation
│       ├── __init__.py
│       └── client.py    # curl_cffi wrapper
│
├── network/             # Network Utilities
│   ├── __init__.py
│   ├── monitor.py       # Network monitoring
│   ├── interceptor.py   # Request/Response interception
│   ├── har.py           # HAR file support
│   └── websocket.py     # WebSocket handling
│
├── llm/                 # LLM Providers
│   ├── __init__.py
│   ├── base.py          # Base provider interface
│   ├── openai.py        # OpenAI integration
│   └── anthropic.py     # Anthropic Claude integration
│
├── agent/               # AI Agent
│   ├── __init__.py
│   ├── agent.py         # Main agent logic
│   └── actions.py       # Agent actions
│
└── watchdogs/           # Monitoring Services
    └── __init__.py
```

## Cac Module Chi Tiet

### 1. CDP Module (`cdp/`)

Module nay quan ly giao tiep voi Chrome qua Chrome DevTools Protocol.

#### CDPConnection (`connection.py`)

Quan ly ket noi WebSocket den Chrome DevTools.

```python
from kuromi_browser.cdp import CDPConnection

# Ket noi den Chrome dang chay
conn = await CDPConnection.connect("ws://localhost:9222/devtools/browser/...")

# Gui command
result = await conn.send("Page.navigate", {"url": "https://example.com"})

# Lang nghe events
conn.on("Page.loadEventFired", lambda event: print("Page loaded"))
```

**Tinh nang:**
- Ket noi WebSocket async
- Command queue va response matching
- Event subscription
- Auto-reconnect

#### CDPLauncher (`launcher.py`)

Khoi dong Chrome browser voi cac options phu hop.

```python
from kuromi_browser.cdp import CDPLauncher

# Khoi dong Chrome
process = await CDPLauncher.launch(
    headless=True,
    args=["--no-sandbox"],
    user_data_dir="/tmp/chrome-profile"
)

# Lay WebSocket URL
ws_url = await CDPLauncher.get_websocket_url(process)
```

**Tinh nang:**
- Tim Chrome executable tu dong
- Quan ly Chrome process
- Headless/headed mode
- Profile management

#### CDPSession (`session.py`)

Session cap cao de tuong tac voi page.

```python
from kuromi_browser.cdp import CDPSession

session = CDPSession(connection, target_id)

# Enable domains
await session.send("Page.enable")
await session.send("Network.enable")
await session.send("Runtime.enable")

# Inject script
await session.send(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "window.test = true;"}
)
```

### 2. DOM Module (`dom/`)

Module xu ly DOM elements va queries.

#### DOMElement (`element.py`)

Wrapper cho DOM elements voi cac method tien ich.

```python
from kuromi_browser.dom import DOMElement

element = await page.query_selector("#button")

# Thuoc tinh
tag = element.tag_name
text = await element.text_content()
html = await element.inner_html()

# Hanh dong
await element.click()
await element.fill("Hello")
await element.hover()
```

#### Locator (`locator.py`)

He thong tim kiem elements linh hoat.

```python
from kuromi_browser.dom import Locator

# CSS selector
locator = Locator.css("#submit-button")

# XPath
locator = Locator.xpath("//button[@type='submit']")

# Text content
locator = Locator.text("Submit")

# Ket hop
locator = Locator.css("form").child(Locator.css("button"))
```

### 3. Session Module (`session/`)

Module HTTP mode su dung curl_cffi cho TLS impersonation.

#### Session Client (`client.py`)

HTTP client voi browser fingerprint.

```python
from kuromi_browser.session import Session

session = Session(browser="chrome")

response = await session.get("https://api.example.com/data")
data = response.json()

response = await session.post(
    "https://api.example.com/submit",
    json={"key": "value"}
)
```

**Tinh nang:**
- TLS/JA3 fingerprint matching
- Cookie jar
- Proxy support
- Auto redirect

### 4. Events Module (`events/`)

He thong event-driven cho cac thanh phan.

#### EventBus (`bus.py`)

Central event bus cho inter-component communication.

```python
from kuromi_browser.events import EventBus, EventType

bus = EventBus()

# Dang ky handler
@bus.on(EventType.PAGE_LOAD)
async def handle_load(event):
    print(f"Page loaded: {event.data}")

# Phat event
await bus.emit(EventType.PAGE_LOAD, {"url": "https://example.com"})
```

#### EventTypes (`types.py`)

Dinh nghia cac loai event:

- `PAGE_LOAD` - Trang da tai xong
- `PAGE_ERROR` - Loi trang
- `REQUEST` - Network request
- `RESPONSE` - Network response
- `CONSOLE` - Console message
- `DIALOG` - Alert/Confirm/Prompt

### 5. Stealth Module (`stealth/`)

Module chong phat hien bot - day la phan quan trong nhat cua project.

#### CDP Patches (`cdp/patches.py`)

JavaScript patches de an dau automation.

```python
from kuromi_browser.stealth.cdp import CDPPatches

patches = CDPPatches(fingerprint)

# Lay tat ca patches
script = patches.get_combined_patch()

# Ap dung vao page
await patches.apply_to_page(cdp_session)
```

**Cac patch bao gom:**

| Patch | Muc dich |
|-------|----------|
| `WEBDRIVER_PATCH` | An `navigator.webdriver` |
| `CHROME_PATCHES` | Gia lap `chrome.runtime`, `chrome.loadTimes`, etc. |
| `PERMISSIONS_PATCH` | Fix permissions API |
| `IFRAME_PATCH` | Fix iframe detection |
| `PLUGINS_PATCH` | Gia lap plugins va mimeTypes |
| `LANGUAGES_PATCH` | Set navigator.languages |
| `WEBGL_PATCH` | Spoof WebGL vendor/renderer |
| `CANVAS_NOISE_PATCH` | Them noise vao canvas fingerprint |
| `AUDIO_NOISE_PATCH` | Them noise vao audio fingerprint |
| `SCREEN_PATCH` | Spoof screen properties |
| `TIMEZONE_PATCH` | Override timezone |

#### FingerprintGenerator (`fingerprint/__init__.py`)

Tao browser fingerprints thuc te.

```python
from kuromi_browser.stealth.fingerprint import FingerprintGenerator

# Tao ngau nhien
fp = FingerprintGenerator.generate()

# Tao cho browser/OS cu the
fp = FingerprintGenerator.generate(
    browser="chrome",
    os="windows",
    locale="en-US"
)

# Tao nhat quan (cung identifier = cung fingerprint)
fp = FingerprintGenerator.generate_consistent("user-123")

# Dung browserforge
fp = FingerprintGenerator.from_browserforge()

# Validate fingerprint
issues = FingerprintGenerator.validate(fp)
```

**Du lieu thong ke:**

- `SCREEN_RESOLUTIONS` - Do phan giai man hinh pho bien
- `USER_AGENTS` - User agents theo browser/OS
- `WEBGL_RENDERERS` - WebGL renderers theo GPU
- `TIMEZONES` - Timezone data

#### Human Mouse (`behavior/mouse.py`)

Mo phong di chuyen chuot giong nguoi.

```python
from kuromi_browser.stealth.behavior import HumanMouse

# Tao duong di Bezier
path = HumanMouse.generate_path(
    start=(100, 100),
    end=(500, 300),
    speed=500  # pixels/second
)

# Di chuyen chuot
await HumanMouse.move(cdp_session, start, end)

# Click
await HumanMouse.click(cdp_session, x=500, y=300)

# Scroll
await HumanMouse.scroll(cdp_session, x=500, y=300, delta_y=-300)

# Drag
await HumanMouse.drag(cdp_session, start=(100, 100), end=(300, 300))
```

**Tinh nang:**

- Bezier curve paths
- Variable speed (nhanh o giua, cham o 2 dau)
- Random jitter
- Overshoot simulation

#### Human Keyboard (`behavior/keyboard.py`)

Mo phong go phim giong nguoi.

```python
from kuromi_browser.stealth.behavior import HumanKeyboard

# Go text
await HumanKeyboard.type(cdp_session, "Hello World")

# Voi delay ngau nhien
await HumanKeyboard.type(
    cdp_session,
    "Hello World",
    delay_range=(50, 150)  # ms giua cac phim
)
```

**Tinh nang:**

- Variable typing speed
- Typo simulation (tuy chon)
- Key press/release timing

#### TLS Client (`tls/client.py`)

HTTP client voi TLS fingerprint impersonation.

```python
from kuromi_browser.stealth.tls import TLSClient, TLSConfig

# Tao client
client = TLSClient(browser="chrome")

# Request
response = client.get("https://example.com")

# Voi config
config = TLSConfig(
    impersonate="chrome120",
    proxy="http://proxy:8080",
    timeout=30.0
)
client = TLSClient(config=config)
```

**Ho tro browsers:**

- Chrome 99-124
- Firefox 102-117
- Safari 15.3-17.0
- Edge 99-101

### 6. Network Module (`network/`)

#### NetworkMonitor (`monitor.py`)

Theo doi network traffic.

```python
from kuromi_browser.network import NetworkMonitor

monitor = NetworkMonitor(cdp_session)
await monitor.start()

# Lay requests
requests = monitor.get_requests()

# Filter
api_requests = monitor.filter(url_pattern="*/api/*")
```

#### NetworkInterceptor (`interceptor.py`)

Chan va sua doi requests/responses.

```python
from kuromi_browser.network import NetworkInterceptor

interceptor = NetworkInterceptor(cdp_session)

@interceptor.on_request("**/api/**")
async def handle_request(request):
    # Sua headers
    request.headers["X-Custom"] = "value"
    return request

@interceptor.on_response("**/api/**")
async def handle_response(response):
    # Sua response
    data = response.json()
    data["modified"] = True
    return response.with_json(data)
```

### 7. LLM Module (`llm/`)

#### Base Provider (`base.py`)

Interface cho LLM providers.

```python
from kuromi_browser.llm.base import LLMProvider

class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict]) -> str:
        """Chat completion."""
        pass

    @abstractmethod
    async def chat_with_vision(
        self,
        messages: list[dict],
        images: list[bytes]
    ) -> str:
        """Chat voi image input."""
        pass
```

#### OpenAI Provider (`openai.py`)

```python
from kuromi_browser.llm import OpenAI

llm = OpenAI(
    api_key="sk-...",
    model="gpt-4-vision-preview"
)

response = await llm.chat([
    {"role": "user", "content": "Hello!"}
])
```

#### Anthropic Provider (`anthropic.py`)

```python
from kuromi_browser.llm import Anthropic

llm = Anthropic(
    api_key="sk-ant-...",
    model="claude-3-opus-20240229"
)

response = await llm.chat_with_vision(
    messages=[{"role": "user", "content": "Mo ta anh nay"}],
    images=[screenshot_bytes]
)
```

### 8. Agent Module (`agent/`)

#### Agent (`agent.py`)

AI agent de tu dong hoa browser.

```python
from kuromi_browser import Agent

agent = Agent(llm=llm, page=page)

result = await agent.run(
    "Tim kiem Python tutorials tren Google",
    max_steps=10
)

if result.success:
    print(result.result)
else:
    print(f"Error: {result.error}")

# Xem lich su
for step in result.history:
    print(f"Step {step['step']}: {step['action']['type']}")
```

#### Actions (`actions.py`)

Dinh nghia cac action ma agent co the thuc hien:

```python
from kuromi_browser.agent.actions import Action, ActionType

# Cac loai action
ActionType.NAVIGATE    # Di chuyen den URL
ActionType.CLICK       # Click element
ActionType.TYPE        # Go text
ActionType.FILL        # Dien form
ActionType.SCROLL      # Cuon trang
ActionType.HOVER       # Hover element
ActionType.PRESS       # Nhan phim
ActionType.WAIT        # Doi
ActionType.SCREENSHOT  # Chup man hinh
ActionType.EXTRACT     # Lay text
ActionType.DONE        # Hoan thanh
ActionType.FAIL        # That bai
```

## Data Flow

### Browser Mode Flow

```
User Code
    │
    ▼
Page (page.py)
    │
    ▼
CDPSession (cdp/session.py)
    │
    ▼
CDPConnection (cdp/connection.py)
    │
    ▼
Chrome Browser (via WebSocket)
```

### Stealth Mode Flow

```
User Code
    │
    ▼
StealthPage (page.py)
    │
    ├──▶ FingerprintGenerator
    │
    ├──▶ CDPPatches ──▶ JavaScript Injection
    │
    ├──▶ HumanMouse ──▶ Bezier Curves
    │
    └──▶ HumanKeyboard ──▶ Natural Typing
```

### Hybrid Mode Flow

```
User Code
    │
    ▼
HybridPage (page.py)
    │
    ├──▶ Browser Mode (CDP)
    │       └──▶ JavaScript execution
    │           └──▶ Complex interactions
    │
    └──▶ Session Mode (HTTP)
            └──▶ API calls
                └──▶ Fast data fetching
```

### AI Agent Flow

```
User Task
    │
    ▼
Agent (agent/agent.py)
    │
    ├──▶ Screenshot ──▶ LLM (with vision)
    │                       │
    │                       ▼
    │                   Decision
    │                       │
    ▼                       ▼
Page ◀────────────── Action Execution
    │
    ▼
Result
```

## Design Principles

### 1. Async-First

Tat ca cac operations la async de toi uu performance.

```python
# Tat ca methods la async
await page.goto(url)
await page.click(selector)
await page.screenshot()
```

### 2. Interface-Based

Su dung abstract base classes de dinh nghia contracts.

```python
# interfaces.py
class BasePage(ABC):
    @abstractmethod
    async def goto(self, url: str) -> None: ...

    @abstractmethod
    async def click(self, selector: str) -> None: ...
```

### 3. Composition over Inheritance

Cac component duoc to hop thay vi ke thua sau.

```python
class HybridPage:
    def __init__(self, cdp_session, session):
        self._cdp = cdp_session
        self._session = session
```

### 4. Event-Driven

Su dung events de giao tiep giua cac component.

```python
bus.on(EventType.PAGE_LOAD, handler)
bus.emit(EventType.PAGE_LOAD, data)
```

### 5. Fail-Safe Stealth

Cac stealth patches duoc thiet ke de khong lam hong page neu co loi.

```python
# Moi patch duoc wrap trong try-catch
try {
    Object.defineProperty(navigator, 'webdriver', {...});
} catch (e) {}
```

## Tiep Theo

- [API Reference](api-reference.md) - Tai lieu API chi tiet
- [Stealth Guide](stealth-guide.md) - Huong dan chong phat hien
- [Getting Started](getting-started.md) - Bat dau su dung
