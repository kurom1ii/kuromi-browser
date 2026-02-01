"""
Task Parser for natural language to browser actions in kuromi-browser.

This module converts natural language task descriptions into structured
browser actions that can be executed by the Agent.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kuromi_browser.llm.base import LLMProvider
    from kuromi_browser.page import Page


class TaskType(str, Enum):
    """High-level task type."""

    NAVIGATION = "navigation"
    FORM_FILL = "form_fill"
    CLICK = "click"
    EXTRACTION = "extraction"
    SEARCH = "search"
    LOGIN = "login"
    PURCHASE = "purchase"
    DOWNLOAD = "download"
    SCROLL = "scroll"
    WAIT = "wait"
    CUSTOM = "custom"


@dataclass
class ParsedAction:
    """A single parsed action from natural language."""

    action_type: str
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: float = 1.0
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for Agent."""
        result: dict[str, Any] = {"type": self.action_type}

        if self.selector:
            result["args"] = {"selector": self.selector}
        else:
            result["args"] = {}

        if self.value:
            if self.action_type in ("type", "fill"):
                result["args"]["text" if self.action_type == "type" else "value"] = self.value
            elif self.action_type == "navigate":
                result["args"]["url"] = self.value
            else:
                result["args"]["value"] = self.value

        if self.url:
            result["args"]["url"] = self.url

        if self.reasoning:
            result["reasoning"] = self.reasoning

        return result


@dataclass
class ParsedTask:
    """Complete parsed task with multiple steps."""

    original_text: str
    task_type: TaskType
    steps: list[ParsedAction]
    variables: dict[str, str] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original": self.original_text,
            "type": self.task_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
        }


