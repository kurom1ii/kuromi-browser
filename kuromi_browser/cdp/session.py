"""
CDP Session management.

Provides high-level session management for CDP targets.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

from kuromi_browser.cdp.connection import CDPConnection, CDPError
from kuromi_browser.interfaces import BaseCDPSession

logger = logging.getLogger(__name__)


class CDPSession(BaseCDPSession):
    """Chrome DevTools Protocol session for a specific target.

    A CDPSession is attached to a specific target (page, worker, etc.) and
    provides methods to send CDP commands and receive events.

    Example:
        async with CDPConnection(ws_url) as connection:
            session = await CDPSession.create(connection, target_id)
            await session.send("Page.enable")
            await session.send("Page.navigate", {"url": "https://example.com"})
            await session.detach()
    """

    def __init__(
        self,
        connection: CDPConnection,
        target_id: str,
        session_id: str,
    ) -> None:
        """Initialize CDP session.

        Args:
            connection: Parent CDP connection.
            target_id: Target ID this session is attached to.
            session_id: CDP session ID.
        """
        self._connection = connection
        self._target_id = target_id
        self._session_id = session_id
        self._event_handlers: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self._detached = False

    @property
    def target_id(self) -> str:
        """Get the target ID."""
        return self._target_id

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def is_connected(self) -> bool:
        """Check if session is connected."""
        return not self._detached and self._connection.is_connected

    @classmethod
    async def create(
        cls,
        connection: CDPConnection,
        target_id: str,
        *,
        flatten: bool = True,
    ) -> "CDPSession":
        """Create and attach a new CDP session to a target.

        Args:
            connection: CDP connection to use.
            target_id: Target to attach to.
            flatten: Use flatten mode for session.

        Returns:
            Attached CDPSession.
        """
        result = await connection.send(
            "Target.attachToTarget",
            {
                "targetId": target_id,
                "flatten": flatten,
            },
        )
        session_id = result["sessionId"]
        session = cls(connection, target_id, session_id)

        logger.debug(f"Created CDP session {session_id} for target {target_id}")
        return session

    async def send(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Send a CDP command to this session's target.

        Args:
            method: CDP method name.
            params: Method parameters.
            timeout: Command timeout in seconds.

        Returns:
            Command result.

        Raises:
            CDPError: If command fails.
            RuntimeError: If session is detached.
        """
        if self._detached:
            raise RuntimeError("Session is detached")

        return await self._connection.send(
            method,
            params,
            session_id=self._session_id,
            timeout=timeout,
        )

    def on(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register an event handler for this session.

        Args:
            event: Event name (e.g., "Page.loadEventFired").
            handler: Event handler function.
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

        # Also register with connection for session-scoped events
        self._connection.on(event, handler, session_id=self._session_id)

    def off(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Remove an event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
        """
        if event in self._event_handlers:
            handlers = self._event_handlers[event]
            if handler in handlers:
                handlers.remove(handler)

        self._connection.off(event, handler, session_id=self._session_id)

    async def detach(self) -> None:
        """Detach from the target."""
        if self._detached:
            return

        try:
            await self._connection.send(
                "Target.detachFromTarget",
                {"sessionId": self._session_id},
            )
        except CDPError:
            pass  # Ignore errors during detach

        self._connection.remove_session_handlers(self._session_id)
        self._detached = True
        self._event_handlers.clear()

        logger.debug(f"Detached CDP session {self._session_id}")

    async def __aenter__(self) -> "CDPSession":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.detach()


class TargetManager:
    """Manages CDP targets and sessions.

    Provides utilities for discovering and managing browser targets.
    """

    def __init__(self, connection: CDPConnection) -> None:
        """Initialize target manager.

        Args:
            connection: CDP connection to use.
        """
        self._connection = connection
        self._sessions: dict[str, CDPSession] = {}
        self._target_info: dict[str, dict[str, Any]] = {}

    async def get_targets(self) -> list[dict[str, Any]]:
        """Get all available targets.

        Returns:
            List of target info dictionaries.
        """
        result = await self._connection.send("Target.getTargets")
        targets = result.get("targetInfos", [])

        # Cache target info
        for target in targets:
            self._target_info[target["targetId"]] = target

        return targets

    async def get_pages(self) -> list[dict[str, Any]]:
        """Get all page targets.

        Returns:
            List of page target info.
        """
        targets = await self.get_targets()
        return [t for t in targets if t.get("type") == "page"]

    async def get_target_info(self, target_id: str) -> Optional[dict[str, Any]]:
        """Get info for a specific target.

        Args:
            target_id: Target ID.

        Returns:
            Target info or None.
        """
        if target_id in self._target_info:
            return self._target_info[target_id]

        await self.get_targets()
        return self._target_info.get(target_id)

    async def create_session(self, target_id: str) -> CDPSession:
        """Create a CDP session for a target.

        Args:
            target_id: Target to attach to.

        Returns:
            CDP session.
        """
        if target_id in self._sessions:
            session = self._sessions[target_id]
            if session.is_connected:
                return session

        session = await CDPSession.create(self._connection, target_id)
        self._sessions[target_id] = session
        return session

    async def close_session(self, target_id: str) -> None:
        """Close a CDP session.

        Args:
            target_id: Target ID of session to close.
        """
        session = self._sessions.pop(target_id, None)
        if session:
            await session.detach()

    async def create_page(self, url: str = "about:blank") -> CDPSession:
        """Create a new page and return its session.

        Args:
            url: Initial URL for the page.

        Returns:
            CDP session for the new page.
        """
        result = await self._connection.send(
            "Target.createTarget",
            {"url": url},
        )
        target_id = result["targetId"]
        return await self.create_session(target_id)

    async def close_page(self, target_id: str) -> None:
        """Close a page.

        Args:
            target_id: Target ID of page to close.
        """
        await self.close_session(target_id)
        try:
            await self._connection.send(
                "Target.closeTarget",
                {"targetId": target_id},
            )
        except CDPError:
            pass

    async def enable_auto_attach(self) -> None:
        """Enable automatic attachment to new targets."""
        await self._connection.send(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            },
        )

    async def close_all_sessions(self) -> None:
        """Close all managed sessions."""
        for target_id in list(self._sessions.keys()):
            await self.close_session(target_id)


class PageSession:
    """High-level page session with common CDP domains enabled.

    Wraps a CDPSession with convenience methods for page automation.
    """

    def __init__(self, session: CDPSession) -> None:
        """Initialize page session.

        Args:
            session: CDP session for the page.
        """
        self._session = session
        self._enabled_domains: set[str] = set()

    @property
    def session(self) -> CDPSession:
        """Get the underlying CDP session."""
        return self._session

    async def enable(self) -> None:
        """Enable common CDP domains for page automation."""
        domains = ["Page", "DOM", "Network", "Runtime"]

        for domain in domains:
            if domain not in self._enabled_domains:
                await self._session.send(f"{domain}.enable")
                self._enabled_domains.add(domain)

    async def disable(self) -> None:
        """Disable enabled CDP domains."""
        for domain in list(self._enabled_domains):
            try:
                await self._session.send(f"{domain}.disable")
            except CDPError:
                pass
            self._enabled_domains.discard(domain)

    # Page domain methods

    async def navigate(
        self,
        url: str,
        *,
        referrer: Optional[str] = None,
        wait_until: str = "load",
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Navigate to a URL.

        Args:
            url: URL to navigate to.
            referrer: Optional referrer URL.
            wait_until: Wait condition (load, domcontentloaded, networkidle).
            timeout: Navigation timeout in seconds.

        Returns:
            Navigation result.
        """
        params: dict[str, Any] = {"url": url}
        if referrer:
            params["referrer"] = referrer

        # Set up load event waiter
        load_event = asyncio.Event()

        def on_load(params: dict[str, Any]) -> None:
            load_event.set()

        event_name = {
            "load": "Page.loadEventFired",
            "domcontentloaded": "Page.domContentEventFired",
        }.get(wait_until, "Page.loadEventFired")

        self._session.on(event_name, on_load)

        try:
            result = await self._session.send("Page.navigate", params)

            if "errorText" in result:
                raise CDPError(-1, result["errorText"])

            # Wait for load event
            await asyncio.wait_for(load_event.wait(), timeout=timeout)

            return result
        finally:
            self._session.off(event_name, on_load)

    async def reload(self, *, ignore_cache: bool = False) -> None:
        """Reload the page.

        Args:
            ignore_cache: Ignore cached content.
        """
        await self._session.send(
            "Page.reload",
            {"ignoreCache": ignore_cache},
        )

    async def get_content(self) -> str:
        """Get the page HTML content.

        Returns:
            Page HTML.
        """
        result = await self._session.send(
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML"},
        )
        return result.get("result", {}).get("value", "")

    async def screenshot(
        self,
        *,
        format: str = "png",
        quality: Optional[int] = None,
        full_page: bool = False,
    ) -> bytes:
        """Take a screenshot.

        Args:
            format: Image format (png, jpeg, webp).
            quality: JPEG quality (0-100).
            full_page: Capture full scrollable page.

        Returns:
            Screenshot image data.
        """
        import base64

        params: dict[str, Any] = {"format": format}
        if quality is not None:
            params["quality"] = quality
        if full_page:
            params["captureBeyondViewport"] = True

        result = await self._session.send("Page.captureScreenshot", params)
        return base64.b64decode(result["data"])

    # DOM domain methods

    async def get_document(self) -> dict[str, Any]:
        """Get the document root node.

        Returns:
            Document node.
        """
        result = await self._session.send("DOM.getDocument", {"depth": -1})
        return result.get("root", {})

    async def query_selector(
        self,
        selector: str,
        *,
        node_id: Optional[int] = None,
    ) -> Optional[int]:
        """Query for an element.

        Args:
            selector: CSS selector.
            node_id: Node to search within (default: document).

        Returns:
            Node ID or None if not found.
        """
        if node_id is None:
            doc = await self.get_document()
            node_id = doc.get("nodeId")

        try:
            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": node_id, "selector": selector},
            )
            return result.get("nodeId") if result.get("nodeId", 0) > 0 else None
        except CDPError:
            return None

    async def query_selector_all(
        self,
        selector: str,
        *,
        node_id: Optional[int] = None,
    ) -> list[int]:
        """Query for all matching elements.

        Args:
            selector: CSS selector.
            node_id: Node to search within.

        Returns:
            List of node IDs.
        """
        if node_id is None:
            doc = await self.get_document()
            node_id = doc.get("nodeId")

        result = await self._session.send(
            "DOM.querySelectorAll",
            {"nodeId": node_id, "selector": selector},
        )
        return result.get("nodeIds", [])

    # Runtime domain methods

    async def evaluate(
        self,
        expression: str,
        *,
        await_promise: bool = True,
        return_by_value: bool = True,
    ) -> Any:
        """Evaluate JavaScript expression.

        Args:
            expression: JavaScript expression.
            await_promise: Await promise results.
            return_by_value: Return value directly vs object reference.

        Returns:
            Evaluation result.
        """
        result = await self._session.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": return_by_value,
            },
        )

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise CDPError(-1, exc.get("text", "JavaScript error"))

        return result.get("result", {}).get("value")

    async def call_function(
        self,
        function_declaration: str,
        *args: Any,
        await_promise: bool = True,
        return_by_value: bool = True,
    ) -> Any:
        """Call a JavaScript function.

        Args:
            function_declaration: Function code.
            *args: Function arguments.
            await_promise: Await promise results.
            return_by_value: Return value directly.

        Returns:
            Function result.
        """
        result = await self._session.send(
            "Runtime.callFunctionOn",
            {
                "functionDeclaration": function_declaration,
                "arguments": [{"value": arg} for arg in args],
                "awaitPromise": await_promise,
                "returnByValue": return_by_value,
            },
        )

        if "exceptionDetails" in result:
            exc = result["exceptionDetails"]
            raise CDPError(-1, exc.get("text", "JavaScript error"))

        return result.get("result", {}).get("value")

    # Network domain methods

    async def set_extra_headers(self, headers: dict[str, str]) -> None:
        """Set extra HTTP headers.

        Args:
            headers: Headers to add to all requests.
        """
        await self._session.send(
            "Network.setExtraHTTPHeaders",
            {"headers": headers},
        )

    async def set_user_agent(
        self,
        user_agent: str,
        *,
        accept_language: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> None:
        """Set user agent override.

        Args:
            user_agent: User agent string.
            accept_language: Accept-Language header.
            platform: Platform override.
        """
        params: dict[str, Any] = {"userAgent": user_agent}
        if accept_language:
            params["acceptLanguage"] = accept_language
        if platform:
            params["platform"] = platform

        await self._session.send("Network.setUserAgentOverride", params)

    async def set_request_interception(self, patterns: list[dict[str, Any]]) -> None:
        """Enable request interception.

        Args:
            patterns: URL patterns to intercept.
        """
        await self._session.send(
            "Fetch.enable",
            {"patterns": patterns},
        )

    async def close(self) -> None:
        """Close the page session."""
        await self.disable()
        await self._session.detach()
