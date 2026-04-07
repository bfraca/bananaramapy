"""Tests for the shared sizing module."""

from __future__ import annotations

import pytest

from bananarama.models.sizing import resolve_dimensions, resolve_openai_size


class TestResolveDimensions:
    def test_square_1k(self):
        w, h = resolve_dimensions("1:1", "1K", "gemini")
        assert w == 1024
        assert h == 1024

    def test_landscape_16_9(self):
        w, h = resolve_dimensions("16:9", "1K", "gemini")
        assert w > h
        assert w % 64 == 0
        assert h % 64 == 0

    def test_portrait_9_16(self):
        w, h = resolve_dimensions("9:16", "1K", "gemini")
        assert h > w
        assert w % 64 == 0
        assert h % 64 == 0

    def test_higher_resolution_scales_up(self):
        w1, h1 = resolve_dimensions("1:1", "1K", "gemini")
        w2, h2 = resolve_dimensions("1:1", "2K", "gemini")
        assert w2 > w1
        assert h2 > h1

    def test_provider_clamping_openai(self):
        w, h = resolve_dimensions("16:9", "2K", "openai")
        assert w <= 1536
        assert h <= 1536

    def test_provider_clamping_flux(self):
        w, h = resolve_dimensions("16:9", "4K", "flux")
        assert w <= 2048
        assert h <= 2048

    def test_all_multiples_of_64(self):
        for ar in ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]:
            for res in ["1K", "2K"]:
                w, h = resolve_dimensions(ar, res, "gemini")
                assert w % 64 == 0, f"{ar}/{res}: w={w}"
                assert h % 64 == 0, f"{ar}/{res}: h={h}"

    def test_invalid_aspect_ratio(self):
        with pytest.raises(ValueError, match="Unsupported aspect ratio"):
            resolve_dimensions("7:3", "1K", "gemini")


class TestResolveOpenAISize:
    def test_square(self):
        assert resolve_openai_size("1:1") == "1024x1024"

    def test_landscape(self):
        assert resolve_openai_size("16:9") == "1536x1024"

    def test_portrait(self):
        assert resolve_openai_size("9:16") == "1024x1536"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Unsupported aspect ratio for OpenAI"):
            resolve_openai_size("7:3")
