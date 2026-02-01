"""
LLM integration module for kuromi-browser.

This module provides LLM client integrations:
- LLMClient: Abstract base for LLM providers
- OpenAIClient: OpenAI API integration
- AnthropicClient: Anthropic Claude API integration
- PromptTemplates: Pre-built prompts for browser automation
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Chat message for LLM interaction."""

    role: str
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    usage: Optional[dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a completion request."""
        ...


class OpenAIClient(LLMClient):
    """OpenAI API client for GPT models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: Any = None

    async def _ensure_client(self) -> None:
        """Initialize the OpenAI client if needed."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

    async def chat(
        self,
        messages: list[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError

    async def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError


class AnthropicClient(LLMClient):
    """Anthropic API client for Claude models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any = None

    async def _ensure_client(self) -> None:
        """Initialize the Anthropic client if needed."""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=self._api_key)

    async def chat(
        self,
        messages: list[Message],
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError

    async def complete(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError


class PromptTemplates:
    """Pre-built prompt templates for browser automation."""

    SYSTEM_AGENT = """You are a browser automation agent. Your goal is to complete tasks on web pages.

You can perform the following actions:
- click(selector): Click on an element
- type(selector, text): Type text into an element
- fill(selector, value): Fill an input field
- press(key): Press a keyboard key
- scroll(direction, amount): Scroll the page
- hover(selector): Hover over an element
- select(selector, value): Select an option
- wait(ms): Wait for a duration
- goto(url): Navigate to a URL
- extract(selector): Extract text from element
- done(result): Task completed successfully
- fail(reason): Task failed

Respond with JSON: {"action": "action_name", "args": {...}, "reasoning": "..."}
"""

    OBSERVATION_PROMPT = """Current page state:
URL: {url}
Title: {title}

Visible elements:
{elements}

Task: {task}

What action should we take next?"""

    REFLECTION_PROMPT = """Previous action: {action}
Result: {result}

Was this successful? What should we do next?"""


__all__ = [
    "Message",
    "LLMResponse",
    "LLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "PromptTemplates",
]
