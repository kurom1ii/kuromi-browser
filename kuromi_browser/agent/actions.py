"""
Actions for the AI Agent in kuromi-browser.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ActionType(str, Enum):
    """Available action types for the agent."""

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    FILL = "fill"
    SCROLL = "scroll"
    HOVER = "hover"
    PRESS = "press"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    EXTRACT = "extract"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"
    DONE = "done"
    FAIL = "fail"


@dataclass
class Action:
    """Represents an action to be performed by the agent."""

    type: ActionType
    args: dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "type": self.type.value,
            "args": self.args,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Action":
        """Create action from dictionary."""
        action_type = data.get("type", "").lower()
        try:
            action_enum = ActionType(action_type)
        except ValueError:
            action_enum = ActionType.FAIL

        return cls(
            type=action_enum,
            args=data.get("args", {}),
            reasoning=data.get("reasoning"),
        )

    # Factory methods for common actions
    @classmethod
    def navigate(cls, url: str, reasoning: Optional[str] = None) -> "Action":
        """Create a navigate action."""
        return cls(type=ActionType.NAVIGATE, args={"url": url}, reasoning=reasoning)

    @classmethod
    def click(cls, selector: str, reasoning: Optional[str] = None) -> "Action":
        """Create a click action."""
        return cls(type=ActionType.CLICK, args={"selector": selector}, reasoning=reasoning)

    @classmethod
    def type_text(
        cls, selector: str, text: str, reasoning: Optional[str] = None
    ) -> "Action":
        """Create a type action."""
        return cls(
            type=ActionType.TYPE,
            args={"selector": selector, "text": text},
            reasoning=reasoning,
        )

    @classmethod
    def fill(cls, selector: str, value: str, reasoning: Optional[str] = None) -> "Action":
        """Create a fill action."""
        return cls(
            type=ActionType.FILL,
            args={"selector": selector, "value": value},
            reasoning=reasoning,
        )

    @classmethod
    def scroll(
        cls,
        direction: str = "down",
        amount: int = 500,
        reasoning: Optional[str] = None,
    ) -> "Action":
        """Create a scroll action."""
        return cls(
            type=ActionType.SCROLL,
            args={"direction": direction, "amount": amount},
            reasoning=reasoning,
        )

    @classmethod
    def hover(cls, selector: str, reasoning: Optional[str] = None) -> "Action":
        """Create a hover action."""
        return cls(type=ActionType.HOVER, args={"selector": selector}, reasoning=reasoning)

    @classmethod
    def press(cls, key: str, reasoning: Optional[str] = None) -> "Action":
        """Create a press key action."""
        return cls(type=ActionType.PRESS, args={"key": key}, reasoning=reasoning)

    @classmethod
    def wait(cls, ms: int = 1000, reasoning: Optional[str] = None) -> "Action":
        """Create a wait action."""
        return cls(type=ActionType.WAIT, args={"ms": ms}, reasoning=reasoning)

    @classmethod
    def screenshot(cls, reasoning: Optional[str] = None) -> "Action":
        """Create a screenshot action."""
        return cls(type=ActionType.SCREENSHOT, reasoning=reasoning)

    @classmethod
    def extract(cls, selector: str, reasoning: Optional[str] = None) -> "Action":
        """Create an extract action."""
        return cls(type=ActionType.EXTRACT, args={"selector": selector}, reasoning=reasoning)

    @classmethod
    def done(cls, result: Any = None, reasoning: Optional[str] = None) -> "Action":
        """Create a done action (task completed)."""
        return cls(type=ActionType.DONE, args={"result": result}, reasoning=reasoning)

    @classmethod
    def fail(cls, reason: str, reasoning: Optional[str] = None) -> "Action":
        """Create a fail action (task failed)."""
        return cls(type=ActionType.FAIL, args={"reason": reason}, reasoning=reasoning)


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    action: Action
    data: Any = None
    error: Optional[str] = None
    screenshot: Optional[bytes] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "action": self.action.to_dict(),
            "data": self.data,
            "error": self.error,
            "has_screenshot": self.screenshot is not None,
        }


__all__ = [
    "ActionType",
    "Action",
    "ActionResult",
]
