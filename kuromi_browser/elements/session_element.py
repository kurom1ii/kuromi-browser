"""
Session element for kuromi-browser.

HTTP-based element that uses lxml for parsing HTML from responses.
Provides a DOM-like interface for elements parsed from HTTP responses.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Iterator, Optional, Union
from urllib.parse import urljoin

from lxml import html
from lxml.etree import _Element, tostring

from kuromi_browser.elements.base import BaseElement
from kuromi_browser.elements.locator import Locator, LocatorType, ParsedLocator

# Try to import cssselect, fall back to XPath if not available
try:
    from lxml.cssselect import CSSSelector
    HAS_CSSSELECT = True
except ImportError:
    HAS_CSSSELECT = False

if TYPE_CHECKING:
    pass


class SessionElement(BaseElement):
    """Element wrapper for lxml elements.

    Provides a consistent interface for interacting with HTML elements
    parsed from HTTP responses, similar to browser DOM elements.

    This is a synchronous implementation suitable for HTTP-based scraping
    where JavaScript execution is not needed.

    Example:
        response = await session.get("https://example.com")
        doc = SessionElement.from_html(response.text)

        # Query elements
        title = doc.ele('title').text
        links = doc.eles('a').links()

        # Navigate DOM
        for item in doc.eles('.item'):
            name = item.ele('.name').text
            price = item.ele('.price').text
    """

    def __init__(
        self,
        element: _Element,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize SessionElement.

        Args:
            element: The lxml element to wrap.
            base_url: Base URL for resolving relative links.
        """
        self._element = element
        self._base_url = base_url

    @classmethod
    def from_html(
        cls,
        html_content: str,
        base_url: Optional[str] = None,
    ) -> "SessionElement":
        """Create a SessionElement from HTML string.

        Args:
            html_content: HTML content to parse.
            base_url: Base URL for resolving relative links.

        Returns:
            SessionElement wrapping the parsed document.
        """
        element = html.fromstring(html_content)
        return cls(element, base_url=base_url)

    @classmethod
    def from_fragment(
        cls,
        html_content: str,
        base_url: Optional[str] = None,
    ) -> list["SessionElement"]:
        """Create SessionElements from HTML fragment.

        Args:
            html_content: HTML fragment to parse.
            base_url: Base URL for resolving relative links.

        Returns:
            List of SessionElements.
        """
        elements = html.fragments_fromstring(html_content)
        return [
            cls(el, base_url=base_url)
            for el in elements
            if isinstance(el, _Element)
        ]

    # Properties

    @property
    def tag(self) -> str:
        """Get the element's tag name."""
        return str(self._element.tag)

    @property
    def text(self) -> str:
        """Get the text content of the element (including children)."""
        return self._element.text_content().strip()

    @property
    def raw_text(self) -> Optional[str]:
        """Get the direct text content (not including children)."""
        return self._element.text

    @property
    def tail(self) -> Optional[str]:
        """Get the tail text after this element."""
        return self._element.tail

    @property
    def html(self) -> str:
        """Get the outer HTML of the element."""
        return tostring(self._element, encoding="unicode", method="html")

    @property
    def inner_html(self) -> str:
        """Get the inner HTML of the element."""
        parts = []
        if self._element.text:
            parts.append(self._element.text)
        for child in self._element:
            parts.append(tostring(child, encoding="unicode", method="html"))
        return "".join(parts)

    @property
    def attrs(self) -> dict[str, str]:
        """Get all attributes as a dictionary."""
        return dict(self._element.attrib)

    # Attribute access

    def attr(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value.

        Args:
            name: Attribute name.
            default: Default value if attribute doesn't exist.

        Returns:
            The attribute value or default.
        """
        return self._element.get(name, default)

    @property
    def id(self) -> Optional[str]:
        """Get the element's id attribute."""
        return self._element.get("id")

    @property
    def classes(self) -> list[str]:
        """Get list of class names."""
        return self._element.get("class", "").split()

    def has_class(self, class_name: str) -> bool:
        """Check if element has a specific class.

        Args:
            class_name: Class name to check.

        Returns:
            True if element has the class.
        """
        return class_name in self.classes

    # Link and src properties

    @property
    def link(self) -> Optional[str]:
        """Get the href attribute, resolved against base URL."""
        href = self._element.get("href")
        if href and self._base_url:
            return urljoin(self._base_url, href)
        return href

    @property
    def src(self) -> Optional[str]:
        """Get the src attribute, resolved against base URL."""
        src = self._element.get("src")
        if src and self._base_url:
            return urljoin(self._base_url, src)
        return src

    # Element queries

    def ele(self, selector: str) -> Optional["SessionElement"]:
        """Find the first element matching the selector.

        Args:
            selector: CSS selector, XPath, or DrissionPage-style selector.
                Prefixes: css:/c:, xpath:/x:, text:/tx:
                Auto-detects XPath if starts with / or (

        Returns:
            The first matching element or None.
        """
        elements = self.eles(selector)
        return elements[0] if elements else None

    def eles(self, selector: str) -> list["SessionElement"]:
        """Find all elements matching the selector.

        Args:
            selector: CSS selector, XPath, or DrissionPage-style selector.

        Returns:
            List of matching elements.
        """
        parsed = Locator.parse_full(selector)

        if parsed.type in (LocatorType.XPATH, LocatorType.TEXT, LocatorType.TEXT_EXACT):
            xpath = parsed.to_xpath()
            # Make relative if needed
            if not xpath.startswith(".") and not xpath.startswith("/"):
                xpath = ".//" + xpath
            elif xpath.startswith("/") and not xpath.startswith("//"):
                xpath = "." + xpath

            results = self._element.xpath(xpath)
            elements = [
                SessionElement(el, base_url=self._base_url)
                for el in results
                if isinstance(el, _Element)
            ]
        else:
            # CSS or other types that can be converted to CSS
            css = parsed.to_css()
            if css:
                if HAS_CSSSELECT:
                    results = self._element.cssselect(css)
                else:
                    # Fall back to XPath conversion
                    xpath = Locator.css_to_xpath(css)
                    if not xpath.startswith("."):
                        xpath = "." + xpath if xpath.startswith("/") else ".//" + xpath
                    results = self._element.xpath(xpath)
                elements = [
                    SessionElement(el, base_url=self._base_url)
                    for el in results
                    if isinstance(el, _Element)
                ]
            else:
                elements = []

        # Handle index
        if parsed.index is not None:
            if 0 <= parsed.index < len(elements):
                return [elements[parsed.index]]
            return []

        return elements

    def xpath(self, expression: str) -> list["SessionElement"]:
        """Execute XPath expression directly.

        Args:
            expression: XPath expression.

        Returns:
            List of matching elements.
        """
        results = self._element.xpath(expression)
        return [
            SessionElement(el, base_url=self._base_url)
            for el in results
            if isinstance(el, _Element)
        ]

    def css(self, selector: str) -> list["SessionElement"]:
        """Execute CSS selector directly.

        Args:
            selector: CSS selector.

        Returns:
            List of matching elements.
        """
        if HAS_CSSSELECT:
            results = self._element.cssselect(selector)
        else:
            # Fall back to XPath conversion
            xpath = Locator.css_to_xpath(selector)
            if not xpath.startswith("."):
                xpath = "." + xpath if xpath.startswith("/") else ".//" + xpath
            results = self._element.xpath(xpath)
        return [
            SessionElement(el, base_url=self._base_url)
            for el in results
            if isinstance(el, _Element)
        ]

    # Navigation

    @property
    def parent(self) -> Optional["SessionElement"]:
        """Get the parent element."""
        parent = self._element.getparent()
        if parent is not None:
            return SessionElement(parent, base_url=self._base_url)
        return None

    @property
    def children(self) -> list["SessionElement"]:
        """Get all direct child elements."""
        return [
            SessionElement(child, base_url=self._base_url)
            for child in self._element
        ]

    @property
    def siblings(self) -> list["SessionElement"]:
        """Get all sibling elements."""
        parent = self._element.getparent()
        if parent is None:
            return []
        return [
            SessionElement(sibling, base_url=self._base_url)
            for sibling in parent
            if sibling is not self._element
        ]

    def next(self, selector: Optional[str] = None) -> Optional["SessionElement"]:
        """Get the next sibling element.

        Args:
            selector: Optional selector to filter siblings.

        Returns:
            Next sibling element or None.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css()

            sibling = self._element.getnext()
            while sibling is not None:
                el = SessionElement(sibling, base_url=self._base_url)
                if css and sibling.cssselect(f"self::{css}"):
                    return el
                elif el._matches_selector(parsed):
                    return el
                sibling = sibling.getnext()
            return None

        sibling = self._element.getnext()
        if sibling is not None:
            return SessionElement(sibling, base_url=self._base_url)
        return None

    def prev(self, selector: Optional[str] = None) -> Optional["SessionElement"]:
        """Get the previous sibling element.

        Args:
            selector: Optional selector to filter siblings.

        Returns:
            Previous sibling element or None.
        """
        if selector:
            parsed = Locator.parse_full(selector)
            css = parsed.to_css()

            sibling = self._element.getprevious()
            while sibling is not None:
                el = SessionElement(sibling, base_url=self._base_url)
                if css and sibling.cssselect(f"self::{css}"):
                    return el
                elif el._matches_selector(parsed):
                    return el
                sibling = sibling.getprevious()
            return None

        sibling = self._element.getprevious()
        if sibling is not None:
            return SessionElement(sibling, base_url=self._base_url)
        return None

    def _matches_selector(self, parsed: ParsedLocator) -> bool:
        """Check if this element matches a parsed selector."""
        if parsed.type == LocatorType.TAG:
            return self.tag.lower() == parsed.value.lower()
        if parsed.type == LocatorType.ID:
            return self.id == parsed.value
        if parsed.type == LocatorType.CLASS:
            return parsed.value in self.classes
        if parsed.type == LocatorType.TEXT:
            return parsed.value.lower() in self.text.lower()
        if parsed.type == LocatorType.TEXT_EXACT:
            return self.text == parsed.value
        # For CSS/ATTR, try cssselect
        css = parsed.to_css()
        if css:
            try:
                return bool(self._element.cssselect(f"self::{css}"))
            except Exception:
                pass
        return False

    def ancestor(self, selector: Optional[str] = None) -> Optional["SessionElement"]:
        """Find an ancestor element.

        Args:
            selector: Optional selector to match ancestor.

        Returns:
            Matching ancestor or immediate parent if no selector.
        """
        if not selector:
            return self.parent

        parsed = Locator.parse_full(selector)
        parent = self._element.getparent()

        while parent is not None:
            el = SessionElement(parent, base_url=self._base_url)
            if el._matches_selector(parsed):
                return el
            parent = parent.getparent()

        return None

    # State checks

    def is_displayed(self) -> bool:
        """Check if element would be displayed (basic check).

        Note: This is a heuristic since we don't have CSS info.

        Returns:
            True if element appears to be displayable.
        """
        # Check for hidden attribute
        if self._element.get("hidden") is not None:
            return False

        # Check for common hiding styles
        style = self._element.get("style", "")
        if "display: none" in style or "display:none" in style:
            return False
        if "visibility: hidden" in style or "visibility:hidden" in style:
            return False

        return True

    # Form data

    @property
    def value(self) -> Optional[str]:
        """Get the value attribute (for form elements)."""
        return self._element.get("value")

    @property
    def name(self) -> Optional[str]:
        """Get the name attribute."""
        return self._element.get("name")

    def form_data(self) -> dict[str, str]:
        """Extract form data from a form element.

        Returns:
            Dictionary of form field names and values.
        """
        data = {}

        # Input elements - use XPath
        for input_el in self._element.xpath(".//input"):
            name = input_el.get("name")
            if not name:
                continue

            input_type = input_el.get("type", "text").lower()

            if input_type in ("checkbox", "radio"):
                if input_el.get("checked") is not None:
                    data[name] = input_el.get("value", "on")
            elif input_type not in ("button", "submit", "reset", "image"):
                data[name] = input_el.get("value", "")

        # Textarea elements - use XPath
        for textarea in self._element.xpath(".//textarea"):
            name = textarea.get("name")
            if name:
                data[name] = textarea.text_content() if hasattr(textarea, 'text_content') else (textarea.text or "")

        # Select elements - use XPath
        for select in self._element.xpath(".//select"):
            name = select.get("name")
            if not name:
                continue

            # Get selected option - use XPath
            selected = select.xpath(".//option[@selected]")
            if selected:
                opt = selected[0]
                data[name] = opt.get("value") or (opt.text_content() if hasattr(opt, 'text_content') else (opt.text or ""))
            else:
                # First option is default
                options = select.xpath(".//option")
                if options:
                    opt = options[0]
                    data[name] = opt.get("value") or (opt.text_content() if hasattr(opt, 'text_content') else (opt.text or ""))

        return data

    # Utilities

    def links(self) -> list[str]:
        """Get all href values from descendant <a> elements.

        Returns:
            List of resolved href values.
        """
        hrefs = []
        for el in self._element.xpath(".//a[@href]"):
            href = el.get("href")
            if href:
                if self._base_url:
                    href = urljoin(self._base_url, href)
                hrefs.append(href)
        return hrefs

    def images(self) -> list[str]:
        """Get all src values from descendant <img> elements.

        Returns:
            List of resolved src values.
        """
        srcs = []
        for el in self._element.xpath(".//img[@src]"):
            src = el.get("src")
            if src:
                if self._base_url:
                    src = urljoin(self._base_url, src)
                srcs.append(src)
        return srcs

    def table_data(self, include_headers: bool = True) -> list[list[str]]:
        """Extract data from a table element.

        Args:
            include_headers: Include header row if present.

        Returns:
            List of rows, each row is a list of cell texts.
        """
        rows = []

        if include_headers:
            for tr in self._element.cssselect("thead tr"):
                row = [th.text_content().strip() for th in tr.cssselect("th")]
                if row:
                    rows.append(row)

        for tr in self._element.cssselect("tbody tr, tr"):
            # Skip if already in thead
            if tr.getparent() is not None and tr.getparent().tag == "thead":
                continue
            row = [td.text_content().strip() for td in tr.cssselect("td, th")]
            if row:
                rows.append(row)

        return rows

    # Iteration

    def __iter__(self) -> Iterator["SessionElement"]:
        """Iterate over child elements."""
        for child in self._element:
            yield SessionElement(child, base_url=self._base_url)

    def __len__(self) -> int:
        """Return number of child elements."""
        return len(self._element)

    def __bool__(self) -> bool:
        """Element is truthy if it exists."""
        return True

    def __repr__(self) -> str:
        """String representation of the element."""
        attrs = " ".join(f'{k}="{v}"' for k, v in list(self.attrs.items())[:3])
        if attrs:
            return f"<SessionElement <{self.tag} {attrs}...>>"
        return f"<SessionElement <{self.tag}>>"


# Backward compatibility alias
HTMLElement = SessionElement


__all__ = [
    "SessionElement",
    "HTMLElement",
]
