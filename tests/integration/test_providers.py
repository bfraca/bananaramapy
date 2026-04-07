"""Integration tests for image generation providers.

These tests make real API calls and require API keys.
Run with: ``pytest -m integration``

Required environment variables:
  - GEMINI_API_KEY   — for Gemini tests
  - OPENAI_API_KEY   — for OpenAI tests
  - TOGETHER_API_KEY — for FLUX tests
"""

from __future__ import annotations

import pytest

from bananarama.models.base import ImageRequest

from .conftest import requires_gemini, requires_openai, requires_together

pytestmark = pytest.mark.integration


@requires_gemini
class TestGeminiProvider:
    """Integration tests for the Gemini provider."""

    async def test_generate_simple_image(self) -> None:
        from bananarama.models.gemini import GeminiProvider

        provider = GeminiProvider(model="gemini-2.5-flash-image")
        request = ImageRequest(
            prompt="A simple red circle on a white background",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        assert result.image_data
        assert len(result.image_data) > 100
        assert result.model == "gemini-2.5-flash-image"

    async def test_token_usage_populated(self) -> None:
        from bananarama.models.gemini import GeminiProvider

        provider = GeminiProvider(model="gemini-2.5-flash-image")
        request = ImageRequest(
            prompt="A blue square",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        # Gemini should return token usage metadata
        assert result.input_tokens.text > 0 or result.input_tokens.image > 0
        assert result.output_tokens.image > 0

    async def test_cost_computed(self) -> None:
        from bananarama.costs.pricing import compute_cost
        from bananarama.models.gemini import GeminiProvider

        provider = GeminiProvider(model="gemini-2.5-flash-image")
        request = ImageRequest(
            prompt="A green triangle",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        cost = compute_cost(result)
        assert cost > 0


@requires_openai
class TestOpenAIProvider:
    """Integration tests for the OpenAI provider."""

    async def test_generate_simple_image(self) -> None:
        from bananarama.models.openai import OpenAIProvider

        provider = OpenAIProvider(model="gpt-image-1")
        request = ImageRequest(
            prompt="A simple yellow star on a dark background",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        assert result.image_data
        assert len(result.image_data) > 100
        assert result.model == "gpt-image-1"

    async def test_cost_computed(self) -> None:
        from bananarama.costs.pricing import compute_cost
        from bananarama.models.openai import OpenAIProvider

        provider = OpenAIProvider(model="gpt-image-1")
        request = ImageRequest(
            prompt="A purple hexagon",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        cost = compute_cost(result)
        assert cost > 0


@requires_together
class TestFluxProvider:
    """Integration tests for the FLUX provider (via Together AI)."""

    async def test_generate_simple_image(self) -> None:
        from bananarama.models.flux import FluxProvider

        provider = FluxProvider(model="flux-2-schnell")
        request = ImageRequest(
            prompt="A simple orange diamond on a white background",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        assert result.image_data
        assert len(result.image_data) > 100
        assert result.model == "flux-2-schnell"

    async def test_seed_reproducibility(self) -> None:
        from bananarama.models.flux import FluxProvider

        provider = FluxProvider(model="flux-2-schnell")
        request = ImageRequest(
            prompt="A cyan circle",
            aspect_ratio="1:1",
            resolution="1K",
            seed=42,
        )
        result1 = await provider.generate(request)
        result2 = await provider.generate(request)
        # Same seed should produce identical images
        assert result1.image_data == result2.image_data

    async def test_per_image_cost(self) -> None:
        from bananarama.costs.pricing import compute_cost
        from bananarama.models.flux import FluxProvider

        provider = FluxProvider(model="flux-2-schnell")
        request = ImageRequest(
            prompt="A magenta pentagon",
            aspect_ratio="1:1",
            resolution="1K",
        )
        result = await provider.generate(request)
        cost = compute_cost(result)
        # FLUX uses flat per-image pricing
        assert cost > 0
