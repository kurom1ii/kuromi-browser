"""
CDP WebSocket connection handler.

Manages the WebSocket connection to Chrome/Chromium's DevTools Protocol endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    websockets = None  # type: ignore
    WebSocketClientProtocol = None  # type: ignore

logger = logging.getLogger(__name__)


class CDPError(Exception):
    """CDP protocol error."""

    def __init__(self, code: int, message: str, data: Optional[Any] = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"CDP Error {code}: {message}")


class CDPConnection:
    """Manages the WebSocket connection to a browser's CDP endpoint.

    Handles message routing, callbacks, and event dispatching.

    Example:
        connection = CDPConnection("ws://localhost:9222/devtools/browser/xxx")
        await connection.connect()
        result = await connection.send("Browser.getVersion")
        print(result)
        await connection.disconnect()
    """

    def __init__(
        self,
        ws_url: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        """Initialize CDP connection.

        Args:
            ws_url: WebSocket URL to connect to.
            timeout: Default timeout for commands in seconds.
        """
        if websockets is None:
            raise ImportError(
                "websockets package is required for CDP. "
                "Install it with: pip install websockets"
            )

        self._ws_url = ws_url
        self._timeout = timeout
        self._ws: Optional[WebSocketClientProtocol] = None
        self._message_id = 0
        self._callbacks: dict[int, asyncio.Future[Any]] = {}
        self._event_handlers: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}
        self._session_handlers: dict[str, dict[str, list[Callable[[dict[str, Any]], Any]]]] = {}
        self._receive_task: Optional[asyncio.Task[None]] = None
        self._connected = False
        self._closed = False

    @property
    def ws_url(self) -> str:
        """Get the WebSocket URL."""
        return self._ws_url

    @property
    def is_connected(self) -> bool:
        """Check if connected to CDP."""
        return self._connected and self._ws is not None

    async def connect(self) -> None:
        """Establish WebSocket connection to CDP endpoint."""
        if self._connected:
            return

        if self._closed:
            raise RuntimeError("Connection was closed and cannot be reused")

        logger.debug(f"Connecting to CDP: {self._ws_url}")
        self._ws = await websockets.connect(
            self._ws_url,
            max_size=100 * 1024 * 1024,  # 100MB max message size
            ping_interval=30,
            ping_timeout=10,
        )
        self._connected = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.debug("CDP connection established")

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if not self._connected:
            return

        self._connected = False
        self._closed = True

        # Cancel receive loop
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Cancel pending callbacks
        for future in self._callbacks.values():
            if not future.done():
                future.cancel()
        self._callbacks.clear()

        # Close WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None

        logger.debug("CDP connection closed")

    async def send(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        *,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Send a CDP command and wait for response.

        Args:
            method: CDP method name (e.g., "Page.navigate").
            params: Optional parameters for the method.
            session_id: Optional session ID for target-specific commands.
            timeout: Optional timeout override in seconds.

        Returns:
            The result from the CDP response.

        Raises:
            CDPError: If the CDP command returns an error.
            asyncio.TimeoutError: If the command times out.
            RuntimeError: If not connected.
        """
        if not self._connected or self._ws is None:
            raise RuntimeError("Not connected to CDP")

        self._message_id += 1
        message_id = self._message_id

        message: dict[str, Any] = {
            "id": message_id,
            "method": method,
        }
        if params:
            message["params"] = params
        if session_id:
            message["sessionId"] = session_id

        # Create future for response
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._callbacks[message_id] = future

        try:
            # Send message
            await self._ws.send(json.dumps(message))
            logger.debug(f"CDP send: {method} (id={message_id})")

            # Wait for response with timeout
            result = await asyncio.wait_for(
                future,
                timeout=timeout or self._timeout,
            )
            return result

        except asyncio.TimeoutError:
            self._callbacks.pop(message_id, None)
            raise
        except Exception:
            self._callbacks.pop(message_id, None)
            raise

    def on(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Register a CDP event handler.

        Args:
            event: Event name (e.g., "Page.loadEventFired").
            handler: Callback function for the event.
            session_id: Optional session ID to scope the handler.
        """
        if session_id:
            if session_id not in self._session_handlers:
                self._session_handlers[session_id] = {}
            if event not in self._session_handlers[session_id]:
                self._session_handlers[session_id][event] = []
            self._session_handlers[session_id][event].append(handler)
        else:
            if event not in self._event_handlers:
                self._event_handlers[event] = []
            self._event_handlers[event].append(handler)

    def off(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
        *,
        session_id: Optional[str] = None,
    ) -> None:
        """Remove a CDP event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
            session_id: Optional session ID.
        """
        if session_id:
            if session_id in self._session_handlers:
                handlers = self._session_handlers[session_id].get(event, [])
                if handler in handlers:
                    handlers.remove(handler)
        else:
            handlers = self._event_handlers.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

    def remove_session_handlers(self, session_id: str) -> None:
        """Remove all handlers for a session.

        Args:
            session_id: Session ID to remove handlers for.
        """
        self._session_handlers.pop(session_id, None)

    async def _receive_loop(self) -> None:
        """Background loop to receive and dispatch messages."""
        if self._ws is None:
            return

        try:
            async for message in self._ws:
                if not self._connected:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from CDP: {message[:100]}")
                except Exception as e:
                    logger.exception(f"Error handling CDP message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.debug("CDP WebSocket connection closed")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"CDP receive loop error: {e}")
        finally:
            self._connected = False

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle an incoming CDP message.

        Args:
            data: Parsed JSON message.
        """
        if "id" in data:
            # Response to a command
            message_id = data["id"]
            future = self._callbacks.pop(message_id, None)
            if future and not future.done():
                if "error" in data:
                    error = data["error"]
                    future.set_exception(
                        CDPError(
                            error.get("code", -1),
                            error.get("message", "Unknown error"),
                            error.get("data"),
                        )
                    )
                else:
                    future.set_result(data.get("result", {}))

        elif "method" in data:
            # Event
            event = data["method"]
            params = data.get("params", {})
            session_id = data.get("sessionId")

            handlers: list[Callable[[dict[str, Any]], Any]] = []

            # Get session-specific handlers
            if session_id and session_id in self._session_handlers:
                handlers.extend(
                    self._session_handlers[session_id].get(event, [])
                )

            # Get global handlers
            handlers.extend(self._event_handlers.get(event, []))

            # Dispatch to handlers
            for handler in handlers:
                try:
                    result = handler(params)
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.exception(f"Error in CDP event handler for {event}: {e}")

    async def __aenter__(self) -> "CDPConnection":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
