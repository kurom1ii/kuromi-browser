# Huong Dan Bat Dau

Tai lieu huong dan cai dat va su dung co ban Kuromi Browser.

## Yeu Cau He Thong

- Python 3.10 tro len
- Chrome/Chromium browser (cho che do browser)
- Ket noi internet

## Cai Dat

### Cai dat co ban

```bash
pip install kuromi-browser
```

### Cai dat day du (bao gom LLM support)

```bash
pip install kuromi-browser[full]
```

### Cai dat cho development

```bash
pip install kuromi-browser[dev]
```

### Dependencies

| Package | Mo ta | Bat buoc |
|---------|-------|----------|
| websockets | CDP WebSocket client | Co |
| httpx | HTTP client | Co |
| lxml | HTML parser | Co |
| pydantic | Data validation | Co |
| curl_cffi | TLS fingerprinting | Co |
| openai | OpenAI LLM | Khong (llm) |
| anthropic | Claude LLM | Khong (llm) |
| browserforge | Fingerprint generator | Khong (full) |
| Pillow | Image processing | Khong (full) |

## Su Dung Co Ban

### Che Do Don Gian (giong DrissionPage)

```python
import asyncio
from kuromi_browser import Page

async def main():
    page = Page()
    await page.goto('https://example.com')

    # Tim va click element
    button = await page.query_selector('#submit-button')
    await button.click()

    # Lay noi dung text
    content = await page.query_selector('.content')
    print(await content.text_content())

    await page.close()

asyncio.run(main())
```

### Che Do Stealth (Anti-Detection)

```python
import asyncio
from kuromi_browser import StealthPage, Fingerprint

async def main():
    # Tao fingerprint tu dong
    fingerprint = Fingerprint()

    # Tao page voi stealth mode
    page = StealthPage(fingerprint=fingerprint)

    # Truy cap trang web co bot protection
    await page.goto('https://protected-site.com')

    # Stealth patches duoc ap dung tu dong
    await page.apply_stealth()

    await page.close()

asyncio.run(main())
```

### Che Do Hybrid (HTTP + Browser)

```python
import asyncio
from kuromi_browser import HybridPage

async def main():
    page = HybridPage()

    # Su dung HTTP session (nhanh hon)
    response = await page.fetch('https://api.example.com/data')
    data = response.json()

    # Chuyen sang browser khi can JavaScript
    await page.goto('https://example.com/js-app')
    await page.click('#dynamic-button')

    # Dong bo cookies giua session va browser
    await page.sync_cookies_to_session()

    await page.close()

asyncio.run(main())
```

### Che Do AI Agent (giong Browser-Use)

```python
import asyncio
from kuromi_browser import Agent, Browser

async def main():
    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)

        # Yeu cau agent thuc hien task
        result = await agent.run(
            "Tim kiem 'Python tutorial' tren Google va click ket qua dau tien"
        )

        print(result)

asyncio.run(main())
```

## Cau Truc Du An

```
kuromi_browser/
├── __init__.py          # Main exports
├── models.py            # Data models (Fingerprint, Cookie, etc.)
├── interfaces.py        # Abstract base classes
├── page.py              # Page, StealthPage, HybridPage
├── cdp/                 # Chrome DevTools Protocol
│   ├── connection.py    # WebSocket connection
│   ├── session.py       # CDP session management
│   └── launcher.py      # Chrome launcher
├── dom/                 # DOM handling
├── session/             # HTTP session (curl_cffi)
├── events/              # Event system
│   ├── bus.py           # Event bus
│   └── types.py         # Event types
├── stealth/             # Anti-detection
│   ├── cdp/             # CDP patches
│   ├── fingerprint/     # Fingerprint generation
│   ├── behavior/        # Human-like behavior
│   │   ├── mouse.py     # Mouse movements
│   │   └── keyboard.py  # Typing patterns
│   └── tls/             # TLS/JA3 spoofing
├── agent/               # AI agent
├── watchdogs/           # Monitoring services
└── network/             # Network utilities
```

## Tiep Theo

- [Cau Hinh](./configuration.md) - Tim hieu cac tuy chon cau hinh
- [Page API](./api/page.md) - API day du cua Page
- [Stealth Guide](./stealth-guide.md) - Huong dan anti-detection
