"""Tests for cost calculation."""

from __future__ import annotations

from bananarama.costs.pricing import MODEL_PRICES, compute_cost
from bananarama.models.base import ImageResult, TokenUsage


class TestModelPrices:
    def test_known_models(self):
        expected = {
            "gemini-3.1-flash-image-preview",
            "gemini-3-pro-image-preview",
            "gemini-2.5-flash-image",
        }
        assert set(MODEL_PRICES.keys()) == expected

    def test_all_have_fields(self):
        for model, prices in MODEL_PRICES.items():
            assert prices.input_text > 0, f"{model} missing input_text"
            assert prices.output_text > 0, f"{model} missing output_text"
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
