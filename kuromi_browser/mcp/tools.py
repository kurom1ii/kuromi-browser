"""
MCP Tool definitions for kuromi-browser.

Organized tool groups for different browser automation capabilities.
"""

from dataclasses import dataclass
from typing import Any, Callable, Coroutine


@dataclass
class ToolInfo:
    """Tool metadata."""

    name: str
    description: str
    handler: Callable[..., Coroutine[Any, Any, Any]]


class BrowserTools:
    """Browser lifecycle management tools.

    Tools:
        - browser_launch: Launch browser with stealth/proxy
        - browser_close: Close browser instance
    """

    TOOLS = ["browser_launch", "browser_close"]


class NavigationTools:
    """Page navigation tools.

    Tools:
        - navigate: Go to URL
        - go_back: Browser back
        - go_forward: Browser forward
        - reload: Refresh page
    """

    TOOLS = ["navigate", "go_back", "go_forward", "reload"]


class ElementTools:
    """DOM element interaction tools.

    Tools:
        - click: Click element
        - type_text: Type into element
        - fill: Fill input field
        - select_option: Select dropdown option
        - hover: Hover over element
        - scroll: Scroll page/element
        - get_content: Get element content
        - get_attribute: Get element attribute
        - query_selector_all: Query multiple elements
        - upload_file: Upload file to input
    """

    TOOLS = [
        "click",
        "type_text",
        "fill",
        "select_option",
        "hover",
        "scroll",
        "get_content",
        "get_attribute",
        "query_selector_all",
        "upload_file",
    ]


class ScreenshotTools:
    """Screenshot and visual capture tools.

    Tools:
        - screenshot: Capture page/element screenshot
    """

    TOOLS = ["screenshot"]


class NetworkTools:
    """Network management and monitoring tools.

    Tools:
        - get_cookies: Get browser cookies
        - set_cookies: Set browser cookies
        - clear_cookies: Clear all cookies
        - intercept_requests: Enable request interception
        - get_network_log: Get captured requests
        - download: Download file from URL
    """

    TOOLS = [
        "get_cookies",
        "set_cookies",
        "clear_cookies",
        "intercept_requests",
        "get_network_log",
        "download",
    ]


class StealthTools:
    """Stealth and anti-detection tools.

    Tools:
        - set_fingerprint: Set browser fingerprint
        - generate_fingerprint: Generate random fingerprint
        - set_proxy: Configure proxy
    """

    TOOLS = ["set_fingerprint", "generate_fingerprint", "set_proxy"]


class PageTools:
    """Multi-page management tools.

    Tools:
        - new_page: Open new tab
        - list_pages: List open pages
        - switch_page: Switch to page
        - close_page: Close page
        - get_page_info: Get page details
    """

    TOOLS = ["new_page", "list_pages", "switch_page", "close_page", "get_page_info"]


class WaitTools:
    """Wait and synchronization tools.

    Tools:
        - wait_for_selector: Wait for element
        - wait_for_navigation: Wait for page load
    """

    TOOLS = ["wait_for_selector", "wait_for_navigation"]


class InputTools:
    """Keyboard and mouse input tools.

    Tools:
        - press_key: Press keyboard key
        - mouse_move: Move mouse cursor
        - handle_dialog: Handle browser dialogs
    """

    TOOLS = ["press_key", "mouse_move", "handle_dialog"]


class JavaScriptTools:
    """JavaScript execution tools.

    Tools:
        - evaluate: Execute JavaScript in page
    """

    TOOLS = ["evaluate"]


# All tool groups
ALL_TOOL_GROUPS = [
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
]

# Flat list of all tools
ALL_TOOLS = []
for group in ALL_TOOL_GROUPS:
    ALL_TOOLS.extend(group.TOOLS)
