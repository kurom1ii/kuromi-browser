"""
Tab Manager for kuromi-browser.

Handles tab creation, switching, closing, and lifecycle management.
Provides a high-level API for managing multiple browser tabs.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPConnection, CDPSession
    from kuromi_browser.page import Page

logger = logging.getLogger(__name__)


class TabState(str, Enum):
    """Tab lifecycle states."""

    CREATED = "created"
    LOADING = "loading"
    LOADED = "loaded"
    CRASHED = "crashed"
    CLOSED = "closed"


@dataclass
class TabInfo:
    """Information about a browser tab."""

    target_id: str
    """CDP target ID."""

    url: str = "about:blank"
    """Current URL."""

    title: str = ""
    """Page title."""

    state: TabState = TabState.CREATED
    """Current tab state."""

    browser_context_id: Optional[str] = None
    """Browser context this tab belongs to."""

    opener_id: Optional[str] = None
    """Target ID of the tab that opened this one."""

    is_active: bool = False
    """Whether this tab is currently active/focused."""

    created_at: float = 0.0
    """Timestamp when tab was created."""

    favicon_url: Optional[str] = None
    """Tab favicon URL if available."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "target_id": self.target_id,
            "url": self.url,
            "title": self.title,
            "state": self.state.value,
            "browser_context_id": self.browser_context_id,
            "opener_id": self.opener_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "favicon_url": self.favicon_url,
        }


@dataclass
class TabEvents:
    """Event callbacks for tab lifecycle."""

    on_created: list[Callable[[TabInfo], Any]] = field(default_factory=list)
    on_updated: list[Callable[[TabInfo], Any]] = field(default_factory=list)
    on_closed: list[Callable[[str], Any]] = field(default_factory=list)
    on_crashed: list[Callable[[TabInfo], Any]] = field(default_factory=list)
    on_activated: list[Callable[[TabInfo], Any]] = field(default_factory=list)


class Tab:
    """Represents a single browser tab.

    Wraps a CDP session and provides tab-specific operations.
    """

    def __init__(
        self,
        manager: "TabManager",
        info: TabInfo,
        session: Optional["CDPSession"] = None,
    ) -> None:
        self._manager = manager
        self._info = info
        self._session = session
        self._page: Optional["Page"] = None
        self._event_handlers: dict[str, list[Callable[..., Any]]] = {}

    @property
    def id(self) -> str:
        """Tab/target ID."""
        return self._info.target_id

    @property
    def url(self) -> str:
        """Current URL."""
        return self._info.url

    @property
    def title(self) -> str:
        """Page title."""
        return self._info.title

    @property
    def state(self) -> TabState:
        """Current tab state."""
        return self._info.state

    @property
    def is_active(self) -> bool:
        """Whether this tab is active."""
        return self._info.is_active

    @property
    def info(self) -> TabInfo:
        """Tab info."""
        return self._info

    @property
    def session(self) -> Optional["CDPSession"]:
        """CDP session for this tab."""
        return self._session

    @property
    def page(self) -> Optional["Page"]:
        """Page instance for this tab."""
        return self._page

    async def get_session(self) -> "CDPSession":
        """Get or create CDP session for this tab.

        Returns:
            CDPSession attached to this tab.
        """
        if self._session is None:
            self._session = await self._manager._create_session(self._info.target_id)
        return self._session

    async def get_page(self) -> "Page":
        """Get or create Page instance for this tab.

        Returns:
            Page instance for browser automation.
        """
        if self._page is None:
            from kuromi_browser.page import Page

            session = await self.get_session()
            self._page = Page(session)

            # Enable required domains
            await session.send("Page.enable")
            await session.send("Runtime.enable")
            await session.send("Network.enable")
            await session.send("DOM.enable")

        return self._page

    async def activate(self) -> None:
        """Activate/focus this tab."""
        await self._manager.activate(self.id)

    async def goto(self, url: str, **kwargs: Any) -> None:
        """Navigate tab to URL.

        Args:
            url: URL to navigate to.
            **kwargs: Additional navigation options.
        """
        page = await self.get_page()
        await page.goto(url, **kwargs)
        self._info.url = url

    async def reload(self, **kwargs: Any) -> None:
        """Reload the tab."""
        page = await self.get_page()
        await page.reload(**kwargs)

    async def go_back(self) -> None:
        """Navigate back in history."""
        page = await self.get_page()
        await page.go_back()

    async def go_forward(self) -> None:
        """Navigate forward in history."""
        page = await self.get_page()
        await page.go_forward()

    async def close(self) -> None:
        """Close this tab."""
        await self._manager.close(self.id)

    async def screenshot(self, **kwargs: Any) -> bytes:
        """Take screenshot of tab.

        Returns:
            Screenshot image data.
        """
        page = await self.get_page()
        return await page.screenshot(**kwargs)

    async def content(self) -> str:
        """Get page HTML content.

        Returns:
            HTML content string.
        """
        page = await self.get_page()
        return await page.content()

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Evaluate JavaScript in the tab.

        Args:
            expression: JavaScript expression.
            *args: Arguments to pass.

        Returns:
            Evaluation result.
        """
        page = await self.get_page()
        return await page.evaluate(expression, *args)

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Register event handler.

        Args:
            event: Event name.
            handler: Event handler function.
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
        """
        if event in self._event_handlers:
            self._event_handlers[event].remove(handler)

    async def _cleanup(self) -> None:
        """Clean up tab resources."""
        if self._session:
            try:
                await self._session.detach()
            except Exception:
                pass
            self._session = None

        self._page = None
        self._info.state = TabState.CLOSED

    def __repr__(self) -> str:
        return f"Tab(id={self.id!r}, url={self.url!r}, state={self.state.value})"


