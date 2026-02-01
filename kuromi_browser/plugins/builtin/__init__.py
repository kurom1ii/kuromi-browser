"""
Built-in plugins for kuromi-browser.

Provides common functionality plugins out of the box.
"""

from .logging_plugin import LoggingPlugin
from .timing_plugin import TimingPlugin
from .retry_plugin import RetryPlugin

__all__ = [
    "LoggingPlugin",
    "TimingPlugin",
    "RetryPlugin",
]
