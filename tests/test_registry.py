"""Tests for the model registry."""

from __future__ import annotations

import pytest

from bananarama.models.registry import (
    get_provider,
    get_provider_name,
    is_provider_available,
    list_models,
)


class TestListModels:
    def test_contains_gemini_models(self):
        models = list_models()
        assert "gemini-3.1-flash-image-preview" in models
        assert "gemini-3-pro-image-preview" in models
        assert "gemini-2.5-flash-image" in models

    def test_contains_openai_models(self):
        models = list_models()
        assert "gpt-image-1" in models
        assert "gpt-image-1.5" in models

    def test_contains_flux_models(self):
        models = list_models()
        assert "flux-2-pro" in models
        assert "flux-2-dev" in models
        assert "flux-2-schnell" in models

    def test_sorted(self):
        models = list_models()
        assert models == sorted(models)


class TestGetProvider:
    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            get_provider("nonexistent-model")

    def test_gemini_model_returns_provider(self):
        provider = get_provider("gemini-3.1-flash-image-preview", api_key="test-key")
        assert provider.__class__.__name__ == "GeminiProvider"


class TestGetProviderName:
    def test_gemini(self):
        assert get_provider_name("gemini-3.1-flash-image-preview") == "Google Gemini"

    def test_openai(self):
        assert get_provider_name("gpt-image-1") == "OpenAI"

    def test_flux(self):
        assert get_provider_name("flux-2-pro") == "FLUX (Together AI)"

    def test_unknown(self):
        assert get_provider_name("nonexistent") == "Unknown"


class TestIsProviderAvailable:
    def test_gemini_available(self):
        # google-genai is a required dep, so it should always be available
        assert is_provider_available("gemini-3.1-flash-image-preview") is True

    def test_unknown_model(self):
        assert is_provider_available("nonexistent") is False
