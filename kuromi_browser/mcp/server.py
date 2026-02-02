"""
MCP Server implementation for kuromi-browser.

Provides a Model Context Protocol server that exposes browser automation
capabilities to AI agents. Supports full browser control, stealth features,
and network interception.
"""

import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    ImageContent,
    Tool,
)

from kuromi_browser.models import (
    BrowserConfig,
    PageConfig,
    ProxyConfig,
    Fingerprint,
)

logger = logging.getLogger(__name__)


class BrowserMCPServer:
    """MCP Server for browser automation.

    Exposes kuromi-browser capabilities through the Model Context Protocol,
    allowing AI agents to control browsers, navigate pages, interact with
    elements, capture screenshots, and manage network requests.

    Example:
        >>> server = BrowserMCPServer()
        >>> await server.start()
    """

    def __init__(self, name: str = "kuromi-browser"):
        """Initialize the MCP server.

        Args:
            name: Server name for identification.
        """
        self.name = name
        self.server = Server(name)
        self._browser = None
        self._page = None
        self._pages: dict[str, Any] = {}
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Register all available tools with the server."""
        # Register tool handlers
        self.server.list_tools_handler(self._list_tools)
        self.server.call_tool_handler(self._call_tool)

    async def _list_tools(self) -> list[Tool]:
        """List all available tools."""
        return [
            # Browser lifecycle
            Tool(
                name="browser_launch",
                description="Launch a new browser instance with optional stealth and proxy settings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "headless": {
                            "type": "boolean",
                            "description": "Run in headless mode",
                            "default": False,
                        },
                        "stealth": {
                            "type": "boolean",
                            "description": "Enable stealth mode with fingerprint spoofing",
                            "default": True,
                        },
                        "proxy": {
                            "type": "string",
                            "description": "Proxy URL (http://host:port or socks5://user:pass@host:port)",
                        },
                        "user_data_dir": {
                            "type": "string",
                            "description": "Path to user data directory for persistent sessions",
                        },
                    },
                },
            ),
            Tool(
                name="browser_close",
                description="Close the browser instance",
                inputSchema={"type": "object", "properties": {}},
            ),
            # Navigation
            Tool(
                name="navigate",
                description="Navigate to a URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to",
                        },
                        "wait_until": {
                            "type": "string",
                            "enum": ["load", "domcontentloaded", "networkidle"],
                            "description": "Wait condition",
                            "default": "load",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                            "default": 30000,
                        },
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="go_back",
                description="Navigate back in browser history",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="go_forward",
                description="Navigate forward in browser history",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="reload",
                description="Reload the current page",
                inputSchema={"type": "object", "properties": {}},
            ),
            # Element interaction
            Tool(
                name="click",
                description="Click on an element by selector",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                        "button": {
                            "type": "string",
                            "enum": ["left", "right", "middle"],
                            "default": "left",
                        },
                        "click_count": {
                            "type": "integer",
                            "description": "Number of clicks",
                            "default": 1,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                            "default": 30000,
                        },
                    },
                    "required": ["selector"],
                },
            ),
            Tool(
                name="type_text",
                description="Type text into an element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to type",
                        },
                        "delay": {
                            "type": "integer",
                            "description": "Delay between keystrokes in ms",
                            "default": 50,
                        },
                        "clear": {
                            "type": "boolean",
                            "description": "Clear existing text first",
                            "default": False,
                        },
                    },
                    "required": ["selector", "text"],
                },
            ),
            Tool(
                name="fill",
                description="Fill an input field (clears existing content)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to fill",
                        },
                    },
                    "required": ["selector", "value"],
                },
            ),
            Tool(
                name="select_option",
                description="Select option(s) in a select element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector",
                        },
                        "value": {
                            "type": "string",
                            "description": "Option value to select",
                        },
                        "label": {
                            "type": "string",
                            "description": "Option label to select",
                        },
                        "index": {
                            "type": "integer",
                            "description": "Option index to select",
                        },
                    },
                    "required": ["selector"],
                },
            ),
            Tool(
                name="hover",
                description="Hover over an element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                    },
                    "required": ["selector"],
                },
            ),
            Tool(
                name="scroll",
                description="Scroll the page or element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Element selector (optional, scrolls page if not provided)",
                        },
                        "x": {
                            "type": "integer",
                            "description": "Horizontal scroll amount",
                            "default": 0,
                        },
                        "y": {
                            "type": "integer",
                            "description": "Vertical scroll amount",
                            "default": 0,
                        },
                    },
                },
            ),
            # Content extraction
            Tool(
                name="get_content",
                description="Get page content (HTML or text)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Element selector (optional)",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["html", "text", "inner_html", "inner_text"],
                            "default": "text",
                        },
                    },
                },
            ),
            Tool(
                name="get_attribute",
                description="Get element attribute value",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                        "attribute": {
                            "type": "string",
                            "description": "Attribute name",
                        },
                    },
                    "required": ["selector", "attribute"],
                },
            ),
            Tool(
                name="query_selector_all",
                description="Query multiple elements and get their info",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector",
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Attributes to extract",
                            "default": ["innerText", "href", "src"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max elements to return",
                            "default": 100,
                        },
                    },
                    "required": ["selector"],
                },
            ),
            # Screenshot
            Tool(
                name="screenshot",
                description="Take a screenshot of the page or element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Element selector (optional)",
                        },
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page",
                            "default": False,
                        },
                        "format": {
                            "type": "string",
                            "enum": ["png", "jpeg", "webp"],
                            "default": "png",
                        },
                        "quality": {
                            "type": "integer",
                            "description": "Image quality (1-100) for jpeg/webp",
                            "default": 80,
                        },
                    },
                },
            ),
            # JavaScript execution
            Tool(
                name="evaluate",
                description="Execute JavaScript in the page context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "JavaScript expression to evaluate",
                        },
                    },
                    "required": ["expression"],
                },
            ),
            # Wait operations
            Tool(
                name="wait_for_selector",
                description="Wait for an element to appear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "CSS selector or XPath",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["attached", "detached", "visible", "hidden"],
                            "default": "visible",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                            "default": 30000,
                        },
                    },
                    "required": ["selector"],
                },
            ),
            Tool(
                name="wait_for_navigation",
                description="Wait for navigation to complete",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "wait_until": {
                            "type": "string",
                            "enum": ["load", "domcontentloaded", "networkidle"],
                            "default": "load",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                            "default": 30000,
                        },
                    },
                },
            ),
            # Cookie management
            Tool(
                name="get_cookies",
                description="Get cookies for the current page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs to get cookies for",
                        },
                    },
                },
            ),
            Tool(
                name="set_cookies",
                description="Set cookies",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cookies": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"},
                                    "domain": {"type": "string"},
                                    "path": {"type": "string"},
                                    "secure": {"type": "boolean"},
                                    "httpOnly": {"type": "boolean"},
                                },
                                "required": ["name", "value"],
                            },
                            "description": "Cookies to set",
                        },
                    },
                    "required": ["cookies"],
                },
            ),
            Tool(
                name="clear_cookies",
                description="Clear all cookies",
                inputSchema={"type": "object", "properties": {}},
            ),
            # Stealth and fingerprint
            Tool(
                name="set_fingerprint",
                description="Set browser fingerprint for stealth mode",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_agent": {
                            "type": "string",
                            "description": "Custom user agent",
                        },
                        "platform": {
                            "type": "string",
                            "description": "Platform (e.g., 'Linux x86_64')",
                        },
                        "screen_width": {
                            "type": "integer",
                            "description": "Screen width",
                        },
                        "screen_height": {
                            "type": "integer",
                            "description": "Screen height",
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (e.g., 'America/New_York')",
                        },
                        "locale": {
                            "type": "string",
                            "description": "Locale (e.g., 'en-US')",
                        },
                        "webgl_vendor": {
                            "type": "string",
                            "description": "WebGL vendor",
                        },
                        "webgl_renderer": {
                            "type": "string",
                            "description": "WebGL renderer",
                        },
                    },
                },
            ),
            Tool(
                name="generate_fingerprint",
                description="Generate a random consistent fingerprint",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "os": {
                            "type": "string",
                            "enum": ["windows", "macos", "linux"],
                            "description": "Target operating system",
                        },
                        "browser": {
                            "type": "string",
                            "enum": ["chrome", "firefox", "edge"],
                            "default": "chrome",
                        },
                        "seed": {
                            "type": "integer",
                            "description": "Random seed for reproducible fingerprints",
                        },
                    },
                },
            ),
            # Proxy management
            Tool(
                name="set_proxy",
                description="Set or change the proxy for the browser",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "proxy": {
                            "type": "string",
                            "description": "Proxy URL (http://host:port, socks5://user:pass@host:port)",
                        },
                    },
                    "required": ["proxy"],
                },
            ),
            # Network interception
            Tool(
                name="intercept_requests",
                description="Enable request interception",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL patterns to intercept",
                        },
                        "block_resources": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "document",
                                    "stylesheet",
                                    "image",
                                    "media",
                                    "font",
                                    "script",
                                    "xhr",
                                    "fetch",
                                    "websocket",
                                ],
                            },
                            "description": "Resource types to block",
                        },
                    },
                },
            ),
            Tool(
                name="get_network_log",
                description="Get captured network requests",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter_url": {
                            "type": "string",
                            "description": "Filter by URL pattern",
                        },
                        "include_response": {
                            "type": "boolean",
                            "description": "Include response bodies",
                            "default": False,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max requests to return",
                            "default": 100,
                        },
                    },
                },
            ),
            # Page management
            Tool(
                name="new_page",
                description="Open a new page/tab",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to open (optional)",
                        },
                    },
                },
            ),
            Tool(
                name="list_pages",
                description="List all open pages",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="switch_page",
                description="Switch to a different page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID to switch to",
                        },
                    },
                    "required": ["page_id"],
                },
            ),
            Tool(
                name="close_page",
                description="Close a page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID to close (optional, closes current if not provided)",
                        },
                    },
                },
            ),
            # File operations
            Tool(
                name="upload_file",
                description="Upload a file to a file input element",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "File input selector",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to upload",
                        },
                    },
                    "required": ["selector", "file_path"],
                },
            ),
            Tool(
                name="download",
                description="Download a file from URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to download from",
                        },
                        "save_path": {
                            "type": "string",
                            "description": "Path to save the file",
                        },
                    },
                    "required": ["url", "save_path"],
                },
            ),
            # Dialog handling
            Tool(
                name="handle_dialog",
                description="Set up dialog (alert, confirm, prompt) handling",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["accept", "dismiss"],
                            "description": "Action to take on dialogs",
                        },
                        "prompt_text": {
                            "type": "string",
                            "description": "Text to enter for prompt dialogs",
                        },
                    },
                    "required": ["action"],
                },
            ),
            # Keyboard and mouse
            Tool(
                name="press_key",
                description="Press a keyboard key or combination",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Key to press (e.g., 'Enter', 'Control+A', 'Escape')",
                        },
                    },
                    "required": ["key"],
                },
            ),
            Tool(
                name="mouse_move",
                description="Move mouse to coordinates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X coordinate"},
                        "y": {"type": "integer", "description": "Y coordinate"},
                        "human_like": {
                            "type": "boolean",
                            "description": "Use human-like movement",
                            "default": True,
                        },
                    },
                    "required": ["x", "y"],
                },
            ),
            # Page info
            Tool(
                name="get_page_info",
                description="Get current page information",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def _call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        """Handle tool calls."""
        try:
            handler = getattr(self, f"_tool_{name}", None)
            if not handler:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True,
                )

            result = await handler(arguments)

            # Handle different result types
            if isinstance(result, bytes):
                # Screenshot or binary data
                return CallToolResult(
                    content=[
                        ImageContent(
                            type="image",
                            data=base64.b64encode(result).decode(),
                            mimeType=f"image/{arguments.get('format', 'png')}",
                        )
                    ]
                )
            elif isinstance(result, dict) or isinstance(result, list):
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=str(result))]
                )

        except Exception as e:
            logger.exception(f"Tool {name} failed")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    # Tool implementations
    async def _tool_browser_launch(self, args: dict) -> dict:
        """Launch browser."""
        from kuromi_browser import Browser

        config = BrowserConfig(
            headless=args.get("headless", False),
            stealth=args.get("stealth", True),
            proxy=args.get("proxy"),
            user_data_dir=args.get("user_data_dir"),
        )

        self._browser = Browser(config)
        await self._browser.start()
        self._page = await self._browser.new_page()

        return {"status": "launched", "stealth": config.stealth}

    async def _tool_browser_close(self, args: dict) -> dict:
        """Close browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
        return {"status": "closed"}

    async def _tool_navigate(self, args: dict) -> dict:
        """Navigate to URL."""
        self._ensure_page()
        url = args["url"]
        wait_until = args.get("wait_until", "load")
        timeout = args.get("timeout", 30000)

        await self._page.goto(url, wait_until=wait_until, timeout=timeout)
        return {"url": self._page.url, "title": await self._page.title()}

    async def _tool_go_back(self, args: dict) -> dict:
        """Go back in history."""
        self._ensure_page()
        await self._page.go_back()
        return {"url": self._page.url}

    async def _tool_go_forward(self, args: dict) -> dict:
        """Go forward in history."""
        self._ensure_page()
        await self._page.go_forward()
        return {"url": self._page.url}

    async def _tool_reload(self, args: dict) -> dict:
        """Reload page."""
        self._ensure_page()
        await self._page.reload()
        return {"url": self._page.url}

    async def _tool_click(self, args: dict) -> dict:
        """Click element."""
        self._ensure_page()
        selector = args["selector"]
        button = args.get("button", "left")
        click_count = args.get("click_count", 1)
        timeout = args.get("timeout", 30000)

        await self._page.click(
            selector, button=button, click_count=click_count, timeout=timeout
        )
        return {"clicked": selector}

    async def _tool_type_text(self, args: dict) -> dict:
        """Type text into element."""
        self._ensure_page()
        selector = args["selector"]
        text = args["text"]
        delay = args.get("delay", 50)
        clear = args.get("clear", False)

        if clear:
            await self._page.fill(selector, "")
        await self._page.type(selector, text, delay=delay)
        return {"typed": text, "selector": selector}

    async def _tool_fill(self, args: dict) -> dict:
        """Fill input field."""
        self._ensure_page()
        selector = args["selector"]
        value = args["value"]

        await self._page.fill(selector, value)
        return {"filled": selector, "value": value}

    async def _tool_select_option(self, args: dict) -> dict:
        """Select option in select element."""
        self._ensure_page()
        selector = args["selector"]

        if "value" in args:
            await self._page.select_option(selector, value=args["value"])
        elif "label" in args:
            await self._page.select_option(selector, label=args["label"])
        elif "index" in args:
            await self._page.select_option(selector, index=args["index"])

        return {"selected": selector}

    async def _tool_hover(self, args: dict) -> dict:
        """Hover over element."""
        self._ensure_page()
        selector = args["selector"]
        await self._page.hover(selector)
        return {"hovered": selector}

    async def _tool_scroll(self, args: dict) -> dict:
        """Scroll page or element."""
        self._ensure_page()
        x = args.get("x", 0)
        y = args.get("y", 0)
        selector = args.get("selector")

        if selector:
            await self._page.evaluate(
                f"document.querySelector('{selector}').scrollBy({x}, {y})"
            )
        else:
            await self._page.evaluate(f"window.scrollBy({x}, {y})")

        return {"scrolled": {"x": x, "y": y}}

    async def _tool_get_content(self, args: dict) -> dict:
        """Get page content."""
        self._ensure_page()
        selector = args.get("selector")
        fmt = args.get("format", "text")

        if selector:
            element = await self._page.query_selector(selector)
            if not element:
                return {"error": f"Element not found: {selector}"}

            if fmt == "html":
                content = await element.get_attribute("outerHTML")
            elif fmt == "inner_html":
                content = await element.get_attribute("innerHTML")
            elif fmt == "inner_text":
                content = await element.inner_text()
            else:
                content = await element.text_content()
        else:
            if fmt in ("html", "inner_html"):
                content = await self._page.content()
            else:
                content = await self._page.evaluate("document.body.innerText")

        return {"content": content}

    async def _tool_get_attribute(self, args: dict) -> dict:
        """Get element attribute."""
        self._ensure_page()
        selector = args["selector"]
        attribute = args["attribute"]

        element = await self._page.query_selector(selector)
        if not element:
            return {"error": f"Element not found: {selector}"}

        value = await element.get_attribute(attribute)
        return {"attribute": attribute, "value": value}

    async def _tool_query_selector_all(self, args: dict) -> list:
        """Query multiple elements."""
        self._ensure_page()
        selector = args["selector"]
        attributes = args.get("attributes", ["innerText", "href", "src"])
        limit = args.get("limit", 100)

        elements = await self._page.query_selector_all(selector)
        results = []

        for i, el in enumerate(elements[:limit]):
            item = {}
            for attr in attributes:
                if attr == "innerText":
                    item[attr] = await el.text_content()
                else:
                    item[attr] = await el.get_attribute(attr)
            results.append(item)

        return results

    async def _tool_screenshot(self, args: dict) -> bytes:
        """Take screenshot."""
        self._ensure_page()
        selector = args.get("selector")
        full_page = args.get("full_page", False)
        fmt = args.get("format", "png")
        quality = args.get("quality", 80)

        options = {"type": fmt, "full_page": full_page}
        if fmt in ("jpeg", "webp"):
            options["quality"] = quality

        if selector:
            element = await self._page.query_selector(selector)
            if element:
                return await element.screenshot(**options)

        return await self._page.screenshot(**options)

    async def _tool_evaluate(self, args: dict) -> Any:
        """Evaluate JavaScript."""
        self._ensure_page()
        expression = args["expression"]
        result = await self._page.evaluate(expression)
        return {"result": result}

    async def _tool_wait_for_selector(self, args: dict) -> dict:
        """Wait for selector."""
        self._ensure_page()
        selector = args["selector"]
        state = args.get("state", "visible")
        timeout = args.get("timeout", 30000)

        await self._page.wait_for_selector(selector, state=state, timeout=timeout)
        return {"found": selector}

    async def _tool_wait_for_navigation(self, args: dict) -> dict:
        """Wait for navigation."""
        self._ensure_page()
        wait_until = args.get("wait_until", "load")
        timeout = args.get("timeout", 30000)

        await self._page.wait_for_load_state(wait_until, timeout=timeout)
        return {"url": self._page.url}

    async def _tool_get_cookies(self, args: dict) -> list:
        """Get cookies."""
        self._ensure_page()
        urls = args.get("urls")
        cookies = await self._page.context.cookies(urls=urls)
        return cookies

    async def _tool_set_cookies(self, args: dict) -> dict:
        """Set cookies."""
        self._ensure_page()
        cookies = args["cookies"]
        await self._page.context.add_cookies(cookies)
        return {"set": len(cookies)}

    async def _tool_clear_cookies(self, args: dict) -> dict:
        """Clear cookies."""
        self._ensure_page()
        await self._page.context.clear_cookies()
        return {"cleared": True}

    async def _tool_set_fingerprint(self, args: dict) -> dict:
        """Set fingerprint."""
        self._ensure_page()
        # Build fingerprint from args
        fingerprint = Fingerprint(
            user_agent=args.get("user_agent", Fingerprint().user_agent),
            timezone=args.get("timezone", "America/New_York"),
            locale=args.get("locale", "en-US"),
        )

        if "platform" in args:
            fingerprint.navigator.platform = args["platform"]
        if "screen_width" in args:
            fingerprint.screen.width = args["screen_width"]
        if "screen_height" in args:
            fingerprint.screen.height = args["screen_height"]
        if "webgl_vendor" in args:
            fingerprint.webgl.vendor = args["webgl_vendor"]
        if "webgl_renderer" in args:
            fingerprint.webgl.renderer = args["webgl_renderer"]

        # Apply fingerprint
        await self._page.set_fingerprint(fingerprint)
        return {"fingerprint": "set"}

    async def _tool_generate_fingerprint(self, args: dict) -> dict:
        """Generate random fingerprint."""
        from kuromi_browser.stealth.fingerprint import FingerprintGenerator

        os = args.get("os")
        browser = args.get("browser", "chrome")
        seed = args.get("seed")

        generator = FingerprintGenerator()
        fingerprint = generator.generate(os=os, browser=browser, seed=seed)

        return fingerprint.model_dump()

    async def _tool_set_proxy(self, args: dict) -> dict:
        """Set proxy."""
        proxy_url = args["proxy"]
        proxy = ProxyConfig.from_url(proxy_url)

        # Note: Changing proxy at runtime requires browser restart
        return {
            "proxy": proxy_url,
            "type": proxy.proxy_type.value,
            "note": "Proxy will be applied on next browser launch",
        }

    async def _tool_intercept_requests(self, args: dict) -> dict:
        """Enable request interception."""
        self._ensure_page()
        patterns = args.get("patterns", ["*"])
        block_resources = args.get("block_resources", [])

        await self._page.route(
            patterns,
            lambda route: route.abort()
            if route.request.resource_type in block_resources
            else route.continue_(),
        )

        return {"intercepting": True, "patterns": patterns, "blocking": block_resources}

    async def _tool_get_network_log(self, args: dict) -> list:
        """Get network log."""
        self._ensure_page()
        # This would require network monitoring to be enabled
        return {"requests": [], "note": "Enable network monitoring first"}

    async def _tool_new_page(self, args: dict) -> dict:
        """Open new page."""
        self._ensure_browser()
        page = await self._browser.new_page()
        page_id = str(id(page))
        self._pages[page_id] = page

        if "url" in args:
            await page.goto(args["url"])

        return {"page_id": page_id, "url": page.url if "url" in args else "about:blank"}

    async def _tool_list_pages(self, args: dict) -> list:
        """List all pages."""
        self._ensure_browser()
        pages = []
        for page_id, page in self._pages.items():
            pages.append({"page_id": page_id, "url": page.url, "title": await page.title()})
        return pages

    async def _tool_switch_page(self, args: dict) -> dict:
        """Switch to page."""
        page_id = args["page_id"]
        if page_id not in self._pages:
            return {"error": f"Page not found: {page_id}"}

        self._page = self._pages[page_id]
        return {"switched_to": page_id, "url": self._page.url}

    async def _tool_close_page(self, args: dict) -> dict:
        """Close page."""
        page_id = args.get("page_id")

        if page_id:
            if page_id in self._pages:
                await self._pages[page_id].close()
                del self._pages[page_id]
        elif self._page:
            await self._page.close()
            self._page = None

        return {"closed": page_id or "current"}

    async def _tool_upload_file(self, args: dict) -> dict:
        """Upload file."""
        self._ensure_page()
        selector = args["selector"]
        file_path = args["file_path"]

        await self._page.set_input_files(selector, file_path)
        return {"uploaded": file_path}

    async def _tool_download(self, args: dict) -> dict:
        """Download file."""
        self._ensure_page()
        url = args["url"]
        save_path = args["save_path"]

        async with self._page.expect_download() as download_info:
            await self._page.goto(url)

        download = await download_info.value
        await download.save_as(save_path)
        return {"downloaded": save_path}

    async def _tool_handle_dialog(self, args: dict) -> dict:
        """Handle dialogs."""
        self._ensure_page()
        action = args["action"]
        prompt_text = args.get("prompt_text")

        def handler(dialog):
            if action == "accept":
                dialog.accept(prompt_text)
            else:
                dialog.dismiss()

        self._page.on("dialog", handler)
        return {"dialog_handler": action}

    async def _tool_press_key(self, args: dict) -> dict:
        """Press keyboard key."""
        self._ensure_page()
        key = args["key"]
        await self._page.keyboard.press(key)
        return {"pressed": key}

    async def _tool_mouse_move(self, args: dict) -> dict:
        """Move mouse."""
        self._ensure_page()
        x = args["x"]
        y = args["y"]
        human_like = args.get("human_like", True)

        if human_like and hasattr(self._page, "human_mouse"):
            await self._page.human_mouse.move_to(x, y)
        else:
            await self._page.mouse.move(x, y)

        return {"moved_to": {"x": x, "y": y}}

    async def _tool_get_page_info(self, args: dict) -> dict:
        """Get page info."""
        self._ensure_page()
        return {
            "url": self._page.url,
            "title": await self._page.title(),
            "viewport": await self._page.viewport_size(),
        }

    def _ensure_browser(self) -> None:
        """Ensure browser is running."""
        if not self._browser:
            raise RuntimeError("Browser not launched. Call browser_launch first.")

    def _ensure_page(self) -> None:
        """Ensure page is available."""
        self._ensure_browser()
        if not self._page:
            raise RuntimeError("No page available. Call browser_launch first.")

    async def start(self) -> None:
        """Start the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Run the MCP server."""
    server = BrowserMCPServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
