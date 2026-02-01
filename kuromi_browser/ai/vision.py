"""
Vision Analysis module for kuromi-browser.

This module provides screenshot analysis capabilities for LLM-based
browser automation, including visual element detection and OCR.
"""

import base64
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kuromi_browser.page import Page
    from kuromi_browser.llm.base import LLMProvider


class AnalysisType(str, Enum):
    """Type of visual analysis to perform."""

    GENERAL = "general"
    ELEMENTS = "elements"
    TEXT = "text"
    FORMS = "forms"
    NAVIGATION = "navigation"
    ERRORS = "errors"
    CAPTCHA = "captcha"


@dataclass
class VisualElement:
    """A visually detected element."""

    description: str
    element_type: str
    location: Optional[dict[str, float]] = None
    text: Optional[str] = None
    confidence: float = 1.0
    suggested_action: Optional[str] = None


@dataclass
class ScreenshotAnalysis:
    """Result of screenshot analysis."""

    description: str
    elements: list[VisualElement] = field(default_factory=list)
    text_content: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    is_error_page: bool = False
    has_captcha: bool = False
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "elements": [
                {
                    "description": e.description,
                    "type": e.element_type,
                    "location": e.location,
                    "text": e.text,
                    "suggested_action": e.suggested_action,
                }
                for e in self.elements
            ],
            "text_content": self.text_content,
            "suggestions": self.suggestions,
            "is_error_page": self.is_error_page,
            "has_captcha": self.has_captcha,
        }


