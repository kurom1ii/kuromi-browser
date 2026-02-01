"""
Plugin base classes for kuromi-browser.

Provides the foundation for building extensible plugins that integrate
with the browser's hook system and event bus.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

if TYPE_CHECKING:
    from kuromi_browser.browser.browser import Browser
    from kuromi_browser.browser.context import BrowserContext
    from kuromi_browser.browser.hooks import HookManager, HookPhase, HookContext
    from kuromi_browser.events.bus import AsyncEventEmitter, EventBus

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    """Plugin lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class PluginPriority(int, Enum):
    """Standard plugin priorities."""

    HIGHEST = 1000
    HIGH = 100
    NORMAL = 0
    LOW = -100
    LOWEST = -1000


@dataclass
class PluginMetadata:
    """Plugin metadata and configuration."""

    name: str
    """Unique plugin name."""

    version: str = "1.0.0"
    """Plugin version."""

    description: str = ""
    """Human-readable description."""

    author: str = ""
    """Plugin author."""

    dependencies: list[str] = field(default_factory=list)
    """List of plugin names this plugin depends on."""

    priority: int = PluginPriority.NORMAL
    """Plugin priority (higher = runs first)."""

    tags: list[str] = field(default_factory=list)
    """Tags for categorization."""

    config_schema: Optional[dict[str, Any]] = None
    """Optional JSON schema for plugin configuration."""


@dataclass
class PluginContext:
    """Context provided to plugins during execution."""

    browser: Optional["Browser"] = None
    """Browser instance if available."""

    context: Optional["BrowserContext"] = None
    """Browser context if available."""

    hook_manager: Optional["HookManager"] = None
    """Hook manager for registering hooks."""

    event_bus: Optional["EventBus"] = None
    """Event bus for emitting/listening to events."""

    config: dict[str, Any] = field(default_factory=dict)
    """Plugin-specific configuration."""

    shared_data: dict[str, Any] = field(default_factory=dict)
    """Shared data between plugins."""


class Plugin(ABC):
    """Base class for all plugins.

    Plugins extend browser functionality by hooking into lifecycle events
    and processing requests/responses.

    Example:
        class MyPlugin(Plugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom plugin"
                )

            async def setup(self, ctx: PluginContext) -> None:
                # Register hooks, subscribe to events
                ctx.hook_manager.register(
                    HookPhase.PAGE_LOAD,
                    self.on_page_load
                )

            async def on_page_load(self, hook_ctx: HookContext) -> None:
                print(f"Page loaded: {hook_ctx.data.get('url')}")
    """

    def __init__(self) -> None:
        """Initialize plugin."""
        self._state = PluginState.UNINITIALIZED
        self._context: Optional[PluginContext] = None
        self._registered_hooks: list[Any] = []
        self._event_subscriptions: list[tuple[str, Callable]] = []

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        ...

    @property
    def name(self) -> str:
        """Plugin name."""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Plugin version."""
        return self.metadata.version

    @property
    def state(self) -> PluginState:
        """Current plugin state."""
        return self._state

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._state == PluginState.ENABLED

    @property
    def context(self) -> Optional[PluginContext]:
        """Plugin context."""
        return self._context

    async def initialize(self, ctx: PluginContext) -> None:
        """Initialize the plugin with context.

        Called once when the plugin is loaded.

        Args:
            ctx: Plugin context.
        """
        self._context = ctx
        try:
            await self.setup(ctx)
            self._state = PluginState.INITIALIZED
            logger.debug(f"Plugin {self.name} initialized")
        except Exception as e:
            self._state = PluginState.ERROR
            logger.error(f"Plugin {self.name} failed to initialize: {e}")
            raise

    async def setup(self, ctx: PluginContext) -> None:
        """Setup plugin hooks and event handlers.

        Override this method to register hooks and subscribe to events.

        Args:
            ctx: Plugin context.
        """
        pass

    async def enable(self) -> None:
        """Enable the plugin.

        Called when the plugin is activated.
        """
        if self._state == PluginState.INITIALIZED or self._state == PluginState.DISABLED:
            await self.on_enable()
            self._state = PluginState.ENABLED
            logger.debug(f"Plugin {self.name} enabled")

    async def on_enable(self) -> None:
        """Called when plugin is enabled.

        Override to perform actions when enabling.
        """
        pass

    async def disable(self) -> None:
        """Disable the plugin.

        Called when the plugin is deactivated.
        """
        if self._state == PluginState.ENABLED:
            await self.on_disable()
            self._state = PluginState.DISABLED
            logger.debug(f"Plugin {self.name} disabled")

    async def on_disable(self) -> None:
        """Called when plugin is disabled.

        Override to perform cleanup when disabling.
        """
        pass

    async def destroy(self) -> None:
        """Destroy the plugin and clean up resources.

        Called when the plugin is unloaded.
        """
        await self.on_destroy()

        # Unregister all hooks
        if self._context and self._context.hook_manager:
            for hook in self._registered_hooks:
                self._context.hook_manager.unregister(hook)

        # Unsubscribe from all events
        if self._context and self._context.event_bus:
            for event, handler in self._event_subscriptions:
                self._context.event_bus.off(event, handler)

        self._registered_hooks.clear()
        self._event_subscriptions.clear()
        self._state = PluginState.UNINITIALIZED
        logger.debug(f"Plugin {self.name} destroyed")

    async def on_destroy(self) -> None:
        """Called when plugin is being destroyed.

        Override to perform final cleanup.
        """
        pass

    def register_hook(
        self,
        phase: "HookPhase",
        handler: Callable,
        *,
        priority: Optional[int] = None,
        name: Optional[str] = None,
    ) -> Any:
        """Helper to register a hook and track it for cleanup.

        Args:
            phase: Hook phase.
            handler: Handler function.
            priority: Hook priority (defaults to plugin priority).
            name: Hook name.

        Returns:
            Registered hook.
        """
        if not self._context or not self._context.hook_manager:
            raise RuntimeError("Plugin not initialized with hook manager")

        hook = self._context.hook_manager.register(
            phase,
            handler,
            priority=priority if priority is not None else self.metadata.priority,
            name=name or f"{self.name}:{phase.value}",
        )
        self._registered_hooks.append(hook)
        return hook

    def subscribe_event(
        self,
        event: str,
        handler: Callable,
    ) -> None:
        """Helper to subscribe to an event and track it for cleanup.

        Args:
            event: Event name.
            handler: Handler function.
        """
        if not self._context or not self._context.event_bus:
            raise RuntimeError("Plugin not initialized with event bus")

        self._context.event_bus.on(event, handler)
        self._event_subscriptions.append((event, handler))

    async def emit_event(self, event: str, *args: Any, **kwargs: Any) -> bool:
        """Helper to emit an event.

        Args:
            event: Event name.
            *args: Event arguments.
            **kwargs: Event keyword arguments.

        Returns:
            True if any handler was called.
        """
        if not self._context or not self._context.event_bus:
            raise RuntimeError("Plugin not initialized with event bus")

        return await self._context.event_bus.emit(event, *args, **kwargs)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get plugin configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value.
        """
        if not self._context:
            return default
        return self._context.config.get(key, default)

    def set_shared_data(self, key: str, value: Any) -> None:
        """Set shared data for other plugins.

        Args:
            key: Data key.
            value: Data value.
        """
        if self._context:
            self._context.shared_data[f"{self.name}:{key}"] = value

    def get_shared_data(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """Get shared data from another plugin.

        Args:
            plugin_name: Source plugin name.
            key: Data key.
            default: Default value.

        Returns:
            Shared data value.
        """
        if not self._context:
            return default
        return self._context.shared_data.get(f"{plugin_name}:{key}", default)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} state={self._state.value}>"


