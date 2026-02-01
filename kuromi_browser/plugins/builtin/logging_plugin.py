"""
Logging plugin for kuromi-browser.

Provides comprehensive logging for browser operations, requests,
and lifecycle events.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from kuromi_browser.browser.hooks import HookPhase, HookContext
from kuromi_browser.plugins.base import (
    HookPlugin,
    PluginContext,
    PluginMetadata,
    PluginPriority,
    hook,
)

logger = logging.getLogger("kuromi_browser.plugins.logging")


@dataclass
class LoggingConfig:
    """Configuration for the logging plugin."""

    log_level: int = logging.INFO
    """Default log level."""

    log_navigation: bool = True
    """Log page navigation events."""

    log_requests: bool = True
    """Log network requests."""

    log_responses: bool = False
    """Log network responses (verbose)."""

    log_lifecycle: bool = True
    """Log browser lifecycle events."""

    log_errors: bool = True
    """Log errors and exceptions."""

    log_console: bool = False
    """Log browser console messages."""

    include_headers: bool = False
    """Include headers in request/response logs."""

    include_body: bool = False
    """Include body in request/response logs (very verbose)."""

    max_body_length: int = 500
    """Maximum body length to log."""

    format_json: bool = True
    """Pretty-print JSON data."""

    custom_formatter: Optional[Callable[[str, dict], str]] = None
    """Custom log formatter function."""


class LoggingPlugin(HookPlugin):
    """Plugin that logs browser operations and events.

    Provides detailed logging for debugging and monitoring browser
    automation workflows.

    Example:
        plugin = LoggingPlugin(LoggingConfig(
            log_level=logging.DEBUG,
            log_requests=True,
            log_responses=True,
        ))

        manager.load_plugin(plugin)
    """

    def __init__(self, config: Optional[LoggingConfig] = None) -> None:
        """Initialize logging plugin.

        Args:
            config: Logging configuration.
        """
        super().__init__()
        self._config = config or LoggingConfig()
        self._request_times: dict[str, float] = {}

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="logging",
            version="1.0.0",
            description="Comprehensive logging for browser operations",
            author="kuromi-browser",
            priority=PluginPriority.HIGHEST,  # Run first to capture all events
            tags=["builtin", "logging", "debug"],
        )

    @property
    def config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self._config

    def _log(self, level: int, message: str, data: Optional[dict] = None) -> None:
        """Log a message with optional data.

        Args:
            level: Log level.
            message: Log message.
            data: Optional data to include.
        """
        if self._config.custom_formatter and data:
            message = self._config.custom_formatter(message, data)
        elif data:
            import json
            if self._config.format_json:
                try:
                    data_str = json.dumps(data, indent=2, default=str)
                except Exception:
                    data_str = str(data)
            else:
                data_str = str(data)
            message = f"{message}\n{data_str}"

        logger.log(level, message)

    @hook(HookPhase.BROWSER_LAUNCH)
    async def on_browser_launch(self, ctx: HookContext) -> None:
        """Log browser launch."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[BROWSER] Launching browser",
                ctx.data,
            )

    @hook(HookPhase.BROWSER_CONNECTED)
    async def on_browser_connected(self, ctx: HookContext) -> None:
        """Log browser connected."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[BROWSER] Connected",
                ctx.data,
            )

    @hook(HookPhase.BROWSER_DISCONNECTED)
    async def on_browser_disconnected(self, ctx: HookContext) -> None:
        """Log browser disconnected."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[BROWSER] Disconnected",
                ctx.data,
            )

    @hook(HookPhase.BROWSER_CLOSE)
    async def on_browser_close(self, ctx: HookContext) -> None:
        """Log browser close."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[BROWSER] Closing",
                ctx.data,
            )

    @hook(HookPhase.CONTEXT_CREATED)
    async def on_context_created(self, ctx: HookContext) -> None:
        """Log context created."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[CONTEXT] Created",
                ctx.data,
            )

    @hook(HookPhase.CONTEXT_CLOSE)
    async def on_context_close(self, ctx: HookContext) -> None:
        """Log context close."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[CONTEXT] Closing",
                ctx.data,
            )

    @hook(HookPhase.PAGE_CREATED)
    async def on_page_created(self, ctx: HookContext) -> None:
        """Log page created."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[PAGE] Created",
                ctx.data,
            )

    @hook(HookPhase.PAGE_NAVIGATE)
    async def on_page_navigate(self, ctx: HookContext) -> None:
        """Log page navigation."""
        if self._config.log_navigation:
            url = ctx.data.get("url", "unknown")
            self._log(
                self._config.log_level,
                f"[NAVIGATE] {url}",
                {"url": url} if self._config.log_level <= logging.DEBUG else None,
            )

    @hook(HookPhase.PAGE_LOAD)
    async def on_page_load(self, ctx: HookContext) -> None:
        """Log page load."""
        if self._config.log_navigation:
            url = ctx.data.get("url", "unknown")
            title = ctx.data.get("title", "")
            load_time = ctx.data.get("load_time_ms", 0)
            self._log(
                self._config.log_level,
                f"[LOADED] {url} - {title} ({load_time:.0f}ms)",
            )

    @hook(HookPhase.PAGE_CLOSE)
    async def on_page_close(self, ctx: HookContext) -> None:
        """Log page close."""
        if self._config.log_lifecycle:
            self._log(
                self._config.log_level,
                "[PAGE] Closed",
                ctx.data,
            )

    @hook(HookPhase.REQUEST_START)
    async def on_request_start(self, ctx: HookContext) -> None:
        """Log request start."""
        if self._config.log_requests:
            url = ctx.data.get("url", "unknown")
            method = ctx.data.get("method", "GET")
            request_id = ctx.data.get("request_id", "")

            # Track timing
            if request_id:
                self._request_times[request_id] = time.time()

            log_data = None
            if self._config.log_level <= logging.DEBUG:
                log_data = {"method": method, "url": url}
                if self._config.include_headers:
                    log_data["headers"] = ctx.data.get("headers", {})

            self._log(
                self._config.log_level,
                f"[REQUEST] {method} {url}",
                log_data,
            )

    @hook(HookPhase.REQUEST_COMPLETE)
    async def on_request_complete(self, ctx: HookContext) -> None:
        """Log request complete."""
        if self._config.log_responses:
            url = ctx.data.get("url", "unknown")
            status = ctx.data.get("status", 0)
            request_id = ctx.data.get("request_id", "")

            # Calculate duration
            duration = 0.0
            if request_id and request_id in self._request_times:
                duration = (time.time() - self._request_times.pop(request_id)) * 1000

            status_emoji = "+" if 200 <= status < 300 else "-"

            log_data = None
            if self._config.log_level <= logging.DEBUG:
                log_data = {"status": status, "duration_ms": duration}
                if self._config.include_headers:
                    log_data["headers"] = ctx.data.get("headers", {})

            self._log(
                self._config.log_level,
                f"[RESPONSE] [{status_emoji}{status}] {url} ({duration:.0f}ms)",
                log_data,
            )

    @hook(HookPhase.REQUEST_FAILED)
    async def on_request_failed(self, ctx: HookContext) -> None:
        """Log request failure."""
        if self._config.log_errors:
            url = ctx.data.get("url", "unknown")
            error = ctx.data.get("error", "unknown error")
            request_id = ctx.data.get("request_id", "")

            # Clean up timing
            if request_id:
                self._request_times.pop(request_id, None)

            self._log(
                logging.ERROR,
                f"[REQUEST FAILED] {url}: {error}",
            )

    @hook(HookPhase.PAGE_ERROR)
    async def on_page_error(self, ctx: HookContext) -> None:
        """Log page errors."""
        if self._config.log_errors:
            message = ctx.data.get("message", "unknown error")
            stack = ctx.data.get("stack", "")

            self._log(
                logging.ERROR,
                f"[PAGE ERROR] {message}",
                {"stack": stack} if stack else None,
            )

    @hook(HookPhase.CONSOLE_MESSAGE)
    async def on_console_message(self, ctx: HookContext) -> None:
        """Log console messages."""
        if self._config.log_console:
            msg_type = ctx.data.get("type", "log")
            text = ctx.data.get("text", "")

            level_map = {
                "log": logging.INFO,
                "info": logging.INFO,
                "warn": logging.WARNING,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "debug": logging.DEBUG,
            }
            level = level_map.get(msg_type, logging.INFO)

            self._log(
                level,
                f"[CONSOLE:{msg_type.upper()}] {text}",
            )

    @hook(HookPhase.DIALOG_OPENED)
    async def on_dialog_opened(self, ctx: HookContext) -> None:
        """Log dialog events."""
        if self._config.log_lifecycle:
            dialog_type = ctx.data.get("type", "unknown")
            message = ctx.data.get("message", "")

            self._log(
                self._config.log_level,
                f"[DIALOG:{dialog_type.upper()}] {message}",
            )

    async def on_enable(self) -> None:
        """Configure logger when enabled."""
        logger.setLevel(self._config.log_level)

    async def on_destroy(self) -> None:
        """Clean up request times."""
        self._request_times.clear()


__all__ = ["LoggingPlugin", "LoggingConfig"]
