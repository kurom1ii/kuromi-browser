"""
Browser Lifecycle Hooks for kuromi-browser.

Provides hook points for browser, context, and page lifecycle events.
Allows custom behavior at key points in the browser automation workflow.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from kuromi_browser.browser.browser import Browser
    from kuromi_browser.browser.context import BrowserContext
    from kuromi_browser.interfaces import BasePage

logger = logging.getLogger(__name__)


class HookPhase(str, Enum):
    """Lifecycle phases for hooks."""

    # Browser hooks
    BROWSER_LAUNCH = "browser_launch"
    BROWSER_CONNECTED = "browser_connected"
    BROWSER_DISCONNECTED = "browser_disconnected"
    BROWSER_CLOSE = "browser_close"

    # Context hooks
    CONTEXT_CREATED = "context_created"
    CONTEXT_CLOSE = "context_close"

    # Page hooks
    PAGE_CREATED = "page_created"
    PAGE_NAVIGATE = "page_navigate"
    PAGE_LOAD = "page_load"
    PAGE_CLOSE = "page_close"

    # Request hooks
    REQUEST_START = "request_start"
    REQUEST_COMPLETE = "request_complete"
    REQUEST_FAILED = "request_failed"

    # Error hooks
    PAGE_ERROR = "page_error"
    CONSOLE_MESSAGE = "console_message"
    DIALOG_OPENED = "dialog_opened"


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    phase: HookPhase
    """Current lifecycle phase."""

    browser: Optional["Browser"] = None
    """Browser instance if available."""

    context: Optional["BrowserContext"] = None
    """Browser context if available."""

    page: Optional["BasePage"] = None
    """Page instance if available."""

    data: dict[str, Any] = field(default_factory=dict)
    """Additional data for the hook."""

    error: Optional[Exception] = None
    """Error if this is an error hook."""

    cancelled: bool = False
    """Set to True to cancel the operation (for pre-hooks)."""

    def cancel(self) -> None:
        """Cancel the operation (only works for pre-hooks)."""
        self.cancelled = True


# Type for hook handlers
HookHandler = Callable[[HookContext], Any]


@dataclass
class Hook:
    """Represents a registered hook."""

    phase: HookPhase
    """Phase this hook runs on."""

    handler: HookHandler
    """Handler function."""

    priority: int = 0
    """Priority (higher runs first)."""

    once: bool = False
    """If True, hook is removed after first execution."""

    name: Optional[str] = None
    """Optional name for identification."""


class HookManager:
    """Manages lifecycle hooks.

    Allows registering callbacks for various browser lifecycle events.

    Example:
        hooks = HookManager()

        # Register hook
        @hooks.on(HookPhase.PAGE_NAVIGATE)
        async def on_navigate(ctx: HookContext):
            print(f"Navigating to: {ctx.data.get('url')}")

        # Register with priority
        hooks.register(
            HookPhase.BROWSER_LAUNCH,
            my_handler,
            priority=10,
            name="setup_stealth"
        )

        # Use with browser
        async with Browser(hooks=hooks) as browser:
            # Hooks are called automatically
            pass
    """

    def __init__(self) -> None:
        """Initialize hook manager."""
        self._hooks: dict[HookPhase, list[Hook]] = {phase: [] for phase in HookPhase}

    def register(
        self,
        phase: HookPhase,
        handler: HookHandler,
        *,
        priority: int = 0,
        once: bool = False,
        name: Optional[str] = None,
    ) -> Hook:
        """Register a hook handler.

        Args:
            phase: Lifecycle phase to hook.
            handler: Handler function.
            priority: Priority (higher runs first).
            once: Remove after first execution.
            name: Optional name for the hook.

        Returns:
            The registered hook.
        """
        hook = Hook(
            phase=phase,
            handler=handler,
            priority=priority,
            once=once,
            name=name,
        )

        self._hooks[phase].append(hook)
        # Sort by priority (highest first)
        self._hooks[phase].sort(key=lambda h: -h.priority)

        return hook

    def unregister(self, hook: Hook) -> bool:
        """Unregister a hook.

        Args:
            hook: Hook to remove.

        Returns:
            True if removed.
        """
        if hook in self._hooks[hook.phase]:
            self._hooks[hook.phase].remove(hook)
            return True
        return False

    def unregister_by_name(self, name: str) -> int:
        """Unregister hooks by name.

        Args:
            name: Hook name to remove.

        Returns:
            Number of hooks removed.
        """
        removed = 0
        for phase in HookPhase:
            hooks_to_remove = [h for h in self._hooks[phase] if h.name == name]
            for hook in hooks_to_remove:
                self._hooks[phase].remove(hook)
                removed += 1
        return removed

    def on(
        self,
        phase: HookPhase,
        *,
        priority: int = 0,
        once: bool = False,
        name: Optional[str] = None,
    ) -> Callable[[HookHandler], HookHandler]:
        """Decorator to register a hook.

        Args:
            phase: Lifecycle phase.
            priority: Priority (higher runs first).
            once: Remove after first execution.
            name: Optional name.

        Returns:
            Decorator function.

        Example:
            @hooks.on(HookPhase.PAGE_LOAD)
            async def on_load(ctx):
                print("Page loaded!")
        """

        def decorator(handler: HookHandler) -> HookHandler:
            self.register(phase, handler, priority=priority, once=once, name=name)
            return handler

        return decorator

    async def run(
        self,
        phase: HookPhase,
        *,
        browser: Optional["Browser"] = None,
        context: Optional["BrowserContext"] = None,
        page: Optional["BasePage"] = None,
        data: Optional[dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> HookContext:
        """Run hooks for a phase.

        Args:
            phase: Lifecycle phase.
            browser: Browser instance.
            context: Browser context.
            page: Page instance.
            data: Additional data.
            error: Error if applicable.

        Returns:
            Hook context after all hooks ran.
        """
        ctx = HookContext(
            phase=phase,
            browser=browser,
            context=context,
            page=page,
            data=data or {},
            error=error,
        )

        hooks_to_remove: list[Hook] = []

        for hook in self._hooks[phase]:
            if ctx.cancelled:
                break

            try:
                result = hook.handler(ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Hook error in {phase.value}: {e}")

            if hook.once:
                hooks_to_remove.append(hook)

        # Remove one-time hooks
        for hook in hooks_to_remove:
            self._hooks[hook.phase].remove(hook)

        return ctx

    def get_hooks(self, phase: HookPhase) -> list[Hook]:
        """Get hooks for a phase.

        Args:
            phase: Lifecycle phase.

        Returns:
            List of hooks.
        """
        return list(self._hooks[phase])

    def clear(self, phase: Optional[HookPhase] = None) -> None:
        """Clear hooks.

        Args:
            phase: Phase to clear (None = all phases).
        """
        if phase:
            self._hooks[phase].clear()
        else:
            for p in HookPhase:
                self._hooks[p].clear()

    def __len__(self) -> int:
        """Total number of hooks."""
        return sum(len(hooks) for hooks in self._hooks.values())


# Convenience functions for common hooks


def before_navigate(
    hooks: HookManager,
    handler: HookHandler,
    *,
    priority: int = 0,
) -> Hook:
    """Register a before-navigate hook.

    The handler can call ctx.cancel() to prevent navigation.

    Args:
        hooks: Hook manager.
        handler: Handler function.
        priority: Priority.

    Returns:
        Registered hook.
    """
    return hooks.register(HookPhase.PAGE_NAVIGATE, handler, priority=priority)


def after_load(
    hooks: HookManager,
    handler: HookHandler,
    *,
    priority: int = 0,
) -> Hook:
    """Register an after-load hook.

    Args:
        hooks: Hook manager.
        handler: Handler function.
        priority: Priority.

    Returns:
        Registered hook.
    """
    return hooks.register(HookPhase.PAGE_LOAD, handler, priority=priority)


def on_request(
    hooks: HookManager,
    handler: HookHandler,
    *,
    priority: int = 0,
) -> Hook:
    """Register a request hook.

    Args:
        hooks: Hook manager.
        handler: Handler function.
        priority: Priority.

    Returns:
        Registered hook.
    """
    return hooks.register(HookPhase.REQUEST_START, handler, priority=priority)


def on_error(
    hooks: HookManager,
    handler: HookHandler,
    *,
    priority: int = 0,
) -> Hook:
    """Register an error hook.

    Args:
        hooks: Hook manager.
        handler: Handler function.
        priority: Priority.

    Returns:
        Registered hook.
    """
    return hooks.register(HookPhase.PAGE_ERROR, handler, priority=priority)


# Global hook manager for convenience
_global_hooks = HookManager()


def get_global_hooks() -> HookManager:
    """Get the global hook manager.

    Returns:
        Global HookManager instance.
    """
    return _global_hooks


__all__ = [
    "Hook",
    "HookContext",
    "HookHandler",
    "HookManager",
    "HookPhase",
    "after_load",
    "before_navigate",
    "get_global_hooks",
    "on_error",
    "on_request",
]
