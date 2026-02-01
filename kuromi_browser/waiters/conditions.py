"""
Wait conditions for kuromi-browser.

Provides various wait conditions for element and page state checking.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Optional, Pattern, Union

if TYPE_CHECKING:
    from kuromi_browser.dom.element import Element
    from kuromi_browser.cdp.session import CDPSession


class WaitCondition(ABC):
    """Abstract base class for wait conditions.

    A wait condition is a predicate that can be polled until it returns True
    or a truthy value.
    """

    @abstractmethod
    async def check(self) -> Any:
        """Check if the condition is satisfied.

        Returns:
            False/None if not satisfied, truthy value if satisfied.
        """
        ...

    @property
    def description(self) -> str:
        """Human-readable description of the condition."""
        return self.__class__.__name__


# Element State Conditions

class ElementVisible(WaitCondition):
    """Wait for element to become visible."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return await self._element.is_visible()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be visible"


class ElementHidden(WaitCondition):
    """Wait for element to become hidden."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return not await self._element.is_visible()
        except Exception:
            return True  # Element gone = hidden

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be hidden"


class ElementEnabled(WaitCondition):
    """Wait for element to become enabled."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return await self._element.is_enabled()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be enabled"


class ElementDisabled(WaitCondition):
    """Wait for element to become disabled."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return not await self._element.is_enabled()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be disabled"


class ElementChecked(WaitCondition):
    """Wait for checkbox/radio to be checked."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return await self._element.is_checked()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be checked"


class ElementUnchecked(WaitCondition):
    """Wait for checkbox/radio to be unchecked."""

    def __init__(self, element: "Element") -> None:
        self._element = element

    async def check(self) -> bool:
        try:
            return not await self._element.is_checked()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element {self._element.node_id} to be unchecked"


class ElementTextContains(WaitCondition):
    """Wait for element text to contain a substring."""

    def __init__(self, element: "Element", text: str) -> None:
        self._element = element
        self._text = text

    async def check(self) -> bool:
        try:
            content = await self._element.text_content()
            return self._text in content
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element text to contain '{self._text}'"


class ElementTextEquals(WaitCondition):
    """Wait for element text to equal a value."""

    def __init__(self, element: "Element", text: str) -> None:
        self._element = element
        self._text = text

    async def check(self) -> bool:
        try:
            content = await self._element.text_content()
            return content.strip() == self._text
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element text to equal '{self._text}'"


class ElementTextMatches(WaitCondition):
    """Wait for element text to match a regex pattern."""

    def __init__(self, element: "Element", pattern: Union[str, Pattern[str]]) -> None:
        self._element = element
        self._pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    async def check(self) -> bool:
        try:
            content = await self._element.text_content()
            return bool(self._pattern.search(content))
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element text to match '{self._pattern.pattern}'"


class ElementAttributeEquals(WaitCondition):
    """Wait for element attribute to equal a value."""

    def __init__(self, element: "Element", name: str, value: str) -> None:
        self._element = element
        self._name = name
        self._value = value

    async def check(self) -> bool:
        try:
            attr = await self._element.attr(self._name)
            return attr == self._value
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element attribute '{self._name}' to equal '{self._value}'"


class ElementAttributeContains(WaitCondition):
    """Wait for element attribute to contain a substring."""

    def __init__(self, element: "Element", name: str, value: str) -> None:
        self._element = element
        self._name = name
        self._value = value

    async def check(self) -> bool:
        try:
            attr = await self._element.attr(self._name)
            return attr is not None and self._value in attr
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element attribute '{self._name}' to contain '{self._value}'"


class ElementHasAttribute(WaitCondition):
    """Wait for element to have an attribute."""

    def __init__(self, element: "Element", name: str) -> None:
        self._element = element
        self._name = name

    async def check(self) -> bool:
        try:
            attr = await self._element.attr(self._name)
            return attr is not None
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element to have attribute '{self._name}'"


class ElementHasClass(WaitCondition):
    """Wait for element to have a CSS class."""

    def __init__(self, element: "Element", class_name: str) -> None:
        self._element = element
        self._class_name = class_name

    async def check(self) -> bool:
        try:
            classes = await self._element.attr("class")
            if classes is None:
                return False
            return self._class_name in classes.split()
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"element to have class '{self._class_name}'"


class ElementNotHasClass(WaitCondition):
    """Wait for element to not have a CSS class."""

    def __init__(self, element: "Element", class_name: str) -> None:
        self._element = element
        self._class_name = class_name

    async def check(self) -> bool:
        try:
            classes = await self._element.attr("class")
            if classes is None:
                return True
            return self._class_name not in classes.split()
        except Exception:
            return True

    @property
    def description(self) -> str:
        return f"element to not have class '{self._class_name}'"


# Selector-based conditions (for checking DOM existence)

