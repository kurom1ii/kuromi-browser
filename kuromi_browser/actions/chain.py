"""
Actions Chaining - Fluent API for kuromi-browser.

Provides a unified interface for chaining mouse, keyboard, form,
and scroll actions in a fluent, readable manner.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, Sequence, Tuple, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.dom.element import Element

from kuromi_browser.actions.forms import FormHandler
from kuromi_browser.actions.keyboard import KeyboardController, KeyModifier
from kuromi_browser.actions.mouse import MouseButton, MouseController
from kuromi_browser.actions.scroll import ScrollBehavior, ScrollController


class ActionChain:
    """Fluent API for chaining browser actions.

    Provides a unified interface for performing sequences of mouse,
    keyboard, form, and scroll actions in a readable, chainable manner.

    Example:
        actions = ActionChain(cdp_session)

        # Chain multiple actions
        await (
            actions
            .move_to(100, 100)
            .click()
            .type("Hello World")
            .press("Enter")
            .wait(0.5)
            .scroll_down(300)
            .perform()
        )

        # Or perform immediately
        await actions.click(200, 300).type("Test").perform()
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        *,
        human_like: bool = True,
    ) -> None:
        """Initialize ActionChain.

        Args:
            cdp_session: CDP session for sending commands.
            human_like: Use human-like behavior for all actions.
        """
        self._session = cdp_session
        self._human_like = human_like

        # Controllers
        self._mouse = MouseController(cdp_session, human_like=human_like)
        self._keyboard = KeyboardController(cdp_session, human_like=human_like)
        self._scroll = ScrollController(cdp_session, human_like=human_like)
        self._form = FormHandler(cdp_session, human_like=human_like)

        # Action queue
        self._actions: List[Callable[[], Awaitable[Any]]] = []

    @property
    def mouse(self) -> MouseController:
        """Get the mouse controller."""
        return self._mouse

    @property
    def keyboard(self) -> KeyboardController:
        """Get the keyboard controller."""
        return self._keyboard

    @property
    def scroll(self) -> ScrollController:
        """Get the scroll controller."""
        return self._scroll

    @property
    def form(self) -> FormHandler:
        """Get the form handler."""
        return self._form

    def _add_action(self, action: Callable[[], Awaitable[Any]]) -> "ActionChain":
        """Add action to the queue."""
        self._actions.append(action)
        return self

    async def perform(self) -> "ActionChain":
        """Execute all queued actions.

        Returns:
            Self for further chaining.
        """
        for action in self._actions:
            await action()
        self._actions.clear()
        return self

    def reset(self) -> "ActionChain":
        """Clear all queued actions without executing.

        Returns:
            Self for chaining.
        """
        self._actions.clear()
        return self

    # Mouse actions

    def move_to(
        self,
        x: float,
        y: float,
        *,
        steps: Optional[int] = None,
    ) -> "ActionChain":
        """Queue mouse move to position.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            steps: Number of intermediate steps.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.move_to(x, y, steps=steps)
        )

    def move_by(
        self,
        dx: float,
        dy: float,
    ) -> "ActionChain":
        """Queue mouse move by offset.

        Args:
            dx: X offset.
            dy: Y offset.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.move_by(dx, dy)
        )

    def click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "ActionChain":
        """Queue mouse click.

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).
            button: Mouse button.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.click(x, y, button=button)
        )

    def double_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> "ActionChain":
        """Queue double click.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.double_click(x, y)
        )

    def right_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> "ActionChain":
        """Queue right click.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.right_click(x, y)
        )

    def mouse_down(
        self,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "ActionChain":
        """Queue mouse button press.

        Args:
            button: Mouse button.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.down(button)
        )

    def mouse_up(
        self,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "ActionChain":
        """Queue mouse button release.

        Args:
            button: Mouse button.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.up(button)
        )

    def hover(
        self,
        x: float,
        y: float,
        *,
        duration: Optional[float] = None,
    ) -> "ActionChain":
        """Queue hover at position.

        Args:
            x: X coordinate.
            y: Y coordinate.
            duration: Hover duration.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.hover(x, y, duration=duration)
        )

    def drag(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> "ActionChain":
        """Queue drag operation.

        Args:
            start_x: Start X.
            start_y: Start Y.
            end_x: End X.
            end_y: End Y.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.drag(start_x, start_y, end_x, end_y)
        )

    def drag_by(
        self,
        dx: float,
        dy: float,
    ) -> "ActionChain":
        """Queue drag by offset.

        Args:
            dx: X offset.
            dy: Y offset.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.drag_by(dx, dy)
        )

    def click_element(
        self,
        element: "Element",
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "ActionChain":
        """Queue click on element.

        Args:
            element: Element to click.
            button: Mouse button.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.click_element(element, button=button)
        )

    def hover_element(
        self,
        element: "Element",
        *,
        duration: Optional[float] = None,
    ) -> "ActionChain":
        """Queue hover over element.

        Args:
            element: Element to hover.
            duration: Hover duration.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.hover_element(element, duration=duration)
        )

    def drag_and_drop(
        self,
        source: "Element",
        target: "Element",
    ) -> "ActionChain":
        """Queue drag and drop between elements.

        Args:
            source: Source element.
            target: Target element.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._mouse.drag_and_drop(source, target)
        )

    # Keyboard actions

    def type(
        self,
        text: str,
        *,
        delay: Optional[float] = None,
    ) -> "ActionChain":
        """Queue typing text.

        Args:
            text: Text to type.
            delay: Delay between keystrokes.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.type(text, delay=delay)
        )

    def press(
        self,
        key: str,
        *,
        delay: Optional[float] = None,
    ) -> "ActionChain":
        """Queue key press.

        Args:
            key: Key to press.
            delay: Hold duration.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.press(key, delay=delay)
        )

    def key_down(
        self,
        key: str,
    ) -> "ActionChain":
        """Queue key down (without release).

        Args:
            key: Key to press.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.down(key)
        )

    def key_up(
        self,
        key: str,
    ) -> "ActionChain":
        """Queue key release.

        Args:
            key: Key to release.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.up(key)
        )

    def shortcut(
        self,
        *keys: str,
    ) -> "ActionChain":
        """Queue keyboard shortcut.

        Args:
            *keys: Keys to press together.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.shortcut(*keys)
        )

    def combo(
        self,
        combo_string: str,
    ) -> "ActionChain":
        """Queue key combination from string.

        Args:
            combo_string: Combination like "Ctrl+A".

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._keyboard.combo(combo_string)
        )

    def select_all(self) -> "ActionChain":
        """Queue select all."""
        return self._add_action(lambda: self._keyboard.select_all())

    def copy(self) -> "ActionChain":
        """Queue copy."""
        return self._add_action(lambda: self._keyboard.copy())

    def paste(self) -> "ActionChain":
        """Queue paste."""
        return self._add_action(lambda: self._keyboard.paste())

    def cut(self) -> "ActionChain":
        """Queue cut."""
        return self._add_action(lambda: self._keyboard.cut())

    def undo(self) -> "ActionChain":
        """Queue undo."""
        return self._add_action(lambda: self._keyboard.undo())

    def redo(self) -> "ActionChain":
        """Queue redo."""
        return self._add_action(lambda: self._keyboard.redo())

    # Scroll actions

    def scroll_to(
        self,
        x: float,
        y: float,
    ) -> "ActionChain":
        """Queue scroll to position.

        Args:
            x: Target X.
            y: Target Y.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._scroll.to(x, y)
        )

    def scroll_by(
        self,
        dx: float = 0,
        dy: float = 0,
    ) -> "ActionChain":
        """Queue scroll by amount.

        Args:
            dx: Horizontal amount.
            dy: Vertical amount.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._scroll.by(dx, dy)
        )

    def scroll_down(
        self,
        amount: float = 300,
    ) -> "ActionChain":
        """Queue scroll down.

        Args:
            amount: Pixels to scroll.

        Returns:
            Self for chaining.
        """
        return self.scroll_by(0, amount)

    def scroll_up(
        self,
        amount: float = 300,
    ) -> "ActionChain":
        """Queue scroll up.

        Args:
            amount: Pixels to scroll.

        Returns:
            Self for chaining.
        """
        return self.scroll_by(0, -amount)

    def scroll_left(
        self,
        amount: float = 300,
    ) -> "ActionChain":
        """Queue scroll left.

        Args:
            amount: Pixels to scroll.

        Returns:
            Self for chaining.
        """
        return self.scroll_by(-amount, 0)

    def scroll_right(
        self,
        amount: float = 300,
    ) -> "ActionChain":
        """Queue scroll right.

        Args:
            amount: Pixels to scroll.

        Returns:
            Self for chaining.
        """
        return self.scroll_by(amount, 0)

    def scroll_to_top(self) -> "ActionChain":
        """Queue scroll to top."""
        return self._add_action(lambda: self._scroll.to_top())

    def scroll_to_bottom(self) -> "ActionChain":
        """Queue scroll to bottom."""
        return self._add_action(lambda: self._scroll.to_bottom())

    def scroll_into_view(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue scroll element into view.

        Args:
            element: Element to scroll to.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._scroll.into_view(element)
        )

    def page_down(
        self,
        pages: float = 1,
    ) -> "ActionChain":
        """Queue page down.

        Args:
            pages: Number of pages.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._scroll.page_down(pages=pages)
        )

    def page_up(
        self,
        pages: float = 1,
    ) -> "ActionChain":
        """Queue page up.

        Args:
            pages: Number of pages.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._scroll.page_up(pages=pages)
        )

    # Form actions

    def fill(
        self,
        element: "Element",
        value: str,
    ) -> "ActionChain":
        """Queue fill input.

        Args:
            element: Input element.
            value: Value to fill.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.fill(element, value)
        )

    def check(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue check checkbox.

        Args:
            element: Checkbox element.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.check(element)
        )

    def uncheck(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue uncheck checkbox.

        Args:
            element: Checkbox element.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.uncheck(element)
        )

    def select_option(
        self,
        element: "Element",
        value: str,
    ) -> "ActionChain":
        """Queue select option.

        Args:
            element: Select element.
            value: Value to select.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.select_by_value(element, value)
        )

    def upload_file(
        self,
        element: "Element",
        file_path: str,
    ) -> "ActionChain":
        """Queue file upload.

        Args:
            element: File input element.
            file_path: Path to file.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.upload_file(element, file_path)
        )

    def submit(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue form submit.

        Args:
            element: Form or submit button.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: self._form.submit(element)
        )

    # Utility actions

    def wait(
        self,
        seconds: float,
    ) -> "ActionChain":
        """Queue wait/pause.

        Args:
            seconds: Time to wait.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: asyncio.sleep(seconds)
        )

    def pause(
        self,
        seconds: float,
    ) -> "ActionChain":
        """Alias for wait()."""
        return self.wait(seconds)

    def focus(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue focus element.

        Args:
            element: Element to focus.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: element.focus()
        )

    def blur(
        self,
        element: "Element",
    ) -> "ActionChain":
        """Queue blur (unfocus) element.

        Args:
            element: Element to blur.

        Returns:
            Self for chaining.
        """
        return self._add_action(
            lambda: element._call_function("function() { this.blur(); }")
        )

    def custom(
        self,
        action: Callable[[], Awaitable[Any]],
    ) -> "ActionChain":
        """Queue custom async action.

        Args:
            action: Async function to execute.

        Returns:
            Self for chaining.
        """
        return self._add_action(action)

    # Context manager for auto-perform

    async def __aenter__(self) -> "ActionChain":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - auto-perform."""
        await self.perform()


def create_action_chain(
    cdp_session: "CDPSession",
    *,
    human_like: bool = True,
) -> ActionChain:
    """Create a new action chain.

    Args:
        cdp_session: CDP session.
        human_like: Use human-like behavior.

    Returns:
        New ActionChain instance.
    """
    return ActionChain(cdp_session, human_like=human_like)


__all__ = ["ActionChain", "create_action_chain"]
