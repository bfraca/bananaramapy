"""Tests for CI/CD scaffolding."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from bananarama.ci import scaffold_workflow

if TYPE_CHECKING:
    from pathlib import Path


class TestScaffoldWorkflow:
    def test_creates_workflow_file(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        assert result.exists()
        assert result.name == "bananarama.yaml"
        assert result.parent.name == "workflows"

    def test_workflow_is_valid_yaml(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        with open(result) as f:
            data = yaml.safe_load(f)
        assert "name" in data
        assert data["name"] == "Bananarama Generate"

    def test_default_config_path(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        content = result.read_text()
        assert "bananarama.yaml" in content

    def test_custom_config_path(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path, config="demo/bananarama.yaml")
        content = result.read_text()
        assert "demo/bananarama.yaml" in content

    def test_max_cost_included(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path, max_cost=1.50)
        content = result.read_text()
        assert "max-cost: 1.5" in content

    def test_no_max_cost_by_default(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        content = result.read_text()
        assert "max-cost" not in content

    def test_extra_deps_included(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path, extra_deps="all")
        content = result.read_text()
        assert "extra-deps: all" in content

    def test_custom_concurrency(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path, concurrency=3)
        content = result.read_text()
        assert "concurrency: 3" in content

    def test_refuses_overwrite_by_default(self, tmp_path: Path) -> None:
        scaffold_workflow(tmp_path)
        with pytest.raises(FileExistsError, match="already exists"):
            scaffold_workflow(tmp_path)

    def test_allows_overwrite_when_flag_set(self, tmp_path: Path) -> None:
        scaffold_workflow(tmp_path)
        result = scaffold_workflow(tmp_path, overwrite=True)
        assert result.exists()

    def test_creates_github_directory_structure(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        assert (tmp_path / ".github" / "workflows").is_dir()
        assert result == tmp_path / ".github" / "workflows" / "bananarama.yaml"

    def test_workflow_references_reusable_workflow(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        content = result.read_text()
        assert "bfraca/bananaramapy/.github/workflows/generate.yaml@main" in content

    def test_workflow_has_secret_references(self, tmp_path: Path) -> None:
        result = scaffold_workflow(tmp_path)
        content = result.read_text()
        assert "GEMINI_API_KEY" in content
        assert "OPENAI_API_KEY" in content
        assert "TOGETHER_API_KEY" in content
