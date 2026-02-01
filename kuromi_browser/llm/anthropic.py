"""
Anthropic LLM Provider for kuromi-browser.
"""

import base64
import os
from typing import Any, Optional

from kuromi_browser.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic API provider for Claude models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model to use (default: claude-sonnet-4-20250514).
        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = model
        self._client: Any = None

    async def _ensure_client(self) -> None:
        """Initialize the Anthropic client if needed."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise ImportError(
                    "anthropic package is required. Install with: pip install anthropic"
                )

            self._client = AsyncAnthropic(api_key=self._api_key)

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
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional arguments passed to the API.

        Returns:
            The assistant's response text.
        """
        await self._ensure_client()

        # Extract system message if present
        system_message = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        response = await self._client.messages.create(
            model=kwargs.pop("model", self._model),
            messages=chat_messages,
            system=system_message or "",
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        return response.content[0].text

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
            images: List of image data as bytes (PNG/JPEG).
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional arguments passed to the API.

        Returns:
            The assistant's response text.
        """
        await self._ensure_client()

        # Extract system message if present
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user" and images:
                # Add images to the user message
                content = []
                for image_data in images:
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_image,
                        },
                    })
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                chat_messages.append({"role": msg["role"], "content": content})
                images = []  # Only add images once
            else:
                chat_messages.append(msg)

        response = await self._client.messages.create(
            model=kwargs.pop("model", self._model),
            messages=chat_messages,
            system=system_message or "",
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        return response.content[0].text


__all__ = ["AnthropicProvider"]
