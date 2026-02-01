"""
AI Agent for browser automation in kuromi-browser.
"""

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from kuromi_browser.agent.actions import Action, ActionResult, ActionType
from kuromi_browser.interfaces import BaseAgent
from kuromi_browser.llm.base import LLMProvider

if TYPE_CHECKING:
    from kuromi_browser.page import Page


@dataclass
class AgentResult:
    """Result of running an agent task."""

    success: bool
    task: str
    result: Any = None
    error: Optional[str] = None
    steps: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "task": self.task,
            "result": self.result,
            "error": self.error,
            "steps": self.steps,
            "history": self.history,
        }


class Agent(BaseAgent):
    """AI-powered browser automation agent.

    Uses LLMs to understand tasks, plan actions, and execute them
    on web pages automatically.
    """

    SYSTEM_PROMPT = """You are a browser automation agent. Your goal is to complete tasks on web pages.

You can perform the following actions:
- navigate: {"url": "..."} - Navigate to a URL
- click: {"selector": "..."} - Click on an element
- type: {"selector": "...", "text": "..."} - Type text into an element
- fill: {"selector": "...", "value": "..."} - Fill an input field
- scroll: {"direction": "up|down", "amount": 500} - Scroll the page
- hover: {"selector": "..."} - Hover over an element
- press: {"key": "..."} - Press a keyboard key
- wait: {"ms": 1000} - Wait for a duration
- screenshot: {} - Take a screenshot
- extract: {"selector": "..."} - Extract text from element
- done: {"result": ...} - Task completed successfully
- fail: {"reason": "..."} - Task failed

Respond with JSON only: {"type": "action_type", "args": {...}, "reasoning": "..."}
"""

    def __init__(
        self,
        llm: LLMProvider,
        page: Optional["Page"] = None,
    ) -> None:
        """Initialize the agent.

        Args:
            llm: LLM provider for decision making.
            page: Browser page to control (optional, can be set later).
        """
        self._llm = llm
        self._page = page
        self._history: list[dict[str, Any]] = []
        self._current_step = 0

    @property
    def page(self) -> Optional["Page"]:
        """Get the current page."""
        return self._page

    @page.setter
    def page(self, value: "Page") -> None:
        """Set the page to control."""
        self._page = value

    @property
    def history(self) -> list[dict[str, Any]]:
        """Get the action history."""
        return self._history.copy()

    async def run(
        self,
        task: str,
        *,
        max_steps: int = 10,
        timeout: Optional[float] = None,
    ) -> AgentResult:
        """Run the agent to complete a task.

        Args:
            task: Description of the task to complete.
            max_steps: Maximum number of steps to take.
            timeout: Timeout in seconds (not yet implemented).

        Returns:
            AgentResult with success status and any extracted data.
        """
        if self._page is None:
            return AgentResult(
                success=False,
                task=task,
                error="No page set for the agent",
            )

        self._history = []
        self._current_step = 0

        try:
            for step in range(max_steps):
                self._current_step = step + 1

                # Take screenshot for vision
                screenshot = await self._page.screenshot()

                # Think about what to do next
                action = await self._think(task, screenshot)

                # Record the action
                self._history.append({
                    "step": self._current_step,
                    "action": action.to_dict(),
                })

                # Check if we're done
                if action.type == ActionType.DONE:
                    return AgentResult(
                        success=True,
                        task=task,
                        result=action.args.get("result"),
                        steps=self._current_step,
                        history=self._history,
                    )

                if action.type == ActionType.FAIL:
                    return AgentResult(
                        success=False,
                        task=task,
                        error=action.args.get("reason", "Task failed"),
                        steps=self._current_step,
                        history=self._history,
                    )

                # Execute the action
                result = await self._execute(action)

                # Record the result
                self._history[-1]["result"] = result.to_dict()

                if not result.success:
                    # Continue even on failure, let the agent decide what to do
                    pass

            # Max steps reached
            return AgentResult(
                success=False,
                task=task,
                error=f"Max steps ({max_steps}) reached without completing task",
                steps=self._current_step,
                history=self._history,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                task=task,
                error=str(e),
                steps=self._current_step,
                history=self._history,
            )

    async def _think(self, task: str, screenshot: Optional[bytes] = None) -> Action:
        """Use LLM to decide the next action.

        Args:
            task: The task to complete.
            screenshot: Current page screenshot.

        Returns:
            The action to perform.
        """
        # Build context from history
        history_context = ""
        if self._history:
            history_context = "\n\nPrevious actions:\n"
            for entry in self._history[-5:]:  # Last 5 actions
                action = entry["action"]
                result = entry.get("result", {})
                history_context += f"- {action['type']}: {action.get('args', {})} -> {'success' if result.get('success') else 'failed'}\n"

        # Build the prompt
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Task: {task}\n\nStep: {self._current_step}{history_context}\n\nBased on the current screenshot, what action should we take next?",
            },
        ]

        # Get LLM response
        if screenshot:
            response = await self._llm.chat_with_vision(messages, [screenshot])
        else:
            response = await self._llm.chat(messages)

        # Parse the response as JSON
        return self._parse_action_response(response)

    def _parse_action_response(self, response: str) -> Action:
        """Parse LLM response into an Action.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed Action object.
        """
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return Action.from_dict(data)
        except json.JSONDecodeError:
            pass

        # Fallback: create a fail action
        return Action.fail(f"Could not parse LLM response: {response[:100]}")

    async def _execute(self, action: Action) -> ActionResult:
        """Execute an action on the page.

        Args:
            action: The action to execute.

        Returns:
            ActionResult with success status and any data.
        """
        if self._page is None:
            return ActionResult(
                success=False,
                action=action,
                error="No page set",
            )

        try:
            data = None

            if action.type == ActionType.NAVIGATE:
                await self._page.goto(action.args["url"])

            elif action.type == ActionType.CLICK:
                await self._page.click(action.args["selector"])

            elif action.type == ActionType.TYPE:
                await self._page.type(
                    action.args["selector"],
                    action.args["text"],
                )

            elif action.type == ActionType.FILL:
                await self._page.fill(
                    action.args["selector"],
                    action.args["value"],
                )

            elif action.type == ActionType.SCROLL:
                direction = action.args.get("direction", "down")
                amount = action.args.get("amount", 500)
                scroll_y = amount if direction == "down" else -amount
                await self._page.evaluate(f"window.scrollBy(0, {scroll_y})")

            elif action.type == ActionType.HOVER:
                await self._page.hover(action.args["selector"])

            elif action.type == ActionType.PRESS:
                # Press on body or focused element
                await self._page.press("body", action.args["key"])

            elif action.type == ActionType.WAIT:
                await self._page.wait_for_timeout(action.args.get("ms", 1000))

            elif action.type == ActionType.SCREENSHOT:
                data = await self._page.screenshot()

            elif action.type == ActionType.EXTRACT:
                element = await self._page.query_selector(action.args["selector"])
                if element:
                    data = await element.text_content()

            elif action.type == ActionType.BACK:
                await self._page.go_back()

            elif action.type == ActionType.FORWARD:
                await self._page.go_forward()

            elif action.type == ActionType.RELOAD:
                await self._page.reload()

            elif action.type in (ActionType.DONE, ActionType.FAIL):
                # These are handled in the run loop
                pass

            else:
                return ActionResult(
                    success=False,
                    action=action,
                    error=f"Unknown action type: {action.type}",
                )

            return ActionResult(success=True, action=action, data=data)

        except Exception as e:
            return ActionResult(
                success=False,
                action=action,
                error=str(e),
            )

    # BaseAgent interface methods
    async def step(self, instruction: str) -> Any:
        """Execute a single step based on an instruction."""
        if self._page is None:
            raise RuntimeError("No page set for the agent")

        screenshot = await self._page.screenshot()
        action = await self._think(instruction, screenshot)
        result = await self._execute(action)
        return result.to_dict()

    async def observe(self) -> dict[str, Any]:
        """Observe the current state of the page."""
        if self._page is None:
            return {"error": "No page set"}

        return {
            "url": self._page.url,
            "title": self._page.title,
        }

    async def act(self, action: str, *args: Any, **kwargs: Any) -> Any:
        """Perform an action on the page."""
        try:
            action_type = ActionType(action.lower())
        except ValueError:
            return {"success": False, "error": f"Unknown action: {action}"}

        action_obj = Action(type=action_type, args=kwargs)
        result = await self._execute(action_obj)
        return result.to_dict()

    async def plan(self, goal: str) -> list[str]:
        """Generate a plan to achieve a goal."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Create a step-by-step plan to achieve this goal: {goal}\n\nRespond with a numbered list of actions.",
            },
        ]

        response = await self._llm.chat(messages)

        # Parse numbered list
        steps = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove number prefix
                step = re.sub(r"^\d+[\.\)]\s*", "", line)
                step = step.lstrip("- ")
                if step:
                    steps.append(step)

        return steps

    async def reflect(
        self,
        observation: dict[str, Any],
        action: str,
        result: Any,
    ) -> str:
        """Reflect on an action's result."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Observation: {observation}\nAction taken: {action}\nResult: {result}\n\nReflect on this result. Was it successful? What should we do next?",
            },
        ]

        return await self._llm.chat(messages)


__all__ = [
    "Agent",
    "AgentResult",
]
