"""
HAR Recorder and Exporter for kuromi-browser.

Records and exports network traffic in HTTP Archive (HAR) 1.2 format.
Supports streaming recording, page timings, and content capture.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from kuromi_browser.models import NetworkRequest, NetworkResponse
from kuromi_browser.network.listener import NetworkEntry, NetworkListener
from kuromi_browser.network.monitor import NetworkMonitor


@dataclass
class HARPage:
    """HAR page information."""

    id: str
    title: str = ""
    started_datetime: Optional[datetime] = None
    on_content_load: float = -1  # ms
    on_load: float = -1  # ms

    def to_dict(self) -> dict[str, Any]:
        """Convert to HAR page dict."""
        started = self.started_datetime or datetime.now(timezone.utc)
        return {
            "startedDateTime": started.isoformat(),
            "id": self.id,
            "title": self.title,
            "pageTimings": {
                "onContentLoad": self.on_content_load,
                "onLoad": self.on_load,
            },
        }


@dataclass
class HARTimings:
    """HAR timing information for a request."""

    blocked: float = -1  # Time spent in queue
    dns: float = -1  # DNS resolution time
    connect: float = -1  # Time to create TCP connection
    ssl: float = -1  # Time for SSL/TLS handshake
    send: float = -1  # Time to send request
    wait: float = -1  # Time waiting for response
    receive: float = -1  # Time to receive response

    @classmethod
    def from_cdp_timing(cls, timing: dict[str, Any], total_time: float) -> "HARTimings":
        """Create HARTimings from CDP timing data.

        Args:
            timing: CDP Network.ResourceTiming object.
            total_time: Total request time in ms.

        Returns:
            HARTimings instance.
        """
        # CDP timing values are in milliseconds since request start
        dns_start = timing.get("dnsStart", -1)
        dns_end = timing.get("dnsEnd", -1)
        connect_start = timing.get("connectStart", -1)
        connect_end = timing.get("connectEnd", -1)
        ssl_start = timing.get("sslStart", -1)
        ssl_end = timing.get("sslEnd", -1)
        send_start = timing.get("sendStart", -1)
        send_end = timing.get("sendEnd", -1)
        receive_headers_end = timing.get("receiveHeadersEnd", -1)

        blocked = dns_start if dns_start >= 0 else (connect_start if connect_start >= 0 else 0)
        dns = (dns_end - dns_start) if dns_start >= 0 and dns_end >= 0 else -1
        connect = (connect_end - connect_start) if connect_start >= 0 and connect_end >= 0 else -1
        ssl = (ssl_end - ssl_start) if ssl_start >= 0 and ssl_end >= 0 else -1
        send = (send_end - send_start) if send_start >= 0 and send_end >= 0 else -1
        wait = (receive_headers_end - send_end) if send_end >= 0 and receive_headers_end >= 0 else -1

        # Calculate receive time from total
        accounted = max(0, blocked) + max(0, dns) + max(0, connect) + max(0, ssl) + max(0, send) + max(0, wait)
        receive = max(0, total_time - accounted)

        return cls(
            blocked=blocked,
            dns=dns,
            connect=connect,
            ssl=ssl,
            send=send,
            wait=wait,
            receive=receive,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to HAR timings dict."""
        return {
            "blocked": self.blocked,
            "dns": self.dns,
            "connect": self.connect,
            "ssl": self.ssl,
            "send": self.send,
            "wait": self.wait,
            "receive": self.receive,
        }


