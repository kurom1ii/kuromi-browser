"""
Request Interceptor for kuromi-browser.

Intercepts, modifies, and mocks network requests via CDP Fetch domain.
"""

from __future__ import annotations

import base64
import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union


@dataclass
class InterceptRule:
    """Rule for intercepting requests."""

    url_pattern: str
    action: str  # 'block', 'modify', 'mock'
    modifier: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None
    mock_response: Optional[dict[str, Any]] = None


@dataclass
class MockResponse:
    """Mock response configuration."""

    status: int = 200
    status_text: str = "OK"
    headers: dict[str, str] = field(default_factory=dict)
    body: Union[str, bytes] = ""
    content_type: str = "text/plain"

    def to_cdp_params(self, request_id: str) -> dict[str, Any]:
        """Convert to CDP Fetch.fulfillRequest parameters."""
        headers = dict(self.headers)
        if "Content-Type" not in headers:
            headers["Content-Type"] = self.content_type

        response_headers = [
            {"name": k, "value": v} for k, v in headers.items()
        ]

        body = self.body
        if isinstance(body, str):
            body = body.encode("utf-8")
        body_base64 = base64.b64encode(body).decode("ascii")

        return {
            "requestId": request_id,
            "responseCode": self.status,
            "responsePhrase": self.status_text,
            "responseHeaders": response_headers,
            "body": body_base64,
        }


class RequestInterceptor:
    """Intercepts and modifies network requests.

    Uses CDP Fetch domain to intercept, block, modify, or mock requests.
    """

    def __init__(self, cdp_session: Any) -> None:
        """Initialize request interceptor.

        Args:
            cdp_session: CDP session for communicating with browser.
        """
        self._session = cdp_session
        self._rules: list[InterceptRule] = []
        self._enabled = False
        self._patterns: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        """Check if interceptor is enabled."""
        return self._enabled

    async def start(self, patterns: Optional[list[str]] = None) -> None:
        """Start intercepting network requests.

        Args:
            patterns: URL patterns to intercept. Default is '*' (all).
        """
        if self._enabled:
            return

        if patterns is None:
            patterns = ["*"]

        self._patterns = [{"urlPattern": p} for p in patterns]
        await self._session.send("Fetch.enable", {"patterns": self._patterns})
        self._session.on("Fetch.requestPaused", self._on_request_paused)
        self._enabled = True

    async def stop(self) -> None:
        """Stop intercepting requests."""
        if not self._enabled:
            return
        await self._session.send("Fetch.disable")
        self._enabled = False

    def _match_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches pattern (glob or regex)."""
        if pattern.startswith("^") or pattern.endswith("$"):
            return bool(re.match(pattern, url))
        return fnmatch.fnmatch(url, pattern)

    async def _on_request_paused(self, params: dict[str, Any]) -> None:
        """Handle Fetch.requestPaused event."""
        request_id = params.get("requestId", "")
        request = params.get("request", {})
        url = request.get("url", "")

        for rule in self._rules:
            if self._match_pattern(url, rule.url_pattern):
                if rule.action == "block":
                    await self._session.send(
                        "Fetch.failRequest",
                        {"requestId": request_id, "errorReason": "BlockedByClient"},
                    )
                    return
                elif rule.action == "mock" and rule.mock_response:
                    mock = MockResponse(**rule.mock_response)
                    await self._session.send(
                        "Fetch.fulfillRequest",
                        mock.to_cdp_params(request_id),
                    )
                    return
                elif rule.action == "modify" and rule.modifier:
                    modified = rule.modifier(request)
                    await self._session.send(
                        "Fetch.continueRequest",
                        {
                            "requestId": request_id,
                            "url": modified.get("url", url),
                            "method": modified.get("method", request.get("method")),
                            "headers": [
                                {"name": k, "value": v}
                                for k, v in modified.get("headers", {}).items()
                            ] if "headers" in modified else None,
                            "postData": modified.get("postData"),
                        },
                    )
                    return

        await self._session.send(
            "Fetch.continueRequest",
            {"requestId": request_id},
        )

    def block(self, url_pattern: str) -> None:
        """Block requests matching the URL pattern.

        Args:
            url_pattern: Glob or regex pattern to match URLs.
        """
        self._rules.append(InterceptRule(
            url_pattern=url_pattern,
            action="block",
        ))

    def unblock(self, url_pattern: str) -> None:
        """Remove a block rule.

        Args:
            url_pattern: The pattern to unblock.
        """
        self._rules = [
            r for r in self._rules
            if not (r.url_pattern == url_pattern and r.action == "block")
        ]

    def modify(
        self,
        url_pattern: str,
        modifier: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Modify requests matching the URL pattern.

        Args:
            url_pattern: Glob or regex pattern to match URLs.
            modifier: Function that takes request dict and returns modified dict.
                      Can modify 'url', 'method', 'headers', 'postData'.
        """
        self._rules.append(InterceptRule(
            url_pattern=url_pattern,
            action="modify",
            modifier=modifier,
        ))

    def mock(
        self,
        url_pattern: str,
        response: Union[dict[str, Any], MockResponse],
    ) -> None:
        """Mock responses for requests matching the URL pattern.

        Args:
            url_pattern: Glob or regex pattern to match URLs.
            response: Mock response configuration. Can be a dict with keys:
                      - status: HTTP status code (default 200)
                      - status_text: Status text (default "OK")
                      - headers: Response headers dict
                      - body: Response body (str or bytes)
                      - content_type: Content-Type header value
        """
        if isinstance(response, MockResponse):
            response_dict = {
                "status": response.status,
                "status_text": response.status_text,
                "headers": response.headers,
                "body": response.body,
                "content_type": response.content_type,
            }
        else:
            response_dict = response

        self._rules.append(InterceptRule(
            url_pattern=url_pattern,
            action="mock",
            mock_response=response_dict,
        ))

    def clear_rules(self) -> None:
        """Clear all interception rules."""
        self._rules.clear()

    def remove_rule(self, url_pattern: str, action: Optional[str] = None) -> None:
        """Remove rules matching the pattern.

        Args:
            url_pattern: Pattern to remove.
            action: Optionally filter by action type.
        """
        self._rules = [
            r for r in self._rules
            if r.url_pattern != url_pattern or (action and r.action != action)
        ]
