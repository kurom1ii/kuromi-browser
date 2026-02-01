"""
BrowserPage - CDP-based browser control.

Provides full browser automation capabilities using Chrome DevTools Protocol.
This is the most feature-complete mode, supporting JavaScript execution,
real rendering, and all browser APIs.
"""

import asyncio
import base64
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

from kuromi_browser.interfaces import BaseElement, BasePage
from kuromi_browser.models import PageMode

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession
    from kuromi_browser.models import (
        Cookie,
        Fingerprint,
        NetworkResponse,
        PageConfig,
    )


class BrowserElement(BaseElement):
    """CDP-based DOM element implementation."""

    def __init__(
        self,
        page: "BrowserPage",
        object_id: str,
        backend_node_id: Optional[int] = None,
        node_id: Optional[int] = None,
    ) -> None:
        self._page = page
        self._object_id = object_id
        self._backend_node_id = backend_node_id
        self._node_id = node_id
        self._tag_name: Optional[str] = None

    @property
    def object_id(self) -> str:
        """Get the CDP object ID."""
        return self._object_id

    @property
    def tag_name(self) -> str:
        if self._tag_name is None:
            raise RuntimeError("Element not initialized - call _init() first")
        return self._tag_name

    async def _init(self) -> "BrowserElement":
        """Initialize element properties."""
        self._tag_name = await self._call_function(
            "function() { return this.tagName.toLowerCase(); }"
        )
        return self

    async def _call_function(
        self, func: str, *args: Any, return_value: bool = True
    ) -> Any:
        """Call a function on this element."""
        result = await self._page._cdp.send(
            "Runtime.callFunctionOn",
            {
                "objectId": self._object_id,
                "functionDeclaration": func,
                "arguments": [{"value": arg} for arg in args],
                "returnByValue": return_value,
                "awaitPromise": True,
            },
        )
        if "exceptionDetails" in result:
            raise RuntimeError(
                f"JavaScript error: {result['exceptionDetails'].get('text', 'Unknown')}"
            )
        if return_value:
            return result.get("result", {}).get("value")
        return result.get("result", {}).get("objectId")

    async def get_attribute(self, name: str) -> Optional[str]:
        """Get element attribute."""
        return await self._call_function(
            f"function() {{ return this.getAttribute({repr(name)}); }}"
        )

    async def get_property(self, name: str) -> Any:
        """Get element property."""
        return await self._call_function(f"function() {{ return this[{repr(name)}]; }}")

    async def text_content(self) -> Optional[str]:
        """Get text content."""
        return await self._call_function("function() { return this.textContent; }")

    async def inner_text(self) -> str:
        """Get inner text."""
        result = await self._call_function("function() { return this.innerText; }")
        return result or ""

    async def inner_html(self) -> str:
        """Get inner HTML."""
        result = await self._call_function("function() { return this.innerHTML; }")
        return result or ""

    async def outer_html(self) -> str:
        """Get outer HTML."""
        result = await self._call_function("function() { return this.outerHTML; }")
        return result or ""

    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Get bounding box."""
        result = await self._call_function(
            """
            function() {
                const rect = this.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return null;
                return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
            }
        """
        )
        return result

    async def is_visible(self) -> bool:
        """Check if element is visible."""
        result = await self._call_function(
            """
            function() {
                const style = window.getComputedStyle(this);
                return style.display !== 'none' &&
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0' &&
                       this.offsetWidth > 0 &&
                       this.offsetHeight > 0;
            }
        """
        )
        return bool(result)

    async def is_enabled(self) -> bool:
        """Check if element is enabled."""
        result = await self._call_function("function() { return !this.disabled; }")
        return bool(result)

    async def is_checked(self) -> bool:
        """Check if checkbox/radio is checked."""
        result = await self._call_function("function() { return !!this.checked; }")
        return bool(result)

    async def _scroll_into_view_if_needed(self) -> None:
        """Scroll element into view if needed."""
        await self._call_function(
            """
            function() {
                if (this.scrollIntoViewIfNeeded) {
                    this.scrollIntoViewIfNeeded(true);
                } else {
                    this.scrollIntoView({block: 'center', inline: 'center'});
                }
            }
        """
        )

    async def _get_click_point(
        self, position: Optional[dict[str, float]] = None
    ) -> tuple[float, float]:
        """Get click coordinates."""
        box = await self.bounding_box()
        if not box:
            raise RuntimeError("Element has no bounding box - may not be visible")

        if position:
            x = box["x"] + position.get("x", box["width"] / 2)
            y = box["y"] + position.get("y", box["height"] / 2)
        else:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2

        return x, y

    async def click(
        self,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click the element."""
        if not force:
            await self._scroll_into_view_if_needed()
            await asyncio.sleep(0.05)  # Small delay for scroll

        x, y = await self._get_click_point(position)

        # Mouse move
        await self._page._cdp.send(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": x, "y": y},
        )

        # Mouse down
        await self._page._cdp.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
            },
        )

        if delay > 0:
            await asyncio.sleep(delay / 1000)

        # Mouse up
        await self._page._cdp.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
            },
        )

    async def dblclick(
        self,
        *,
        button: str = "left",
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Double click the element."""
        await self.click(
            button=button,
            click_count=2,
            delay=delay,
            force=force,
            modifiers=modifiers,
            position=position,
        )

    async def hover(
        self,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over element."""
        if not force:
            await self._scroll_into_view_if_needed()

        x, y = await self._get_click_point(position)
        await self._page._cdp.send(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": x, "y": y},
        )

    async def fill(
        self,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill input with value."""
        await self.focus()
        # Clear existing value
        await self._call_function("function() { this.value = ''; }")
        # Set new value
        await self._call_function(f"function() {{ this.value = {repr(value)}; }}")
        # Trigger events
        await self._call_function(
            """
            function() {
                this.dispatchEvent(new Event('input', {bubbles: true}));
                this.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """
        )

    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into element character by character."""
        await self.focus()
        for char in text:
            await self._page._cdp.send(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "text": char},
            )
            await self._page._cdp.send(
                "Input.dispatchKeyEvent",
                {"type": "keyUp", "text": char},
            )
            if delay > 0:
                await asyncio.sleep(delay / 1000)

    async def press(
        self,
        key: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Press a key."""
        await self._page._cdp.send(
            "Input.dispatchKeyEvent",
            {"type": "keyDown", "key": key},
        )
        if delay > 0:
            await asyncio.sleep(delay / 1000)
        await self._page._cdp.send(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": key},
        )

    async def select_option(
        self,
        *values: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in select element."""
        selected = await self._call_function(
            f"""
            function() {{
                const values = {list(values)};
                const options = Array.from(this.options);
                const selected = [];
                for (const opt of options) {{
                    opt.selected = values.includes(opt.value);
                    if (opt.selected) selected.push(opt.value);
                }}
                this.dispatchEvent(new Event('change', {{bubbles: true}}));
                return selected;
            }}
        """
        )
        return selected or []

    async def check(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Check checkbox."""
        if not await self.is_checked():
            await self.click(force=force)

    async def uncheck(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Uncheck checkbox."""
        if await self.is_checked():
            await self.click(force=force)

    async def focus(self) -> None:
        """Focus the element."""
        await self._call_function("function() { this.focus(); }")

    async def scroll_into_view(self) -> None:
        """Scroll element into view."""
        await self._call_function(
            "function() { this.scrollIntoView({block: 'center', inline: 'center'}); }"
        )

    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take screenshot of element."""
        box = await self.bounding_box()
        if not box:
            raise RuntimeError("Element has no bounding box")

        return await self._page.screenshot(
            path=path,
            clip=box,
            type=type,
            quality=quality,
            omit_background=omit_background,
        )

    async def query_selector(self, selector: str) -> Optional["BrowserElement"]:
        """Find child element."""
        object_id = await self._call_function(
            f"function() {{ return this.querySelector({repr(selector)}); }}",
            return_value=False,
        )
        if object_id:
            elem = BrowserElement(self._page, object_id)
            await elem._init()
            return elem
        return None

    async def query_selector_all(self, selector: str) -> list["BrowserElement"]:
        """Find all child elements."""
        result = await self._page._cdp.send(
            "Runtime.callFunctionOn",
            {
                "objectId": self._object_id,
                "functionDeclaration": f"function() {{ return Array.from(this.querySelectorAll({repr(selector)})); }}",
                "returnByValue": False,
            },
        )

        elements: list["BrowserElement"] = []
        obj = result.get("result", {})
        if obj.get("objectId"):
            props = await self._page._cdp.send(
                "Runtime.getProperties",
                {"objectId": obj["objectId"], "ownProperties": True},
            )
            for prop in props.get("result", []):
                if prop.get("name", "").isdigit():
                    value = prop.get("value", {})
                    if value.get("objectId"):
                        elem = BrowserElement(self._page, value["objectId"])
                        await elem._init()
                        elements.append(elem)
        return elements

    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript on this element."""
        return await self._call_function(expression, *args)


class BrowserPage(BasePage):
    """CDP-based browser page with full automation capabilities.

    Provides complete browser control including:
    - JavaScript execution
    - Real DOM manipulation
    - Network interception
    - Screenshot/PDF generation
    - Cookie management
    - Event handling
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        config: Optional["PageConfig"] = None,
        fingerprint: Optional["Fingerprint"] = None,
    ) -> None:
        """Initialize BrowserPage.

        Args:
            cdp_session: CDP session for browser communication.
            config: Optional page configuration.
            fingerprint: Optional fingerprint for stealth mode.
        """
        self._cdp = cdp_session
        self._config = config
        self._fingerprint = fingerprint
        self._url = ""
        self._title = ""
        self._event_handlers: dict[str, list[Callable[..., Any]]] = {}
        self._frame_id: Optional[str] = None
        self._initialized = False

    @property
    def cdp(self) -> "CDPSession":
        """Get the CDP session."""
        return self._cdp

    @property
    def url(self) -> str:
        return self._url

    @property
    def title(self) -> str:
        return self._title

    @property
    def mode(self) -> PageMode:
        return PageMode.BROWSER

    @property
    def fingerprint(self) -> Optional["Fingerprint"]:
        """Get the fingerprint configuration."""
        return self._fingerprint

    async def _ensure_initialized(self) -> None:
        """Ensure page domains are enabled."""
        if not self._initialized:
            await self._cdp.send("Page.enable")
            await self._cdp.send("Runtime.enable")
            await self._cdp.send("Network.enable")
            await self._cdp.send("DOM.enable")
            self._initialized = True

    async def _get_frame_id(self) -> str:
        """Get the main frame ID."""
        if self._frame_id is None:
            result = await self._cdp.send("Page.getFrameTree")
            self._frame_id = result["frameTree"]["frame"]["id"]
        return self._frame_id

    async def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
    ) -> Optional["NetworkResponse"]:
        """Navigate to a URL."""
        await self._ensure_initialized()

        params: dict[str, Any] = {"url": url}
        if referer:
            params["referer"] = referer

        result = await self._cdp.send("Page.navigate", params)

        if "errorText" in result:
            raise RuntimeError(f"Navigation failed: {result['errorText']}")

        self._frame_id = result.get("frameId")
        self._url = url

        await self.wait_for_load_state(wait_until, timeout=timeout)
        await self._update_title()

        return None

    async def _update_title(self) -> None:
        """Update the cached page title."""
        try:
            result = await self._cdp.send(
                "Runtime.evaluate", {"expression": "document.title"}
            )
            self._title = result.get("result", {}).get("value", "")
        except Exception:
            pass

    async def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Reload the page."""
        await self._cdp.send("Page.reload")
        await self.wait_for_load_state(wait_until, timeout=timeout)
        return None

    async def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate back in history."""
        history = await self._cdp.send("Page.getNavigationHistory")
        current_index = history["currentIndex"]
        if current_index > 0:
            entry = history["entries"][current_index - 1]
            await self._cdp.send(
                "Page.navigateToHistoryEntry", {"entryId": entry["id"]}
            )
            await self.wait_for_load_state(wait_until, timeout=timeout)
            self._url = entry.get("url", "")
        return None

    async def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate forward in history."""
        history = await self._cdp.send("Page.getNavigationHistory")
        current_index = history["currentIndex"]
        entries = history["entries"]
        if current_index < len(entries) - 1:
            entry = entries[current_index + 1]
            await self._cdp.send(
                "Page.navigateToHistoryEntry", {"entryId": entry["id"]}
            )
            await self.wait_for_load_state(wait_until, timeout=timeout)
            self._url = entry.get("url", "")
        return None

    async def content(self) -> str:
        """Get page HTML content."""
        result = await self._cdp.send(
            "Runtime.evaluate", {"expression": "document.documentElement.outerHTML"}
        )
        return result.get("result", {}).get("value", "")

    async def set_content(
        self,
        html: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Set page HTML content."""
        frame_id = await self._get_frame_id()
        await self._cdp.send(
            "Page.setDocumentContent", {"frameId": frame_id, "html": html}
        )
        await self.wait_for_load_state(wait_until, timeout=timeout)

    async def query_selector(self, selector: str) -> Optional[BrowserElement]:
        """Find element by CSS selector."""
        result = await self._cdp.send(
            "Runtime.evaluate",
            {
                "expression": f"document.querySelector({repr(selector)})",
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("subtype") != "null":
            object_id = obj.get("objectId")
            if object_id:
                elem = BrowserElement(self, object_id)
                await elem._init()
                return elem
        return None

    async def query_selector_all(self, selector: str) -> list[BrowserElement]:
        """Find all elements matching CSS selector."""
        result = await self._cdp.send(
            "Runtime.evaluate",
            {
                "expression": f"Array.from(document.querySelectorAll({repr(selector)}))",
                "returnByValue": False,
            },
        )
        elements: list[BrowserElement] = []
        obj = result.get("result", {})
        if obj.get("objectId"):
            props = await self._cdp.send(
                "Runtime.getProperties",
                {"objectId": obj["objectId"], "ownProperties": True},
            )
            for prop in props.get("result", []):
                if prop.get("name", "").isdigit():
                    value = prop.get("value", {})
                    if value.get("objectId"):
                        elem = BrowserElement(self, value["objectId"])
                        await elem._init()
                        elements.append(elem)
        return elements

    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[BrowserElement]:
        """Wait for element to appear."""
        timeout_ms = int((timeout or 30) * 1000)
        interval = 100
        elapsed = 0

        while elapsed < timeout_ms:
            element = await self.query_selector(selector)
            if element:
                if state == "attached":
                    return element
                if state == "visible" and await element.is_visible():
                    return element
                if state == "hidden" and not await element.is_visible():
                    return element
            await asyncio.sleep(interval / 1000)
            elapsed += interval

        return None

    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for page load state."""
        timeout_ms = int((timeout or 30) * 1000)

        if state == "domcontentloaded":
            js = "document.readyState === 'interactive' || document.readyState === 'complete'"
        elif state == "networkidle":
            await asyncio.sleep(0.5)
            return
        else:
            js = "document.readyState === 'complete'"

        interval = 100
        elapsed = 0
        while elapsed < timeout_ms:
            result = await self._cdp.send("Runtime.evaluate", {"expression": js})
            if result.get("result", {}).get("value"):
                return
            await asyncio.sleep(interval / 1000)
            elapsed += interval

    async def wait_for_url(
        self,
        url: Union[str, Callable[[str], bool]],
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Wait for URL to match."""
        timeout_ms = int((timeout or 30) * 1000)
        interval = 100
        elapsed = 0

        while elapsed < timeout_ms:
            current = self._url
            if callable(url):
                if url(current):
                    return
            elif current == url or url in current:
                return
            await asyncio.sleep(interval / 1000)
            elapsed += interval

    async def wait_for_timeout(self, timeout: float) -> None:
        """Wait for specified milliseconds."""
        await asyncio.sleep(timeout / 1000)

    async def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click on element."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.click(
                button=button,
                click_count=click_count,
                delay=delay,
                force=force,
                modifiers=modifiers,
                position=position,
            )
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def dblclick(
        self,
        selector: str,
        *,
        button: str = "left",
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Double click on element."""
        await self.click(
            selector,
            button=button,
            click_count=2,
            delay=delay,
            force=force,
            modifiers=modifiers,
            position=position,
            timeout=timeout,
        )

    async def fill(
        self,
        selector: str,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill input field."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.fill(value, force=force)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into element."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.type(text, delay=delay)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def press(
        self,
        selector: str,
        key: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Press key on element."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.press(key, delay=delay)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def hover(
        self,
        selector: str,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over element."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.hover(force=force, modifiers=modifiers, position=position)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def select_option(
        self,
        selector: str,
        *values: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in select element."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            return await element.select_option(*values)
        raise RuntimeError(f"Element not found: {selector}")

    async def check(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Check checkbox."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.check(force=force)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def uncheck(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Uncheck checkbox."""
        element = await self.wait_for_selector(selector, timeout=timeout)
        if element:
            await element.uncheck(force=force)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript expression."""
        if not args:
            result = await self._cdp.send(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            )
            return result.get("result", {}).get("value")

        result = await self._cdp.send(
            "Runtime.evaluate", {"expression": "document", "returnByValue": False}
        )
        object_id = result.get("result", {}).get("objectId")

        call_result = await self._cdp.send(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": expression,
                "arguments": [{"value": arg} for arg in args],
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        return call_result.get("result", {}).get("value")

    async def evaluate_handle(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript and return handle."""
        result = await self._cdp.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": False,
                "awaitPromise": True,
            },
        )
        return result.get("result", {}).get("objectId")

    async def add_script_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
        type: str = "",
    ) -> BrowserElement:
        """Add script tag to page."""
        if url:
            js = f"const s=document.createElement('script');s.src={repr(url)};s.type={repr(type or 'text/javascript')};document.head.appendChild(s);s"
        elif content:
            js = f"const s=document.createElement('script');s.textContent={repr(content)};s.type={repr(type or 'text/javascript')};document.head.appendChild(s);s"
        elif path:
            with open(path, "r") as f:
                content = f.read()
            js = f"const s=document.createElement('script');s.textContent={repr(content)};s.type={repr(type or 'text/javascript')};document.head.appendChild(s);s"
        else:
            raise ValueError("Must provide url, path, or content")

        result = await self._cdp.send(
            "Runtime.evaluate", {"expression": js, "returnByValue": False}
        )
        elem = BrowserElement(self, result.get("result", {}).get("objectId", ""))
        await elem._init()
        return elem

    async def add_style_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
    ) -> BrowserElement:
        """Add style tag to page."""
        if url:
            js = f"const l=document.createElement('link');l.rel='stylesheet';l.href={repr(url)};document.head.appendChild(l);l"
        elif content:
            js = f"const s=document.createElement('style');s.textContent={repr(content)};document.head.appendChild(s);s"
        elif path:
            with open(path, "r") as f:
                content = f.read()
            js = f"const s=document.createElement('style');s.textContent={repr(content)};document.head.appendChild(s);s"
        else:
            raise ValueError("Must provide url, path, or content")

        result = await self._cdp.send(
            "Runtime.evaluate", {"expression": js, "returnByValue": False}
        )
        elem = BrowserElement(self, result.get("result", {}).get("objectId", ""))
        await elem._init()
        return elem

    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict[str, float]] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take screenshot."""
        params: dict[str, Any] = {
            "format": type,
            "captureBeyondViewport": full_page,
        }
        if quality and type in ("jpeg", "webp"):
            params["quality"] = quality
        if clip:
            params["clip"] = {
                "x": clip["x"],
                "y": clip["y"],
                "width": clip["width"],
                "height": clip["height"],
                "scale": 1,
            }
        if omit_background:
            params["omitBackground"] = True

        result = await self._cdp.send("Page.captureScreenshot", params)
        data = base64.b64decode(result["data"])

        if path:
            with open(path, "wb") as f:
                f.write(data)

        return data

    async def pdf(
        self,
        *,
        path: Optional[str] = None,
        scale: float = 1,
        display_header_footer: bool = False,
        header_template: str = "",
        footer_template: str = "",
        print_background: bool = False,
        landscape: bool = False,
        page_ranges: str = "",
        format: str = "Letter",
        width: Optional[str] = None,
        height: Optional[str] = None,
        margin: Optional[dict[str, str]] = None,
        prefer_css_page_size: bool = False,
    ) -> bytes:
        """Generate PDF."""
        params: dict[str, Any] = {
            "scale": scale,
            "displayHeaderFooter": display_header_footer,
            "printBackground": print_background,
            "landscape": landscape,
            "preferCSSPageSize": prefer_css_page_size,
        }
        if header_template:
            params["headerTemplate"] = header_template
        if footer_template:
            params["footerTemplate"] = footer_template
        if page_ranges:
            params["pageRanges"] = page_ranges

        result = await self._cdp.send("Page.printToPDF", params)
        data = base64.b64decode(result["data"])

        if path:
            with open(path, "wb") as f:
                f.write(data)

        return data

    async def get_cookies(
        self,
        *urls: str,
    ) -> list["Cookie"]:
        """Get cookies."""
        from kuromi_browser.models import Cookie

        params: dict[str, Any] = {}
        if urls:
            params["urls"] = list(urls)

        result = await self._cdp.send("Network.getCookies", params)
        cookies = []
        for c in result.get("cookies", []):
            cookies.append(
                Cookie(
                    name=c["name"],
                    value=c["value"],
                    domain=c.get("domain", ""),
                    path=c.get("path", "/"),
                    expires=c.get("expires"),
                    http_only=c.get("httpOnly", False),
                    secure=c.get("secure", False),
                    same_site=c.get("sameSite", "Lax"),
                )
            )
        return cookies

    async def set_cookies(
        self,
        *cookies: "Cookie",
    ) -> None:
        """Set cookies."""
        for cookie in cookies:
            params: dict[str, Any] = {
                "name": cookie.name,
                "value": cookie.value,
                "path": cookie.path,
                "secure": cookie.secure,
                "httpOnly": cookie.http_only,
                "sameSite": cookie.same_site,
            }
            if cookie.domain:
                params["domain"] = cookie.domain
            if cookie.expires:
                params["expires"] = cookie.expires
            await self._cdp.send("Network.setCookie", params)

    async def delete_cookies(
        self,
        *names: str,
    ) -> None:
        """Delete specific cookies."""
        for name in names:
            await self._cdp.send("Network.deleteCookies", {"name": name})

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        await self._cdp.send("Network.clearBrowserCookies")

    async def set_extra_http_headers(
        self,
        headers: dict[str, str],
    ) -> None:
        """Set extra HTTP headers."""
        await self._cdp.send("Network.setExtraHTTPHeaders", {"headers": headers})

    async def set_viewport(
        self,
        width: int,
        height: int,
        *,
        device_scale_factor: float = 1,
        is_mobile: bool = False,
        has_touch: bool = False,
    ) -> None:
        """Set viewport size."""
        await self._cdp.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": device_scale_factor,
                "mobile": is_mobile,
            },
        )
        if has_touch:
            await self._cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": True})

    async def expose_function(
        self,
        name: str,
        callback: Callable[..., Any],
    ) -> None:
        """Expose function to page context."""
        await self._cdp.send("Runtime.addBinding", {"name": name})

        def on_binding_called(params: dict[str, Any]) -> None:
            if params.get("name") == name:
                asyncio.create_task(self._handle_binding(callback, params))

        self._cdp.on("Runtime.bindingCalled", on_binding_called)

    async def _handle_binding(
        self,
        callback: Callable[..., Any],
        params: dict[str, Any],
    ) -> None:
        """Handle exposed function call."""
        import json

        args = json.loads(params.get("payload", "[]"))
        result = callback(*args)
        if asyncio.iscoroutine(result):
            result = await result

    async def route(
        self,
        url: Union[str, Callable[[str], bool]],
        handler: Callable[..., Any],
    ) -> None:
        """Intercept network requests."""
        await self._cdp.send("Fetch.enable")

        def on_request(params: dict[str, Any]) -> None:
            request_url = params.get("request", {}).get("url", "")
            match = False
            if callable(url):
                match = url(request_url)
            else:
                match = url in request_url

            if match:
                asyncio.create_task(handler(params))
            else:
                asyncio.create_task(
                    self._cdp.send(
                        "Fetch.continueRequest", {"requestId": params["requestId"]}
                    )
                )

        self._cdp.on("Fetch.requestPaused", on_request)

    async def unroute(
        self,
        url: Union[str, Callable[[str], bool]],
    ) -> None:
        """Remove route handler."""
        await self._cdp.send("Fetch.disable")

    def on(
        self,
        event: str,
        handler: Callable[..., Any],
    ) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(
        self,
        event: str,
        handler: Callable[..., Any],
    ) -> None:
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)

    async def close(self) -> None:
        """Close the page."""
        try:
            await self._cdp.send("Page.close")
        except Exception:
            pass

    async def bring_to_front(self) -> None:
        """Bring page to front."""
        await self._cdp.send("Page.bringToFront")

    async def emulate_media(
        self,
        *,
        media: Optional[str] = None,
        color_scheme: Optional[str] = None,
        reduced_motion: Optional[str] = None,
    ) -> None:
        """Emulate media features."""
        features = []
        if color_scheme:
            features.append({"name": "prefers-color-scheme", "value": color_scheme})
        if reduced_motion:
            features.append({"name": "prefers-reduced-motion", "value": reduced_motion})

        params: dict[str, Any] = {}
        if media:
            params["media"] = media
        if features:
            params["features"] = features

        await self._cdp.send("Emulation.setEmulatedMedia", params)

    async def set_geolocation(
        self,
        latitude: float,
        longitude: float,
        *,
        accuracy: float = 0,
    ) -> None:
        """Set geolocation."""
        await self._cdp.send(
            "Emulation.setGeolocationOverride",
            {
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
            },
        )

    async def set_offline(self, offline: bool = True) -> None:
        """Set offline mode."""
        await self._cdp.send(
            "Network.emulateNetworkConditions",
            {
                "offline": offline,
                "latency": 0,
                "downloadThroughput": -1,
                "uploadThroughput": -1,
            },
        )

    def __repr__(self) -> str:
        return f"<BrowserPage url={self._url!r}>"
