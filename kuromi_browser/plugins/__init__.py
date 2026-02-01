"""
Plugin system for kuromi-browser.

Provides extensible plugin architecture for customizing browser behavior:
- Plugin base classes for building custom plugins
- Hook integration for lifecycle events
- Event emitter integration for cross-component communication
- Middleware chain for request/response processing
- Plugin loader for dynamic plugin loading
- Built-in plugins for common functionality

Example:
    from kuromi_browser.plugins import (
        Plugin,
        PluginMetadata,
        PluginManager,
        PluginContext,
        LoggingPlugin,
        TimingPlugin,
        RetryPlugin,
    )
    from kuromi_browser.browser.hooks import HookManager, HookPhase
    from kuromi_browser.events import get_event_bus

    # Create plugin manager
    manager = PluginManager()

    # Load built-in plugins
    manager.load_plugin(LoggingPlugin())
    manager.load_plugin(TimingPlugin())
    manager.load_plugin(RetryPlugin())

    # Load custom plugins from file
    manager.load_from_file("./my_plugin.py")

    # Create plugin context
    context = PluginContext(
        hook_manager=HookManager(),
        event_bus=get_event_bus(),
        config={"debug": True},
    )

    # Initialize and enable plugins
    await manager.initialize(context)
    await manager.enable_all()

    # Use with browser
    async with Browser(plugin_manager=manager) as browser:
        # Plugins are active
        page = await browser.new_page()
        await page.goto("https://example.com")

    # Cleanup
    await manager.shutdown()

Custom Plugin Example:
    from kuromi_browser.plugins import Plugin, PluginMetadata, PluginContext
    from kuromi_browser.browser.hooks import HookPhase, HookContext

    class MyPlugin(Plugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="my-plugin",
                version="1.0.0",
                description="My custom plugin",
            )

        async def setup(self, ctx: PluginContext) -> None:
            # Register hooks
            self.register_hook(
                HookPhase.PAGE_LOAD,
                self.on_page_load,
            )

            # Subscribe to events
            self.subscribe_event("custom_event", self.on_custom_event)

        async def on_page_load(self, hook_ctx: HookContext) -> None:
            url = hook_ctx.data.get("url")
            print(f"Page loaded: {url}")

        async def on_custom_event(self, data: dict) -> None:
            print(f"Custom event: {data}")
"""

# Base classes
from .base import (
    Plugin,
    PluginMetadata,
    PluginContext,
    PluginState,
    PluginPriority,
    MiddlewarePlugin,
    HookPlugin,
    hook,
)

# Middleware
from .middleware import (
    MiddlewareChain,
    MiddlewareContext,
    MiddlewareResult,
    MiddlewareBuilder,
    middleware,
)

# Loader
from .loader import (
    PluginManager,
    PluginDiscovery,
    PluginLoadError,
)

# Built-in plugins
from .builtin import (
    LoggingPlugin,
    TimingPlugin,
    RetryPlugin,
)

# Re-export config classes from built-in plugins
from .builtin.logging_plugin import LoggingConfig
from .builtin.timing_plugin import TimingConfig, TimingMetric, TimingStats
from .builtin.retry_plugin import RetryConfig, RetryState, BackoffStrategy, with_retry, RetryContext

__all__ = [
    # Base
    "Plugin",
    "PluginMetadata",
    "PluginContext",
    "PluginState",
    "PluginPriority",
    "MiddlewarePlugin",
    "HookPlugin",
    "hook",
    # Middleware
    "MiddlewareChain",
    "MiddlewareContext",
    "MiddlewareResult",
    "MiddlewareBuilder",
    "middleware",
    # Loader
    "PluginManager",
    "PluginDiscovery",
    "PluginLoadError",
    # Built-in plugins
    "LoggingPlugin",
    "TimingPlugin",
    "RetryPlugin",
    # Config classes
    "LoggingConfig",
    "TimingConfig",
    "TimingMetric",
    "TimingStats",
    "RetryConfig",
    "RetryState",
    "BackoffStrategy",
    "with_retry",
    "RetryContext",
]
