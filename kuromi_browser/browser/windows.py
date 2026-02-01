"""
Window Controller for kuromi-browser.

Manages browser windows including positioning, sizing, and state.
Supports multi-window scenarios and window lifecycle events.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPConnection

logger = logging.getLogger(__name__)


class WindowState(str, Enum):
    """Window state types."""

    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"


@dataclass
class WindowBounds:
    """Window position and size."""

    left: int = 0
    """X position of window."""

    top: int = 0
    """Y position of window."""

    width: int = 1920
    """Window width."""

    height: int = 1080
    """Window height."""

    window_state: WindowState = WindowState.NORMAL
    """Window state."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "windowState": self.window_state.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WindowBounds":
        """Create from dictionary."""
        return cls(
            left=data.get("left", 0),
            top=data.get("top", 0),
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            window_state=WindowState(data.get("windowState", "normal")),
        )


@dataclass
class WindowInfo:
    """Information about a browser window."""

    window_id: int
    """Browser window ID."""

    bounds: WindowBounds
    """Window bounds."""

    target_ids: list[str] = field(default_factory=list)
    """Target IDs (tabs) in this window."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "window_id": self.window_id,
            "bounds": self.bounds.to_dict(),
            "target_ids": self.target_ids,
        }


@dataclass
class WindowEvents:
    """Event callbacks for window lifecycle."""

    on_created: list[Callable[[WindowInfo], Any]] = field(default_factory=list)
    on_closed: list[Callable[[int], Any]] = field(default_factory=list)
    on_bounds_changed: list[Callable[[WindowInfo], Any]] = field(default_factory=list)
    on_state_changed: list[Callable[[WindowInfo], Any]] = field(default_factory=list)


class Window:
    """Represents a browser window.

    Provides methods to control window position, size, and state.
    """

    def __init__(
        self,
        controller: "WindowController",
        info: WindowInfo,
    ) -> None:
        """Initialize window.

        Args:
            controller: Parent window controller.
            info: Window information.
        """
        self._controller = controller
        self._info = info

    @property
    def id(self) -> int:
        """Window ID."""
        return self._info.window_id

    @property
    def bounds(self) -> WindowBounds:
        """Window bounds."""
        return self._info.bounds

    @property
    def state(self) -> WindowState:
        """Window state."""
        return self._info.bounds.window_state

    @property
    def left(self) -> int:
        """Window X position."""
        return self._info.bounds.left

    @property
    def top(self) -> int:
        """Window Y position."""
        return self._info.bounds.top

    @property
    def width(self) -> int:
        """Window width."""
        return self._info.bounds.width

    @property
    def height(self) -> int:
        """Window height."""
        return self._info.bounds.height

    @property
    def target_ids(self) -> list[str]:
        """Target IDs in this window."""
        return self._info.target_ids

    @property
    def info(self) -> WindowInfo:
        """Window info."""
        return self._info

    async def set_bounds(
        self,
        *,
        left: Optional[int] = None,
        top: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        """Set window bounds.

        Args:
            left: X position.
            top: Y position.
            width: Window width.
            height: Window height.
        """
        bounds: dict[str, Any] = {}
        if left is not None:
            bounds["left"] = left
        if top is not None:
            bounds["top"] = top
        if width is not None:
            bounds["width"] = width
        if height is not None:
            bounds["height"] = height

        await self._controller._set_window_bounds(self.id, bounds)

        # Update local state
        if left is not None:
            self._info.bounds.left = left
        if top is not None:
            self._info.bounds.top = top
        if width is not None:
            self._info.bounds.width = width
        if height is not None:
            self._info.bounds.height = height

    async def move(self, left: int, top: int) -> None:
        """Move window to position.

        Args:
            left: X position.
            top: Y position.
        """
        await self.set_bounds(left=left, top=top)

    async def resize(self, width: int, height: int) -> None:
        """Resize window.

        Args:
            width: New width.
            height: New height.
        """
        await self.set_bounds(width=width, height=height)

    async def maximize(self) -> None:
        """Maximize window."""
        await self._controller._set_window_bounds(
            self.id, {"windowState": "maximized"}
        )
        self._info.bounds.window_state = WindowState.MAXIMIZED

    async def minimize(self) -> None:
        """Minimize window."""
        await self._controller._set_window_bounds(
            self.id, {"windowState": "minimized"}
        )
        self._info.bounds.window_state = WindowState.MINIMIZED

    async def fullscreen(self) -> None:
        """Enter fullscreen mode."""
        await self._controller._set_window_bounds(
            self.id, {"windowState": "fullscreen"}
        )
        self._info.bounds.window_state = WindowState.FULLSCREEN

    async def restore(self) -> None:
        """Restore window to normal state."""
        await self._controller._set_window_bounds(
            self.id, {"windowState": "normal"}
        )
        self._info.bounds.window_state = WindowState.NORMAL

    async def bring_to_front(self) -> None:
        """Bring window to front."""
        await self._controller._connection.send(
            "Browser.bringToFront",
            {"windowId": self.id},
        )

    async def close(self) -> None:
        """Close window."""
        await self._controller.close(self.id)

    async def refresh(self) -> None:
        """Refresh window info from browser."""
        info = await self._controller._get_window_info(self.id)
        self._info = info

    def __repr__(self) -> str:
        return (
            f"Window(id={self.id}, "
            f"bounds=({self.left}, {self.top}, {self.width}x{self.height}), "
            f"state={self.state.value})"
        )


class WindowController:
    """Controls browser windows.

    Manages window creation, positioning, and lifecycle.

    Example:
        async with Browser() as browser:
            windows = WindowController(browser.connection)

            # Get current window
            window = await windows.get_for_target(target_id)

            # Resize
            await window.resize(1280, 720)

            # Move
            await window.move(100, 100)

            # Maximize
            await window.maximize()
    """

    def __init__(
        self,
        connection: "CDPConnection",
    ) -> None:
        """Initialize window controller.

        Args:
            connection: CDP connection.
        """
        self._connection = connection
        self._windows: dict[int, Window] = {}
        self._events = WindowEvents()

    @property
    def count(self) -> int:
        """Number of tracked windows."""
        return len(self._windows)

    def all(self) -> list[Window]:
        """Get all windows.

        Returns:
            List of all windows.
        """
        return list(self._windows.values())

    def get(self, window_id: int) -> Optional[Window]:
        """Get window by ID.

        Args:
            window_id: Window ID.

        Returns:
            Window or None if not found.
        """
        return self._windows.get(window_id)

    async def get_for_target(self, target_id: str) -> Window:
        """Get window containing a target.

        Args:
            target_id: Target ID.

        Returns:
            Window containing the target.
        """
        result = await self._connection.send(
            "Browser.getWindowForTarget",
            {"targetId": target_id},
        )

        window_id = result["windowId"]
        bounds_data = result.get("bounds", {})

        bounds = WindowBounds.from_dict(bounds_data)
        info = WindowInfo(
            window_id=window_id,
            bounds=bounds,
            target_ids=[target_id],
        )

        if window_id in self._windows:
            # Update existing window
            self._windows[window_id]._info = info
        else:
            # New window
            self._windows[window_id] = Window(self, info)
            await self._emit_event("created", info)

        return self._windows[window_id]

    async def _get_window_info(self, window_id: int) -> WindowInfo:
        """Get window info from browser.

        Args:
            window_id: Window ID.

        Returns:
            Window info.
        """
        result = await self._connection.send(
            "Browser.getWindowBounds",
            {"windowId": window_id},
        )

        bounds_data = result.get("bounds", {})
        bounds = WindowBounds.from_dict(bounds_data)

        return WindowInfo(window_id=window_id, bounds=bounds)

    async def _set_window_bounds(
        self,
        window_id: int,
        bounds: dict[str, Any],
    ) -> None:
        """Set window bounds via CDP.

        Args:
            window_id: Window ID.
            bounds: Bounds to set.
        """
        await self._connection.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_id,
                "bounds": bounds,
            },
        )

        # Fire event
        window = self._windows.get(window_id)
        if window:
            if "windowState" in bounds:
                await self._emit_event("state_changed", window.info)
            else:
                await self._emit_event("bounds_changed", window.info)

    async def close(self, window_id: int) -> bool:
        """Close a window.

        Note: This closes all targets in the window.

        Args:
            window_id: Window to close.

        Returns:
            True if closed.
        """
        window = self._windows.get(window_id)
        if not window:
            return False

        # Close all targets in window
        for target_id in window.target_ids:
            try:
                await self._connection.send(
                    "Target.closeTarget",
                    {"targetId": target_id},
                )
            except Exception:
                pass

        del self._windows[window_id]
        await self._emit_event("closed", window_id)

        return True

    async def refresh(self) -> list[Window]:
        """Refresh all window info.

        Returns:
            List of all windows.
        """
        # Get all targets first
        result = await self._connection.send("Target.getTargets")
        targets = result.get("targetInfos", [])

        page_targets = [t for t in targets if t.get("type") == "page"]

        # Group by window
        for target in page_targets:
            target_id = target["targetId"]
            try:
                await self.get_for_target(target_id)
            except Exception:
                pass

        return self.all()

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit an event to handlers."""
        handlers = getattr(self._events, f"on_{event}", [])
        for handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Register event handler.

        Events:
            - created: Window created (WindowInfo)
            - closed: Window closed (window_id: int)
            - bounds_changed: Window bounds changed (WindowInfo)
            - state_changed: Window state changed (WindowInfo)

        Args:
            event: Event name.
            handler: Handler function.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers is not None:
            handlers.append(handler)

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def __len__(self) -> int:
        return len(self._windows)

    def __iter__(self):
        return iter(self._windows.values())


__all__ = [
    "Window",
    "WindowBounds",
    "WindowController",
    "WindowInfo",
    "WindowState",
]