class TaskParser:
    """Parses natural language tasks into browser actions.

    Uses LLM to understand task intent and convert to structured actions.
    Also supports pattern matching for common tasks without LLM.

    Example:
        parser = TaskParser(llm_provider)

        # Parse a task
        task = await parser.parse("Go to google.com and search for 'python'")
        for step in task.steps:
            print(step.to_dict())

        # Or parse with page context
        task = await parser.parse_with_context(page, "Click the login button")
    """

    # System prompt for task parsing
    SYSTEM_PROMPT = """You are a browser automation task parser. Convert natural language tasks into structured browser actions.

Available actions:
- navigate: {"url": "..."} - Go to a URL
- click: {"selector": "..."} - Click an element
- type: {"selector": "...", "text": "..."} - Type text
- fill: {"selector": "...", "value": "..."} - Fill a form field
- scroll: {"direction": "up|down", "amount": 500} - Scroll page
- hover: {"selector": "..."} - Hover over element
- press: {"key": "..."} - Press keyboard key
- wait: {"ms": 1000} - Wait for duration
- extract: {"selector": "..."} - Extract text from element
- screenshot: {} - Take screenshot
- select: {"selector": "...", "value": "..."} - Select dropdown option
- check: {"selector": "..."} - Check checkbox
- uncheck: {"selector": "..."} - Uncheck checkbox

Respond with JSON array of actions:
[
  {"type": "action", "args": {...}, "reasoning": "why this action"},
  ...
]

For selectors, prefer:
1. ID: #element-id
2. Name: [name="field-name"]
3. Text content: text:Button Text
4. Placeholder: [placeholder="..."]
5. ARIA: [aria-label="..."]
6. CSS class: .class-name

Be specific and use the most reliable selectors possible."""

    # Pattern-based parsing for common tasks (no LLM needed)
    PATTERNS = [
        # Navigation patterns
        (r"(?:go to|navigate to|open|visit)\s+(?:the\s+)?(?:url\s+)?['\"]?([^\s'\"]+)['\"]?",
         lambda m: [ParsedAction("navigate", url=m.group(1))]),

        # Search patterns
        (r"search\s+(?:for\s+)?['\"]([^'\"]+)['\"]",
         lambda m: [
             ParsedAction("fill", selector="input[type='search'], input[name='q'], input[name='search'], #search", value=m.group(1)),
             ParsedAction("press", value="Enter"),
         ]),

        # Click patterns
        (r"click\s+(?:on\s+)?(?:the\s+)?['\"]([^'\"]+)['\"]",
         lambda m: [ParsedAction("click", selector=f"text:{m.group(1)}")]),
        (r"click\s+(?:on\s+)?(?:the\s+)?(.+?)\s+button",
         lambda m: [ParsedAction("click", selector=f"button:has-text('{m.group(1)}')")]),
        (r"click\s+(?:on\s+)?(?:the\s+)?(.+?)\s+link",
         lambda m: [ParsedAction("click", selector=f"a:has-text('{m.group(1)}')")]),

        # Type patterns
        (r"type\s+['\"]([^'\"]+)['\"](?:\s+(?:in|into)\s+(?:the\s+)?(.+))?",
         lambda m: [ParsedAction("type", selector=m.group(2) or "input:focus", value=m.group(1))]),
        (r"enter\s+['\"]([^'\"]+)['\"](?:\s+(?:in|into)\s+(?:the\s+)?(.+))?",
         lambda m: [ParsedAction("fill", selector=m.group(2) or "input:focus", value=m.group(1))]),

        # Fill patterns
        (r"fill\s+(?:in\s+)?(?:the\s+)?(.+?)\s+(?:field\s+)?with\s+['\"]([^'\"]+)['\"]",
         lambda m: [ParsedAction("fill", selector=m.group(1), value=m.group(2))]),

        # Scroll patterns
        (r"scroll\s+(up|down)(?:\s+(\d+))?",
         lambda m: [ParsedAction("scroll", value=f"{m.group(1)}:{m.group(2) or '500'}")]),
        (r"scroll\s+to\s+(?:the\s+)?(top|bottom)",
         lambda m: [ParsedAction("scroll", value=f"{'up' if m.group(1) == 'top' else 'down'}:max")]),

        # Wait patterns
        (r"wait\s+(?:for\s+)?(\d+)\s*(?:ms|milliseconds)?",
         lambda m: [ParsedAction("wait", value=m.group(1))]),
        (r"wait\s+(?:for\s+)?(\d+)\s*(?:s|seconds?)",
         lambda m: [ParsedAction("wait", value=str(int(m.group(1)) * 1000))]),

        # Extract patterns
        (r"(?:get|extract|read)\s+(?:the\s+)?text\s+(?:from\s+)?(?:the\s+)?(.+)",
         lambda m: [ParsedAction("extract", selector=m.group(1))]),

        # Screenshot patterns
        (r"(?:take|capture)\s+(?:a\s+)?screenshot",
         lambda m: [ParsedAction("screenshot")]),

        # Press key patterns
        (r"press\s+(?:the\s+)?(\w+)(?:\s+key)?",
         lambda m: [ParsedAction("press", value=m.group(1))]),

        # Login patterns
        (r"log\s*in\s+(?:with\s+)?(?:username\s+)?['\"]([^'\"]+)['\"](?:\s+(?:and\s+)?password\s+['\"]([^'\"]+)['\"])?",
         lambda m: [
             ParsedAction("fill", selector="input[type='text'], input[type='email'], input[name='username'], input[name='email'], #username, #email", value=m.group(1)),
             ParsedAction("fill", selector="input[type='password'], input[name='password'], #password", value=m.group(2) or ""),
             ParsedAction("click", selector="button[type='submit'], input[type='submit'], button:has-text('Log in'), button:has-text('Sign in')"),
         ] if m.group(2) else [
             ParsedAction("fill", selector="input[type='text'], input[type='email'], input[name='username'], input[name='email'], #username, #email", value=m.group(1)),
         ]),
    ]

    def __init__(
        self,
        llm: Optional["LLMProvider"] = None,
        *,
        use_patterns: bool = True,
        max_steps: int = 20,
    ) -> None:
        """Initialize Task Parser.

        Args:
            llm: LLM provider for complex parsing. If None, only patterns are used.
            use_patterns: Whether to try pattern matching first.
            max_steps: Maximum number of steps to generate.
        """
        self._llm = llm
        self._use_patterns = use_patterns
        self._max_steps = max_steps

    async def parse(
        self,
        task: str,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ParsedTask:
        """Parse a natural language task into structured actions.

        Args:
            task: Natural language task description.
            context: Optional context (URL, page state, etc.).

        Returns:
            ParsedTask with steps to execute.
        """
        task = task.strip()

        # Try pattern matching first
        if self._use_patterns:
            matched_steps = self._try_patterns(task)
            if matched_steps:
                task_type = self._infer_task_type(task)
                return ParsedTask(
                    original_text=task,
                    task_type=task_type,
                    steps=matched_steps,
                )

        # Fall back to LLM if available
        if self._llm:
            return await self._parse_with_llm(task, context)

        # No LLM, return basic task
        return ParsedTask(
            original_text=task,
            task_type=TaskType.CUSTOM,
            steps=[],
        )

    async def parse_with_context(
        self,
        page: "Page",
        task: str,
        *,
        include_screenshot: bool = False,
    ) -> ParsedTask:
        """Parse task with current page context.

        Args:
            page: Browser page for context.
            task: Natural language task.
            include_screenshot: Whether to include screenshot in analysis.

        Returns:
            ParsedTask with context-aware steps.
        """
        context = {
            "url": page.url,
            "title": page.title,
        }

        # Get DOM snapshot for context
        from kuromi_browser.ai.dom_serializer import DOMSerializer, SerializationFormat
        serializer = DOMSerializer(page, max_elements=50)
        snapshot = await serializer.serialize(SerializationFormat.TEXT)
        context["page_content"] = snapshot.to_text()

        # Parse with context
        return await self.parse(task, context=context)

    def _try_patterns(self, task: str) -> list[ParsedAction]:
        """Try to match task against known patterns.

        Args:
            task: Task text.

        Returns:
            List of actions if matched, empty list otherwise.
        """
        task_lower = task.lower()

        for pattern, action_builder in self.PATTERNS:
            match = re.search(pattern, task_lower, re.IGNORECASE)
            if match:
                try:
                    return action_builder(match)
                except Exception:
                    continue

        return []

    def _infer_task_type(self, task: str) -> TaskType:
        """Infer the high-level task type from text.

        Args:
            task: Task text.

        Returns:
            TaskType enum value.
        """
        task_lower = task.lower()

        if any(w in task_lower for w in ["go to", "navigate", "open", "visit"]):
            return TaskType.NAVIGATION
        if any(w in task_lower for w in ["fill", "enter", "type into"]):
            return TaskType.FORM_FILL
        if any(w in task_lower for w in ["click", "press", "tap"]):
            return TaskType.CLICK
        if any(w in task_lower for w in ["get", "extract", "read", "scrape"]):
            return TaskType.EXTRACTION
        if any(w in task_lower for w in ["search", "find", "look for"]):
            return TaskType.SEARCH
        if any(w in task_lower for w in ["log in", "login", "sign in"]):
            return TaskType.LOGIN
        if any(w in task_lower for w in ["buy", "purchase", "checkout", "add to cart"]):
            return TaskType.PURCHASE
        if any(w in task_lower for w in ["download", "save"]):
            return TaskType.DOWNLOAD
        if any(w in task_lower for w in ["scroll"]):
            return TaskType.SCROLL
        if any(w in task_lower for w in ["wait"]):
            return TaskType.WAIT

        return TaskType.CUSTOM

    async def _parse_with_llm(
        self,
        task: str,
        context: Optional[dict[str, Any]] = None,
    ) -> ParsedTask:
        """Use LLM to parse complex tasks.

        Args:
            task: Task text.
            context: Optional context information.

        Returns:
            ParsedTask with LLM-generated steps.
        """
        # Build prompt
        prompt = f"Convert this task to browser actions:\n\n{task}"

        if context:
            prompt += "\n\nCurrent page context:\n"
            if "url" in context:
                prompt += f"URL: {context['url']}\n"
            if "title" in context:
                prompt += f"Title: {context['title']}\n"
            if "page_content" in context:
                prompt += f"\nVisible elements:\n{context['page_content'][:2000]}\n"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await self._llm.chat(
            messages,
            temperature=0.2,
            max_tokens=1024,
        )

        # Parse JSON response
        steps = self._parse_llm_response(response)
        task_type = self._infer_task_type(task)

        return ParsedTask(
            original_text=task,
            task_type=task_type,
            steps=steps,
        )

    def _parse_llm_response(self, response: str) -> list[ParsedAction]:
        """Parse LLM response into actions.

        Args:
            response: LLM response text.

        Returns:
            List of parsed actions.
        """
        import json

        steps: list[ParsedAction] = []

        # Try to find JSON array in response
        try:
            # Find JSON array
            start = response.find("[")
            end = response.rfind("]") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                actions = json.loads(json_str)

                for action in actions[:self._max_steps]:
                    if isinstance(action, dict):
                        args = action.get("args", {})
                        steps.append(ParsedAction(
                            action_type=action.get("type", ""),
                            selector=args.get("selector"),
                            value=args.get("value") or args.get("text") or args.get("url"),
                            url=args.get("url"),
                            reasoning=action.get("reasoning"),
                        ))

        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return steps


class TaskDecomposer:
    """Decomposes complex tasks into simpler subtasks.

    Useful for breaking down high-level goals into atomic actions.
    """

    DECOMPOSITION_PROMPT = """Break down this high-level task into simple, atomic subtasks:

Task: {task}

Rules:
1. Each subtask should be a single browser action
2. Include all necessary steps (navigation, waiting, clicking, etc.)
3. Be explicit about what to click/fill/etc.
4. Handle potential obstacles (popups, loading, etc.)

Respond with numbered list of subtasks."""

    def __init__(self, llm: "LLMProvider") -> None:
        """Initialize decomposer.

        Args:
            llm: LLM provider.
        """
        self._llm = llm

    async def decompose(
        self,
        task: str,
        *,
        context: Optional[str] = None,
    ) -> list[str]:
        """Decompose a complex task into subtasks.

        Args:
            task: Complex task description.
            context: Optional context about current state.

        Returns:
            List of simpler subtask descriptions.
        """
        prompt = self.DECOMPOSITION_PROMPT.format(task=task)

        if context:
            prompt += f"\n\nCurrent context: {context}"

        messages = [{"role": "user", "content": prompt}]

        response = await self._llm.chat(
            messages,
            temperature=0.3,
            max_tokens=1024,
        )

        # Parse numbered list
        subtasks: list[str] = []
        for line in response.split("\n"):
            line = line.strip()
            # Match numbered items
            match = re.match(r"^\d+[\.\)]\s*(.+)$", line)
            if match:
                subtasks.append(match.group(1))
            elif line.startswith("- "):
                subtasks.append(line[2:])

        return subtasks


class TaskValidator:
    """Validates parsed tasks and checks for issues."""

    # Dangerous patterns to warn about
    DANGEROUS_PATTERNS = [
        (r"password", "Task involves password - ensure secure handling"),
        (r"credit\s*card", "Task involves payment info - verify security"),
        (r"delete|remove", "Task involves deletion - confirm action"),
        (r"submit|send", "Task submits data - verify correctness"),
    ]

    def validate(self, task: ParsedTask) -> list[str]:
        """Validate a parsed task.

        Args:
            task: Parsed task to validate.

        Returns:
            List of warning messages.
        """
        warnings: list[str] = []

        # Check for empty task
        if not task.steps:
            warnings.append("Task has no steps - may need LLM parsing")

        # Check for dangerous patterns
        task_text = task.original_text.lower()
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, task_text, re.IGNORECASE):
                warnings.append(message)

        # Check for invalid selectors
        for step in task.steps:
            if step.selector:
                if step.selector.count("'") % 2 != 0:
                    warnings.append(f"Unbalanced quotes in selector: {step.selector}")
                if step.selector.count('"') % 2 != 0:
                    warnings.append(f"Unbalanced quotes in selector: {step.selector}")

        # Check for missing values
        for step in task.steps:
            if step.action_type in ("fill", "type") and not step.value:
                warnings.append(f"Action '{step.action_type}' missing value")
            if step.action_type == "navigate" and not step.url:
                warnings.append("Navigate action missing URL")

        return warnings


async def parse_task(
    task: str,
    llm: Optional["LLMProvider"] = None,
) -> ParsedTask:
    """Convenience function to parse a task.

    Args:
        task: Natural language task.
        llm: Optional LLM for complex parsing.

    Returns:
        ParsedTask with steps.
    """
    parser = TaskParser(llm)
    return await parser.parse(task)


__all__ = [
    "TaskType",
    "ParsedAction",
    "ParsedTask",
    "TaskParser",
    "TaskDecomposer",
    "TaskValidator",
    "parse_task",
]
