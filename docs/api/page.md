# Page API Reference

API day du cho cac lop Page trong Kuromi Browser.

## Page Classes

Kuromi Browser cung cap 3 loai Page:

| Class | Mo ta | Su dung |
|-------|-------|---------|
| `Page` | CDP-based browser page | Automation thong thuong |
| `StealthPage` | Page voi anti-detection | Trang co bot protection |
| `HybridPage` | Browser + HTTP session | Toi uu performance |

## Page

### Constructor

```python
from kuromi_browser import Page
from kuromi_browser.cdp import CDPSession

page = Page(
    cdp_session=cdp_session,  # CDPSession instance
    config=page_config,        # Optional PageConfig
)
```

### Properties

#### url

Lay URL hien tai cua trang.

```python
current_url = page.url
# "https://example.com/path"
```

#### title

Lay title cua trang.

```python
page_title = page.title
# "Example Domain"
```

#### mode

Lay che do hoat dong cua page.

```python
from kuromi_browser import PageMode

mode = page.mode
# PageMode.BROWSER
```

### Navigation Methods

#### goto(url, **options)

Di chuyen den URL.

```python
response = await page.goto(
    "https://example.com",
    timeout=30000,           # Timeout (ms)
    wait_until="load",       # "load", "domcontentloaded", "networkidle"
    referer="https://google.com",  # Referer header
)
```

**Tham so:**
- `url` (str): URL can di chuyen
- `timeout` (float, optional): Timeout tinh bang ms
- `wait_until` (str): Trang thai cho doi
- `referer` (str, optional): Referer header

**Tra ve:** `NetworkResponse` hoac `None`

#### reload(**options)

Tai lai trang hien tai.

```python
response = await page.reload(
    timeout=30000,
    wait_until="load",
)
```

#### go_back(**options)

Di chuyen lui trong history.

```python
response = await page.go_back(
    timeout=30000,
    wait_until="load",
)
```

#### go_forward(**options)

Di chuyen toi trong history.

```python
response = await page.go_forward(
    timeout=30000,
    wait_until="load",
)
```

### Content Methods

#### content()

Lay HTML content cua trang.

```python
html = await page.content()
# "<!DOCTYPE html><html>..."
```

#### set_content(html, **options)

Dat HTML content cho trang.

```python
await page.set_content(
    "<html><body><h1>Hello</h1></body></html>",
    timeout=30000,
    wait_until="load",
)
```

### Selector Methods

#### query_selector(selector)

Tim mot element theo CSS selector.

```python
element = await page.query_selector("#main-content")
if element:
    text = await element.text_content()
```

**Tham so:**
- `selector` (str): CSS selector

**Tra ve:** `Element` hoac `None`

#### query_selector_all(selector)

Tim tat ca elements theo CSS selector.

```python
elements = await page.query_selector_all(".item")
for element in elements:
    print(await element.text_content())
```

**Tra ve:** `list[Element]`

### Wait Methods

#### wait_for_selector(selector, **options)

Cho doi element xuat hien.

```python
element = await page.wait_for_selector(
    "#dynamic-content",
    state="visible",     # "attached", "detached", "visible", "hidden"
    timeout=10000,
)
```

**Tham so:**
- `selector` (str): CSS selector
- `state` (str): Trang thai cho doi
- `timeout` (float, optional): Timeout

**Tra ve:** `Element` hoac `None`

#### wait_for_load_state(state, **options)

Cho doi trang dat trang thai.

```python
await page.wait_for_load_state(
    "networkidle",  # "load", "domcontentloaded", "networkidle"
    timeout=30000,
)
```

#### wait_for_url(url, **options)

Cho doi navigation den URL.

```python
# Cho doi URL chinh xac
await page.wait_for_url("https://example.com/success")

# Cho doi URL matching function
await page.wait_for_url(
    lambda url: "success" in url,
    timeout=10000,
)
```

#### wait_for_timeout(timeout)

Cho doi mot khoang thoi gian.

```python
await page.wait_for_timeout(2000)  # 2 giay
```

### Interaction Methods

#### click(selector, **options)

Click vao element.

