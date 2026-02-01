"""
Network Listener for kuromi-browser.

Enhanced network traffic listener with CDP Network domain integration,
real-time streaming support, and advanced filtering capabilities.
"""

from __future__ import annotations

import asyncio
import base64
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional, Union

from kuromi_browser.models import NetworkRequest, NetworkResponse
from kuromi_browser.network.filter import FilterCriteria, NetworkFilter


@dataclass
class NetworkEntry:
    """Complete network entry with request, response, and timing data."""

    request: NetworkRequest
    response: Optional[NetworkResponse] = None
    body: Optional[bytes] = None
    error: Optional[str] = None
    timing: Optional[dict[str, float]] = None
    security_details: Optional[dict[str, Any]] = None

    # Timestamps
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Get request duration in milliseconds."""
        if self.finished_at:
            return (self.finished_at - self.started_at) * 1000
        return None

    @property
    def is_complete(self) -> bool:
        """Check if the entry is complete (has response or error)."""
        return self.response is not None or self.error is not None


@dataclass
class StreamingChunk:
    """Chunk of data received during streaming."""

    request_id: str
    data: bytes
    timestamp: float = field(default_factory=time.time)
    encoded_length: int = 0
    is_final: bool = False


class NetworkListener:
    """Enhanced network traffic listener with CDP Network domain.

    Provides comprehensive network monitoring with:
    - Request/Response capture with timing data
    - Response body retrieval
    - Real-time streaming support
    - Flexible filtering
    - Event-driven architecture

    Example:
        listener = NetworkListener(cdp_session)
        await listener.start()

        # Register callbacks
        listener.on_request(lambda req: print(f"Request: {req.url}"))
        listener.on_response(lambda res: print(f"Response: {res.status}"))

        # Wait for specific request
        request = await listener.wait_for_request("*api/users*")

        # Stream responses in real-time
        async for entry in listener.stream():
            print(f"Entry: {entry.request.url}")

        # Get filtered entries
        entries = listener.get_entries(filter=api_filter())
    """

    def __init__(
        self,
        cdp_session: Any,
        *,
        max_entries: int = 10000,
        capture_body: bool = False,
        capture_timing: bool = True,
    ) -> None:
        """Initialize network listener.

        Args:
            cdp_session: CDP session for browser communication.
            max_entries: Maximum number of entries to keep in memory.
            capture_body: Whether to automatically capture response bodies.
            capture_timing: Whether to capture detailed timing info.
        """
        self._session = cdp_session
        self._max_entries = max_entries
        self._capture_body = capture_body
        self._capture_timing = capture_timing

        # Storage
        self._entries: dict[str, NetworkEntry] = {}
        self._entry_order: deque[str] = deque(maxlen=max_entries)

        # Listeners
        self._request_listeners: list[Callable[[NetworkRequest], Any]] = []
        self._response_listeners: list[Callable[[NetworkResponse], Any]] = []
        self._entry_listeners: list[Callable[[NetworkEntry], Any]] = []
        self._error_listeners: list[Callable[[str, str], Any]] = []
        self._streaming_listeners: list[Callable[[StreamingChunk], Any]] = []

        # State
        self._enabled = False
        self._filter: Optional[NetworkFilter] = None

        # Streaming support
        self._stream_queue: Optional[asyncio.Queue[NetworkEntry]] = None
        self._streaming = False

        # Pending data loaders
        self._data_loading: dict[str, asyncio.Event] = {}

    @property
    def enabled(self) -> bool:
        """Check if listener is enabled."""
        return self._enabled

    def set_filter(self, filter: Optional[NetworkFilter]) -> None:
        """Set filter for captured entries.

        Args:
            filter: NetworkFilter to apply, or None to capture all.
        """
        self._filter = filter

    async def start(
        self,
        *,
        max_post_data_size: int = 65536,
        max_resource_buffer_size: int = 104857600,
        max_total_buffer_size: int = 209715200,
    ) -> None:
        """Start listening for network traffic.

        Args:
            max_post_data_size: Maximum size of POST data to capture.
            max_resource_buffer_size: Max buffer per resource.
            max_total_buffer_size: Max total buffer size.
        """
        if self._enabled:
            return

        # Enable Network domain
        await self._session.send("Network.enable", {
            "maxPostDataSize": max_post_data_size,
            "maxResourceBufferSize": max_resource_buffer_size,
            "maxTotalBufferSize": max_total_buffer_size,
        })

        # Register CDP event handlers
        self._session.on("Network.requestWillBeSent", self._on_request_will_be_sent)
        self._session.on("Network.requestWillBeSentExtraInfo", self._on_request_extra_info)
        self._session.on("Network.responseReceived", self._on_response_received)
        self._session.on("Network.responseReceivedExtraInfo", self._on_response_extra_info)
        self._session.on("Network.loadingFinished", self._on_loading_finished)
        self._session.on("Network.loadingFailed", self._on_loading_failed)
        self._session.on("Network.dataReceived", self._on_data_received)

        self._enabled = True

    async def stop(self) -> None:
        """Stop listening for network traffic."""
        if not self._enabled:
            return

        await self._session.send("Network.disable")
        self._enabled = False
        self._streaming = False

        if self._stream_queue:
            self._stream_queue = None

    def _on_request_will_be_sent(self, params: dict[str, Any]) -> None:
        """Handle Network.requestWillBeSent event."""
        request_id = params.get("requestId", "")
        request_data = params.get("request", {})

        # Build NetworkRequest
        request = NetworkRequest(
            request_id=request_id,
            url=request_data.get("url", ""),
            method=request_data.get("method", "GET"),
            headers=request_data.get("headers", {}),
            post_data=request_data.get("postData"),
            resource_type=params.get("type", "Other"),
            timestamp=params.get("timestamp", time.time()),
        )

        # Apply filter
        if self._filter and not self._filter.matches_request(request):
            return

        # Create entry
        entry = NetworkEntry(
            request=request,
            started_at=params.get("wallTime", time.time()),
        )

        # Store entry
        self._entries[request_id] = entry
        self._entry_order.append(request_id)

        # Cleanup old entries if needed
        while len(self._entry_order) > self._max_entries:
            old_id = self._entry_order.popleft()
            self._entries.pop(old_id, None)

        # Notify listeners
        self._notify_request_listeners(request)

    def _on_request_extra_info(self, params: dict[str, Any]) -> None:
        """Handle Network.requestWillBeSentExtraInfo event."""
        request_id = params.get("requestId", "")
        entry = self._entries.get(request_id)
        if not entry:
            return

        # Update headers with extra info (raw headers)
        headers = params.get("headers", {})
        entry.request.headers.update(headers)

    def _on_response_received(self, params: dict[str, Any]) -> None:
        """Handle Network.responseReceived event."""
        request_id = params.get("requestId", "")
        entry = self._entries.get(request_id)
        if not entry:
            return

        response_data = params.get("response", {})

        # Build NetworkResponse
        response = NetworkResponse(
            request_id=request_id,
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

        # Apply filter for response
        if self._filter and not self._filter.matches_response(response):
            # Remove entry if response doesn't match
            self._entries.pop(request_id, None)
            return

        entry.response = response

        # Capture timing if enabled
        if self._capture_timing:
            timing = response_data.get("timing", {})
            if timing:
                entry.timing = timing

        # Capture security details
        security_details = response_data.get("securityDetails")
        if security_details:
            entry.security_details = security_details

        # Notify listeners
        self._notify_response_listeners(response)

    def _on_response_extra_info(self, params: dict[str, Any]) -> None:
        """Handle Network.responseReceivedExtraInfo event."""
        request_id = params.get("requestId", "")
        entry = self._entries.get(request_id)
        if not entry or not entry.response:
            return

        # Update headers with extra info
        headers = params.get("headers", {})
        entry.response.headers.update(headers)

    def _on_loading_finished(self, params: dict[str, Any]) -> None:
        """Handle Network.loadingFinished event."""
        request_id = params.get("requestId", "")
        entry = self._entries.get(request_id)
        if not entry:
            return

        entry.finished_at = params.get("timestamp", time.time())

        # Signal data loading complete
        if request_id in self._data_loading:
            self._data_loading[request_id].set()

        # Auto-capture body if enabled
        if self._capture_body and entry.response:
            asyncio.create_task(self._capture_response_body(request_id))

        # Notify entry listeners
        self._notify_entry_listeners(entry)

        # Add to stream queue
        if self._streaming and self._stream_queue:
            try:
                self._stream_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _on_loading_failed(self, params: dict[str, Any]) -> None:
        """Handle Network.loadingFailed event."""
        request_id = params.get("requestId", "")
        entry = self._entries.get(request_id)
        if not entry:
            return

        entry.error = params.get("errorText", "Unknown error")
        entry.finished_at = params.get("timestamp", time.time())

        # Signal data loading complete (with error)
        if request_id in self._data_loading:
            self._data_loading[request_id].set()

        # Notify error listeners
        for listener in self._error_listeners:
            try:
                listener(request_id, entry.error)
            except Exception:
                pass

        # Notify entry listeners
        self._notify_entry_listeners(entry)

        # Add to stream queue
        if self._streaming and self._stream_queue:
            try:
                self._stream_queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass

    def _on_data_received(self, params: dict[str, Any]) -> None:
        """Handle Network.dataReceived event (streaming)."""
        request_id = params.get("requestId", "")

        chunk = StreamingChunk(
            request_id=request_id,
            data=b"",  # Actual data not provided in this event
            timestamp=params.get("timestamp", time.time()),
            encoded_length=params.get("encodedDataLength", 0),
        )

        for listener in self._streaming_listeners:
            try:
                listener(chunk)
            except Exception:
                pass

    async def _capture_response_body(self, request_id: str) -> None:
        """Capture response body for an entry."""
        entry = self._entries.get(request_id)
        if not entry:
            return

        try:
            result = await self._session.send(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            body = result.get("body", "")
            is_base64 = result.get("base64Encoded", False)

            if is_base64:
                entry.body = base64.b64decode(body)
            else:
                entry.body = body.encode("utf-8")
        except Exception:
            pass  # Body may not be available

    def _notify_request_listeners(self, request: NetworkRequest) -> None:
        """Notify all request listeners."""
        for listener in self._request_listeners:
            try:
                result = listener(request)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass

    def _notify_response_listeners(self, response: NetworkResponse) -> None:
        """Notify all response listeners."""
        for listener in self._response_listeners:
            try:
                result = listener(response)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass

    def _notify_entry_listeners(self, entry: NetworkEntry) -> None:
        """Notify all entry listeners."""
        for listener in self._entry_listeners:
            try:
                result = listener(entry)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass

    # Public API - Listener registration

    def on_request(self, callback: Callable[[NetworkRequest], Any]) -> None:
        """Register callback for new requests.

        Args:
            callback: Function called when a request is captured.
        """
        self._request_listeners.append(callback)

    def on_response(self, callback: Callable[[NetworkResponse], Any]) -> None:
        """Register callback for responses.

        Args:
            callback: Function called when a response is received.
        """
        self._response_listeners.append(callback)

    def on_entry(self, callback: Callable[[NetworkEntry], Any]) -> None:
        """Register callback for complete entries.

        Args:
            callback: Function called when an entry is complete.
        """
        self._entry_listeners.append(callback)

    def on_error(self, callback: Callable[[str, str], Any]) -> None:
        """Register callback for network errors.

        Args:
            callback: Function called on error with (request_id, error_text).
        """
        self._error_listeners.append(callback)

    def on_streaming_data(self, callback: Callable[[StreamingChunk], Any]) -> None:
        """Register callback for streaming data chunks.

        Args:
            callback: Function called when data is received.
        """
        self._streaming_listeners.append(callback)

    # Public API - Data retrieval

    def get_entries(
        self,
        *,
        filter: Optional[NetworkFilter] = None,
        complete_only: bool = False,
    ) -> list[NetworkEntry]:
        """Get all captured network entries.

        Args:
            filter: Optional filter to apply.
            complete_only: Only return complete entries.

        Returns:
            List of NetworkEntry objects.
        """
        entries = [self._entries[rid] for rid in self._entry_order if rid in self._entries]

        if complete_only:
            entries = [e for e in entries if e.is_complete]

        if filter:
            entries = [
                e for e in entries
                if filter.matches_request(e.request)
                and (e.response is None or filter.matches_response(e.response))
            ]

        return entries

    def get_entry(self, request_id: str) -> Optional[NetworkEntry]:
        """Get a specific entry by request ID.

        Args:
            request_id: The request ID.

        Returns:
            NetworkEntry if found, None otherwise.
        """
        return self._entries.get(request_id)

    def get_requests(
        self,
        *,
        filter: Optional[NetworkFilter] = None,
    ) -> list[NetworkRequest]:
        """Get all captured requests.

        Args:
            filter: Optional filter to apply.

        Returns:
            List of NetworkRequest objects.
        """
        requests = [self._entries[rid].request for rid in self._entry_order if rid in self._entries]
        if filter:
            requests = filter.filter_requests(requests)
        return requests

    def get_responses(
        self,
        *,
        filter: Optional[NetworkFilter] = None,
    ) -> list[NetworkResponse]:
        """Get all captured responses.

        Args:
            filter: Optional filter to apply.

        Returns:
            List of NetworkResponse objects.
        """
        responses = [
            self._entries[rid].response
            for rid in self._entry_order
            if rid in self._entries and self._entries[rid].response
        ]
        if filter:
            responses = filter.filter_responses(responses)
        return responses

    async def get_response_body(self, request_id: str) -> Optional[bytes]:
        """Get the body of a response.

        Args:
            request_id: The request ID.

        Returns:
            Response body as bytes, or None if not available.
        """
        entry = self._entries.get(request_id)
        if entry and entry.body:
            return entry.body

        try:
            result = await self._session.send(
                "Network.getResponseBody",
                {"requestId": request_id},
            )
            body = result.get("body", "")
            is_base64 = result.get("base64Encoded", False)

            if is_base64:
                return base64.b64decode(body)
            return body.encode("utf-8")
        except Exception:
            return None

    # Public API - Waiting

    async def wait_for_request(
        self,
        url_pattern: str,
        *,
        timeout: float = 30.0,
        filter: Optional[NetworkFilter] = None,
    ) -> NetworkRequest:
        """Wait for a request matching the URL pattern.

        Args:
            url_pattern: Glob pattern to match URL.
            timeout: Maximum time to wait in seconds.
            filter: Additional filter criteria.

        Returns:
            Matching NetworkRequest.

        Raises:
            asyncio.TimeoutError: If no matching request within timeout.
        """
        import fnmatch

        future: asyncio.Future[NetworkRequest] = asyncio.get_event_loop().create_future()

        def on_request(request: NetworkRequest) -> None:
            if future.done():
                return
            if not fnmatch.fnmatch(request.url, url_pattern):
                return
            if filter and not filter.matches_request(request):
                return
            future.set_result(request)

        self._request_listeners.append(on_request)
        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            if on_request in self._request_listeners:
                self._request_listeners.remove(on_request)

    async def wait_for_response(
        self,
        url_pattern: str,
        *,
        timeout: float = 30.0,
        filter: Optional[NetworkFilter] = None,
    ) -> NetworkResponse:
        """Wait for a response matching the URL pattern.

        Args:
            url_pattern: Glob pattern to match URL.
            timeout: Maximum time to wait in seconds.
            filter: Additional filter criteria.

        Returns:
            Matching NetworkResponse.

        Raises:
            asyncio.TimeoutError: If no matching response within timeout.
        """
        import fnmatch

        future: asyncio.Future[NetworkResponse] = asyncio.get_event_loop().create_future()

        def on_response(response: NetworkResponse) -> None:
            if future.done():
                return
            if not fnmatch.fnmatch(response.url, url_pattern):
                return
            if filter and not filter.matches_response(response):
                return
            future.set_result(response)

        self._response_listeners.append(on_response)
        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            if on_response in self._response_listeners:
                self._response_listeners.remove(on_response)

    async def wait_for_entry(
        self,
        url_pattern: str,
        *,
        timeout: float = 30.0,
        filter: Optional[NetworkFilter] = None,
    ) -> NetworkEntry:
        """Wait for a complete entry matching the URL pattern.

        Args:
            url_pattern: Glob pattern to match URL.
            timeout: Maximum time to wait in seconds.
            filter: Additional filter criteria.

        Returns:
            Matching NetworkEntry.

        Raises:
            asyncio.TimeoutError: If no matching entry within timeout.
        """
        import fnmatch

        future: asyncio.Future[NetworkEntry] = asyncio.get_event_loop().create_future()

        def on_entry(entry: NetworkEntry) -> None:
            if future.done():
                return
            if not fnmatch.fnmatch(entry.request.url, url_pattern):
                return
            if filter:
                if not filter.matches_request(entry.request):
                    return
                if entry.response and not filter.matches_response(entry.response):
                    return
            future.set_result(entry)

        self._entry_listeners.append(on_entry)
        try:
            return await asyncio.wait_for(future, timeout)
        finally:
            if on_entry in self._entry_listeners:
                self._entry_listeners.remove(on_entry)

    async def wait_for_idle(
        self,
        *,
        timeout: float = 30.0,
        idle_time: float = 0.5,
    ) -> None:
        """Wait for network to become idle.

        Args:
            timeout: Maximum time to wait in seconds.
            idle_time: Time without activity to consider idle.

        Raises:
            asyncio.TimeoutError: If network doesn't become idle.
        """
        last_activity = time.time()

        def update_activity(entry: NetworkEntry) -> None:
            nonlocal last_activity
            last_activity = time.time()

        self._entry_listeners.append(update_activity)
        try:
            start = time.time()
            while time.time() - start < timeout:
                if time.time() - last_activity >= idle_time:
                    return
                await asyncio.sleep(0.1)
            raise asyncio.TimeoutError("Network did not become idle")
        finally:
            if update_activity in self._entry_listeners:
                self._entry_listeners.remove(update_activity)

    # Public API - Streaming

    async def stream(
        self,
        *,
        filter: Optional[NetworkFilter] = None,
    ) -> AsyncIterator[NetworkEntry]:
        """Stream network entries as they complete.

        Args:
            filter: Optional filter to apply.

        Yields:
            NetworkEntry objects as they are captured.

        Example:
            async for entry in listener.stream():
                print(f"Request: {entry.request.url}")
                if entry.response:
                    print(f"Response: {entry.response.status}")
        """
        self._streaming = True
        self._stream_queue = asyncio.Queue(maxsize=1000)

        try:
            while self._streaming:
                try:
                    entry = await asyncio.wait_for(
                        self._stream_queue.get(),
                        timeout=1.0,
                    )

                    if filter:
                        if not filter.matches_request(entry.request):
                            continue
                        if entry.response and not filter.matches_response(entry.response):
                            continue

                    yield entry
                except asyncio.TimeoutError:
                    continue
        finally:
            self._streaming = False
            self._stream_queue = None

    def stop_streaming(self) -> None:
        """Stop the streaming iterator."""
        self._streaming = False

    # Public API - Utilities

    def clear(self) -> None:
        """Clear all captured entries."""
        self._entries.clear()
        self._entry_order.clear()
        self._data_loading.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about captured traffic.

        Returns:
            Dict with traffic statistics.
        """
        entries = list(self._entries.values())
        complete = [e for e in entries if e.is_complete]
        errors = [e for e in entries if e.error]

        durations = [e.duration_ms for e in complete if e.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        status_codes: dict[int, int] = {}
        for entry in complete:
            if entry.response:
                status = entry.response.status
                status_codes[status] = status_codes.get(status, 0) + 1

        resource_types: dict[str, int] = {}
        for entry in entries:
            rt = entry.request.resource_type
            resource_types[rt] = resource_types.get(rt, 0) + 1

        return {
            "total_entries": len(entries),
            "complete_entries": len(complete),
            "pending_entries": len(entries) - len(complete),
            "error_entries": len(errors),
            "average_duration_ms": avg_duration,
            "status_codes": status_codes,
            "resource_types": resource_types,
        }


__all__ = [
    "NetworkListener",
    "NetworkEntry",
    "StreamingChunk",
]