@dataclass
class HAREntry:
    """Complete HAR entry with all details."""

    request: NetworkRequest
    response: Optional[NetworkResponse] = None
    started_datetime: Optional[datetime] = None
    time: float = 0  # Total time in ms
    timings: Optional[HARTimings] = None
    server_ip: str = ""
    connection: str = ""
    page_ref: str = ""

    # Content
    request_body_size: int = 0
    response_body_size: int = 0
    response_body: Optional[bytes] = None
    response_body_encoded: bool = False

    # Cookies
    request_cookies: list[dict[str, Any]] = field(default_factory=list)
    response_cookies: list[dict[str, Any]] = field(default_factory=list)

    # Security
    security_state: str = ""
    security_details: Optional[dict[str, Any]] = None

    # Additional
    comment: str = ""

    def to_dict(self, include_body: bool = True) -> dict[str, Any]:
        """Convert to HAR entry dict.

        Args:
            include_body: Whether to include response body.

        Returns:
            HAR entry as dict.
        """
        started = self.started_datetime or datetime.now(timezone.utc)

        # Build request object
        request_dict = {
            "method": self.request.method,
            "url": self.request.url,
            "httpVersion": "HTTP/1.1",
            "cookies": self.request_cookies,
            "headers": self._headers_to_list(self.request.headers),
            "queryString": self._parse_query_string(self.request.url),
            "headersSize": -1,
            "bodySize": self.request_body_size,
        }

        if self.request.post_data:
            content_type = self.request.headers.get("Content-Type", "")
            request_dict["postData"] = {
                "mimeType": content_type,
                "text": self.request.post_data,
            }

            # Parse params for form data
            if "application/x-www-form-urlencoded" in content_type:
                request_dict["postData"]["params"] = self._parse_form_data(
                    self.request.post_data
                )

        # Build response object
        if self.response:
            content_dict: dict[str, Any] = {
                "size": self.response_body_size,
                "mimeType": self.response.mime_type,
                "compression": 0,
            }

            if include_body and self.response_body:
                if self.response_body_encoded:
                    content_dict["text"] = base64.b64encode(self.response_body).decode("ascii")
                    content_dict["encoding"] = "base64"
                else:
                    try:
                        content_dict["text"] = self.response_body.decode("utf-8")
                    except UnicodeDecodeError:
                        content_dict["text"] = base64.b64encode(self.response_body).decode("ascii")
                        content_dict["encoding"] = "base64"

            response_dict = {
                "status": self.response.status,
                "statusText": self.response.status_text,
                "httpVersion": "HTTP/1.1",
                "cookies": self.response_cookies,
                "headers": self._headers_to_list(self.response.headers),
                "content": content_dict,
                "redirectURL": self.response.headers.get("Location", ""),
                "headersSize": -1,
                "bodySize": self.response_body_size,
            }
        else:
            response_dict = {
                "status": 0,
                "statusText": "",
                "httpVersion": "HTTP/1.1",
                "cookies": [],
                "headers": [],
                "content": {"size": 0, "mimeType": ""},
                "redirectURL": "",
                "headersSize": -1,
                "bodySize": -1,
            }

        # Build timings
        timings_dict = self.timings.to_dict() if self.timings else {
            "send": 0,
            "wait": self.time,
            "receive": 0,
        }

        entry = {
            "startedDateTime": started.isoformat(),
            "time": self.time,
            "request": request_dict,
            "response": response_dict,
            "cache": {},
            "timings": timings_dict,
            "serverIPAddress": self.server_ip,
            "connection": self.connection,
        }

        if self.page_ref:
            entry["pageref"] = self.page_ref

        if self.comment:
            entry["comment"] = self.comment

        # Add security info if available
        if self.security_details:
            entry["_securityDetails"] = self.security_details

        return entry

    def _headers_to_list(self, headers: dict[str, str]) -> list[dict[str, str]]:
        """Convert headers dict to HAR format."""
        return [{"name": k, "value": v} for k, v in headers.items()]

    def _parse_query_string(self, url: str) -> list[dict[str, str]]:
        """Parse query string from URL."""
        from urllib.parse import parse_qs, urlparse

        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query, keep_blank_values=True)
            return [
                {"name": k, "value": v[0] if v else ""}
                for k, v in query.items()
            ]
        except Exception:
            return []

    def _parse_form_data(self, data: str) -> list[dict[str, str]]:
        """Parse URL-encoded form data."""
        from urllib.parse import parse_qs

        try:
            parsed = parse_qs(data, keep_blank_values=True)
            return [
                {"name": k, "value": v[0] if v else ""}
                for k, v in parsed.items()
            ]
        except Exception:
            return []