class SelectorAttached(WaitCondition):
    """Wait for selector to find an element in DOM."""

    def __init__(self, cdp_session: "CDPSession", selector: str) -> None:
        self._session = cdp_session
        self._selector = selector
        self._found_element: Optional["Element"] = None

    async def check(self) -> Optional["Element"]:
        try:
            from kuromi_browser.dom.element import Element

            result = await self._session.send("DOM.getDocument", {"depth": 0})
            doc_node_id = result["root"]["nodeId"]

            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": doc_node_id, "selector": self._selector},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                self._found_element = Element(self._session, node_id)
                return self._found_element
            return None
        except Exception:
            return None

    @property
    def description(self) -> str:
        return f"selector '{self._selector}' to be attached"


class SelectorDetached(WaitCondition):
    """Wait for selector to not find any element in DOM."""

    def __init__(self, cdp_session: "CDPSession", selector: str) -> None:
        self._session = cdp_session
        self._selector = selector

    async def check(self) -> bool:
        try:
            result = await self._session.send("DOM.getDocument", {"depth": 0})
            doc_node_id = result["root"]["nodeId"]

            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": doc_node_id, "selector": self._selector},
            )
            return result.get("nodeId", 0) == 0
        except Exception:
            return True

    @property
    def description(self) -> str:
        return f"selector '{self._selector}' to be detached"


class SelectorVisible(WaitCondition):
    """Wait for selector to find a visible element."""

    def __init__(self, cdp_session: "CDPSession", selector: str) -> None:
        self._session = cdp_session
        self._selector = selector
        self._found_element: Optional["Element"] = None

    async def check(self) -> Optional["Element"]:
        try:
            from kuromi_browser.dom.element import Element

            result = await self._session.send("DOM.getDocument", {"depth": 0})
            doc_node_id = result["root"]["nodeId"]

            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": doc_node_id, "selector": self._selector},
            )
            node_id = result.get("nodeId", 0)
            if node_id > 0:
                element = Element(self._session, node_id)
                if await element.is_visible():
                    self._found_element = element
                    return element
            return None
        except Exception:
            return None

    @property
    def description(self) -> str:
        return f"selector '{self._selector}' to be visible"


class SelectorHidden(WaitCondition):
    """Wait for selector to not find any visible element."""

    def __init__(self, cdp_session: "CDPSession", selector: str) -> None:
        self._session = cdp_session
        self._selector = selector

    async def check(self) -> bool:
        try:
            from kuromi_browser.dom.element import Element

            result = await self._session.send("DOM.getDocument", {"depth": 0})
            doc_node_id = result["root"]["nodeId"]

            result = await self._session.send(
                "DOM.querySelector",
                {"nodeId": doc_node_id, "selector": self._selector},
            )
            node_id = result.get("nodeId", 0)
            if node_id == 0:
                return True  # Not found = hidden
            element = Element(self._session, node_id)
            return not await element.is_visible()
        except Exception:
            return True

    @property
    def description(self) -> str:
        return f"selector '{self._selector}' to be hidden"


# Page Load Conditions

class PageLoadState(WaitCondition):
    """Wait for page to reach a specific load state."""

    def __init__(self, cdp_session: "CDPSession", state: str = "complete") -> None:
        """Initialize page load state condition.

        Args:
            cdp_session: CDP session.
            state: Target state - 'loading', 'interactive', or 'complete'.
        """
        self._session = cdp_session
        self._state = state

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "document.readyState", "returnByValue": True},
            )
            current_state = result.get("result", {}).get("value", "")

            if self._state == "loading":
                return current_state == "loading"
            elif self._state == "interactive":
                return current_state in ("interactive", "complete")
            else:  # complete
                return current_state == "complete"
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"page load state to be '{self._state}'"


class DOMContentLoaded(WaitCondition):
    """Wait for DOMContentLoaded event."""

    def __init__(self, cdp_session: "CDPSession") -> None:
        self._session = cdp_session

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": "document.readyState !== 'loading'",
                    "returnByValue": True,
                },
            )
            return result.get("result", {}).get("value", False)
        except Exception:
            return False

    @property
    def description(self) -> str:
        return "DOMContentLoaded"


class PageLoaded(WaitCondition):
    """Wait for page load event."""

    def __init__(self, cdp_session: "CDPSession") -> None:
        self._session = cdp_session

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": "document.readyState === 'complete'",
                    "returnByValue": True,
                },
            )
            return result.get("result", {}).get("value", False)
        except Exception:
            return False

    @property
    def description(self) -> str:
        return "page loaded"


# URL Conditions

class URLEquals(WaitCondition):
    """Wait for URL to equal a value."""

    def __init__(self, cdp_session: "CDPSession", url: str) -> None:
        self._session = cdp_session
        self._url = url

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "window.location.href", "returnByValue": True},
            )
            current_url = result.get("result", {}).get("value", "")
            return current_url == self._url
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"URL to equal '{self._url}'"


