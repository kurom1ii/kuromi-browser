"""
OpenAI LLM Provider for kuromi-browser.
"""

import base64
import os
from typing import Any, Optional

from kuromi_browser.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for GPT models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: Model to use (default: gpt-4o).
            base_url: Custom base URL for API requests.
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._base_url = base_url
        self._client: Any = None

    async def _ensure_client(self) -> None:
        """Initialize the OpenAI client if needed."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai package is required. Install with: pip install openai"
                )

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

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
            **kwargs: Additional arguments passed to the API.

        Returns:
            The assistant's response text.
        """
        await self._ensure_client()

        response = await self._client.chat.completions.create(
            model=kwargs.pop("model", self._model),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        return response.choices[0].message.content or ""

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
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional arguments passed to the API.

        Returns:
            The assistant's response text.
        """
        await self._ensure_client()

        # Build messages with images
        vision_messages = []
        for msg in messages:
            if msg["role"] == "user" and images:
                # Add images to the last user message
                content = []
                if msg.get("content"):
                    content.append({"type": "text", "text": msg["content"]})
                for image_data in images:
                    base64_image = base64.b64encode(image_data).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    })
                vision_messages.append({"role": msg["role"], "content": content})
                images = []  # Only add images once
            else:
                vision_messages.append(msg)

        response = await self._client.chat.completions.create(
            model=kwargs.pop("model", self._model),
            messages=vision_messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs,
        )

        return response.choices[0].message.content or ""


__all__ = ["OpenAIProvider"]
