"""
Async Event Bus for kuromi-browser.

Provides async/await support for event handling with typed events,
middleware support, and event filtering capabilities.
"""

import asyncio
import logging
import time
import weakref
from typing import Any, Callable, Optional, Union, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

# Type aliases for clarity
EventHandler = Callable[..., Any]
AsyncEventHandler = Callable[..., Awaitable[Any]]
EventMiddleware = Callable[["Event"], Awaitable[Optional["Event"]]]
EventFilter = Callable[["Event"], bool]


class EventPriority(int, Enum):
    """Priority levels for event handlers."""

    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


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
    """Base event class with timestamp support and propagation control."""

    type: EventType
    data: Any = None
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None
    propagation_stopped: bool = field(default=False, repr=False)
    _metadata: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def stop_propagation(self) -> None:
        """Stop the event from propagating to other handlers."""
        self.propagation_stopped = True

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata on the event."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the event."""
        return self._metadata.get(key, default)


@dataclass
class HandlerEntry:
    """Wrapper for event handlers with priority and filter support."""

    handler: EventHandler
    priority: EventPriority = EventPriority.NORMAL
    filter: Optional[EventFilter] = None

    def matches(self, event: Event) -> bool:
        """Check if this handler should handle the event."""
        if self.filter is None:
            return True
        try:
            return self.filter(event)
        except Exception:
            return True


