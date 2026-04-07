"""Google Gemini image generation provider."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from google import genai
from google.genai import types

from bananarama.models.base import ImageProvider, ImageRequest, ImageResult, TokenUsage

GEMINI_MODELS = [
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image",
]

SYSTEM_PROMPT = (
    "Draw a picture based on the user's description, carefully following their "
    "specified style. Do not include text unless explicitly requested."
)


class GeminiProvider(ImageProvider):
    """Image generation using Google Gemini via the google-genai SDK."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        self.model = model
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def _build_config(self, request: ImageRequest) -> types.GenerateContentConfig:
        """Build the generation config for a request."""
        image_config: dict[str, Any] = {"aspect_ratio": request.aspect_ratio}

        if self.model == "gemini-3-pro-image-preview":
            image_config["image_size"] = request.resolution

        config_kwargs: dict[str, Any] = {
            "response_modalities": ["TEXT", "IMAGE"],
            "system_instruction": SYSTEM_PROMPT,
            "image_config": types.ImageConfig(**image_config),
        }

        if request.seed is not None:
            config_kwargs["seed"] = request.seed

        return types.GenerateContentConfig(**config_kwargs)

    def _build_contents(self, request: ImageRequest) -> list[types.Part]:
        """Build the content parts for a request."""
        parts: list[types.Part] = [types.Part.from_text(text=request.prompt)]

        for img_bytes in request.reference_images:
            b64_data = base64.b64encode(img_bytes).decode("ascii")
            parts.append(
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=b64_data.encode("ascii"),
                    )
                )
            )

        return parts

    def _extract_result(self, response: types.GenerateContentResponse) -> ImageResult:
        """Extract image data and token usage from a response."""
        image_data: bytes | None = None

        if response.candidates:
            candidate = response.candidates[0]
            content = candidate.content
            if content and content.parts:
                for part in content.parts:
                    if part.inline_data and part.inline_data.data:
                        raw = part.inline_data.data
                        if isinstance(raw, str):
                            image_data = base64.b64decode(raw)
                        else:
                            image_data = bytes(raw)
                        break

        if image_data is None:
            text_parts: list[str] = []
            if response.candidates:
                candidate = response.candidates[0]
                content = candidate.content
                if content and content.parts:
                    for part in content.parts:
                        if part.text:
                            text_parts.append(part.text)
            text = "\n".join(text_parts) if text_parts else ""
            msg = f"Gemini did not return an image. Response: {text}"
            raise RuntimeError(msg)

        input_tokens = TokenUsage()
        output_tokens = TokenUsage()

        usage = response.usage_metadata
        if usage:
            if usage.prompt_tokens_details:
                for detail in usage.prompt_tokens_details:
                    modality = (detail.modality or "TEXT").upper()
                    count = detail.token_count or 0
                    if modality == "IMAGE":
                        input_tokens.image += count
                    else:
                        input_tokens.text += count

            if usage.candidates_tokens_details:
                for detail in usage.candidates_tokens_details:
                    modality = (detail.modality or "TEXT").upper()
                    count = detail.token_count or 0
                    if modality == "IMAGE":
                        output_tokens.image += count
                    else:
                        output_tokens.text += count

        return ImageResult(
            image_data=image_data,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate a single image."""
        config = self._build_config(request)
        contents = self._build_contents(request)

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=contents,  # type: ignore[arg-type]
            config=config,
        )

        return self._extract_result(response)

    async def generate_batch(
        self, requests: list[ImageRequest]
    ) -> list[ImageResult | BaseException]:
        """Generate multiple images concurrently."""
        tasks = [self.generate(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(results)
