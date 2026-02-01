"""
Tests for kuromi-browser network module.

Tests the filtering system, HAR recording, and network listener functionality.
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from kuromi_browser.models import NetworkRequest, NetworkResponse
from kuromi_browser.network import (
    NetworkFilter,
    FilterCriteria,
    ResourceType,
    HttpMethod,
    url_filter,
    method_filter,
    resource_type_filter,
    api_filter,
    document_filter,
    status_filter,
    error_filter,
    success_filter,
    HARRecorder,
    HAREntry,
    HARPage,
    HARTimings,
    NetworkEntry,
)


# Test fixtures

@pytest.fixture
def sample_request() -> NetworkRequest:
    """Create a sample network request."""
    return NetworkRequest(
        request_id="req-1",
        url="https://api.example.com/users/123",
        method="GET",
        headers={"Content-Type": "application/json", "Authorization": "Bearer token"},
        resource_type="XHR",
        timestamp=time.time(),
    )


@pytest.fixture
def sample_post_request() -> NetworkRequest:
    """Create a sample POST request."""
    return NetworkRequest(
        request_id="req-2",
        url="https://api.example.com/users",
        method="POST",
        headers={"Content-Type": "application/json"},
        post_data='{"name": "John"}',
        resource_type="Fetch",
        timestamp=time.time(),
    )


@pytest.fixture
def sample_response() -> NetworkResponse:
    """Create a sample network response."""
    return NetworkResponse(
        request_id="req-1",
        url="https://api.example.com/users/123",
        status=200,
        status_text="OK",
        headers={"Content-Type": "application/json"},
        mime_type="application/json",
        timestamp=time.time(),
    )


@pytest.fixture
def error_response() -> NetworkResponse:
    """Create an error response."""
    return NetworkResponse(
        request_id="req-3",
        url="https://api.example.com/error",
        status=500,
        status_text="Internal Server Error",
        headers={},
        mime_type="text/plain",
        timestamp=time.time(),
    )


# FilterCriteria tests

class TestFilterCriteria:
    """Tests for FilterCriteria class."""

    def test_default_criteria(self):
        """Test default criteria matches everything."""
        criteria = FilterCriteria()
        assert criteria.url is None
        assert criteria.method is None

    def test_url_pattern(self):
        """Test URL pattern in criteria."""
        criteria = FilterCriteria(url_pattern="*api*")
        assert criteria.url_pattern == "*api*"

    def test_regex_compilation(self):
        """Test regex pattern is compiled."""
        criteria = FilterCriteria(url_regex=r"^https://.*\.com")
        import re
        assert isinstance(criteria.url_regex, re.Pattern)


# NetworkFilter tests

class TestNetworkFilter:
    """Tests for NetworkFilter class."""

    def test_empty_filter_matches_all(self, sample_request: NetworkRequest):
        """Test empty filter matches all requests."""
        f = NetworkFilter()
        assert f.matches_request(sample_request) is True

    def test_url_pattern_filter(self, sample_request: NetworkRequest):
        """Test URL pattern filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(url_pattern="*api.example.com*"))
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter()
        f2.add_criteria(FilterCriteria(url_pattern="*other.com*"))
        assert f2.matches_request(sample_request) is False

    def test_url_contains_filter(self, sample_request: NetworkRequest):
        """Test URL contains filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(url_contains="users"))
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter()
        f2.add_criteria(FilterCriteria(url_contains="products"))
        assert f2.matches_request(sample_request) is False

    def test_method_filter(
        self,
        sample_request: NetworkRequest,
        sample_post_request: NetworkRequest,
    ):
        """Test HTTP method filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(method=HttpMethod.GET))
        assert f.matches_request(sample_request) is True
        assert f.matches_request(sample_post_request) is False

    def test_methods_filter(
        self,
        sample_request: NetworkRequest,
        sample_post_request: NetworkRequest,
    ):
        """Test multiple HTTP methods filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(methods=[HttpMethod.GET, HttpMethod.POST]))
        assert f.matches_request(sample_request) is True
        assert f.matches_request(sample_post_request) is True

    def test_resource_type_filter(self, sample_request: NetworkRequest):
        """Test resource type filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(resource_type=ResourceType.XHR))
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter()
        f2.add_criteria(FilterCriteria(resource_type=ResourceType.DOCUMENT))
        assert f2.matches_request(sample_request) is False

    def test_resource_types_filter(
        self,
        sample_request: NetworkRequest,
        sample_post_request: NetworkRequest,
    ):
        """Test multiple resource types filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(
            resource_types=[ResourceType.XHR, ResourceType.FETCH]
        ))
        assert f.matches_request(sample_request) is True
        assert f.matches_request(sample_post_request) is True

    def test_header_filter(self, sample_request: NetworkRequest):
        """Test header filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(has_header="Authorization"))
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter()
        f2.add_criteria(FilterCriteria(has_header="X-Custom"))
        assert f2.matches_request(sample_request) is False

    def test_status_filter(
        self,
        sample_response: NetworkResponse,
        error_response: NetworkResponse,
    ):
        """Test status code filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(status=200))
        assert f.matches_response(sample_response) is True
        assert f.matches_response(error_response) is False

    def test_status_range_filter(
        self,
        sample_response: NetworkResponse,
        error_response: NetworkResponse,
    ):
        """Test status code range filtering."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(status_range=(200, 299)))
        assert f.matches_response(sample_response) is True
        assert f.matches_response(error_response) is False

        f2 = NetworkFilter()
        f2.add_criteria(FilterCriteria(status_range=(500, 599)))
        assert f2.matches_response(sample_response) is False
        assert f2.matches_response(error_response) is True

    def test_blacklist(self, sample_request: NetworkRequest):
        """Test URL blacklist."""
        f = NetworkFilter()
        f.add_url_blacklist(["*api.example.com*"])
        assert f.matches_request(sample_request) is False

    def test_whitelist(self, sample_request: NetworkRequest):
        """Test URL whitelist."""
        f = NetworkFilter()
        f.add_url_whitelist(["*api.example.com*"])
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter()
        f2.add_url_whitelist(["*other.com*"])
        assert f2.matches_request(sample_request) is False

    def test_or_mode(self, sample_request: NetworkRequest):
        """Test OR mode filtering."""
        f = NetworkFilter(match_all=False)
        f.add_criteria(FilterCriteria(url_pattern="*nomatch*"))
        f.add_criteria(FilterCriteria(url_pattern="*api*"))
        assert f.matches_request(sample_request) is True

    def test_and_mode(self, sample_request: NetworkRequest):
        """Test AND mode filtering."""
        f = NetworkFilter(match_all=True)
        f.add_criteria(FilterCriteria(url_pattern="*api*"))
        f.add_criteria(FilterCriteria(method=HttpMethod.GET))
        assert f.matches_request(sample_request) is True

        f2 = NetworkFilter(match_all=True)
        f2.add_criteria(FilterCriteria(url_pattern="*api*"))
        f2.add_criteria(FilterCriteria(method=HttpMethod.POST))
        assert f2.matches_request(sample_request) is False

    def test_filter_requests_list(
        self,
        sample_request: NetworkRequest,
        sample_post_request: NetworkRequest,
    ):
        """Test filtering a list of requests."""
        f = NetworkFilter()
        f.add_criteria(FilterCriteria(method=HttpMethod.GET))

        requests = [sample_request, sample_post_request]
        filtered = f.filter_requests(requests)

        assert len(filtered) == 1
        assert filtered[0].method == "GET"


