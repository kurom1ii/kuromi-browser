"""
Chrome DevTools Protocol (CDP) module for kuromi-browser.

This module provides low-level access to CDP for browser automation:
- CDPConnection: WebSocket connection to Chrome/Chromium
- CDPSession: Session for a specific target (page, worker, etc.)
- BrowserProcess: Manages browser process lifecycle
- TargetManager: Manages CDP targets and sessions
- PageSession: High-level page automation

Example usage:
    ```python
    from kuromi_browser.cdp import (
        CDPConnection,
        CDPSession,
        BrowserProcess,
        BrowserLaunchOptions,
        launch_browser,
    )

    # Launch browser and connect
    async with BrowserProcess() as browser:
        async with CDPConnection(browser.ws_endpoint) as connection:
            # Get available pages
            result = await connection.send("Target.getTargets")
            pages = [t for t in result["targetInfos"] if t["type"] == "page"]

            # Attach to a page
            session = await CDPSession.create(connection, pages[0]["targetId"])
            await session.send("Page.enable")
            await session.send("Page.navigate", {"url": "https://example.com"})
            await session.detach()
    ```

Or with higher-level helpers:
    ```python
    from kuromi_browser.cdp import launch_browser, TargetManager, PageSession

    browser = await launch_browser()
    async with CDPConnection(browser.ws_endpoint) as connection:
        manager = TargetManager(connection)
        session = await manager.create_page("https://example.com")

        page = PageSession(session)
        await page.enable()
        content = await page.get_content()
        await page.close()

    await browser.close()
    ```
"""

from kuromi_browser.cdp.connection import (
    CDPConnection,
    CDPError,
)
from kuromi_browser.cdp.launcher import (
    BrowserLaunchOptions,
    BrowserProcess,
    find_browser_executable,
    launch_browser,
)
from kuromi_browser.cdp.session import (
    CDPSession,
    PageSession,
    TargetManager,
)

__all__ = [
    # Connection
    "CDPConnection",
    "CDPError",
    # Launcher
    "BrowserLaunchOptions",
    "BrowserProcess",
    "find_browser_executable",
    "launch_browser",
    # Session
    "CDPSession",
    "PageSession",
    "TargetManager",
]
