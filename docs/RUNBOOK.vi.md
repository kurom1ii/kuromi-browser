# Sổ Tay Vận Hành (RUNBOOK)

Hướng dẫn triển khai, giám sát và xử lý sự cố cho Kuromi Browser.

---

## 📋 Mục Lục

1. [Triển Khai](#triển-khai)
2. [Cấu Hình MCP Server](#cấu-hình-mcp-server)
3. [Giám Sát](#giám-sát)
4. [Xử Lý Sự Cố](#xử-lý-sự-cố)
5. [Tối Ưu Hiệu Suất](#tối-ưu-hiệu-suất)
6. [Rollback](#rollback)
7. [Bảo Mật](#bảo-mật)

---

## 🚀 Triển Khai

### Cài Đặt Package

```bash
# Từ PyPI (khi publish)
pip install kuromi-browser

# Từ source
pip install git+https://github.com/kurom1ii/kuromi-browser.git

# Với đầy đủ tính năng
pip install kuromi-browser[full]

# Development
pip install -e ".[dev,full]"
```

### Kiểm Tra Cài Đặt

```python
# Kiểm tra import
from kuromi_browser import Browser, Fingerprint, Page
from kuromi_browser.stealth import get_stealth_chromium_args, CDPPatches
print("✅ Import OK")

# Kiểm tra phiên bản
import kuromi_browser
print(f"Version: {kuromi_browser.__version__}")
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Cài đặt Chrome
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt kuromi-browser
RUN pip install kuromi-browser[full]

# Environment
ENV CHROMIUM_PATH=/usr/bin/chromium
ENV DISPLAY=:99

# Entrypoint
CMD ["python", "-m", "kuromi_browser.mcp"]
```

```bash
# Build
docker build -t kuromi-browser .

# Run
docker run -d --name kuromi kuromi-browser
```

---

## 🔌 Cấu Hình MCP Server

### Chạy Local

```bash
# Chạy MCP server
python -m kuromi_browser.mcp

# Với custom port
KUROMI_MCP_PORT=8080 python -m kuromi_browser.mcp

# Với logging
KUROMI_LOG_LEVEL=DEBUG python -m kuromi_browser.mcp
```

### Tích Hợp Claude Desktop

Thêm vào `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kuromi-browser": {
      "command": "python",
      "args": ["-m", "kuromi_browser.mcp"],
      "env": {
        "KUROMI_HEADLESS": "true",
        "KUROMI_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### MCP Tools Có Sẵn

| Tool | Mô tả |
|------|-------|
| `browser_launch` | Khởi động browser |
| `browser_close` | Đóng browser |
| `page_goto` | Navigate đến URL |
| `page_content` | Lấy HTML content |
| `page_screenshot` | Chụp screenshot |
| `element_click` | Click element |
| `element_type` | Nhập text |
| `element_query` | Query selector |
| `network_intercept` | Intercept requests |
| `stealth_apply` | Apply stealth mode |

---

## 📊 Giám Sát

### Health Check

```python
from kuromi_browser import Browser

async def health_check() -> dict:
    """Kiểm tra health của service."""
    try:
        async with Browser(headless=True) as browser:
            page = await browser.new_page()
            await page.goto("about:blank", timeout=10000)
            await page.close()
            return {
                "status": "healthy",
                "browser": "ok",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### Logging

```python
import logging

# Bật debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Logging cụ thể cho kuromi
logging.getLogger("kuromi_browser").setLevel(logging.DEBUG)
logging.getLogger("kuromi_browser.cdp").setLevel(logging.INFO)
```

### Metrics Cần Theo Dõi

| Metric | Mô tả | Ngưỡng cảnh báo |
|--------|-------|-----------------|
| `page_load_time` | Thời gian load trang | > 30s |
| `memory_usage` | RAM của browser | > 2GB |
| `error_rate` | Tỷ lệ thất bại | > 5% |
| `active_connections` | Số CDP connections | > 100 |
| `browser_instances` | Số browser đang chạy | > 10 |
| `screenshot_size` | Kích thước screenshot | > 10MB |

### Prometheus Metrics (Tùy chọn)

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
page_loads = Counter('kuromi_page_loads_total', 'Total page loads')
errors = Counter('kuromi_errors_total', 'Total errors', ['type'])

# Histograms
load_time = Histogram('kuromi_page_load_seconds', 'Page load time')

# Gauges
active_browsers = Gauge('kuromi_active_browsers', 'Active browser count')
```

---

## 🔧 Xử Lý Sự Cố

### ❌ Lỗi: Browser Không Khởi Động

**Triệu chứng:**
- `BrowserLaunchError`
- `ChromiumNotFound`
- Browser process treo

**Nguyên nhân & Giải pháp:**

```bash
# 1. Kiểm tra Chrome có cài đặt không
which chromium-browser
which google-chrome

# 2. Kiểm tra quyền thực thi
ls -la /usr/bin/chromium-browser

# 3. Set đường dẫn custom
export CHROMIUM_PATH=/usr/bin/chromium-browser
```

```python
from kuromi_browser import Browser, BrowserConfig

# Trong code
config = BrowserConfig(
    executable_path="/usr/bin/chromium-browser",
    headless=True,
    args=["--no-sandbox", "--disable-dev-shm-usage"]
)
async with Browser(config=config) as browser:
    ...
```

### ❌ Lỗi: Bị Phát Hiện Bot

**Triệu chứng:**
- Cloudflare challenge
- CAPTCHA liên tục
- Access denied

**Giải pháp:**

```python
from kuromi_browser import Browser, BrowserConfig
from kuromi_browser.stealth import (
    FingerprintGenerator,
    get_stealth_chromium_args,
    apply_stealth,
)

# 1. Sử dụng stealth args
args = get_stealth_chromium_args()
config = BrowserConfig(args=args, headless=False)  # Thử headful trước

# 2. Generate fingerprint thực tế
fp = FingerprintGenerator.generate(
    browser="chrome",
    os="windows",
    locale="en-US"
)

# 3. Apply stealth
async with Browser(config=config) as browser:
    page = await browser.new_page()
    await apply_stealth(page.cdp_session, fp)
    await page.goto("https://protected-site.com")
```

**Checklist kiểm tra:**
- [ ] Headless = False (thử headful)
- [ ] Có sử dụng `get_stealth_chromium_args()`
- [ ] Fingerprint nhất quán (browser + OS + locale)
- [ ] Không dùng proxy bị blacklist
- [ ] Thêm delay giữa các actions

### ❌ Lỗi: Memory Leak

**Triệu chứng:**
- RAM tăng liên tục
- OOM (Out of Memory) errors
- Browser chậm dần

**Giải pháp:**

```python
# 1. Luôn đóng page sau khi dùng
page = await browser.new_page()
try:
    await page.goto("...")
    # ... làm việc
finally:
    await page.close()  # ❗ Quan trọng

# 2. Sử dụng context manager
async with browser.new_page() as page:
    await page.goto("...")
    # ... tự động đóng khi exit

# 3. Giới hạn số pages đồng thời
MAX_CONCURRENT_PAGES = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)

async def process_url(url):
    async with semaphore:
        async with browser.new_page() as page:
            await page.goto(url)

# 4. Periodic cleanup
async def cleanup_loop():
    while True:
        await asyncio.sleep(300)  # 5 phút
        import gc
        gc.collect()
        logger.info("Memory cleanup done")
```

### ❌ Lỗi: Timeout

**Triệu chứng:**
- `TimeoutError` khi navigate
- Page load chậm

**Giải pháp:**

```python
from kuromi_browser import PageConfig

# 1. Tăng timeout
config = PageConfig(timeout=60000)  # 60 giây

# 2. Sử dụng wait_until phù hợp
await page.goto(url, wait_until="domcontentloaded")  # Nhanh hơn "load"
# Các options: "load", "domcontentloaded", "networkidle"

# 3. Retry với backoff
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def goto_with_retry(page, url):
    await page.goto(url, timeout=30000)
```

### ❌ Lỗi: Proxy Connection Failed

**Triệu chứng:**
- `ProxyConnectionError`
- Connection refused
- SSL errors

**Giải pháp:**

```python
from kuromi_browser import ProxyConfig

# 1. Kiểm tra format proxy
# HTTP
proxy = ProxyConfig.from_url("http://user:pass@proxy.com:8080")

# SOCKS5
proxy = ProxyConfig.from_url("socks5://user:pass@socks.com:1080")

# 2. Test proxy trước
import httpx

async def test_proxy(proxy_url: str) -> bool:
    try:
        async with httpx.AsyncClient(proxy=proxy_url) as client:
            response = await client.get("https://httpbin.org/ip", timeout=10)
            print(f"IP: {response.json()['origin']}")
            return True
    except Exception as e:
        print(f"Proxy error: {e}")
        return False

# 3. Sử dụng trong browser
config = BrowserConfig(proxy=proxy)
```

---

## ⚡ Tối Ưu Hiệu Suất

### Browser Optimization

```python
from kuromi_browser import BrowserConfig

config = BrowserConfig(
    headless=True,
    args=[
        # Performance
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",

        # Memory
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",  # Nếu không cần ảnh

        # Network
        "--disable-background-networking",
        "--disable-sync",
    ]
)
```

### Connection Pooling

```python
from kuromi_browser.browser import BrowserPool

# Tạo pool
pool = BrowserPool(
    max_browsers=5,
    idle_timeout=300,  # 5 phút
)

async def process_task(url: str):
    browser = await pool.acquire()
    try:
        page = await browser.new_page()
        try:
            await page.goto(url)
            return await page.content()
        finally:
            await page.close()
    finally:
        await pool.release(browser)

# Cleanup khi shutdown
await pool.close_all()
```

### Parallel Processing

```python
import asyncio
from kuromi_browser import Browser

async def process_urls(urls: list[str], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def process_one(url):
        async with semaphore:
            async with Browser(headless=True) as browser:
                page = await browser.new_page()
                await page.goto(url)
                content = await page.content()
                await page.close()
                return content

    tasks = [process_one(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Sử dụng
urls = ["https://example1.com", "https://example2.com", ...]
results = await process_urls(urls, max_concurrent=10)
```

---

## ⏪ Rollback

### Code Rollback

```bash
# Rollback về version cụ thể
pip install kuromi-browser==0.1.0

# Hoặc từ git tag
pip install git+https://github.com/kurom1ii/kuromi-browser.git@v0.1.0
```

### Configuration Rollback

```bash
# Backup trước khi thay đổi
cp config.yaml config.yaml.bak

# Restore khi cần
cp config.yaml.bak config.yaml
```

### Database/State Rollback

```python
# Nếu sử dụng profiles
from kuromi_browser.browser import ProfileManager

pm = ProfileManager()

# Export profile trước khi thay đổi
await pm.export_profile("myprofile", "/backup/myprofile.tar.gz")

# Restore khi cần
await pm.import_profile("/backup/myprofile.tar.gz")
```

---

## 🔒 Bảo Mật

### Credentials Management

```python
import os

# ❌ KHÔNG làm thế này
proxy = "http://myuser:mypassword@proxy.com:8080"

# ✅ Sử dụng environment variables
proxy_user = os.environ.get("PROXY_USER")
proxy_pass = os.environ.get("PROXY_PASS")
proxy_host = os.environ.get("PROXY_HOST")

proxy = f"http://{proxy_user}:{proxy_pass}@{proxy_host}"
```

### Browser Security

```python
config = BrowserConfig(
    args=[
        # Tắt các tính năng không cần thiết
        "--disable-extensions",
        "--disable-plugins",
        "--disable-sync",
        "--disable-translate",
        "--disable-background-networking",

        # Sandbox (bật nếu có thể)
        # "--no-sandbox",  # Chỉ tắt khi cần thiết

        # Privacy
        "--incognito",
        "--disable-client-side-phishing-detection",
    ]
)
```

### Sensitive Data

```python
# Không log sensitive data
import logging

class SensitiveFilter(logging.Filter):
    SENSITIVE_PATTERNS = ['password', 'token', 'key', 'secret']

    def filter(self, record):
        message = record.getMessage()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message.lower():
                record.msg = "[REDACTED]"
        return True

logger.addFilter(SensitiveFilter())
```

---

## 📞 Hỗ Trợ

### Resources

- **GitHub Issues:** https://github.com/kurom1ii/kuromi-browser/issues
- **Documentation:** https://github.com/kurom1ii/kuromi-browser#readme

### Debug Checklist

1. ✅ Bật debug logging
2. ✅ Kiểm tra Chrome console (JS errors)
3. ✅ Kiểm tra Network tab (failed requests)
4. ✅ Chụp screenshot tại điểm lỗi
5. ✅ Test với minimal code
6. ✅ Thử headful mode
7. ✅ Kiểm tra proxy connectivity
8. ✅ Verify fingerprint consistency
