"""
Network module for kuromi-browser.

This module provides network interception and manipulation:
- NetworkInterceptor: Intercept and modify requests/responses
- RequestPattern: Define patterns for request matching
- ResponseMock: Mock responses for testing
"""

from typing import Any, Callable, Optional, Union
from dataclasses import dataclass

from kuromi_browser.models import NetworkRequest, NetworkResponse


@dataclass
class RequestPattern:
    """Pattern for matching network requests."""

    url: Optional[str] = None
    url_pattern: Optional[str] = None
    method: Optional[str] = None
    resource_type: Optional[str] = None

    def matches(self, request: NetworkRequest) -> bool:
        """Check if this pattern matches a request."""
        raise NotImplementedError


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
        raise NotImplementedError


class NetworkInterceptor:
    """Intercepts and modifies network requests.

    Allows inspection, blocking, and modification of network traffic.
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
        raise NotImplementedError


class NetworkMonitor:
    """Monitors network traffic for analysis.

    Collects and aggregates network request/response data.
    """

    def __init__(self) -> None:
        self._requests: list[NetworkRequest] = []
        self._responses: list[NetworkResponse] = []
        self._enabled = False

    @property
    def requests(self) -> list[NetworkRequest]:
        return self._requests.copy()

    @property
    def responses(self) -> list[NetworkResponse]:
        return self._responses.copy()

    def start(self) -> None:
        """Start monitoring network traffic."""
        self._enabled = True

    def stop(self) -> None:
        """Stop monitoring network traffic."""
        self._enabled = False

    def clear(self) -> None:
        """Clear collected data."""
        self._requests.clear()
        self._responses.clear()

    def wait_for_request(
        self,
        pattern: RequestPattern,
        timeout: float = 30.0,
    ) -> NetworkRequest:
        """Wait for a request matching the pattern."""
        raise NotImplementedError

    def wait_for_response(
        self,
        pattern: RequestPattern,
        timeout: float = 30.0,
    ) -> NetworkResponse:
        """Wait for a response matching the pattern."""
        raise NotImplementedError


__all__ = [
    "RequestPattern",
    "ResponseMock",
    "NetworkInterceptor",
    "NetworkMonitor",
]
