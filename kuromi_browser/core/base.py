"""
Core base classes for kuromi-browser.

This module provides enhanced base classes that integrate with the event system
and provide both sync and async interfaces. All core components should inherit
from these classes for consistent behavior.
"""

from abc import ABC, abstractmethod
import asyncio
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
)
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from kuromi_browser.events import (
    AsyncEventEmitter,
    Event,
    EventType,
    get_event_bus,
)

if TYPE_CHECKING:
    from kuromi_browser.models import (
        Cookie,
        Fingerprint,
        NetworkResponse,
        PageConfig,
    )
    from kuromi_browser.cdp import CDPSession

T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# Core Mixins
# =============================================================================


class EventEmitterMixin:
    """Mixin that provides event emission capabilities.

    Components inheriting from this mixin can emit events both locally
    and to the global event bus for cross-component communication.
    """

    def __init__(self) -> None:
        self._local_emitter = AsyncEventEmitter()
        self._event_bus = get_event_bus()
        self._emit_to_bus = True  # Whether to also emit to global bus

    def on(
        self,
        event: Union[str, EventType],
        handler: Callable[..., Any],
    ) -> "EventEmitterMixin":
        """Register a local event handler."""
        self._local_emitter.on(event, handler)
        return self

    def once(
        self,
        event: Union[str, EventType],
        handler: Callable[..., Any],
    ) -> "EventEmitterMixin":
        """Register a one-time local event handler."""
        self._local_emitter.once(event, handler)
        return self

    def off(
        self,
        event: Union[str, EventType],
        handler: Optional[Callable[..., Any]] = None,
    ) -> "EventEmitterMixin":
        """Remove an event handler."""
        self._local_emitter.off(event, handler)
        return self

    async def emit(
        self,
        event: Union[str, EventType, Event],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit an event to local handlers and optionally to global bus."""
        # Emit locally first
        local_handled = await self._local_emitter.emit(event, *args, **kwargs)

        # Also emit to global bus if enabled
        bus_handled = False
        if self._emit_to_bus:
            bus_handled = await self._event_bus.emit(event, *args, **kwargs)

        return local_handled or bus_handled

    def emit_sync(
        self,
        event: Union[str, EventType],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit an event synchronously (only sync handlers)."""
        local_handled = self._local_emitter.emit_sync(event, *args, **kwargs)
        bus_handled = False
        if self._emit_to_bus:
            bus_handled = self._event_bus.emit_sync(event, *args, **kwargs)
        return local_handled or bus_handled

    async def wait_for_event(
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
            predicate: Optional function to filter events.

        Returns:
            Event data when the event is emitted.
        """
        future: asyncio.Future = asyncio.Future()

        def handler(*args: Any, **kwargs: Any) -> None:
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
            raise TimeoutError(f"Timeout waiting for event: {event}")


class LifecycleMixin:
    """Mixin for managing component lifecycle.

    Provides standardized initialization, cleanup, and resource management.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
        self._cleanup_handlers: list[Callable[[], Awaitable[None]]] = []

    @property
    def is_initialized(self) -> bool:
        """Check if component is initialized."""
        return self._initialized

    @property
    def is_closed(self) -> bool:
        """Check if component is closed."""
        return self._closed

    def _ensure_initialized(self) -> None:
        """Ensure component is initialized before use."""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} is not initialized")
        if self._closed:
            raise RuntimeError(f"{self.__class__.__name__} is already closed")

    def add_cleanup_handler(
        self,
        handler: Callable[[], Awaitable[None]],
    ) -> None:
        """Register a cleanup handler to run on close."""
        self._cleanup_handlers.append(handler)

    async def _run_cleanup(self) -> None:
        """Run all registered cleanup handlers."""
        for handler in reversed(self._cleanup_handlers):
            try:
                await handler()
            except Exception as e:
                # Log but don't fail on cleanup errors
                print(f"Cleanup error in {self.__class__.__name__}: {e}")
        self._cleanup_handlers.clear()


class ConfigurableMixin(Generic[T]):
    """Mixin for components with configuration.

    Provides standardized configuration access and validation.
    """

    def __init__(self, config: Optional[T] = None) -> None:
        self._config = config

    @property
    def config(self) -> Optional[T]:
        """Get the component configuration."""
        return self._config

    def configure(self, config: T) -> None:
        """Update the component configuration."""
        self._config = config
        self._on_config_change(config)

    def _on_config_change(self, config: T) -> None:
        """Called when configuration changes. Override to handle updates."""
        pass


# =============================================================================
# Core Base Classes
# =============================================================================


class CoreComponent(EventEmitterMixin, LifecycleMixin, ABC):
    """Base class for all core components.

    Combines event emission and lifecycle management into a single base class.
    All major kuromi-browser components should inherit from this.
    """

    def __init__(self) -> None:
        EventEmitterMixin.__init__(self)
        LifecycleMixin.__init__(self)
        self._id = f"{self.__class__.__name__}_{id(self)}"

    @property
    def component_id(self) -> str:
        """Get unique component identifier."""
        return self._id

    async def initialize(self) -> None:
        """Initialize the component.

        Override this method to perform async initialization.
        Call super().initialize() at the start.
        """
        if self._initialized:
            return
        self._initialized = True
        await self.emit(EventType.CONTEXT_CREATED, {"component": self._id})

    async def close(self) -> None:
        """Close the component and release resources.

        Override this method to perform cleanup.
        Call super().close() at the end.
        """
        if self._closed:
            return
        self._closed = True
        await self._run_cleanup()
        await self.emit(EventType.CONTEXT_CLOSE, {"component": self._id})

    async def __aenter__(self) -> "CoreComponent":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()


@dataclass
class ElementState:
    """Represents the state of a DOM element at a point in time."""

    tag_name: str = ""
    visible: bool = False
    enabled: bool = True
    checked: bool = False
    text_content: str = ""
    bounding_box: Optional[dict[str, float]] = None
    attributes: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class BaseElementCore(CoreComponent, ABC):
    """Enhanced base class for DOM elements with event support.

    Extends the basic element interface with:
    - Event emission for actions
    - State caching and invalidation
    - Retry logic for transient failures
    """

    def __init__(self) -> None:
        super().__init__()
        self._state_cache: Optional[ElementState] = None
        self._cache_ttl: float = 0.5  # Cache valid for 500ms
        self._retry_count: int = 3
        self._retry_delay: float = 0.1

    @property
    @abstractmethod
    def tag_name(self) -> str:
        """Get the element's tag name."""
        ...

    @property
    def cached_state(self) -> Optional[ElementState]:
        """Get cached element state if still valid."""
        if self._state_cache is None:
            return None
        if time.time() - self._state_cache.timestamp > self._cache_ttl:
            self._state_cache = None
            return None
        return self._state_cache

    def invalidate_cache(self) -> None:
        """Invalidate the state cache."""
        self._state_cache = None

    async def get_state(self, force_refresh: bool = False) -> ElementState:
        """Get the current element state.

        Args:
            force_refresh: If True, bypass cache and fetch fresh state.

        Returns:
            Current element state.
        """
        if not force_refresh and self.cached_state is not None:
            return self.cached_state

        state = ElementState(
            tag_name=self.tag_name,
            visible=await self.is_visible(),
            enabled=await self.is_enabled(),
            checked=await self.is_checked(),
            text_content=await self.text_content() or "",
            bounding_box=await self.bounding_box(),
            timestamp=time.time(),
        )
        self._state_cache = state
        return state

    async def _with_retry(
        self,
        operation: Callable[[], Awaitable[R]],
        operation_name: str,
    ) -> R:
        """Execute an operation with retry logic.

        Args:
            operation: Async callable to execute.
            operation_name: Name for error messages.

        Returns:
            Operation result.
        """
        last_error: Optional[Exception] = None
        for attempt in range(self._retry_count):
            try:
                return await operation()
            except Exception as e:
                last_error = e
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
                    self.invalidate_cache()

        raise RuntimeError(
            f"Failed to {operation_name} after {self._retry_count} attempts: {last_error}"
        )

    # Abstract methods from BaseElement interface

    @abstractmethod
    async def get_attribute(self, name: str) -> Optional[str]:
        """Get an attribute value from the element."""
        ...

    @abstractmethod
    async def get_property(self, name: str) -> Any:
        """Get a JavaScript property from the element."""
        ...

    @abstractmethod
    async def text_content(self) -> Optional[str]:
        """Get the text content of the element."""
        ...

    @abstractmethod
    async def inner_text(self) -> str:
        """Get the inner text of the element."""
        ...

    @abstractmethod
    async def inner_html(self) -> str:
        """Get the inner HTML of the element."""
        ...

    @abstractmethod
    async def outer_html(self) -> str:
        """Get the outer HTML of the element."""
        ...

    @abstractmethod
    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Get the element's bounding box."""
        ...

    @abstractmethod
    async def is_visible(self) -> bool:
        """Check if the element is visible."""
        ...

    @abstractmethod
    async def is_enabled(self) -> bool:
        """Check if the element is enabled."""
        ...

    @abstractmethod
    async def is_checked(self) -> bool:
        """Check if the element is checked."""
        ...

    @abstractmethod
    async def click(
        self,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click the element."""
        ...

    @abstractmethod
    async def fill(
        self,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill the element with text."""
        ...

    @abstractmethod
    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into the element."""
        ...

    @abstractmethod
    async def hover(
        self,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over the element."""
        ...

    @abstractmethod
    async def focus(self) -> None:
        """Focus the element."""
        ...

    @abstractmethod
    async def scroll_into_view(self) -> None:
        """Scroll the element into view."""
        ...

    @abstractmethod
    async def query_selector(self, selector: str) -> Optional["BaseElementCore"]:
        """Find a child element."""
        ...

    @abstractmethod
    async def query_selector_all(self, selector: str) -> list["BaseElementCore"]:
        """Find all matching child elements."""
        ...


@dataclass
class PageState:
    """Represents the state of a page at a point in time."""

    url: str = ""
    title: str = ""
    load_state: str = "loading"
    content_length: int = 0
    timestamp: float = field(default_factory=time.time)


class BasePageCore(CoreComponent, ABC):
    """Enhanced base class for pages with event support.

    Extends the basic page interface with:
    - Event emission for navigation and actions
    - State tracking and history
    - Hook system for extensibility
    """

    def __init__(self) -> None:
        super().__init__()
        self._navigation_hooks: list[Callable[[str], Awaitable[None]]] = []
        self._action_hooks: list[Callable[[str, Any], Awaitable[None]]] = []
        self._state_history: list[PageState] = []
        self._max_history: int = 100

    @property
    @abstractmethod
    def url(self) -> str:
        """Get the current page URL."""
        ...

    @property
    @abstractmethod
    def title(self) -> str:
        """Get the page title."""
        ...

    @property
    def state_history(self) -> list[PageState]:
        """Get the page state history."""
        return self._state_history.copy()

    def add_navigation_hook(
        self,
        hook: Callable[[str], Awaitable[None]],
    ) -> None:
        """Add a hook to be called before navigation.

        Args:
            hook: Async function receiving the target URL.
        """
        self._navigation_hooks.append(hook)

    def add_action_hook(
        self,
        hook: Callable[[str, Any], Awaitable[None]],
    ) -> None:
        """Add a hook to be called before actions.

        Args:
            hook: Async function receiving action name and parameters.
        """
        self._action_hooks.append(hook)

    async def _run_navigation_hooks(self, url: str) -> None:
        """Run all navigation hooks."""
        for hook in self._navigation_hooks:
            await hook(url)

    async def _run_action_hooks(self, action: str, params: Any) -> None:
        """Run all action hooks."""
        for hook in self._action_hooks:
            await hook(action, params)

    def _record_state(self, load_state: str = "complete") -> None:
        """Record current page state to history."""
        state = PageState(
            url=self.url,
            title=self.title,
            load_state=load_state,
        )
        self._state_history.append(state)
        # Trim history if needed
        if len(self._state_history) > self._max_history:
            self._state_history = self._state_history[-self._max_history:]

    # Navigation methods with event emission

    @abstractmethod
    async def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
    ) -> Optional["NetworkResponse"]:
        """Navigate to a URL."""
        ...

    @abstractmethod
    async def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Reload the page."""
        ...

    @abstractmethod
    async def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate back in history."""
        ...

    @abstractmethod
    async def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate forward in history."""
        ...

    @abstractmethod
    async def content(self) -> str:
        """Get the page HTML content."""
        ...

    @abstractmethod
    async def query_selector(self, selector: str) -> Optional[BaseElementCore]:
        """Find an element matching the selector."""
        ...

    @abstractmethod
    async def query_selector_all(self, selector: str) -> list[BaseElementCore]:
        """Find all elements matching the selector."""
        ...

    @abstractmethod
    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[BaseElementCore]:
        """Wait for an element to appear."""
        ...

    @abstractmethod
    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for the page to reach a load state."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript in the page."""
        ...

    @abstractmethod
    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict[str, float]] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take a screenshot of the page."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the page."""
        ...


# =============================================================================
# Context Manager Utilities
# =============================================================================


@asynccontextmanager
async def managed_component(component: CoreComponent):
    """Context manager for auto-initializing and closing components.

    Example:
        async with managed_component(page) as p:
            await p.goto("https://example.com")
    """
    try:
        await component.initialize()
        yield component
    finally:
        await component.close()


@asynccontextmanager
async def event_scope(
    emitter: EventEmitterMixin,
    event: Union[str, EventType],
    handler: Callable[..., Any],
):
    """Temporarily register an event handler within a scope.

    Example:
        async with event_scope(page, "request", log_request):
            await page.goto("https://example.com")
    """
    emitter.on(event, handler)
    try:
        yield
    finally:
        emitter.off(event, handler)


__all__ = [
    # Mixins
    "EventEmitterMixin",
    "LifecycleMixin",
    "ConfigurableMixin",
    # Core classes
    "CoreComponent",
    "BaseElementCore",
    "BasePageCore",
    # State classes
    "ElementState",
    "PageState",
    # Utilities
    "managed_component",
    "event_scope",
]
