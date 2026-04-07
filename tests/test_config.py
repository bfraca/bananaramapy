"""Tests for config parsing."""

from __future__ import annotations

import pytest
import yaml

from bananarama.config import (
    Defaults,
    _check_aspect_ratio,
    _check_resolution,
    _coerce_ratio,
    _levenshtein,
    _parse_defaults,
    _parse_image,
    _suggest_model,
    parse_image_config,
    resolve_config_path,
    validate_api_keys,
    validate_model,
)


class TestResolveConfigPath:
    def test_file_path(self, tmp_path):
        config = tmp_path / "bananarama.yaml"
        config.write_text("images: []")
        assert resolve_config_path(config) == config

    def test_directory_path(self, tmp_path):
        config = tmp_path / "bananarama.yaml"
        config.write_text("images: []")
        assert resolve_config_path(tmp_path) == config

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Cannot find"):
            resolve_config_path(tmp_path / "nonexistent.yaml")


class TestParseDefaults:
    def test_none_returns_defaults(self):
        result = _parse_defaults(None)
        assert result.model == "gemini-3.1-flash-image-preview"
        assert result.style is None
        assert result.aspect_ratio == "16:9"
        assert result.resolution == "1K"
        assert result.n == 1
        assert result.force is False
        assert result.seed is None

    def test_extracts_values(self):
        result = _parse_defaults(
            {
                "style": "chunky gouache",
                "aspect-ratio": "16:9",
                "resolution": "2K",
                "model": "gemini-3-pro-image-preview",
            }
        )
        assert result.model == "gemini-3-pro-image-preview"
        assert result.style == "chunky gouache"
        assert result.aspect_ratio == "16:9"
        assert result.resolution == "2K"


class TestParseImage:
    def test_errors_on_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            _parse_image({"description": "A picture"}, Defaults())

    def test_errors_on_missing_description(self):
        with pytest.raises(ValueError, match="description"):
            _parse_image({"name": "test"}, Defaults())

    def test_uses_description_from_defaults(self):
        defaults = _parse_defaults({"description": "default desc"})
        result = _parse_image({"name": "test", "style": "watercolor"}, defaults)
        assert result.description == "default desc"

        result = _parse_image({"name": "test", "description": "custom desc"}, defaults)
        assert result.description == "custom desc"

    def test_merges_defaults_with_overrides(self):
        defaults = Defaults(
            model="gemini-2.5-flash-image",
            style="default style",
            aspect_ratio="16:9",
            resolution="1K",
            n=1,
        )

        result = _parse_image({"name": "img1", "description": "desc1"}, defaults)
        assert result.model == "gemini-2.5-flash-image"
        assert result.style == "default style"
        assert result.aspect_ratio == "16:9"

        result = _parse_image(
            {"name": "img2", "description": "desc2", "aspect-ratio": "1:1"},
            defaults,
        )
        assert result.style == "default style"
        assert result.aspect_ratio == "1:1"

        result = _parse_image(
            {
                "name": "img3",
                "description": "desc3",
                "model": "gemini-3-pro-image-preview",
            },
            defaults,
        )
        assert result.model == "gemini-3-pro-image-preview"

    def test_force_from_defaults_and_overrides(self):
        result = _parse_image({"name": "test", "description": "desc"}, Defaults())
        assert result.force is False

        defaults = _parse_defaults({"force": True})
        result = _parse_image({"name": "test", "description": "desc"}, defaults)
        assert result.force is True

        result = _parse_image(
            {"name": "test", "description": "desc", "force": False}, defaults
        )
        assert result.force is False

    def test_seed_from_defaults_and_overrides(self):
        result = _parse_image({"name": "test", "description": "desc"}, Defaults())
        assert result.seed is None

        defaults = _parse_defaults({"seed": 42})
        result = _parse_image({"name": "test", "description": "desc"}, defaults)
        assert result.seed == 42

        result = _parse_image(
            {"name": "test", "description": "desc", "seed": 99}, defaults
        )
        assert result.seed == 99


