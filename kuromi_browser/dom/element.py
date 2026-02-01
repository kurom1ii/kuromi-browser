"""
Element class for kuromi-browser.

Provides a high-level interface for interacting with DOM elements via CDP.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession

from kuromi_browser.dom.locator import Locator

logger = logging.getLogger(__name__)


class Element:
    """CDP-based DOM element wrapper.

    Provides a convenient interface for interacting with DOM elements
    using Chrome DevTools Protocol.

    Example:
        element = await page.query('#submit')
        await element.click()
        text = element.text
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        node_id: int,
        backend_node_id: Optional[int] = None,
        object_id: Optional[str] = None,
    ) -> None:
        """Initialize Element.

        Args:
            cdp_session: CDP session for sending commands.
            node_id: DOM node ID.
            backend_node_id: Backend node ID (persists across navigations).
            object_id: Remote object ID for JavaScript interaction.
        """
        self._session = cdp_session
        self._node_id = node_id
        self._backend_node_id = backend_node_id
        self._object_id = object_id
        self._cached_tag: Optional[str] = None
        self._cached_attrs: Optional[dict[str, str]] = None

    @property
    def node_id(self) -> int:
        """Get the DOM node ID."""
        return self._node_id

    @property
    def backend_node_id(self) -> Optional[int]:
        """Get the backend node ID."""
        return self._backend_node_id

    @property
    def object_id(self) -> Optional[str]:
        """Get the remote object ID."""
        return self._object_id

    async def _ensure_object_id(self) -> str:
        """Ensure we have a remote object ID for JavaScript calls."""
        if self._object_id:
            return self._object_id

        result = await self._session.send(
            "DOM.resolveNode",
            {"nodeId": self._node_id},
        )
        self._object_id = result["object"]["objectId"]
        return self._object_id

    async def _call_function(
        self,
        function_declaration: str,
        *args: Any,
        return_by_value: bool = True,
    ) -> Any:
        """Call a JavaScript function on this element."""
        object_id = await self._ensure_object_id()

        call_args = []
        for arg in args:
            if isinstance(arg, Element):
                arg_object_id = await arg._ensure_object_id()
                call_args.append({"objectId": arg_object_id})
            else:
                call_args.append({"value": arg})

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": object_id,
                "functionDeclaration": function_declaration,
                "arguments": call_args,
                "returnByValue": return_by_value,
                "awaitPromise": True,
            },
        )

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise RuntimeError(f"JavaScript error: {exc.get('text', 'Unknown error')}")

        return result.get("result", {}).get("value")

    # Properties

    @property
    def text(self) -> str:
        """Get the element's text content (sync, returns cached or empty)."""
        # For sync access, return empty - use text_content() for async
        return ""

    async def text_content(self) -> str:
        """Get the element's text content.

        Returns:
            Text content of the element.
        """
        result = await self._call_function("function() { return this.textContent; }")
        return result or ""

    @property
    def html(self) -> str:
        """Get the element's outer HTML (sync, returns cached or empty)."""
        return ""

    async def outer_html(self) -> str:
        """Get the element's outer HTML.

        Returns:
            Outer HTML of the element.
        """
        result = await self._session.send(
            "DOM.getOuterHTML",
            {"nodeId": self._node_id},
        )
        return result.get("outerHTML", "")

    async def inner_html(self) -> str:
        """Get the element's inner HTML.

        Returns:
            Inner HTML of the element.
        """
        result = await self._call_function("function() { return this.innerHTML; }")
        return result or ""

    @property
    def tag(self) -> str:
        """Get the element's tag name (sync, returns cached or empty)."""
        return self._cached_tag or ""

    async def tag_name(self) -> str:
        """Get the element's tag name.

        Returns:
            Tag name in lowercase.
        """
        if self._cached_tag:
            return self._cached_tag

        result = await self._call_function(
            "function() { return this.tagName.toLowerCase(); }"
        )
        self._cached_tag = result or ""
        return self._cached_tag

    # Actions

    async def click(self, force: bool = False) -> None:
        """Click the element.

        Args:
            force: If True, click even if element is not visible.
        """
        if not force:
            await self.scroll_into_view()
            await asyncio.sleep(0.1)

        # Get element center position
        box = await self.bounding_box()
        if not box:
            if force:
                # Force click via JavaScript
                await self._call_function("function() { this.click(); }")
                return
            raise RuntimeError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        # Perform click via Input domain
        await self._session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            },
        )
        await self._session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            },
        )

    async def type(self, text: str, delay: float = 0) -> None:
        """Type text into the element.

        Args:
            text: Text to type.
            delay: Delay between keystrokes in seconds.
        """
        await self.focus()

        for char in text:
            await self._session.send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "text": char,
                },
            )
            await self._session.send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyUp",
                    "text": char,
                },
            )
            if delay > 0:
                await asyncio.sleep(delay)

    async def fill(self, value: str) -> None:
        """Fill the element with text (clears existing content first).

        Args:
            value: Value to fill.
        """
        await self.clear()
        await self._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )

    async def clear(self) -> None:
        """Clear the element's value."""
        await self.focus()
        await self._call_function(
            """function() {
                this.value = '';
                this.dispatchEvent(new Event('input', { bubbles: true }));
            }"""
        )

    async def focus(self) -> None:
        """Focus the element."""
        await self._session.send(
            "DOM.focus",
            {"nodeId": self._node_id},
        )

    async def hover(self) -> None:
        """Hover over the element."""
        await self.scroll_into_view()

        box = await self.bounding_box()
        if not box:
            raise RuntimeError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        await self._session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseMoved",
                "x": x,
                "y": y,
            },
        )

    async def scroll_into_view(self) -> None:
        """Scroll the element into view."""
        await self._call_function(
            "function() { this.scrollIntoView({ block: 'center', behavior: 'instant' }); }"
        )

    async def screenshot(self, *, format: str = "png", quality: int = 80) -> bytes:
        """Take a screenshot of the element.

        Args:
            format: Image format (png, jpeg, webp).
            quality: JPEG quality (0-100).

        Returns:
            Screenshot image data.
        """
        box = await self.bounding_box()
        if not box:
            raise RuntimeError("Element not visible or has no bounding box")

        params: dict[str, Any] = {
            "format": format,
            "clip": {
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
                "scale": 1,
            },
        }
        if format in ("jpeg", "webp"):
            params["quality"] = quality

        result = await self._session.send("Page.captureScreenshot", params)
        return base64.b64decode(result["data"])

    # Attributes

    async def attr(self, name: str) -> Optional[str]:
        """Get an attribute value.

        Args:
            name: Attribute name.

        Returns:
            Attribute value or None.
        """
        result = await self._call_function(
            "function(name) { return this.getAttribute(name); }",
            name,
        )
        return result

    async def set_attr(self, name: str, value: str) -> None:
        """Set an attribute value.

        Args:
            name: Attribute name.
            value: Attribute value.
        """
        await self._session.send(
            "DOM.setAttributeValue",
            {
                "nodeId": self._node_id,
                "name": name,
                "value": value,
            },
        )

    async def remove_attr(self, name: str) -> None:
        """Remove an attribute.

        Args:
            name: Attribute name.
        """
        await self._session.send(
            "DOM.removeAttribute",
            {
                "nodeId": self._node_id,
                "name": name,
            },
        )

    async def property(self, name: str) -> Any:
        """Get a JavaScript property.

        Args:
            name: Property name.

        Returns:
            Property value.
        """
        return await self._call_function(
            f"function() {{ return this.{name}; }}"
        )

    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Get the element's bounding box.

        Returns:
            Dict with x, y, width, height or None if not visible.
        """
        try:
            result = await self._session.send(
                "DOM.getBoxModel",
                {"nodeId": self._node_id},
            )
            model = result.get("model")
            if not model:
                return None

            # Use content box
            content = model.get("content", [])
            if len(content) < 8:
                return None

            # Content is [x1, y1, x2, y2, x3, y3, x4, y4]
            x = min(content[0], content[2], content[4], content[6])
            y = min(content[1], content[3], content[5], content[7])
            width = max(content[0], content[2], content[4], content[6]) - x
            height = max(content[1], content[3], content[5], content[7]) - y

            return {"x": x, "y": y, "width": width, "height": height}
        except Exception:
            return None

    async def is_visible(self) -> bool:
        """Check if the element is visible.

        Returns:
            True if visible.
        """
        result = await self._call_function(
            """function() {
                const style = window.getComputedStyle(this);
                return style.display !== 'none' &&
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0' &&
                       this.offsetWidth > 0 &&
                       this.offsetHeight > 0;
            }"""
        )
        return bool(result)

    async def is_enabled(self) -> bool:
        """Check if the element is enabled.

        Returns:
            True if enabled.
        """
        result = await self._call_function("function() { return !this.disabled; }")
        return bool(result)

    async def is_checked(self) -> bool:
        """Check if the element (checkbox/radio) is checked.

        Returns:
            True if checked.
        """
        result = await self._call_function("function() { return this.checked; }")
        return bool(result)

    # Relative locators

    async def parent(self, selector: Optional[str] = None) -> Optional["Element"]:
        """Get the parent element.

        Args:
            selector: Optional selector to match parent against.

        Returns:
            Parent element or None.
        """
        if selector:
            # Find closest matching parent
            object_id = await self._ensure_object_id()
            selector_type, parsed = Locator.parse(selector)

            if selector_type == "css":
                result = await self._session.send(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": object_id,
                        "functionDeclaration": f"function() {{ return this.closest('{parsed}'); }}",
                        "returnByValue": False,
                    },
                )
            else:
                # XPath for parent matching
                result = await self._session.send(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": object_id,
                        "functionDeclaration": """function(xpath) {
                            let el = this.parentElement;
                            while (el) {
                                const result = document.evaluate(xpath, el, null,
                                    XPathResult.BOOLEAN_TYPE, null);
                                if (result.booleanValue) return el;
                                el = el.parentElement;
                            }
                            return null;
                        }""",
                        "arguments": [{"value": parsed}],
                        "returnByValue": False,
                    },
                )

            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("objectId"):
                return await self._element_from_object_id(obj["objectId"])
            return None
        else:
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await self._ensure_object_id(),
                    "functionDeclaration": "function() { return this.parentElement; }",
                    "returnByValue": False,
                },
            )
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("objectId"):
                return await self._element_from_object_id(obj["objectId"])
            return None

    async def child(self, selector: Optional[str] = None) -> Optional["Element"]:
        """Get the first child element.

        Args:
            selector: Optional selector to filter children.

        Returns:
            First matching child element or None.
        """
        if selector:
            selector_type, parsed = Locator.parse(selector)
            if selector_type == "css":
                result = await self._session.send(
                    "DOM.querySelector",
                    {"nodeId": self._node_id, "selector": f":scope > {parsed}"},
                )
            else:
                # XPath for children
                result = await self._session.send(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": await self._ensure_object_id(),
                        "functionDeclaration": f"""function() {{
                            const result = document.evaluate('./{parsed}', this, null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                            return result.singleNodeValue;
                        }}""",
                        "returnByValue": False,
                    },
                )
                obj = result.get("result", {})
                if obj.get("type") == "object" and obj.get("objectId"):
                    return await self._element_from_object_id(obj["objectId"])
                return None

            node_id = result.get("nodeId", 0)
            if node_id > 0:
                return Element(self._session, node_id)
            return None
        else:
            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": self._node_id, "selector": ":scope > *"},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                return Element(self._session, node_id)
            return None

    async def children(self, selector: Optional[str] = None) -> list["Element"]:
        """Get all child elements.

        Args:
            selector: Optional selector to filter children.

        Returns:
            List of matching child elements.
        """
        if selector:
            selector_type, parsed = Locator.parse(selector)
            if selector_type == "css":
                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": self._node_id, "selector": f":scope > {parsed}"},
                )
                return [Element(self._session, nid) for nid in result.get("nodeIds", [])]

        result = await self._session.send(
            "DOM.querySelectorAll",
            {"nodeId": self._node_id, "selector": ":scope > *"},
        )
        return [Element(self._session, nid) for nid in result.get("nodeIds", [])]

    async def next(self, selector: Optional[str] = None) -> Optional["Element"]:
        """Get the next sibling element.

        Args:
            selector: Optional selector to match next sibling.

        Returns:
            Next sibling element or None.
        """
        if selector:
            selector_type, parsed = Locator.parse(selector)
            func = f"""function() {{
                let el = this.nextElementSibling;
                while (el) {{
                    if (el.matches('{parsed}')) return el;
                    el = el.nextElementSibling;
                }}
                return null;
            }}"""
        else:
            func = "function() { return this.nextElementSibling; }"

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await self._ensure_object_id(),
                "functionDeclaration": func,
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("objectId"):
            return await self._element_from_object_id(obj["objectId"])
        return None

    async def prev(self, selector: Optional[str] = None) -> Optional["Element"]:
        """Get the previous sibling element.

        Args:
            selector: Optional selector to match previous sibling.

        Returns:
            Previous sibling element or None.
        """
        if selector:
            selector_type, parsed = Locator.parse(selector)
            func = f"""function() {{
                let el = this.previousElementSibling;
                while (el) {{
                    if (el.matches('{parsed}')) return el;
                    el = el.previousElementSibling;
                }}
                return null;
            }}"""
        else:
            func = "function() { return this.previousElementSibling; }"

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await self._ensure_object_id(),
                "functionDeclaration": func,
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("objectId"):
            return await self._element_from_object_id(obj["objectId"])
        return None

    async def query(self, selector: str) -> Optional["Element"]:
        """Query for a descendant element.

        Args:
            selector: Selector string.

        Returns:
            First matching element or None.
        """
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": self._node_id, "selector": parsed},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                return Element(self._session, node_id)
            return None
        else:
            # XPath query
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await self._ensure_object_id(),
                    "functionDeclaration": f"""function() {{
                        const result = document.evaluate('{parsed}', this, null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        return result.singleNodeValue;
                    }}""",
                    "returnByValue": False,
                },
            )
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("objectId"):
                return await self._element_from_object_id(obj["objectId"])
            return None

    async def query_all(self, selector: str) -> list["Element"]:
        """Query for all descendant elements.

        Args:
            selector: Selector string.

        Returns:
            List of matching elements.
        """
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            result = await self._session.send(
                "DOM.querySelectorAll",
                {"nodeId": self._node_id, "selector": parsed},
            )
            return [Element(self._session, nid) for nid in result.get("nodeIds", [])]
        else:
            # XPath query all
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await self._ensure_object_id(),
                    "functionDeclaration": f"""function() {{
                        const result = document.evaluate('{parsed}', this, null,
                            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        const nodes = [];
                        for (let i = 0; i < result.snapshotLength; i++) {{
                            nodes.push(result.snapshotItem(i));
                        }}
                        return nodes;
                    }}""",
                    "returnByValue": False,
                },
            )
            # Handle array of objects
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("objectId"):
                # Get array elements
                props = await self._session.send(
                    "Runtime.getProperties",
                    {"objectId": obj["objectId"], "ownProperties": True},
                )
                elements = []
                for prop in props.get("result", []):
                    if prop.get("name", "").isdigit():
                        prop_obj = prop.get("value", {})
                        if prop_obj.get("objectId"):
                            el = await self._element_from_object_id(prop_obj["objectId"])
                            if el:
                                elements.append(el)
                return elements
            return []

    async def _element_from_object_id(self, object_id: str) -> Optional["Element"]:
        """Create an Element from a remote object ID."""
        try:
            result = await self._session.send(
                "DOM.describeNode",
                {"objectId": object_id},
            )
            node = result.get("node", {})
            node_id = node.get("nodeId", 0)
            backend_node_id = node.get("backendNodeId")

            if node_id > 0:
                return Element(
                    self._session,
                    node_id,
                    backend_node_id=backend_node_id,
                    object_id=object_id,
                )
            return None
        except Exception:
            return None

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Evaluate JavaScript in the context of this element.

        Args:
            expression: JavaScript expression or function.
            *args: Arguments to pass to the function.

        Returns:
            Evaluation result.
        """
        return await self._call_function(expression, *args)

    async def select_option(self, *values: str) -> list[str]:
        """Select options in a <select> element.

        Args:
            *values: Values to select.

        Returns:
            List of selected values.
        """
        result = await self._call_function(
            """function(...values) {
                const selected = [];
                for (const option of this.options) {
                    option.selected = values.includes(option.value);
                    if (option.selected) selected.push(option.value);
                }
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
                return selected;
            }""",
            *values,
        )
        return result or []

    async def check(self) -> None:
        """Check a checkbox or radio button."""
        if not await self.is_checked():
            await self.click()

    async def uncheck(self) -> None:
        """Uncheck a checkbox."""
        if await self.is_checked():
            await self.click()

    def __repr__(self) -> str:
        return f"<Element node_id={self._node_id}>"


__all__ = ["Element"]
