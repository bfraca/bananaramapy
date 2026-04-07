"""Tests for cost calculation."""

from __future__ import annotations

from bananarama.costs.pricing import (
    MODEL_PRICES,
    PER_IMAGE_PRICES,
    compute_cost,
    estimate_cost,
)
from bananarama.models.base import ImageResult, TokenUsage


class TestModelPrices:
    def test_gemini_models(self):
        assert "gemini-3.1-flash-image-preview" in MODEL_PRICES
        assert "gemini-3-pro-image-preview" in MODEL_PRICES
        assert "gemini-2.5-flash-image" in MODEL_PRICES

    def test_openai_models(self):
        assert "gpt-image-1" in MODEL_PRICES
        assert "gpt-image-1.5" in MODEL_PRICES

    def test_flux_per_image_models(self):
        assert "flux-2-pro" in PER_IMAGE_PRICES
        assert "flux-2-dev" in PER_IMAGE_PRICES
        assert "flux-2-schnell" in PER_IMAGE_PRICES

    def test_all_token_prices_have_output_image(self):
        for model, prices in MODEL_PRICES.items():
            assert prices.output_image > 0, f"{model} missing output_image"


class TestComputeCost:
    def test_known_model(self):
        result = ImageResult(
            image_data=b"fake",
            model="gemini-3.1-flash-image-preview",
            input_tokens=TokenUsage(text=100, image=200),
            output_tokens=TokenUsage(text=50, image=1000),
        )
        cost = compute_cost(result)
        # input: (100 * 0.50 + 200 * 0.50) / 1e6 = 0.00015
        # output: (50 * 3.00 + 1000 * 60.00) / 1e6 = 0.06015
        expected = 0.00015 + 0.06015
        assert abs(cost - expected) < 1e-8

    def test_unknown_model(self):
        result = ImageResult(
            image_data=b"fake",
            model="unknown-model",
            input_tokens=TokenUsage(text=100, image=200),
            output_tokens=TokenUsage(text=50, image=1000),
        )
        assert compute_cost(result) == 0.0

    def test_per_image_pricing(self):
        result = ImageResult(
            image_data=b"fake",
            model="flux-2-pro",
            input_tokens=TokenUsage(),
            output_tokens=TokenUsage(),
        )
        assert compute_cost(result) == 0.05


class TestEstimateCost:
    def test_known_token_model(self):
        est = estimate_cost("gemini-3.1-flash-image-preview")
        assert est is not None
        assert est > 0

    def test_known_per_image_model(self):
        est = estimate_cost("flux-2-pro")
        assert est == 0.05

    def test_unknown_model(self):
        assert estimate_cost("nonexistent") is None
