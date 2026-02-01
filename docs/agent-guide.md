# Huong Dan AI Agent

Huong dan su dung AI Agent trong Kuromi Browser de tu dong hoa browser bang ngon ngu tu nhien.

## Tong Quan

Kuromi Browser tich hop AI Agent (lay cam hung tu Browser-Use) cho phep dieu khien browser bang cac lenh ngon ngu tu nhien. Agent se:

1. **Observe** - Quan sat trang thai hien tai cua page
2. **Think** - Phan tich va lap ke hoach
3. **Act** - Thuc hien hanh dong
4. **Reflect** - Danh gia ket qua

## Cai Dat

```bash
pip install kuromi-browser[llm]
```

## Cau Hinh LLM

### OpenAI

```python
from kuromi_browser.llm import OpenAI

llm = OpenAI(
    api_key="sk-...",
    model="gpt-4-turbo",
    temperature=0.1,
)
```

### Anthropic Claude

```python
from kuromi_browser.llm import Anthropic

llm = Anthropic(
    api_key="sk-ant-...",
    model="claude-3-opus",
)
```

### Azure OpenAI

```python
from kuromi_browser.llm import AzureOpenAI

llm = AzureOpenAI(
    api_key="...",
    endpoint="https://your-resource.openai.azure.com",
    deployment="gpt-4",
    api_version="2024-02-15-preview",
)
```

## Su Dung Co Ban

### Tao Agent

```python
import asyncio
from kuromi_browser import Browser, Agent

async def main():
    async with Browser() as browser:
        page = await browser.new_page()

        # Tao agent voi page
        agent = Agent(page)

        # Chay task
        result = await agent.run(
            "Di den google.com va tim kiem 'Python tutorial'"
        )

        print(result)

asyncio.run(main())
```

### Voi LLM Provider

```python
from kuromi_browser import Browser, Agent
from kuromi_browser.llm import OpenAI

async def main():
    llm = OpenAI(api_key="sk-...")

    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page, llm=llm)

        result = await agent.run("Tim gia Bitcoin hien tai")
        print(result)
```

## Agent API

### Constructor

```python
from kuromi_browser import Agent, AgentConfig

config = AgentConfig(
    max_steps=100,          # So buoc toi da
    timeout=300,            # Timeout (giay)
    screenshot_mode="auto", # "auto", "always", "never"
    verbose=True,           # In log chi tiet
)

agent = Agent(
    page=page,
    llm=llm,
    config=config,
)
```

### run(task)

Chay agent de hoan thanh task.

```python
result = await agent.run(
    "Dang nhap vao trang web voi username 'user' va password 'pass'",
    max_steps=50,
    timeout=120,
)
```

**Tham so:**
- `task` (str): Mo ta task can lam
- `max_steps` (int): So buoc toi da
- `timeout` (float): Timeout (giay)

**Tra ve:** Ket qua cua task (tuy vao task)

### step(instruction)

Thuc hien mot buoc don le.

```python
result = await agent.step("Click vao nut 'Submit'")
```

### observe()

Quan sat trang thai hien tai.

```python
state = await agent.observe()
print(state)
# {
#     "url": "https://example.com",
#     "title": "Example Page",
#     "elements": [...],
#     "screenshot": "base64...",
# }
```

### act(action, *args, **kwargs)

Thuc hien hanh dong cu the.

```python
await agent.act("click", selector="#button")
await agent.act("type", selector="#input", text="Hello")
await agent.act("scroll", direction="down", amount=500)
```

### plan(goal)

Tao ke hoach cho goal.

```python
steps = await agent.plan("Mua san pham va thanh toan")
for step in steps:
    print(step)
# [
#     "1. Tim san pham trong danh sach",
#     "2. Click vao san pham",
#     "3. Click nut 'Them vao gio'",
#     "4. Di den gio hang",
#     "5. Click 'Thanh toan'",
#     "6. Dien thong tin thanh toan",
#     "7. Xac nhan don hang",
# ]
```

### reflect(observation, action, result)

Danh gia hanh dong.

```python
reflection = await agent.reflect(
    observation={"page": "login"},
    action="click submit button",
    result="error message appeared",
)
print(reflection)
# "Hanh dong that bai. Can kiem tra lai thong tin dang nhap."
```

## Agent Actions

Cac hanh dong agent co the thuc hien:

### Navigation

```python
# Mo URL
await agent.act("goto", url="https://example.com")

# Quay lai
await agent.act("go_back")

# Tien toi
await agent.act("go_forward")

# Reload
await agent.act("reload")
```

### Element Interaction

```python
# Click
await agent.act("click", selector="#button")
await agent.act("click", text="Submit")  # Tim theo text

# Double click
await agent.act("dblclick", selector="#item")

# Type
await agent.act("type", selector="#input", text="Hello World")

# Fill (xoa truoc khi dien)
await agent.act("fill", selector="#input", value="New Value")

# Select option
await agent.act("select", selector="#dropdown", value="option1")

# Check/Uncheck
await agent.act("check", selector="#checkbox")
await agent.act("uncheck", selector="#checkbox")

# Hover
await agent.act("hover", selector="#menu")
```

