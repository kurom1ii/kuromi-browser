# Hướng Dẫn Đóng Góp (CONTRIBUTING)

Tài liệu hướng dẫn phát triển và đóng góp vào Kuromi Browser.

---

## 📋 Mục Lục

1. [Cài Đặt Môi Trường](#cài-đặt-môi-trường)
2. [Cấu Trúc Codebase](#cấu-trúc-codebase)
3. [Luồng Dữ Liệu](#luồng-dữ-liệu)
4. [Dependencies](#dependencies)
5. [Quy Trình Phát Triển](#quy-trình-phát-triển)
6. [Testing](#testing)
7. [Code Style](#code-style)

---

## 🔧 Cài Đặt Môi Trường

### Yêu Cầu

- Python 3.10+ (khuyến nghị 3.11+)
- Git
- Chrome/Chromium (cho browser automation)

### Bước Cài Đặt

```bash
# 1. Clone repository
git clone https://github.com/kurom1ii/kuromi-browser.git
cd kuromi-browser

# 2. Tạo virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# hoặc .venv\Scripts\activate  # Windows

# 3. Cài đặt với dev dependencies
pip install -e ".[dev,full]"

# 4. Cài pre-commit hooks
pre-commit install

# 5. Kiểm tra cài đặt
python -c "from kuromi_browser import Browser; print('OK')"
```

---

## 📁 Cấu Trúc Codebase

```
kuromi-browser/
├── kuromi_browser/           # 📦 Main package (100 files, 50 directories)
│   │
│   ├── __init__.py           # 🎯 Entry point - Export tất cả public APIs
│   ├── models.py             # 📊 Pydantic models (Fingerprint, Config, etc.)
│   ├── interfaces.py         # 🔌 Abstract base classes
│   ├── page.py               # 📄 High-level Page classes
│   │
│   ├── cdp/                  # 🔗 Chrome DevTools Protocol
│   │   ├── connection.py     #    WebSocket connection management
│   │   ├── session.py        #    CDP session per target
│   │   └── launcher.py       #    Browser process launcher
│   │
│   ├── browser/              # 🌐 Browser Management
│   │   ├── browser.py        #    Main Browser class
│   │   ├── context.py        #    BrowserContext (isolated sessions)
│   │   ├── tabs.py           #    TabManager
│   │   ├── profiles.py       #    ProfileManager (persistent data)
│   │   ├── windows.py        #    Window positioning/sizing
│   │   └── hooks.py          #    Lifecycle hooks
│   │
│   ├── session/              # 📡 HTTP Mode (curl_cffi)
│   │   ├── client.py         #    Session với TLS spoofing
│   │   ├── response.py       #    Response wrapper
│   │   └── element.py        #    SessionElement
│   │
│   ├── dom/                  # 🏗️ DOM Service
│   │   ├── service.py        #    DOM operations
│   │   ├── element.py        #    Element class
│   │   └── locator.py        #    CSS/XPath locators
│   │
│   ├── stealth/              # 🥷 Anti-Detection
│   │   ├── __init__.py       #    Stealth orchestration
│   │   ├── cdp/              #    CDP patches (Patchright techniques)
│   │   │   └── patches.py    #    JavaScript injection patches
│   │   ├── fingerprint/      #    Fingerprint generation
│   │   ├── behavior/         #    Human-like mouse/keyboard
│   │   └── tls/              #    TLS/JA3 impersonation
│   │
│   ├── actions/              # 🎮 User Actions
│   │   ├── mouse.py          #    MouseController
│   │   ├── keyboard.py       #    KeyboardController
│   │   ├── forms.py          #    FormHandler
│   │   ├── scroll.py         #    ScrollController
│   │   └── chain.py          #    ActionChain (fluent API)
│   │
│   ├── waiters/              # ⏳ Wait Conditions
│   │   ├── __init__.py       #    Waiter, ElementWaiter
│   │   └── conditions.py     #    30+ wait conditions
│   │
│   ├── network/              # 🌍 Network Layer
│   │   ├── monitor.py        #    NetworkMonitor
│   │   ├── filter.py         #    Request/Response filtering
│   │   ├── listener.py       #    Real-time streaming
│   │   ├── har.py            #    HAR export
│   │   └── interceptor.py    #    Request interception
│   │
│   ├── agent/                # 🤖 AI Agent
│   │   ├── agent.py          #    Agent class (LLM-powered)
│   │   └── actions.py        #    Agent actions
│   │
│   ├── ai/                   # 🧠 AI Integration
│   │   ├── dom_serializer.py #    DOM → LLM format
│   │   ├── vision.py         #    Screenshot analysis
│   │   └── task_parser.py    #    Natural language → Actions
│   │
│   ├── llm/                  # 💬 LLM Providers
│   │   ├── base.py           #    LLMProvider interface
│   │   ├── openai.py         #    OpenAI integration
│   │   └── anthropic.py      #    Anthropic integration
│   │
│   ├── events/               # 📢 Event System
│   │   ├── bus.py            #    EventBus singleton
│   │   └── types.py          #    Event types
│   │
│   ├── media/                # 📸 Media Handling
│   │   ├── screenshot.py     #    Screenshot capture
│   │   ├── recorder.py       #    Page recording
│   │   ├── pdf.py            #    PDF export
│   │   └── downloader.py     #    File downloads
│   │
│   ├── mcp/                  # 🔌 Model Context Protocol
│   │   ├── server.py         #    MCP server
│   │   └── tools.py          #    40+ MCP tools
│   │
│   ├── config/               # ⚙️ Configuration
│   │   ├── options.py        #    Config classes
│   │   └── defaults.py       #    Default values
│   │
│   └── plugins/              # 🧩 Plugin System
│       ├── base.py           #    Plugin interface
│       ├── loader.py         #    Plugin loader
│       └── builtin/          #    Built-in plugins
│
├── tests/                    # 🧪 Test Suite
├── docs/                     # 📚 Documentation
└── pyproject.toml            # 📦 Project config
```

---

## 🔄 Luồng Dữ Liệu

### 1. Browser Mode (CDP)

```
┌─────────────┐     WebSocket      ┌──────────────┐     CDP Protocol    ┌─────────────┐
│   Browser   │ ◄──────────────► │  CDPSession  │ ◄─────────────────► │   Chrome    │
│   (Python)  │                    │              │                      │  (Process)  │
└─────────────┘                    └──────────────┘                      └─────────────┘
      │                                   │
      │ new_page()                        │ Target.createTarget
      ▼                                   ▼
┌─────────────┐                    ┌──────────────┐
│    Page     │                    │   Tab/Page   │
│   Object    │                    │  (in Chrome) │
└─────────────┘                    └──────────────┘
```

**Chi tiết:**
1. `Browser` khởi tạo Chrome process với stealth args
2. `CDPConnection` kết nối qua WebSocket
3. `CDPSession` gửi commands (Page.navigate, DOM.querySelector, etc.)
4. Chrome xử lý và trả về kết quả

### 2. Session Mode (HTTP)

```
┌─────────────┐     curl_cffi      ┌──────────────┐     HTTPS/TLS      ┌─────────────┐
│   Session   │ ◄──────────────► │   Request    │ ◄─────────────────► │   Server    │
│   (Python)  │   TLS Spoofing    │   Builder    │   Chrome JA3       │             │
└─────────────┘                    └──────────────┘                      └─────────────┘
      │
      │ get(), post()
      ▼
┌─────────────┐
│  Response   │ ◄─── lxml parsing ◄─── HTML content
│   Object    │
└─────────────┘
```

**Chi tiết:**
1. `Session` sử dụng curl_cffi để giả lập TLS fingerprint
2. Request được gửi với JA3 giống Chrome thật
3. Response được parse bằng lxml để query elements

### 3. Stealth Mode Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Stealth Initialization                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. FingerprintGenerator.generate()                                     │
│     ├── Navigator properties (platform, vendor, languages)              │
│     ├── Screen (resolution, color depth)                                │
│     ├── WebGL (GPU info)                                                │
│     ├── Canvas noise seed                                               │
│     ├── Audio noise seed                                                │
│     ├── WebRTC (disabled/fake)                                          │
│     ├── Input leak protection (Patchright)                              │
│     └── UserAgentData (Client Hints)                                    │
│                                                                         │
│  2. get_stealth_chromium_args()                                         │
│     ├── --disable-blink-features=AutomationControlled                   │
│     └── Remove: --enable-automation, --disable-extensions               │
│                                                                         │
│  3. CDPPatches.apply_to_page()                                          │
│     ├── Page.addScriptToEvaluateOnNewDocument                           │
│     │   ├── WEBDRIVER_PATCH (hide navigator.webdriver)                  │
│     │   ├── CHROME_PATCHES (chrome.runtime, csi, loadTimes)             │
│     │   ├── CANVAS_NOISE_PATCH                                          │
│     │   ├── AUDIO_NOISE_PATCH                                           │
│     │   ├── WEBGL_PATCH                                                 │
│     │   ├── INPUT_LEAK_FIX_PATCH (Patchright)                           │
│     │   ├── COALESCED_EVENTS_PATCH                                      │
│     │   └── ... (27 patches total)                                      │
│     │                                                                   │
│     └── Emulation.setUserAgentOverride                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. AI Agent Flow

```
┌─────────────┐     Task      ┌──────────────┐     DOM Snapshot    ┌─────────────┐
│    User     │ ─────────────► │    Agent     │ ◄────────────────── │    Page     │
│   (Text)    │               │              │                      │             │
└─────────────┘               └──────────────┘                      └─────────────┘
                                    │                                     ▲
                                    │ Prompt + DOM                        │
                                    ▼                                     │
                              ┌──────────────┐                            │
                              │  LLMProvider │                            │
                              │  (OpenAI/    │                            │
                              │  Anthropic)  │                            │
                              └──────────────┘                            │
                                    │                                     │
                                    │ Action JSON                         │
                                    ▼                                     │
                              ┌──────────────┐     Execute      ──────────┘
                              │ AgentActions │ ─────────────────►
                              │ (click, type,│
                              │  scroll...)  │
                              └──────────────┘
```

---

## 📦 Dependencies

### Core Dependencies (Bắt buộc)

| Package | Phiên bản | Mục đích | Cách sử dụng |
|---------|-----------|----------|--------------|
| `websockets` | >=12.0 | CDP WebSocket | Kết nối đến Chrome DevTools |
| `httpx` | >=0.27.0 | HTTP client | Async HTTP requests |
| `lxml` | >=5.0.0 | HTML parsing | Parse HTML, query CSS/XPath |
| `pydantic` | >=2.0 | Data models | Validation, serialization |
| `curl_cffi` | >=0.6.0 | TLS spoofing | Giả lập JA3 fingerprint |

### Optional - LLM

| Package | Phiên bản | Mục đích |
|---------|-----------|----------|
| `openai` | >=1.0 | OpenAI GPT API |
| `anthropic` | >=0.18 | Claude API |

### Optional - Full Features

| Package | Phiên bản | Mục đích |
|---------|-----------|----------|
| `browserforge` | >=1.0 | Fingerprint từ Bayesian network |
| `Pillow` | >=10.0 | Image processing |

### Dev Dependencies

| Package | Phiên bản | Mục đích |
|---------|-----------|----------|
| `pytest` | >=8.0 | Testing framework |
| `pytest-asyncio` | >=0.23 | Async test support |
| `ruff` | >=0.3 | Linting + formatting |
| `pyright` | >=1.1 | Type checking |
| `pre-commit` | >=3.0 | Git hooks |

---

## 🔨 Quy Trình Phát Triển

### 1. Tạo Feature Branch

```bash
git checkout -b feature/ten-tinh-nang
```

### 2. Viết Tests Trước (TDD)

```bash
# Tạo file test
touch tests/test_ten_tinh_nang.py
```

```python
# tests/test_ten_tinh_nang.py
import pytest
from kuromi_browser import TenClass

class TestTenClass:
    def test_chuc_nang_co_ban(self):
        obj = TenClass()
        assert obj.method() == ket_qua_mong_doi

    @pytest.mark.asyncio
    async def test_async_method(self):
        obj = TenClass()
        result = await obj.async_method()
        assert result is not None
```

### 3. Implement Feature

```python
# kuromi_browser/module/ten_class.py
class TenClass:
    """Mô tả class.

    Example:
        obj = TenClass()
        result = obj.method()
    """

    def method(self) -> str:
        """Mô tả method.

        Returns:
            Kết quả
        """
        return "ket_qua"
```

### 4. Chạy Tests

```bash
# Chạy tất cả tests
pytest

# Chạy test cụ thể
pytest tests/test_ten_tinh_nang.py -v

# Với coverage
pytest --cov=kuromi_browser
```

### 5. Kiểm tra Code Quality

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
pyright kuromi_browser

# Chạy tất cả checks
pre-commit run --all-files
```

### 6. Commit

```bash
git add .
git commit -m "feat: thêm tính năng XYZ"
```

**Commit message format:**
- `feat:` Tính năng mới
- `fix:` Sửa bug
- `docs:` Documentation
- `refactor:` Refactoring
- `test:` Tests
- `chore:` Maintenance

---

## 🧪 Testing

### Cấu Trúc Tests

```
tests/
├── conftest.py              # Fixtures chung
├── test_models.py           # Test data models
├── test_browser.py          # Test browser management
├── test_cdp.py              # Test CDP connection
├── test_session.py          # Test HTTP session
├── test_stealth.py          # Test anti-detection
├── test_actions.py          # Test mouse/keyboard
├── test_network.py          # Test network layer
└── test_agent.py            # Test AI agent
```

### Fixtures (conftest.py)

```python
import pytest
from kuromi_browser import Browser, Fingerprint

@pytest.fixture
def fingerprint():
    """Fixture tạo fingerprint."""
    return Fingerprint()

@pytest.fixture
async def browser():
    """Fixture tạo browser."""
    async with Browser(headless=True) as b:
        yield b

@pytest.fixture
async def page(browser):
    """Fixture tạo page."""
    page = await browser.new_page()
    yield page
    await page.close()
```

### Chạy Tests Theo Loại

```bash
# Unit tests
pytest tests/test_models.py

# Integration tests
pytest tests/test_browser.py

# Async tests
pytest tests/test_cdp.py --asyncio-mode=auto

# Với markers
pytest -m "not slow"  # Bỏ qua slow tests
```

---

## 📝 Code Style

### Python Style Guidelines

1. **Type hints bắt buộc:**
```python
def fetch_data(
    url: str,
    *,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    ...
```

2. **Docstrings (Google style):**
```python
def method(self, param: str) -> bool:
    """Mô tả ngắn gọn.

    Mô tả chi tiết hơn nếu cần.

    Args:
        param: Mô tả parameter

    Returns:
        Mô tả giá trị trả về

    Raises:
        ValueError: Khi nào raise
    """
```

3. **Import order:**
```python
# Standard library
import asyncio
from typing import Any

# Third-party
import httpx
from pydantic import BaseModel

# Local
from kuromi_browser.models import Fingerprint
```

4. **Naming conventions:**
```python
# Classes: PascalCase
class BrowserManager:
    pass

# Functions/methods: snake_case
def get_browser_info():
    pass

# Constants: UPPER_CASE
MAX_RETRIES = 3

# Private: leading underscore
def _internal_method():
    pass
```

### Line Length

- Max 100 characters
- Exceptions: URLs, import statements

---

## 🆘 Hỗ Trợ

- **GitHub Issues:** https://github.com/kurom1ii/kuromi-browser/issues
- **Discussions:** https://github.com/kurom1ii/kuromi-browser/discussions
