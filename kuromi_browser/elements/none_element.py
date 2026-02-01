"""
NoneElement pattern for kuromi-browser.

Provides a null object pattern for elements that don't exist,
allowing chained operations without null checks.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional


class NoneElement:
    """Null object pattern for elements.

    Returns None/empty values for all properties and operations
    instead of raising AttributeError. This enables chaining without
    explicit null checks.

    Example:
        # Without NoneElement:
        element = page.ele('#maybe-exists')
        if element:
            text = element.text
        else:
            text = ''

        # With NoneElement:
        element = page.ele('#maybe-exists')  # Returns NoneElement if not found
        text = element.text  # Returns '' instead of raising error

        # Chained access:
        value = page.ele('.container').ele('.item').ele('.value').text
        # Returns '' if any element in chain doesn't exist
    """

    _instance: Optional["NoneElement"] = None

    def __new__(cls) -> "NoneElement":
        """Singleton pattern - only one NoneElement instance needed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # Properties - return empty/None values

    @property
    def tag(self) -> str:
        """Returns empty string."""
        return ""

    @property
    def text(self) -> str:
        """Returns empty string."""
        return ""

    @property
    def html(self) -> str:
        """Returns empty string."""
        return ""

    @property
    def inner_html(self) -> str:
        """Returns empty string."""
        return ""

    @property
    def attrs(self) -> dict[str, str]:
        """Returns empty dict."""
        return {}

    @property
    def parent(self) -> "NoneElement":
        """Returns NoneElement."""
        return self

    @property
    def children(self) -> list:
        """Returns empty list."""
        return []

    @property
    def siblings(self) -> list:
        """Returns empty list."""
        return []

    @property
    def link(self) -> None:
        """Returns None."""
        return None

    @property
    def src(self) -> None:
        """Returns None."""
        return None

    @property
    def id(self) -> None:
        """Returns None."""
        return None

    @property
    def classes(self) -> list[str]:
        """Returns empty list."""
        return []

    @property
    def value(self) -> None:
        """Returns None."""
        return None

    @property
    def name(self) -> None:
        """Returns None."""
        return None

    @property
    def exists(self) -> bool:
        """Returns False - element doesn't exist."""
        return False

    # Attribute access

    def attr(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Returns default value."""
        return default

    def __getitem__(self, name: str) -> None:
        """Returns None for subscript access."""
        return None

    # Element queries - always return NoneElement or empty list

    def ele(self, selector: str) -> "NoneElement":
        """Returns NoneElement."""
        return self

    def eles(self, selector: str) -> list:
        """Returns empty list."""
        return []

    def s(self, selector: str) -> "NoneElement":
        """Alias for ele()."""
        return self

    def ss(self, selector: str) -> list:
        """Alias for eles()."""
        return []

    # Async methods for BrowserElement compatibility

    async def find(self, selector: str) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def find_all(self, selector: str) -> list:
        """Returns empty list."""
        return []

    async def query(self, selector: str) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def query_all(self, selector: str) -> list:
        """Returns empty list."""
        return []

    # Navigation - return NoneElement

    def next(self, selector: Optional[str] = None) -> "NoneElement":
        """Returns NoneElement."""
        return self

    def prev(self, selector: Optional[str] = None) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def get_parent(self, selector: Optional[str] = None) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def get_children(self, selector: Optional[str] = None) -> list:
        """Returns empty list."""
        return []

    async def get_next(self, selector: Optional[str] = None) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def get_prev(self, selector: Optional[str] = None) -> "NoneElement":
        """Returns NoneElement."""
        return self

    # State checks - return False

    def is_displayed(self) -> bool:
        """Returns False."""
        return False

    async def is_visible(self) -> bool:
        """Returns False."""
        return False

    async def is_enabled(self) -> bool:
        """Returns False."""
        return False

    async def is_checked(self) -> bool:
        """Returns False."""
        return False

    async def is_editable(self) -> bool:
        """Returns False."""
        return False

    def has_class(self, class_name: str) -> bool:
        """Returns False."""
        return False

    # Async property getters

    async def tag_name(self) -> str:
        """Returns empty string."""
        return ""

    async def text_content(self) -> str:
        """Returns empty string."""
        return ""

    async def inner_text(self) -> str:
        """Returns empty string."""
        return ""

    async def outer_html(self) -> str:
        """Returns empty string."""
        return ""

    async def get_inner_html(self) -> str:
        """Returns empty string."""
        return ""

    async def get_attrs(self) -> dict[str, str]:
        """Returns empty dict."""
        return {}

    async def get_attr(self, name: str) -> None:
        """Returns None."""
        return None

    async def property(self, name: str) -> None:
        """Returns None."""
        return None

    async def get_link(self) -> None:
        """Returns None."""
        return None

    async def get_src(self) -> None:
        """Returns None."""
        return None

    # Actions - do nothing (no-ops)

    async def click(self, *, force: bool = False, timeout: Optional[float] = None) -> None:
        """No-op."""
        pass

    async def dblclick(self, *, force: bool = False, timeout: Optional[float] = None) -> None:
        """No-op."""
        pass

    async def hover(self, *, force: bool = False, timeout: Optional[float] = None) -> None:
        """No-op."""
        pass

    async def fill(
        self,
        value: str,
        *,
        clear: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        """No-op."""
        pass

    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """No-op."""
        pass

    async def clear(self) -> None:
        """No-op."""
        pass

    async def focus(self) -> None:
        """No-op."""
        pass

    async def blur(self) -> None:
        """No-op."""
        pass

    async def select_option(
        self,
        *values: str,
        by: str = "value",
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Returns empty list."""
        return []

    async def check(self, *, force: bool = False) -> None:
        """No-op."""
        pass

    async def uncheck(self, *, force: bool = False) -> None:
        """No-op."""
        pass

    async def scroll_into_view(self) -> None:
        """No-op."""
        pass

    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        format: str = "png",
        quality: int = 80,
    ) -> bytes:
        """Returns empty bytes."""
        return b""

    async def bounding_box(self) -> None:
        """Returns None."""
        return None

    async def evaluate(self, expression: str, *args: Any) -> None:
        """Returns None."""
        return None

    async def set_attr(self, name: str, value: str) -> None:
        """No-op."""
        pass

    async def remove_attr(self, name: str) -> None:
        """No-op."""
        pass

    # Shadow DOM - return NoneElement

    async def shadow_root(self) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def find_in_shadow(self, selector: str) -> "NoneElement":
        """Returns NoneElement."""
        return self

    async def find_all_in_shadow(self, selector: str) -> list:
        """Returns empty list."""
        return []

    # Utilities

    def links(self) -> list[str]:
        """Returns empty list."""
        return []

    def images(self) -> list[str]:
        """Returns empty list."""
        return []

    def form_data(self) -> dict[str, str]:
        """Returns empty dict."""
        return {}

    def table_data(self, include_headers: bool = True) -> list[list[str]]:
        """Returns empty list."""
        return []

    # XPath/CSS direct access

    def xpath(self, expression: str) -> list:
        """Returns empty list."""
        return []

    def css(self, selector: str) -> list:
        """Returns empty list."""
        return []

    # Boolean conversion

    def __bool__(self) -> bool:
        """NoneElement is always falsy."""
        return False

    # Iteration

    def __iter__(self) -> Iterator:
        """Empty iterator."""
        return iter([])

    def __len__(self) -> int:
        """Returns 0."""
        return 0

    # String representation

    def __repr__(self) -> str:
        """String representation."""
        return "<NoneElement>"

    def __str__(self) -> str:
        """String conversion returns empty string."""
        return ""

    # Comparison

    def __eq__(self, other: Any) -> bool:
        """NoneElement equals None and other NoneElements."""
        return other is None or isinstance(other, NoneElement)

    def __ne__(self, other: Any) -> bool:
        """Not equal."""
        return not self.__eq__(other)


# Singleton instance
NONE_ELEMENT = NoneElement()


def none_element() -> NoneElement:
    """Get the singleton NoneElement instance.

    Returns:
        The NoneElement singleton.
    """
    return NONE_ELEMENT


__all__ = [
    "NoneElement",
    "NONE_ELEMENT",
    "none_element",
]
