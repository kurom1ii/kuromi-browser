"""
Shadow DOM support for kuromi-browser.

Provides utilities for working with Shadow DOM elements, including
piercing through shadow boundaries and managing shadow roots.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.elements.browser_element import BrowserElement

from kuromi_browser.elements.locator import Locator, LocatorType

logger = logging.getLogger(__name__)


class ShadowRoot:
    """Represents a Shadow DOM root.

    Provides methods for querying elements within a shadow DOM boundary.
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        object_id: str,
        host_element: Optional["BrowserElement"] = None,
        mode: str = "open",
    ) -> None:
        """Initialize ShadowRoot.

        Args:
            cdp_session: CDP session for sending commands.
            object_id: Remote object ID of the shadow root.
            host_element: The element that hosts this shadow root.
            mode: Shadow DOM mode ('open' or 'closed').
        """
        self._session = cdp_session
        self._object_id = object_id
        self._host = host_element
        self._mode = mode

    @property
    def mode(self) -> str:
        """Get the shadow DOM mode."""
        return self._mode

    @property
    def host(self) -> Optional["BrowserElement"]:
        """Get the host element."""
        return self._host

    async def query(self, selector: str) -> Optional["BrowserElement"]:
        """Query for an element within this shadow root.

        Args:
            selector: CSS selector.

        Returns:
            Element or None if not found.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        parsed = Locator.parse_full(selector)
        css = parsed.to_css() or selector

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": self._object_id,
                "functionDeclaration": f"""function() {{
                    return this.querySelector('{css}');
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

    async def query_all(self, selector: str) -> list["BrowserElement"]:
        """Query for all elements within this shadow root.

        Args:
            selector: CSS selector.

        Returns:
            List of matching elements.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        parsed = Locator.parse_full(selector)
        css = parsed.to_css() or selector

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": self._object_id,
                "functionDeclaration": f"""function() {{
                    return Array.from(this.querySelectorAll('{css}'));
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

    async def get_inner_html(self) -> str:
        """Get the inner HTML of the shadow root.

        Returns:
            Inner HTML content.
        """
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": self._object_id,
                "functionDeclaration": "function() { return this.innerHTML; }",
                "returnByValue": True,
            },
        )
        return result.get("result", {}).get("value", "")

    async def _element_from_object_id(self, object_id: str) -> Optional["BrowserElement"]:
        """Create a BrowserElement from a remote object ID."""
        from kuromi_browser.elements.browser_element import BrowserElement

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
                )

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
                )
        except Exception as e:
            logger.debug(f"Failed to create element from object: {e}")
        return None

    def __repr__(self) -> str:
        return f"<ShadowRoot mode={self._mode}>"


