"""
Network Request Filter for kuromi-browser.

Provides flexible filtering system for network requests and responses.
Supports filtering by URL, method, resource type, headers, and custom predicates.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Pattern, Union

from kuromi_browser.models import NetworkRequest, NetworkResponse


class ResourceType(str, Enum):
    """Common resource types in browser network requests."""

    DOCUMENT = "Document"
    STYLESHEET = "Stylesheet"
    IMAGE = "Image"
    MEDIA = "Media"
    FONT = "Font"
    SCRIPT = "Script"
    TEXT_TRACK = "TextTrack"
    XHR = "XHR"
    FETCH = "Fetch"
    PREFETCH = "Prefetch"
    EVENT_SOURCE = "EventSource"
    WEBSOCKET = "WebSocket"
    MANIFEST = "Manifest"
    SIGNED_EXCHANGE = "SignedExchange"
    PING = "Ping"
    CSP_VIOLATION_REPORT = "CSPViolationReport"
    PREFLIGHT = "Preflight"
    OTHER = "Other"


class HttpMethod(str, Enum):
    """HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    CONNECT = "CONNECT"
    TRACE = "TRACE"


@dataclass
class FilterCriteria:
    """Criteria for filtering network requests/responses.

    All criteria are AND-ed together. Use None to skip a criterion.
    """

    # URL matching
    url: Optional[str] = None  # Exact URL match
    url_pattern: Optional[str] = None  # Glob pattern (e.g., "*api*")
    url_regex: Optional[Union[str, Pattern[str]]] = None  # Regex pattern
    url_contains: Optional[str] = None  # URL contains substring
    url_prefix: Optional[str] = None  # URL starts with
    url_suffix: Optional[str] = None  # URL ends with

    # Domain matching
    domain: Optional[str] = None  # Exact domain match
    domain_pattern: Optional[str] = None  # Glob pattern for domain

    # Method matching
    method: Optional[Union[str, HttpMethod]] = None  # Single method
    methods: Optional[list[Union[str, HttpMethod]]] = None  # Multiple methods

    # Resource type matching
    resource_type: Optional[Union[str, ResourceType]] = None  # Single type
    resource_types: Optional[list[Union[str, ResourceType]]] = None  # Multiple types
    exclude_resource_types: Optional[list[Union[str, ResourceType]]] = None

    # Header matching
    has_header: Optional[str] = None  # Request must have header
    header_value: Optional[tuple[str, str]] = None  # (header_name, value)
    header_pattern: Optional[tuple[str, str]] = None  # (header_name, regex_pattern)

    # Status code matching (for responses)
    status: Optional[int] = None  # Exact status
    status_range: Optional[tuple[int, int]] = None  # (min, max) inclusive
    status_codes: Optional[list[int]] = None  # Multiple codes

    # Content type matching (for responses)
    content_type: Optional[str] = None  # Contains content type
    content_types: Optional[list[str]] = None  # Multiple content types

    # Custom predicate
    predicate: Optional[Callable[[Any], bool]] = None

    # Cache-related
    from_cache: Optional[bool] = None
    from_service_worker: Optional[bool] = None

    def __post_init__(self) -> None:
        """Compile regex pattern if provided as string."""
        if isinstance(self.url_regex, str):
            self.url_regex = re.compile(self.url_regex)


