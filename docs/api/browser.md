# Browser API Reference

API cho quan ly Browser trong Kuromi Browser.

## Tong Quan

Browser class quan ly browser process va cung cap methods de tao pages/contexts moi.

## Browser

### Constructor

```python
from kuromi_browser import Browser, BrowserConfig

# Mac dinh
browser = Browser()

# Voi config
config = BrowserConfig(
    headless=True,
    stealth=True,
)
browser = Browser(config=config)
```

### Context Manager

```python
async with Browser() as browser:
    page = await browser.new_page()
    await page.goto("https://example.com")
# Browser tu dong dong khi thoat
```

### Properties

#### is_connected

Kiem tra browser con ket noi khong.

```python
if browser.is_connected:
    print("Browser dang hoat dong")
```

#### contexts

Lay danh sach browser contexts.

```python
contexts = browser.contexts
for ctx in contexts:
    print(f"Context co {len(ctx.pages)} pages")
```

### Methods

#### new_context(**options)

Tao browser context moi (isolated session).

```python
from kuromi_browser import PageConfig, Fingerprint

context = await browser.new_context(
    config=PageConfig(
        viewport={"width": 1920, "height": 1080},
    ),
    fingerprint=Fingerprint(),
)

# Tao page trong context
page = await context.new_page()
```

**Tham so:**
- `config` (PageConfig, optional): Cau hinh page
- `fingerprint` (Fingerprint, optional): Fingerprint config

**Tra ve:** `BrowserContext`

#### new_page(**options)

Tao page moi trong default context.

```python
page = await browser.new_page(
    config=PageConfig(timeout=60000),
    fingerprint=Fingerprint(),
)
```

**Tham so:**
- `config` (PageConfig, optional): Cau hinh page
- `fingerprint` (Fingerprint, optional): Fingerprint config

**Tra ve:** `Page`

#### version()

Lay version cua browser.

```python
version = await browser.version()
# "Chrome/120.0.6099.129"
```

#### close()

Dong browser.

```python
await browser.close()
```

## BrowserContext

Browser context la session co lap voi cookies, storage, va settings rieng.

### Properties

#### browser

Lay parent browser.

```python
parent = context.browser
```

#### pages

Lay danh sach pages trong context.

```python
pages = context.pages
for page in pages:
    print(page.url)
```

### Methods

#### new_page(**options)

Tao page moi trong context nay.

```python
page = await context.new_page(
    config=PageConfig(),
)
```

#### get_cookies(*urls)

Lay cookies cua context.

```python
# Tat ca cookies
cookies = await context.get_cookies()

# Cookies cho URL cu the
cookies = await context.get_cookies("https://example.com")
```

#### set_cookies(*cookies)

Dat cookies cho context.

```python
from kuromi_browser import Cookie

await context.set_cookies(
    Cookie(name="session", value="abc123", domain="example.com"),
    Cookie(name="user", value="john", domain="example.com"),
)
```

#### clear_cookies()

Xoa tat ca cookies.

```python
await context.clear_cookies()
```

#### add_init_script(script)

Them script chay tren moi page moi.

```python
await context.add_init_script("""
    // Script nay chay truoc moi page script khac
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
""")
```

#### expose_function(name, callback)

Expose Python function cho tat ca pages.

```python
def my_function(x, y):
    return x + y

await context.expose_function("myFunction", my_function)

# Trong JavaScript cua moi page:
# window.myFunction(1, 2) => 3
```

#### route(url, handler)

Intercept network requests cho tat ca pages.

```python
async def block_images(request):
    if request.resource_type == "image":
        return None  # Block
    return request  # Cho phep

await context.route("**/*", block_images)
```

#### unroute(url)

Xoa route handler.

```python
await context.unroute("**/*")
```

#### set_geolocation(latitude, longitude, **options)

Dat geolocation.

```python
await context.set_geolocation(
    latitude=40.7128,
    longitude=-74.0060,
    accuracy=100,
)
```

#### set_permissions(permissions, **options)

Dat permissions.

```python
await context.set_permissions(
    ["geolocation", "notifications"],
    origin="https://example.com",
)
```

#### close()

Dong context va tat ca pages.

```python
await context.close()
```

## CDPSession

Chrome DevTools Protocol session cho low-level control.

### Lay CDPSession

```python
# Tu page
cdp = await page.context.new_cdp_session(page)

# Hoac tu browser
cdp = await browser.new_cdp_session()
```

### send(method, params)

Gui CDP command.

```python
# Lay document
result = await cdp.send("DOM.getDocument")
root = result["root"]

# Chup screenshot
screenshot = await cdp.send("Page.captureScreenshot", {
    "format": "png",
    "quality": 80,
})

# Enable network
await cdp.send("Network.enable")
```

### on(event, handler)

Dang ky CDP event handler.

```python
def on_request(params):
    print(f"Request: {params['request']['url']}")

cdp.on("Network.requestWillBeSent", on_request)
```

### off(event, handler)

Xoa event handler.

```python
cdp.off("Network.requestWillBeSent", on_request)
```

### detach()

Detach tu CDP session.

```python
await cdp.detach()
```

## Vi Du

### Multiple Contexts

```python
async def multi_context_example():
    async with Browser() as browser:
        # Context 1 - User A
        ctx1 = await browser.new_context()
        page1 = await ctx1.new_page()
        await page1.goto("https://example.com")
        await page1.fill("#username", "userA")

        # Context 2 - User B (isolated)
        ctx2 = await browser.new_context()
        page2 = await ctx2.new_page()
        await page2.goto("https://example.com")
        await page2.fill("#username", "userB")

        # Moi context co cookies rieng
        cookies1 = await ctx1.get_cookies()
        cookies2 = await ctx2.get_cookies()

        await ctx1.close()
        await ctx2.close()
```

### Stealth Browser

```python
from kuromi_browser import Browser, BrowserConfig, Fingerprint

async def stealth_example():
    config = BrowserConfig(
        headless=True,
        stealth=True,
        args=["--disable-blink-features=AutomationControlled"],
    )

    fingerprint = Fingerprint()

    async with Browser(config=config) as browser:
        page = await browser.new_page(fingerprint=fingerprint)

        # Page da co stealth patches
        await page.goto("https://bot.sannysoft.com")
        await page.screenshot(path="stealth_test.png")
```

### CDP Commands

```python
async def cdp_example():
    async with Browser() as browser:
        page = await browser.new_page()
        cdp = await page.context.new_cdp_session(page)

        # Enable Performance
        await cdp.send("Performance.enable")

        await page.goto("https://example.com")

        # Lay metrics
        metrics = await cdp.send("Performance.getMetrics")
        for metric in metrics["metrics"]:
            print(f"{metric['name']}: {metric['value']}")

        await cdp.detach()
```

## Tiep Theo

- [Page API](./page.md) - Page methods
- [Element API](./element.md) - Element interactions
- [CDP Protocol](../advanced/cdp.md) - Low-level CDP
