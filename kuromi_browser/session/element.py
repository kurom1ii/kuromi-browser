"""
Session element wrapper for HTML parsing.

Provides a DOM-like interface for elements parsed from HTTP responses using lxml.
"""

from typing import TYPE_CHECKING, Optional, Union
import re

from lxml import html
from lxml.etree import _Element, tostring

if TYPE_CHECKING:
    from lxml.cssselect import CSSSelector


class SessionElement:
    """Element wrapper for lxml elements.

    Provides a consistent interface for interacting with HTML elements
    parsed from HTTP responses, similar to browser DOM elements.
    """

    def __init__(self, element: _Element) -> None:
        """Initialize SessionElement.

        Args:
            element: The lxml element to wrap.
        """
        self._element = element

    @property
    def tag(self) -> str:
        """Get the element's tag name."""
        return self._element.tag

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

    def attr(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value.

        Args:
            name: Attribute name.
            default: Default value if attribute doesn't exist.

        Returns:
            The attribute value or default.
        """
        return self._element.get(name, default)

    def __getitem__(self, name: str) -> Optional[str]:
        """Get an attribute value using subscript notation."""
        return self._element.get(name)

    @property
    def parent(self) -> Optional["SessionElement"]:
        """Get the parent element."""
        parent = self._element.getparent()
        if parent is not None:
            return SessionElement(parent)
        return None

    @property
    def children(self) -> list["SessionElement"]:
        """Get all child elements."""
        return [SessionElement(child) for child in self._element]

    @property
    def siblings(self) -> list["SessionElement"]:
        """Get all sibling elements."""
        parent = self._element.getparent()
        if parent is None:
            return []
        return [
            SessionElement(sibling)
            for sibling in parent
            if sibling is not self._element
        ]

    def next(self) -> Optional["SessionElement"]:
        """Get the next sibling element."""
        sibling = self._element.getnext()
        if sibling is not None:
            return SessionElement(sibling)
        return None

    def prev(self) -> Optional["SessionElement"]:
        """Get the previous sibling element."""
        sibling = self._element.getprevious()
        if sibling is not None:
            return SessionElement(sibling)
        return None

    def _parse_selector(self, selector: str) -> tuple[str, str]:
        """Parse selector and determine type (css, xpath, text, etc).

        Selector prefixes:
            - css: or c: -> CSS selector
            - xpath: or x: -> XPath expression
            - text: or t: -> Text content search
            - @attr= -> Attribute search
            - # -> ID search
            - . -> Class search
            - No prefix -> Auto-detect (CSS by default)

        Args:
            selector: The selector string.

        Returns:
            Tuple of (selector_type, cleaned_selector).
        """
        selector = selector.strip()

        # Check for explicit prefixes
        if selector.startswith(("css:", "c:")):
            prefix_len = 4 if selector.startswith("css:") else 2
            return ("css", selector[prefix_len:].strip())

        if selector.startswith(("xpath:", "x:")):
            prefix_len = 6 if selector.startswith("xpath:") else 2
            return ("xpath", selector[prefix_len:].strip())

        if selector.startswith(("text:", "t:")):
            prefix_len = 5 if selector.startswith("text:") else 2
            return ("text", selector[prefix_len:].strip())

        # Check for XPath indicators
        if selector.startswith(("/", "(", ".")):
            if selector.startswith("./") or selector.startswith("//") or selector.startswith("("):
                return ("xpath", selector)

        # Attribute search: @attr=value
        if selector.startswith("@") and "=" in selector:
            return ("attr", selector[1:])

        # Default to CSS
        return ("css", selector)

    def ele(self, selector: str) -> Optional["SessionElement"]:
        """Find the first element matching the selector.

        Args:
            selector: CSS selector, XPath, or special selector.
                Prefixes: css:/c:, xpath:/x:, text:/t:
                Auto-detects XPath if starts with / or (

        Returns:
            The first matching element or None.
        """
        elements = self.eles(selector)
        return elements[0] if elements else None

    def eles(self, selector: str) -> list["SessionElement"]:
        """Find all elements matching the selector.

        Args:
            selector: CSS selector, XPath, or special selector.

        Returns:
            List of matching elements.
        """
        selector_type, clean_selector = self._parse_selector(selector)

        if selector_type == "xpath":
            elements = self._element.xpath(clean_selector)
        elif selector_type == "css":
            elements = self._element.cssselect(clean_selector)
        elif selector_type == "text":
            # Search for elements containing text
            xpath = f".//*[contains(text(), '{clean_selector}')]"
            elements = self._element.xpath(xpath)
        elif selector_type == "attr":
            # Parse @attr=value
            if "=" in clean_selector:
                attr_name, attr_value = clean_selector.split("=", 1)
                attr_value = attr_value.strip("\"'")
                xpath = f".//*[@{attr_name}='{attr_value}']"
                elements = self._element.xpath(xpath)
            else:
                elements = []
        else:
            elements = []

        return [SessionElement(el) for el in elements if isinstance(el, _Element)]

    def xpath(self, expression: str) -> list["SessionElement"]:
        """Execute XPath expression.

        Args:
            expression: XPath expression.

        Returns:
            List of matching elements.
        """
        results = self._element.xpath(expression)
        return [SessionElement(el) for el in results if isinstance(el, _Element)]

    def css(self, selector: str) -> list["SessionElement"]:
        """Execute CSS selector.

        Args:
            selector: CSS selector.

        Returns:
            List of matching elements.
        """
        results = self._element.cssselect(selector)
        return [SessionElement(el) for el in results]

    def has_class(self, class_name: str) -> bool:
        """Check if element has a specific class.

        Args:
            class_name: Class name to check.

        Returns:
            True if element has the class.
        """
        classes = self._element.get("class", "").split()
        return class_name in classes

    @property
    def classes(self) -> list[str]:
        """Get list of class names."""
        return self._element.get("class", "").split()

    @property
    def id(self) -> Optional[str]:
        """Get the element's id attribute."""
        return self._element.get("id")

    def links(self) -> list[str]:
        """Get all href values from descendant <a> elements.

        Returns:
            List of href values.
        """
        return [
            el.get("href")
            for el in self._element.xpath(".//a[@href]")
            if el.get("href")
        ]

    def images(self) -> list[str]:
        """Get all src values from descendant <img> elements.

        Returns:
            List of src values.
        """
        return [
            el.get("src")
            for el in self._element.xpath(".//img[@src]")
            if el.get("src")
        ]

    def __repr__(self) -> str:
        """String representation of the element."""
        attrs = " ".join(f'{k}="{v}"' for k, v in list(self.attrs.items())[:3])
        if attrs:
            return f"<SessionElement <{self.tag} {attrs}...>>"
        return f"<SessionElement <{self.tag}>>"

    def __bool__(self) -> bool:
        """Element is truthy if it exists."""
        return True

    def __len__(self) -> int:
        """Return number of child elements."""
        return len(self._element)

    def __iter__(self):
        """Iterate over child elements."""
        for child in self._element:
            yield SessionElement(child)