# Factory function tests

class TestFilterFactoryFunctions:
    """Tests for filter factory functions."""

    def test_url_filter(self, sample_request: NetworkRequest):
        """Test url_filter factory."""
        f = url_filter("*api*")
        assert f.matches_request(sample_request) is True

    def test_method_filter(self, sample_request: NetworkRequest):
        """Test method_filter factory."""
        f = method_filter(HttpMethod.GET)
        assert f.matches_request(sample_request) is True

    def test_resource_type_filter(self, sample_request: NetworkRequest):
        """Test resource_type_filter factory."""
        f = resource_type_filter(ResourceType.XHR, ResourceType.FETCH)
        assert f.matches_request(sample_request) is True

    def test_api_filter(self, sample_request: NetworkRequest):
        """Test api_filter factory."""
        f = api_filter()
        assert f.matches_request(sample_request) is True

    def test_document_filter(self, sample_request: NetworkRequest):
        """Test document_filter factory."""
        f = document_filter()
        assert f.matches_request(sample_request) is False

    def test_status_filter(self, sample_response: NetworkResponse):
        """Test status_filter factory."""
        f = status_filter(status=200)
        assert f.matches_response(sample_response) is True

    def test_error_filter(
        self,
        sample_response: NetworkResponse,
        error_response: NetworkResponse,
    ):
        """Test error_filter factory."""
        f = error_filter()
        assert f.matches_response(sample_response) is False
        assert f.matches_response(error_response) is True

    def test_success_filter(
        self,
        sample_response: NetworkResponse,
        error_response: NetworkResponse,
    ):
        """Test success_filter factory."""
        f = success_filter()
        assert f.matches_response(sample_response) is True
        assert f.matches_response(error_response) is False


# HARTimings tests

class TestHARTimings:
    """Tests for HARTimings class."""

    def test_default_timings(self):
        """Test default timing values."""
        timings = HARTimings()
        assert timings.blocked == -1
        assert timings.dns == -1

    def test_to_dict(self):
        """Test conversion to dict."""
        timings = HARTimings(blocked=10, dns=5, connect=20)
        d = timings.to_dict()
        assert d["blocked"] == 10
        assert d["dns"] == 5
        assert d["connect"] == 20

    def test_from_cdp_timing(self):
        """Test creation from CDP timing data."""
        cdp_timing = {
            "dnsStart": 0,
            "dnsEnd": 5,
            "connectStart": 5,
            "connectEnd": 25,
            "sendStart": 25,
            "sendEnd": 30,
            "receiveHeadersEnd": 50,
        }
        timings = HARTimings.from_cdp_timing(cdp_timing, total_time=100)
        assert timings.dns == 5
        assert timings.connect == 20
        assert timings.send == 5
        assert timings.wait == 20


