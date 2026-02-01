"""
HTTP response wrapper for Session mode.

Provides a rich interface for HTTP responses with HTML parsing capabilities.
"""

from typing import TYPE_CHECKING, Any, Optional, Union
import json as json_module

from lxml import html
from lxml.etree import _Element

from kuromi_browser.session.element import SessionElement

if TYPE_CHECKING:
    from curl_cffi.requests import Response as CurlResponse


class Response:
    """HTTP response wrapper with HTML parsing.

    Wraps raw HTTP responses (from curl_cffi) and provides
    convenient methods for accessing response data and parsing HTML.
    """

    def __init__(self, raw_response: "CurlResponse") -> None:
        """Initialize Response wrapper.

        Args:
            raw_response: The raw response from curl_cffi.
        """
        self._response = raw_response
        self._tree: Optional[_Element] = None
        self._json_data: Optional[Any] = None

    @property
    def status_code(self) -> int:
        """Get the HTTP status code."""
        return self._response.status_code

    @property
    def ok(self) -> bool:
        """Check if the response was successful (2xx status)."""
        return 200 <= self.status_code < 300

    @property
    def reason(self) -> str:
        """Get the HTTP status reason phrase."""
        return self._response.reason or ""

    @property
    def url(self) -> str:
        """Get the final URL after redirects."""
        return str(self._response.url)

    @property
    def headers(self) -> dict[str, str]:
        """Get response headers as a dictionary."""
        return dict(self._response.headers)

    @property
    def cookies(self) -> dict[str, str]:
        """Get response cookies as a dictionary."""
        return dict(self._response.cookies)

    @property
    def text(self) -> str:
        """Get the response body as text."""
        return self._response.text

    @property
    def content(self) -> bytes:
        """Get the response body as bytes."""
        return self._response.content

    @property
    def encoding(self) -> Optional[str]:
        """Get the response encoding."""
        return self._response.encoding

    def json(self, **kwargs: Any) -> Any:
        """Parse the response body as JSON.

        Args:
            **kwargs: Arguments passed to json.loads.

        Returns:
            Parsed JSON data.

        Raises:
            json.JSONDecodeError: If the response is not valid JSON.
        """
        if self._json_data is None:
            self._json_data = json_module.loads(self.text, **kwargs)
        return self._json_data

    @property
    def tree(self) -> _Element:
        """Get the parsed HTML tree (lxml HtmlElement).

        Returns:
            The root element of the parsed HTML document.
        """
        if self._tree is None:
            self._tree = html.fromstring(self.text)
        return self._tree

    def ele(self, selector: str) -> Optional[SessionElement]:
        """Find the first element matching the selector.

        Args:
            selector: CSS selector, XPath, or special selector.
                Prefixes: css:/c:, xpath:/x:, text:/t:
                Auto-detects XPath if starts with / or (

        Returns:
            The first matching element or None.
        """
        root = SessionElement(self.tree)
        return root.ele(selector)

    def eles(self, selector: str) -> list[SessionElement]:
        """Find all elements matching the selector.

        Args:
            selector: CSS selector, XPath, or special selector.

        Returns:
            List of matching elements.
        """
        root = SessionElement(self.tree)
        return root.eles(selector)

    def xpath(self, expression: str) -> list[SessionElement]:
        """Execute XPath expression on the document.

        Args:
            expression: XPath expression.

        Returns:
            List of matching elements.
        """
        root = SessionElement(self.tree)
        return root.xpath(expression)

    def css(self, selector: str) -> list[SessionElement]:
        """Execute CSS selector on the document.

        Args:
            selector: CSS selector.

        Returns:
            List of matching elements.
        """
        root = SessionElement(self.tree)
        return root.css(selector)

    @property
    def title(self) -> Optional[str]:
        """Get the page title."""
        title_elem = self.ele("title")
        return title_elem.text if title_elem else None

    @property
    def body(self) -> Optional[SessionElement]:
        """Get the body element."""
        return self.ele("body")

    @property
    def head(self) -> Optional[SessionElement]:
        """Get the head element."""
        return self.ele("head")

    def links(self) -> list[str]:
        """Get all href values from <a> elements.

        Returns:
            List of href values.
        """
        return [
            el.attr("href")
            for el in self.eles("a[href]")
            if el.attr("href")
        ]

    def images(self) -> list[str]:
        """Get all src values from <img> elements.

        Returns:
            List of src values.
        """
        return [
            el.attr("src")
            for el in self.eles("img[src]")
            if el.attr("src")
        ]

    def forms(self) -> list[SessionElement]:
        """Get all form elements.

        Returns:
            List of form elements.
        """
        return self.eles("form")

    def scripts(self) -> list[SessionElement]:
        """Get all script elements.

        Returns:
            List of script elements.
        """
        return self.eles("script")

    def meta(self, name: Optional[str] = None) -> Union[list[SessionElement], Optional[str]]:
        """Get meta elements or a specific meta content.

        Args:
            name: If provided, returns the content of the meta tag with this name.

        Returns:
            List of meta elements, or the content string if name is provided.
        """
        if name is None:
            return self.eles("meta")
        elem = self.ele(f'meta[name="{name}"]')
        return elem.attr("content") if elem else None

    def __repr__(self) -> str:
        """String representation of the response."""
        return f"<Response [{self.status_code}] {self.url}>"

    def __bool__(self) -> bool:
        """Response is truthy if status is OK."""
        return self.ok

    def raise_for_status(self) -> None:
        """Raise an exception if the response status indicates an error.

        Raises:
            HTTPError: If the response status code indicates an error.
        """
        if not self.ok:
            raise HTTPError(
                f"HTTP {self.status_code}: {self.reason}",
                response=self,
            )


class HTTPError(Exception):
    """HTTP error exception."""

    def __init__(self, message: str, response: Response) -> None:
        """Initialize HTTPError.

        Args:
            message: Error message.
            response: The response that caused the error.
        """
        super().__init__(message)
        self.response = response
