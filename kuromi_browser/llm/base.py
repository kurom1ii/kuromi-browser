"""
Base LLM Provider interface for kuromi-browser.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


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


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The assistant's response text.
        """
        ...

    @abstractmethod
    async def chat_with_vision(
        self,
        messages: list[dict],
        images: list[bytes],
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request with image inputs.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            images: List of image data as bytes.
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The assistant's response text.
        """
        ...


__all__ = [
    "Message",
    "LLMResponse",
    "LLMProvider",
]