class HARRecorder:
    """Records network traffic in HAR format.

    Enhanced HAR recorder with support for:
    - Multiple pages
    - Detailed timing information
    - Response body capture
    - Cookie parsing
    - Streaming recording
    - Compression

    Example:
        # Using with NetworkListener
        listener = NetworkListener(cdp_session)
        recorder = HARRecorder.from_listener(listener)
        await recorder.start()

        # Navigate and record
        await page.goto("https://example.com")

        # Export
        recorder.save("traffic.har")
        recorder.save("traffic.har.gz", compress=True)
    """

    VERSION = "1.2"
    CREATOR_NAME = "kuromi-browser"
    CREATOR_VERSION = "1.0.0"

    def __init__(
        self,
        monitor: Optional[NetworkMonitor] = None,
        listener: Optional[NetworkListener] = None,
    ) -> None:
        """Initialize HAR recorder.

        Args:
            monitor: NetworkMonitor instance (legacy).
            listener: NetworkListener instance (preferred).
        """
        self._monitor = monitor
        self._listener = listener
        self._entries: list[HAREntry] = []
        self._pages: list[HARPage] = []
        self._current_page: Optional[HARPage] = None
        self._recording = False
        self._start_time: Optional[float] = None
        self._request_times: dict[str, float] = {}
        self._capture_body = False
        self._body_callback: Optional[Callable[[str], bytes]] = None

    @classmethod
    def from_listener(
        cls,
        listener: NetworkListener,
        *,
        capture_body: bool = False,
    ) -> "HARRecorder":
        """Create HAR recorder from NetworkListener.

        Args:
            listener: NetworkListener instance.
            capture_body: Whether to capture response bodies.

        Returns:
            HARRecorder instance.
        """
        recorder = cls(listener=listener)
        recorder._capture_body = capture_body
        return recorder

    @classmethod
    def from_monitor(cls, monitor: NetworkMonitor) -> "HARRecorder":
        """Create HAR recorder from NetworkMonitor (legacy).

        Args:
            monitor: NetworkMonitor instance.

        Returns:
            HARRecorder instance.
        """
        return cls(monitor=monitor)

    @property
    def recording(self) -> bool:
        """Check if recording is active."""
        return self._recording

    def start(self, page_title: str = "") -> None:
        """Start recording network traffic.

        Args:
            page_title: Title for the initial page.
        """
        if self._recording:
            return

        self._entries.clear()
        self._pages.clear()
        self._request_times.clear()
        self._start_time = time.time()
        self._recording = True

        # Create initial page
        self.new_page(page_title)

        # Register with listener or monitor
        if self._listener:
            self._listener.on_entry(self._on_entry)
        elif self._monitor:
            self._monitor.on_request(self._on_request_legacy)
            self._monitor.on_response(self._on_response_legacy)

    def stop(self) -> dict[str, Any]:
        """Stop recording and return HAR data.

        Returns:
            Complete HAR object as dict.
        """
        self._recording = False
        return self.to_har()

    def new_page(
        self,
        title: str = "",
        *,
        on_content_load: float = -1,
        on_load: float = -1,
    ) -> str:
        """Start a new page in the recording.

        Args:
            title: Page title.
            on_content_load: DOMContentLoaded time in ms.
            on_load: Load event time in ms.

        Returns:
            Page ID.
        """
        page_id = f"page_{len(self._pages) + 1}"
        page = HARPage(
            id=page_id,
            title=title,
            started_datetime=datetime.now(timezone.utc),
            on_content_load=on_content_load,
            on_load=on_load,
        )
        self._pages.append(page)
        self._current_page = page
        return page_id

    def update_page_timings(
        self,
        page_id: Optional[str] = None,
        *,
        on_content_load: Optional[float] = None,
        on_load: Optional[float] = None,
    ) -> None:
        """Update page timing information.

        Args:
            page_id: Page ID to update (default: current page).
            on_content_load: DOMContentLoaded time in ms.
            on_load: Load event time in ms.
        """
        page = None
        if page_id:
            page = next((p for p in self._pages if p.id == page_id), None)
        elif self._current_page:
            page = self._current_page

        if page:
            if on_content_load is not None:
                page.on_content_load = on_content_load
            if on_load is not None:
                page.on_load = on_load

    def _on_entry(self, entry: NetworkEntry) -> None:
        """Handle NetworkListener entry."""
        if not self._recording:
            return

        started = datetime.fromtimestamp(entry.started_at, tz=timezone.utc)
        total_time = entry.duration_ms or 0

        # Create HAR timings from CDP timing data
        timings = None
        if entry.timing:
            timings = HARTimings.from_cdp_timing(entry.timing, total_time)

        har_entry = HAREntry(
            request=entry.request,
            response=entry.response,
            started_datetime=started,
            time=total_time,
            timings=timings,
            server_ip=entry.response.remote_ip if entry.response and entry.response.remote_ip else "",
            connection=str(entry.response.remote_port) if entry.response and entry.response.remote_port else "",
            page_ref=self._current_page.id if self._current_page else "",
            request_body_size=len(entry.request.post_data) if entry.request.post_data else 0,
            response_body=entry.body,
            response_body_size=len(entry.body) if entry.body else 0,
            security_details=entry.security_details,
        )

        # Parse cookies
        har_entry.request_cookies = self._parse_cookies(
            entry.request.headers.get("Cookie", "")
        )
        if entry.response:
            har_entry.response_cookies = self._parse_set_cookies(
                entry.response.headers.get("Set-Cookie", "")
            )

        self._entries.append(har_entry)

    def _on_request_legacy(self, request: NetworkRequest) -> None:
        """Handle legacy NetworkMonitor request."""
        if not self._recording:
            return
        self._request_times[request.request_id] = request.timestamp

    def _on_response_legacy(self, response: NetworkResponse) -> None:
        """Handle legacy NetworkMonitor response."""
        if not self._recording or not self._monitor:
            return

        request = self._monitor.get_request(response.request_id)
        if not request:
            return

        start_time = self._request_times.get(response.request_id, request.timestamp)
        total_time = (response.timestamp - start_time) * 1000

        started = datetime.fromtimestamp(start_time, tz=timezone.utc)

        har_entry = HAREntry(
            request=request,
            response=response,
            started_datetime=started,
            time=total_time,
            server_ip=response.remote_ip or "",
            connection=str(response.remote_port) if response.remote_port else "",
            page_ref=self._current_page.id if self._current_page else "",
            request_body_size=len(request.post_data) if request.post_data else 0,
        )

        har_entry.request_cookies = self._parse_cookies(
            request.headers.get("Cookie", "")
        )
        har_entry.response_cookies = self._parse_set_cookies(
            response.headers.get("Set-Cookie", "")
        )

        self._entries.append(har_entry)

    def _parse_cookies(self, cookie_header: str) -> list[dict[str, Any]]:
        """Parse Cookie header into HAR format."""
        if not cookie_header:
            return []

        cookies = []
        for pair in cookie_header.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, value = pair.split("=", 1)
                cookies.append({"name": name.strip(), "value": value.strip()})

        return cookies

    def _parse_set_cookies(self, set_cookie_header: str) -> list[dict[str, Any]]:
        """Parse Set-Cookie header into HAR format."""
        if not set_cookie_header:
            return []

        cookies = []

        # Handle multiple Set-Cookie headers (may be comma-separated)
        for cookie_str in set_cookie_header.split("\n"):
            cookie_str = cookie_str.strip()
            if not cookie_str:
                continue

            parts = cookie_str.split(";")
            if not parts:
                continue

            # First part is name=value
            name_value = parts[0].strip()
            if "=" not in name_value:
                continue

            name, value = name_value.split("=", 1)
            cookie: dict[str, Any] = {
                "name": name.strip(),
                "value": value.strip(),
            }

            # Parse attributes
            for part in parts[1:]:
                part = part.strip().lower()
                if "=" in part:
                    attr_name, attr_value = part.split("=", 1)
                    attr_name = attr_name.strip()
                    attr_value = attr_value.strip()

                    if attr_name == "path":
                        cookie["path"] = attr_value
                    elif attr_name == "domain":
                        cookie["domain"] = attr_value
                    elif attr_name == "expires":
                        cookie["expires"] = attr_value
                    elif attr_name == "max-age":
                        try:
                            cookie["maxAge"] = int(attr_value)
                        except ValueError:
                            pass
                    elif attr_name == "samesite":
                        cookie["sameSite"] = attr_value
                else:
                    if part == "secure":
                        cookie["secure"] = True
                    elif part == "httponly":
                        cookie["httpOnly"] = True

            cookies.append(cookie)

        return cookies

    def add_entry(self, entry: HAREntry) -> None:
        """Manually add an entry to the recording.

        Args:
            entry: HAREntry to add.
        """
        if not entry.page_ref and self._current_page:
            entry.page_ref = self._current_page.id
        self._entries.append(entry)

    def get_entries(self) -> list[HAREntry]:
        """Get all recorded entries.

        Returns:
            List of HAREntry objects.
        """
        return list(self._entries)

    def to_har(
        self,
        *,
        include_body: bool = True,
        browser_name: str = "Chromium",
        browser_version: str = "",
    ) -> dict[str, Any]:
        """Convert recorded data to HAR format.

        Args:
            include_body: Whether to include response bodies.
            browser_name: Browser name for HAR metadata.
            browser_version: Browser version for HAR metadata.

        Returns:
            Complete HAR object as dict.
        """
        # Ensure at least one page exists
        if not self._pages:
            self._pages.append(HARPage(
                id="page_1",
                started_datetime=datetime.now(timezone.utc),
            ))

        return {
            "log": {
                "version": self.VERSION,
                "creator": {
                    "name": self.CREATOR_NAME,
                    "version": self.CREATOR_VERSION,
                },
                "browser": {
                    "name": browser_name,
                    "version": browser_version,
                },
                "pages": [p.to_dict() for p in self._pages],
                "entries": [e.to_dict(include_body=include_body) for e in self._entries],
            }
        }

    def to_json(
        self,
        *,
        indent: int = 2,
        include_body: bool = True,
    ) -> str:
        """Convert to JSON string.

        Args:
            indent: JSON indentation level.
            include_body: Whether to include response bodies.

        Returns:
            HAR as JSON string.
        """
        return json.dumps(self.to_har(include_body=include_body), indent=indent)

    def save(
        self,
        path: Union[str, Path],
        *,
        compress: bool = False,
        include_body: bool = True,
    ) -> None:
        """Save HAR data to file.

        Args:
            path: File path to save HAR data.
            compress: Whether to gzip compress the output.
            include_body: Whether to include response bodies.
        """
        path = Path(path)
        har_data = self.to_json(include_body=include_body)

        if compress or path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as f:
                f.write(har_data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(har_data)

    @classmethod
    def load(cls, path: Union[str, Path]) -> dict[str, Any]:
        """Load HAR data from file.

        Args:
            path: File path to load from.

        Returns:
            HAR data as dict.
        """
        path = Path(path)

        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    def clear(self) -> None:
        """Clear all recorded entries and pages."""
        self._entries.clear()
        self._pages.clear()
        self._request_times.clear()
        self._current_page = None

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about recorded traffic.

        Returns:
            Dict with recording statistics.
        """
        total_request_size = sum(e.request_body_size for e in self._entries)
        total_response_size = sum(e.response_body_size for e in self._entries)
        total_time = sum(e.time for e in self._entries)

        status_codes: dict[int, int] = {}
        for entry in self._entries:
            if entry.response:
                status = entry.response.status
                status_codes[status] = status_codes.get(status, 0) + 1

        methods: dict[str, int] = {}
        for entry in self._entries:
            method = entry.request.method
            methods[method] = methods.get(method, 0) + 1

        return {
            "total_entries": len(self._entries),
            "total_pages": len(self._pages),
            "total_request_size_bytes": total_request_size,
            "total_response_size_bytes": total_response_size,
            "total_time_ms": total_time,
            "status_codes": status_codes,
            "methods": methods,
        }


__all__ = [
    "HARRecorder",
    "HAREntry",
    "HARPage",
    "HARTimings",
]
