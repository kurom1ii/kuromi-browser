"""
Retry plugin for kuromi-browser.

Provides automatic retry functionality for failed operations.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Set, Type

from kuromi_browser.browser.hooks import HookPhase, HookContext
from kuromi_browser.plugins.base import (
    MiddlewarePlugin,
    PluginContext,
    PluginMetadata,
    PluginPriority,
)

logger = logging.getLogger("kuromi_browser.plugins.retry")


class BackoffStrategy(str, Enum):
    """Backoff strategies for retry delays."""

    FIXED = "fixed"
    """Fixed delay between retries."""

    LINEAR = "linear"
    """Linearly increasing delay."""

    EXPONENTIAL = "exponential"
    """Exponentially increasing delay."""

    JITTER = "jitter"
    """Exponential with random jitter."""


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    """Maximum number of retry attempts."""

    initial_delay: float = 1.0
    """Initial delay in seconds."""

    max_delay: float = 30.0
    """Maximum delay between retries."""

    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    """Backoff strategy."""

    backoff_factor: float = 2.0
    """Factor for exponential/linear backoff."""

    jitter_range: float = 0.5
    """Random jitter range (0-1)."""

    retry_on_status: Set[int] = field(default_factory=lambda: {429, 500, 502, 503, 504})
    """HTTP status codes that trigger retry."""

    retry_on_exceptions: tuple[Type[Exception], ...] = field(
        default_factory=lambda: (TimeoutError, ConnectionError)
    )
    """Exception types that trigger retry."""

    retry_on_navigation: bool = True
    """Retry failed navigation."""

    retry_on_request: bool = True
    """Retry failed requests."""

    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    """Callback on retry: (attempt, error, delay)."""

    should_retry: Optional[Callable[[Any, Exception], bool]] = None
    """Custom function to determine if should retry."""


@dataclass
class RetryState:
    """State for tracking retry attempts."""

    attempts: int = 0
    """Number of attempts made."""

    last_error: Optional[Exception] = None
    """Last error encountered."""

    total_delay: float = 0.0
    """Total delay accumulated."""


class RetryPlugin(MiddlewarePlugin):
    """Plugin that provides automatic retry functionality.

    Automatically retries failed operations with configurable
    backoff strategies.

    Example:
        plugin = RetryPlugin(RetryConfig(
            max_retries=3,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retry_on_status={500, 502, 503},
        ))

        manager.load_plugin(plugin)
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        """Initialize retry plugin.

        Args:
            config: Retry configuration.
        """
        super().__init__()
        self._config = config or RetryConfig()
        self._retry_states: dict[str, RetryState] = {}

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="retry",
            version="1.0.0",
            description="Automatic retry with backoff for failed operations",
            author="kuromi-browser",
            priority=PluginPriority.LOW,  # Run after other middleware
            tags=["builtin", "reliability", "retry"],
        )

    @property
    def config(self) -> RetryConfig:
        """Get retry configuration."""
        return self._config

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt.

        Args:
            attempt: Current attempt number (1-based).

        Returns:
            Delay in seconds.
        """
        strategy = self._config.backoff_strategy
        initial = self._config.initial_delay
        factor = self._config.backoff_factor
        max_delay = self._config.max_delay

        if strategy == BackoffStrategy.FIXED:
            delay = initial
        elif strategy == BackoffStrategy.LINEAR:
            delay = initial * attempt
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay = initial * (factor ** (attempt - 1))
        elif strategy == BackoffStrategy.JITTER:
            base_delay = initial * (factor ** (attempt - 1))
            jitter = random.uniform(
                -self._config.jitter_range,
                self._config.jitter_range,
            )
            delay = base_delay * (1 + jitter)
        else:
            delay = initial

        return min(delay, max_delay)

    def _should_retry(
        self,
        state: RetryState,
        error: Optional[Exception] = None,
        status_code: Optional[int] = None,
    ) -> bool:
        """Determine if operation should be retried.

        Args:
            state: Current retry state.
            error: Exception that occurred.
            status_code: HTTP status code if applicable.

        Returns:
            True if should retry.
        """
        # Check max retries
        if state.attempts >= self._config.max_retries:
            return False

        # Custom retry function
        if self._config.should_retry and error:
            return self._config.should_retry(None, error)

        # Check status code
        if status_code and status_code in self._config.retry_on_status:
            return True

        # Check exception type
        if error and isinstance(error, self._config.retry_on_exceptions):
            return True

        return False

    async def _do_retry(
        self,
        key: str,
        operation: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute operation with retry logic.

        Args:
            key: Unique key for this operation.
            operation: Async function to execute.
            *args: Arguments for operation.
            **kwargs: Keyword arguments for operation.

        Returns:
            Operation result.

        Raises:
            Exception: If all retries fail.
        """
        state = self._retry_states.get(key)
        if state is None:
            state = RetryState()
            self._retry_states[key] = state

        last_error: Optional[Exception] = None

        while True:
            state.attempts += 1

            try:
                result = operation(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result

                # Success - clean up state
                del self._retry_states[key]
                return result

            except Exception as e:
                last_error = e
                state.last_error = e

                if not self._should_retry(state, error=e):
                    del self._retry_states[key]
                    raise

                # Calculate delay
                delay = self._calculate_delay(state.attempts)
                state.total_delay += delay

                # Callback
                if self._config.on_retry:
                    self._config.on_retry(state.attempts, e, delay)

                logger.warning(
                    f"Retry {state.attempts}/{self._config.max_retries} "
                    f"after {delay:.1f}s: {e}"
                )

                await asyncio.sleep(delay)

    async def process_request(
        self,
        request: Any,
        next_handler: Callable,
    ) -> Any:
        """Process request with retry support.

        Args:
            request: The request to process.
            next_handler: Next handler in chain.

        Returns:
            Response from handler.
        """
        if not self._config.retry_on_request:
            return await next_handler(request)

        # Generate unique key for this request
        request_id = getattr(request, "id", None) or id(request)
        key = f"request:{request_id}"

        return await self._do_retry(key, next_handler, request)

    async def setup(self, ctx: PluginContext) -> None:
        """Setup retry hooks."""
        await super().setup(ctx)

        if ctx.hook_manager and self._config.retry_on_navigation:
            # Register hook for navigation retry
            self.register_hook(
                HookPhase.PAGE_NAVIGATE,
                self._on_navigate,
                priority=PluginPriority.LOWEST,
            )

    async def _on_navigate(self, ctx: HookContext) -> None:
        """Handle navigation with retry support."""
        # Navigation retry is handled at a higher level
        # This hook is mainly for tracking/logging
        pass

    async def on_destroy(self) -> None:
        """Clean up retry states."""
        self._retry_states.clear()


def with_retry(
    max_retries: int = 3,
    *,
    delay: float = 1.0,
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator to add retry behavior to a function.

    Args:
        max_retries: Maximum retry attempts.
        delay: Initial delay in seconds.
        backoff: Backoff strategy.
        exceptions: Exception types to retry on.

    Returns:
        Decorator function.

    Example:
        @with_retry(max_retries=3, delay=1.0)
        async def fetch_data():
            # May fail and be retried
            pass
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = RetryConfig(
                max_retries=max_retries,
                initial_delay=delay,
                backoff_strategy=backoff,
                retry_on_exceptions=exceptions,
            )

            plugin = RetryPlugin(config)
            await plugin.initialize(PluginContext())
            await plugin.enable()

            try:
                return await plugin._do_retry(
                    f"decorated:{id(func)}",
                    func,
                    *args,
                    **kwargs,
                )
            finally:
                await plugin.destroy()

        return wrapper

    return decorator


class RetryContext:
    """Context manager for retry operations.

    Example:
        async with RetryContext(max_retries=3) as retry:
            result = await retry.execute(my_async_func, arg1, arg2)
    """

    def __init__(
        self,
        max_retries: int = 3,
        **config_kwargs: Any,
    ) -> None:
        """Initialize retry context.

        Args:
            max_retries: Maximum retry attempts.
            **config_kwargs: Additional config options.
        """
        self._config = RetryConfig(max_retries=max_retries, **config_kwargs)
        self._plugin = RetryPlugin(self._config)

    async def __aenter__(self) -> "RetryContext":
        """Enter context."""
        await self._plugin.initialize(PluginContext())
        await self._plugin.enable()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit context."""
        await self._plugin.destroy()

    async def execute(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry.

        Args:
            func: Function to execute.
            *args: Function arguments.
            **kwargs: Function keyword arguments.

        Returns:
            Function result.
        """
        return await self._plugin._do_retry(
            f"context:{id(func)}",
            func,
            *args,
            **kwargs,
        )


__all__ = [
    "RetryPlugin",
    "RetryConfig",
    "RetryState",
    "BackoffStrategy",
    "with_retry",
    "RetryContext",
]
