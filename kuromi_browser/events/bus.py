"""
Async Event Bus for kuromi-browser.

Provides async/await support for event handling with typed events.
"""

import asyncio
import time
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class EventType(str, Enum):
    """Standard event types used throughout the library."""

    # Navigation events
    NAVIGATE = "navigate"
    PAGE_LOADED = "page_loaded"
    PAGE_LOAD = "page.load"
    PAGE_DOMCONTENTLOADED = "page.domcontentloaded"
    PAGE_NAVIGATED = "page.navigated"
    PAGE_ERROR = "page.error"
    PAGE_CONSOLE = "page.console"
    PAGE_DIALOG = "page.dialog"
    PAGE_DOWNLOAD = "page.download"
    PAGE_POPUP = "page.popup"
    PAGE_CLOSE = "page.close"

    # DOM events
    DOM_READY = "dom_ready"
    ELEMENT_FOUND = "element_found"
    ELEMENT_NOT_FOUND = "element_not_found"

    # Network events
    REQUEST = "request"
    RESPONSE = "response"
    NETWORK_REQUEST = "network.request"
    NETWORK_RESPONSE = "network.response"
    NETWORK_FAILED = "network.failed"
    NETWORK_FINISHED = "network.finished"

    # Action events
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    HOVER = "hover"
    SCREENSHOT = "screenshot"

    # Frame events
    FRAME_ATTACHED = "frame.attached"
    FRAME_NAVIGATED = "frame.navigated"
    FRAME_DETACHED = "frame.detached"

    # Worker events
    WORKER_CREATED = "worker.created"
    WORKER_DESTROYED = "worker.destroyed"

    # Lifecycle events
    BROWSER_STARTED = "browser_started"
    BROWSER_CLOSED = "browser_closed"
    BROWSER_DISCONNECTED = "browser.disconnected"
    CONTEXT_CREATED = "context.created"
    CONTEXT_CLOSE = "context.close"


@dataclass
class Event:
    """Base event class with timestamp support."""

    type: EventType
    data: Any = None
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class AsyncEventEmitter:
    """Async event emitter supporting both sync and async handlers."""

    def __init__(self) -> None:
        self._handlers: dict[Union[str, EventType], list[Callable[..., Any]]] = {}
        self._once_handlers: dict[Union[str, EventType], list[Callable[..., Any]]] = {}
        self._lock = asyncio.Lock()

    def on(self, event: Union[str, EventType], handler: Callable[..., Any]) -> "AsyncEventEmitter":
        """Register an event handler."""
        key = event.value if isinstance(event, EventType) else event
        if key not in self._handlers:
            self._handlers[key] = []
        self._handlers[key].append(handler)
        return self

    def once(self, event: Union[str, EventType], handler: Callable[..., Any]) -> "AsyncEventEmitter":
        """Register a one-time event handler."""
        key = event.value if isinstance(event, EventType) else event
        if key not in self._once_handlers:
            self._once_handlers[key] = []
        self._once_handlers[key].append(handler)
        return self

    def off(
        self, event: Union[str, EventType], handler: Optional[Callable[..., Any]] = None
    ) -> "AsyncEventEmitter":
        """Remove an event handler."""
        key = event.value if isinstance(event, EventType) else event
        if handler is None:
            self._handlers.pop(key, None)
            self._once_handlers.pop(key, None)
        else:
            if key in self._handlers and handler in self._handlers[key]:
                self._handlers[key].remove(handler)
            if key in self._once_handlers and handler in self._once_handlers[key]:
                self._once_handlers[key].remove(handler)
        return self

    async def emit(self, event: Union[str, EventType, Event], *args: Any, **kwargs: Any) -> bool:
        """Emit an event to all registered handlers (async)."""
        if isinstance(event, Event):
            key = event.type.value if isinstance(event.type, EventType) else event.type
            args = (event,) + args
        else:
            key = event.value if isinstance(event, EventType) else event

        handled = False
        handlers = self._handlers.get(key, [])[:]
        once_handlers = self._once_handlers.pop(key, [])
        all_handlers = handlers + once_handlers

        for handler in all_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
                handled = True
            except Exception as e:
                # Log but don't stop other handlers
                print(f"Error in event handler for {key}: {e}")

        return handled

    def emit_sync(self, event: Union[str, EventType], *args: Any, **kwargs: Any) -> bool:
        """Emit an event synchronously (only calls sync handlers)."""
        key = event.value if isinstance(event, EventType) else event
        handled = False

        handlers = self._handlers.get(key, [])[:]
        once_handlers = self._once_handlers.pop(key, [])
        all_handlers = handlers + once_handlers

        for handler in all_handlers:
            if not asyncio.iscoroutinefunction(handler):
                try:
                    handler(*args, **kwargs)
                    handled = True
                except Exception as e:
                    print(f"Error in sync event handler for {key}: {e}")

        return handled

    def listener_count(self, event: Union[str, EventType]) -> int:
        """Get the number of listeners for an event."""
        key = event.value if isinstance(event, EventType) else event
        count = len(self._handlers.get(key, []))
        count += len(self._once_handlers.get(key, []))
        return count

    def remove_all_listeners(self, event: Optional[Union[str, EventType]] = None) -> "AsyncEventEmitter":
        """Remove all listeners, optionally for a specific event."""
        if event is None:
            self._handlers.clear()
            self._once_handlers.clear()
        else:
            key = event.value if isinstance(event, EventType) else event
            self._handlers.pop(key, None)
            self._once_handlers.pop(key, None)
        return self

    async def wait_for(
        self, event: Union[str, EventType], timeout: Optional[float] = None
    ) -> Any:
        """Wait for an event to be emitted."""
        future: asyncio.Future = asyncio.Future()

        def handler(*args, **kwargs):
            if not future.done():
                if args:
                    future.set_result(args[0] if len(args) == 1 else args)
                else:
                    future.set_result(None)

        self.once(event, handler)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.off(event, handler)
            raise


class EventBus(AsyncEventEmitter):
    """Global async event bus for cross-component communication.

    Singleton pattern allows different parts of the library to
    communicate without direct coupling.
    """

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._once_handlers = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        if cls._instance is not None:
            cls._instance._handlers.clear()
            cls._instance._once_handlers.clear()
        cls._instance = None

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Get the singleton instance."""
        return cls()


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus.get_instance()


__all__ = [
    "EventType",
    "Event",
    "AsyncEventEmitter",
    "EventBus",
    "get_event_bus",
]
