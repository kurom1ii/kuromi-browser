"""
WebSocket Monitor for kuromi-browser.

Monitors WebSocket connections and messages via CDP Network domain.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class WebSocketConnection:
    """WebSocket connection information."""

    request_id: str
    url: str
    initiator: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class WebSocketFrame:
    """WebSocket frame data."""

    request_id: str
    opcode: int
    mask: bool
    payload_data: str
    timestamp: float = field(default_factory=time.time)

    @property
    def is_text(self) -> bool:
        """Check if frame contains text data."""
        return self.opcode == 1

    @property
    def is_binary(self) -> bool:
        """Check if frame contains binary data."""
        return self.opcode == 2


class WebSocketMonitor:
    """Monitors WebSocket connections and messages.

    Uses CDP Network domain to capture WebSocket traffic.
    """

    def __init__(self, cdp_session: Any) -> None:
        """Initialize WebSocket monitor.

        Args:
            cdp_session: CDP session for communicating with browser.
        """
        self._session = cdp_session
        self._connections: dict[str, WebSocketConnection] = {}
        self._frames: dict[str, list[WebSocketFrame]] = {}
        self._connection_listeners: list[Callable[[WebSocketConnection], None]] = []
        self._frame_listeners: list[Callable[[WebSocketFrame], None]] = []
        self._close_listeners: list[Callable[[str], None]] = []
        self._error_listeners: list[Callable[[str, str], None]] = []
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if monitor is enabled."""
        return self._enabled

    async def start(self) -> None:
        """Start monitoring WebSocket traffic."""
        if self._enabled:
            return
        await self._session.send("Network.enable")
        self._session.on("Network.webSocketCreated", self._on_created)
        self._session.on("Network.webSocketFrameReceived", self._on_frame_received)
        self._session.on("Network.webSocketFrameSent", self._on_frame_sent)
        self._session.on("Network.webSocketClosed", self._on_closed)
        self._session.on("Network.webSocketFrameError", self._on_error)
        self._enabled = True

    async def stop(self) -> None:
        """Stop monitoring WebSocket traffic."""
        if not self._enabled:
            return
        self._enabled = False

    def on_connection(self, callback: Callable[[WebSocketConnection], None]) -> None:
        """Register callback for new WebSocket connections.

        Args:
            callback: Function called when a WebSocket connection is created.
        """
        self._connection_listeners.append(callback)

    def on_frame(self, callback: Callable[[WebSocketFrame], None]) -> None:
        """Register callback for WebSocket frames.

        Args:
            callback: Function called when a frame is received or sent.
        """
        self._frame_listeners.append(callback)

    def on_close(self, callback: Callable[[str], None]) -> None:
        """Register callback for WebSocket close events.

        Args:
            callback: Function called when a WebSocket is closed, with request_id.
        """
        self._close_listeners.append(callback)

    def on_error(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for WebSocket errors.

        Args:
            callback: Function called on error, with request_id and error message.
        """
        self._error_listeners.append(callback)

    def _on_created(self, params: dict[str, Any]) -> None:
        """Handle Network.webSocketCreated event."""
        connection = WebSocketConnection(
            request_id=params.get("requestId", ""),
            url=params.get("url", ""),
            initiator=params.get("initiator", {}).get("url"),
        )
        self._connections[connection.request_id] = connection
        self._frames[connection.request_id] = []

        for listener in self._connection_listeners:
            try:
                listener(connection)
            except Exception:
                pass

    def _on_frame_received(self, params: dict[str, Any]) -> None:
        """Handle Network.webSocketFrameReceived event."""
        self._handle_frame(params)

    def _on_frame_sent(self, params: dict[str, Any]) -> None:
        """Handle Network.webSocketFrameSent event."""
        self._handle_frame(params)

    def _handle_frame(self, params: dict[str, Any]) -> None:
        """Process a WebSocket frame event."""
        response = params.get("response", {})
        frame = WebSocketFrame(
            request_id=params.get("requestId", ""),
            opcode=response.get("opcode", 1),
            mask=response.get("mask", False),
            payload_data=response.get("payloadData", ""),
            timestamp=params.get("timestamp", time.time()),
        )

        if frame.request_id in self._frames:
            self._frames[frame.request_id].append(frame)

        for listener in self._frame_listeners:
            try:
                listener(frame)
            except Exception:
                pass

    def _on_closed(self, params: dict[str, Any]) -> None:
        """Handle Network.webSocketClosed event."""
        request_id = params.get("requestId", "")
        for listener in self._close_listeners:
            try:
                listener(request_id)
            except Exception:
                pass

    def _on_error(self, params: dict[str, Any]) -> None:
        """Handle Network.webSocketFrameError event."""
        request_id = params.get("requestId", "")
        error_message = params.get("errorMessage", "")
        for listener in self._error_listeners:
            try:
                listener(request_id, error_message)
            except Exception:
                pass

    def get_connections(self) -> list[WebSocketConnection]:
        """Get all tracked WebSocket connections.

        Returns:
            List of WebSocketConnection objects.
        """
        return list(self._connections.values())

    def get_connection(self, request_id: str) -> Optional[WebSocketConnection]:
        """Get a specific WebSocket connection.

        Args:
            request_id: The request ID.

        Returns:
            WebSocketConnection if found, None otherwise.
        """
        return self._connections.get(request_id)

    def get_frames(self, request_id: str) -> list[WebSocketFrame]:
        """Get all frames for a WebSocket connection.

        Args:
            request_id: The request ID.

        Returns:
            List of WebSocketFrame objects.
        """
        return self._frames.get(request_id, [])

    def get_all_frames(self) -> list[WebSocketFrame]:
        """Get all frames from all connections.

        Returns:
            List of all WebSocketFrame objects.
        """
        all_frames = []
        for frames in self._frames.values():
            all_frames.extend(frames)
        return sorted(all_frames, key=lambda f: f.timestamp)

    def clear(self) -> None:
        """Clear all tracked connections and frames."""
        self._connections.clear()
        self._frames.clear()