class ShadowDOMHelper:
    """Helper class for working with Shadow DOM.

    Provides utility methods for finding elements across shadow boundaries,
    piercing through shadow DOMs, and managing shadow roots.
    """

    def __init__(self, cdp_session: "CDPSession") -> None:
        """Initialize ShadowDOMHelper.

        Args:
            cdp_session: CDP session for sending commands.
        """
        self._session = cdp_session

    async def get_shadow_root(
        self,
        element: "BrowserElement",
    ) -> Optional[ShadowRoot]:
        """Get the shadow root of an element.

        Args:
            element: Element that may have a shadow root.

        Returns:
            ShadowRoot or None if no shadow root.
        """
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await element._ensure_object_id(),
                "functionDeclaration": """function() {
                    return { shadowRoot: this.shadowRoot, mode: this.shadowRoot?.mode };
                }""",
                "returnByValue": False,
            },
        )

        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("objectId"):
            # Get the shadowRoot property
            props = await self._session.send(
                "Runtime.getProperties",
                {"objectId": obj["objectId"], "ownProperties": True},
            )

            shadow_root_obj = None
            mode = "open"

            for prop in props.get("result", []):
                if prop.get("name") == "shadowRoot":
                    value = prop.get("value", {})
                    if value.get("type") == "object" and value.get("objectId"):
                        shadow_root_obj = value["objectId"]
                elif prop.get("name") == "mode":
                    value = prop.get("value", {})
                    mode = value.get("value", "open")

            if shadow_root_obj:
                return ShadowRoot(
                    self._session,
                    shadow_root_obj,
                    host_element=element,
                    mode=mode,
                )

        return None

    async def pierce_query(
        self,
        selector: str,
        root: Optional["BrowserElement"] = None,
    ) -> Optional["BrowserElement"]:
        """Query for an element, piercing through all shadow DOMs.

        This will search through both the light DOM and all shadow DOMs
        to find the first matching element.

        Args:
            selector: CSS selector.
            root: Optional root element to start from (defaults to document).

        Returns:
            First matching element or None.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        parsed = Locator.parse_full(selector)
        css = parsed.to_css()

        if not css:
            raise ValueError("pierce_query only supports CSS selectors")

        if root:
            object_id = await root._ensure_object_id()
            expression = f"""
                (function(root) {{
                    function queryShadow(node, selector) {{
                        const result = node.querySelector(selector);
                        if (result) return result;

                        const elements = node.querySelectorAll('*');
                        for (const el of elements) {{
                            if (el.shadowRoot) {{
                                const shadowResult = queryShadow(el.shadowRoot, selector);
                                if (shadowResult) return shadowResult;
                            }}
                        }}
                        return null;
                    }}
                    return queryShadow(root, '{css}');
                }})(this)
            """
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": object_id,
                    "functionDeclaration": f"function() {{ {expression} }}",
                    "returnByValue": False,
                },
            )
        else:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": f"""
                        (function() {{
                            function queryShadow(root, selector) {{
                                const result = root.querySelector(selector);
                                if (result) return result;

                                const elements = root.querySelectorAll('*');
                                for (const el of elements) {{
                                    if (el.shadowRoot) {{
                                        const shadowResult = queryShadow(el.shadowRoot, selector);
                                        if (shadowResult) return shadowResult;
                                    }}
                                }}
                                return null;
                            }}
                            return queryShadow(document, '{css}');
                        }})()
                    """,
                    "returnByValue": False,
                },
            )

        obj = result.get("result", {})
        if obj.get("type") == "object" and obj.get("subtype") != "null":
            object_id = obj.get("objectId")
            if object_id:
                return await self._element_from_object_id(object_id)
        return None

    async def pierce_query_all(
        self,
        selector: str,
        root: Optional["BrowserElement"] = None,
    ) -> list["BrowserElement"]:
        """Query for all elements, piercing through all shadow DOMs.

        Args:
            selector: CSS selector.
            root: Optional root element to start from.

        Returns:
            List of all matching elements.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        parsed = Locator.parse_full(selector)
        css = parsed.to_css()

        if not css:
            raise ValueError("pierce_query_all only supports CSS selectors")

        expression = f"""
            (function() {{
                const results = [];
                function queryShadowAll(node, selector) {{
                    results.push(...node.querySelectorAll(selector));

                    const elements = node.querySelectorAll('*');
                    for (const el of elements) {{
                        if (el.shadowRoot) {{
                            queryShadowAll(el.shadowRoot, selector);
                        }}
                    }}
                }}
                queryShadowAll({('this' if root else 'document')}, '{css}');
                return results;
            }})()
        """

        if root:
            object_id = await root._ensure_object_id()
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": object_id,
                    "functionDeclaration": f"function() {{ {expression} }}",
                    "returnByValue": False,
                },
            )
        else:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": expression,
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

    async def find_shadow_hosts(
        self,
        root: Optional["BrowserElement"] = None,
    ) -> list["BrowserElement"]:
        """Find all elements that have shadow roots.

        Args:
            root: Optional root element to search from.

        Returns:
            List of elements with shadow roots.
        """
        expression = """
            (function() {
                const hosts = [];
                const walker = document.createTreeWalker(
                    %s,
                    NodeFilter.SHOW_ELEMENT,
                    null
                );
                let node;
                while (node = walker.nextNode()) {
                    if (node.shadowRoot) {
                        hosts.push(node);
                    }
                }
                return hosts;
            })()
        """ % ("this" if root else "document.body || document.documentElement")

        if root:
            object_id = await root._ensure_object_id()
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": object_id,
                    "functionDeclaration": f"function() {{ return {expression}; }}",
                    "returnByValue": False,
                },
            )
        else:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": expression,
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

    async def get_shadow_tree(
        self,
        element: "BrowserElement",
        max_depth: int = 10,
    ) -> dict[str, Any]:
        """Get the shadow tree structure starting from an element.

        Args:
            element: Starting element.
            max_depth: Maximum depth to traverse.

        Returns:
            Dictionary representing the shadow tree structure.
        """
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await element._ensure_object_id(),
                "functionDeclaration": f"""function() {{
                    function buildTree(node, depth) {{
                        if (depth > {max_depth}) return null;

                        const info = {{
                            tag: node.tagName?.toLowerCase() || '#shadow-root',
                            id: node.id || null,
                            classes: node.className?.split?.(' ').filter(Boolean) || [],
                            hasShadow: !!node.shadowRoot,
                            children: []
                        }};

                        if (node.shadowRoot) {{
                            info.shadowRoot = buildTree(node.shadowRoot, depth + 1);
                        }}

                        const childNodes = node.children || node.childNodes || [];
                        for (const child of childNodes) {{
                            if (child.nodeType === 1) {{
                                info.children.push(buildTree(child, depth + 1));
                            }}
                        }}

                        return info;
                    }}
                    return buildTree(this, 0);
                }}""",
                "returnByValue": True,
            },
        )

        return result.get("result", {}).get("value", {})

    async def _element_from_object_id(self, object_id: str) -> Optional["BrowserElement"]:
        """Create a BrowserElement from a remote object ID."""
        from kuromi_browser.elements.browser_element import BrowserElement

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
                )

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
                )
        except Exception as e:
            logger.debug(f"Failed to create element from object: {e}")
        return None


__all__ = [
    "ShadowRoot",
    "ShadowDOMHelper",
]
