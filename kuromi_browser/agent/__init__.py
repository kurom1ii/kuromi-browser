"""
AI Agent module for kuromi-browser.

This module provides LLM-powered browser automation:
- Agent: Main AI agent class with vision and DOM support
- AgentResult: Result of running an agent task
- AgentConfig: Configuration for agent behavior
- Action, ActionType, ActionResult: Action definitions

For advanced AI features, use the `ai` module which provides:
- AIAgent: High-level wrapper with all AI capabilities
- DOMSerializer: Convert DOM to LLM-friendly formats
- VisionAnalyzer: Screenshot analysis
- TaskParser: Natural language task parsing

Example:
    from kuromi_browser.agent import Agent, AgentConfig
    from kuromi_browser.llm import OpenAIProvider

    # Simple usage
    llm = OpenAIProvider()
    agent = Agent(llm, page)
    result = await agent.run("Click the login button")

    # With config
    config = AgentConfig(model="gpt-4o", max_steps=20)
    agent = create_agent(page, config)
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
        use_vision: bool = True,
        use_dom: bool = True,
    ) -> None:
        """Initialize agent configuration.

        Args:
            model: LLM model to use.
            provider: LLM provider ('openai' or 'anthropic').
            api_key: API key (or use env var).
            max_steps: Maximum steps per task.
            max_retries: Number of retries on failure.
            timeout: Overall timeout in seconds.
            screenshot_on_step: Take screenshot on each step.
            dom_snapshot_on_step: Get DOM snapshot on each step.
            verbose: Print debug information.
            system_prompt: Custom system prompt override.
            use_vision: Enable vision/screenshot analysis.
            use_dom: Enable DOM serialization.
        """
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
        self.use_vision = use_vision
        self.use_dom = use_dom


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


async def create_agent(
    page: "Page",
    config: Optional[AgentConfig] = None,
) -> Agent:
    """Create an agent with the given configuration.

    Args:
        page: Browser page to control.
        config: Agent configuration.

    Returns:
        Configured Agent instance.
    """
    from kuromi_browser.llm import OpenAIProvider, AnthropicProvider

    config = config or AgentConfig()

    # Create LLM provider
    if config.provider.lower() == "openai":
        llm = OpenAIProvider(api_key=config.api_key, model=config.model)
    elif config.provider.lower() in ("anthropic", "claude"):
        llm = AnthropicProvider(api_key=config.api_key, model=config.model)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")

    # Create agent
    agent = Agent(
        llm,
        page,
        use_vision=config.use_vision,
        use_dom=config.use_dom,
    )

    return agent


__all__ = [
    "Agent",
    "AgentResult",
    "AgentConfig",
    "AgentActions",
    "Action",
    "ActionType",
    "ActionResult",
    "create_agent",
]
