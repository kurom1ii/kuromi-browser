"""
Network Monitor for kuromi-browser.

Monitors and captures network traffic via CDP Network domain.
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
from typing import Any, Callable, Optional

from kuromi_browser.models import NetworkRequest, NetworkResponse


class NetworkMonitor:
    """Monitors network traffic for analysis.

    Captures all network requests and responses via CDP protocol.
    """

    def __init__(self, cdp_session: Any) -> None:
        """Initialize network monitor.

        Args:
            cdp_session: CDP session for communicating with browser.
        """
        self._session = cdp_session
        self._requests: dict[str, NetworkRequest] = {}
        self._responses: dict[str, NetworkResponse] = {}
        self._request_listeners: list[Callable[[NetworkRequest], None]] = []
        self._response_listeners: list[Callable[[NetworkResponse], None]] = []
        self._enabled = False

    @property
    def enabled(self) -> bool:
        """Check if monitor is enabled."""
        return self._enabled

    async def start(self) -> None:
        """Start monitoring network traffic."""
        if self._enabled:
            return
        await self._session.send("Network.enable")
        self._session.on("Network.requestWillBeSent", self._on_request)
        self._session.on("Network.responseReceived", self._on_response)
        self._session.on("Network.loadingFinished", self._on_loading_finished)
        self._session.on("Network.loadingFailed", self._on_loading_failed)
        self._enabled = True

    async def stop(self) -> None:
        """Stop monitoring network traffic."""
        if not self._enabled:
            return
        await self._session.send("Network.disable")
        self._enabled = False

    def on_request(self, callback: Callable[[NetworkRequest], None]) -> None:
        """Register a callback for new requests.

        Args:
            callback: Function to call when a request is captured.
        """
        self._request_listeners.append(callback)

    def on_response(self, callback: Callable[[NetworkResponse], None]) -> None:
        """Register a callback for responses.

        Args:
            callback: Function to call when a response is received.
        """
        self._response_listeners.append(callback)

    def _on_request(self, params: dict[str, Any]) -> None:
        """Handle Network.requestWillBeSent event."""
        request_data = params.get("request", {})
        request = NetworkRequest(
            request_id=params.get("requestId", ""),
            url=request_data.get("url", ""),
            method=request_data.get("method", "GET"),
            headers=request_data.get("headers", {}),
            post_data=request_data.get("postData"),
            resource_type=params.get("type", "Other"),
            timestamp=params.get("timestamp", time.time()),
        )
        self._requests[request.request_id] = request
        for listener in self._request_listeners:
            try:
                listener(request)
            except Exception:
                pass

    def _on_response(self, params: dict[str, Any]) -> None:
        """Handle Network.responseReceived event."""
        response_data = params.get("response", {})
        response = NetworkResponse(
            request_id=params.get("requestId", ""),
            url=response_data.get("url", ""),
            status=response_data.get("status", 0),
            status_text=response_data.get("statusText", ""),
            headers=response_data.get("headers", {}),
            mime_type=response_data.get("mimeType", ""),
            remote_ip=response_data.get("remoteIPAddress"),
            remote_port=response_data.get("remotePort"),
            from_cache=response_data.get("fromDiskCache", False),
            from_service_worker=response_data.get("fromServiceWorker", False),
            timestamp=params.get("timestamp", time.time()),
        )
        self._responses[response.request_id] = response
        for listener in self._response_listeners:
            try:
                listener(response)
            except Exception:
                pass

    def _on_loading_finished(self, params: dict[str, Any]) -> None:
        """Handle Network.loadingFinished event."""
        pass

    def _on_loading_failed(self, params: dict[str, Any]) -> None:
        """Handle Network.loadingFailed event."""
        pass

    def get_requests(self, url_pattern: Optional[str] = None) -> list[NetworkRequest]:
        """Get captured requests, optionally filtered by URL pattern.

        Args:
            url_pattern: Glob pattern to match URLs (e.g., '*api*').

        Returns:
            List of matching NetworkRequest objects.
        """
        requests = list(self._requests.values())
        if url_pattern:
            requests = [r for r in requests if fnmatch.fnmatch(r.url, url_pattern)]
        return requests

    def get_responses(self, url_pattern: Optional[str] = None) -> list[NetworkResponse]:
        """Get captured responses, optionally filtered by URL pattern.

        Args:
            url_pattern: Glob pattern to match URLs.

        Returns:
            List of matching NetworkResponse objects.
        """
        responses = list(self._responses.values())
        if url_pattern:
            responses = [r for r in responses if fnmatch.fnmatch(r.url, url_pattern)]
        return responses

    def get_request(self, request_id: str) -> Optional[NetworkRequest]:
        """Get a specific request by ID.

        Args:
            request_id: The request ID.

        Returns:
            NetworkRequest if found, None otherwise.
        """
        return self._requests.get(request_id)

    def get_response(self, request_id: str) -> Optional[NetworkResponse]:
        """Get a specific response by request ID.

        Args:
            request_id: The request ID.

        Returns:
            NetworkResponse if found, None otherwise.
        """
        return self._responses.get(request_id)

    async def get_response_body(self, request_id: str) -> Optional[bytes]:
        """Get the body of a response.

        Args:
            request_id: The request ID.

        Returns:
            Response body as bytes, or None if not available.
        """
        try:
            result = await self._session.send(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            body = result.get("body", "")
            is_base64 = result.get("base64Encoded", False)
            if is_base64:
                import base64
                return base64.b64decode(body)
            return body.encode("utf-8")
        except Exception:
            return None

    def clear(self) -> None:
        """Clear all captured requests and responses."""
        self._requests.clear()
        self._responses.clear()

    async def wait_for_request(
        self,
        url_pattern: str,
        timeout: float = 30.0,
    ) -> NetworkRequest:
        """Wait for a request matching the URL pattern.

        Args:
            url_pattern: Glob pattern to match URL.
            timeout: Maximum time to wait in seconds.

        Returns:
            Matching NetworkRequest.

        Raises:
            asyncio.TimeoutError: If no matching request within timeout.
        """
        future: asyncio.Future[NetworkRequest] = asyncio.get_event_loop().create_future()

        def on_request(request: NetworkRequest) -> None:
            if fnmatch.fnmatch(request.url, url_pattern) and not future.done():
                future.set_result(request)

        self._request_listeners.append(on_request)
        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            self._request_listeners.remove(on_request)

    async def wait_for_response(
        self,
        url_pattern: str,
        timeout: float = 30.0,
    ) -> NetworkResponse:
        """Wait for a response matching the URL pattern.

        Args:
            url_pattern: Glob pattern to match URL.
            timeout: Maximum time to wait in seconds.

        Returns:
            Matching NetworkResponse.

        Raises:
            asyncio.TimeoutError: If no matching response within timeout.
        """
        future: asyncio.Future[NetworkResponse] = asyncio.get_event_loop().create_future()

        def on_response(response: NetworkResponse) -> None:
            if fnmatch.fnmatch(response.url, url_pattern) and not future.done():
                future.set_result(response)

        self._response_listeners.append(on_response)
        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            self._response_listeners.remove(on_response)
