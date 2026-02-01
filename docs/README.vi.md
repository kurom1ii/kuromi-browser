# Kuromi Browser - Tai lieu tieng Viet

> Thu vien tu dong hoa trinh duyet Python voi kha nang chong phat hien (anti-detection), tich hop AI/LLM, va che do kep ket hop CDP voi HTTP session.

## Gioi thieu

Kuromi Browser la mot thu vien Python manh me danh cho tu dong hoa trinh duyet, ket hop uu diem cua:

- **Browser-Use**: Tu dong hoa trinh duyet bang AI/LLM
- **DrissionPage**: Dieu khien trinh duyet che do kep (Browser + HTTP)

### Tinh nang noi bat

- **Che do kep**: Ket hop Browser (CDP) va Session (HTTP) trong mot API
- **AI Agent**: Tich hop LLM de tu dong hoa thong minh
- **Stealth Mode**: Chong phat hien bot va gia mao fingerprint
- **API don gian**: Cu phap kieu DrissionPage, de su dung
- **Async-First**: Ho tro async/await native
- **Event-Driven**: He thong watchdog mo rong

## Cai dat

```bash
pip install kuromi-browser
```

### Cai dat tuy chon

```bash
# Voi ho tro LLM
pip install kuromi-browser[llm]

# Voi TLS impersonation
pip install kuromi-browser[tls]

# Day du tinh nang
pip install kuromi-browser[all]
```

## Su dung nhanh

### Che do don gian

```python
from kuromi_browser import Page

page = Page()
page.get('https://example.com')
page.ele('#button').click()
print(page.ele('.content').text)
```

### Che do Stealth

```python
from kuromi_browser import StealthPage

page = StealthPage()  # Tu dong fingerprint + CDP patches
page.get('https://protected-site.com')
```

### Che do AI

```python
from kuromi_browser import Agent
from kuromi_browser.llm import OpenAI

agent = Agent(llm=OpenAI())
result = await agent.run("Tim kiem Python tutorials tren Google")
print(result)
```

### Che do Hybrid

```python
from kuromi_browser import HybridPage

page = HybridPage()
# HTTP request nhanh
data = page.session.get('https://api.example.com/data').json()
# Browser cho tuong tac phuc tap
page.browser.get('https://example.com')
page.browser.ele('#submit').click()
```

## Tai lieu chi tiet

- [Huong dan bat dau](getting-started.md) - Cai dat va su dung co ban
- [Kien truc project](architecture.md) - Cau truc va thiet ke
- [API Reference](api-reference.md) - Tham khao API chi tiet
- [Huong dan Stealth](stealth-guide.md) - Chong phat hien va fingerprint

## Dong gop

Chung toi hoan nghenh moi dong gop! Vui long doc [CONTRIBUTING.md](../CONTRIBUTING.md) de biet them chi tiet.

## Giay phep

MIT License - xem [LICENSE](../LICENSE) de biet them chi tiet.