```python
await page.click(
    "#submit-button",
    button="left",        # "left", "right", "middle"
    click_count=1,        # So lan click
    delay=100,            # Delay giua cac click (ms)
    force=False,          # Bo qua actionability checks
    modifiers=["Shift"],  # Modifier keys
    position={"x": 10, "y": 10},  # Vi tri click
    timeout=30000,
)
```

#### dblclick(selector, **options)

Double-click vao element.

```python
await page.dblclick("#editable-text")
```

#### fill(selector, value, **options)

Dien gia tri vao input field.

```python
await page.fill(
    "#username",
    "myusername",
    force=False,
    timeout=30000,
)
```

#### type(selector, text, **options)

Go text tung ky tu (co delay).

```python
await page.type(
    "#search-input",
    "search query",
    delay=50,  # Delay giua moi ky tu (ms)
    timeout=30000,
)
```

#### press(selector, key, **options)

Nhan phim khi focus vao element.

```python
await page.press("#input", "Enter")
await page.press("#input", "Control+A")
```

#### hover(selector, **options)

Di chuyen chuot den element.

```python
await page.hover(
    "#dropdown-trigger",
    force=False,
    modifiers=None,
    position=None,
    timeout=30000,
)
```

#### select_option(selector, *values, **options)

Chon options trong select element.

```python
selected = await page.select_option(
    "#country-select",
    "us", "uk",  # Values hoac labels
    timeout=30000,
)
```

**Tra ve:** `list[str]` - Cac values da chon

#### check(selector, **options)

Check checkbox hoac radio button.

```python
await page.check("#agree-checkbox")
```

#### uncheck(selector, **options)

Uncheck checkbox.

```python
await page.uncheck("#newsletter-checkbox")
```

### JavaScript Execution

#### evaluate(expression, *args)

Chay JavaScript trong context cua trang.

```python
# Expression don gian
title = await page.evaluate("document.title")

# Function voi arguments
result = await page.evaluate(
    "(a, b) => a + b",
    5, 10,
)  # 15

# Lay du lieu phuc tap
data = await page.evaluate("""
    () => {
        return {
            title: document.title,
            url: window.location.href,
            links: Array.from(document.querySelectorAll('a')).map(a => a.href)
        }
    }
""")
```

#### evaluate_handle(expression, *args)

Chay JavaScript va tra ve handle den object.

```python
handle = await page.evaluate_handle("document.body")
```

#### add_script_tag(**options)

Them script tag vao trang.

```python
# Tu URL
await page.add_script_tag(url="https://cdn.example.com/script.js")

# Tu file local
await page.add_script_tag(path="/path/to/script.js")

# Tu noi dung
await page.add_script_tag(content="console.log('Hello')")
```

#### add_style_tag(**options)

Them style tag vao trang.

```python
await page.add_style_tag(content="body { background: red; }")
```

### Screenshot & PDF

#### screenshot(**options)

Chup anh man hinh.

```python
# Luu vao file
await page.screenshot(path="screenshot.png")

# Lay bytes
screenshot_bytes = await page.screenshot(
    full_page=True,           # Chup ca trang
    type="png",               # "png", "jpeg"
    quality=80,               # Chi cho jpeg
    omit_background=True,     # Background trong suot
)

# Chup vung cu the
await page.screenshot(
    clip={"x": 0, "y": 0, "width": 500, "height": 500}
)
```

#### pdf(**options)

Tao PDF tu trang (chi headless).

```python
pdf_bytes = await page.pdf(
    path="document.pdf",
    scale=1,
    display_header_footer=True,
    header_template="<span>Header</span>",
    footer_template="<span>Page <span class='pageNumber'></span></span>",
    print_background=True,
    landscape=False,
    page_ranges="1-5",
    format="A4",           # hoac width/height
    margin={"top": "1cm", "bottom": "1cm"},
)
```

### Cookie Management

#### get_cookies(*urls)

Lay cookies.

```python
cookies = await page.get_cookies()
cookies = await page.get_cookies("https://example.com")
```

**Tra ve:** `list[Cookie]`

#### set_cookies(*cookies)

Dat cookies.

