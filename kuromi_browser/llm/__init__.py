"""
LLM integration module for kuromi-browser.

This module provides LLM client integrations:
- LLMProvider: Abstract base for LLM providers
- OpenAIProvider: OpenAI API integration
- AnthropicProvider: Anthropic Claude API integration
- PromptTemplates: Pre-built prompts for browser automation
"""

from kuromi_browser.llm.base import LLMProvider, LLMResponse, Message
from kuromi_browser.llm.openai import OpenAIProvider
from kuromi_browser.llm.anthropic import AnthropicProvider


class PromptTemplates:
    """Pre-built prompt templates for browser automation."""

    SYSTEM_AGENT = """You are a browser automation agent. Your goal is to complete tasks on web pages.

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
    "LLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "PromptTemplates",
]