class TabManager:
    """Manages browser tabs.

    Provides methods for creating, switching, and closing tabs,
    as well as tab lifecycle event handling.

    Example:
        async with Browser() as browser:
            tabs = browser.tabs

            # Create new tab
            tab = await tabs.new("https://example.com")

            # List all tabs
            for t in tabs.all():
                print(t.url)

            # Switch to tab
            await tabs.activate(tab.id)

            # Close tab
            await tabs.close(tab.id)
    """

    def __init__(
        self,
        connection: "CDPConnection",
        browser_context_id: Optional[str] = None,
    ) -> None:
        """Initialize tab manager.

        Args:
            connection: CDP connection to browser.
            browser_context_id: Optional context ID for isolated tabs.
        """
        self._connection = connection
        self._browser_context_id = browser_context_id
        self._tabs: dict[str, Tab] = {}
        self._active_tab_id: Optional[str] = None
        self._events = TabEvents()
        self._auto_attach_enabled = False
        self._sessions: WeakValueDictionary[str, "CDPSession"] = WeakValueDictionary()

    @property
    def count(self) -> int:
        """Number of tabs."""
        return len(self._tabs)

    @property
    def active(self) -> Optional[Tab]:
        """Currently active tab."""
        if self._active_tab_id:
            return self._tabs.get(self._active_tab_id)
        return None

    @property
    def connection(self) -> "CDPConnection":
        """CDP connection."""
        return self._connection

    def all(self) -> list[Tab]:
        """Get all tabs.

        Returns:
            List of all tabs.
        """
        return list(self._tabs.values())

    def get(self, target_id: str) -> Optional[Tab]:
        """Get tab by target ID.

        Args:
            target_id: Tab target ID.

        Returns:
            Tab or None if not found.
        """
        return self._tabs.get(target_id)

    def find_by_url(self, url: str, *, exact: bool = False) -> Optional[Tab]:
        """Find tab by URL.

        Args:
            url: URL to search for.
            exact: Require exact match (default: partial match).

        Returns:
            First matching tab or None.
        """
        for tab in self._tabs.values():
            if exact:
                if tab.url == url:
                    return tab
            else:
                if url in tab.url:
                    return tab
        return None

    def find_by_title(self, title: str, *, exact: bool = False) -> Optional[Tab]:
        """Find tab by title.

        Args:
            title: Title to search for.
            exact: Require exact match.

        Returns:
            First matching tab or None.
        """
        for tab in self._tabs.values():
            if exact:
                if tab.title == title:
                    return tab
            else:
                if title.lower() in tab.title.lower():
                    return tab
        return None

    async def new(
        self,
        url: str = "about:blank",
        *,
        activate: bool = True,
        wait_until: str = "load",
    ) -> Tab:
        """Create a new tab.

        Args:
            url: Initial URL (default: about:blank).
            activate: Whether to activate the new tab.
            wait_until: Wait condition for navigation.

        Returns:
            The newly created tab.
        """
        import time

        params: dict[str, Any] = {"url": url}
        if self._browser_context_id:
            params["browserContextId"] = self._browser_context_id

        result = await self._connection.send("Target.createTarget", params)
        target_id = result["targetId"]

        info = TabInfo(
            target_id=target_id,
            url=url,
            browser_context_id=self._browser_context_id,
            state=TabState.LOADING,
            created_at=time.time(),
        )

        tab = Tab(self, info)
        self._tabs[target_id] = tab

        # Wait for load if navigating to real URL
        if url != "about:blank":
            try:
                page = await tab.get_page()
                await page.wait_for_load_state(wait_until)
                info.state = TabState.LOADED
            except Exception as e:
                logger.warning(f"Tab load error: {e}")
                info.state = TabState.LOADED  # Still mark as loaded

        # Activate if requested
        if activate:
            await self.activate(target_id)

        # Fire event
        await self._emit_event("created", info)

        logger.debug(f"Created new tab: {target_id}")
        return tab

    async def close(self, target_id: str) -> bool:
        """Close a tab.

        Args:
            target_id: Tab to close.

        Returns:
            True if closed successfully.
        """
        tab = self._tabs.get(target_id)
        if not tab:
            return False

        try:
            await tab._cleanup()

            await self._connection.send(
                "Target.closeTarget",
                {"targetId": target_id},
            )
        except Exception as e:
            logger.warning(f"Error closing tab: {e}")

        self._tabs.pop(target_id, None)

        # Update active tab
        if self._active_tab_id == target_id:
            self._active_tab_id = None
            # Activate another tab if available
            if self._tabs:
                next_tab = next(iter(self._tabs.values()))
                await self.activate(next_tab.id)

        # Fire event
        await self._emit_event("closed", target_id)

        logger.debug(f"Closed tab: {target_id}")
        return True

    async def close_all(self, *, keep_one: bool = True) -> int:
        """Close all tabs.

        Args:
            keep_one: Keep at least one tab open.

        Returns:
            Number of tabs closed.
        """
        closed = 0
        tab_ids = list(self._tabs.keys())

        for i, target_id in enumerate(tab_ids):
            if keep_one and i == len(tab_ids) - 1:
                break
            if await self.close(target_id):
                closed += 1

        return closed

    async def activate(self, target_id: str) -> bool:
        """Activate/focus a tab.

        Args:
            target_id: Tab to activate.

        Returns:
            True if activated successfully.
        """
        tab = self._tabs.get(target_id)
        if not tab:
            return False

        try:
            await self._connection.send(
                "Target.activateTarget",
                {"targetId": target_id},
            )
        except Exception as e:
            logger.warning(f"Error activating tab: {e}")
            return False

        # Update active state
        for t in self._tabs.values():
            t._info.is_active = t.id == target_id

        self._active_tab_id = target_id

        # Fire event
        await self._emit_event("activated", tab.info)

        return True

    async def next(self) -> Optional[Tab]:
        """Switch to next tab.

        Returns:
            The newly active tab or None.
        """
        tabs = self.all()
        if not tabs:
            return None

        if self._active_tab_id:
            ids = [t.id for t in tabs]
            try:
                idx = ids.index(self._active_tab_id)
                next_idx = (idx + 1) % len(ids)
                await self.activate(ids[next_idx])
                return self._tabs.get(ids[next_idx])
            except ValueError:
                pass

        # Fallback to first tab
        await self.activate(tabs[0].id)
        return tabs[0]

    async def previous(self) -> Optional[Tab]:
        """Switch to previous tab.

        Returns:
            The newly active tab or None.
        """
        tabs = self.all()
        if not tabs:
            return None

        if self._active_tab_id:
            ids = [t.id for t in tabs]
            try:
                idx = ids.index(self._active_tab_id)
                prev_idx = (idx - 1) % len(ids)
                await self.activate(ids[prev_idx])
                return self._tabs.get(ids[prev_idx])
            except ValueError:
                pass

        # Fallback to last tab
        await self.activate(tabs[-1].id)
        return tabs[-1]

    async def duplicate(self, target_id: str) -> Optional[Tab]:
        """Duplicate a tab.

        Args:
            target_id: Tab to duplicate.

        Returns:
            The new duplicated tab.
        """
        tab = self._tabs.get(target_id)
        if not tab:
            return None

        return await self.new(tab.url)

    async def move(self, target_id: str, index: int) -> bool:
        """Move tab to a specific position.

        Note: This is a logical reorder - actual browser behavior
        may vary.

        Args:
            target_id: Tab to move.
            index: Target position (0-based).

        Returns:
            True if moved successfully.
        """
        if target_id not in self._tabs:
            return False

        # Reorder internal dict
        tabs = list(self._tabs.items())
        tab_idx = next((i for i, (k, _) in enumerate(tabs) if k == target_id), None)

        if tab_idx is None:
            return False

        tab_item = tabs.pop(tab_idx)
        tabs.insert(index, tab_item)
        self._tabs = dict(tabs)

        return True

    async def refresh(self) -> list[Tab]:
        """Refresh tab list from browser.

        Returns:
            Updated list of tabs.
        """
        import time

        result = await self._connection.send("Target.getTargets")
        targets = result.get("targetInfos", [])

        current_ids = set(self._tabs.keys())
        found_ids = set()

        for target in targets:
            if target.get("type") != "page":
                continue

            target_id = target["targetId"]
            found_ids.add(target_id)

            if target_id in self._tabs:
                # Update existing tab info
                tab = self._tabs[target_id]
                tab._info.url = target.get("url", "")
                tab._info.title = target.get("title", "")
            else:
                # New tab discovered
                info = TabInfo(
                    target_id=target_id,
                    url=target.get("url", ""),
                    title=target.get("title", ""),
                    browser_context_id=target.get("browserContextId"),
                    opener_id=target.get("openerId"),
                    state=TabState.LOADED,
                    created_at=time.time(),
                )
                self._tabs[target_id] = Tab(self, info)

        # Remove closed tabs
        for target_id in current_ids - found_ids:
            tab = self._tabs.pop(target_id, None)
            if tab:
                await tab._cleanup()

        return self.all()

    async def enable_auto_attach(self) -> None:
        """Enable automatic attachment to new targets."""
        if self._auto_attach_enabled:
            return

        await self._connection.send(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            },
        )

        # Listen for target events
        self._connection.on("Target.targetCreated", self._on_target_created)
        self._connection.on("Target.targetDestroyed", self._on_target_destroyed)
        self._connection.on("Target.targetInfoChanged", self._on_target_info_changed)
        self._connection.on("Target.targetCrashed", self._on_target_crashed)

        await self._connection.send("Target.setDiscoverTargets", {"discover": True})

        self._auto_attach_enabled = True
        logger.debug("Auto-attach enabled for tabs")

    async def _create_session(self, target_id: str) -> "CDPSession":
        """Create CDP session for a target.

        Args:
            target_id: Target ID.

        Returns:
            CDP session.
        """
        from kuromi_browser.cdp import CDPSession

        result = await self._connection.send(
            "Target.attachToTarget",
            {
                "targetId": target_id,
                "flatten": True,
            },
        )
        session_id = result["sessionId"]

        session = CDPSession(self._connection, target_id, session_id)
        self._sessions[target_id] = session

        return session

    async def _on_target_created(self, params: dict[str, Any]) -> None:
        """Handle new target creation."""
        import time

        target_info = params.get("targetInfo", {})
        if target_info.get("type") != "page":
            return

        target_id = target_info["targetId"]

        # Skip if already tracked
        if target_id in self._tabs:
            return

        info = TabInfo(
            target_id=target_id,
            url=target_info.get("url", ""),
            title=target_info.get("title", ""),
            browser_context_id=target_info.get("browserContextId"),
            opener_id=target_info.get("openerId"),
            state=TabState.CREATED,
            created_at=time.time(),
        )

        self._tabs[target_id] = Tab(self, info)
        await self._emit_event("created", info)

        logger.debug(f"Target created: {target_id}")

    async def _on_target_destroyed(self, params: dict[str, Any]) -> None:
        """Handle target destruction."""
        target_id = params.get("targetId")
        if not target_id or target_id not in self._tabs:
            return

        tab = self._tabs.pop(target_id, None)
        if tab:
            await tab._cleanup()

        if self._active_tab_id == target_id:
            self._active_tab_id = None

        await self._emit_event("closed", target_id)
        logger.debug(f"Target destroyed: {target_id}")

    async def _on_target_info_changed(self, params: dict[str, Any]) -> None:
        """Handle target info update."""
        target_info = params.get("targetInfo", {})
        target_id = target_info.get("targetId")

        tab = self._tabs.get(target_id)
        if not tab:
            return

        # Update info
        tab._info.url = target_info.get("url", tab._info.url)
        tab._info.title = target_info.get("title", tab._info.title)

        await self._emit_event("updated", tab.info)

    async def _on_target_crashed(self, params: dict[str, Any]) -> None:
        """Handle target crash."""
        target_id = params.get("targetId")

        tab = self._tabs.get(target_id)
        if not tab:
            return

        tab._info.state = TabState.CRASHED
        await self._emit_event("crashed", tab.info)

        logger.warning(f"Tab crashed: {target_id}")

    async def _emit_event(self, event: str, data: Any) -> None:
        """Emit an event to handlers."""
        handlers = getattr(self._events, f"on_{event}", [])
        for handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def on(self, event: str, handler: Callable[..., Any]) -> None:
        """Register event handler.

        Events:
            - created: Tab created (TabInfo)
            - updated: Tab info updated (TabInfo)
            - closed: Tab closed (target_id: str)
            - crashed: Tab crashed (TabInfo)
            - activated: Tab activated (TabInfo)

        Args:
            event: Event name.
            handler: Handler function.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers is not None:
            handlers.append(handler)

    def off(self, event: str, handler: Callable[..., Any]) -> None:
        """Remove event handler.

        Args:
            event: Event name.
            handler: Handler to remove.
        """
        handlers = getattr(self._events, f"on_{event}", None)
        if handlers and handler in handlers:
            handlers.remove(handler)

    async def cleanup(self) -> None:
        """Clean up all tabs and resources."""
        for tab in list(self._tabs.values()):
            await tab._cleanup()
        self._tabs.clear()
        self._active_tab_id = None

    def __len__(self) -> int:
        return len(self._tabs)

    def __iter__(self):
        return iter(self._tabs.values())

    def __getitem__(self, target_id: str) -> Tab:
        return self._tabs[target_id]

    def __contains__(self, target_id: str) -> bool:
        return target_id in self._tabs


__all__ = [
    "Tab",
    "TabInfo",
    "TabManager",
    "TabState",
]