class NetworkFilter:
    """Flexible network request/response filter.

    Supports multiple filter criteria with AND/OR logic.

    Example:
        # Create filter for API requests
        filter = NetworkFilter()
        filter.add_criteria(FilterCriteria(
            url_pattern="*api*",
            methods=["GET", "POST"],
            resource_types=[ResourceType.XHR, ResourceType.FETCH],
        ))

        # Check if request matches
        if filter.matches_request(request):
            print("API request detected!")

        # Filter a list of requests
        api_requests = filter.filter_requests(all_requests)
    """

    def __init__(self, match_all: bool = True) -> None:
        """Initialize network filter.

        Args:
            match_all: If True, all criteria must match (AND).
                       If False, any criteria can match (OR).
        """
        self._criteria: list[FilterCriteria] = []
        self._match_all = match_all
        self._url_blacklist: list[str] = []
        self._url_whitelist: list[str] = []

    def add_criteria(self, criteria: FilterCriteria) -> "NetworkFilter":
        """Add filter criteria.

        Args:
            criteria: FilterCriteria to add.

        Returns:
            Self for chaining.
        """
        self._criteria.append(criteria)
        return self

    def add_url_blacklist(self, patterns: list[str]) -> "NetworkFilter":
        """Add URL patterns to blacklist (always excluded).

        Args:
            patterns: Glob patterns to blacklist.

        Returns:
            Self for chaining.
        """
        self._url_blacklist.extend(patterns)
        return self

    def add_url_whitelist(self, patterns: list[str]) -> "NetworkFilter":
        """Add URL patterns to whitelist (only these if set).

        Args:
            patterns: Glob patterns to whitelist.

        Returns:
            Self for chaining.
        """
        self._url_whitelist.extend(patterns)
        return self

    def clear(self) -> None:
        """Clear all criteria."""
        self._criteria.clear()
        self._url_blacklist.clear()
        self._url_whitelist.clear()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""

    def _matches_criteria(
        self,
        criteria: FilterCriteria,
        url: str,
        method: Optional[str] = None,
        resource_type: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        status: Optional[int] = None,
        mime_type: Optional[str] = None,
        from_cache: Optional[bool] = None,
        from_service_worker: Optional[bool] = None,
    ) -> bool:
        """Check if a request/response matches the given criteria."""
        headers = headers or {}

        # URL matching
        if criteria.url and url != criteria.url:
            return False

        if criteria.url_pattern and not fnmatch.fnmatch(url, criteria.url_pattern):
            return False

        if criteria.url_regex:
            pattern = criteria.url_regex
            if isinstance(pattern, str):
                pattern = re.compile(pattern)
            if not pattern.search(url):
                return False

        if criteria.url_contains and criteria.url_contains not in url:
            return False

        if criteria.url_prefix and not url.startswith(criteria.url_prefix):
            return False

        if criteria.url_suffix and not url.endswith(criteria.url_suffix):
            return False

        # Domain matching
        if criteria.domain or criteria.domain_pattern:
            domain = self._extract_domain(url)
            if criteria.domain and domain != criteria.domain:
                return False
            if criteria.domain_pattern and not fnmatch.fnmatch(domain, criteria.domain_pattern):
                return False

        # Method matching
        if method:
            method_upper = method.upper()
            if criteria.method:
                expected = criteria.method.value if isinstance(criteria.method, HttpMethod) else criteria.method
                if method_upper != expected.upper():
                    return False

            if criteria.methods:
                expected_methods = [
                    m.value if isinstance(m, HttpMethod) else m.upper()
                    for m in criteria.methods
                ]
                if method_upper not in expected_methods:
                    return False

        # Resource type matching
        if resource_type:
            if criteria.resource_type:
                expected = (
                    criteria.resource_type.value
                    if isinstance(criteria.resource_type, ResourceType)
                    else criteria.resource_type
                )
                if resource_type != expected:
                    return False

            if criteria.resource_types:
                expected_types = [
                    t.value if isinstance(t, ResourceType) else t
                    for t in criteria.resource_types
                ]
                if resource_type not in expected_types:
                    return False

            if criteria.exclude_resource_types:
                excluded = [
                    t.value if isinstance(t, ResourceType) else t
                    for t in criteria.exclude_resource_types
                ]
                if resource_type in excluded:
                    return False

        # Header matching
        if criteria.has_header and criteria.has_header not in headers:
            return False

        if criteria.header_value:
            header_name, expected_value = criteria.header_value
            if headers.get(header_name) != expected_value:
                return False

        if criteria.header_pattern:
            header_name, pattern = criteria.header_pattern
            header_value = headers.get(header_name, "")
            if not re.search(pattern, header_value):
                return False

        # Status code matching
        if status is not None:
            if criteria.status is not None and status != criteria.status:
                return False

            if criteria.status_range:
                min_status, max_status = criteria.status_range
                if not (min_status <= status <= max_status):
                    return False

            if criteria.status_codes and status not in criteria.status_codes:
                return False

        # Content type matching
        if mime_type:
            if criteria.content_type and criteria.content_type not in mime_type:
                return False

            if criteria.content_types:
                if not any(ct in mime_type for ct in criteria.content_types):
                    return False

        # Cache matching
        if criteria.from_cache is not None and from_cache is not None:
            if criteria.from_cache != from_cache:
                return False

        if criteria.from_service_worker is not None and from_service_worker is not None:
            if criteria.from_service_worker != from_service_worker:
                return False

        return True

    def _check_blackwhitelist(self, url: str) -> bool:
        """Check URL against blacklist and whitelist."""
        # Blacklist takes priority
        for pattern in self._url_blacklist:
            if fnmatch.fnmatch(url, pattern):
                return False

        # If whitelist is set, URL must match at least one pattern
        if self._url_whitelist:
            for pattern in self._url_whitelist:
                if fnmatch.fnmatch(url, pattern):
                    return True
            return False

        return True

    def matches_request(self, request: NetworkRequest) -> bool:
        """Check if a request matches the filter criteria.

        Args:
            request: NetworkRequest to check.

        Returns:
            True if request matches, False otherwise.
        """
        # Check blacklist/whitelist first
        if not self._check_blackwhitelist(request.url):
            return False

        # No criteria means match everything
        if not self._criteria:
            return True

        results = []
        for criteria in self._criteria:
            # Check custom predicate
            if criteria.predicate:
                if not criteria.predicate(request):
                    results.append(False)
                    continue

            matches = self._matches_criteria(
                criteria,
                url=request.url,
                method=request.method,
                resource_type=request.resource_type,
                headers=request.headers,
            )
            results.append(matches)

        if self._match_all:
            return all(results)
        return any(results)

    def matches_response(self, response: NetworkResponse) -> bool:
        """Check if a response matches the filter criteria.

        Args:
            response: NetworkResponse to check.

        Returns:
            True if response matches, False otherwise.
        """
        # Check blacklist/whitelist first
        if not self._check_blackwhitelist(response.url):
            return False

        # No criteria means match everything
        if not self._criteria:
            return True

        results = []
        for criteria in self._criteria:
            # Check custom predicate
            if criteria.predicate:
                if not criteria.predicate(response):
                    results.append(False)
                    continue

            matches = self._matches_criteria(
                criteria,
                url=response.url,
                status=response.status,
                mime_type=response.mime_type,
                headers=response.headers,
                from_cache=response.from_cache,
                from_service_worker=response.from_service_worker,
            )
            results.append(matches)

        if self._match_all:
            return all(results)
        return any(results)

    def filter_requests(
        self,
        requests: list[NetworkRequest],
    ) -> list[NetworkRequest]:
        """Filter a list of requests.

        Args:
            requests: List of NetworkRequest objects.

        Returns:
            Filtered list of matching requests.
        """
        return [r for r in requests if self.matches_request(r)]

    def filter_responses(
        self,
        responses: list[NetworkResponse],
    ) -> list[NetworkResponse]:
        """Filter a list of responses.

        Args:
            responses: List of NetworkResponse objects.

        Returns:
            Filtered list of matching responses.
        """
        return [r for r in responses if self.matches_response(r)]


