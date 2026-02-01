"""
AI Agent module for kuromi-browser.

This module provides LLM-powered browser automation:
- Agent: Main AI agent class
- AgentResult: Result of running an agent task
- AgentConfig: Configuration for agent behavior
- Action, ActionType, ActionResult: Action definitions
"""

from typing import TYPE_CHECKING, Optional

from kuromi_browser.agent.actions import Action, ActionResult, ActionType
from kuromi_browser.agent.agent import Agent, AgentResult

if TYPE_CHECKING:
    from kuromi_browser.page import Page
    from kuromi_browser.llm import LLMProvider


class AgentConfig:
    """Configuration for AI agent behavior."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        provider: str = "openai",
        api_key: Optional[str] = None,
        max_steps: int = 100,
        max_retries: int = 3,
        timeout: float = 300.0,
        screenshot_on_step: bool = True,
        dom_snapshot_on_step: bool = True,
        verbose: bool = False,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.timeout = timeout
        self.screenshot_on_step = screenshot_on_step
        self.dom_snapshot_on_step = dom_snapshot_on_step
        self.verbose = verbose
        self.system_prompt = system_prompt


class AgentActions:
    """Available actions for the AI agent.

    Defines the action space that the agent can use to interact
    with web pages.
    """

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    FILL = "fill"
    PRESS = "press"
    SCROLL = "scroll"
    HOVER = "hover"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    WAIT = "wait"
    GOTO = "goto"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    DONE = "done"
    FAIL = "fail"

    @classmethod
    def all(cls) -> list[str]:
        """Get all available actions."""
        return [
            cls.NAVIGATE,
            cls.CLICK,
            cls.TYPE,
            cls.FILL,
            cls.PRESS,
            cls.SCROLL,
            cls.HOVER,
            cls.SELECT,
            cls.CHECK,
            cls.UNCHECK,
            cls.WAIT,
            cls.GOTO,
            cls.BACK,
            cls.FORWARD,
            cls.RELOAD,
            cls.SCREENSHOT,
            cls.EXTRACT,
            cls.DONE,
            cls.FAIL,
        ]


__all__ = [
    "Agent",
    "AgentResult",
    "AgentConfig",
    "AgentActions",
    "Action",
    "ActionType",
    "ActionResult",
]
