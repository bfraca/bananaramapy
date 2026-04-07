"""Cost calculation for image generation.

Phase 1: hardcoded pricing from API docs, calculated from real token usage.
Phase 3: will load from prices.toml and add dry-run estimates.
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


# Prices per million tokens.
# Source: https://ai.google.dev/pricing (as of April 2026)
# Phase 3: these will be loaded from a prices.toml data file.
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
}


def compute_cost(result: ImageResult) -> float:
    """Compute the dollar cost of a generation result from token usage.

    Returns 0.0 if the model has no known pricing.
    """
    prices = MODEL_PRICES.get(result.model)
    if prices is None:
        return 0.0

    input_cost = (
        result.input_tokens.text * prices.input_text
        + result.input_tokens.image * prices.input_image
    ) / 1_000_000

    output_cost = (
        result.output_tokens.text * prices.output_text
        + result.output_tokens.image * prices.output_image
    ) / 1_000_000

    return input_cost + output_cost
