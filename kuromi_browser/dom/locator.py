"""
Locator system for kuromi-browser.

Provides DrissionPage-style selector shortcuts and parsing utilities.
"""

from typing import Literal, Tuple

SelectorType = Literal["css", "xpath"]


class Locator:
    """Parser for DrissionPage-style selector shortcuts.

    Supports various selector formats:
    - '#id' -> CSS selector for ID
    - '.class' -> CSS selector for class
    - 't:tag' or 'tag:tag' -> CSS selector for tag
    - '@attr=value' -> CSS selector for attribute
    - 'text:content' or 'tx:content' -> XPath for text contains
    - 'x:xpath' or 'xpath:xpath' -> XPath expression
    - Plain selector -> treated as CSS

    Example:
        >>> Locator.parse('#submit')
        ('css', '#submit')
        >>> Locator.parse('@name=email')
        ('css', '[name="email"]')
        >>> Locator.parse('text:Login')
        ('xpath', '//*[contains(text(), "Login")]')
    """

    @staticmethod
    def parse(selector: str) -> Tuple[SelectorType, str]:
        """Parse a selector string into type and selector.

        Args:
            selector: DrissionPage-style selector string.

        Returns:
            Tuple of (selector_type, parsed_selector).
        """
        if not selector:
            raise ValueError("Selector cannot be empty")

        selector = selector.strip()

        # CSS ID selector
        if selector.startswith('#'):
            return 'css', selector

        # CSS class selector
        if selector.startswith('.'):
            return 'css', selector

        # Tag selector shortcuts
        if selector.startswith('t:'):
            return 'css', selector[2:].strip()
        if selector.startswith('tag:'):
            return 'css', selector[4:].strip()

        # Attribute selector: @name=value -> [name="value"]
        if selector.startswith('@'):
            attr_part = selector[1:]
            if '=' in attr_part:
                name, value = attr_part.split('=', 1)
                # Handle quotes in value
                value = value.strip().strip('"').strip("'")
                return 'css', f'[{name.strip()}="{value}"]'
            else:
                # Just attribute exists: @disabled -> [disabled]
                return 'css', f'[{attr_part.strip()}]'

        # Text contains selector
        if selector.startswith('text:'):
            text = selector[5:].strip()
            return 'xpath', f'//*[contains(text(), "{text}")]'
        if selector.startswith('tx:'):
            text = selector[3:].strip()
            return 'xpath', f'//*[contains(text(), "{text}")]'

        # Exact text match
        if selector.startswith('text='):
            text = selector[5:].strip()
            return 'xpath', f'//*[text()="{text}"]'

        # XPath selector
        if selector.startswith('x:'):
            return 'xpath', selector[2:].strip()
        if selector.startswith('xpath:'):
            return 'xpath', selector[6:].strip()

        # Auto-detect XPath if starts with /
        if selector.startswith('/') or selector.startswith('('):
            return 'xpath', selector

        # Default to CSS selector
        return 'css', selector

    @staticmethod
    def is_xpath(selector: str) -> bool:
        """Check if the selector should be treated as XPath.

        Args:
            selector: Selector string.

        Returns:
            True if selector is XPath format.
        """
        selector = selector.strip()
        return (
            selector.startswith('x:') or
            selector.startswith('xpath:') or
            selector.startswith('text:') or
            selector.startswith('tx:') or
            selector.startswith('text=') or
            selector.startswith('/') or
            selector.startswith('(')
        )

    @staticmethod
    def combine(base: str, child: str) -> str:
        """Combine two selectors into a descendant selector.

        Args:
            base: Base selector.
            child: Child selector.

        Returns:
            Combined selector string.
        """
        base_type, base_sel = Locator.parse(base)
        child_type, child_sel = Locator.parse(child)

        if base_type == 'xpath' or child_type == 'xpath':
            # Convert both to XPath for combination
            if base_type == 'css':
                base_sel = Locator.css_to_xpath(base_sel)
            if child_type == 'css':
                child_sel = Locator.css_to_xpath(child_sel)

            # Combine XPath expressions
            if child_sel.startswith('/'):
                return base_sel + child_sel
            else:
                return f"{base_sel}//{child_sel}"
        else:
            # Both are CSS, just combine
            return f"{base_sel} {child_sel}"

    @staticmethod
    def css_to_xpath(css: str) -> str:
        """Convert a simple CSS selector to XPath.

        Note: This is a basic implementation for common cases.

        Args:
            css: CSS selector.

        Returns:
            XPath expression.
        """
        # Handle ID selector
        if css.startswith('#'):
            id_val = css[1:]
            return f'//*[@id="{id_val}"]'

        # Handle class selector
        if css.startswith('.'):
            class_val = css[1:]
            return f'//*[contains(@class, "{class_val}")]'

        # Handle attribute selector [attr="value"]
        if css.startswith('[') and css.endswith(']'):
            attr_content = css[1:-1]
            if '=' in attr_content:
                name, value = attr_content.split('=', 1)
                value = value.strip('"').strip("'")
                return f'//*[@{name}="{value}"]'
            else:
                return f'//*[@{attr_content}]'

        # Handle tag selector
        if css.isalnum() or (css.replace('-', '').replace('_', '').isalnum()):
            return f'//{css}'

        # Complex selectors - return as-is with // prefix
        return f'//{css}'


__all__ = [
    "Locator",
    "SelectorType",
]
