"""
AI Agent module for kuromi-browser.

This module provides LLM-powered browser automation:
- Agent: Main AI agent class
- AgentConfig: Configuration for agent behavior
- Actions: Available browser actions for the agent
- Prompts: System prompts and templates
"""

from typing import TYPE_CHECKING, Any, Optional

from kuromi_browser.interfaces import BaseAgent

if TYPE_CHECKING:
    from kuromi_browser.page import Page
    from kuromi_browser.models import Fingerprint


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


class Agent(BaseAgent):
    """AI-powered browser automation agent.

    Uses LLMs to understand tasks, plan actions, and execute them
    on web pages automatically.
    """

    def __init__(
        self,
        page: "Page",
        config: Optional[AgentConfig] = None,
    ) -> None:
        self._page = page
        self._config = config or AgentConfig()
        self._history: list[dict[str, Any]] = []
        self._current_step = 0

    @property
    def page(self) -> "Page":
        return self._page

    @property
    def config(self) -> AgentConfig:
        return self._config

    @property
    def history(self) -> list[dict[str, Any]]:
        return self._history.copy()

    async def run(
        self,
        task: str,
        *,
        max_steps: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Run the agent to complete a task."""
        raise NotImplementedError

    async def step(
        self,
        instruction: str,
    ) -> Any:
        """Execute a single step based on an instruction."""
        raise NotImplementedError

    async def observe(self) -> dict[str, Any]:
        """Observe the current state of the page."""
        raise NotImplementedError

    async def act(
        self,
        action: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Perform an action on the page."""
        raise NotImplementedError

    async def plan(
        self,
        goal: str,
    ) -> list[str]:
        """Generate a plan to achieve a goal."""
        raise NotImplementedError

    async def reflect(
        self,
        observation: dict[str, Any],
        action: str,
        result: Any,
    ) -> str:
        """Reflect on an action's result."""
        raise NotImplementedError

    async def _get_page_state(self) -> dict[str, Any]:
        """Get current page state for LLM context."""
        raise NotImplementedError

    async def _parse_action(self, llm_response: str) -> tuple[str, list[Any], dict[str, Any]]:
        """Parse LLM response into action, args, kwargs."""
        raise NotImplementedError

    async def _execute_action(
        self, action: str, args: list[Any], kwargs: dict[str, Any]
    ) -> Any:
        """Execute a parsed action on the page."""
        raise NotImplementedError


class AgentActions:
    """Available actions for the AI agent.

    Defines the action space that the agent can use to interact
    with web pages.
    """

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
    "AgentConfig",
    "AgentActions",
]
