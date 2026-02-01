# Session API Reference

API cho HTTP Session trong Kuromi Browser.

## Tong Quan

Session cung cap HTTP client nhe voi TLS fingerprinting thong qua curl_cffi. Su dung cho cac truong hop khong can full browser.

## Session

### Constructor

```python
from kuromi_browser.session import Session

session = Session(
    impersonate="chrome120",  # TLS profile
    proxy="http://...",       # Proxy
    timeout=30,               # Default timeout (s)
)
```

**Tham so:**
- `impersonate` (str): TLS profile ("chrome120", "firefox121", "safari17", ...)
- `proxy` (str, optional): Proxy URL
- `timeout` (float): Default timeout (giay)
- `headers` (dict): Default headers
- `cookies` (dict): Initial cookies

### Properties

#### cookies

Lay cookies hien tai.

```python
all_cookies = session.cookies
# {"session_id": "abc123", "user": "john"}
```

### HTTP Methods

#### get(url, **options)

Thuc hien GET request.

```python
response = await session.get(
    "https://api.example.com/data",
    params={"page": 1, "limit": 10},
    headers={"Authorization": "Bearer token"},
    timeout=10,
    follow_redirects=True,
)
```

**Tham so:**
- `url` (str): URL
- `params` (dict, optional): Query parameters
- `headers` (dict, optional): Request headers
- `timeout` (float, optional): Timeout
- `follow_redirects` (bool): Theo redirect

**Tra ve:** `NetworkResponse`

#### post(url, **options)

Thuc hien POST request.

```python
# JSON body
response = await session.post(
    "https://api.example.com/users",
    json={"name": "John", "email": "john@example.com"},
)

# Form data
response = await session.post(
    "https://example.com/login",
    data={"username": "john", "password": "secret"},
)

# Raw body
response = await session.post(
    "https://api.example.com/upload",
    data=b"binary content",
    headers={"Content-Type": "application/octet-stream"},
)
```

**Tham so:**
- `url` (str): URL
- `data` (dict|str|bytes, optional): Request body
- `json` (dict, optional): JSON body (tu dong set Content-Type)
- `headers` (dict, optional): Request headers
- `timeout` (float, optional): Timeout
- `follow_redirects` (bool): Theo redirect

#### put(url, **options)

Thuc hien PUT request.

```python
response = await session.put(
    "https://api.example.com/users/1",
    json={"name": "John Updated"},
)
```

#### patch(url, **options)

Thuc hien PATCH request.

```python
response = await session.patch(
    "https://api.example.com/users/1",
    json={"email": "newemail@example.com"},
)
```

#### delete(url, **options)

Thuc hien DELETE request.

```python
response = await session.delete(
    "https://api.example.com/users/1",
)
```

#### head(url, **options)

Thuc hien HEAD request.

```python
response = await session.head("https://example.com/file.zip")
content_length = response.headers.get("Content-Length")
```

#### options(url, **options)

Thuc hien OPTIONS request (CORS preflight).

```python
response = await session.options("https://api.example.com/endpoint")
allowed_methods = response.headers.get("Access-Control-Allow-Methods")
```

#### request(method, url, **options)

Thuc hien request voi method bat ky.

```python
response = await session.request(
    "PATCH",
    "https://api.example.com/resource",
    json={"field": "value"},
)
```

### Configuration Methods

#### set_fingerprint(fingerprint)

Dat fingerprint cho TLS spoofing.

```python
from kuromi_browser import Fingerprint

fp = Fingerprint(
    user_agent="Mozilla/5.0 ...",
)
await session.set_fingerprint(fp)
```

#### set_proxy(proxy)

Dat proxy.

```python
await session.set_proxy("http://user:pass@proxy.example.com:8080")
```

#### set_cookies(cookies)

Dat cookies.

```python
await session.set_cookies({
    "session_id": "abc123",
    "preferences": "dark_mode",
})
```

#### clear_cookies()

Xoa tat ca cookies.

```python
await session.clear_cookies()
```

#### close()

Dong session.

```python
await session.close()
```

## NetworkResponse

Response tu HTTP request.

### Properties

```python
response.status        # 200
response.status_text   # "OK"
response.url           # "https://api.example.com/data"
response.headers       # {"Content-Type": "application/json", ...}
response.body          # b'{"result": "success"}'
```

### Methods

#### text()

Lay body dang text.

```python
text = response.text()
# "Hello World"
```

#### json()

Parse body dang JSON.

```python
data = response.json()
# {"result": "success", "data": [...]}
```

## SessionPool

Quan ly nhieu sessions.

```python
from kuromi_browser.session import SessionPool

pool = SessionPool(
    size=10,              # So session toi da
    impersonate="chrome120",
)

# Lay session tu pool
async with pool.acquire() as session:
    response = await session.get("https://example.com")
```

## TLS Profiles

Cac TLS profile ho tro:

| Profile | Mo ta |
|---------|-------|
| `chrome120` | Chrome 120 |
| `chrome119` | Chrome 119 |
| `chrome110` | Chrome 110 |
| `firefox121` | Firefox 121 |
| `firefox120` | Firefox 120 |
| `safari17` | Safari 17 |
| `safari16` | Safari 16 |
| `edge120` | Edge 120 |

## Vi Du

### API Client

```python
from kuromi_browser.session import Session

async def fetch_users():
    session = Session(impersonate="chrome120")

    try:
        # Login
        login_response = await session.post(
            "https://api.example.com/auth/login",
            json={"email": "user@example.com", "password": "secret"},
        )
        token = login_response.json()["token"]

        # Fetch data voi auth
        response = await session.get(
            "https://api.example.com/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        return response.json()

    finally:
        await session.close()
```

### Concurrent Requests

```python
import asyncio
from kuromi_browser.session import Session

async def fetch_all(urls):
    session = Session()

    try:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]

    finally:
        await session.close()
```

### Retry Logic

```python
from kuromi_browser.session import Session

async def fetch_with_retry(url, max_retries=3):
    session = Session()

    for attempt in range(max_retries):
        try:
            response = await session.get(url, timeout=10)
            if response.status == 200:
                return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    await session.close()
```

## Tiep Theo

- [Page API](./page.md) - Browser page control
- [HybridPage](./page.md#hybridpage) - Ket hop HTTP va browser
- [Stealth Guide](../stealth-guide.md) - TLS fingerprinting chi tiet
