"""
Mouse Actions Controller for kuromi-browser.

Provides high-level mouse interaction APIs using CDP Input domain.
Integrates with HumanMouse for stealth human-like movements.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, Tuple, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.dom.element import Element

from kuromi_browser.stealth.behavior.mouse import HumanMouse, Point


class MouseButton(str, Enum):
    """Mouse button types."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    BACK = "back"
    FORWARD = "forward"


@dataclass
class MousePosition:
    """Current mouse position state."""

    x: float
    y: float

    def as_tuple(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))


class MouseController:
    """High-level mouse actions controller.

    Provides click, double-click, right-click, drag & drop, hover,
    and movement operations with optional human-like behavior.

    Example:
        mouse = MouseController(cdp_session)
        await mouse.move_to(100, 200)
        await mouse.click()

        # Or with element
        await mouse.click_element(element)

        # Drag and drop
        await mouse.drag(100, 100, 300, 300)
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        *,
        human_like: bool = True,
        speed: Optional[float] = None,
    ) -> None:
        """Initialize MouseController.

        Args:
            cdp_session: CDP session for sending commands.
            human_like: Use human-like mouse movements.
            speed: Movement speed in pixels/second (None for random).
        """
        self._session = cdp_session
        self._human_like = human_like
        self._speed = speed
        self._position = MousePosition(0, 0)

    @property
    def position(self) -> MousePosition:
        """Get current mouse position."""
        return self._position

    @property
    def x(self) -> float:
        """Get current X coordinate."""
        return self._position.x

    @property
    def y(self) -> float:
        """Get current Y coordinate."""
        return self._position.y

    async def _dispatch_mouse_event(
        self,
        event_type: str,
        x: float,
        y: float,
        button: str = "none",
        click_count: int = 0,
        modifiers: int = 0,
        delta_x: float = 0,
        delta_y: float = 0,
    ) -> None:
        """Dispatch a mouse event via CDP."""
        params: dict[str, Any] = {
            "type": event_type,
            "x": x,
            "y": y,
            "modifiers": modifiers,
        }

        if button != "none":
            params["button"] = button
        if click_count > 0:
            params["clickCount"] = click_count
        if delta_x != 0 or delta_y != 0:
            params["deltaX"] = delta_x
            params["deltaY"] = delta_y

        await self._session.send("Input.dispatchMouseEvent", params)

    async def move_to(
        self,
        x: float,
        y: float,
        *,
        steps: Optional[int] = None,
    ) -> "MouseController":
        """Move mouse to specified position.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            steps: Number of intermediate steps (None for auto).

        Returns:
            Self for chaining.
        """
        start = self._position.as_tuple()
        end = (int(x), int(y))

        if self._human_like:
            await HumanMouse.move(
                self._session,
                start,
                end,
                speed=self._speed,
            )
        else:
            # Direct movement
            if steps and steps > 1:
                for i in range(steps):
                    t = (i + 1) / steps
                    ix = start[0] + (end[0] - start[0]) * t
                    iy = start[1] + (end[1] - start[1]) * t
                    await self._dispatch_mouse_event("mouseMoved", ix, iy)
                    await asyncio.sleep(0.01)
            else:
                await self._dispatch_mouse_event("mouseMoved", x, y)

        self._position = MousePosition(x, y)
        return self

    async def move_by(
        self,
        dx: float,
        dy: float,
    ) -> "MouseController":
        """Move mouse by offset from current position.

        Args:
            dx: X offset.
            dy: Y offset.

        Returns:
            Self for chaining.
        """
        return await self.move_to(self._position.x + dx, self._position.y + dy)

    async def click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        click_count: int = 1,
        delay: Optional[float] = None,
        modifiers: int = 0,
    ) -> "MouseController":
        """Perform a mouse click.

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).
            button: Mouse button to click.
            click_count: Number of clicks (1=single, 2=double, 3=triple).
            delay: Delay between press and release.
            modifiers: Keyboard modifiers (1=Alt, 2=Ctrl, 4=Meta, 8=Shift).

        Returns:
            Self for chaining.
        """
        if x is not None and y is not None:
            await self.move_to(x, y)

        button_str = button.value if isinstance(button, MouseButton) else button
        cx, cy = self._position.x, self._position.y

        if self._human_like:
            # Add slight pre-click delay
            await asyncio.sleep(random.uniform(0.03, 0.08))

        for i in range(click_count):
            # Mouse down
            await self._dispatch_mouse_event(
                "mousePressed",
                cx,
                cy,
                button=button_str,
                click_count=i + 1,
                modifiers=modifiers,
            )

            # Hold delay
            if delay:
                await asyncio.sleep(delay)
            elif self._human_like:
                await asyncio.sleep(random.uniform(0.05, 0.12))

            # Mouse up
            await self._dispatch_mouse_event(
                "mouseReleased",
                cx,
                cy,
                button=button_str,
                click_count=i + 1,
                modifiers=modifiers,
            )

            # Delay between multiple clicks
            if i < click_count - 1:
                if self._human_like:
                    await asyncio.sleep(random.uniform(0.08, 0.15))
                else:
                    await asyncio.sleep(0.05)

        return self

    async def double_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        modifiers: int = 0,
    ) -> "MouseController":
        """Perform a double click.

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).
            button: Mouse button to click.
            modifiers: Keyboard modifiers.

        Returns:
            Self for chaining.
        """
        return await self.click(
            x, y, button=button, click_count=2, modifiers=modifiers
        )

    async def triple_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> "MouseController":
        """Perform a triple click (select line/paragraph).

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).

        Returns:
            Self for chaining.
        """
        return await self.click(x, y, click_count=3)

    async def right_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        *,
        modifiers: int = 0,
    ) -> "MouseController":
        """Perform a right click (context menu).

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).
            modifiers: Keyboard modifiers.

        Returns:
            Self for chaining.
        """
        return await self.click(x, y, button=MouseButton.RIGHT, modifiers=modifiers)

    async def middle_click(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> "MouseController":
        """Perform a middle click.

        Args:
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).

        Returns:
            Self for chaining.
        """
        return await self.click(x, y, button=MouseButton.MIDDLE)

    async def down(
        self,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        *,
        modifiers: int = 0,
    ) -> "MouseController":
        """Press mouse button down (without release).

        Args:
            button: Mouse button.
            modifiers: Keyboard modifiers.

        Returns:
            Self for chaining.
        """
        button_str = button.value if isinstance(button, MouseButton) else button
        await self._dispatch_mouse_event(
            "mousePressed",
            self._position.x,
            self._position.y,
            button=button_str,
            click_count=1,
            modifiers=modifiers,
        )
        return self

    async def up(
        self,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        *,
        modifiers: int = 0,
    ) -> "MouseController":
        """Release mouse button.

        Args:
            button: Mouse button.
            modifiers: Keyboard modifiers.

        Returns:
            Self for chaining.
        """
        button_str = button.value if isinstance(button, MouseButton) else button
        await self._dispatch_mouse_event(
            "mouseReleased",
            self._position.x,
            self._position.y,
            button=button_str,
            click_count=1,
            modifiers=modifiers,
        )
        return self

    async def hover(
        self,
        x: float,
        y: float,
        *,
        duration: Optional[float] = None,
    ) -> "MouseController":
        """Move mouse to position and hover.

        Args:
            x: X coordinate.
            y: Y coordinate.
            duration: How long to hover (seconds).

        Returns:
            Self for chaining.
        """
        await self.move_to(x, y)

        if duration:
            await asyncio.sleep(duration)
        elif self._human_like:
            await asyncio.sleep(random.uniform(0.1, 0.3))

        return self

    async def drag(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        steps: Optional[int] = None,
    ) -> "MouseController":
        """Drag from start to end position.

        Args:
            start_x: Start X coordinate.
            start_y: Start Y coordinate.
            end_x: End X coordinate.
            end_y: End Y coordinate.
            button: Mouse button to hold during drag.
            steps: Number of movement steps.

        Returns:
            Self for chaining.
        """
        button_str = button.value if isinstance(button, MouseButton) else button

        if self._human_like:
            await HumanMouse.drag(
                self._session,
                (int(start_x), int(start_y)),
                (int(end_x), int(end_y)),
                button=button_str,
            )
            self._position = MousePosition(end_x, end_y)
        else:
            # Move to start
            await self.move_to(start_x, start_y)
            await asyncio.sleep(0.05)

            # Press
            await self._dispatch_mouse_event(
                "mousePressed",
                start_x,
                start_y,
                button=button_str,
                click_count=1,
            )
            await asyncio.sleep(0.05)

            # Move to end
            num_steps = steps or 10
            for i in range(1, num_steps + 1):
                t = i / num_steps
                ix = start_x + (end_x - start_x) * t
                iy = start_y + (end_y - start_y) * t
                await self._dispatch_mouse_event("mouseMoved", ix, iy, button=button_str)
                await asyncio.sleep(0.02)

            # Release
            await asyncio.sleep(0.05)
            await self._dispatch_mouse_event(
                "mouseReleased",
                end_x,
                end_y,
                button=button_str,
                click_count=1,
            )
            self._position = MousePosition(end_x, end_y)

        return self

    async def drag_by(
        self,
        dx: float,
        dy: float,
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "MouseController":
        """Drag from current position by offset.

        Args:
            dx: X offset.
            dy: Y offset.
            button: Mouse button to hold during drag.

        Returns:
            Self for chaining.
        """
        return await self.drag(
            self._position.x,
            self._position.y,
            self._position.x + dx,
            self._position.y + dy,
            button=button,
        )

    async def drag_and_drop(
        self,
        source: "Element",
        target: "Element",
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
    ) -> "MouseController":
        """Drag element to another element.

        Args:
            source: Element to drag.
            target: Element to drop onto.
            button: Mouse button to hold during drag.

        Returns:
            Self for chaining.
        """
        source_box = await source.bounding_box()
        target_box = await target.bounding_box()

        if not source_box or not target_box:
            raise ValueError("Source or target element not visible")

        start_x = source_box["x"] + source_box["width"] / 2
        start_y = source_box["y"] + source_box["height"] / 2
        end_x = target_box["x"] + target_box["width"] / 2
        end_y = target_box["y"] + target_box["height"] / 2

        return await self.drag(start_x, start_y, end_x, end_y, button=button)

    async def click_element(
        self,
        element: "Element",
        *,
        button: Union[MouseButton, str] = MouseButton.LEFT,
        click_count: int = 1,
        offset_x: float = 0,
        offset_y: float = 0,
        force: bool = False,
    ) -> "MouseController":
        """Click on an element.

        Args:
            element: Element to click.
            button: Mouse button.
            click_count: Number of clicks.
            offset_x: X offset from element center.
            offset_y: Y offset from element center.
            force: Force click even if element not visible.

        Returns:
            Self for chaining.
        """
        if not force:
            await element.scroll_into_view()
            await asyncio.sleep(0.1)

        box = await element.bounding_box()
        if not box:
            if force:
                # JavaScript click fallback
                await element._call_function("function() { this.click(); }")
                return self
            raise ValueError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2 + offset_x
        y = box["y"] + box["height"] / 2 + offset_y

        return await self.click(x, y, button=button, click_count=click_count)

    async def hover_element(
        self,
        element: "Element",
        *,
        duration: Optional[float] = None,
        offset_x: float = 0,
        offset_y: float = 0,
    ) -> "MouseController":
        """Hover over an element.

        Args:
            element: Element to hover.
            duration: How long to hover.
            offset_x: X offset from element center.
            offset_y: Y offset from element center.

        Returns:
            Self for chaining.
        """
        await element.scroll_into_view()
        await asyncio.sleep(0.1)

        box = await element.bounding_box()
        if not box:
            raise ValueError("Element not visible or has no bounding box")

        x = box["x"] + box["width"] / 2 + offset_x
        y = box["y"] + box["height"] / 2 + offset_y

        return await self.hover(x, y, duration=duration)

    async def wheel(
        self,
        delta_x: float = 0,
        delta_y: float = 0,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> "MouseController":
        """Scroll using mouse wheel.

        Args:
            delta_x: Horizontal scroll amount.
            delta_y: Vertical scroll amount (positive = down).
            x: X coordinate (current position if None).
            y: Y coordinate (current position if None).

        Returns:
            Self for chaining.
        """
        px = x if x is not None else self._position.x
        py = y if y is not None else self._position.y

        await self._dispatch_mouse_event(
            "mouseWheel",
            px,
            py,
            delta_x=delta_x,
            delta_y=delta_y,
        )

        return self

    async def scroll(
        self,
        delta_x: float = 0,
        delta_y: float = 0,
        *,
        x: Optional[float] = None,
        y: Optional[float] = None,
        steps: int = 5,
        smooth: bool = True,
    ) -> "MouseController":
        """Scroll with optional smooth scrolling.

        Args:
            delta_x: Total horizontal scroll amount.
            delta_y: Total vertical scroll amount.
            x: X coordinate for scroll.
            y: Y coordinate for scroll.
            steps: Number of scroll steps for smooth scrolling.
            smooth: Use smooth scrolling.

        Returns:
            Self for chaining.
        """
        px = x if x is not None else self._position.x
        py = y if y is not None else self._position.y

        if smooth and self._human_like:
            await HumanMouse.scroll(
                self._session,
                int(px),
                int(py),
                delta_x=int(delta_x),
                delta_y=int(delta_y),
                steps=steps,
            )
        else:
            await self.wheel(delta_x, delta_y, x=px, y=py)

        return self

    def set_human_like(self, enabled: bool) -> "MouseController":
        """Enable or disable human-like movements.

        Args:
            enabled: Enable human-like behavior.

        Returns:
            Self for chaining.
        """
        self._human_like = enabled
        return self

    def set_speed(self, speed: Optional[float]) -> "MouseController":
        """Set movement speed.

        Args:
            speed: Speed in pixels/second (None for random).

        Returns:
            Self for chaining.
        """
        self._speed = speed
        return self


__all__ = ["MouseController", "MouseButton", "MousePosition"]