# HARPage tests

class TestHARPage:
    """Tests for HARPage class."""

    def test_page_creation(self):
        """Test page creation."""
        page = HARPage(id="page_1", title="Test Page")
        assert page.id == "page_1"
        assert page.title == "Test Page"

    def test_to_dict(self):
        """Test conversion to dict."""
        page = HARPage(
            id="page_1",
            title="Test",
            on_content_load=100,
            on_load=200,
        )
        d = page.to_dict()
        assert d["id"] == "page_1"
        assert d["title"] == "Test"
        assert d["pageTimings"]["onContentLoad"] == 100
        assert d["pageTimings"]["onLoad"] == 200


# HAREntry tests

class TestHAREntry:
    """Tests for HAREntry class."""

    def test_entry_creation(self, sample_request: NetworkRequest):
        """Test entry creation."""
        entry = HAREntry(request=sample_request)
        assert entry.request == sample_request
        assert entry.response is None

    def test_entry_with_response(
        self,
        sample_request: NetworkRequest,
        sample_response: NetworkResponse,
    ):
        """Test entry with response."""
        entry = HAREntry(
            request=sample_request,
            response=sample_response,
            time=100,
        )
        assert entry.response.status == 200
        assert entry.time == 100

    def test_to_dict(
        self,
        sample_request: NetworkRequest,
        sample_response: NetworkResponse,
    ):
        """Test conversion to dict."""
        entry = HAREntry(
            request=sample_request,
            response=sample_response,
            started_datetime=datetime.now(timezone.utc),
            time=100,
        )
        d = entry.to_dict()

        assert d["request"]["method"] == "GET"
        assert d["request"]["url"] == sample_request.url
        assert d["response"]["status"] == 200
        assert d["time"] == 100

    def test_to_dict_without_body(
        self,
        sample_request: NetworkRequest,
        sample_response: NetworkResponse,
    ):
        """Test conversion to dict without body."""
        entry = HAREntry(
            request=sample_request,
            response=sample_response,
            response_body=b'{"data": "test"}',
        )
        d = entry.to_dict(include_body=False)
        assert "text" not in d["response"]["content"]


# HARRecorder tests

class TestHARRecorder:
    """Tests for HARRecorder class."""

    def test_recorder_creation(self):
        """Test recorder creation."""
        recorder = HARRecorder()
        assert recorder.recording is False

    def test_start_stop(self):
        """Test start and stop recording."""
        recorder = HARRecorder()
        recorder.start("Test Page")
        assert recorder.recording is True

        har = recorder.stop()
        assert recorder.recording is False
        assert "log" in har

    def test_new_page(self):
        """Test creating new pages."""
        recorder = HARRecorder()
        recorder.start()

        page_id = recorder.new_page("Second Page")
        assert page_id == "page_2"

    def test_to_har_format(self):
        """Test HAR format output."""
        recorder = HARRecorder()
        recorder.start("Test")

        har = recorder.to_har()
        assert har["log"]["version"] == "1.2"
        assert har["log"]["creator"]["name"] == "kuromi-browser"
        assert len(har["log"]["pages"]) > 0

    def test_get_stats(self, sample_request: NetworkRequest):
        """Test statistics."""
        recorder = HARRecorder()
        recorder.start()

        entry = HAREntry(request=sample_request, time=100)
        recorder.add_entry(entry)

        stats = recorder.get_stats()
        assert stats["total_entries"] == 1

    def test_clear(self, sample_request: NetworkRequest):
        """Test clearing recorder."""
        recorder = HARRecorder()
        recorder.start()

        entry = HAREntry(request=sample_request)
        recorder.add_entry(entry)
        assert len(recorder.get_entries()) == 1

        recorder.clear()
        assert len(recorder.get_entries()) == 0


# NetworkEntry tests

class TestNetworkEntry:
    """Tests for NetworkEntry class."""

    def test_entry_creation(self, sample_request: NetworkRequest):
        """Test entry creation."""
        entry = NetworkEntry(request=sample_request)
        assert entry.request == sample_request
        assert entry.is_complete is False

    def test_entry_with_response(
        self,
        sample_request: NetworkRequest,
        sample_response: NetworkResponse,
    ):
        """Test entry with response."""
        entry = NetworkEntry(
            request=sample_request,
            response=sample_response,
        )
        assert entry.is_complete is True

    def test_entry_with_error(self, sample_request: NetworkRequest):
        """Test entry with error."""
        entry = NetworkEntry(
            request=sample_request,
            error="Connection refused",
        )
        assert entry.is_complete is True

    def test_duration(self, sample_request: NetworkRequest):
        """Test duration calculation."""
        now = time.time()
        entry = NetworkEntry(
            request=sample_request,
            started_at=now,
            finished_at=now + 0.1,  # 100ms
        )
        assert entry.duration_ms is not None
        assert 90 < entry.duration_ms < 110


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