class URLContains(WaitCondition):
    """Wait for URL to contain a substring."""

    def __init__(self, cdp_session: "CDPSession", substring: str) -> None:
        self._session = cdp_session
        self._substring = substring

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "window.location.href", "returnByValue": True},
            )
            current_url = result.get("result", {}).get("value", "")
            return self._substring in current_url
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"URL to contain '{self._substring}'"


class URLMatches(WaitCondition):
    """Wait for URL to match a regex pattern."""

    def __init__(
        self, cdp_session: "CDPSession", pattern: Union[str, Pattern[str]]
    ) -> None:
        self._session = cdp_session
        self._pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "window.location.href", "returnByValue": True},
            )
            current_url = result.get("result", {}).get("value", "")
            return bool(self._pattern.search(current_url))
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"URL to match '{self._pattern.pattern}'"


# Title Conditions

class TitleEquals(WaitCondition):
    """Wait for page title to equal a value."""

    def __init__(self, cdp_session: "CDPSession", title: str) -> None:
        self._session = cdp_session
        self._title = title

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "document.title", "returnByValue": True},
            )
            current_title = result.get("result", {}).get("value", "")
            return current_title == self._title
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"title to equal '{self._title}'"


class TitleContains(WaitCondition):
    """Wait for page title to contain a substring."""

    def __init__(self, cdp_session: "CDPSession", substring: str) -> None:
        self._session = cdp_session
        self._substring = substring

    async def check(self) -> bool:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {"expression": "document.title", "returnByValue": True},
            )
            current_title = result.get("result", {}).get("value", "")
            return self._substring in current_title
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"title to contain '{self._substring}'"


# JavaScript Conditions

class JavaScriptCondition(WaitCondition):
    """Wait for a JavaScript expression to return truthy value."""

    def __init__(self, cdp_session: "CDPSession", expression: str) -> None:
        self._session = cdp_session
        self._expression = expression

    async def check(self) -> Any:
        try:
            result = await self._session.send(
                "Runtime.evaluate",
                {
                    "expression": self._expression,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            )
            return result.get("result", {}).get("value")
        except Exception:
            return False

    @property
    def description(self) -> str:
        return f"JavaScript condition: {self._expression[:50]}..."


# Custom Condition

class CustomCondition(WaitCondition):
    """Wait for a custom async predicate to return True."""

    def __init__(
        self,
        predicate: Callable[[], Union[bool, Any]],
        description: str = "custom condition",
    ) -> None:
        self._predicate = predicate
        self._description = description

    async def check(self) -> Any:
        result = self._predicate()
        if asyncio.iscoroutine(result):
            return await result
        return result

    @property
    def description(self) -> str:
        return self._description


# Composite Conditions

class AllConditions(WaitCondition):
    """Wait for all conditions to be satisfied."""

    def __init__(self, *conditions: WaitCondition) -> None:
        self._conditions = conditions

    async def check(self) -> bool:
        for condition in self._conditions:
            result = await condition.check()
            if not result:
                return False
        return True

    @property
    def description(self) -> str:
        descriptions = [c.description for c in self._conditions]
        return f"all of: [{', '.join(descriptions)}]"


class AnyCondition(WaitCondition):
    """Wait for any condition to be satisfied."""

    def __init__(self, *conditions: WaitCondition) -> None:
        self._conditions = conditions

    async def check(self) -> Any:
        for condition in self._conditions:
            result = await condition.check()
            if result:
                return result
        return False

    @property
    def description(self) -> str:
        descriptions = [c.description for c in self._conditions]
        return f"any of: [{', '.join(descriptions)}]"


class NotCondition(WaitCondition):
    """Wait for a condition to NOT be satisfied."""

    def __init__(self, condition: WaitCondition) -> None:
        self._condition = condition

    async def check(self) -> bool:
        result = await self._condition.check()
        return not result

    @property
    def description(self) -> str:
        return f"NOT ({self._condition.description})"


__all__ = [
    "WaitCondition",
    # Element states
    "ElementVisible",
    "ElementHidden",
    "ElementEnabled",
    "ElementDisabled",
    "ElementChecked",
    "ElementUnchecked",
    "ElementTextContains",
    "ElementTextEquals",
    "ElementTextMatches",
    "ElementAttributeEquals",
    "ElementAttributeContains",
    "ElementHasAttribute",
    "ElementHasClass",
    "ElementNotHasClass",
    # Selector-based
    "SelectorAttached",
    "SelectorDetached",
    "SelectorVisible",
    "SelectorHidden",
    # Page load
    "PageLoadState",
    "DOMContentLoaded",
    "PageLoaded",
    # URL
    "URLEquals",
    "URLContains",
    "URLMatches",
    # Title
    "TitleEquals",
    "TitleContains",
    # JavaScript
    "JavaScriptCondition",
    # Custom
    "CustomCondition",
    # Composite
    "AllConditions",
    "AnyCondition",
    "NotCondition",
]