class TestValidation:
    def test_invalid_aspect_ratio(self):
        with pytest.raises(ValueError, match="invalid aspect-ratio"):
            _check_aspect_ratio("5:3", "test")

    def test_invalid_resolution(self):
        with pytest.raises(ValueError, match="invalid resolution"):
            _check_resolution("8K", "test")

    def test_n_less_than_1(self):
        with pytest.raises(ValueError, match="n"):
            _parse_image(
                {"name": "test", "description": "desc", "n": 0},
                Defaults(),
            )


class TestCoerceRatio:
    def test_string_passthrough(self):
        assert _coerce_ratio("16:9") == "16:9"
        assert _coerce_ratio("1:1") == "1:1"

    def test_sexagesimal_fix_16_9(self):
        # PyYAML parses unquoted 16:9 as 969 (16*60+9)
        assert _coerce_ratio(969) == "16:9"

    def test_sexagesimal_fix_21_9(self):
        assert _coerce_ratio(1269) == "21:9"

    def test_sexagesimal_fix_all_ratios(self):
        assert _coerce_ratio(61) == "1:1"
        assert _coerce_ratio(123) == "2:3"
        assert _coerce_ratio(182) == "3:2"
        assert _coerce_ratio(184) == "3:4"
        assert _coerce_ratio(243) == "4:3"
        assert _coerce_ratio(245) == "4:5"
        assert _coerce_ratio(304) == "5:4"
        assert _coerce_ratio(556) == "9:16"

    def test_unknown_int_becomes_str(self):
        assert _coerce_ratio(42) == "42"


class TestLevenshtein:
    def test_identical(self):
        assert _levenshtein("abc", "abc") == 0

    def test_single_edit(self):
        assert _levenshtein("abc", "ab") == 1
        assert _levenshtein("abc", "axc") == 1

    def test_empty(self):
        assert _levenshtein("", "abc") == 3


class TestSuggestModel:
    def test_close_match(self):
        known = ["gemini-3.1-flash-image-preview", "gpt-image-1"]
        assert _suggest_model("gpt-image-1.5", known) == "gpt-image-1"

    def test_no_close_match(self):
        known = ["gemini-3.1-flash-image-preview"]
        assert _suggest_model("totally-different-model-xyz", known) is None

    def test_empty_known(self):
        assert _suggest_model("anything", []) is None


class TestValidateModel:
    def test_known_model_no_warning(self):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            validate_model("gemini-3.1-flash-image-preview")

    def test_unknown_model_warns(self):
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_model("gemini-3.1-flash-image")
            assert len(w) == 1
            assert "Unknown model" in str(w[0].message)
            assert "Did you mean" in str(w[0].message)

    def test_totally_unknown_model_warns_without_suggestion(self):
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_model("xyzzy-nonexistent-model-foobar")
            assert len(w) == 1
            assert "Unknown model" in str(w[0].message)
            assert "Did you mean" not in str(w[0].message)


class TestValidateApiKeys:
    def test_warns_on_missing_key(self, monkeypatch):
        import warnings

        from bananarama.config import ImageSpec

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        images = [
            ImageSpec(
                name="test", description="desc", model="gemini-3.1-flash-image-preview"
            )
        ]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            validate_api_keys(images)
            key_warnings = [x for x in w if "API key not set" in str(x.message)]
            assert len(key_warnings) >= 1


class TestParseImageConfig:
    def test_full_config(self, tmp_path):
        config_data = {
            "output-dir": "imgs",
            "images": [{"name": "test", "description": "desc"}],
        }
        config_file = tmp_path / "bananarama.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = parse_image_config(config_file)
        assert result.output_dir == "imgs"
        assert len(result.images) == 1
        assert result.images[0].name == "test"

    def test_output_dir_none_when_not_specified(self, tmp_path):
        config_data = {"images": [{"name": "test", "description": "desc"}]}
        config_file = tmp_path / "bananarama.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = parse_image_config(config_file)
        assert result.output_dir is None

    def test_missing_images_field(self, tmp_path):
        config_file = tmp_path / "bananarama.yaml"
        config_file.write_text("defaults:\n  style: test\n")

        with pytest.raises(ValueError, match="images"):
            parse_image_config(config_file)
