"""
Watchdogs module for kuromi-browser.

This module provides monitoring and health checks:
- ConnectionWatchdog: Monitor browser connection health
- TimeoutWatchdog: Handle operation timeouts
- ResourceWatchdog: Monitor memory/CPU usage
"""

import asyncio
from typing import Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class WatchdogState(str, Enum):
    """Watchdog state."""

    IDLE = "idle"
    RUNNING = "running"
    TRIGGERED = "triggered"
    STOPPED = "stopped"


@dataclass
class WatchdogEvent:
    """Event emitted by a watchdog."""

    watchdog_type: str
    state: WatchdogState
    message: str
    data: Optional[dict[str, Any]] = None


class BaseWatchdog:
    """Base class for watchdogs."""

    def __init__(
        self,
        name: str,
        callback: Optional[Callable[[WatchdogEvent], Any]] = None,
    ) -> None:
        self._name = name
        self._callback = callback
        self._state = WatchdogState.IDLE
        self._task: Optional[asyncio.Task[Any]] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> WatchdogState:
        return self._state

    async def start(self) -> None:
        """Start the watchdog."""
        self._state = WatchdogState.RUNNING

    async def stop(self) -> None:
        """Stop the watchdog."""
        self._state = WatchdogState.STOPPED
        if self._task:
            self._task.cancel()
            self._task = None

    async def reset(self) -> None:
        """Reset the watchdog."""
        self._state = WatchdogState.IDLE

    def _emit(self, event: WatchdogEvent) -> None:
        """Emit an event to the callback."""
        if self._callback:
            self._callback(event)


class ConnectionWatchdog(BaseWatchdog):
    """Monitors browser connection health.

    Triggers when the connection to the browser is lost or becomes
    unresponsive.
    """

    def __init__(
        self,
        ping_interval: float = 5.0,
        ping_timeout: float = 10.0,
        callback: Optional[Callable[[WatchdogEvent], Any]] = None,
    ) -> None:
        super().__init__("connection", callback)
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._last_pong: float = 0.0

    async def start(self) -> None:
        """Start monitoring connection."""
        await super().start()
        self._task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        """Monitor loop."""
        raise NotImplementedError

    async def ping(self) -> bool:
        """Send a ping to check connection."""
        raise NotImplementedError


class TimeoutWatchdog(BaseWatchdog):
    """Handles operation timeouts.

    Triggers when an operation exceeds its allotted time.
    """

    def __init__(
        self,
        timeout: float,
        callback: Optional[Callable[[WatchdogEvent], Any]] = None,
    ) -> None:
        super().__init__("timeout", callback)
        self._timeout = timeout

    async def start(self) -> None:
        """Start the timeout timer."""
        await super().start()
        self._task = asyncio.create_task(self._wait())

    async def _wait(self) -> None:
        """Wait for timeout."""
        try:
            await asyncio.sleep(self._timeout / 1000)
            self._state = WatchdogState.TRIGGERED
            self._emit(
                WatchdogEvent(
                    watchdog_type="timeout",
                    state=WatchdogState.TRIGGERED,
                    message=f"Operation timed out after {self._timeout}ms",
                )
            )
        except asyncio.CancelledError:
            pass


class ResourceWatchdog(BaseWatchdog):
    """Monitors system resource usage.

    Triggers when memory or CPU usage exceeds thresholds.
    """

    def __init__(
        self,
        memory_threshold_mb: float = 1024,
        cpu_threshold_percent: float = 90.0,
        check_interval: float = 10.0,
        callback: Optional[Callable[[WatchdogEvent], Any]] = None,
    ) -> None:
        super().__init__("resource", callback)
        self._memory_threshold = memory_threshold_mb
        self._cpu_threshold = cpu_threshold_percent
        self._check_interval = check_interval

    async def start(self) -> None:
        """Start monitoring resources."""
        await super().start()
        self._task = asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        """Monitor loop."""
        raise NotImplementedError

    async def get_usage(self) -> dict[str, float]:
        """Get current resource usage."""
        raise NotImplementedError


class WatchdogManager:
    """Manages multiple watchdogs."""

    def __init__(self) -> None:
        self._watchdogs: dict[str, BaseWatchdog] = {}

    def add(self, watchdog: BaseWatchdog) -> None:
        """Add a watchdog."""
        self._watchdogs[watchdog.name] = watchdog

    def remove(self, name: str) -> None:
        """Remove a watchdog by name."""
        if name in self._watchdogs:
            del self._watchdogs[name]

    def get(self, name: str) -> Optional[BaseWatchdog]:
        """Get a watchdog by name."""
        return self._watchdogs.get(name)

    async def start_all(self) -> None:
        """Start all watchdogs."""
        for watchdog in self._watchdogs.values():
            await watchdog.start()

    async def stop_all(self) -> None:
        """Stop all watchdogs."""
        for watchdog in self._watchdogs.values():
            await watchdog.stop()


__all__ = [
    "WatchdogState",
    "WatchdogEvent",
    "BaseWatchdog",
    "ConnectionWatchdog",
    "TimeoutWatchdog",
    "ResourceWatchdog",
    "WatchdogManager",
]