```python
from kuromi_browser import Cookie

await page.set_cookies(
    Cookie(
        name="session_id",
        value="abc123",
        domain="example.com",
        path="/",
        secure=True,
        http_only=True,
    )
)
```

#### delete_cookies(*names)

Xoa cookies theo ten.

```python
await page.delete_cookies("session_id", "tracking_id")
```

#### clear_cookies()

Xoa tat ca cookies.

```python
await page.clear_cookies()
```

### Headers & Viewport

#### set_extra_http_headers(headers)

Dat them HTTP headers.

```python
await page.set_extra_http_headers({
    "X-Custom-Header": "value",
    "Accept-Language": "vi-VN",
})
```

#### set_viewport(width, height, **options)

Dat kich thuoc viewport.

```python
await page.set_viewport(
    1920, 1080,
    device_scale_factor=2,
    is_mobile=False,
    has_touch=False,
)
```

### Event Handling

#### on(event, handler)

Dang ky event handler.

```python
def on_console(message):
    print(f"Console: {message}")

page.on("console", on_console)
```

**Cac events:**
- `console` - Console messages
- `dialog` - Alert/confirm/prompt dialogs
- `request` - Network requests
- `response` - Network responses
- `load` - Page load
- `domcontentloaded` - DOM ready
- `error` - Page errors

#### off(event, handler)

Xoa event handler.

```python
page.off("console", on_console)
```

### Network Interception

#### route(url, handler)

Chan va xu ly network requests.

```python
async def handle_request(request):
    if "ads" in request.url:
        return None  # Block request
    return request  # Cho phep

await page.route("**/*", handle_request)
```

#### unroute(url)

Xoa route handler.

```python
await page.unroute("**/*")
```

### Misc

#### expose_function(name, callback)

Expose Python function cho JavaScript.

```python
def compute(x, y):
    return x * y

await page.expose_function("compute", compute)

# Trong JavaScript:
# window.compute(5, 10) => 50
```

#### close()

Dong page.

```python
await page.close()
```

---

## StealthPage

Extends `Page` voi cac tinh nang anti-detection.

### Constructor

```python
from kuromi_browser import StealthPage, Fingerprint

page = StealthPage(
    cdp_session=cdp_session,
    fingerprint=Fingerprint(),  # Optional
    config=page_config,
)
```

### Additional Properties

#### fingerprint

Lay fingerprint hien tai.

```python
fp = page.fingerprint
```

#### stealth_enabled

Kiem tra stealth mode.

```python
is_stealth = page.stealth_enabled  # True
```

### Additional Methods

#### apply_stealth()

Ap dung cac stealth patches.

```python
await page.apply_stealth()
```

#### set_fingerprint(fingerprint)

Dat fingerprint moi.

```python
new_fingerprint = Fingerprint(
    user_agent="Custom UA",
    navigator=NavigatorProperties(platform="Win32"),
)
await page.set_fingerprint(new_fingerprint)
```

---

## HybridPage

Ket hop Browser va HTTP Session.

### Constructor

```python
from kuromi_browser import HybridPage
from kuromi_browser.session import Session

page = HybridPage(
    cdp_session=cdp_session,
    session=Session(),
    fingerprint=fingerprint,
    config=config,
)
```

### Additional Properties

#### session

Lay HTTP session.

```python
http_session = page.session
```

### Additional Methods

#### fetch(url, **options)

Thuc hien HTTP request (nhanh hon browser).

```python
response = await page.fetch(
    "https://api.example.com/data",
    method="POST",
    headers={"Content-Type": "application/json"},
    json={"key": "value"},
    use_browser_cookies=True,
)

data = response.json()
```

#### sync_cookies_to_session()

Copy cookies tu browser sang HTTP session.

```python
await page.sync_cookies_to_session()
```

#### sync_cookies_to_browser()

Copy cookies tu HTTP session sang browser.

```python
await page.sync_cookies_to_browser()
```

---

## Tiep Theo

- [Element API](./element.md) - Chi tiet ve Element
- [Session API](./session.md) - HTTP Session API
- [Browser API](./browser.md) - Browser management
