"""
DOM parsing and manipulation module for kuromi-browser.

This module provides fast DOM parsing using lxml:
- DOMParser: Parse HTML/XML documents
- DOMElement: Wrapper for parsed elements
- Selector: CSS selector engine
- XPath: XPath query support
"""

from typing import Any, Iterator, Optional, Union

from lxml import etree
from lxml.html import HtmlElement


class DOMElement:
    """Wrapper around lxml element for convenient DOM manipulation.

    Provides a simple interface for querying and extracting data from
    parsed HTML documents.
    """

    def __init__(self, element: HtmlElement) -> None:
        self._element = element

    @property
    def tag(self) -> str:
        """Get the element's tag name."""
        return self._element.tag

    @property
    def text(self) -> Optional[str]:
        """Get the element's text content."""
        return self._element.text

    @property
    def tail(self) -> Optional[str]:
        """Get the element's tail text."""
        return self._element.tail

    @property
    def attrib(self) -> dict[str, str]:
        """Get all attributes as a dictionary."""
        return dict(self._element.attrib)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value."""
        return self._element.get(key, default)

    def text_content(self) -> str:
        """Get all text content including descendants."""
        return "".join(self._element.itertext())

    def css(self, selector: str) -> list["DOMElement"]:
        """Query elements using CSS selector."""
        from lxml.cssselect import CSSSelector

        sel = CSSSelector(selector)
        return [DOMElement(el) for el in sel(self._element)]

    def css_first(self, selector: str) -> Optional["DOMElement"]:
        """Get the first element matching CSS selector."""
        results = self.css(selector)
        return results[0] if results else None

    def xpath(self, path: str) -> list[Union["DOMElement", str, Any]]:
        """Query using XPath expression."""
        results = self._element.xpath(path)
        return [
            DOMElement(el) if isinstance(el, HtmlElement) else el for el in results
        ]

    def xpath_first(self, path: str) -> Optional[Union["DOMElement", str, Any]]:
        """Get the first result from XPath query."""
        results = self.xpath(path)
        return results[0] if results else None

    def children(self) -> list["DOMElement"]:
        """Get all direct children."""
        return [DOMElement(el) for el in self._element]

    def parent(self) -> Optional["DOMElement"]:
        """Get the parent element."""
        parent = self._element.getparent()
        return DOMElement(parent) if parent is not None else None

    def iter(self, *tags: str) -> Iterator["DOMElement"]:
        """Iterate over descendants, optionally filtered by tag."""
        for el in self._element.iter(*tags):
            yield DOMElement(el)

    def to_string(self, encoding: str = "unicode") -> str:
        """Serialize element to HTML string."""
        from lxml.html import tostring

        return tostring(self._element, encoding=encoding)

    def __repr__(self) -> str:
        return f"<DOMElement tag={self.tag!r}>"


class DOMParser:
    """HTML/XML document parser.

    Uses lxml for fast and robust parsing of HTML documents.
    """

    @staticmethod
    def parse_html(html: str) -> DOMElement:
        """Parse an HTML string into a DOM tree."""
        from lxml.html import fromstring

        element = fromstring(html)
        return DOMElement(element)

    @staticmethod
    def parse_html_fragment(html: str) -> list[DOMElement]:
        """Parse an HTML fragment into multiple elements."""
        from lxml.html import fragments_fromstring

        elements = fragments_fromstring(html)
        return [DOMElement(el) for el in elements if isinstance(el, HtmlElement)]

    @staticmethod
    def parse_xml(xml: str) -> DOMElement:
        """Parse an XML string into a DOM tree."""
        element = etree.fromstring(xml.encode())
        return DOMElement(element)


__all__ = [
    "DOMElement",
    "DOMParser",
]