class AsyncEventEmitter:
    """Async event emitter supporting both sync and async handlers.

    Features:
    - Priority-based handler ordering
    - Event filtering
    - Middleware support
    - Event propagation control
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[HandlerEntry]] = {}
        self._once_handlers: dict[str, list[HandlerEntry]] = {}
        self._middleware: list[EventMiddleware] = []
        self._lock = asyncio.Lock()
        self._error_handler: Optional[Callable[[Exception, Event], None]] = None

    def on(
        self,
        event: Union[str, EventType],
        handler: EventHandler,
        *,
        priority: EventPriority = EventPriority.NORMAL,
        filter: Optional[EventFilter] = None,
    ) -> "AsyncEventEmitter":
        """Register an event handler.

        Args:
            event: Event type to listen for.
            handler: Handler function (sync or async).
            priority: Handler priority (higher runs first).
            filter: Optional filter function.

        Returns:
            Self for chaining.
        """
        key = event.value if isinstance(event, EventType) else event
        if key not in self._handlers:
            self._handlers[key] = []

        entry = HandlerEntry(handler=handler, priority=priority, filter=filter)
        self._handlers[key].append(entry)
        # Sort by priority (descending)
        self._handlers[key].sort(key=lambda e: e.priority, reverse=True)
        return self

    def once(
        self,
        event: Union[str, EventType],
        handler: EventHandler,
        *,
        priority: EventPriority = EventPriority.NORMAL,
        filter: Optional[EventFilter] = None,
    ) -> "AsyncEventEmitter":
        """Register a one-time event handler.

        Args:
            event: Event type to listen for.
            handler: Handler function (sync or async).
            priority: Handler priority.
            filter: Optional filter function.

        Returns:
            Self for chaining.
        """
        key = event.value if isinstance(event, EventType) else event
        if key not in self._once_handlers:
            self._once_handlers[key] = []

        entry = HandlerEntry(handler=handler, priority=priority, filter=filter)
        self._once_handlers[key].append(entry)
        self._once_handlers[key].sort(key=lambda e: e.priority, reverse=True)
        return self

    def off(
        self,
        event: Union[str, EventType],
        handler: Optional[EventHandler] = None,
    ) -> "AsyncEventEmitter":
        """Remove an event handler.

        Args:
            event: Event type.
            handler: Specific handler to remove, or None to remove all.

        Returns:
            Self for chaining.
        """
        key = event.value if isinstance(event, EventType) else event
        if handler is None:
            self._handlers.pop(key, None)
            self._once_handlers.pop(key, None)
        else:
            if key in self._handlers:
                self._handlers[key] = [
                    e for e in self._handlers[key] if e.handler != handler
                ]
            if key in self._once_handlers:
                self._once_handlers[key] = [
                    e for e in self._once_handlers[key] if e.handler != handler
                ]
        return self

    def use(self, middleware: EventMiddleware) -> "AsyncEventEmitter":
        """Add middleware to process events before handlers.

        Middleware can modify or filter events. Return None to stop propagation.

        Args:
            middleware: Async function that receives and optionally transforms events.

        Returns:
            Self for chaining.
        """
        self._middleware.append(middleware)
        return self

    def remove_middleware(self, middleware: EventMiddleware) -> "AsyncEventEmitter":
        """Remove a middleware."""
        if middleware in self._middleware:
            self._middleware.remove(middleware)
        return self

    def set_error_handler(
        self,
        handler: Callable[[Exception, str], None],
    ) -> "AsyncEventEmitter":
        """Set a custom error handler for handler exceptions.

        Args:
            handler: Function receiving the exception and event key.

        Returns:
            Self for chaining.
        """
        self._error_handler = handler
        return self

    async def _run_middleware(self, event: Event) -> Optional[Event]:
        """Run middleware chain on event."""
        current = event
        for mw in self._middleware:
            try:
                result = await mw(current)
                if result is None:
                    return None
                current = result
            except Exception as e:
                logger.warning(f"Middleware error: {e}")
        return current

    async def emit(
        self,
        event: Union[str, EventType, Event],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit an event to all registered handlers (async).

        Args:
            event: Event type, string, or Event object.
            *args: Arguments to pass to handlers.
            **kwargs: Keyword arguments to pass to handlers.

        Returns:
            True if any handler was called.
        """
        event_obj: Optional[Event] = None
        if isinstance(event, Event):
            key = event.type.value if isinstance(event.type, EventType) else event.type
            event_obj = event
            # Run middleware if we have an Event object
            if self._middleware:
                event_obj = await self._run_middleware(event_obj)
                if event_obj is None:
                    return False
            args = (event_obj,) + args
        else:
            key = event.value if isinstance(event, EventType) else event

        handled = False
        handlers = self._handlers.get(key, [])[:]
        once_handlers = self._once_handlers.pop(key, [])
        all_handlers = handlers + once_handlers

        for entry in all_handlers:
            # Check filter
            if event_obj is not None and not entry.matches(event_obj):
                continue

            # Check propagation
            if event_obj is not None and event_obj.propagation_stopped:
                break

            try:
                if asyncio.iscoroutinefunction(entry.handler):
                    await entry.handler(*args, **kwargs)
                else:
                    entry.handler(*args, **kwargs)
                handled = True
            except Exception as e:
                if self._error_handler:
                    self._error_handler(e, key)
                else:
                    logger.error(f"Error in event handler for {key}: {e}")

        return handled

    def emit_sync(
        self,
        event: Union[str, EventType],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit an event synchronously (only calls sync handlers).

        Args:
            event: Event type or string.
            *args: Arguments to pass to handlers.
            **kwargs: Keyword arguments to pass to handlers.

        Returns:
            True if any handler was called.
        """
        key = event.value if isinstance(event, EventType) else event
        handled = False

        handlers = self._handlers.get(key, [])[:]
        once_handlers = self._once_handlers.pop(key, [])
        all_handlers = handlers + once_handlers

        for entry in all_handlers:
            if not asyncio.iscoroutinefunction(entry.handler):
                try:
                    entry.handler(*args, **kwargs)
                    handled = True
                except Exception as e:
                    if self._error_handler:
                        self._error_handler(e, key)
                    else:
                        logger.error(f"Error in sync event handler for {key}: {e}")

        return handled

    def listener_count(self, event: Union[str, EventType]) -> int:
        """Get the number of listeners for an event."""
        key = event.value if isinstance(event, EventType) else event
        count = len(self._handlers.get(key, []))
        count += len(self._once_handlers.get(key, []))
        return count

    def listeners(self, event: Union[str, EventType]) -> list[EventHandler]:
        """Get all listeners for an event."""
        key = event.value if isinstance(event, EventType) else event
        handlers = [e.handler for e in self._handlers.get(key, [])]
        handlers.extend(e.handler for e in self._once_handlers.get(key, []))
        return handlers

    def event_names(self) -> list[str]:
        """Get all registered event names."""
        names = set(self._handlers.keys())
        names.update(self._once_handlers.keys())
        return list(names)

    def remove_all_listeners(
        self,
        event: Optional[Union[str, EventType]] = None,
    ) -> "AsyncEventEmitter":
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
        self,
        event: Union[str, EventType],
        *,
        timeout: Optional[float] = None,
        predicate: Optional[Callable[..., bool]] = None,
    ) -> Any:
        """Wait for an event to be emitted.

        Args:
            event: Event type to wait for.
            timeout: Maximum time to wait in seconds.
            predicate: Optional function to filter which events to accept.

        Returns:
            Event data when matched.
        """
        future: asyncio.Future = asyncio.Future()

        def handler(*args, **kwargs):
            if future.done():
                return
            if predicate is not None:
                try:
                    if not predicate(*args, **kwargs):
                        return
                except Exception:
                    return
            if args:
                future.set_result(args[0] if len(args) == 1 else args)
            else:
                future.set_result(kwargs if kwargs else None)

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

    Features:
    - Global event routing
    - Namespace support via event prefixes
    - Wildcard subscriptions (planned)
    """

    _instance: Optional["EventBus"] = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._once_handlers = {}
            cls._instance._middleware = []
            cls._instance._lock = asyncio.Lock()
            cls._instance._error_handler = None
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        if cls._instance is not None:
            cls._instance._handlers.clear()
            cls._instance._once_handlers.clear()
            cls._instance._middleware.clear()
            cls._instance._error_handler = None
        cls._instance = None

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Get the singleton instance."""
        return cls()


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus.get_instance()


# =============================================================================
# Utility decorators
# =============================================================================


def on_event(
    event: Union[str, EventType],
    *,
    priority: EventPriority = EventPriority.NORMAL,
    bus: Optional[AsyncEventEmitter] = None,
) -> Callable[[EventHandler], EventHandler]:
    """Decorator to register a function as an event handler.

    Args:
        event: Event type to listen for.
        priority: Handler priority.
        bus: Event emitter to register on (defaults to global bus).

    Example:
        @on_event(EventType.PAGE_LOADED)
        async def handle_page_loaded(event):
            print(f"Page loaded: {event.data}")
    """
    def decorator(func: EventHandler) -> EventHandler:
        target = bus or get_event_bus()
        target.on(event, func, priority=priority)
        return func
    return decorator


def emit_event(
    event_type: EventType,
    *,
    source: Optional[str] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to emit an event after a function completes.

    Args:
        event_type: Event type to emit.
        source: Optional source identifier.

    Example:
        @emit_event(EventType.CLICK)
        async def click_button(self, selector):
            ...  # click logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = await func(*args, **kwargs)
                event = Event(
                    type=event_type,
                    data={"args": args[1:], "kwargs": kwargs, "result": result},
                    source=source,
                )
                await get_event_bus().emit(event)
                return result
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                event = Event(
                    type=event_type,
                    data={"args": args[1:], "kwargs": kwargs, "result": result},
                    source=source,
                )
                get_event_bus().emit_sync(event_type, event)
                return result
            return sync_wrapper
    return decorator


__all__ = [
    # Types
    "EventType",
    "EventPriority",
    "Event",
    "HandlerEntry",
    # Type aliases
    "EventHandler",
    "AsyncEventHandler",
    "EventMiddleware",
    "EventFilter",
    # Classes
    "AsyncEventEmitter",
    "EventBus",
    # Functions
    "get_event_bus",
    # Decorators
    "on_event",
    "emit_event",
]
