"""
Middleware chain for kuromi-browser plugins.

Provides a middleware pipeline for processing requests and responses
through multiple plugins in order.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar

from .base import MiddlewarePlugin, PluginPriority

logger = logging.getLogger(__name__)

# Generic types for request/response
Req = TypeVar("Req")
Res = TypeVar("Res")


@dataclass
class MiddlewareContext(Generic[Req]):
    """Context passed through the middleware chain."""

    request: Req
    """The request being processed."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Metadata that can be modified by middleware."""

    cancelled: bool = False
    """Set to True to cancel the request."""

    error: Optional[Exception] = None
    """Error if processing failed."""

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the request.

        Args:
            reason: Optional cancellation reason.
        """
        self.cancelled = True
        if reason:
            self.metadata["cancel_reason"] = reason


@dataclass
class MiddlewareResult(Generic[Res]):
    """Result from middleware chain processing."""

    response: Optional[Res] = None
    """The response if successful."""

    error: Optional[Exception] = None
    """Error if processing failed."""

    cancelled: bool = False
    """True if request was cancelled."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Accumulated metadata from middleware."""

    @property
    def success(self) -> bool:
        """Check if processing was successful."""
        return self.response is not None and not self.error and not self.cancelled


class MiddlewareChain(Generic[Req, Res]):
    """Manages a chain of middleware plugins.

    Middleware is executed in priority order (highest first) for requests,
    and reverse order for responses.

    Example:
        chain = MiddlewareChain()

        # Add middleware
        chain.add(auth_middleware)
        chain.add(logging_middleware)
        chain.add(retry_middleware)

        # Process request
        result = await chain.process(request, final_handler)

        if result.success:
            print(f"Response: {result.response}")
    """

    def __init__(self) -> None:
        """Initialize middleware chain."""
        self._middleware: list[MiddlewarePlugin] = []
        self._sorted = True

    def add(self, middleware: MiddlewarePlugin) -> "MiddlewareChain[Req, Res]":
        """Add middleware to the chain.

        Args:
            middleware: Middleware plugin to add.

        Returns:
            Self for chaining.
        """
        self._middleware.append(middleware)
        self._sorted = False
        return self

    def remove(self, middleware: MiddlewarePlugin) -> bool:
        """Remove middleware from the chain.

        Args:
            middleware: Middleware to remove.

        Returns:
            True if removed.
        """
        if middleware in self._middleware:
            self._middleware.remove(middleware)
            return True
        return False

    def remove_by_name(self, name: str) -> int:
        """Remove middleware by plugin name.

        Args:
            name: Plugin name to remove.

        Returns:
            Number of middleware removed.
        """
        to_remove = [m for m in self._middleware if m.name == name]
        for m in to_remove:
            self._middleware.remove(m)
        return len(to_remove)

    def clear(self) -> None:
        """Clear all middleware."""
        self._middleware.clear()

    def _ensure_sorted(self) -> None:
        """Ensure middleware is sorted by priority."""
        if not self._sorted:
            self._middleware.sort(key=lambda m: -m.metadata.priority)
            self._sorted = True

    async def process(
        self,
        request: Req,
        final_handler: Callable[[Req], Res],
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MiddlewareResult[Res]:
        """Process a request through the middleware chain.

        Args:
            request: Request to process.
            final_handler: Handler called after all middleware.
            metadata: Optional initial metadata.

        Returns:
            Result containing response or error.
        """
        self._ensure_sorted()

        ctx = MiddlewareContext(
            request=request,
            metadata=metadata or {},
        )

        result = MiddlewareResult[Res](metadata=ctx.metadata)

        if not self._middleware:
            # No middleware, call handler directly
            try:
                response = final_handler(request)
                if asyncio.iscoroutine(response):
                    response = await response
                result.response = response
            except Exception as e:
                result.error = e
                logger.error(f"Final handler error: {e}")
            return result

        # Build chain from inside out
        async def build_chain(index: int) -> Callable[[Req], Res]:
            if index >= len(self._middleware):
                # End of chain, call final handler
                async def final(req: Req) -> Res:
                    if ctx.cancelled:
                        raise RuntimeError(
                            f"Request cancelled: {ctx.metadata.get('cancel_reason', 'unknown')}"
                        )
                    response = final_handler(req)
                    if asyncio.iscoroutine(response):
                        response = await response
                    return response

                return final

            middleware = self._middleware[index]
            next_handler = await build_chain(index + 1)

            async def handler(req: Req) -> Res:
                if not middleware.is_enabled:
                    return await next_handler(req)

                try:
                    response = await middleware.process_request(req, next_handler)
                    # Process response through middleware
                    response = await middleware.process_response(response, req)
                    return response
                except Exception as e:
                    logger.error(f"Middleware {middleware.name} error: {e}")
                    raise

            return handler

        try:
            chain = await build_chain(0)
            result.response = await chain(request)
        except Exception as e:
            result.error = e
            if ctx.cancelled:
                result.cancelled = True

        return result

    def __len__(self) -> int:
        """Number of middleware in chain."""
        return len(self._middleware)

    def __iter__(self):
        """Iterate over middleware."""
        self._ensure_sorted()
        return iter(self._middleware)


class MiddlewareBuilder:
    """Builder for creating middleware from functions.

    Example:
        middleware = (
            MiddlewareBuilder("my-middleware")
            .on_request(lambda req, next: next(req))
            .on_response(lambda res, req: res)
            .with_priority(PluginPriority.HIGH)
            .build()
        )
    """

    def __init__(self, name: str) -> None:
        """Initialize builder.

        Args:
            name: Middleware name.
        """
        self._name = name
        self._version = "1.0.0"
        self._description = ""
        self._priority = PluginPriority.NORMAL
        self._request_handler: Optional[Callable] = None
        self._response_handler: Optional[Callable] = None

    def with_version(self, version: str) -> "MiddlewareBuilder":
        """Set version.

        Args:
            version: Version string.

        Returns:
            Self for chaining.
        """
        self._version = version
        return self

    def with_description(self, description: str) -> "MiddlewareBuilder":
        """Set description.

        Args:
            description: Description text.

        Returns:
            Self for chaining.
        """
        self._description = description
        return self

    def with_priority(self, priority: int) -> "MiddlewareBuilder":
        """Set priority.

        Args:
            priority: Priority value.

        Returns:
            Self for chaining.
        """
        self._priority = priority
        return self

    def on_request(
        self, handler: Callable[[Any, Callable], Any]
    ) -> "MiddlewareBuilder":
        """Set request handler.

        Args:
            handler: Function(request, next_handler) -> response.

        Returns:
            Self for chaining.
        """
        self._request_handler = handler
        return self

    def on_response(
        self, handler: Callable[[Any, Any], Any]
    ) -> "MiddlewareBuilder":
        """Set response handler.

        Args:
            handler: Function(response, request) -> response.

        Returns:
            Self for chaining.
        """
        self._response_handler = handler
        return self

    def build(self) -> MiddlewarePlugin:
        """Build the middleware plugin.

        Returns:
            Configured middleware plugin.
        """
        from .base import PluginMetadata

        name = self._name
        version = self._version
        description = self._description
        priority = self._priority
        request_handler = self._request_handler
        response_handler = self._response_handler

        class FunctionalMiddleware(MiddlewarePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name=name,
                    version=version,
                    description=description,
                    priority=priority,
                )

            async def process_request(self, request: Any, next_handler: Callable) -> Any:
                if request_handler:
                    result = request_handler(request, next_handler)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                return await next_handler(request)

            async def process_response(self, response: Any, request: Any) -> Any:
                if response_handler:
                    result = response_handler(response, request)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                return response

        return FunctionalMiddleware()


def middleware(
    name: str,
    *,
    priority: int = PluginPriority.NORMAL,
) -> Callable:
    """Decorator to create middleware from a function.

    Args:
        name: Middleware name.
        priority: Middleware priority.

    Returns:
        Decorator function.

    Example:
        @middleware("auth", priority=PluginPriority.HIGH)
        async def auth_middleware(request, next_handler):
            request.headers["Auth"] = "token"
            return await next_handler(request)
    """

    def decorator(func: Callable) -> MiddlewarePlugin:
        return (
            MiddlewareBuilder(name)
            .with_priority(priority)
            .on_request(func)
            .build()
        )

    return decorator


__all__ = [
    "MiddlewareChain",
    "MiddlewareContext",
    "MiddlewareResult",
    "MiddlewareBuilder",
    "middleware",
]
