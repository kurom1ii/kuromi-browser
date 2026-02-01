"""
Dual-Mode Page System for kuromi-browser.

This module provides three page modes for different automation scenarios:

- **BrowserPage**: Full CDP-based browser automation with JavaScript execution,
  real rendering, and complete browser capabilities.

- **SessionPage**: Lightweight HTTP-only mode using curl_cffi for fast requests
  with TLS fingerprint spoofing. No JavaScript execution but much faster.

- **HybridPage**: Intelligent combination of both modes. Uses SessionPage for
  fast data fetching and BrowserPage when JavaScript execution is needed.

Example usage:
    from kuromi_browser.pages import BrowserPage, SessionPage, HybridPage

    # Full browser mode
    async with browser.new_page() as page:
        browser_page = BrowserPage(page)
        await browser_page.goto("https://example.com")
        await browser_page.click("button#submit")

    # HTTP-only mode (fast)
    async with SessionPage(impersonate="chrome120") as page:
        response = await page.goto("https://api.example.com/data")
        data = response.json()

    # Hybrid mode (intelligent switching)
    async with HybridPage(cdp_session, session) as page:
        # Uses HTTP for initial fetch
        await page.goto("https://example.com")
        # Switches to browser for JavaScript
        await page.click("button.dynamic")
"""

from kuromi_browser.pages.browser_page import BrowserPage
from kuromi_browser.pages.session_page import SessionPage
from kuromi_browser.pages.hybrid_page import HybridPage
from kuromi_browser.pages.cookies import (
    CookieJar,
    CookieConverter,
    sync_cookies_browser_to_session,
    sync_cookies_session_to_browser,
)

__all__ = [
    "BrowserPage",
    "SessionPage",
    "HybridPage",
    "CookieJar",
    "CookieConverter",
    "sync_cookies_browser_to_session",
    "sync_cookies_session_to_browser",
]
