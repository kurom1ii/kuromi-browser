"""
Browser element for kuromi-browser.

CDP-based DOM element that supports live browser interactions.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession

from kuromi_browser.elements.base import ActionableElement
from kuromi_browser.elements.locator import Locator, LocatorType, ParsedLocator

logger = logging.getLogger(__name__)


class BrowserElement(ActionableElement):
    """CDP-based DOM element wrapper.

    Provides a convenient interface for interacting with live DOM elements
    using Chrome DevTools Protocol. Supports both sync and async property access.

    Example:
        element = await page.ele('#submit')
        await element.click()
        text = await element.text_content()

        # Sync access (cached values)
        tag = element.tag
        attrs = element.attrs
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        node_id: int,
        backend_node_id: Optional[int] = None,
        object_id: Optional[str] = None,
        frame_id: Optional[str] = None,
    ) -> None:
        """Initialize BrowserElement.

        Args:
            cdp_session: CDP session for sending commands.
            node_id: DOM node ID.
            backend_node_id: Backend node ID (persists across navigations).
            object_id: Remote object ID for JavaScript interaction.
            frame_id: Frame ID if element is in an iframe.
        """
        self._session = cdp_session
        self._node_id = node_id
        self._backend_node_id = backend_node_id
        self._object_id = object_id
        self._frame_id = frame_id

        # Cached values
        self._cached_tag: Optional[str] = None
        self._cached_attrs: Optional[dict[str, str]] = None
        self._cached_text: Optional[str] = None

    # Node identifiers

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

    @property
    def frame_id(self) -> Optional[str]:
        """Get the frame ID."""
        return self._frame_id

    # Internal helpers

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
            if isinstance(arg, BrowserElement):
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

    async def _element_from_object_id(self, object_id: str) -> Optional["BrowserElement"]:
        """Create a BrowserElement from a remote object ID."""
        try:
            result = await self._session.send(
                "DOM.describeNode",
                {"objectId": object_id},
            )
            node = result.get("node", {})
            node_id = node.get("nodeId", 0)
            backend_node_id = node.get("backendNodeId")

            if node_id > 0:
                return BrowserElement(
                    self._session,
                    node_id,
                    backend_node_id=backend_node_id,
                    object_id=object_id,
                    frame_id=self._frame_id,
                )

            # If nodeId is 0, request it
            result = await self._session.send(
                "DOM.requestNode",
                {"objectId": object_id},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                return BrowserElement(
                    self._session,
                    node_id,
                    backend_node_id=backend_node_id,
                    object_id=object_id,
                    frame_id=self._frame_id,
                )
        except Exception as e:
            logger.debug(f"Failed to create element from object: {e}")
        return None

    # Properties (sync access with cached values)

    @property
    def tag(self) -> str:
        """Get the element's tag name (sync, returns cached value)."""
        return self._cached_tag or ""

    @property
    def text(self) -> str:
        """Get the element's text content (sync, returns cached value)."""
        return self._cached_text or ""

    @property
    def html(self) -> str:
        """Get the element's outer HTML (sync, returns empty - use outer_html())."""
        return ""

    @property
    def inner_html(self) -> str:
        """Get the element's inner HTML (sync, returns empty - use get_inner_html())."""
        return ""

    @property
    def attrs(self) -> dict[str, str]:
        """Get all attributes (sync, returns cached value)."""
        return self._cached_attrs or {}

    # Async property getters

    async def tag_name(self) -> str:
        """Get the element's tag name (async).

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

    async def text_content(self) -> str:
        """Get the element's text content (async).

        Returns:
            Text content of the element.
        """
        result = await self._call_function("function() { return this.textContent; }")
        self._cached_text = result or ""
        return self._cached_text

    async def inner_text(self) -> str:
        """Get the element's inner text (async).

        Returns:
            Inner text of the element.
        """
        result = await self._call_function("function() { return this.innerText; }")
        return result or ""

    async def outer_html(self) -> str:
        """Get the element's outer HTML (async).

        Returns:
            Outer HTML of the element.
        """
        result = await self._session.send(
            "DOM.getOuterHTML",
            {"nodeId": self._node_id},
        )
        return result.get("outerHTML", "")

    async def get_inner_html(self) -> str:
        """Get the element's inner HTML (async).

        Returns:
            Inner HTML of the element.
        """
        result = await self._call_function("function() { return this.innerHTML; }")
        return result or ""

    async def get_attrs(self) -> dict[str, str]:
        """Get all attributes (async).

        Returns:
            Dictionary of attributes.
        """
        result = await self._call_function(
            """function() {
                const attrs = {};
                for (const attr of this.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }"""
        )
        self._cached_attrs = result or {}
        return self._cached_attrs

    # Attribute access

    def attr(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value (sync, from cache).

        Args:
            name: Attribute name.
            default: Default value.

        Returns:
            Attribute value or default.
        """
        return self.attrs.get(name, default)

    async def get_attr(self, name: str) -> Optional[str]:
        """Get an attribute value (async).

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
        # Update cache
        if self._cached_attrs is not None:
            self._cached_attrs[name] = value

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
        # Update cache
        if self._cached_attrs is not None:
            self._cached_attrs.pop(name, None)

    async def get_property(self, name: str) -> Any:
        """Get a JavaScript property.

        Args:
            name: Property name.

        Returns:
            Property value.
        """
        return await self._call_function(f"function() {{ return this.{name}; }}")

    # Link and src properties

    @property
    def link(self) -> Optional[str]:
        """Get the href attribute if element is a link."""
        return self.attrs.get("href")

    @property
    def src(self) -> Optional[str]:
        """Get the src attribute if element has one."""
        return self.attrs.get("src")

    async def get_link(self) -> Optional[str]:
        """Get the href attribute (async)."""
        return await self.get_attr("href")

    async def get_src(self) -> Optional[str]:
        """Get the src attribute (async)."""
        return await self.get_attr("src")

    # Element queries

    def ele(self, selector: str) -> Optional["BrowserElement"]:
        """Sync version - not supported, use s() or async ele()."""
        raise NotImplementedError(
            "Use 'await element.find(selector)' for async or element.s(selector) not supported"
        )

    def eles(self, selector: str) -> list["BrowserElement"]:
        """Sync version - not supported."""
        raise NotImplementedError("Use 'await element.find_all(selector)' for async")

    async def find(self, selector: str) -> Optional["BrowserElement"]:
        """Find the first child element matching the selector.

        Args:
            selector: Selector string (CSS, XPath, or DrissionPage-style).

        Returns:
            First matching element or None.
        """
        parsed = Locator.parse_full(selector)

        if parsed.type in (LocatorType.XPATH, LocatorType.TEXT, LocatorType.TEXT_EXACT):
            xpath = parsed.to_xpath()
            # Make relative
            if not xpath.startswith("."):
                xpath = "." + xpath if xpath.startswith("/") else ".//" + xpath

            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await self._ensure_object_id(),
                    "functionDeclaration": f"""function() {{
                        const result = document.evaluate(
                            '{xpath.replace("'", "\\'")}',
                            this,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        return result.singleNodeValue;
                    }}""",
                    "returnByValue": False,
                },
            )
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("subtype") != "null":
                object_id = obj.get("objectId")
                if object_id:
                    el = await self._element_from_object_id(object_id)
                    if el and parsed.index is not None:
                        # Handle index - need to find all and return nth
                        elements = await self.find_all(selector)
                        if 0 <= parsed.index < len(elements):
                            return elements[parsed.index]
                        return None
                    return el
            return None
        else:
            # CSS selector
            css = parsed.to_css() or parsed.value
            try:
                result = await self._session.send(
                    "DOM.querySelector",
                    {"nodeId": self._node_id, "selector": css},
                )
                node_id = result.get("nodeId", 0)
                if node_id > 0:
                    if parsed.index is not None:
                        elements = await self.find_all(selector)
                        if 0 <= parsed.index < len(elements):
                            return elements[parsed.index]
                        return None
                    return BrowserElement(self._session, node_id, frame_id=self._frame_id)
            except Exception as e:
                logger.debug(f"Query failed: {e}")
            return None

    async def find_all(self, selector: str) -> list["BrowserElement"]:
        """Find all child elements matching the selector.

        Args:
            selector: Selector string.

        Returns:
            List of matching elements.
        """
        parsed = Locator.parse_full(selector)

        if parsed.type in (LocatorType.XPATH, LocatorType.TEXT, LocatorType.TEXT_EXACT):
            xpath = parsed.to_xpath()
            # Make relative
            if not xpath.startswith("."):
                xpath = "." + xpath if xpath.startswith("/") else ".//" + xpath

            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await self._ensure_object_id(),
                    "functionDeclaration": f"""function() {{
                        const result = document.evaluate(
                            '{xpath.replace("'", "\\'")}',
                            this,
                            null,
                            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                            null
                        );
                        const nodes = [];
                        for (let i = 0; i < result.snapshotLength; i++) {{
                            nodes.push(result.snapshotItem(i));
                        }}
                        return nodes;
                    }}""",
                    "returnByValue": False,
                },
            )
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("objectId"):
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
        else:
            # CSS selector
            css = parsed.to_css() or parsed.value
            try:
                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": self._node_id, "selector": css},
                )
                return [
                    BrowserElement(self._session, nid, frame_id=self._frame_id)
                    for nid in result.get("nodeIds", [])
                ]
            except Exception as e:
                logger.debug(f"Query all failed: {e}")
            return []

    # Aliases
    async def query(self, selector: str) -> Optional["BrowserElement"]:
        """Alias for find()."""
        return await self.find(selector)

    async def query_all(self, selector: str) -> list["BrowserElement"]:
        """Alias for find_all()."""
        return await self.find_all(selector)

    # Navigation

    @property
    def parent(self) -> Optional["BrowserElement"]:
        """Get parent (sync not supported)."""
        raise NotImplementedError("Use 'await element.get_parent()'")

    @property
    def children(self) -> list["BrowserElement"]:
        """Get children (sync not supported)."""
        raise NotImplementedError("Use 'await element.get_children()'")

    async def get_parent(self, selector: Optional[str] = None) -> Optional["BrowserElement"]:
        """Get the parent element.

        Args:
            selector: Optional selector to match parent against.

        Returns:
            Parent element or None.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css()

            if css:
                result = await self._session.send(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": await self._ensure_object_id(),
                        "functionDeclaration": f"function() {{ return this.closest('{css}'); }}",
                        "returnByValue": False,
                    },
                )
            else:
                xpath = parsed.to_xpath()
                result = await self._session.send(
                    "Runtime.callFunctionOn",
                    {
                        "objectId": await self._ensure_object_id(),
                        "functionDeclaration": f"""function() {{
                            let el = this.parentElement;
                            while (el) {{
                                const result = document.evaluate('{xpath}', el, null,
                                    XPathResult.BOOLEAN_TYPE, null);
                                if (result.booleanValue) return el;
                                el = el.parentElement;
                            }}
                            return null;
                        }}""",
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

    async def get_children(self, selector: Optional[str] = None) -> list["BrowserElement"]:
        """Get all child elements.

        Args:
            selector: Optional selector to filter children.

        Returns:
            List of child elements.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css()
            if css:
                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": self._node_id, "selector": f":scope > {css}"},
                )
                return [
                    BrowserElement(self._session, nid, frame_id=self._frame_id)
                    for nid in result.get("nodeIds", [])
                ]

        result = await self._session.send(
            "DOM.querySelectorAll",
            {"nodeId": self._node_id, "selector": ":scope > *"},
        )
        return [
            BrowserElement(self._session, nid, frame_id=self._frame_id)
            for nid in result.get("nodeIds", [])
        ]

    def next(self, selector: Optional[str] = None) -> Optional["BrowserElement"]:
        """Get next sibling (sync not supported)."""
        raise NotImplementedError("Use 'await element.get_next()'")

    def prev(self, selector: Optional[str] = None) -> Optional["BrowserElement"]:
        """Get previous sibling (sync not supported)."""
        raise NotImplementedError("Use 'await element.get_prev()'")

    async def get_next(self, selector: Optional[str] = None) -> Optional["BrowserElement"]:
        """Get the next sibling element.

        Args:
            selector: Optional selector to match next sibling.

        Returns:
            Next sibling element or None.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css() or "*"
            func = f"""function() {{
                let el = this.nextElementSibling;
                while (el) {{
                    if (el.matches('{css}')) return el;
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

    async def get_prev(self, selector: Optional[str] = None) -> Optional["BrowserElement"]:
        """Get the previous sibling element.

        Args:
            selector: Optional selector to match previous sibling.

        Returns:
            Previous sibling element or None.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css() or "*"
            func = f"""function() {{
                let el = this.previousElementSibling;
                while (el) {{
                    if (el.matches('{css}')) return el;
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

    # State checks

    def is_displayed(self) -> bool:
        """Check if displayed (sync not supported)."""
        raise NotImplementedError("Use 'await element.is_visible()'")

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

    async def is_editable(self) -> bool:
        """Check if the element is editable.

        Returns:
            True if editable.
        """
        result = await self._call_function(
            """function() {
                const tag = this.tagName.toLowerCase();
                if (tag === 'input' || tag === 'textarea') {
                    return !this.disabled && !this.readOnly;
                }
                return this.isContentEditable;
            }"""
        )
        return bool(result)

    # Bounding box

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

            content = model.get("content", [])
            if len(content) < 8:
                return None

            x = min(content[0], content[2], content[4], content[6])
            y = min(content[1], content[3], content[5], content[7])
            width = max(content[0], content[2], content[4], content[6]) - x
            height = max(content[1], content[3], content[5], content[7]) - y

            return {"x": x, "y": y, "width": width, "height": height}
        except Exception:
            return None

    # Actions

    async def click(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Click the element.

        Args:
            force: If True, click even if element is not visible.
            timeout: Not used currently.
        """
        if not force:
            await self.scroll_into_view()
            await asyncio.sleep(0.1)

        box = await self.bounding_box()
        if not box:
            if force:
                await self._call_function("function() { this.click(); }")
                return
            raise RuntimeError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

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

    async def dblclick(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Double-click the element."""
        if not force:
            await self.scroll_into_view()
            await asyncio.sleep(0.1)

        box = await self.bounding_box()
        if not box:
            if force:
                await self._call_function(
                    """function() {
                        const evt = new MouseEvent('dblclick', { bubbles: true });
                        this.dispatchEvent(evt);
                    }"""
                )
                return
            raise RuntimeError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        await self._session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 2,
            },
        )
        await self._session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 2,
            },
        )

    async def hover(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over the element."""
        if not force:
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

    async def fill(
        self,
        value: str,
        *,
        clear: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill the element with text.

        Args:
            value: Value to fill.
            clear: If True, clear existing content first.
            timeout: Not used currently.
        """
        if clear:
            await self.clear()
        await self._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )

    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into the element character by character.

        Args:
            text: Text to type.
            delay: Delay between keystrokes in seconds.
            timeout: Not used currently.
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

    async def blur(self) -> None:
        """Remove focus from the element."""
        await self._call_function("function() { this.blur(); }")

    async def select_option(
        self,
        *values: str,
        by: str = "value",
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in a <select> element.

        Args:
            *values: Values to select.
            by: Selection method ('value', 'text', 'index').
            timeout: Not used currently.

        Returns:
            List of selected values.
        """
        if by == "value":
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
        elif by == "text":
            result = await self._call_function(
                """function(...texts) {
                    const selected = [];
                    for (const option of this.options) {
                        option.selected = texts.includes(option.text);
                        if (option.selected) selected.push(option.value);
                    }
                    this.dispatchEvent(new Event('input', { bubbles: true }));
                    this.dispatchEvent(new Event('change', { bubbles: true }));
                    return selected;
                }""",
                *values,
            )
        elif by == "index":
            indices = [int(v) for v in values]
            result = await self._call_function(
                """function(...indices) {
                    const selected = [];
                    for (let i = 0; i < this.options.length; i++) {
                        this.options[i].selected = indices.includes(i);
                        if (this.options[i].selected) selected.push(this.options[i].value);
                    }
                    this.dispatchEvent(new Event('input', { bubbles: true }));
                    this.dispatchEvent(new Event('change', { bubbles: true }));
                    return selected;
                }""",
                *indices,
            )
        else:
            raise ValueError(f"Unknown selection method: {by}")

        return result or []

    async def check(self, *, force: bool = False) -> None:
        """Check a checkbox or radio button."""
        if not await self.is_checked():
            await self.click(force=force)

    async def uncheck(self, *, force: bool = False) -> None:
        """Uncheck a checkbox."""
        if await self.is_checked():
            await self.click(force=force)

    async def scroll_into_view(self) -> None:
        """Scroll the element into view."""
        await self._call_function(
            "function() { this.scrollIntoView({ block: 'center', behavior: 'instant' }); }"
        )

    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        format: str = "png",
        quality: int = 80,
    ) -> bytes:
        """Take a screenshot of the element.

        Args:
            path: Optional path to save the screenshot.
            format: Image format ('png', 'jpeg', 'webp').
            quality: JPEG/WebP quality (0-100).

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
        data = base64.b64decode(result["data"])

        if path:
            with open(path, "wb") as f:
                f.write(data)

        return data

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Evaluate JavaScript in the context of this element.

        Args:
            expression: JavaScript expression or function.
            *args: Arguments to pass to the function.

        Returns:
            Evaluation result.
        """
        return await self._call_function(expression, *args)

    # Shadow DOM

    async def shadow_root(self) -> Optional["BrowserElement"]:
        """Get the shadow root of this element.

        Returns:
            Shadow root element or None if no shadow root.
        """
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await self._ensure_object_id(),
                "functionDeclaration": "function() { return this.shadowRoot; }",
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("subtype") != "null":
            object_id = obj.get("objectId")
            if object_id:
                return await self._element_from_object_id(object_id)
        return None

    async def find_in_shadow(self, selector: str) -> Optional["BrowserElement"]:
        """Find an element within this element's shadow DOM.

        Args:
            selector: CSS selector.

        Returns:
            Element or None if not found.
        """
        parsed = Locator.parse_full(selector)
        css = parsed.to_css() or selector

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await self._ensure_object_id(),
                "functionDeclaration": f"""function() {{
                    const shadow = this.shadowRoot;
                    if (!shadow) return null;
                    return shadow.querySelector('{css}');
                }}""",
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("subtype") != "null":
            object_id = obj.get("objectId")
            if object_id:
                return await self._element_from_object_id(object_id)
        return None

    async def find_all_in_shadow(self, selector: str) -> list["BrowserElement"]:
        """Find all elements within this element's shadow DOM.

        Args:
            selector: CSS selector.

        Returns:
            List of matching elements.
        """
        parsed = Locator.parse_full(selector)
        css = parsed.to_css() or selector

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await self._ensure_object_id(),
                "functionDeclaration": f"""function() {{
                    const shadow = this.shadowRoot;
                    if (!shadow) return [];
                    return Array.from(shadow.querySelectorAll('{css}'));
                }}""",
                "returnByValue": False,
            },
        )
        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("objectId"):
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

    def __repr__(self) -> str:
        return f"<BrowserElement node_id={self._node_id}>"


__all__ = ["BrowserElement"]