# Convenience factory functions

def url_filter(pattern: str) -> NetworkFilter:
    """Create a filter for URL pattern.

    Args:
        pattern: Glob pattern to match URLs.

    Returns:
        NetworkFilter configured for URL pattern.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(url_pattern=pattern))
    return f


def method_filter(*methods: Union[str, HttpMethod]) -> NetworkFilter:
    """Create a filter for HTTP methods.

    Args:
        *methods: HTTP methods to match.

    Returns:
        NetworkFilter configured for methods.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(methods=list(methods)))
    return f


def resource_type_filter(*types: Union[str, ResourceType]) -> NetworkFilter:
    """Create a filter for resource types.

    Args:
        *types: Resource types to match.

    Returns:
        NetworkFilter configured for resource types.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(resource_types=list(types)))
    return f


def api_filter(base_url: Optional[str] = None) -> NetworkFilter:
    """Create a filter for API requests (XHR/Fetch).

    Args:
        base_url: Optional base URL pattern for the API.

    Returns:
        NetworkFilter configured for API requests.
    """
    f = NetworkFilter()
    criteria = FilterCriteria(
        resource_types=[ResourceType.XHR, ResourceType.FETCH],
    )
    if base_url:
        criteria.url_pattern = base_url
    f.add_criteria(criteria)
    return f


def document_filter() -> NetworkFilter:
    """Create a filter for document requests.

    Returns:
        NetworkFilter configured for documents.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(resource_type=ResourceType.DOCUMENT))
    return f


def media_filter() -> NetworkFilter:
    """Create a filter for media requests (images, video, audio).

    Returns:
        NetworkFilter configured for media.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(
        resource_types=[ResourceType.IMAGE, ResourceType.MEDIA, ResourceType.FONT],
    ))
    return f


def script_filter() -> NetworkFilter:
    """Create a filter for script requests.

    Returns:
        NetworkFilter configured for scripts.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(
        resource_types=[ResourceType.SCRIPT],
    ))
    return f


def status_filter(
    status: Optional[int] = None,
    status_range: Optional[tuple[int, int]] = None,
) -> NetworkFilter:
    """Create a filter for response status codes.

    Args:
        status: Exact status code to match.
        status_range: (min, max) range of status codes.

    Returns:
        NetworkFilter configured for status codes.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(status=status, status_range=status_range))
    return f


def error_filter() -> NetworkFilter:
    """Create a filter for error responses (4xx and 5xx).

    Returns:
        NetworkFilter configured for error responses.
    """
    f = NetworkFilter(match_all=False)  # OR mode for multiple ranges
    f.add_criteria(FilterCriteria(status_range=(400, 499)))
    f.add_criteria(FilterCriteria(status_range=(500, 599)))
    return f


def success_filter() -> NetworkFilter:
    """Create a filter for successful responses (2xx).

    Returns:
        NetworkFilter configured for success responses.
    """
    f = NetworkFilter()
    f.add_criteria(FilterCriteria(status_range=(200, 299)))
    return f


__all__ = [
    # Enums
    "ResourceType",
    "HttpMethod",
    # Classes
    "FilterCriteria",
    "NetworkFilter",
    # Factory functions
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
