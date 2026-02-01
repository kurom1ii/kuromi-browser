"""
Core architecture for kuromi-browser.

This module provides the foundational components for the browser automation framework:

- **Event-driven Architecture**: Components communicate through events, enabling
  loose coupling and extensibility.

- **Base Classes**: `BaseElementCore` and `BasePageCore` provide enhanced base
  classes with event support, state tracking, and lifecycle management.

- **Sync Support**: Sync wrappers allow async APIs to be used in synchronous code
  through a managed background event loop.

- **Mixins**: Reusable mixins for event emission, lifecycle management, and
  configuration handling.

Example (async):
    ```python
    from kuromi_browser import Browser
    from kuromi_browser.events import EventType

    async with Browser() as browser:
        page = await browser.new_page()

        # Listen to events
        page.on(EventType.PAGE_LOADED, lambda e: print(f"Loaded: {e.url}"))

        await page.goto("https://example.com")
    ```

Example (sync):
    ```python
    from kuromi_browser.core.sync import SyncPage, run_sync

    # Using run_sync for one-off operations
    page = run_sync(browser.new_page())

    # Or using sync wrapper
    sync_page = SyncPage(page)
    sync_page.goto("https://example.com")
    ```
"""

from kuromi_browser.core.base import (
    # Mixins
    EventEmitterMixin,
    LifecycleMixin,
    ConfigurableMixin,
    # Core classes
    CoreComponent,
    BaseElementCore,
    BasePageCore,
    # State classes
    ElementState,
    PageState,
    # Utilities
    managed_component,
    event_scope,
)

from kuromi_browser.core.sync import (
    # Event loop management
    EventLoopManager,
    get_event_loop_manager,
    run_sync,
    # Decorators
    sync_method,
    make_sync,
    # Wrapper classes
    SyncElement,
    SyncPage,
    # Utilities
    sync_wrapper,
    SyncContextManager,
    sync_context,
)


__all__ = [
    # === Base Module ===
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
    # Context managers
    "managed_component",
    "event_scope",
    # === Sync Module ===
    # Event loop
    "EventLoopManager",
    "get_event_loop_manager",
    "run_sync",
    # Decorators
    "sync_method",
    "make_sync",
    # Wrapper classes
    "SyncElement",
    "SyncPage",
    # Utilities
    "sync_wrapper",
    "SyncContextManager",
    "sync_context",
]
