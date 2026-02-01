"""
Timing plugin for kuromi-browser.

Tracks and reports timing metrics for browser operations.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from kuromi_browser.browser.hooks import HookPhase, HookContext
from kuromi_browser.plugins.base import (
    HookPlugin,
    PluginContext,
    PluginMetadata,
    PluginPriority,
    hook,
)

logger = logging.getLogger("kuromi_browser.plugins.timing")


@dataclass
class TimingMetric:
    """Individual timing metric."""

    name: str
    """Metric name."""

    start_time: float
    """Start timestamp."""

    end_time: Optional[float] = None
    """End timestamp."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    @property
    def is_complete(self) -> bool:
        """Check if timing is complete."""
        return self.end_time is not None

    def complete(self) -> float:
        """Mark timing as complete.

        Returns:
            Duration in milliseconds.
        """
        self.end_time = time.time()
        return self.duration_ms


@dataclass
class TimingStats:
    """Statistical summary of timing metrics."""

    name: str
    """Metric name."""

    count: int
    """Number of samples."""

    total_ms: float
    """Total time in milliseconds."""

    min_ms: float
    """Minimum time."""

    max_ms: float
    """Maximum time."""

    mean_ms: float
    """Mean time."""

    median_ms: float
    """Median time."""

    stdev_ms: float
    """Standard deviation."""

    p95_ms: float
    """95th percentile."""

    p99_ms: float
    """99th percentile."""

    def __str__(self) -> str:
        return (
            f"{self.name}: count={self.count}, "
            f"mean={self.mean_ms:.1f}ms, "
            f"min={self.min_ms:.1f}ms, "
            f"max={self.max_ms:.1f}ms, "
            f"p95={self.p95_ms:.1f}ms"
        )


@dataclass
class TimingConfig:
    """Configuration for timing plugin."""

    track_navigation: bool = True
    """Track page navigation timing."""

    track_requests: bool = True
    """Track network request timing."""

    track_actions: bool = True
    """Track user action timing."""

    track_lifecycle: bool = True
    """Track lifecycle event timing."""

    max_samples: int = 1000
    """Maximum samples to keep per metric."""

    report_interval: float = 0.0
    """Automatic reporting interval (0 = disabled)."""

    slow_threshold_ms: float = 5000.0
    """Threshold for slow operation warnings."""

    on_slow_operation: Optional[Callable[[TimingMetric], None]] = None
    """Callback for slow operations."""

    on_metric_complete: Optional[Callable[[TimingMetric], None]] = None
    """Callback when a metric completes."""


