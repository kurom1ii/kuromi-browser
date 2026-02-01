"""
AI Integration module for kuromi-browser.

This module provides the AI layer that bridges LLM capabilities with
browser automation, including:

- DOMSerializer: Convert DOM to LLM-friendly formats
- VisionAnalyzer: Screenshot analysis with multimodal LLMs
- TaskParser: Natural language to browser actions
- AIAgent: High-level AI agent wrapper

Example:
    from kuromi_browser.ai import AIAgent, DOMSerializer, VisionAnalyzer

    # Create AI agent with page and LLM
    agent = AIAgent(page, llm_provider)

    # Run a natural language task
    result = await agent.run("Go to google.com and search for 'python'")

    # Or use components directly
    serializer = DOMSerializer(page)
    snapshot = await serializer.serialize()

    analyzer = VisionAnalyzer(llm_provider)
    analysis = await analyzer.analyze_page(page, "Find the login form")
"""

from typing import TYPE_CHECKING, Any, Optional

from kuromi_browser.ai.dom_serializer import (
    DOMSerializer,
    DOMSnapshot,
    ElementInfo,
    SerializationFormat,
    serialize_page_for_llm,
)
from kuromi_browser.ai.vision import (
    AnalysisType,
    ScreenshotAnalysis,
    VisualElement,
    VisionAnalyzer,
    analyze_screenshot,
)
from kuromi_browser.ai.task_parser import (
    ParsedAction,
    ParsedTask,
    TaskDecomposer,
    TaskParser,
    TaskType,
    TaskValidator,
    parse_task,
)

if TYPE_CHECKING:
    from kuromi_browser.page import Page
    from kuromi_browser.llm.base import LLMProvider
    from kuromi_browser.agent import Agent


