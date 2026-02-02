# Runbook

Operations guide for Kuromi Browser.

## Deployment

### Package Installation

```bash
# From PyPI (when published)
pip install kuromi-browser

# From source
pip install git+https://github.com/kurom1ii/kuromi-browser.git

# With all features
pip install kuromi-browser[full]

# Development install
pip install -e ".[dev,full]"
```

### Docker (Future)

```dockerfile
FROM python:3.11-slim

RUN pip install kuromi-browser[full]

# Install Chromium
RUN apt-get update && apt-get install -y chromium

CMD ["python", "-m", "kuromi_browser.mcp"]
```

## MCP Server Deployment

### Local Setup

```bash
# Run MCP server
python -m kuromi_browser.mcp

# With custom port
KUROMI_MCP_PORT=8080 python -m kuromi_browser.mcp
```

### Claude Desktop Integration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "kuromi-browser": {
      "command": "python",
      "args": ["-m", "kuromi_browser.mcp"]
    }
  }
}
```

## Monitoring

### Health Checks

```python
from kuromi_browser import Browser

async def health_check():
    try:
        async with Browser() as browser:
            page = await browser.new_page()
            await page.goto("about:blank")
            return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("kuromi_browser").setLevel(logging.DEBUG)
```

### Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| page_load_time | Page load duration | >30s |
| memory_usage | Browser memory | >2GB |
| error_rate | Failed operations | >5% |
| connection_pool | Active connections | >100 |

## Common Issues

### Issue: Browser Won't Launch

**Symptoms:**
- `ChromiumNotFound` error
- Browser process hangs

**Solutions:**
```bash
# Check Chrome installation
which chromium-browser
which google-chrome

# Set custom path
export CHROMIUM_PATH=/usr/bin/chromium-browser

# Or in code
from kuromi_browser import BrowserConfig
config = BrowserConfig(executable_path="/usr/bin/chromium-browser")
```

### Issue: Detection by Anti-Bot

**Symptoms:**
- Cloudflare challenges
- CAPTCHA requests
- Access denied

**Solutions:**
```python
from kuromi_browser.stealth import (
    get_stealth_chromium_args,
    FingerprintGenerator,
    apply_stealth,
)

# Use stealth args
args = get_stealth_chromium_args()

# Generate realistic fingerprint
fp = FingerprintGenerator.generate(browser="chrome", os="windows")

# Apply stealth patches
await apply_stealth(cdp_session, fp)
```

### Issue: Memory Leak

**Symptoms:**
- Growing memory usage
- OOM errors

**Solutions:**
```python
# Always close pages
page = await browser.new_page()
try:
    await page.goto("...")
finally:
    await page.close()

# Use context manager
async with browser.new_page() as page:
    await page.goto("...")

# Limit concurrent pages
MAX_PAGES = 5
```

### Issue: Timeout Errors

**Symptoms:**
- `TimeoutError` on navigation
- Slow page loads

**Solutions:**
```python
# Increase timeout
from kuromi_browser import PageConfig

config = PageConfig(timeout=60000)  # 60 seconds

# Use wait_until
await page.goto(url, wait_until="networkidle")
```

### Issue: Proxy Connection Failed

**Symptoms:**
- `ProxyConnectionError`
- Connection refused

**Solutions:**
```python
# Verify proxy format
from kuromi_browser import ProxyConfig

# HTTP proxy
proxy = ProxyConfig.from_url("http://user:pass@proxy.com:8080")

# SOCKS5 proxy
proxy = ProxyConfig.from_url("socks5://user:pass@socks.com:1080")

# Test connection
import httpx
async with httpx.AsyncClient(proxy=proxy.to_httpx_proxy()) as client:
    response = await client.get("https://httpbin.org/ip")
    print(response.json())
```

## Rollback Procedures

### Code Rollback

```bash
# Revert to previous version
pip install kuromi-browser==0.1.0

# Or from git tag
pip install git+https://github.com/kurom1ii/kuromi-browser.git@v0.1.0
```

### Configuration Rollback

```bash
# Backup config before changes
cp config.yaml config.yaml.bak

# Restore
cp config.yaml.bak config.yaml
```

## Performance Tuning

### Browser Optimization

```python
from kuromi_browser import BrowserConfig

config = BrowserConfig(
    headless=True,
    args=[
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
    ]
)
```

### Connection Pooling

```python
from kuromi_browser.browser import BrowserPool

# Create pool
pool = BrowserPool(max_browsers=5)

# Get browser from pool
browser = await pool.acquire()
try:
    page = await browser.new_page()
    await page.goto("...")
finally:
    await pool.release(browser)
```

### Memory Management

```python
# Periodic cleanup
import asyncio

async def cleanup_loop():
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        import gc
        gc.collect()
```

## Security Considerations

### Credentials

- Never commit credentials
- Use environment variables
- Rotate proxy credentials regularly

```python
import os

proxy_user = os.environ.get("PROXY_USER")
proxy_pass = os.environ.get("PROXY_PASS")
```

### Browser Security

```python
# Disable unnecessary features
args = [
    "--disable-extensions",
    "--disable-plugins",
    "--disable-sync",
    "--disable-translate",
]
```

## Support

### Resources

- GitHub Issues: https://github.com/kurom1ii/kuromi-browser/issues
- Documentation: https://github.com/kurom1ii/kuromi-browser#readme

### Debugging Tips

1. Enable debug logging
2. Check browser console for JS errors
3. Use CDP inspector for network issues
4. Test with minimal code first
