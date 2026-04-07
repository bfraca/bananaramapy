"""FLUX image generation provider via Together AI."""

from __future__ import annotations

import asyncio
import base64

from bananarama.models.base import ImageProvider, ImageRequest, ImageResult, TokenUsage
from bananarama.models.sizing import resolve_dimensions

FLUX_MODELS = [
    "flux-2-pro",
    "flux-2-dev",
    "flux-2-schnell",
]

# Together AI model name mapping.
_TOGETHER_MODEL_MAP: dict[str, str] = {
    "flux-2-pro": "black-forest-labs/FLUX.2-pro",
    "flux-2-dev": "black-forest-labs/FLUX.2-dev",
    "flux-2-schnell": "black-forest-labs/FLUX.2-schnell",
}


class FluxProvider(ImageProvider):
    """Image generation using FLUX models via Together AI.

    Requires the ``together`` package: ``uv pip install bananarama[flux]``
    """

    def __init__(self, model: str, api_key: str | None = None) -> None:
        try:
            from together import AsyncTogether
        except ImportError:
            msg = (
                "FLUX provider requires the 'together' package. "
                "Install it with: uv pip install bananarama[flux]"
            )
            raise ImportError(msg) from None

        self.model = model
        self._together_model = _TOGETHER_MODEL_MAP.get(model, model)
        self._client = AsyncTogether(api_key=api_key)

    async def generate(self, request: ImageRequest) -> ImageResult:
        """Generate a single image via Together AI's image API."""
        width, height = resolve_dimensions(
            request.aspect_ratio, request.resolution, provider="flux"
        )

        kwargs: dict[str, object] = {
            "model": self._together_model,
            "prompt": request.prompt,
            "width": width,
            "height": height,
            "n": 1,
            "response_format": "b64_json",
        }
        if request.seed is not None:
            kwargs["seed"] = request.seed

        response = await self._client.images.generate(**kwargs)

        item = response.data[0]
        if item.b64_json:
            image_data = base64.b64decode(item.b64_json)
        else:
            msg = "Together AI did not return b64_json image data"
            raise RuntimeError(msg)

        # FLUX via Together AI uses flat per-image pricing, no token breakdown.
        return ImageResult(
            image_data=image_data,
            model=self.model,
            input_tokens=TokenUsage(),
            output_tokens=TokenUsage(),
        )

    async def generate_batch(
        self, requests: list[ImageRequest]
    ) -> list[ImageResult | BaseException]:
        """Generate multiple images concurrently."""
        tasks = [self.generate(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return list(results)
