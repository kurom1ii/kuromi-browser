"""
Synchronous wrappers for kuromi-browser async APIs.

This module provides sync-compatible interfaces that wrap async operations,
allowing kuromi-browser to be used in synchronous contexts like scripts
or interactive sessions.
"""

import asyncio
import atexit
import functools
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

if TYPE_CHECKING:
    from kuromi_browser.core.base import BaseElementCore, BasePageCore
    from kuromi_browser.models import Cookie, NetworkResponse

T = TypeVar("T")
R = TypeVar("R")


# =============================================================================
# Event Loop Management
# =============================================================================


class EventLoopManager:
    """Manages a dedicated event loop for sync wrappers.

    Runs an asyncio event loop in a background thread to allow
    sync code to execute async operations without blocking.
    """

    _instance: Optional["EventLoopManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EventLoopManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize the event loop manager."""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()
        self._shutdown = False

    def _run_loop(self) -> None:
        """Run the event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._started.set()
        try:
            self._loop.run_forever()
        finally:
            # Clean up pending tasks
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            # Run until all tasks are cancelled
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.close()

    def ensure_started(self) -> asyncio.AbstractEventLoop:
        """Ensure the background loop is running and return it."""
        if self._loop is None or not self._loop.is_running():
            if self._thread is not None and self._thread.is_alive():
                self._started.wait()
                if self._loop is not None:
                    return self._loop

            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="kuromi-browser-event-loop",
            )
            self._thread.start()
            self._started.wait()

        if self._loop is None:
            raise RuntimeError("Failed to start event loop")
        return self._loop

    def run_coroutine(
        self,
        coro: Awaitable[T],
        timeout: Optional[float] = None,
    ) -> T:
        """Run a coroutine and return the result.

        Args:
            coro: Coroutine to execute.
            timeout: Maximum time to wait in seconds.

        Returns:
            Coroutine result.
        """
        loop = self.ensure_started()

        # Check if we're already in the event loop thread
        if threading.current_thread() is self._thread:
            raise RuntimeError(
                "Cannot call sync wrapper from within the event loop thread"
            )

        # Check if there's already a running loop in this thread
        try:
            running_loop = asyncio.get_running_loop()
            if running_loop is not None:
                raise RuntimeError(
                    "Cannot use sync wrapper from within an async context. "
                    "Use 'await' directly instead."
                )
        except RuntimeError:
            # No running loop - this is expected for sync context
            pass

        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except asyncio.TimeoutError:
            future.cancel()
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

    def shutdown(self) -> None:
        """Shutdown the event loop."""
        if self._shutdown:
            return
        self._shutdown = True

        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)

    @classmethod
    def get_instance(cls) -> "EventLoopManager":
        """Get the singleton instance."""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (mainly for testing)."""
        if cls._instance is not None:
            cls._instance.shutdown()
            cls._instance = None


# Register cleanup on exit
atexit.register(lambda: EventLoopManager.get_instance().shutdown())


def get_event_loop_manager() -> EventLoopManager:
    """Get the global event loop manager."""
    return EventLoopManager.get_instance()


def run_sync(
    coro: Awaitable[T],
    timeout: Optional[float] = None,
) -> T:
    """Run an async coroutine synchronously.

    This is the main entry point for executing async code from sync contexts.

    Args:
        coro: Coroutine to execute.
        timeout: Maximum time to wait in seconds.

    Returns:
        Coroutine result.

    Example:
        result = run_sync(page.goto("https://example.com"))
    """
    return get_event_loop_manager().run_coroutine(coro, timeout)


# =============================================================================
# Sync Wrapper Decorator
# =============================================================================


def sync_method(
    timeout: Optional[float] = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., R]]:
    """Decorator to create a sync wrapper for an async method.

    Args:
        timeout: Default timeout for the operation.

    Example:
        class SyncPage:
            @sync_method(timeout=30)
            async def goto(self, url: str) -> None:
                await self._async_page.goto(url)
    """
    def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            coro = func(self, *args, **kwargs)
            return run_sync(coro, timeout=timeout)
        return wrapper
    return decorator


def make_sync(
    async_func: Callable[..., Awaitable[R]],
    timeout: Optional[float] = None,
) -> Callable[..., R]:
    """Convert an async function to a sync function.

    Args:
        async_func: Async function to wrap.
        timeout: Default timeout for operations.

    Returns:
        Sync version of the function.

    Example:
        async def fetch_data(url: str) -> str:
            ...

        fetch_data_sync = make_sync(fetch_data, timeout=30)
        result = fetch_data_sync("https://example.com")
    """
    @functools.wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        coro = async_func(*args, **kwargs)
        return run_sync(coro, timeout=timeout)
    return wrapper


