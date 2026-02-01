"""
Enhanced locator parser for kuromi-browser.

Provides a powerful yet simple selector syntax inspired by DrissionPage.
Supports CSS, XPath, text-based, attribute-based, and combined selectors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Union


class LocatorType(str, Enum):
    """Type of locator strategy."""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    TEXT_EXACT = "text_exact"
    ID = "id"
    CLASS = "class"
    TAG = "tag"
    ATTR = "attr"
    COMBINED = "combined"


@dataclass
class ParsedLocator:
    """Parsed locator with type and value."""

    type: LocatorType
    value: str
    original: str
    index: Optional[int] = None  # For indexed selectors like "div@i=2"

    def to_css(self) -> Optional[str]:
        """Convert to CSS selector if possible."""
        if self.type == LocatorType.CSS:
            return self.value
        if self.type == LocatorType.ID:
            return f"#{self.value}"
        if self.type == LocatorType.CLASS:
            return f".{self.value}"
        if self.type == LocatorType.TAG:
            return self.value
        if self.type == LocatorType.ATTR:
            return self.value  # Already in [attr="value"] format
        return None

    def to_xpath(self) -> str:
        """Convert to XPath expression."""
        if self.type == LocatorType.XPATH:
            return self.value
        if self.type == LocatorType.CSS:
            return Locator.css_to_xpath(self.value)
        if self.type == LocatorType.ID:
            return f'//*[@id="{self.value}"]'
        if self.type == LocatorType.CLASS:
            return f'//*[contains(@class, "{self.value}")]'
        if self.type == LocatorType.TAG:
            return f"//{self.value}"
        if self.type == LocatorType.TEXT:
            return f'//*[contains(text(), "{self.value}")]'
        if self.type == LocatorType.TEXT_EXACT:
            return f'//*[text()="{self.value}"]'
        if self.type == LocatorType.ATTR:
            # Parse [attr="value"] format
            match = re.match(r'\[([^=]+)(?:="([^"]*)")?\]', self.value)
            if match:
                attr, val = match.groups()
                if val is not None:
                    return f'//*[@{attr}="{val}"]'
                return f"//*[@{attr}]"
            return f"//*{self.value}"
        return f"//{self.value}"


class Locator:
    """Enhanced locator parser with DrissionPage-style syntax.

    Supported selector formats:

    ## Basic Selectors
    - `#id` -> CSS ID selector
    - `.class` -> CSS class selector
    - `tag` -> Tag name (if alphanumeric)
    - `css:selector` or `c:selector` -> Explicit CSS selector

    ## XPath Selectors
    - `/xpath` or `//xpath` -> XPath expression
    - `(xpath)` -> XPath expression
    - `x:xpath` or `xpath:xpath` -> Explicit XPath

    ## Text Selectors
    - `text:content` or `tx:content` -> Contains text
    - `text=content` -> Exact text match
    - `@text()=value` -> XPath text match

    ## Attribute Selectors
    - `@attr=value` -> Attribute equals
    - `@attr` -> Attribute exists
    - `@attr^=value` -> Attribute starts with
    - `@attr$=value` -> Attribute ends with
    - `@attr*=value` -> Attribute contains

    ## Tag Selectors
    - `t:tag` or `tag:tag` -> Tag name
    - `<tag>` -> Tag name

    ## Index Selectors
    - `selector@i=N` -> Nth element (0-based)
    - `selector@index=N` -> Same as above

    ## Combined Selectors
    - `tag#id.class` -> Combined tag, id, class
    - `tag[attr="value"]` -> Tag with attribute

    Examples:
        >>> Locator.parse('#submit')
        ParsedLocator(type=LocatorType.ID, value='submit')
        >>> Locator.parse('@name=email')
        ParsedLocator(type=LocatorType.ATTR, value='[name="email"]')
        >>> Locator.parse('text:Login')
        ParsedLocator(type=LocatorType.TEXT, value='Login')
        >>> Locator.parse('button@i=2')
        ParsedLocator(type=LocatorType.TAG, value='button', index=2)
    """

    # Prefix patterns
    _PREFIX_MAP = {
        "css:": LocatorType.CSS,
        "c:": LocatorType.CSS,
        "xpath:": LocatorType.XPATH,
        "x:": LocatorType.XPATH,
        "text:": LocatorType.TEXT,
        "tx:": LocatorType.TEXT,
        "t:": LocatorType.TAG,
        "tag:": LocatorType.TAG,
        "id:": LocatorType.ID,
        "class:": LocatorType.CLASS,
    }

    @classmethod
    def parse(cls, selector: str) -> Tuple[str, str]:
        """Parse selector and return (type, value) tuple for backward compatibility.

        Args:
            selector: Selector string.

        Returns:
            Tuple of (selector_type, parsed_selector).
        """
        parsed = cls.parse_full(selector)
        css = parsed.to_css()
        if css is not None:
            return "css", css
        return "xpath", parsed.to_xpath()

    @classmethod
    def parse_full(cls, selector: str) -> ParsedLocator:
        """Parse selector into a ParsedLocator object.

        Args:
            selector: Selector string.

        Returns:
            ParsedLocator with type, value, and optional index.

        Raises:
            ValueError: If selector is empty.
        """
        if not selector:
            raise ValueError("Selector cannot be empty")

        original = selector
        selector = selector.strip()

        # Check for index suffix: selector@i=N or selector@index=N
        index = None
        index_match = re.search(r"@(?:i|index)=(\d+)$", selector)
        if index_match:
            index = int(index_match.group(1))
            selector = selector[: index_match.start()]

        # Check for explicit prefixes
        for prefix, loc_type in cls._PREFIX_MAP.items():
            if selector.lower().startswith(prefix):
                value = selector[len(prefix) :].strip()
                return ParsedLocator(
                    type=loc_type, value=value, original=original, index=index
                )

        # Exact text match: text=value
        if selector.startswith("text="):
            return ParsedLocator(
                type=LocatorType.TEXT_EXACT,
                value=selector[5:].strip(),
                original=original,
                index=index,
            )

        # ID selector: #id
        if selector.startswith("#") and not selector.startswith("##"):
            # Check if it's a pure ID (no other selectors)
            if re.match(r"^#[\w-]+$", selector):
                return ParsedLocator(
                    type=LocatorType.ID,
                    value=selector[1:],
                    original=original,
                    index=index,
                )
            # Combined selector like #id.class
            return ParsedLocator(
                type=LocatorType.CSS, value=selector, original=original, index=index
            )

        # Class selector: .class
        if selector.startswith("."):
            if re.match(r"^\.[\w-]+$", selector):
                return ParsedLocator(
                    type=LocatorType.CLASS,
                    value=selector[1:],
                    original=original,
                    index=index,
                )
            return ParsedLocator(
                type=LocatorType.CSS, value=selector, original=original, index=index
            )

        # XPath: starts with / or ( or .//
        if (
            selector.startswith("/")
            or selector.startswith("(")
            or selector.startswith(".//")
        ):
            return ParsedLocator(
                type=LocatorType.XPATH, value=selector, original=original, index=index
            )

        # Tag selector: <tag>
        if selector.startswith("<") and selector.endswith(">"):
            return ParsedLocator(
                type=LocatorType.TAG,
                value=selector[1:-1].strip(),
                original=original,
                index=index,
            )

        # Attribute selector: @attr=value, @attr^=value, etc.
        if selector.startswith("@"):
            return cls._parse_attribute_selector(selector[1:], original, index)

        # Check if it's a simple tag name (alphanumeric with hyphens/underscores)
        if re.match(r"^[a-zA-Z][\w-]*$", selector):
            return ParsedLocator(
                type=LocatorType.TAG, value=selector, original=original, index=index
            )

        # Check for CSS combinator patterns
        if any(c in selector for c in [" ", ">", "+", "~", "[", ":"]):
            return ParsedLocator(
                type=LocatorType.CSS, value=selector, original=original, index=index
            )

        # Default to CSS
        return ParsedLocator(
            type=LocatorType.CSS, value=selector, original=original, index=index
        )

    @classmethod
    def _parse_attribute_selector(
        cls, attr_str: str, original: str, index: Optional[int]
    ) -> ParsedLocator:
        """Parse attribute selector (@attr=value format)."""
        # Special case: @text()=value for XPath text
        if attr_str.startswith("text()"):
            if "=" in attr_str:
                value = attr_str.split("=", 1)[1].strip().strip('"').strip("'")
                return ParsedLocator(
                    type=LocatorType.TEXT_EXACT,
                    value=value,
                    original=original,
                    index=index,
                )
            return ParsedLocator(
                type=LocatorType.XPATH,
                value="//*[text()]",
                original=original,
                index=index,
            )

        # Parse operator and value
        operators = ["^=", "$=", "*=", "~=", "|=", "="]
        for op in operators:
            if op in attr_str:
                attr, value = attr_str.split(op, 1)
                attr = attr.strip()
                value = value.strip().strip('"').strip("'")

                # Convert to CSS attribute selector
                if op == "=":
                    css_value = f'[{attr}="{value}"]'
                else:
                    css_value = f'[{attr}{op}"{value}"]'

                return ParsedLocator(
                    type=LocatorType.ATTR,
                    value=css_value,
                    original=original,
                    index=index,
                )

        # Attribute exists: @disabled
        return ParsedLocator(
            type=LocatorType.ATTR,
            value=f"[{attr_str.strip()}]",
            original=original,
            index=index,
        )

    @staticmethod
    def is_xpath(selector: str) -> bool:
        """Check if selector should be treated as XPath.

        Args:
            selector: Selector string.

        Returns:
            True if selector is XPath format.
        """
        selector = selector.strip()
        return (
            selector.startswith("x:")
            or selector.startswith("xpath:")
            or selector.startswith("text:")
            or selector.startswith("tx:")
            or selector.startswith("text=")
            or selector.startswith("/")
            or selector.startswith("(")
            or selector.startswith(".//")
        )

    @staticmethod
    def css_to_xpath(css: str) -> str:
        """Convert a simple CSS selector to XPath.

        Handles common cases. For complex selectors, consider using
        cssselect library.

        Args:
            css: CSS selector.

        Returns:
            XPath expression.
        """
        css = css.strip()

        # ID selector
        if css.startswith("#"):
            match = re.match(r"#([\w-]+)(.*)", css)
            if match:
                id_val, rest = match.groups()
                if not rest:
                    return f'//*[@id="{id_val}"]'
                # Has additional selectors
                xpath = f'//*[@id="{id_val}"]'
                if rest.startswith("."):
                    classes = re.findall(r"\.([\w-]+)", rest)
                    for cls in classes:
                        xpath = f'{xpath}[contains(@class, "{cls}")]'
                return xpath

        # Class selector
        if css.startswith("."):
            classes = re.findall(r"\.([\w-]+)", css)
            if len(classes) == 1:
                return f'//*[contains(@class, "{classes[0]}")]'
            xpath = "//*"
            for cls in classes:
                xpath += f'[contains(@class, "{cls}")]'
            return xpath

        # Attribute selector [attr="value"]
        if css.startswith("[") and css.endswith("]"):
            attr_content = css[1:-1]
            # Handle different operators
            for op in ["^=", "$=", "*=", "~=", "|=", "="]:
                if op in attr_content:
                    name, value = attr_content.split(op, 1)
                    value = value.strip('"').strip("'")
                    if op == "=":
                        return f'//*[@{name}="{value}"]'
                    elif op == "^=":
                        return f'//*[starts-with(@{name}, "{value}")]'
                    elif op == "$=":
                        return f'//*[substring(@{name}, string-length(@{name}) - string-length("{value}") + 1) = "{value}"]'
                    elif op == "*=":
                        return f'//*[contains(@{name}, "{value}")]'
            return f"//*[@{attr_content}]"

        # Tag selector
        if re.match(r"^[a-zA-Z][\w-]*$", css):
            return f"//{css}"

        # Tag with class: tag.class
        match = re.match(r"^([a-zA-Z][\w-]*)((?:\.[a-zA-Z][\w-]*)+)$", css)
        if match:
            tag, classes_str = match.groups()
            classes = re.findall(r"\.([\w-]+)", classes_str)
            xpath = f"//{tag}"
            for cls in classes:
                xpath += f'[contains(@class, "{cls}")]'
            return xpath

        # Tag with ID: tag#id
        match = re.match(r"^([a-zA-Z][\w-]*)#([\w-]+)$", css)
        if match:
            tag, id_val = match.groups()
            return f'//{tag}[@id="{id_val}"]'

        # Complex selector - return generic XPath
        return f"//*[contains(., '{css}')]"

    @staticmethod
    def combine(base: str, child: str) -> str:
        """Combine two selectors into a descendant selector.

        Args:
            base: Base selector.
            child: Child selector.

        Returns:
            Combined selector string.
        """
        base_parsed = Locator.parse_full(base)
        child_parsed = Locator.parse_full(child)

        base_is_xpath = base_parsed.type in (
            LocatorType.XPATH,
            LocatorType.TEXT,
            LocatorType.TEXT_EXACT,
        )
        child_is_xpath = child_parsed.type in (
            LocatorType.XPATH,
            LocatorType.TEXT,
            LocatorType.TEXT_EXACT,
        )

        if base_is_xpath or child_is_xpath:
            base_xpath = base_parsed.to_xpath()
            child_xpath = child_parsed.to_xpath()

            # Handle relative XPath
            if child_xpath.startswith("/"):
                return base_xpath + child_xpath
            elif child_xpath.startswith("."):
                return f"{base_xpath}/{child_xpath[1:]}"
            else:
                return f"{base_xpath}//{child_xpath}"
        else:
            # Both are CSS
            base_css = base_parsed.to_css() or base_parsed.value
            child_css = child_parsed.to_css() or child_parsed.value
            return f"{base_css} {child_css}"

    @staticmethod
    def escape_text(text: str) -> str:
        """Escape text for use in XPath expressions.

        Args:
            text: Text to escape.

        Returns:
            Escaped text safe for XPath.
        """
        if "'" not in text:
            return f"'{text}'"
        if '"' not in text:
            return f'"{text}"'
        # Contains both quotes - use concat
        parts = text.split("'")
        return "concat('" + "', \"'\", '".join(parts) + "')"


# Export for backward compatibility
SelectorType = str


__all__ = [
    "Locator",
    "LocatorType",
    "ParsedLocator",
    "SelectorType",
]
