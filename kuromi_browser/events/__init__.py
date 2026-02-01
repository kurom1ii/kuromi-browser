"""
Event system for kuromi-browser.

This module provides event handling and pub/sub capabilities:
- EventEmitter: Base class for event-driven components
- EventBus: Global event bus for cross-component communication
- AsyncEventEmitter: Async-compatible event emitter
- Typed events for different operations
"""

from typing import Any, Callable, Optional

# Import from bus module
from .bus import (
    EventType,
    Event,
    AsyncEventEmitter,
    EventBus,
    get_event_bus,
)

# Import typed events
from .types import (
    # Navigation
    NavigateEvent,
    PageLoadedEvent,
    # DOM
    DOMReadyEvent,
    ElementFoundEvent,
    # Network
    RequestEvent,
    ResponseEvent,
    # Actions
    ClickEvent,
    TypeEvent,
    ScrollEvent,
    HoverEvent,
    ScreenshotEvent,
    # Lifecycle
    BrowserStartedEvent,
    BrowserClosedEvent,
    ContextCreatedEvent,
    # Page events
    ConsoleEvent,
    DialogEvent,
    ErrorEvent,
)


class EventEmitter:
    """Mixin class for event-driven components.

    Provides methods to register, emit, and handle events.
    Synchronous version - use AsyncEventEmitter for async support.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._once_handlers: dict[str, list[Callable[..., Any]]] = {}

    def on(self, event: str, handler: Callable[..., Any]) -> "EventEmitter":
        """Register an event handler."""
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)
        return self

    def once(self, event: str, handler: Callable[..., Any]) -> "EventEmitter":
        """Register a one-time event handler."""
        if event not in self._once_handlers:
            self._once_handlers[event] = []
        self._once_handlers[event].append(handler)
        return self

    def off(self, event: str, handler: Optional[Callable[..., Any]] = None) -> "EventEmitter":
        """Remove an event handler."""
        if handler is None:
            self._handlers.pop(event, None)
            self._once_handlers.pop(event, None)
        else:
            if event in self._handlers and handler in self._handlers[event]:
                self._handlers[event].remove(handler)
            if event in self._once_handlers and handler in self._once_handlers[event]:
                self._once_handlers[event].remove(handler)
        return self

    def emit(self, event: str, *args: Any, **kwargs: Any) -> bool:
        """Emit an event to all registered handlers."""
        handled = False

        if event in self._handlers:
            for handler in self._handlers[event]:
                handler(*args, **kwargs)
                handled = True

        if event in self._once_handlers:
            handlers = self._once_handlers.pop(event, [])
            for handler in handlers:
                handler(*args, **kwargs)
                handled = True

        return handled

    def listener_count(self, event: str) -> int:
        """Get the number of listeners for an event."""
        count = len(self._handlers.get(event, []))
        count += len(self._once_handlers.get(event, []))
        return count

    def remove_all_listeners(self, event: Optional[str] = None) -> "EventEmitter":
        """Remove all listeners, optionally for a specific event."""
        if event is None:
            self._handlers.clear()
            self._once_handlers.clear()
        else:
            self._handlers.pop(event, None)
            self._once_handlers.pop(event, None)
        return self


__all__ = [
    # Core
    "EventType",
    "Event",
    "EventEmitter",
    "AsyncEventEmitter",
    "EventBus",
    "get_event_bus",
    # Navigation events
    "NavigateEvent",
    "PageLoadedEvent",
    # DOM events
    "DOMReadyEvent",
    "ElementFoundEvent",
    # Network events
    "RequestEvent",
    "ResponseEvent",
    # Action events
    "ClickEvent",
    "TypeEvent",
    "ScrollEvent",
    "HoverEvent",
    "ScreenshotEvent",
    # Lifecycle events
    "BrowserStartedEvent",
    "BrowserClosedEvent",
    "ContextCreatedEvent",
    # Page events
    "ConsoleEvent",
    "DialogEvent",
    "ErrorEvent",
]