# =============================================================================
# Sync Wrapper Classes
# =============================================================================


class SyncElement:
    """Synchronous wrapper for BaseElementCore.

    Provides a sync-compatible interface for element interactions.
    """

    def __init__(
        self,
        async_element: "BaseElementCore",
        default_timeout: float = 30.0,
    ) -> None:
        self._async = async_element
        self._timeout = default_timeout

    @property
    def tag_name(self) -> str:
        """Get the element's tag name."""
        return self._async.tag_name

    def get_attribute(self, name: str) -> Optional[str]:
        """Get an attribute value."""
        return run_sync(self._async.get_attribute(name), self._timeout)

    def get_property(self, name: str) -> Any:
        """Get a JavaScript property."""
        return run_sync(self._async.get_property(name), self._timeout)

    def text_content(self) -> Optional[str]:
        """Get the text content."""
        return run_sync(self._async.text_content(), self._timeout)

    def inner_text(self) -> str:
        """Get the inner text."""
        return run_sync(self._async.inner_text(), self._timeout)

    def inner_html(self) -> str:
        """Get the inner HTML."""
        return run_sync(self._async.inner_html(), self._timeout)

    def outer_html(self) -> str:
        """Get the outer HTML."""
        return run_sync(self._async.outer_html(), self._timeout)

    def bounding_box(self) -> Optional[dict[str, float]]:
        """Get the bounding box."""
        return run_sync(self._async.bounding_box(), self._timeout)

    def is_visible(self) -> bool:
        """Check if visible."""
        return run_sync(self._async.is_visible(), self._timeout)

    def is_enabled(self) -> bool:
        """Check if enabled."""
        return run_sync(self._async.is_enabled(), self._timeout)

    def is_checked(self) -> bool:
        """Check if checked."""
        return run_sync(self._async.is_checked(), self._timeout)

    def click(
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
        run_sync(
            self._async.click(
                button=button,
                click_count=click_count,
                delay=delay,
                force=force,
                modifiers=modifiers,
                position=position,
                timeout=timeout or self._timeout,
            ),
            timeout or self._timeout,
        )

    def fill(
        self,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill the element with text."""
        run_sync(
            self._async.fill(value, force=force, timeout=timeout or self._timeout),
            timeout or self._timeout,
        )

    def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into the element."""
        run_sync(
            self._async.type(text, delay=delay, timeout=timeout or self._timeout),
            timeout or self._timeout,
        )

    def hover(
        self,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over the element."""
        run_sync(
            self._async.hover(
                force=force,
                modifiers=modifiers,
                position=position,
                timeout=timeout or self._timeout,
            ),
            timeout or self._timeout,
        )

    def focus(self) -> None:
        """Focus the element."""
        run_sync(self._async.focus(), self._timeout)

    def scroll_into_view(self) -> None:
        """Scroll into view."""
        run_sync(self._async.scroll_into_view(), self._timeout)

    def query_selector(self, selector: str) -> Optional["SyncElement"]:
        """Find a child element."""
        result = run_sync(self._async.query_selector(selector), self._timeout)
        return SyncElement(result, self._timeout) if result else None

    def query_selector_all(self, selector: str) -> list["SyncElement"]:
        """Find all matching child elements."""
        results = run_sync(self._async.query_selector_all(selector), self._timeout)
        return [SyncElement(el, self._timeout) for el in results]


class SyncPage:
    """Synchronous wrapper for BasePageCore.

    Provides a sync-compatible interface for page interactions.
    """

    def __init__(
        self,
        async_page: "BasePageCore",
        default_timeout: float = 30.0,
    ) -> None:
        self._async = async_page
        self._timeout = default_timeout

    @property
    def url(self) -> str:
        """Get the current URL."""
        return self._async.url

    @property
    def title(self) -> str:
        """Get the page title."""
        return self._async.title

    def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
    ) -> Optional["NetworkResponse"]:
        """Navigate to a URL."""
        return run_sync(
            self._async.goto(
                url,
                timeout=timeout or self._timeout,
                wait_until=wait_until,
                referer=referer,
            ),
            timeout or self._timeout,
        )

    def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Reload the page."""
        return run_sync(
            self._async.reload(timeout=timeout or self._timeout, wait_until=wait_until),
            timeout or self._timeout,
        )

    def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate back."""
        return run_sync(
            self._async.go_back(timeout=timeout or self._timeout, wait_until=wait_until),
            timeout or self._timeout,
        )

    def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate forward."""
        return run_sync(
            self._async.go_forward(
                timeout=timeout or self._timeout, wait_until=wait_until
            ),
            timeout or self._timeout,
        )

    def content(self) -> str:
        """Get page HTML content."""
        return run_sync(self._async.content(), self._timeout)

    def query_selector(self, selector: str) -> Optional[SyncElement]:
        """Find an element."""
        result = run_sync(self._async.query_selector(selector), self._timeout)
        return SyncElement(result, self._timeout) if result else None

    def query_selector_all(self, selector: str) -> list[SyncElement]:
        """Find all matching elements."""
        results = run_sync(self._async.query_selector_all(selector), self._timeout)
        return [SyncElement(el, self._timeout) for el in results]

    def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[SyncElement]:
        """Wait for an element."""
        result = run_sync(
            self._async.wait_for_selector(
                selector, state=state, timeout=timeout or self._timeout
            ),
            timeout or self._timeout,
        )
        return SyncElement(result, self._timeout) if result else None

    def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for load state."""
        run_sync(
            self._async.wait_for_load_state(state, timeout=timeout or self._timeout),
            timeout or self._timeout,
        )

    def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Click an element."""
        element = self.wait_for_selector(selector, timeout=timeout)
        if element:
            element.click(
                button=button,
                click_count=click_count,
                delay=delay,
                force=force,
                timeout=timeout,
            )
        else:
            raise RuntimeError(f"Element not found: {selector}")

    def fill(
        self,
        selector: str,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill an input field."""
        element = self.wait_for_selector(selector, timeout=timeout)
        if element:
            element.fill(value, force=force, timeout=timeout)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text."""
        element = self.wait_for_selector(selector, timeout=timeout)
        if element:
            element.type(text, delay=delay, timeout=timeout)
        else:
            raise RuntimeError(f"Element not found: {selector}")

    def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript."""
        return run_sync(self._async.evaluate(expression, *args), self._timeout)

    def screenshot(
        self,
        *,
        path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict[str, float]] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take a screenshot."""
        return run_sync(
            self._async.screenshot(
                path=path,
                full_page=full_page,
                clip=clip,
                type=type,
                quality=quality,
                omit_background=omit_background,
            ),
            self._timeout,
        )

    def close(self) -> None:
        """Close the page."""
        run_sync(self._async.close(), self._timeout)

    def __enter__(self) -> "SyncPage":
        """Context manager entry."""
        run_sync(self._async.initialize(), self._timeout)
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        self.close()


# =============================================================================
# Utility Functions
# =============================================================================


def sync_wrapper(
    async_obj: T,
    default_timeout: float = 30.0,
) -> Union[SyncPage, SyncElement, T]:
    """Create an appropriate sync wrapper for an async object.

    Args:
        async_obj: Async object to wrap.
        default_timeout: Default timeout for operations.

    Returns:
        Sync wrapper for the object.
    """
    # Import here to avoid circular imports
    from kuromi_browser.core.base import BaseElementCore, BasePageCore

    if isinstance(async_obj, BasePageCore):
        return SyncPage(async_obj, default_timeout)
    elif isinstance(async_obj, BaseElementCore):
        return SyncElement(async_obj, default_timeout)
    else:
        return async_obj


class SyncContextManager(Generic[T]):
    """Generic sync context manager for async context managers.

    Allows async context managers to be used in sync code.
    """

    def __init__(
        self,
        async_cm: Any,
        timeout: float = 30.0,
    ) -> None:
        self._async_cm = async_cm
        self._timeout = timeout
        self._result: Optional[T] = None

    def __enter__(self) -> T:
        self._result = run_sync(self._async_cm.__aenter__(), self._timeout)
        return self._result

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        run_sync(
            self._async_cm.__aexit__(exc_type, exc_val, exc_tb),
            self._timeout,
        )


def sync_context(
    async_cm: Any,
    timeout: float = 30.0,
) -> SyncContextManager:
    """Create a sync context manager from an async one.

    Example:
        with sync_context(browser.new_page()) as page:
            page.goto("https://example.com")
    """
    return SyncContextManager(async_cm, timeout)


__all__ = [
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