class MiddlewarePlugin(Plugin):
    """Plugin that acts as middleware in the request/response chain.

    Middleware plugins can intercept and modify requests before they
    are sent and responses after they are received.

    Example:
        class AuthMiddleware(MiddlewarePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="auth-middleware",
                    priority=PluginPriority.HIGH
                )

            async def process_request(self, request, next_handler):
                request.headers["Authorization"] = "Bearer token"
                return await next_handler(request)
    """

    @abstractmethod
    async def process_request(
        self,
        request: Any,
        next_handler: Callable,
    ) -> Any:
        """Process a request before it's sent.

        Args:
            request: The request to process.
            next_handler: Call this to continue the chain.

        Returns:
            Response from the chain.
        """
        return await next_handler(request)

    async def process_response(
        self,
        response: Any,
        request: Any,
    ) -> Any:
        """Process a response after it's received.

        Args:
            response: The response to process.
            request: The original request.

        Returns:
            Processed response.
        """
        return response


class HookPlugin(Plugin):
    """Plugin that primarily uses hooks for browser lifecycle events.

    Provides convenient decorators for common hook patterns.
    """

    def __init__(self) -> None:
        super().__init__()
        self._hook_handlers: dict[str, Callable] = {}

    async def setup(self, ctx: PluginContext) -> None:
        """Auto-register decorated hook handlers."""
        await super().setup(ctx)

        # Register any methods decorated with @hook
        for name in dir(self):
            method = getattr(self, name, None)
            if callable(method) and hasattr(method, "_hook_phase"):
                phase = method._hook_phase
                priority = getattr(method, "_hook_priority", self.metadata.priority)
                self.register_hook(phase, method, priority=priority)


def hook(phase: "HookPhase", priority: Optional[int] = None):
    """Decorator to mark a method as a hook handler.

    Args:
        phase: Hook phase to handle.
        priority: Optional priority override.

    Example:
        class MyPlugin(HookPlugin):
            @hook(HookPhase.PAGE_LOAD)
            async def on_page_load(self, ctx: HookContext):
                print("Page loaded!")
    """

    def decorator(func: Callable) -> Callable:
        func._hook_phase = phase
        if priority is not None:
            func._hook_priority = priority
        return func

    return decorator


# Type variable for plugin classes
P = TypeVar("P", bound=Plugin)


__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginContext",
    "PluginState",
    "PluginPriority",
    "MiddlewarePlugin",
    "HookPlugin",
    "hook",
]
