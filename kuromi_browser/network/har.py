"""
HAR Recorder for kuromi-browser.

Records network traffic in HTTP Archive (HAR) format.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from kuromi_browser.models import NetworkRequest, NetworkResponse
from kuromi_browser.network.monitor import NetworkMonitor


class HARRecorder:
    """Records network traffic in HAR format.

    The HTTP Archive (HAR) format is a JSON-based archive format for logging
    web browser interaction with a site.
    """

    def __init__(self, monitor: NetworkMonitor) -> None:
        """Initialize HAR recorder.

        Args:
            monitor: NetworkMonitor instance to record from.
        """
        self.monitor = monitor
        self.entries: list[dict[str, Any]] = []
        self._recording = False
        self._start_time: Optional[float] = None
        self._request_times: dict[str, float] = {}

    @property
    def recording(self) -> bool:
        """Check if recording is active."""
        return self._recording

    def start(self) -> None:
        """Start recording network traffic."""
        if self._recording:
            return
        self.entries.clear()
        self._request_times.clear()
        self._start_time = time.time()
        self._recording = True
        self.monitor.on_request(self._on_request)
        self.monitor.on_response(self._on_response)

    def stop(self) -> dict[str, Any]:
        """Stop recording and return HAR data.

        Returns:
            Complete HAR object as a dict.
        """
        self._recording = False
        return self.to_har()

    def _on_request(self, request: NetworkRequest) -> None:
        """Handle captured request."""
        if not self._recording:
            return
        self._request_times[request.request_id] = request.timestamp

    def _on_response(self, response: NetworkResponse) -> None:
        """Handle captured response."""
        if not self._recording:
            return

        request = self.monitor.get_request(response.request_id)
        if not request:
            return

        start_time = self._request_times.get(response.request_id, request.timestamp)
        wait_time = (response.timestamp - start_time) * 1000

        entry = self._create_entry(request, response, wait_time)
        self.entries.append(entry)

    def _create_entry(
        self,
        request: NetworkRequest,
        response: NetworkResponse,
        wait_time: float,
    ) -> dict[str, Any]:
        """Create a HAR entry from request/response pair."""
        started = datetime.fromtimestamp(request.timestamp, tz=timezone.utc)

        return {
            "startedDateTime": started.isoformat(),
            "time": wait_time,
            "request": {
                "method": request.method,
                "url": request.url,
                "httpVersion": "HTTP/1.1",
                "cookies": [],
                "headers": [
                    {"name": k, "value": v} for k, v in request.headers.items()
                ],
                "queryString": self._parse_query_string(request.url),
                "postData": self._format_post_data(request) if request.post_data else None,
                "headersSize": -1,
                "bodySize": len(request.post_data) if request.post_data else 0,
            },
            "response": {
                "status": response.status,
                "statusText": response.status_text,
                "httpVersion": "HTTP/1.1",
                "cookies": [],
                "headers": [
                    {"name": k, "value": v} for k, v in response.headers.items()
                ],
                "content": {
                    "size": -1,
                    "mimeType": response.mime_type,
                },
                "redirectURL": response.headers.get("Location", ""),
                "headersSize": -1,
                "bodySize": -1,
            },
            "cache": {},
            "timings": {
                "send": 0,
                "wait": wait_time,
                "receive": 0,
            },
            "serverIPAddress": response.remote_ip or "",
            "connection": str(response.remote_port) if response.remote_port else "",
        }

    def _parse_query_string(self, url: str) -> list[dict[str, str]]:
        """Parse query string from URL."""
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        return [
            {"name": k, "value": v[0] if v else ""}
            for k, v in query.items()
        ]

    def _format_post_data(self, request: NetworkRequest) -> dict[str, Any]:
        """Format POST data for HAR entry."""
        content_type = request.headers.get("Content-Type", "")
        return {
            "mimeType": content_type,
            "text": request.post_data,
        }

    def to_har(self) -> dict[str, Any]:
        """Convert recorded data to HAR format.

        Returns:
            Complete HAR object.
        """
        return {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "kuromi-browser",
                    "version": "1.0.0",
                },
                "browser": {
                    "name": "Chromium",
                    "version": "",
                },
                "pages": [
                    {
                        "startedDateTime": datetime.now(timezone.utc).isoformat(),
                        "id": "page_1",
                        "title": "",
                        "pageTimings": {
                            "onContentLoad": -1,
                            "onLoad": -1,
                        },
                    }
                ],
                "entries": self.entries,
            }
        }

    def save(self, path: str) -> None:
        """Save HAR data to file.

        Args:
            path: File path to save HAR data.
        """
        har_data = self.to_har()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(har_data, f, indent=2)

    def clear(self) -> None:
        """Clear recorded entries."""
        self.entries.clear()
        self._request_times.clear()
