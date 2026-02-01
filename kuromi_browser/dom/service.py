"""
DOM Service for kuromi-browser.

Provides DOM querying, shadow DOM handling, iframe handling, and wait mechanisms.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession

from kuromi_browser.dom.element import Element
from kuromi_browser.dom.locator import Locator

logger = logging.getLogger(__name__)


class DOMService:
    """High-level DOM service for interacting with page content.

    Provides methods for querying elements, handling shadow DOM and iframes,
    and waiting for elements to appear.

    Example:
        dom = DOMService(cdp_session)
        await dom.enable()

        # Query elements
        element = await dom.query('#submit')
        elements = await dom.query_all('.item')

        # Wait for element
        element = await dom.wait_for('text:Loading', state='hidden')

        # Shadow DOM
        shadow_host = await dom.query('#shadow-host')
        shadow_element = await dom.query_in_shadow(shadow_host, '.shadow-content')

        # Iframe
        iframe_content = await dom.enter_iframe('#iframe-id')
        inner_element = await iframe_content.query('.inner-content')
    """

    def __init__(self, cdp_session: "CDPSession") -> None:
        """Initialize DOM service.

        Args:
            cdp_session: CDP session for sending commands.
        """
        self._session = cdp_session
        self._document_node_id: Optional[int] = None
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Check if DOM domain is enabled."""
        return self._enabled

    async def enable(self) -> None:
        """Enable DOM domain for this session."""
        if not self._enabled:
            await self._session.send("DOM.enable")
            self._enabled = True

    async def disable(self) -> None:
        """Disable DOM domain."""
        if self._enabled:
            await self._session.send("DOM.disable")
            self._enabled = False
            self._document_node_id = None

    async def get_document(self, depth: int = -1) -> dict[str, Any]:
        """Get the document root node.

        Args:
            depth: Depth of the tree to retrieve (-1 for infinite).

        Returns:
            Document node info.
        """
        result = await self._session.send(
            "DOM.getDocument",
            {"depth": depth},
        )
        self._document_node_id = result.get("root", {}).get("nodeId")
        return result.get("root", {})

    async def _ensure_document(self) -> int:
        """Ensure we have the document node ID."""
        if not self._document_node_id:
            await self.get_document(depth=0)
        return self._document_node_id  # type: ignore

    # Query methods

    async def query(self, selector: str) -> Optional[Element]:
        """Query for an element.

        Args:
            selector: DrissionPage-style selector.

        Returns:
            Element or None if not found.
        """
        doc_node_id = await self._ensure_document()
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            try:
                result = await self._session.send(
                    "DOM.querySelector",
                    {"nodeId": doc_node_id, "selector": parsed},
                )
                node_id = result.get("nodeId", 0)
                if node_id > 0:
                    return Element(self._session, node_id)
            except Exception as e:
                logger.debug(f"Query failed: {e}")
            return None
        else:
            # XPath query
            return await self._query_xpath(parsed)

    async def query_all(self, selector: str) -> list[Element]:
        """Query for all matching elements.

        Args:
            selector: DrissionPage-style selector.

        Returns:
            List of matching elements.
        """
        doc_node_id = await self._ensure_document()
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            try:
                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": doc_node_id, "selector": parsed},
                )
                return [
                    Element(self._session, nid)
                    for nid in result.get("nodeIds", [])
                ]
            except Exception as e:
                logger.debug(f"Query all failed: {e}")
            return []
        else:
            # XPath query all
            return await self._query_xpath_all(parsed)

    async def _query_xpath(self, xpath: str) -> Optional[Element]:
        """Query using XPath expression."""
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": f"""
                        (function() {{
                            const result = document.evaluate(
                                '{xpath.replace("'", "\\'")}',
                                document,
                                null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE,
                                null
                            );
                            return result.singleNodeValue;
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
        except Exception as e:
            logger.debug(f"XPath query failed: {e}")
        return None

    async def _query_xpath_all(self, xpath: str) -> list[Element]:
        """Query all using XPath expression."""
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": f"""
                        (function() {{
                            const result = document.evaluate(
                                '{xpath.replace("'", "\\'")}',
                                document,
                                null,
                                XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
                                null
                            );
                            const nodes = [];
                            for (let i = 0; i < result.snapshotLength; i++) {{
                                nodes.push(result.snapshotItem(i));
                            }}
                            return nodes;
                        }})()
                    """,
                    "returnByValue": False,
                },
            )
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
        except Exception as e:
            logger.debug(f"XPath query all failed: {e}")
        return []

    async def _element_from_object_id(self, object_id: str) -> Optional[Element]:
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
            # If nodeId is 0, request it
            result = await self._session.send(
                "DOM.requestNode",
                {"objectId": object_id},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                return Element(
                    self._session,
                    node_id,
                    backend_node_id=backend_node_id,
                    object_id=object_id,
                )
        except Exception as e:
            logger.debug(f"Failed to create element from object: {e}")
        return None

    # Shadow DOM handling

    async def query_in_shadow(
        self,
        host: Union[Element, str],
        selector: str,
    ) -> Optional[Element]:
        """Query for an element within a shadow DOM.

        Args:
            host: Shadow host element or selector.
            selector: Selector for element within shadow root.

        Returns:
            Element or None if not found.
        """
        if isinstance(host, str):
            host_element = await self.query(host)
            if not host_element:
                return None
        else:
            host_element = host

        selector_type, parsed = Locator.parse(selector)

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await host_element._ensure_object_id(),
                "functionDeclaration": f"""function() {{
                    const shadow = this.shadowRoot;
                    if (!shadow) return null;
                    return shadow.querySelector('{parsed}');
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

    async def query_all_in_shadow(
        self,
        host: Union[Element, str],
        selector: str,
    ) -> list[Element]:
        """Query for all elements within a shadow DOM.

        Args:
            host: Shadow host element or selector.
            selector: Selector for elements within shadow root.

        Returns:
            List of matching elements.
        """
        if isinstance(host, str):
            host_element = await self.query(host)
            if not host_element:
                return []
        else:
            host_element = host

        selector_type, parsed = Locator.parse(selector)

        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await host_element._ensure_object_id(),
                "functionDeclaration": f"""function() {{
                    const shadow = this.shadowRoot;
                    if (!shadow) return [];
                    return Array.from(shadow.querySelectorAll('{parsed}'));
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

    async def pierce_shadow(self, selector: str) -> Optional[Element]:
        """Query piercing through all shadow DOMs.

        Args:
            selector: CSS selector.

        Returns:
            First matching element or None.
        """
        selector_type, parsed = Locator.parse(selector)
        if selector_type != "css":
            raise ValueError("pierce_shadow only supports CSS selectors")

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
                        return queryShadow(document, '{parsed}');
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

    # Iframe handling

    async def enter_iframe(
        self,
        iframe: Union[Element, str],
    ) -> "DOMService":
        """Enter an iframe and return a DOMService for its content.

        Args:
            iframe: Iframe element or selector.

        Returns:
            DOMService for the iframe's content document.
        """
        if isinstance(iframe, str):
            iframe_element = await self.query(iframe)
            if not iframe_element:
                raise ValueError(f"Iframe not found: {iframe}")
        else:
            iframe_element = iframe

        # Get the iframe's content document
        result = await self._session.send(
            "DOM.describeNode",
            {"nodeId": iframe_element.node_id, "depth": 0},
        )
        node = result.get("node", {})
        frame_id = node.get("frameId")

        if not frame_id:
            raise ValueError("Could not get frame ID from iframe")

        # Get content document for the frame
        result = await self._session.send(
            "DOM.getFrameOwner",
            {"frameId": frame_id},
        )

        # Create a new DOM service for the iframe
        iframe_dom = DOMService(self._session)
        iframe_dom._enabled = True

        # Get the iframe's document
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "objectId": await iframe_element._ensure_object_id(),
                "functionDeclaration": "function() { return this.contentDocument; }",
                "returnByValue": False,
            },
        )
        doc_obj = result.get("result", {})
        if doc_obj.get("objectId"):
            desc = await self._session.send(
                "DOM.describeNode",
                {"objectId": doc_obj["objectId"]},
            )
            iframe_dom._document_node_id = desc.get("node", {}).get("nodeId")

        return iframe_dom

    async def list_frames(self) -> list[dict[str, Any]]:
        """List all frames in the page.

        Returns:
            List of frame info dictionaries.
        """
        result = await self._session.send("Page.getFrameTree")
        frames = []

        def collect_frames(tree: dict) -> None:
            frame = tree.get("frame", {})
            frames.append({
                "id": frame.get("id"),
                "url": frame.get("url"),
                "name": frame.get("name"),
                "parent_id": frame.get("parentId"),
            })
            for child in tree.get("childFrames", []):
                collect_frames(child)

        collect_frames(result.get("frameTree", {}))
        return frames

    # Wait mechanisms

    async def wait_for(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: float = 30.0,
        poll_interval: float = 0.1,
    ) -> Optional[Element]:
        """Wait for an element to match a state.

        Args:
            selector: DrissionPage-style selector.
            state: Target state ('attached', 'detached', 'visible', 'hidden').
            timeout: Maximum wait time in seconds.
            poll_interval: Time between checks in seconds.

        Returns:
            Element if found (for attached/visible), None otherwise.

        Raises:
            TimeoutError: If timeout is reached.
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Timeout waiting for '{selector}' to be {state}"
                )

            element = await self.query(selector)

            if state == "attached":
                if element:
                    return element
            elif state == "detached":
                if not element:
                    return None
            elif state == "visible":
                if element and await element.is_visible():
                    return element
            elif state == "hidden":
                if not element or not await element.is_visible():
                    return element
            else:
                raise ValueError(f"Unknown state: {state}")

            await asyncio.sleep(poll_interval)

    async def wait_for_function(
        self,
        expression: str,
        *,
        timeout: float = 30.0,
        poll_interval: float = 0.1,
    ) -> Any:
        """Wait for a JavaScript expression to return truthy.

        Args:
            expression: JavaScript expression.
            timeout: Maximum wait time in seconds.
            poll_interval: Time between checks in seconds.

        Returns:
            Result of the expression.

        Raises:
            TimeoutError: If timeout is reached.
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Timeout waiting for function: {expression[:50]}..."
                )

            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            )

            if "exceptionDetails" not in result:
                value = result.get("result", {}).get("value")
                if value:
                    return value

            await asyncio.sleep(poll_interval)

    async def wait_for_navigation(
        self,
        *,
        timeout: float = 30.0,
        wait_until: str = "load",
    ) -> None:
        """Wait for navigation to complete.

        Args:
            timeout: Maximum wait time in seconds.
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle').

        Raises:
            TimeoutError: If timeout is reached.
        """
        event_name = {
            "load": "Page.loadEventFired",
            "domcontentloaded": "Page.domContentEventFired",
        }.get(wait_until, "Page.loadEventFired")

        event_received = asyncio.Event()

        def on_event(params: dict) -> None:
            event_received.set()

        self._session.on(event_name, on_event)

        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            # Refresh document after navigation
            self._document_node_id = None
        finally:
            self._session.off(event_name, on_event)

    # Utility methods

    async def get_content(self) -> str:
        """Get the page HTML content.

        Returns:
            Full HTML of the page.
        """
        result = await self._session.send(
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML"},
        )
        return result.get("result", {}).get("value", "")

    async def set_content(self, html: str) -> None:
        """Set the page HTML content.

        Args:
            html: HTML content to set.
        """
        doc_node_id = await self._ensure_document()
        await self._session.send(
            "DOM.setOuterHTML",
            {"nodeId": doc_node_id, "outerHTML": html},
        )
        # Refresh document reference
        self._document_node_id = None

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript in the page context.

        Args:
            expression: JavaScript expression.

        Returns:
            Evaluation result.
        """
        result = await self._session.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise RuntimeError(f"JavaScript error: {exc.get('text', 'Unknown error')}")

        return result.get("result", {}).get("value")

    async def scroll_to(
        self,
        x: int = 0,
        y: int = 0,
        *,
        behavior: str = "instant",
    ) -> None:
        """Scroll the page to a position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            behavior: Scroll behavior ('instant', 'smooth').
        """
        await self.evaluate(
            f"window.scrollTo({{ left: {x}, top: {y}, behavior: '{behavior}' }})"
        )

    async def scroll_by(
        self,
        x: int = 0,
        y: int = 0,
        *,
        behavior: str = "instant",
    ) -> None:
        """Scroll the page by an amount.

        Args:
            x: X offset.
            y: Y offset.
            behavior: Scroll behavior ('instant', 'smooth').
        """
        await self.evaluate(
            f"window.scrollBy({{ left: {x}, top: {y}, behavior: '{behavior}' }})"
        )

    async def get_viewport_size(self) -> dict[str, int]:
        """Get the viewport size.

        Returns:
            Dict with width and height.
        """
        result = await self.evaluate(
            "({ width: window.innerWidth, height: window.innerHeight })"
        )
        return result or {"width": 0, "height": 0}

    async def get_scroll_position(self) -> dict[str, int]:
        """Get the current scroll position.

        Returns:
            Dict with x and y.
        """
        result = await self.evaluate(
            "({ x: window.scrollX, y: window.scrollY })"
        )
        return result or {"x": 0, "y": 0}


__all__ = ["DOMService"]
