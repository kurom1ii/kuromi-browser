"""
Network module for kuromi-browser.

This module provides network interception, monitoring, and manipulation:
- NetworkMonitor: Monitor and capture network traffic
- RequestInterceptor: Intercept, block, modify, and mock requests
- HARRecorder: Record network traffic in HAR format
- WebSocketMonitor: Monitor WebSocket connections and messages
- RequestPattern: Define patterns for request matching
- ResponseMock: Mock responses for testing
"""

from typing import Any, Callable, Optional, Union
from dataclasses import dataclass

from kuromi_browser.models import NetworkRequest, NetworkResponse
from kuromi_browser.network.monitor import NetworkMonitor
from kuromi_browser.network.interceptor import RequestInterceptor, MockResponse, InterceptRule
from kuromi_browser.network.har import HARRecorder
from kuromi_browser.network.websocket import (
    WebSocketMonitor,
    WebSocketConnection,
    WebSocketFrame,
)


@dataclass
class RequestPattern:
    """Pattern for matching network requests."""

    url: Optional[str] = None
    url_pattern: Optional[str] = None
    method: Optional[str] = None
    resource_type: Optional[str] = None

    def matches(self, request: NetworkRequest) -> bool:
        """Check if this pattern matches a request."""
        import fnmatch

        if self.url and request.url != self.url:
            return False
        if self.url_pattern and not fnmatch.fnmatch(request.url, self.url_pattern):
            return False
        if self.method and request.method.upper() != self.method.upper():
            return False
        if self.resource_type and request.resource_type != self.resource_type:
            return False
        return True


class ResponseMock:
    """Mock response for intercepted requests."""

    def __init__(
        self,
        *,
        status: int = 200,
        status_text: str = "OK",
        headers: Optional[dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        content_type: str = "text/plain",
    ) -> None:
        self.status = status
        self.status_text = status_text
        self.headers = headers or {}
        self.body = body
        self.content_type = content_type

    def to_response(self, request: NetworkRequest) -> NetworkResponse:
        """Convert to NetworkResponse."""
        import time

        body_bytes = None
        if self.body:
            body_bytes = self.body if isinstance(self.body, bytes) else self.body.encode("utf-8")

        return NetworkResponse(
            request_id=request.request_id,
            url=request.url,
            status=self.status,
            status_text=self.status_text,
            headers=self.headers,
            mime_type=self.content_type,
            body=body_bytes,
            timestamp=time.time(),
        )


class NetworkInterceptor:
    """Intercepts and modifies network requests.

    Allows inspection, blocking, and modification of network traffic.
    This is a higher-level wrapper around RequestInterceptor.
    """

    def __init__(self) -> None:
        self._handlers: list[tuple[RequestPattern, Callable[..., Any]]] = []
        self._blocked_patterns: list[RequestPattern] = []

    def add_handler(
        self,
        pattern: RequestPattern,
        handler: Callable[[NetworkRequest], Optional[NetworkResponse]],
    ) -> None:
        """Add a request handler for matching requests."""
        self._handlers.append((pattern, handler))

    def block(self, pattern: RequestPattern) -> None:
        """Block requests matching the pattern."""
        self._blocked_patterns.append(pattern)

    def unblock(self, pattern: RequestPattern) -> None:
        """Remove a block pattern."""
        if pattern in self._blocked_patterns:
            self._blocked_patterns.remove(pattern)

    async def handle_request(self, request: NetworkRequest) -> Optional[NetworkResponse]:
        """Process a request through handlers."""
        for pattern in self._blocked_patterns:
            if pattern.matches(request):
                return None

        for pattern, handler in self._handlers:
            if pattern.matches(request):
                result = handler(request)
                if result is not None:
                    return result

        return None


__all__ = [
    # Core classes
    "NetworkMonitor",
    "RequestInterceptor",
    "HARRecorder",
    "WebSocketMonitor",
    # Data classes
    "RequestPattern",
    "ResponseMock",
    "MockResponse",
    "InterceptRule",
    "WebSocketConnection",
    "WebSocketFrame",
    # Legacy class
    "NetworkInterceptor",
]