class TimingPlugin(HookPlugin):
    """Plugin that tracks timing metrics for browser operations.

    Provides detailed timing information for performance analysis
    and optimization.

    Example:
        plugin = TimingPlugin(TimingConfig(
            track_navigation=True,
            track_requests=True,
            slow_threshold_ms=3000,
        ))

        manager.load_plugin(plugin)

        # ... run browser operations ...

        # Get timing stats
        stats = plugin.get_stats("navigation")
        print(f"Navigation: {stats}")

        # Get all stats
        report = plugin.generate_report()
    """

    def __init__(self, config: Optional[TimingConfig] = None) -> None:
        """Initialize timing plugin.

        Args:
            config: Timing configuration.
        """
        super().__init__()
        self._config = config or TimingConfig()
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._active_timings: Dict[str, TimingMetric] = {}
        self._report_task: Optional[asyncio.Task] = None

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="timing",
            version="1.0.0",
            description="Timing metrics for browser operations",
            author="kuromi-browser",
            priority=PluginPriority.HIGH,
            tags=["builtin", "performance", "metrics"],
        )

    @property
    def config(self) -> TimingConfig:
        """Get timing configuration."""
        return self._config

    def _start_timing(
        self,
        name: str,
        key: str,
        metadata: Optional[dict] = None,
    ) -> TimingMetric:
        """Start a timing measurement.

        Args:
            name: Metric name.
            key: Unique key for this timing.
            metadata: Optional metadata.

        Returns:
            Timing metric.
        """
        metric = TimingMetric(
            name=name,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self._active_timings[key] = metric
        return metric

    def _end_timing(self, key: str) -> Optional[TimingMetric]:
        """End a timing measurement.

        Args:
            key: Timing key.

        Returns:
            Completed metric or None.
        """
        metric = self._active_timings.pop(key, None)
        if metric is None:
            return None

        duration = metric.complete()

        # Store the duration
        samples = self._metrics[metric.name]
        samples.append(duration)

        # Limit samples
        if len(samples) > self._config.max_samples:
            samples.pop(0)

        # Check for slow operation
        if duration > self._config.slow_threshold_ms:
            logger.warning(f"Slow operation: {metric.name} took {duration:.1f}ms")
            if self._config.on_slow_operation:
                self._config.on_slow_operation(metric)

        # Callback
        if self._config.on_metric_complete:
            self._config.on_metric_complete(metric)

        return metric

    def start_custom_timing(
        self,
        name: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Start a custom timing measurement.

        Args:
            name: Metric name.
            metadata: Optional metadata.

        Returns:
            Timing key to use with end_custom_timing.
        """
        key = f"custom:{name}:{time.time()}"
        self._start_timing(name, key, metadata)
        return key

    def end_custom_timing(self, key: str) -> Optional[float]:
        """End a custom timing measurement.

        Args:
            key: Timing key from start_custom_timing.

        Returns:
            Duration in milliseconds or None.
        """
        metric = self._end_timing(key)
        return metric.duration_ms if metric else None

    @hook(HookPhase.PAGE_NAVIGATE)
    async def on_page_navigate(self, ctx: HookContext) -> None:
        """Start navigation timing."""
        if self._config.track_navigation:
            url = ctx.data.get("url", "unknown")
            key = f"nav:{url}:{time.time()}"
            ctx.data["_timing_key"] = key
            self._start_timing("navigation", key, {"url": url})

    @hook(HookPhase.PAGE_LOAD)
    async def on_page_load(self, ctx: HookContext) -> None:
        """End navigation timing."""
        if self._config.track_navigation:
            key = ctx.data.get("_timing_key")
            if key:
                metric = self._end_timing(key)
                if metric:
                    ctx.data["load_time_ms"] = metric.duration_ms

    @hook(HookPhase.REQUEST_START)
    async def on_request_start(self, ctx: HookContext) -> None:
        """Start request timing."""
        if self._config.track_requests:
            request_id = ctx.data.get("request_id", str(time.time()))
            url = ctx.data.get("url", "unknown")
            resource_type = ctx.data.get("resource_type", "unknown")

            key = f"req:{request_id}"
            self._start_timing(
                f"request:{resource_type}",
                key,
                {"url": url, "resource_type": resource_type},
            )

            # Also track overall requests
            self._start_timing("request", f"req_all:{request_id}", {"url": url})

    @hook(HookPhase.REQUEST_COMPLETE)
    async def on_request_complete(self, ctx: HookContext) -> None:
        """End request timing."""
        if self._config.track_requests:
            request_id = ctx.data.get("request_id", "")
            if request_id:
                self._end_timing(f"req:{request_id}")
                metric = self._end_timing(f"req_all:{request_id}")
                if metric:
                    ctx.data["duration_ms"] = metric.duration_ms

    @hook(HookPhase.REQUEST_FAILED)
    async def on_request_failed(self, ctx: HookContext) -> None:
        """Clean up failed request timing."""
        if self._config.track_requests:
            request_id = ctx.data.get("request_id", "")
            if request_id:
                self._end_timing(f"req:{request_id}")
                self._end_timing(f"req_all:{request_id}")

    @hook(HookPhase.BROWSER_LAUNCH)
    async def on_browser_launch(self, ctx: HookContext) -> None:
        """Start browser launch timing."""
        if self._config.track_lifecycle:
            self._start_timing("browser_launch", "browser_launch")

    @hook(HookPhase.BROWSER_CONNECTED)
    async def on_browser_connected(self, ctx: HookContext) -> None:
        """End browser launch timing."""
        if self._config.track_lifecycle:
            metric = self._end_timing("browser_launch")
            if metric:
                ctx.data["launch_time_ms"] = metric.duration_ms

    @hook(HookPhase.CONTEXT_CREATED)
    async def on_context_created(self, ctx: HookContext) -> None:
        """Track context creation."""
        if self._config.track_lifecycle:
            # Record as instant metric
            self._metrics["context_created"].append(0)

    @hook(HookPhase.PAGE_CREATED)
    async def on_page_created(self, ctx: HookContext) -> None:
        """Track page creation."""
        if self._config.track_lifecycle:
            self._metrics["page_created"].append(0)

    def get_stats(self, name: str) -> Optional[TimingStats]:
        """Get timing statistics for a metric.

        Args:
            name: Metric name.

        Returns:
            Statistics or None if no data.
        """
        samples = self._metrics.get(name)
        if not samples:
            return None

        sorted_samples = sorted(samples)
        count = len(sorted_samples)

        return TimingStats(
            name=name,
            count=count,
            total_ms=sum(sorted_samples),
            min_ms=min(sorted_samples),
            max_ms=max(sorted_samples),
            mean_ms=statistics.mean(sorted_samples),
            median_ms=statistics.median(sorted_samples),
            stdev_ms=statistics.stdev(sorted_samples) if count > 1 else 0,
            p95_ms=sorted_samples[int(count * 0.95)] if count > 0 else 0,
            p99_ms=sorted_samples[int(count * 0.99)] if count > 0 else 0,
        )

    def get_all_stats(self) -> Dict[str, TimingStats]:
        """Get statistics for all metrics.

        Returns:
            Dictionary of metric name to statistics.
        """
        result = {}
        for name in self._metrics:
            stats = self.get_stats(name)
            if stats:
                result[name] = stats
        return result

    def generate_report(self) -> str:
        """Generate a timing report.

        Returns:
            Formatted report string.
        """
        lines = ["=== Timing Report ===", ""]

        all_stats = self.get_all_stats()
        if not all_stats:
            lines.append("No timing data collected.")
            return "\n".join(lines)

        # Group by category
        categories: Dict[str, List[TimingStats]] = defaultdict(list)
        for name, stats in all_stats.items():
            if ":" in name:
                category = name.split(":")[0]
            else:
                category = "general"
            categories[category].append(stats)

        for category, stats_list in sorted(categories.items()):
            lines.append(f"[{category.upper()}]")
            for stats in sorted(stats_list, key=lambda s: s.name):
                lines.append(f"  {stats}")
            lines.append("")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all timing data."""
        self._metrics.clear()
        self._active_timings.clear()

    async def on_enable(self) -> None:
        """Start automatic reporting if configured."""
        if self._config.report_interval > 0:
            self._report_task = asyncio.create_task(self._auto_report())

    async def on_disable(self) -> None:
        """Stop automatic reporting."""
        if self._report_task:
            self._report_task.cancel()
            try:
                await self._report_task
            except asyncio.CancelledError:
                pass
            self._report_task = None

    async def _auto_report(self) -> None:
        """Automatic reporting task."""
        while True:
            await asyncio.sleep(self._config.report_interval)
            logger.info(self.generate_report())

    async def on_destroy(self) -> None:
        """Clean up timing data."""
        await self.on_disable()
        self.clear()


__all__ = ["TimingPlugin", "TimingConfig", "TimingMetric", "TimingStats"]
