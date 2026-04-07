"""Tests for the template gallery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bananarama.templates import (
    TemplateInfo,
    get_template_path,
    init_project,
    list_templates,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestListTemplates:
    def test_returns_all_builtin_templates(self) -> None:
        templates = list_templates()
        names = [t.name for t in templates]
        assert "minimal" in names
        assert "editorial" in names
        assert "photorealistic" in names
        assert "retro" in names
        assert "dark" in names

    def test_returns_template_info_objects(self) -> None:
        templates = list_templates()
        assert len(templates) >= 5
        for tmpl in templates:
            assert isinstance(tmpl, TemplateInfo)
            assert tmpl.name
            assert tmpl.description
            assert tmpl.recommended_model
            assert tmpl.image_count >= 1

    def test_templates_sorted_by_name(self) -> None:
        templates = list_templates()
        names = [t.name for t in templates]
        assert names == sorted(names)


class TestGetTemplatePath:
    def test_returns_path_for_valid_template(self) -> None:
        path = get_template_path("editorial")
        assert path.exists()
        assert path.name == "editorial.yaml"

    def test_raises_for_unknown_template(self) -> None:
        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            get_template_path("nonexistent")

    def test_error_lists_available_templates(self) -> None:
        with pytest.raises(ValueError, match="editorial"):
            get_template_path("nonexistent")


class TestInitProject:
    def test_creates_project_directory(self, tmp_path: Path) -> None:
        dest = tmp_path / "my-project"
        config = init_project("minimal", dest)
        assert config.exists()
        assert config.name == "bananarama.yaml"
        assert config.parent == dest

    def test_config_is_valid_yaml(self, tmp_path: Path) -> None:
        import yaml

        dest = tmp_path / "test-project"
        config = init_project("editorial", dest)
        with open(config) as f:
            data = yaml.safe_load(f)
        assert "defaults" in data
        assert "images" in data
        assert isinstance(data["images"], list)

    def test_refuses_overwrite_by_default(self, tmp_path: Path) -> None:
        dest = tmp_path / "existing"
        init_project("minimal", dest)
        with pytest.raises(FileExistsError, match="already exists"):
            init_project("minimal", dest)

    def test_allows_overwrite_when_flag_set(self, tmp_path: Path) -> None:
        dest = tmp_path / "overwrite-test"
        init_project("minimal", dest)
        config = init_project("editorial", dest, overwrite=True)
        assert config.exists()
        # Should now contain editorial template content
        import yaml

        with open(config) as f:
            data = yaml.safe_load(f)
        style = data["defaults"]["style"]
        assert "editorial" in style.lower() or "chalk" in style.lower()

    def test_raises_for_unknown_template(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not found"):
            init_project("nonexistent", tmp_path / "bad")

    def test_all_templates_produce_valid_configs(self, tmp_path: Path) -> None:
        """Every built-in template should produce a parseable config."""
        import yaml

        for tmpl in list_templates():
            dest = tmp_path / tmpl.name
            config = init_project(tmpl.name, dest)
            with open(config) as f:
                data = yaml.safe_load(f)
            assert "images" in data, f"Template '{tmpl.name}' missing 'images' key"
            assert len(data["images"]) >= 1, f"Template '{tmpl.name}' has no images"


class TestTemplateContent:
    """Validate the content quality of built-in templates."""

    def test_all_templates_have_defaults_style(self) -> None:
        import yaml

        for tmpl in list_templates():
            path = get_template_path(tmpl.name)
            with open(path) as f:
                data = yaml.safe_load(f)
            defaults = data.get("defaults", {})
            assert "style" in defaults, f"Template '{tmpl.name}' missing defaults.style"
            assert len(defaults["style"]) > 50, (
                f"Template '{tmpl.name}' style too short"
            )

    def test_all_templates_have_quoted_aspect_ratio(self) -> None:
        import yaml

        for tmpl in list_templates():
            path = get_template_path(tmpl.name)
            with open(path) as f:
                data = yaml.safe_load(f)
            ratio = data.get("defaults", {}).get("aspect-ratio")
            assert isinstance(ratio, str), (
                f"Template '{tmpl.name}' aspect-ratio should be a quoted string, "
                f"got {type(ratio).__name__}: {ratio}"
            )

    def test_all_images_have_name_and_description(self) -> None:
        import yaml

        for tmpl in list_templates():
            path = get_template_path(tmpl.name)
            with open(path) as f:
                data = yaml.safe_load(f)
            for img in data["images"]:
                assert "name" in img, f"Template '{tmpl.name}' image missing 'name'"
                assert "description" in img, (
                    f"Template '{tmpl.name}' image '{img.get('name')}' "
                    "missing 'description'"
                )
