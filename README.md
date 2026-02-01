# Kuromi Browser 🦊

> Stealthy Python browser automation library combining the best of Browser-Use (AI/LLM) and DrissionPage (dual-mode) with CDP stealth & fingerprint bypass.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- **Dual Mode**: Browser (CDP) + Session (HTTP) in one API
- **AI-Powered**: Optional LLM integration for intelligent automation
- **Stealth Mode**: Built-in anti-detection & fingerprint spoofing
- **Simple API**: DrissionPage-style syntax for ease of use
- **Async-First**: Native async/await support
- **Event-Driven**: Extensible watchdog system

## 🚀 Quick Start

### Simple Mode (like DrissionPage)
```python
from kuromi_browser import Page

page = Page()
page.get('https://example.com')
page.ele('#button').click()
print(page.ele('.content').text)
```

### Stealth Mode
```python
from kuromi_browser import StealthPage

page = StealthPage()  # Auto fingerprint + CDP patches
page.get('https://protected-site.com')
```

### AI Mode (like Browser-Use)
```python
from kuromi_browser import Agent
from kuromi_browser.llm import OpenAI

agent = Agent(llm=OpenAI())
result = await agent.run("Search for Python tutorials on Google")
print(result)
```

### Dual Mode
```python
from kuromi_browser import HybridPage

page = HybridPage()
# Fast HTTP requests
data = page.session.get('https://api.example.com/data').json()
# Browser for complex interactions
page.browser.get('https://example.com')
page.browser.ele('#submit').click()
```

## 📦 Installation

```bash
pip install kuromi-browser
```

## 🏗️ Architecture

```
kuromi_browser/
├── cdp/           # CDP client & browser management
├── dom/           # Element locators & DOM service
├── session/       # HTTP mode with TLS impersonation
├── events/        # Event bus system
├── watchdogs/     # Monitoring services
├── llm/           # LLM provider integrations
├── agent/         # AI agent system
├── stealth/       # Anti-detection & fingerprint
│   ├── cdp/       # CDP patches
│   ├── fingerprint/  # Fingerprint generator
│   ├── behavior/  # Human-like actions
│   └── tls/       # TLS/JA3 impersonation
└── network/       # Network monitoring
```

## 🛡️ Anti-Detection Features

### CDP Stealth
- Patch `navigator.webdriver`
- Hide automation traces
- Sandbox page agent code

### Fingerprint Spoofing
- Navigator properties
- WebGL/Canvas/Audio
- Screen/Viewport
- Market share distribution (via BrowserForge)

### TLS Impersonation
- JA3 fingerprint matching
- Browser TLS profiles (Chrome, Firefox, Safari)
- HTTP/2 fingerprint

### Human-like Behavior
- Bezier curve mouse movement
- Natural typing patterns
- Realistic scroll behavior

## 📚 Documentation

- [Getting Started](docs/getting-started.md)
- [API Reference](docs/api-reference.md)
- [Stealth Guide](docs/stealth-guide.md)
- [AI Agent Guide](docs/agent-guide.md)

## 🔗 References

This project is inspired by and references:

### Python
- [Browser-Use](https://github.com/browser-use/browser-use) - AI browser automation
- [DrissionPage](https://github.com/g1879/DrissionPage) - Dual-mode browser control
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) - Selenium stealth
- [Camoufox](https://github.com/daijro/camoufox) - Firefox anti-detect
- [BrowserForge](https://github.com/daijro/browserforge) - Fingerprint generator
- [curl_cffi](https://github.com/lexiforest/curl_cffi) - TLS impersonation
- [Patchright-Python](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) - Playwright undetected
- [Zendriver](https://github.com/cdpdriver/zendriver) - Async nodriver fork

### JavaScript
- [Puppeteer-Extra](https://github.com/berstend/puppeteer-extra) - Plugin ecosystem
- [Rebrowser-Patches](https://github.com/rebrowser/rebrowser-patches) - CDP patches
- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) - Playwright undetected

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with ❤️ by Kuromi
