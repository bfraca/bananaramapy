"""OpenAI image generation provider (gpt-image-1 / gpt-image-1.5)."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from bananarama.models.base import ImageProvider, ImageRequest, ImageResult, TokenUsage
from bananarama.models.sizing import resolve_openai_size

OPENAI_MODELS = [
    "gpt-image-1",
    "gpt-image-1.5",
]


class OpenAIProvider(ImageProvider):
    """Image generation using OpenAI's GPT-Image models.

    Requires the ``openai`` package: ``uv pip install bananarama[openai]``
    """

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            msg = (
                "OpenAI provider requires the 'openai' package. "
                "Install it with: uv pip install bananarama[openai]"
            )
            raise ImportError(msg) from None

        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate a single image via the OpenAI Images API."""
        size = resolve_openai_size(request.aspect_ratio, request.resolution)

        # Map resolution to quality
        quality: str = "high" if request.resolution in ("2K", "4K") else "medium"

        kwargs: dict[str, Any] = {
            "model": self.model,
            "prompt": request.prompt,
            "size": size,
            "quality": quality,
            "n": 1,
        }

        # Add reference images as input images if available
        if request.reference_images:
            input_images: list[dict[str, str]] = []
            for ref in request.reference_images:
                b64_str = base64.b64encode(ref.data).decode("ascii")
                data_uri = f"data:{ref.mime_type};base64,{b64_str}"
                input_images.append({"type": "base64", "url": data_uri})
            kwargs["image"] = input_images

        response = await self._client.images.generate(**kwargs)

        # Decode the returned image
        item = response.data[0]
        if item.b64_json:
            image_data = base64.b64decode(item.b64_json)
        elif item.url:
            # Fetch from URL if b64 not available
            import httpx

            async with httpx.AsyncClient() as http:
                img_resp = await http.get(item.url)
                img_resp.raise_for_status()
                image_data = img_resp.content
        else:
            msg = "OpenAI returned neither b64_json nor url"
            raise RuntimeError(msg)

        # Extract token usage if available
        input_tokens = TokenUsage()
        output_tokens = TokenUsage()
        usage: Any = getattr(response, "usage", None)
        if usage is not None:
            input_tokens.text = int(getattr(usage, "input_tokens", 0) or 0)
            raw_image_input: Any = getattr(usage, "input_tokens_details", None)
            input_tokens.image = (
                int(raw_image_input) if isinstance(raw_image_input, int) else 0
            )
            output_tokens.image = int(getattr(usage, "output_tokens", 0) or 0)

        return ImageResult(
            image_data=image_data,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate_batch(
        self, requests: list[ImageRequest]
    ) -> list[ImageResult | BaseException]:
        """Generate multiple images concurrently."""
        tasks = [self.generate(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(results)
