"""Cost calculation for image generation.

Loads pricing data from a TOML file (``costs/data/prices.toml`` by default).
Supports both token-based pricing (Gemini, OpenAI) and flat per-image
pricing (FLUX via Together AI).

Set the ``BANANARAMA_PRICES`` environment variable to override the built-in
pricing file with a custom TOML path.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
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


def _default_prices_path() -> Path:
    """Return the path to the built-in prices.toml file."""
    return Path(__file__).parent / "data" / "prices.toml"


def _load_prices(
    path: Path | None = None,
) -> tuple[dict[str, ModelPricing], dict[str, PerImagePricing]]:
    """Load pricing data from a TOML file.

    Returns a tuple of (token-based prices, per-image prices).
    """
    if path is None:
        env_path = os.environ.get("BANANARAMA_PRICES")
        path = Path(env_path) if env_path else _default_prices_path()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    models = data.get("models", {})

    token_prices: dict[str, ModelPricing] = {}
    image_prices: dict[str, PerImagePricing] = {}

    for model_name, info in models.items():
        pricing_model = info.get("pricing_model", "token")

        if pricing_model == "token":
            token_prices[model_name] = ModelPricing(
                input_text=float(info["input_text"]),
                input_image=float(info["input_image"]),
                output_text=float(info["output_text"]),
                output_image=float(info["output_image"]),
            )
        elif pricing_model == "per_image":
            image_prices[model_name] = PerImagePricing(
                cost_per_image=float(info["cost_per_image"]),
            )

    return token_prices, image_prices


# Module-level caches loaded on first access.
MODEL_PRICES: dict[str, ModelPricing] = {}
PER_IMAGE_PRICES: dict[str, PerImagePricing] = {}
_loaded = False


def _ensure_loaded() -> None:
    """Load prices from TOML if not already loaded."""
    global _loaded
    if not _loaded:
        token, per_image = _load_prices()
        MODEL_PRICES.update(token)
        PER_IMAGE_PRICES.update(per_image)
        _loaded = True


def reload_prices(path: Path | None = None) -> None:
    """Reload pricing data, optionally from a specific path.

    Useful for testing or after updating the prices file.
    """
    global _loaded
    MODEL_PRICES.clear()
    PER_IMAGE_PRICES.clear()
    token, per_image = _load_prices(path)
    MODEL_PRICES.update(token)
    PER_IMAGE_PRICES.update(per_image)
    _loaded = True


def compute_cost(result: ImageResult) -> float:
    """Compute the dollar cost of a generation result.

    Uses token-based pricing when available, falling back to flat per-image
    pricing. Returns 0.0 if the model has no known pricing.
    """
    _ensure_loaded()

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
    _ensure_loaded()

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
