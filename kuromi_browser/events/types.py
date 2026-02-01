"""
Typed events for kuromi-browser.

Provides strongly-typed event classes for different operations.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List

from .bus import Event, EventType


# Navigation Events

@dataclass
class NavigateEvent(Event):
    """Event emitted when navigation occurs."""

    type: EventType = field(default=EventType.NAVIGATE)
    url: str = ""
    status_code: Optional[int] = None
    redirect_chain: List[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {"url": self.url, "status_code": self.status_code}


@dataclass
class PageLoadedEvent(Event):
    """Event emitted when page is fully loaded."""

    type: EventType = field(default=EventType.PAGE_LOADED)
    url: str = ""
    title: str = ""
    load_time_ms: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "url": self.url,
                "title": self.title,
                "load_time_ms": self.load_time_ms,
            }


# DOM Events

@dataclass
class DOMReadyEvent(Event):
    """Event emitted when DOM is ready."""

    type: EventType = field(default=EventType.DOM_READY)
    url: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {"url": self.url}


@dataclass
class ElementFoundEvent(Event):
    """Event emitted when an element is found."""

    type: EventType = field(default=EventType.ELEMENT_FOUND)
    selector: str = ""
    tag_name: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "selector": self.selector,
                "tag_name": self.tag_name,
                "attributes": self.attributes,
            }


# Network Events

@dataclass
class RequestEvent(Event):
    """Event emitted when a network request is made."""

    type: EventType = field(default=EventType.REQUEST)
    url: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    resource_type: str = ""
    request_id: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "url": self.url,
                "method": self.method,
                "headers": self.headers,
                "resource_type": self.resource_type,
                "request_id": self.request_id,
            }


@dataclass
class ResponseEvent(Event):
    """Event emitted when a network response is received."""

    type: EventType = field(default=EventType.RESPONSE)
    url: str = ""
    status: int = 0
    status_text: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "url": self.url,
                "status": self.status,
                "status_text": self.status_text,
                "headers": self.headers,
                "request_id": self.request_id,
            }


# Action Events

@dataclass
class ClickEvent(Event):
    """Event emitted when a click action occurs."""

    type: EventType = field(default=EventType.CLICK)
    selector: str = ""
    x: float = 0.0
    y: float = 0.0
    button: str = "left"
    click_count: int = 1

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "selector": self.selector,
                "x": self.x,
                "y": self.y,
                "button": self.button,
                "click_count": self.click_count,
            }


@dataclass
class TypeEvent(Event):
    """Event emitted when text is typed."""

    type: EventType = field(default=EventType.TYPE)
    selector: str = ""
    text: str = ""
    delay_ms: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "selector": self.selector,
                "text": self.text,
                "delay_ms": self.delay_ms,
            }


@dataclass
class ScrollEvent(Event):
    """Event emitted when scrolling occurs."""

    type: EventType = field(default=EventType.SCROLL)
    x: float = 0.0
    y: float = 0.0
    delta_x: float = 0.0
    delta_y: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "x": self.x,
                "y": self.y,
                "delta_x": self.delta_x,
                "delta_y": self.delta_y,
            }


@dataclass
class HoverEvent(Event):
    """Event emitted when hovering over an element."""

    type: EventType = field(default=EventType.HOVER)
    selector: str = ""
    x: float = 0.0
    y: float = 0.0

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "selector": self.selector,
                "x": self.x,
                "y": self.y,
            }


@dataclass
class ScreenshotEvent(Event):
    """Event emitted when a screenshot is taken."""

    type: EventType = field(default=EventType.SCREENSHOT)
    path: str = ""
    full_page: bool = False
    format: str = "png"

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "path": self.path,
                "full_page": self.full_page,
                "format": self.format,
            }


# Lifecycle Events

@dataclass
class BrowserStartedEvent(Event):
    """Event emitted when browser starts."""

    type: EventType = field(default=EventType.BROWSER_STARTED)
    browser_type: str = ""
    headless: bool = True
    pid: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "browser_type": self.browser_type,
                "headless": self.headless,
                "pid": self.pid,
            }


@dataclass
class BrowserClosedEvent(Event):
    """Event emitted when browser closes."""

    type: EventType = field(default=EventType.BROWSER_CLOSED)
    browser_type: str = ""
    reason: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "browser_type": self.browser_type,
                "reason": self.reason,
            }


@dataclass
class ContextCreatedEvent(Event):
    """Event emitted when a browser context is created."""

    type: EventType = field(default=EventType.CONTEXT_CREATED)
    context_id: str = ""
    incognito: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "context_id": self.context_id,
                "incognito": self.incognito,
            }


@dataclass
class ConsoleEvent(Event):
    """Event emitted for console messages."""

    type: EventType = field(default=EventType.PAGE_CONSOLE)
    message_type: str = ""
    text: str = ""
    args: List[Any] = field(default_factory=list)
    location: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "message_type": self.message_type,
                "text": self.text,
                "args": self.args,
                "location": self.location,
            }


@dataclass
class DialogEvent(Event):
    """Event emitted when a dialog appears."""

    type: EventType = field(default=EventType.PAGE_DIALOG)
    dialog_type: str = ""
    message: str = ""
    default_value: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "dialog_type": self.dialog_type,
                "message": self.message,
                "default_value": self.default_value,
            }


@dataclass
class ErrorEvent(Event):
    """Event emitted when an error occurs."""

    type: EventType = field(default=EventType.PAGE_ERROR)
    message: str = ""
    stack: str = ""
    name: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.data is None:
            self.data = {
                "message": self.message,
                "stack": self.stack,
                "name": self.name,
            }


__all__ = [
    # Navigation
    "NavigateEvent",
    "PageLoadedEvent",
    # DOM
    "DOMReadyEvent",
    "ElementFoundEvent",
    # Network
    "RequestEvent",
    "ResponseEvent",
    # Actions
    "ClickEvent",
    "TypeEvent",
    "ScrollEvent",
    "HoverEvent",
    "ScreenshotEvent",
    # Lifecycle
    "BrowserStartedEvent",
    "BrowserClosedEvent",
    "ContextCreatedEvent",
    # Page events
    "ConsoleEvent",
    "DialogEvent",
    "ErrorEvent",
]
