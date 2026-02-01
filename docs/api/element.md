# Element API Reference

API day du cho lop Element trong Kuromi Browser.

## Element

Dai dien cho mot DOM element tren trang web.

### Properties

#### tag_name

Lay ten tag cua element.

```python
tag = element.tag_name
# "div", "a", "button", etc.
```

### Attribute Methods

#### get_attribute(name)

Lay gia tri attribute.

```python
href = await element.get_attribute("href")
class_name = await element.get_attribute("class")
data_id = await element.get_attribute("data-id")
```

**Tham so:**
- `name` (str): Ten attribute

**Tra ve:** `str` hoac `None`

#### get_property(name)

Lay JavaScript property.

```python
# Property khac voi attribute
checked = await element.get_property("checked")  # bool
value = await element.get_property("value")      # str
```

### Content Methods

#### text_content()

Lay text content (bao gom cac child elements).

```python
text = await element.text_content()
# "Hello World"
```

**Tra ve:** `str` hoac `None`

#### inner_text()

Lay visible inner text.

```python
text = await element.inner_text()
# "Visible Text Only"
```

#### inner_html()

Lay inner HTML.

```python
html = await element.inner_html()
# "<span>Child content</span>"
```

#### outer_html()

Lay outer HTML (bao gom ca element).

```python
html = await element.outer_html()
# "<div class='container'><span>Child content</span></div>"
```

### Position & Visibility

#### bounding_box()

Lay bounding box cua element.

```python
box = await element.bounding_box()
if box:
    print(f"Position: ({box['x']}, {box['y']})")
    print(f"Size: {box['width']} x {box['height']}")
```

**Tra ve:**
```python
{
    "x": 100,      # Left position
    "y": 200,      # Top position
    "width": 300,  # Width
    "height": 50,  # Height
}
```

#### is_visible()

Kiem tra element co visible khong.

```python
visible = await element.is_visible()
# True / False
```

#### is_enabled()

Kiem tra element co enabled khong.

```python
enabled = await element.is_enabled()
# True / False
```

#### is_checked()

Kiem tra checkbox/radio co checked khong.

```python
checked = await element.is_checked()
# True / False
```

### Interaction Methods

#### click(**options)

Click vao element.

```python
await element.click(
    button="left",        # "left", "right", "middle"
    click_count=1,        # So lan click
    delay=0,              # Delay giua cac click (ms)
    force=False,          # Bo qua actionability checks
    modifiers=None,       # ["Alt", "Control", "Meta", "Shift"]
    position=None,        # {"x": 10, "y": 10} - relative position
    timeout=30000,
)
```

**Options:**
| Option | Type | Mo ta |
|--------|------|-------|
| `button` | str | Button de click |
| `click_count` | int | So lan click |
| `delay` | float | Delay giua clicks (ms) |
| `force` | bool | Bo qua visibility check |
| `modifiers` | list | Modifier keys |
| `position` | dict | Vi tri click trong element |
| `timeout` | float | Timeout (ms) |

#### dblclick(**options)

Double-click vao element.

```python
await element.dblclick(
    button="left",
    delay=0,
    force=False,
    modifiers=None,
    position=None,
    timeout=30000,
)
```

#### hover(**options)

Di chuyen chuot den element.

```python
await element.hover(
    force=False,
    modifiers=None,
    position=None,
    timeout=30000,
)
```

#### fill(value, **options)

Dien gia tri vao input field. Clear noi dung cu truoc.

```python
await element.fill(
    "new value",
    force=False,
    timeout=30000,
)
```

**Luu y:** `fill()` se xoa noi dung hien tai truoc khi dien.

#### type(text, **options)

Go text tung ky tu. Khong xoa noi dung cu.

```python
await element.type(
    "hello world",
    delay=50,       # Delay giua cac ky tu (ms)
    timeout=30000,
)
```

**Luu y:** `type()` mo phong nguoi dung go phim.

#### press(key, **options)

Nhan phim.

```python
# Phim don
await element.press("Enter")
await element.press("Tab")
await element.press("Escape")

# To hop phim
await element.press("Control+A")
await element.press("Control+C")
await element.press("Shift+Tab")
```