class AIAgent:
    """High-level AI agent that combines all AI capabilities.

    Provides a unified interface for AI-powered browser automation,
    combining DOM serialization, vision analysis, task parsing,
    and the core Agent for execution.

    Example:
        # Create with page and LLM
        ai = AIAgent(page, openai_provider)

        # Run a task
        result = await ai.run("Fill out the contact form with name 'John'")

        # Or step-by-step control
        task = await ai.understand("Click the submit button")
        for step in task.steps:
            await ai.execute_step(step)
    """

    def __init__(
        self,
        page: "Page",
        llm: "LLMProvider",
        *,
        max_steps: int = 20,
        use_vision: bool = True,
        use_dom: bool = True,
        verbose: bool = False,
    ) -> None:
        """Initialize AI Agent.

        Args:
            page: Browser page to control.
            llm: LLM provider for AI capabilities.
            max_steps: Maximum steps per task.
            use_vision: Whether to use screenshot analysis.
            use_dom: Whether to use DOM serialization.
            verbose: Whether to print debug info.
        """
        self._page = page
        self._llm = llm
        self._max_steps = max_steps
        self._use_vision = use_vision
        self._use_dom = use_dom
        self._verbose = verbose

        # Initialize components
        self._serializer = DOMSerializer(page)
        self._vision = VisionAnalyzer(llm) if use_vision else None
        self._parser = TaskParser(llm)
        self._validator = TaskValidator()

        # Core agent for execution
        from kuromi_browser.agent import Agent
        self._agent = Agent(llm, page)

    @property
    def page(self) -> "Page":
        """Get the current page."""
        return self._page

    @page.setter
    def page(self, value: "Page") -> None:
        """Set the page to control."""
        self._page = value
        self._serializer = DOMSerializer(value)
        self._agent.page = value

    async def run(
        self,
        task: str,
        *,
        max_steps: Optional[int] = None,
        on_step: Optional[callable] = None,
    ) -> dict[str, Any]:
        """Run a natural language task.

        Args:
            task: Natural language task description.
            max_steps: Override default max steps.
            on_step: Optional callback after each step.

        Returns:
            Result dictionary with success status and data.
        """
        # Parse the task
        parsed = await self.understand(task)

        # Validate
        warnings = self._validator.validate(parsed)
        if warnings and self._verbose:
            for w in warnings:
                print(f"Warning: {w}")

        # If we have parsed steps, execute them
        if parsed.steps:
            return await self._execute_parsed_task(parsed, on_step)

        # Otherwise, fall back to the core agent
        result = await self._agent.run(
            task,
            max_steps=max_steps or self._max_steps,
        )

        return result.to_dict()

    async def understand(self, task: str) -> ParsedTask:
        """Parse and understand a task without executing.

        Args:
            task: Natural language task.

        Returns:
            ParsedTask with steps.
        """
        return await self._parser.parse_with_context(self._page, task)

    async def observe(self) -> dict[str, Any]:
        """Get current page state.

        Returns:
            Dictionary with page information.
        """
        result = {
            "url": self._page.url,
            "title": self._page.title,
        }

        # Add DOM info
        if self._use_dom:
            snapshot = await self._serializer.serialize()
            result["elements"] = [e.to_dict() for e in snapshot.elements[:20]]
            result["forms"] = snapshot.forms
            result["links_count"] = len(snapshot.links)

        # Add vision analysis
        if self._use_vision and self._vision:
            screenshot = await self._page.screenshot()
            analysis = await self._vision.analyze(screenshot, AnalysisType.GENERAL)
            result["visual_description"] = analysis.description

        return result

    async def analyze_page(
        self,
        analysis_type: AnalysisType = AnalysisType.GENERAL,
    ) -> ScreenshotAnalysis:
        """Analyze the current page visually.

        Args:
            analysis_type: Type of analysis to perform.

        Returns:
            ScreenshotAnalysis with findings.
        """
        if not self._vision:
            raise RuntimeError("Vision analysis not enabled")

        return await self._vision.analyze_page(
            self._page,
            analysis_type=analysis_type,
        )

    async def get_dom_snapshot(
        self,
        format: SerializationFormat = SerializationFormat.MARKDOWN,
    ) -> str:
        """Get serialized DOM snapshot.

        Args:
            format: Output format.

        Returns:
            Serialized DOM as string.
        """
        snapshot = await self._serializer.serialize(format)

        if format == SerializationFormat.TEXT:
            return snapshot.to_text()
        elif format == SerializationFormat.MARKDOWN:
            return snapshot.to_markdown()
        elif format == SerializationFormat.JSON:
            import json
            return json.dumps(snapshot.to_dict(), indent=2)
        else:
            return snapshot.to_text()

    async def execute_step(self, step: ParsedAction) -> dict[str, Any]:
        """Execute a single parsed action.

        Args:
            step: Action to execute.

        Returns:
            Result dictionary.
        """
        try:
            action_type = step.action_type.lower()

            if action_type == "navigate":
                url = step.url or step.value
                if url:
                    await self._page.goto(url)
                    return {"success": True, "action": "navigate", "url": url}

            elif action_type == "click":
                if step.selector:
                    await self._page.click(step.selector)
                    return {"success": True, "action": "click", "selector": step.selector}

            elif action_type == "type":
                if step.selector and step.value:
                    await self._page.type(step.selector, step.value)
                    return {"success": True, "action": "type"}

            elif action_type == "fill":
                if step.selector and step.value:
                    await self._page.fill(step.selector, step.value)
                    return {"success": True, "action": "fill"}

            elif action_type == "press":
                key = step.value or "Enter"
                await self._page.press("body", key)
                return {"success": True, "action": "press", "key": key}

            elif action_type == "scroll":
                direction = "down"
                amount = 500
                if step.value:
                    parts = step.value.split(":")
                    direction = parts[0] if parts else "down"
                    if len(parts) > 1 and parts[1] != "max":
                        amount = int(parts[1])
                    elif len(parts) > 1 and parts[1] == "max":
                        amount = 10000

                scroll_y = amount if direction == "down" else -amount
                await self._page.evaluate(f"window.scrollBy(0, {scroll_y})")
                return {"success": True, "action": "scroll", "direction": direction}

            elif action_type == "wait":
                ms = int(step.value) if step.value else 1000
                await self._page.wait_for_timeout(ms)
                return {"success": True, "action": "wait", "ms": ms}

            elif action_type == "screenshot":
                data = await self._page.screenshot()
                return {"success": True, "action": "screenshot", "size": len(data)}

            elif action_type == "extract":
                if step.selector:
                    element = await self._page.query_selector(step.selector)
                    if element:
                        text = await element.text_content()
                        return {"success": True, "action": "extract", "text": text}

            elif action_type == "hover":
                if step.selector:
                    await self._page.hover(step.selector)
                    return {"success": True, "action": "hover"}

            return {"success": False, "error": f"Unknown or incomplete action: {action_type}"}

        except Exception as e:
            return {"success": False, "error": str(e), "action": step.action_type}

    async def _execute_parsed_task(
        self,
        task: ParsedTask,
        on_step: Optional[callable] = None,
    ) -> dict[str, Any]:
        """Execute a parsed task step by step.

        Args:
            task: Parsed task with steps.
            on_step: Optional callback after each step.

        Returns:
            Result dictionary.
        """
        results: list[dict[str, Any]] = []
        success = True

        for i, step in enumerate(task.steps):
            if self._verbose:
                print(f"Step {i + 1}: {step.action_type} - {step.reasoning or ''}")

            result = await self.execute_step(step)
            results.append(result)

            if on_step:
                on_step(i, step, result)

            if not result.get("success"):
                success = False
                break

            # Small delay between steps
            await self._page.wait_for_timeout(100)

        return {
            "success": success,
            "task": task.original_text,
            "steps": len(results),
            "results": results,
        }


async def create_ai_agent(
    page: "Page",
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> AIAgent:
    """Create an AI agent with specified provider.

    Args:
        page: Browser page to control.
        provider: LLM provider ('openai' or 'anthropic').
        api_key: API key (or use env var).
        model: Model name override.

    Returns:
        Configured AIAgent.
    """
    from kuromi_browser.llm import OpenAIProvider, AnthropicProvider

    if provider.lower() == "openai":
        llm = OpenAIProvider(api_key=api_key, model=model or "gpt-4o")
    elif provider.lower() in ("anthropic", "claude"):
        llm = AnthropicProvider(api_key=api_key, model=model or "claude-sonnet-4-20250514")
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return AIAgent(page, llm)


__all__ = [
    # Main AI agent
    "AIAgent",
    "create_ai_agent",

    # DOM serialization
    "DOMSerializer",
    "DOMSnapshot",
    "ElementInfo",
    "SerializationFormat",
    "serialize_page_for_llm",

    # Vision analysis
    "VisionAnalyzer",
    "ScreenshotAnalysis",
    "VisualElement",
    "AnalysisType",
    "analyze_screenshot",

    # Task parsing
    "TaskParser",
    "ParsedTask",
    "ParsedAction",
    "TaskType",
    "TaskDecomposer",
    "TaskValidator",
    "parse_task",
]
