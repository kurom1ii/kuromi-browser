"""
Wait System for kuromi-browser.

Provides synchronization utilities for waiting on page and element states.

Example:
    from kuromi_browser.waiters import Waiter, ElementWaiter

    # Wait for page load
    waiter = Waiter(cdp_session)
    await waiter.for_load_state("complete")

    # Wait for element
    element = await waiter.for_selector("#submit", state="visible")

    # Element-specific waits
    elem_waiter = ElementWaiter(element)
    await elem_waiter.until_visible()
    await elem_waiter.until_text_contains("Success")
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Optional, Pattern, Union

from kuromi_browser.waiters.conditions import (
    AllConditions,
    AnyCondition,
    CustomCondition,
    DOMContentLoaded,
    ElementAttributeContains,
    ElementAttributeEquals,
    ElementChecked,
    ElementDisabled,
    ElementEnabled,
    ElementHasAttribute,
    ElementHasClass,
    ElementHidden,
    ElementNotHasClass,
    ElementTextContains,
    ElementTextEquals,
    ElementTextMatches,
    ElementUnchecked,
    ElementVisible,
    JavaScriptCondition,
    NotCondition,
    PageLoaded,
    PageLoadState,
    SelectorAttached,
    SelectorDetached,
    SelectorHidden,
    SelectorVisible,
    TitleContains,
    TitleEquals,
    URLContains,
    URLEquals,
    URLMatches,
    WaitCondition,
)

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.dom.element import Element

logger = logging.getLogger(__name__)


class WaitTimeoutError(TimeoutError):
    """Raised when a wait operation times out."""

    def __init__(self, condition: WaitCondition, timeout: float) -> None:
        self.condition = condition
        self.timeout = timeout
        super().__init__(
            f"Timeout {timeout}s waiting for {condition.description}"
        )


class WaitOptions:
    """Configuration options for wait operations."""

    def __init__(
        self,
        timeout: float = 30.0,
        polling_interval: float = 0.1,
        ignore_exceptions: bool = True,
    ) -> None:
        """Initialize wait options.

        Args:
            timeout: Maximum time to wait in seconds.
            polling_interval: Time between condition checks in seconds.
            ignore_exceptions: Whether to ignore exceptions during checks.
        """
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.ignore_exceptions = ignore_exceptions


DEFAULT_OPTIONS = WaitOptions()


class BaseWaiter:
    """Base class for waiters with common wait logic."""

    def __init__(
        self,
        default_timeout: float = 30.0,
        default_polling_interval: float = 0.1,
    ) -> None:
        """Initialize base waiter.

        Args:
            default_timeout: Default timeout in seconds.
            default_polling_interval: Default polling interval in seconds.
        """
        self._default_timeout = default_timeout
        self._default_polling_interval = default_polling_interval

    async def _wait_for(
        self,
        condition: WaitCondition,
        timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
        ignore_exceptions: bool = True,
    ) -> Any:
        """Wait for a condition to be satisfied.

        Args:
            condition: The condition to wait for.
            timeout: Maximum time to wait in seconds.
            polling_interval: Time between checks in seconds.
            ignore_exceptions: Whether to ignore exceptions during checks.

        Returns:
            The result of the condition check (truthy value).

        Raises:
            WaitTimeoutError: If the condition is not met within timeout.
        """
        timeout = timeout if timeout is not None else self._default_timeout
        interval = (
            polling_interval
            if polling_interval is not None
            else self._default_polling_interval
        )

        start_time = time.monotonic()
        last_exception: Optional[Exception] = None

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                if last_exception and not ignore_exceptions:
                    raise last_exception
                raise WaitTimeoutError(condition, timeout)

            try:
                result = await condition.check()
                if result:
                    logger.debug(
                        f"Condition satisfied: {condition.description} "
                        f"(elapsed: {elapsed:.2f}s)"
                    )
                    return result
            except Exception as e:
                last_exception = e
                if not ignore_exceptions:
                    raise
                logger.debug(f"Exception during wait check: {e}")

            # Calculate sleep time to not overshoot timeout
            remaining = timeout - (time.monotonic() - start_time)
            sleep_time = min(interval, max(0, remaining))
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def _wait_for_condition(
        self,
        condition: WaitCondition,
        options: Optional[WaitOptions] = None,
    ) -> Any:
        """Wait for a condition with options.

        Args:
            condition: The condition to wait for.
            options: Wait options.

        Returns:
            The result of the condition check.
        """
        opts = options or DEFAULT_OPTIONS
        return await self._wait_for(
            condition,
            timeout=opts.timeout,
            polling_interval=opts.polling_interval,
            ignore_exceptions=opts.ignore_exceptions,
        )


class Waiter(BaseWaiter):
    """Page-level waiter for synchronization operations.

    Provides methods for waiting on page states, selectors, URLs,
    network idle, and custom conditions.

    Example:
        waiter = Waiter(cdp_session)

        # Wait for load state
        await waiter.for_load_state("complete")

        # Wait for element
        element = await waiter.for_selector("#login-form")

        # Wait for URL change
        await waiter.for_url_contains("/dashboard")

        # Wait for network idle
        await waiter.for_network_idle()
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        default_timeout: float = 30.0,
        default_polling_interval: float = 0.1,
    ) -> None:
        """Initialize waiter.

        Args:
            cdp_session: CDP session for browser communication.
            default_timeout: Default timeout in seconds.
            default_polling_interval: Default polling interval in seconds.
        """
        super().__init__(default_timeout, default_polling_interval)
        self._session = cdp_session
        self._network_tracker: Optional[NetworkIdleTracker] = None

    # Selector-based waits

    async def for_selector(
        self,
        selector: str,
        *,
        state: str = "attached",
        timeout: Optional[float] = None,
    ) -> Optional["Element"]:
        """Wait for a selector to match an element.

        Args:
            selector: CSS selector.
            state: Target state - 'attached', 'detached', 'visible', 'hidden'.
            timeout: Maximum time to wait.

        Returns:
            The element if state is 'attached' or 'visible', None otherwise.

        Raises:
            WaitTimeoutError: If timeout is reached.
        """
        conditions = {
            "attached": SelectorAttached(self._session, selector),
            "detached": SelectorDetached(self._session, selector),
            "visible": SelectorVisible(self._session, selector),
            "hidden": SelectorHidden(self._session, selector),
        }

        condition = conditions.get(state)
        if not condition:
            raise ValueError(f"Invalid state: {state}. Use: attached, detached, visible, hidden")

        result = await self._wait_for(condition, timeout=timeout)

        # Return element for attached/visible states
        if state in ("attached", "visible"):
            return result
        return None

    async def for_selector_all(
        self,
        selector: str,
        *,
        min_count: int = 1,
        timeout: Optional[float] = None,
    ) -> list["Element"]:
        """Wait for selector to match at least min_count elements.

        Args:
            selector: CSS selector.
            min_count: Minimum number of elements to match.
            timeout: Maximum time to wait.

        Returns:
            List of matching elements.
        """
        from kuromi_browser.dom.element import Element

        async def check_count() -> Optional[list[Element]]:
            try:
                result = await self._session.send("DOM.getDocument", {"depth": 0})
                doc_node_id = result["root"]["nodeId"]

                result = await self._session.send(
                    "DOM.querySelectorAll",
                    {"nodeId": doc_node_id, "selector": selector},
                )
                node_ids = result.get("nodeIds", [])
                if len(node_ids) >= min_count:
                    return [Element(self._session, nid) for nid in node_ids]
                return None
            except Exception:
                return None

        condition = CustomCondition(
            check_count,
            f"selector '{selector}' to match at least {min_count} elements",
        )
        return await self._wait_for(condition, timeout=timeout)

    # Page load state waits

    async def for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for page to reach a load state.

        Args:
            state: Target state - 'load', 'domcontentloaded', or 'networkidle'.
            timeout: Maximum time to wait.

        Raises:
            WaitTimeoutError: If timeout is reached.
        """
        if state == "networkidle":
            await self.for_network_idle(timeout=timeout)
            return

        if state == "domcontentloaded":
            condition = DOMContentLoaded(self._session)
        elif state == "load":
            condition = PageLoaded(self._session)
        else:
            # Support 'loading', 'interactive', 'complete'
            condition = PageLoadState(self._session, state)

        await self._wait_for(condition, timeout=timeout)

    async def for_dom_content_loaded(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for DOMContentLoaded event.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(DOMContentLoaded(self._session), timeout=timeout)

    async def for_page_loaded(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for page load event.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(PageLoaded(self._session), timeout=timeout)

    # Network waits

    async def for_network_idle(
        self,
        *,
        idle_time: float = 0.5,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for network to be idle.

        Network is considered idle when there are no pending requests
        for the specified idle_time duration.

        Args:
            idle_time: Time in seconds with no network activity.
            timeout: Maximum time to wait.

        Raises:
            WaitTimeoutError: If timeout is reached.
        """
        tracker = NetworkIdleTracker(self._session, idle_time=idle_time)
        await tracker.start()
        try:
            await self._wait_for(tracker, timeout=timeout)
        finally:
            await tracker.stop()

    async def for_request(
        self,
        url_pattern: str,
        *,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Wait for a request matching the URL pattern.

        Args:
            url_pattern: Glob or regex pattern to match URL.
            timeout: Maximum time to wait.

        Returns:
            Request data.
        """
        import fnmatch

        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

        def on_request(params: dict[str, Any]) -> None:
            request_url = params.get("request", {}).get("url", "")
            if fnmatch.fnmatch(request_url, url_pattern) and not future.done():
                future.set_result(params)

        await self._session.send("Network.enable")
        self._session.on("Network.requestWillBeSent", on_request)

        try:
            timeout_val = timeout if timeout is not None else self._default_timeout
            return await asyncio.wait_for(future, timeout=timeout_val)
        finally:
            self._session.off("Network.requestWillBeSent", on_request)

    async def for_response(
        self,
        url_pattern: str,
        *,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Wait for a response matching the URL pattern.

        Args:
            url_pattern: Glob or regex pattern to match URL.
            timeout: Maximum time to wait.

        Returns:
            Response data.
        """
        import fnmatch

        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

        def on_response(params: dict[str, Any]) -> None:
            response_url = params.get("response", {}).get("url", "")
            if fnmatch.fnmatch(response_url, url_pattern) and not future.done():
                future.set_result(params)

        await self._session.send("Network.enable")
        self._session.on("Network.responseReceived", on_response)

        try:
            timeout_val = timeout if timeout is not None else self._default_timeout
            return await asyncio.wait_for(future, timeout=timeout_val)
        finally:
            self._session.off("Network.responseReceived", on_response)

    # URL waits

    async def for_url(
        self,
        url: Union[str, Pattern[str], Callable[[str], bool]],
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for URL to match.

        Args:
            url: Exact URL, regex pattern, or predicate function.
            timeout: Maximum time to wait.
        """
        if callable(url):
            condition = CustomCondition(
                lambda: self._check_url_predicate(url),
                "URL to match predicate",
            )
        elif hasattr(url, "pattern"):  # Pattern
            condition = URLMatches(self._session, url)  # type: ignore
        else:
            condition = URLEquals(self._session, str(url))

        await self._wait_for(condition, timeout=timeout)

    async def _check_url_predicate(
        self,
        predicate: Callable[[str], bool],
    ) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "window.location.href", "returnByValue": True},
            )
            current_url = result.get("result", {}).get("value", "")
            return predicate(current_url)
        except Exception:
            return False

    async def for_url_contains(
        self,
        substring: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for URL to contain substring.

        Args:
            substring: Substring to find in URL.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            URLContains(self._session, substring),
            timeout=timeout,
        )

    async def for_url_matches(
        self,
        pattern: Union[str, Pattern[str]],
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for URL to match regex pattern.

        Args:
            pattern: Regex pattern.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            URLMatches(self._session, pattern),
            timeout=timeout,
        )

    # Title waits

    async def for_title(
        self,
        title: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for page title to equal value.

        Args:
            title: Expected title.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            TitleEquals(self._session, title),
            timeout=timeout,
        )

    async def for_title_contains(
        self,
        substring: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for page title to contain substring.

        Args:
            substring: Substring to find in title.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            TitleContains(self._session, substring),
            timeout=timeout,
        )

    # JavaScript waits

    async def for_function(
        self,
        expression: str,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """Wait for JavaScript expression to return truthy value.

        Args:
            expression: JavaScript expression to evaluate.
            timeout: Maximum time to wait.

        Returns:
            The result of the expression.
        """
        return await self._wait_for(
            JavaScriptCondition(self._session, expression),
            timeout=timeout,
        )

    async def for_js(
        self,
        expression: str,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """Alias for for_function.

        Args:
            expression: JavaScript expression.
            timeout: Maximum time to wait.

        Returns:
            The result of the expression.
        """
        return await self.for_function(expression, timeout=timeout)

    # Event waits

    async def for_event(
        self,
        event: str,
        *,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Wait for a CDP event.

        Args:
            event: CDP event name (e.g., "Page.loadEventFired").
            timeout: Maximum time to wait.

        Returns:
            Event parameters.
        """
        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()

        def on_event(params: dict[str, Any]) -> None:
            if not future.done():
                future.set_result(params)

        self._session.on(event, on_event)

        try:
            timeout_val = timeout if timeout is not None else self._default_timeout
            return await asyncio.wait_for(future, timeout=timeout_val)
        finally:
            self._session.off(event, on_event)

    # Custom conditions

    async def for_condition(
        self,
        condition: WaitCondition,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """Wait for a custom condition.

        Args:
            condition: WaitCondition instance.
            timeout: Maximum time to wait.

        Returns:
            The result of the condition check.
        """
        return await self._wait_for(condition, timeout=timeout)

    async def for_predicate(
        self,
        predicate: Callable[[], Union[bool, Any]],
        *,
        timeout: Optional[float] = None,
        description: str = "custom predicate",
    ) -> Any:
        """Wait for a custom predicate to return truthy value.

        Args:
            predicate: Function or coroutine returning truthy/falsy value.
            timeout: Maximum time to wait.
            description: Description for error messages.

        Returns:
            The result of the predicate.
        """
        return await self._wait_for(
            CustomCondition(predicate, description),
            timeout=timeout,
        )

    # Timeout/sleep

    async def for_timeout(self, timeout: float) -> None:
        """Wait for a fixed amount of time.

        Args:
            timeout: Time to wait in milliseconds.
        """
        await asyncio.sleep(timeout / 1000)

    async def sleep(self, seconds: float) -> None:
        """Wait for a fixed amount of time.

        Args:
            seconds: Time to wait in seconds.
        """
        await asyncio.sleep(seconds)


class ElementWaiter(BaseWaiter):
    """Element-specific waiter for element state changes.

    Provides methods for waiting on element visibility, text, attributes,
    and other state changes.

    Example:
        elem_waiter = ElementWaiter(element)

        # Wait for visibility
        await elem_waiter.until_visible()

        # Wait for text
        await elem_waiter.until_text_contains("Success")

        # Wait for attribute
        await elem_waiter.until_attribute_equals("disabled", None)
    """

    def __init__(
        self,
        element: "Element",
        default_timeout: float = 30.0,
        default_polling_interval: float = 0.1,
    ) -> None:
        """Initialize element waiter.

        Args:
            element: The element to wait on.
            default_timeout: Default timeout in seconds.
            default_polling_interval: Default polling interval in seconds.
        """
        super().__init__(default_timeout, default_polling_interval)
        self._element = element

    @property
    def element(self) -> "Element":
        """Get the element being waited on."""
        return self._element

    # Visibility

    async def until_visible(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element is visible.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementVisible(self._element),
            timeout=timeout,
        )

    async def until_hidden(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element is hidden.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementHidden(self._element),
            timeout=timeout,
        )

    # Enabled/Disabled

    async def until_enabled(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element is enabled.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementEnabled(self._element),
            timeout=timeout,
        )

    async def until_disabled(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element is disabled.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementDisabled(self._element),
            timeout=timeout,
        )

    # Checked state

    async def until_checked(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until checkbox/radio is checked.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementChecked(self._element),
            timeout=timeout,
        )

    async def until_unchecked(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until checkbox/radio is unchecked.

        Args:
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementUnchecked(self._element),
            timeout=timeout,
        )

    # Text content

    async def until_text_contains(
        self,
        text: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element text contains substring.

        Args:
            text: Substring to find.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementTextContains(self._element, text),
            timeout=timeout,
        )

    async def until_text_equals(
        self,
        text: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element text equals value.

        Args:
            text: Expected text.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementTextEquals(self._element, text),
            timeout=timeout,
        )

    async def until_text_matches(
        self,
        pattern: Union[str, Pattern[str]],
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element text matches regex pattern.

        Args:
            pattern: Regex pattern.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementTextMatches(self._element, pattern),
            timeout=timeout,
        )

    async def until_text_not_empty(
        self,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element has non-empty text.

        Args:
            timeout: Maximum time to wait.
        """
        async def has_text() -> bool:
            text = await self._element.text_content()
            return bool(text and text.strip())

        await self._wait_for(
            CustomCondition(has_text, "element text to be non-empty"),
            timeout=timeout,
        )

    # Attributes

    async def until_attribute_equals(
        self,
        name: str,
        value: Optional[str],
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element attribute equals value.

        Args:
            name: Attribute name.
            value: Expected value (None to wait for attribute to be removed).
            timeout: Maximum time to wait.
        """
        if value is None:
            # Wait for attribute to be removed
            condition = NotCondition(ElementHasAttribute(self._element, name))
        else:
            condition = ElementAttributeEquals(self._element, name, value)

        await self._wait_for(condition, timeout=timeout)

    async def until_attribute_contains(
        self,
        name: str,
        value: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element attribute contains substring.

        Args:
            name: Attribute name.
            value: Substring to find.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementAttributeContains(self._element, name, value),
            timeout=timeout,
        )

    async def until_has_attribute(
        self,
        name: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element has attribute.

        Args:
            name: Attribute name.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementHasAttribute(self._element, name),
            timeout=timeout,
        )

    # CSS classes

    async def until_has_class(
        self,
        class_name: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element has CSS class.

        Args:
            class_name: CSS class name.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementHasClass(self._element, class_name),
            timeout=timeout,
        )

    async def until_not_has_class(
        self,
        class_name: str,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until element does not have CSS class.

        Args:
            class_name: CSS class name.
            timeout: Maximum time to wait.
        """
        await self._wait_for(
            ElementNotHasClass(self._element, class_name),
            timeout=timeout,
        )

    # Custom conditions

    async def until_condition(
        self,
        predicate: Callable[["Element"], Union[bool, Any]],
        *,
        timeout: Optional[float] = None,
        description: str = "custom condition",
    ) -> Any:
        """Wait for custom predicate on element.

        Args:
            predicate: Function taking element and returning truthy/falsy.
            timeout: Maximum time to wait.
            description: Description for error messages.

        Returns:
            The result of the predicate.
        """
        async def check() -> Any:
            result = predicate(self._element)
            if asyncio.iscoroutine(result):
                return await result
            return result

        return await self._wait_for(
            CustomCondition(check, description),
            timeout=timeout,
        )


class NetworkIdleTracker(WaitCondition):
    """Tracks network activity to detect idle state.

    Network is considered idle when there are no pending requests
    for the specified idle_time duration.
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        idle_time: float = 0.5,
    ) -> None:
        """Initialize network idle tracker.

        Args:
            cdp_session: CDP session.
            idle_time: Time with no activity to consider idle (seconds).
        """
        self._session = cdp_session
        self._idle_time = idle_time
        self._pending_requests: set[str] = set()
        self._last_activity: float = 0
        self._started = False

    async def start(self) -> None:
        """Start tracking network activity."""
        if self._started:
            return

        await self._session.send("Network.enable")
        self._session.on("Network.requestWillBeSent", self._on_request_started)
        self._session.on("Network.loadingFinished", self._on_request_finished)
        self._session.on("Network.loadingFailed", self._on_request_finished)
        self._session.on("Network.responseReceived", self._on_response_received)

        self._last_activity = time.monotonic()
        self._started = True

    async def stop(self) -> None:
        """Stop tracking network activity."""
        if not self._started:
            return

        self._session.off("Network.requestWillBeSent", self._on_request_started)
        self._session.off("Network.loadingFinished", self._on_request_finished)
        self._session.off("Network.loadingFailed", self._on_request_finished)
        self._session.off("Network.responseReceived", self._on_response_received)

        self._started = False

    def _on_request_started(self, params: dict[str, Any]) -> None:
        """Handle new request."""
        request_id = params.get("requestId", "")
        if request_id:
            self._pending_requests.add(request_id)
            self._last_activity = time.monotonic()

    def _on_request_finished(self, params: dict[str, Any]) -> None:
        """Handle request finished/failed."""
        request_id = params.get("requestId", "")
        self._pending_requests.discard(request_id)
        self._last_activity = time.monotonic()

    def _on_response_received(self, params: dict[str, Any]) -> None:
        """Handle response received."""
        self._last_activity = time.monotonic()

    async def check(self) -> bool:
        """Check if network is idle.

        Returns:
            True if no pending requests and idle time has passed.
        """
        if self._pending_requests:
            return False

        elapsed = time.monotonic() - self._last_activity
        return elapsed >= self._idle_time

    @property
    def description(self) -> str:
        return f"network idle for {self._idle_time}s"

    @property
    def pending_count(self) -> int:
        """Get number of pending requests."""
        return len(self._pending_requests)


# Re-export conditions
from kuromi_browser.waiters.conditions import (
    WaitCondition,
    AllConditions,
    AnyCondition,
    NotCondition,
    CustomCondition,
)

__all__ = [
    # Main classes
    "Waiter",
    "ElementWaiter",
    "BaseWaiter",
    "NetworkIdleTracker",
    # Configuration
    "WaitOptions",
    "WaitTimeoutError",
    # Base conditions
    "WaitCondition",
    "AllConditions",
    "AnyCondition",
    "NotCondition",
    "CustomCondition",
]