**Phim ho tro:**
- `Enter`, `Tab`, `Escape`, `Backspace`, `Delete`
- `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`
- `Home`, `End`, `PageUp`, `PageDown`
- `F1` - `F12`
- Modifiers: `Control`, `Shift`, `Alt`, `Meta`

#### select_option(*values, **options)

Chon options trong select element.

```python
# Chon theo value
selected = await element.select_option("option1", "option2")

# Tra ve cac values da chon
print(selected)  # ["option1", "option2"]
```

#### check(**options)

Check checkbox hoac radio button.

```python
await element.check(
    force=False,
    timeout=30000,
)
```

#### uncheck(**options)

Uncheck checkbox.

```python
await element.uncheck(
    force=False,
    timeout=30000,
)
```

#### focus()

Focus vao element.

```python
await element.focus()
```

#### scroll_into_view()

Scroll element vao vung nhin.

```python
await element.scroll_into_view()
```

### Screenshot

#### screenshot(**options)

Chup anh element.

```python
# Luu vao file
await element.screenshot(path="element.png")

# Lay bytes
screenshot_bytes = await element.screenshot(
    type="png",           # "png", "jpeg"
    quality=80,           # Chi cho jpeg
    omit_background=True, # Background trong suot
)
```

### Child Elements

#### query_selector(selector)

Tim child element.

```python
child = await element.query_selector(".child-class")
if child:
    await child.click()
```

#### query_selector_all(selector)

Tim tat ca child elements.

```python
children = await element.query_selector_all("li")
for child in children:
    print(await child.text_content())
```

### JavaScript Evaluation

#### evaluate(expression, *args)

Chay JavaScript voi element la `this`.

```python
# Lay style
color = await element.evaluate("el => getComputedStyle(el).color")

# Scroll element
await element.evaluate("el => el.scrollTop = 100")

# Lay attribute phuc tap
data = await element.evaluate("""
    el => ({
        text: el.textContent,
        rect: el.getBoundingClientRect(),
        classes: Array.from(el.classList)
    })
""")
```

---

## Vi Du Su Dung

### Form Handling

```python
async def fill_form(page):
    # Dien form
    await page.fill("#first-name", "Nguyen")
    await page.fill("#last-name", "Van A")
    await page.fill("#email", "example@email.com")

    # Chon option
    await page.select_option("#country", "vn")

    # Check terms
    await page.check("#agree-terms")

    # Submit
    await page.click("#submit-button")
```

### Table Data Extraction

```python
async def extract_table(page):
    rows = await page.query_selector_all("table tbody tr")

    data = []
    for row in rows:
        cells = await row.query_selector_all("td")
        row_data = []
        for cell in cells:
            text = await cell.text_content()
            row_data.append(text)
        data.append(row_data)

    return data
```

### Dynamic Content Waiting

```python
async def wait_for_content(page):
    # Cho doi element xuat hien
    element = await page.wait_for_selector(
        "#dynamic-content",
        state="visible",
        timeout=10000,
    )

    if element:
        # Doc noi dung
        content = await element.text_content()
        return content
    else:
        raise TimeoutError("Content khong xuat hien")
```

### Drag and Drop

```python
async def drag_and_drop(page, source_selector, target_selector):
    source = await page.query_selector(source_selector)
    target = await page.query_selector(target_selector)

    if source and target:
        source_box = await source.bounding_box()
        target_box = await target.bounding_box()

        # Tinh vi tri trung tam
        source_x = source_box["x"] + source_box["width"] / 2
        source_y = source_box["y"] + source_box["height"] / 2
        target_x = target_box["x"] + target_box["width"] / 2
        target_y = target_box["y"] + target_box["height"] / 2

        # Thuc hien drag
        await page.mouse.move(source_x, source_y)
        await page.mouse.down()
        await page.mouse.move(target_x, target_y)
        await page.mouse.up()
```

---

## Tiep Theo

- [Page API](./page.md) - Page methods
- [Session API](./session.md) - HTTP requests
- [Stealth Guide](../stealth-guide.md) - Anti-detection