class VisionAnalyzer:
    """Analyzes screenshots using LLM vision capabilities.

    Uses multimodal LLMs to understand page content visually,
    complementing DOM serialization for better automation.

    Example:
        analyzer = VisionAnalyzer(llm_provider)
        screenshot = await page.screenshot()
        analysis = await analyzer.analyze(screenshot, AnalysisType.ELEMENTS)

        # Or analyze page directly
        analysis = await analyzer.analyze_page(page, "Find the login button")
    """

    # Prompts for different analysis types
    ANALYSIS_PROMPTS = {
        AnalysisType.GENERAL: """Analyze this webpage screenshot and describe:
1. What type of page is this (login, search, article, etc.)?
2. What is the main purpose/content?
3. What are the key interactive elements visible?

Be concise and focus on actionable information.""",

        AnalysisType.ELEMENTS: """Identify all interactive elements in this screenshot:
- Buttons (with their text/purpose)
- Input fields (with their labels/purpose)
- Links (with their text)
- Dropdowns/selects
- Checkboxes/radio buttons

For each element, describe its approximate location (top-left, center, etc.)
and what action it likely performs.

Format as a list with: [type] "text/label" - location - purpose""",

        AnalysisType.TEXT: """Extract all visible text from this screenshot.
Organize by sections (headers, paragraphs, labels, buttons, etc.).
Include any error messages, notifications, or important callouts.""",

        AnalysisType.FORMS: """Analyze the forms visible in this screenshot:
1. What fields are present?
2. What are their labels and types?
3. Are any fields required?
4. What is the form's purpose?
5. Where is the submit button?

Provide structured information for form filling.""",

        AnalysisType.NAVIGATION: """Analyze the navigation structure:
1. What navigation menus are visible?
2. What are the main navigation options?
3. Is there a search bar?
4. Are there breadcrumbs?
5. What is the current page location in the site structure?""",

        AnalysisType.ERRORS: """Check for any errors or issues:
1. Are there any error messages visible?
2. Are there validation errors on form fields?
3. Is there a 404 or error page?
4. Are there any broken images or missing content?
5. Are there any popup dialogs or modals?

If errors exist, describe them in detail.""",

        AnalysisType.CAPTCHA: """Check if there's a CAPTCHA or bot detection:
1. Is there a CAPTCHA visible (reCAPTCHA, hCaptcha, etc.)?
2. Is there a "verify you're human" challenge?
3. Are there any bot detection warnings?
4. Is access blocked?

Describe the type and location if present.""",
    }

    def __init__(
        self,
        llm: "LLMProvider",
        *,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> None:
        """Initialize Vision Analyzer.

        Args:
            llm: LLM provider with vision capabilities.
            max_tokens: Maximum tokens for response.
            temperature: Sampling temperature (lower = more focused).
        """
        self._llm = llm
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def analyze(
        self,
        screenshot: bytes,
        analysis_type: AnalysisType = AnalysisType.GENERAL,
        *,
        custom_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ScreenshotAnalysis:
        """Analyze a screenshot.

        Args:
            screenshot: Screenshot image bytes (PNG/JPEG).
            analysis_type: Type of analysis to perform.
            custom_prompt: Override the default prompt.
            context: Additional context about the page/task.

        Returns:
            ScreenshotAnalysis with findings.
        """
        # Build the prompt
        prompt = custom_prompt or self.ANALYSIS_PROMPTS.get(
            analysis_type,
            self.ANALYSIS_PROMPTS[AnalysisType.GENERAL],
        )

        if context:
            prompt = f"Context: {context}\n\n{prompt}"

        # Send to LLM with vision
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        response = await self._llm.chat_with_vision(
            messages,
            [screenshot],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        # Parse the response
        return self._parse_response(response, analysis_type)

    async def analyze_page(
        self,
        page: "Page",
        task: Optional[str] = None,
        *,
        analysis_type: AnalysisType = AnalysisType.GENERAL,
        full_page: bool = False,
    ) -> ScreenshotAnalysis:
        """Analyze a page by taking and analyzing a screenshot.

        Args:
            page: Browser page to analyze.
            task: Optional task description for context.
            analysis_type: Type of analysis to perform.
            full_page: Whether to capture full page or viewport only.

        Returns:
            ScreenshotAnalysis with findings.
        """
        # Take screenshot
        screenshot = await page.screenshot(full_page=full_page)

        # Build context
        context = None
        if task:
            context = f"Task: {task}\nURL: {page.url}\nTitle: {page.title}"
        else:
            context = f"URL: {page.url}\nTitle: {page.title}"

        return await self.analyze(
            screenshot,
            analysis_type,
            context=context,
        )

    async def find_element(
        self,
        page: "Page",
        description: str,
    ) -> Optional[VisualElement]:
        """Find an element by visual description.

        Args:
            page: Browser page to search.
            description: Description of the element to find.

        Returns:
            VisualElement if found, None otherwise.
        """
        screenshot = await page.screenshot()

        prompt = f"""Find the element described as: "{description}"

Describe:
1. Is this element visible in the screenshot?
2. What type of element is it (button, link, input, etc.)?
3. Where is it located (describe position)?
4. What text or label does it have?
5. What CSS selector might identify it?

If the element is not visible, say "NOT FOUND" and explain why."""

        messages = [{"role": "user", "content": prompt}]

        response = await self._llm.chat_with_vision(
            messages,
            [screenshot],
            temperature=0.2,
            max_tokens=512,
        )

        if "NOT FOUND" in response.upper():
            return None

        return VisualElement(
            description=description,
            element_type="unknown",
            text=description,
            suggested_action=response,
        )

    async def describe_for_action(
        self,
        page: "Page",
        action: str,
    ) -> str:
        """Get guidance for performing an action.

        Args:
            page: Browser page.
            action: Action to perform (e.g., "click login button").

        Returns:
            Guidance text for performing the action.
        """
        screenshot = await page.screenshot()

        prompt = f"""I need to: {action}

Looking at this screenshot:
1. Can this action be performed?
2. What element should I interact with?
3. Describe the element precisely (text, position, appearance)
4. What CSS selector would identify it?
5. Any prerequisites (scrolling, closing popups, etc.)?

Provide clear, step-by-step guidance."""

        messages = [{"role": "user", "content": prompt}]

        response = await self._llm.chat_with_vision(
            messages,
            [screenshot],
            temperature=0.2,
            max_tokens=512,
        )

        return response

    async def compare_screenshots(
        self,
        before: bytes,
        after: bytes,
        action_taken: str,
    ) -> dict[str, Any]:
        """Compare two screenshots to assess action result.

        Args:
            before: Screenshot before action.
            after: Screenshot after action.
            action_taken: Description of the action taken.

        Returns:
            Comparison result with changes detected.
        """
        # Encode both images
        before_b64 = base64.b64encode(before).decode()
        after_b64 = base64.b64encode(after).decode()

        prompt = f"""Compare these two screenshots. The action taken was: {action_taken}

First image: BEFORE the action
Second image: AFTER the action

Analyze:
1. Did the action succeed?
2. What changed between the screenshots?
3. Are there any new elements (modals, messages, etc.)?
4. Is the page in the expected state?
5. Any errors or unexpected results?

Provide a structured comparison."""

        # This requires sending two images - implementation depends on LLM provider
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        # Note: Some providers support multiple images, others need separate calls
        response = await self._llm.chat_with_vision(
            messages,
            [before, after],
            temperature=0.3,
            max_tokens=512,
        )

        return {
            "action": action_taken,
            "analysis": response,
            "success": "success" in response.lower() or "succeeded" in response.lower(),
        }

    async def detect_state(
        self,
        page: "Page",
    ) -> dict[str, Any]:
        """Detect the current state of the page.

        Args:
            page: Browser page.

        Returns:
            State information including page type, loading status, etc.
        """
        screenshot = await page.screenshot()

        prompt = """Analyze the current state of this webpage:

1. Page type: (login, home, search results, product, checkout, error, etc.)
2. Loading state: (fully loaded, loading, partial)
3. User state: (logged in, logged out, unknown)
4. Active dialogs/modals: (yes/no, describe if yes)
5. Visible errors: (yes/no, describe if yes)
6. CAPTCHA present: (yes/no)
7. Main content area: (describe what's visible)

Respond in JSON format."""

        messages = [{"role": "user", "content": prompt}]

        response = await self._llm.chat_with_vision(
            messages,
            [screenshot],
            temperature=0.2,
            max_tokens=512,
        )

        # Try to parse JSON from response
        try:
            import json
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except Exception:
            pass

        return {
            "raw_analysis": response,
            "url": page.url,
            "title": page.title,
        }

    def _parse_response(
        self,
        response: str,
        analysis_type: AnalysisType,
    ) -> ScreenshotAnalysis:
        """Parse LLM response into structured analysis."""
        # Check for error indicators
        is_error = any(
            indicator in response.lower()
            for indicator in ["error", "404", "not found", "failed", "blocked"]
        )

        # Check for captcha
        has_captcha = any(
            indicator in response.lower()
            for indicator in ["captcha", "recaptcha", "hcaptcha", "verify you're human", "bot detection"]
        )

        # Extract elements if element analysis
        elements: list[VisualElement] = []
        if analysis_type == AnalysisType.ELEMENTS:
            elements = self._extract_elements(response)

        # Extract text content if text analysis
        text_content: list[str] = []
        if analysis_type == AnalysisType.TEXT:
            text_content = self._extract_text(response)

        # Generate suggestions based on analysis
        suggestions = self._generate_suggestions(response, analysis_type)

        return ScreenshotAnalysis(
            description=response,
            elements=elements,
            text_content=text_content,
            suggestions=suggestions,
            is_error_page=is_error and analysis_type == AnalysisType.ERRORS,
            has_captcha=has_captcha,
            raw_response=response,
        )

    def _extract_elements(self, response: str) -> list[VisualElement]:
        """Extract element information from response."""
        elements: list[VisualElement] = []

        # Simple parsing - look for common patterns
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for element type indicators
            element_type = None
            for etype in ["button", "input", "link", "dropdown", "checkbox", "radio", "select"]:
                if etype.lower() in line.lower():
                    element_type = etype
                    break

            if element_type:
                # Extract text in quotes
                import re
                text_match = re.search(r'"([^"]+)"', line)
                text = text_match.group(1) if text_match else None

                elements.append(VisualElement(
                    description=line,
                    element_type=element_type,
                    text=text,
                ))

        return elements

    def _extract_text(self, response: str) -> list[str]:
        """Extract text content from response."""
        text_content: list[str] = []

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 5:
                text_content.append(line)

        return text_content

    def _generate_suggestions(
        self,
        response: str,
        analysis_type: AnalysisType,
    ) -> list[str]:
        """Generate action suggestions from analysis."""
        suggestions: list[str] = []

        response_lower = response.lower()

        if "login" in response_lower or "sign in" in response_lower:
            suggestions.append("Consider filling in login credentials")

        if "search" in response_lower:
            suggestions.append("Search functionality available")

        if "captcha" in response_lower:
            suggestions.append("CAPTCHA detected - may need manual intervention")

        if "error" in response_lower:
            suggestions.append("Error detected - check page state")

        if "loading" in response_lower:
            suggestions.append("Page may still be loading - wait for content")

        return suggestions


async def analyze_screenshot(
    llm: "LLMProvider",
    screenshot: bytes,
    prompt: str,
) -> str:
    """Simple function to analyze a screenshot with custom prompt.

    Args:
        llm: LLM provider with vision capabilities.
        screenshot: Screenshot image bytes.
        prompt: Analysis prompt.

    Returns:
        LLM response text.
    """
    messages = [{"role": "user", "content": prompt}]
    return await llm.chat_with_vision(messages, [screenshot])


__all__ = [
    "AnalysisType",
    "VisualElement",
    "ScreenshotAnalysis",
    "VisionAnalyzer",
    "analyze_screenshot",
]
