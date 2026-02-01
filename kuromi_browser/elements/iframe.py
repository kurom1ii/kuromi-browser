"""
Iframe support for kuromi-browser.

Provides utilities for working with iframes, including cross-iframe
element finding and frame management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.elements.browser_element import BrowserElement

from kuromi_browser.elements.locator import Locator

logger = logging.getLogger(__name__)


class FrameInfo:
    """Information about a frame."""

    def __init__(
        self,
        frame_id: str,
        url: str,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        loader_id: Optional[str] = None,
    ) -> None:
        """Initialize FrameInfo.

        Args:
            frame_id: Unique frame identifier.
            url: Frame URL.
            name: Frame name attribute.
            parent_id: Parent frame ID.
            loader_id: Loader identifier.
        """
        self.frame_id = frame_id
        self.url = url
        self.name = name
        self.parent_id = parent_id
        self.loader_id = loader_id

    @property
    def is_main_frame(self) -> bool:
        """Check if this is the main frame."""
        return self.parent_id is None

    def __repr__(self) -> str:
        return f"<FrameInfo id={self.frame_id} url={self.url[:50]}...>"


class FrameContext:
    """Context for working within a specific frame.

    Provides element querying and manipulation within an iframe context.
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        frame_id: str,
        frame_info: Optional[FrameInfo] = None,
    ) -> None:
        """Initialize FrameContext.

        Args:
            cdp_session: CDP session for sending commands.
            frame_id: Frame ID to work within.
            frame_info: Optional frame information.
        """
        self._session = cdp_session
        self._frame_id = frame_id
        self._info = frame_info
        self._document_node_id: Optional[int] = None

    @property
    def frame_id(self) -> str:
        """Get the frame ID."""
        return self._frame_id

    @property
    def info(self) -> Optional[FrameInfo]:
        """Get frame information."""
        return self._info

    async def get_document(self) -> int:
        """Get the document node ID for this frame.

        Returns:
            Document node ID.
        """
        if self._document_node_id:
            return self._document_node_id

        # Get frame's execution context
        result = await self._session.send(
            "Page.getFrameTree",
        )

        # Find our frame and get its document
        async def find_frame_document(tree: dict) -> Optional[int]:
            frame = tree.get("frame", {})
            if frame.get("id") == self._frame_id:
                # Get document for this frame
                result = await self._session.send(
                    "DOM.getDocument",
                    {"depth": 0},
                )
                return result.get("root", {}).get("nodeId")

            for child in tree.get("childFrames", []):
                doc_id = await find_frame_document(child)
                if doc_id:
                    return doc_id
            return None

        self._document_node_id = await find_frame_document(
            result.get("frameTree", {})
        )

        if not self._document_node_id:
            raise RuntimeError(f"Could not get document for frame: {self._frame_id}")

        return self._document_node_id

    async def query(self, selector: str) -> Optional["BrowserElement"]:
        """Query for an element within this frame.

        Args:
            selector: Selector string.

        Returns:
            Element or None if not found.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        doc_node_id = await self.get_document()
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            try:
                result = await self._session.send(
                    "DOM.querySelector",
                    {"nodeId": doc_node_id, "selector": parsed},
                )
                node_id = result.get("nodeId", 0)
                if node_id > 0:
                    return BrowserElement(
                        self._session,
                        node_id,
                        frame_id=self._frame_id,
                    )
            except Exception as e:
                logger.debug(f"Query in frame failed: {e}")
            return None
        else:
            # XPath query in frame context
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": f"""
                        (function() {{
                            const result = document.evaluate(
                                '{parsed.replace("'", "\\'")}',
                                document,
                                null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE,
                                null
                            );
                            return result.singleNodeValue;
                        }})()
                    """,
                    "returnByValue": False,
                    "contextId": await self._get_context_id(),
                },
            )
            obj = result.get("result", {})
            if obj.get("type") == "object" and obj.get("subtype") != "null":
                object_id = obj.get("objectId")
                if object_id:
                    return await self._element_from_object_id(object_id)
            return None

    async def query_all(self, selector: str) -> list["BrowserElement"]:
        """Query for all elements within this frame.

        Args:
            selector: Selector string.

        Returns:
            List of matching elements.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        doc_node_id = await self.get_document()
        selector_type, parsed = Locator.parse(selector)

        if selector_type == "css":
            try:
                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": doc_node_id, "selector": parsed},
                )
                return [
                    BrowserElement(self._session, nid, frame_id=self._frame_id)
                    for nid in result.get("nodeIds", [])
                ]
            except Exception as e:
                logger.debug(f"Query all in frame failed: {e}")
            return []
        else:
            # XPath query all
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": f"""
                        (function() {{
                            const result = document.evaluate(
                                '{parsed.replace("'", "\\'")}',
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
                    "contextId": await self._get_context_id(),
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

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript within this frame.

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
                "contextId": await self._get_context_id(),
            },
        )

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise RuntimeError(f"JavaScript error: {exc.get('text', 'Unknown error')}")

        return result.get("result", {}).get("value")

    async def get_content(self) -> str:
        """Get the HTML content of this frame.

        Returns:
            Full HTML of the frame.
        """
        return await self.evaluate("document.documentElement.outerHTML")

    async def _get_context_id(self) -> int:
        """Get the execution context ID for this frame."""
        result = await self._session.send(
            "Runtime.evaluate",
            {
                "expression": "1",
                "returnByValue": True,
            },
        )
        return result.get("contextId", 0)

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
                    frame_id=self._frame_id,
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
                    frame_id=self._frame_id,
                )
        except Exception as e:
            logger.debug(f"Failed to create element from object: {e}")
        return None

    def __repr__(self) -> str:
        return f"<FrameContext frame_id={self._frame_id}>"


class IframeHelper:
    """Helper class for working with iframes.

    Provides methods for finding, entering, and managing iframes.
    """

    def __init__(self, cdp_session: "CDPSession") -> None:
        """Initialize IframeHelper.

        Args:
            cdp_session: CDP session for sending commands.
        """
        self._session = cdp_session

    async def list_frames(self) -> list[FrameInfo]:
        """List all frames in the page.

        Returns:
            List of frame information objects.
        """
        result = await self._session.send("Page.getFrameTree")
        frames = []

        def collect_frames(tree: dict, parent_id: Optional[str] = None) -> None:
            frame = tree.get("frame", {})
            frames.append(FrameInfo(
                frame_id=frame.get("id", ""),
                url=frame.get("url", ""),
                name=frame.get("name"),
                parent_id=parent_id,
                loader_id=frame.get("loaderId"),
            ))

            current_id = frame.get("id")
            for child in tree.get("childFrames", []):
                collect_frames(child, current_id)

        collect_frames(result.get("frameTree", {}))
        return frames

    async def get_main_frame(self) -> FrameContext:
        """Get the main frame context.

        Returns:
            FrameContext for the main frame.
        """
        frames = await self.list_frames()
        main_frame = next((f for f in frames if f.is_main_frame), None)

        if not main_frame:
            raise RuntimeError("Could not find main frame")

        return FrameContext(self._session, main_frame.frame_id, main_frame)

    async def get_frame_by_name(self, name: str) -> Optional[FrameContext]:
        """Get a frame by its name attribute.

        Args:
            name: Frame name.

        Returns:
            FrameContext or None if not found.
        """
        frames = await self.list_frames()
        frame = next((f for f in frames if f.name == name), None)

        if frame:
            return FrameContext(self._session, frame.frame_id, frame)
        return None

    async def get_frame_by_url(self, url: str, partial: bool = False) -> Optional[FrameContext]:
        """Get a frame by its URL.

        Args:
            url: Frame URL (or partial URL if partial=True).
            partial: If True, match partial URL.

        Returns:
            FrameContext or None if not found.
        """
        frames = await self.list_frames()

        if partial:
            frame = next((f for f in frames if url in f.url), None)
        else:
            frame = next((f for f in frames if f.url == url), None)

        if frame:
            return FrameContext(self._session, frame.frame_id, frame)
        return None

    async def enter_iframe(
        self,
        iframe: Union["BrowserElement", str],
    ) -> FrameContext:
        """Enter an iframe and return its context.

        Args:
            iframe: Iframe element or selector.

        Returns:
            FrameContext for the iframe.
        """
        from kuromi_browser.elements.browser_element import BrowserElement

        if isinstance(iframe, str):
            # Query for the iframe element first
            selector_type, parsed = Locator.parse(iframe)

            result = await self._session.send(
                "DOM.getDocument",
                {"depth": 0},
            )
            doc_node_id = result.get("root", {}).get("nodeId")

            if selector_type == "css":
                result = await self._session.send(
                    "DOM.querySelector",
                    {"nodeId": doc_node_id, "selector": parsed},
                )
                node_id = result.get("nodeId", 0)
                if node_id == 0:
                    raise ValueError(f"Iframe not found: {iframe}")
                iframe_element = BrowserElement(self._session, node_id)
            else:
                raise ValueError("iframe selector must be CSS for now")
        else:
            iframe_element = iframe

        # Get frame ID from the iframe element
        result = await self._session.send(
            "DOM.describeNode",
            {"nodeId": iframe_element.node_id, "depth": 0},
        )
        node = result.get("node", {})
        frame_id = node.get("frameId")

        if not frame_id:
            # Try getting from contentDocument
            result = await self._session.send(
                "Runtime.callFunctionOn",
                {
                    "objectId": await iframe_element._ensure_object_id(),
                    "functionDeclaration": """function() {
                        return this.contentWindow?.frameElement?.getAttribute('data-frame-id') ||
                               this.getAttribute('data-frame-id');
                    }""",
                    "returnByValue": True,
                },
            )

            # If still no frame ID, look through frame tree
            if not frame_id:
                frames = await self.list_frames()
                # Find frame by matching with iframe src
                iframe_src = await iframe_element.get_attr("src")
                if iframe_src:
                    frame = next((f for f in frames if iframe_src in f.url), None)
                    if frame:
                        frame_id = frame.frame_id

        if not frame_id:
            raise ValueError("Could not determine frame ID for iframe")

        # Get frame info
        frames = await self.list_frames()
        frame_info = next((f for f in frames if f.frame_id == frame_id), None)

        return FrameContext(self._session, frame_id, frame_info)

    async def query_across_frames(
        self,
        selector: str,
    ) -> Optional["BrowserElement"]:
        """Query for an element across all frames.

        Searches the main frame and all iframes for a matching element.

        Args:
            selector: Selector string.

        Returns:
            First matching element or None.
        """
        frames = await self.list_frames()

        for frame_info in frames:
            try:
                context = FrameContext(self._session, frame_info.frame_id, frame_info)
                element = await context.query(selector)
                if element:
                    return element
            except Exception as e:
                logger.debug(f"Error querying frame {frame_info.frame_id}: {e}")
                continue

        return None

    async def query_all_across_frames(
        self,
        selector: str,
    ) -> list["BrowserElement"]:
        """Query for all elements across all frames.

        Args:
            selector: Selector string.

        Returns:
            List of all matching elements from all frames.
        """
        frames = await self.list_frames()
        all_elements = []

        for frame_info in frames:
            try:
                context = FrameContext(self._session, frame_info.frame_id, frame_info)
                elements = await context.query_all(selector)
                all_elements.extend(elements)
            except Exception as e:
                logger.debug(f"Error querying frame {frame_info.frame_id}: {e}")
                continue

        return all_elements


__all__ = [
    "FrameInfo",
    "FrameContext",
    "IframeHelper",
]
