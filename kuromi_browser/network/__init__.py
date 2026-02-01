"""
Network module for kuromi-browser.

This module provides comprehensive network interception, monitoring, and manipulation:

Core Components:
- NetworkListener: Enhanced network traffic listener with CDP Network domain
- NetworkMonitor: Legacy network monitor for basic capture
- RequestInterceptor: Intercept, block, modify, and mock requests
- HARRecorder: Record and export network traffic in HAR format
- WebSocketMonitor: Monitor WebSocket connections and messages

Filtering System:
- NetworkFilter: Flexible request/response filtering
- FilterCriteria: Criteria for filtering network traffic
- ResourceType: Common resource type enum
- HttpMethod: HTTP method enum

Convenience Filters:
- url_filter: Filter by URL pattern
- method_filter: Filter by HTTP method
- resource_type_filter: Filter by resource type
- api_filter: Filter API requests (XHR/Fetch)
- document_filter: Filter document requests
- media_filter: Filter media requests
- script_filter: Filter script requests
- status_filter: Filter by response status
- error_filter: Filter error responses (4xx/5xx)
- success_filter: Filter successful responses (2xx)

Example:
    from kuromi_browser.network import (
        NetworkListener,
        NetworkFilter,
        FilterCriteria,
        ResourceType,
        api_filter,
        HARRecorder,
    )

    # Create listener with filter
    listener = NetworkListener(cdp_session)
    listener.set_filter(api_filter("*api.example.com*"))
    await listener.start()

    # Register callbacks
    listener.on_request(lambda req: print(f"Request: {req.url}"))
    listener.on_response(lambda res: print(f"Response: {res.status}"))

    # Wait for specific request
    request = await listener.wait_for_request("*users*")

    # Stream entries
    async for entry in listener.stream():
        print(f"Entry: {entry.request.url}")

    # Record to HAR
    recorder = HARRecorder.from_listener(listener)
    recorder.start("My Page")
    # ... navigate ...
    recorder.save("traffic.har")
"""

from typing import Any, Callable, Optional, Union
from dataclasses import dataclass

from kuromi_browser.models import NetworkRequest, NetworkResponse

# Core monitoring classes
from kuromi_browser.network.monitor import NetworkMonitor
from kuromi_browser.network.listener import (
    NetworkListener,
    NetworkEntry,
    StreamingChunk,
)

# Interception classes
from kuromi_browser.network.interceptor import (
    RequestInterceptor,
    MockResponse,
    InterceptRule,
)

# HAR recording
from kuromi_browser.network.har import (
    HARRecorder,
    HAREntry,
    HARPage,
    HARTimings,
)

# WebSocket monitoring
from kuromi_browser.network.websocket import (
    WebSocketMonitor,
    WebSocketConnection,
    WebSocketFrame,
)

# Filtering system
from kuromi_browser.network.filter import (
    NetworkFilter,
    FilterCriteria,
    ResourceType,
    HttpMethod,
    # Factory functions
    url_filter,
    method_filter,
    resource_type_filter,
    api_filter,
    document_filter,
    media_filter,
    script_filter,
    status_filter,
    error_filter,
    success_filter,
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
    """High-level network interceptor wrapper.

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
    # Core monitoring
    "NetworkMonitor",
    "NetworkListener",
    "NetworkEntry",
    "StreamingChunk",

    # Interception
    "RequestInterceptor",
    "MockResponse",
    "InterceptRule",
    "NetworkInterceptor",
    "RequestPattern",
    "ResponseMock",

    # HAR recording
    "HARRecorder",
    "HAREntry",
    "HARPage",
    "HARTimings",

    # WebSocket
    "WebSocketMonitor",
    "WebSocketConnection",
    "WebSocketFrame",

    # Filtering
    "NetworkFilter",
    "FilterCriteria",
    "ResourceType",
    "HttpMethod",

    # Filter factory functions
    "url_filter",
    "method_filter",
    "resource_type_filter",
    "api_filter",
    "document_filter",
    "media_filter",
    "script_filter",
    "status_filter",
    "error_filter",
    "success_filter",
]