### Scroll

```python
# Scroll xuong
await agent.act("scroll", direction="down", amount=500)

# Scroll len
await agent.act("scroll", direction="up", amount=300)

# Scroll den element
await agent.act("scroll_to", selector="#target")
```

### Waiting

```python
# Cho doi element
await agent.act("wait_for", selector="#loading", state="hidden")

# Cho doi thoi gian
await agent.act("wait", duration=2)  # 2 giay
```

### Data Extraction

```python
# Lay text
text = await agent.act("get_text", selector="#content")

# Lay attribute
href = await agent.act("get_attribute", selector="a", name="href")

# Lay danh sach
items = await agent.act("get_list", selector=".item", extract="text")
```

### Screenshot

```python
# Chup man hinh
await agent.act("screenshot", path="current.png")
```

## Vi Du Thuc Te

### Dang Nhap Website

```python
async def login_example():
    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)

        result = await agent.run("""
            1. Di den https://example.com/login
            2. Dien username 'myuser' vao o username
            3. Dien password 'mypass' vao o password
            4. Click nut Login
            5. Cho den khi trang dashboard hien thi
            6. Xac nhan da dang nhap thanh cong
        """)

        print(f"Ket qua: {result}")
```

### Thu Thap Du Lieu

```python
async def scrape_example():
    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)

        data = await agent.run("""
            1. Di den https://news.example.com
            2. Tim 5 bai bao moi nhat
            3. Voi moi bai bao, lay tieu de va link
            4. Tra ve danh sach cac bai bao
        """)

        for article in data:
            print(f"- {article['title']}: {article['url']}")
```

### E-commerce

```python
async def shopping_example():
    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)

        await agent.run("""
            1. Di den https://shop.example.com
            2. Tim kiem 'laptop'
            3. Loc theo gia tu thap den cao
            4. Chon san pham dau tien
            5. Them vao gio hang
            6. Xac nhan san pham da duoc them
        """)
```

### Form Tu Dong

```python
async def form_example():
    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)

        await agent.run("""
            1. Di den https://example.com/contact
            2. Dien form lien he:
               - Ten: Nguyen Van A
               - Email: example@email.com
               - Tin nhan: Xin chao, toi can ho tro
            3. Click nut Gui
            4. Xac nhan form da gui thanh cong
        """)
```

## Cau Hinh Nang Cao

### AgentConfig

```python
from kuromi_browser import AgentConfig

config = AgentConfig(
    # Gioi han
    max_steps=100,
    timeout=300,

    # Screenshot
    screenshot_mode="auto",  # "auto", "always", "never"
    screenshot_quality=80,

    # Logging
    verbose=True,
    log_level="DEBUG",

    # Retry
    retry_failed_actions=True,
    max_retries=3,

    # Waiting
    default_wait_time=1.0,
    wait_after_action=0.5,

    # Memory
    use_memory=True,
    memory_size=10,  # So buoc nho

    # Vision
    use_vision=True,  # Su dung screenshot de phan tich
)
```

### Custom System Prompt

```python
agent = Agent(
    page=page,
    llm=llm,
    system_prompt="""
    Ban la mot web automation agent.
    Hay lam theo cac buoc mot cach can than.
    Luon kiem tra ket qua sau moi hanh dong.
    Neu gap loi, hay thu cach khac.
    """,
)
```

### Action Hooks

```python
async def before_action(action, params):
    print(f"Sap thuc hien: {action}")

async def after_action(action, params, result):
    print(f"Da thuc hien: {action}, ket qua: {result}")

agent = Agent(
    page=page,
    before_action=before_action,
    after_action=after_action,
)
```

## Best Practices

### 1. Mo Ta Ro Rang

```python
# Tot
await agent.run(
    "Click vao nut mau xanh co text 'Submit' o cuoi form"
)

# Khong tot
await agent.run("Click submit")
```

### 2. Chia Nho Task

```python
# Tot - chia thanh cac buoc
await agent.run("""
    1. Mo trang dang nhap
    2. Dien username
    3. Dien password
    4. Click dang nhap
""")

# Khong tot - mot dong dai
await agent.run("Dang nhap vao trang web roi di den dashboard va lay du lieu")
```

### 3. Xu Ly Loi

```python
try:
    result = await agent.run(task, max_steps=20)
except TimeoutError:
    print("Task qua thoi gian")
except Exception as e:
    print(f"Loi: {e}")
```

### 4. Kiem Tra Ket Qua

```python
result = await agent.run("Tim gia Bitcoin")

# Kiem tra ket qua hop le
if result and "price" in result:
    print(f"Gia: {result['price']}")
else:
    print("Khong tim thay gia")
```

## Tiep Theo

- [Page API](./api/page.md) - Manual page control
- [Stealth Guide](./stealth-guide.md) - Anti-detection
- [Advanced CDP](./advanced/cdp.md) - Low-level control
