"""Cost calculation for image generation.

Supports both token-based pricing (Gemini, OpenAI) and flat per-image
pricing (FLUX via Together AI). Phase 3 will load from prices.toml.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bananarama.models.base import ImageResult


@dataclass
class ModelPricing:
    """Per-million-token pricing for a model, broken down by modality."""

    input_text: float
    input_image: float
    output_text: float
    output_image: float


@dataclass
class PerImagePricing:
    """Flat per-image pricing for providers without token-level billing."""

    cost_per_image: float


# Token-based prices (per million tokens).
# Source: https://ai.google.dev/pricing (as of April 2026)
MODEL_PRICES: dict[str, ModelPricing] = {
    "gemini-3.1-flash-image-preview": ModelPricing(
        input_text=0.50,
        input_image=0.50,
        output_text=3.00,
        output_image=60.00,
    ),
    "gemini-3-pro-image-preview": ModelPricing(
        input_text=1.25,
        input_image=1.25,
        output_text=5.00,
        output_image=60.00,
    ),
    "gemini-2.5-flash-image": ModelPricing(
        input_text=0.15,
        input_image=0.15,
        output_text=0.60,
        output_image=60.00,
    ),
    # OpenAI: token-based pricing
    # Source: https://developers.openai.com/api/docs/models/gpt-image-1
    "gpt-image-1": ModelPricing(
        input_text=5.00,
        input_image=10.00,
        output_text=0.0,
        output_image=40.00,
    ),
    "gpt-image-1.5": ModelPricing(
        input_text=5.00,
        input_image=10.00,
        output_text=0.0,
        output_image=40.00,
    ),
}

# Flat per-image prices (for providers without token-level billing).
# Source: Together AI pricing (as of April 2026)
PER_IMAGE_PRICES: dict[str, PerImagePricing] = {
    "flux-2-pro": PerImagePricing(cost_per_image=0.05),
    "flux-2-dev": PerImagePricing(cost_per_image=0.025),
    "flux-2-schnell": PerImagePricing(cost_per_image=0.003),
}


def compute_cost(result: ImageResult) -> float:
    """Compute the dollar cost of a generation result.

    Uses token-based pricing when available, falling back to flat per-image
    pricing. Returns 0.0 if the model has no known pricing.
    """
    # Try token-based pricing first
    prices = MODEL_PRICES.get(result.model)
    if prices is not None:
        input_cost = (
            result.input_tokens.text * prices.input_text
            + result.input_tokens.image * prices.input_image
        ) / 1_000_000

        output_cost = (
            result.output_tokens.text * prices.output_text
            + result.output_tokens.image * prices.output_image
        ) / 1_000_000

        return input_cost + output_cost

    # Fall back to flat per-image pricing
    per_image = PER_IMAGE_PRICES.get(result.model)
    if per_image is not None:
        return per_image.cost_per_image

    return 0.0


def estimate_cost(model: str) -> float | None:
    """Return an estimated cost per image for a model, or None if unknown.

    For token-based models this is a rough estimate assuming typical usage.
    For per-image models this is the exact flat rate.
    """
    per_image = PER_IMAGE_PRICES.get(model)
    if per_image is not None:
        return per_image.cost_per_image

    prices = MODEL_PRICES.get(model)
    if prices is not None:
        # Rough estimate: ~500 input text tokens, ~300 output image tokens
        input_est = 500 * prices.input_text / 1_000_000
        output_est = 300 * prices.output_image / 1_000_000
        return input_est + output_est

    return None
