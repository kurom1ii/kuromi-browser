"""
MCP (Model Context Protocol) server for kuromi-browser.

This module provides an MCP server that exposes browser automation
capabilities to AI agents via the MCP protocol.

Usage:
    # Run as standalone server
    python -m kuromi_browser.mcp

    # Or integrate with your MCP setup
    from kuromi_browser.mcp import BrowserMCPServer
    server = BrowserMCPServer()
    await server.start()

Tools Available:
    - Browser: launch, close
    - Navigation: navigate, go_back, go_forward, reload
    - Elements: click, type_text, fill, select_option, hover, scroll
    - Content: get_content, get_attribute, query_selector_all
    - Screenshot: screenshot (page or element)
    - Network: get_cookies, set_cookies, clear_cookies, intercept_requests
    - Stealth: set_fingerprint, generate_fingerprint, set_proxy
    - Pages: new_page, list_pages, switch_page, close_page
    - Wait: wait_for_selector, wait_for_navigation
    - Input: press_key, mouse_move, handle_dialog
    - JavaScript: evaluate

Example MCP Configuration:
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
"""

try:
    from kuromi_browser.mcp.server import BrowserMCPServer
except ImportError:
    BrowserMCPServer = None  # MCP SDK not installed

from kuromi_browser.mcp.tools import (
    BrowserTools,
    NavigationTools,
    ElementTools,
    ScreenshotTools,
    NetworkTools,
    StealthTools,
    PageTools,
    WaitTools,
    InputTools,
    JavaScriptTools,
    ALL_TOOLS,
    ALL_TOOL_GROUPS,
)

__all__ = [
    "BrowserMCPServer",
    "BrowserTools",
    "NavigationTools",
    "ElementTools",
    "ScreenshotTools",
    "NetworkTools",
    "StealthTools",
    "PageTools",
    "WaitTools",
    "InputTools",
    "JavaScriptTools",
    "ALL_TOOLS",
    "ALL_TOOL_GROUPS",
]
