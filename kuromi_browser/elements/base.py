"""
Base element interface for kuromi-browser.

Defines the common interface that all element types must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.elements.locator import ParsedLocator


class BaseElement(ABC):
    """Abstract base class for DOM elements.

    Provides a consistent interface for interacting with elements
    regardless of the underlying implementation (CDP, HTTP parsing, etc.).

    This class defines the contract that both BrowserElement (CDP-based)
    and SessionElement (lxml-based) must follow.
    """

    # Properties

    @property
    @abstractmethod
    def tag(self) -> str:
        """Get the element's tag name in lowercase."""
        ...

    @property
    @abstractmethod
    def text(self) -> str:
        """Get the element's text content."""
        ...

    @property
    @abstractmethod
    def html(self) -> str:
        """Get the element's outer HTML."""
        ...

    @property
    @abstractmethod
    def inner_html(self) -> str:
        """Get the element's inner HTML."""
        ...

    @property
    @abstractmethod
    def attrs(self) -> dict[str, str]:
        """Get all attributes as a dictionary."""
        ...

    # Attribute access

    @abstractmethod
    def attr(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value.

        Args:
            name: Attribute name.
            default: Default value if attribute doesn't exist.

        Returns:
            Attribute value or default.
        """
        ...

    def __getitem__(self, name: str) -> Optional[str]:
        """Get an attribute value using subscript notation.

        Args:
            name: Attribute name.

        Returns:
            Attribute value or None.
        """
        return self.attr(name)

    # Element queries

    @abstractmethod
    def ele(self, selector: str) -> Optional["BaseElement"]:
        """Find the first child element matching the selector.

        Args:
            selector: Selector string (CSS, XPath, or DrissionPage-style).

        Returns:
            First matching element or None.
        """
        ...

    @abstractmethod
    def eles(self, selector: str) -> list["BaseElement"]:
        """Find all child elements matching the selector.

        Args:
            selector: Selector string.

        Returns:
            List of matching elements.
        """
        ...

    def s(self, selector: str) -> Optional["BaseElement"]:
        """Alias for ele() - find first matching element.

        Args:
            selector: Selector string.

        Returns:
            First matching element or None.
        """
        return self.ele(selector)

    def ss(self, selector: str) -> list["BaseElement"]:
        """Alias for eles() - find all matching elements.

        Args:
            selector: Selector string.

        Returns:
            List of matching elements.
        """
        return self.eles(selector)

    # Navigation

    @property
    @abstractmethod
    def parent(self) -> Optional["BaseElement"]:
        """Get the parent element."""
        ...

    @property
    @abstractmethod
    def children(self) -> list["BaseElement"]:
        """Get all direct child elements."""
        ...

    @abstractmethod
    def next(self, selector: Optional[str] = None) -> Optional["BaseElement"]:
        """Get the next sibling element.

        Args:
            selector: Optional selector to filter siblings.

        Returns:
            Next sibling element or None.
        """
        ...

    @abstractmethod
    def prev(self, selector: Optional[str] = None) -> Optional["BaseElement"]:
        """Get the previous sibling element.

        Args:
            selector: Optional selector to filter siblings.

        Returns:
            Previous sibling element or None.
        """
        ...

    # State checks

    @property
    def exists(self) -> bool:
        """Check if element exists (always True for real elements)."""
        return True

    @abstractmethod
    def is_displayed(self) -> bool:
        """Check if the element is displayed/visible.

        Returns:
            True if element is visible.
        """
        ...

    # Utilities

    @property
    @abstractmethod
    def link(self) -> Optional[str]:
        """Get the href attribute if element is a link."""
        ...

    @property
    @abstractmethod
    def src(self) -> Optional[str]:
        """Get the src attribute if element has one."""
        ...

    def links(self) -> list[str]:
        """Get all href values from descendant <a> elements.

        Returns:
            List of href values.
        """
        return [
            el.link for el in self.eles("a") if el.link
        ]

    def images(self) -> list[str]:
        """Get all src values from descendant <img> elements.

        Returns:
            List of src values.
        """
        return [
            el.src for el in self.eles("img") if el.src
        ]

    # Boolean conversion

    def __bool__(self) -> bool:
        """Element is truthy if it exists."""
        return self.exists

    # Iteration

    def __iter__(self):
        """Iterate over child elements."""
        return iter(self.children)

    def __len__(self) -> int:
        """Return number of child elements."""
        return len(self.children)

    # String representation

    def __repr__(self) -> str:
        """String representation of the element."""
        attrs_preview = " ".join(
            f'{k}="{v}"' for k, v in list(self.attrs.items())[:3]
        )
        if attrs_preview:
            return f"<{self.__class__.__name__} <{self.tag} {attrs_preview}...>>"
        return f"<{self.__class__.__name__} <{self.tag}>>"


class ActionableElement(BaseElement):
    """Base class for elements that support actions (click, type, etc.).

    Extends BaseElement with action methods that require JavaScript execution
    or CDP commands. Used by BrowserElement.
    """

    @abstractmethod
    async def click(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Click the element.

        Args:
            force: If True, click even if element is not visible.
            timeout: Maximum time to wait for element to be clickable.
        """
        ...

    @abstractmethod
    async def dblclick(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Double-click the element.

        Args:
            force: If True, click even if element is not visible.
            timeout: Maximum time to wait.
        """
        ...

    @abstractmethod
    async def hover(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over the element.

        Args:
            force: If True, hover even if element is not visible.
            timeout: Maximum time to wait.
        """
        ...

    @abstractmethod
    async def fill(
        self,
        value: str,
        *,
        clear: bool = True,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill the element with text.

        Args:
            value: Text to fill.
            clear: If True, clear existing content first.
            timeout: Maximum time to wait.
        """
        ...

    @abstractmethod
    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into the element character by character.

        Args:
            text: Text to type.
            delay: Delay between keystrokes in seconds.
            timeout: Maximum time to wait.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear the element's value."""
        ...

    @abstractmethod
    async def focus(self) -> None:
        """Focus the element."""
        ...

    @abstractmethod
    async def blur(self) -> None:
        """Remove focus from the element."""
        ...

    @abstractmethod
    async def select_option(
        self,
        *values: str,
        by: str = "value",
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in a <select> element.

        Args:
            *values: Values to select.
            by: Selection method ('value', 'text', 'index').
            timeout: Maximum time to wait.

        Returns:
            List of selected values.
        """
        ...

    @abstractmethod
    async def check(self, *, force: bool = False) -> None:
        """Check a checkbox or radio button.

        Args:
            force: If True, check even if not visible.
        """
        ...

    @abstractmethod
    async def uncheck(self, *, force: bool = False) -> None:
        """Uncheck a checkbox.

        Args:
            force: If True, uncheck even if not visible.
        """
        ...

    @abstractmethod
    async def scroll_into_view(self) -> None:
        """Scroll the element into view."""
        ...

    @abstractmethod
    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        format: str = "png",
        quality: int = 80,
    ) -> bytes:
        """Take a screenshot of the element.

        Args:
            path: Optional path to save the screenshot.
            format: Image format ('png', 'jpeg', 'webp').
            quality: JPEG/WebP quality (0-100).

        Returns:
            Screenshot image data.
        """
        ...

    @abstractmethod
    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Get the element's bounding box.

        Returns:
            Dict with x, y, width, height or None if not visible.
        """
        ...

    @abstractmethod
    async def is_visible(self) -> bool:
        """Check if the element is visible.

        Returns:
            True if visible.
        """
        ...

    @abstractmethod
    async def is_enabled(self) -> bool:
        """Check if the element is enabled.

        Returns:
            True if enabled.
        """
        ...

    @abstractmethod
    async def is_checked(self) -> bool:
        """Check if the element (checkbox/radio) is checked.

        Returns:
            True if checked.
        """
        ...

    @abstractmethod
    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Evaluate JavaScript in the context of this element.

        Args:
            expression: JavaScript expression or function.
            *args: Arguments to pass to the function.

        Returns:
            Evaluation result.
        """
        ...


__all__ = [
    "BaseElement",
    "ActionableElement",
]
