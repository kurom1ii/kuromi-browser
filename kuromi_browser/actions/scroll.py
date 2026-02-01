"""
Scroll Controller for kuromi-browser.

Provides smooth scrolling, scroll into view, and various scrolling utilities.
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

from kuromi_browser.stealth.behavior.mouse import HumanMouse


class ScrollBehavior(str, Enum):
    """Scroll behavior types."""

    AUTO = "auto"
    INSTANT = "instant"
    SMOOTH = "smooth"


class ScrollAlignment(str, Enum):
    """Scroll alignment options."""

    START = "start"
    CENTER = "center"
    END = "end"
    NEAREST = "nearest"


@dataclass
class ScrollPosition:
    """Current scroll position."""

    x: float
    y: float
    max_x: float
    max_y: float

    @property
    def is_at_top(self) -> bool:
        return self.y <= 0

    @property
    def is_at_bottom(self) -> bool:
        return self.y >= self.max_y

    @property
    def is_at_left(self) -> bool:
        return self.x <= 0

    @property
    def is_at_right(self) -> bool:
        return self.x >= self.max_x

    @property
    def scroll_percent_y(self) -> float:
        if self.max_y <= 0:
            return 100.0
        return (self.y / self.max_y) * 100

    @property
    def scroll_percent_x(self) -> float:
        if self.max_x <= 0:
            return 100.0
        return (self.x / self.max_x) * 100


class ScrollController:
    """High-level scroll controller.

    Provides smooth scrolling, scroll to element, scroll by amount,
    and various scrolling utilities with optional human-like behavior.

    Example:
        scroll = ScrollController(cdp_session)
        await scroll.to_top()
        await scroll.by(0, 500)  # Scroll down 500px
        await scroll.into_view(element)
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        *,
        human_like: bool = True,
    ) -> None:
        """Initialize ScrollController.

        Args:
            cdp_session: CDP session for sending commands.
            human_like: Use human-like scroll behavior.
        """
        self._session = cdp_session
        self._human_like = human_like

    async def _evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression."""
        result = await self._session.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        return result.get("result", {}).get("value")

    async def get_position(self) -> ScrollPosition:
        """Get current scroll position of the page.

        Returns:
            ScrollPosition object with current and max scroll values.
        """
        data = await self._evaluate(
            """(() => {
                const doc = document.documentElement;
                return {
                    x: window.scrollX || window.pageXOffset || doc.scrollLeft,
                    y: window.scrollY || window.pageYOffset || doc.scrollTop,
                    max_x: Math.max(doc.scrollWidth - doc.clientWidth, 0),
                    max_y: Math.max(doc.scrollHeight - doc.clientHeight, 0)
                };
            })()"""
        )
        return ScrollPosition(**data)

    async def get_viewport_size(self) -> Tuple[int, int]:
        """Get viewport dimensions.

        Returns:
            Tuple of (width, height).
        """
        data = await self._evaluate(
            """(() => ({
                width: window.innerWidth || document.documentElement.clientWidth,
                height: window.innerHeight || document.documentElement.clientHeight
            }))()"""
        )
        return (data["width"], data["height"])

    async def get_page_size(self) -> Tuple[int, int]:
        """Get full page dimensions.

        Returns:
            Tuple of (width, height).
        """
        data = await self._evaluate(
            """(() => ({
                width: Math.max(
                    document.body.scrollWidth,
                    document.documentElement.scrollWidth
                ),
                height: Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight
                )
            }))()"""
        )
        return (data["width"], data["height"])

    async def to(
        self,
        x: float,
        y: float,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
        wait: bool = True,
    ) -> "ScrollController":
        """Scroll to absolute position.

        Args:
            x: Target X position.
            y: Target Y position.
            behavior: Scroll behavior.
            wait: Wait for scroll to complete.

        Returns:
            Self for chaining.
        """
        if self._human_like and behavior == ScrollBehavior.SMOOTH:
            # Use mouse wheel for human-like scrolling
            pos = await self.get_position()
            delta_x = x - pos.x
            delta_y = y - pos.y

            if abs(delta_x) > 0 or abs(delta_y) > 0:
                viewport = await self.get_viewport_size()
                center_x = viewport[0] // 2
                center_y = viewport[1] // 2

                await HumanMouse.scroll(
                    self._session,
                    center_x,
                    center_y,
                    delta_x=int(delta_x),
                    delta_y=int(delta_y),
                    steps=max(5, int(abs(delta_y) / 100)),
                )
        else:
            await self._evaluate(
                f"window.scrollTo({{ left: {x}, top: {y}, behavior: '{behavior.value}' }})"
            )

        if wait and behavior != ScrollBehavior.INSTANT:
            await asyncio.sleep(0.3)

        return self

    async def by(
        self,
        dx: float = 0,
        dy: float = 0,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
        wait: bool = True,
    ) -> "ScrollController":
        """Scroll by relative amount.

        Args:
            dx: Horizontal scroll amount.
            dy: Vertical scroll amount.
            behavior: Scroll behavior.
            wait: Wait for scroll to complete.

        Returns:
            Self for chaining.
        """
        if self._human_like and behavior == ScrollBehavior.SMOOTH:
            viewport = await self.get_viewport_size()
            center_x = viewport[0] // 2
            center_y = viewport[1] // 2

            await HumanMouse.scroll(
                self._session,
                center_x,
                center_y,
                delta_x=int(dx),
                delta_y=int(dy),
                steps=max(3, int(abs(dy) / 100)),
            )
        else:
            await self._evaluate(
                f"window.scrollBy({{ left: {dx}, top: {dy}, behavior: '{behavior.value}' }})"
            )

        if wait and behavior != ScrollBehavior.INSTANT:
            await asyncio.sleep(0.2)

        return self

    async def to_top(
        self,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll to top of page.

        Args:
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        return await self.to(0, 0, behavior=behavior)

    async def to_bottom(
        self,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll to bottom of page.

        Args:
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        pos = await self.get_position()
        return await self.to(0, pos.max_y, behavior=behavior)

    async def to_left(
        self,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll to left edge.

        Args:
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        pos = await self.get_position()
        return await self.to(0, pos.y, behavior=behavior)

    async def to_right(
        self,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll to right edge.

        Args:
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        pos = await self.get_position()
        return await self.to(pos.max_x, pos.y, behavior=behavior)

    async def page_down(
        self,
        *,
        pages: float = 1,
    ) -> "ScrollController":
        """Scroll down by viewport height(s).

        Args:
            pages: Number of pages to scroll.

        Returns:
            Self for chaining.
        """
        viewport = await self.get_viewport_size()
        return await self.by(0, viewport[1] * pages)

    async def page_up(
        self,
        *,
        pages: float = 1,
    ) -> "ScrollController":
        """Scroll up by viewport height(s).

        Args:
            pages: Number of pages to scroll.

        Returns:
            Self for chaining.
        """
        viewport = await self.get_viewport_size()
        return await self.by(0, -viewport[1] * pages)

    async def into_view(
        self,
        element: "Element",
        *,
        block: ScrollAlignment = ScrollAlignment.CENTER,
        inline: ScrollAlignment = ScrollAlignment.NEAREST,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll element into view.

        Args:
            element: Element to scroll into view.
            block: Vertical alignment.
            inline: Horizontal alignment.
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        if self._human_like:
            # Get element position and scroll
            box = await element.bounding_box()
            if box:
                viewport = await self.get_viewport_size()
                pos = await self.get_position()

                # Calculate target scroll position
                target_y = pos.y + box["y"] - viewport[1] // 2 + box["height"] // 2

                if block == ScrollAlignment.START:
                    target_y = pos.y + box["y"]
                elif block == ScrollAlignment.END:
                    target_y = pos.y + box["y"] - viewport[1] + box["height"]

                # Clamp to valid range
                target_y = max(0, min(target_y, pos.max_y))

                if abs(target_y - pos.y) > 10:
                    await self.to(pos.x, target_y)
            else:
                # Fallback to JavaScript
                await element.scroll_into_view()
        else:
            await element._call_function(
                f"""function() {{
                    this.scrollIntoView({{
                        block: '{block.value}',
                        inline: '{inline.value}',
                        behavior: '{behavior.value}'
                    }});
                }}"""
            )

        if behavior != ScrollBehavior.INSTANT:
            await asyncio.sleep(0.2)

        return self

    async def into_view_if_needed(
        self,
        element: "Element",
    ) -> "ScrollController":
        """Scroll element into view only if not already visible.

        Args:
            element: Element to check and possibly scroll.

        Returns:
            Self for chaining.
        """
        is_visible = await element._call_function(
            """function() {
                const rect = this.getBoundingClientRect();
                return (
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                );
            }"""
        )

        if not is_visible:
            await self.into_view(element)

        return self

    async def to_element(
        self,
        element: "Element",
        *,
        offset_x: float = 0,
        offset_y: float = 0,
    ) -> "ScrollController":
        """Scroll so element is at specified position.

        Args:
            element: Target element.
            offset_x: X offset from element top-left.
            offset_y: Y offset from element top-left.

        Returns:
            Self for chaining.
        """
        box = await element.bounding_box()
        if not box:
            raise ValueError("Element not visible or has no bounding box")

        pos = await self.get_position()

        # Element's position relative to document
        doc_x = pos.x + box["x"]
        doc_y = pos.y + box["y"]

        return await self.to(doc_x + offset_x, doc_y + offset_y)

    async def scroll_element(
        self,
        element: "Element",
        dx: float = 0,
        dy: float = 0,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll within a scrollable element.

        Args:
            element: Scrollable element (with overflow).
            dx: Horizontal scroll amount.
            dy: Vertical scroll amount.
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        await element._call_function(
            f"""function(dx, dy) {{
                this.scrollBy({{
                    left: dx,
                    top: dy,
                    behavior: '{behavior.value}'
                }});
            }}""",
            dx,
            dy,
        )

        if behavior != ScrollBehavior.INSTANT:
            await asyncio.sleep(0.2)

        return self

    async def scroll_element_to(
        self,
        element: "Element",
        x: float,
        y: float,
        *,
        behavior: ScrollBehavior = ScrollBehavior.SMOOTH,
    ) -> "ScrollController":
        """Scroll within a scrollable element to position.

        Args:
            element: Scrollable element.
            x: Target X position within element.
            y: Target Y position within element.
            behavior: Scroll behavior.

        Returns:
            Self for chaining.
        """
        await element._call_function(
            f"""function(x, y) {{
                this.scrollTo({{
                    left: x,
                    top: y,
                    behavior: '{behavior.value}'
                }});
            }}""",
            x,
            y,
        )

        if behavior != ScrollBehavior.INSTANT:
            await asyncio.sleep(0.2)

        return self

    async def infinite_scroll(
        self,
        *,
        max_scrolls: int = 10,
        scroll_delay: float = 1.0,
        wait_for_content: float = 2.0,
        scroll_amount: Optional[float] = None,
    ) -> int:
        """Perform infinite scrolling to load dynamic content.

        Args:
            max_scrolls: Maximum number of scroll iterations.
            scroll_delay: Delay between scrolls.
            wait_for_content: Time to wait for content to load.
            scroll_amount: Amount to scroll each time (None = viewport height).

        Returns:
            Number of scrolls performed.
        """
        viewport = await self.get_viewport_size()
        amount = scroll_amount or viewport[1] * 0.8

        last_height = 0
        scrolls_performed = 0

        for _ in range(max_scrolls):
            # Scroll down
            await self.by(0, amount)
            scrolls_performed += 1

            # Wait for content to load
            await asyncio.sleep(scroll_delay)

            # Check if we've reached the bottom
            pos = await self.get_position()
            page_size = await self.get_page_size()

            if page_size[1] == last_height:
                # No new content loaded, wait a bit more
                await asyncio.sleep(wait_for_content)
                page_size = await self.get_page_size()

                if page_size[1] == last_height:
                    # Still no new content, stop
                    break

            last_height = page_size[1]

            # Check if at bottom
            if pos.is_at_bottom:
                break

        return scrolls_performed

    async def wait_for_scroll_idle(
        self,
        *,
        timeout: float = 5.0,
        check_interval: float = 0.1,
    ) -> bool:
        """Wait for scroll to stop.

        Args:
            timeout: Maximum time to wait.
            check_interval: Interval between checks.

        Returns:
            True if scroll stopped, False if timeout.
        """
        last_pos = await self.get_position()
        stable_count = 0
        elapsed = 0.0

        while elapsed < timeout:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

            pos = await self.get_position()
            if pos.x == last_pos.x and pos.y == last_pos.y:
                stable_count += 1
                if stable_count >= 3:
                    return True
            else:
                stable_count = 0
                last_pos = pos

        return False

    def set_human_like(self, enabled: bool) -> "ScrollController":
        """Enable or disable human-like scrolling.

        Args:
            enabled: Enable human-like behavior.

        Returns:
            Self for chaining.
        """
        self._human_like = enabled
        return self


__all__ = [
    "ScrollController",
    "ScrollBehavior",
    "ScrollAlignment",
    "ScrollPosition",
]
