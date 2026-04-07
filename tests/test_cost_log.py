"""Tests for the persistent cost log."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bananarama.costs.log import (
    append_run,
    last_runs,
    log_path,
    set_log_path,
    spend_by_model,
    total_spend,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestCostLog:
    def _setup_log(self, tmp_path: Path) -> Path:
        """Point the cost log at a temp file for testing."""
        path = tmp_path / "cost-log.csv"
        set_log_path(path)
        return path

    def test_append_creates_file(self, tmp_path: Path) -> None:
        path = self._setup_log(tmp_path)
        assert not path.exists()
        append_run("test.yaml", "gemini-3.1-flash-image-preview", 2, 0.123)
        assert path.exists()

    def test_total_spend(self, tmp_path: Path) -> None:
        self._setup_log(tmp_path)
        append_run("a.yaml", "model-a", 1, 0.100)
        append_run("b.yaml", "model-b", 2, 0.200)
        assert abs(total_spend() - 0.300) < 1e-6

    def test_spend_by_model(self, tmp_path: Path) -> None:
        self._setup_log(tmp_path)
        append_run("a.yaml", "model-a", 1, 0.050)
        append_run("b.yaml", "model-b", 2, 0.100)
        append_run("c.yaml", "model-a", 3, 0.150)
        by_model = spend_by_model()
        assert abs(by_model["model-a"] - 0.200) < 1e-6
        assert abs(by_model["model-b"] - 0.100) < 1e-6

    def test_last_runs_ordering(self, tmp_path: Path) -> None:
        self._setup_log(tmp_path)
        for i in range(5):
            append_run(f"config-{i}.yaml", "model-x", 1, float(i))
        recent = last_runs(3)
        assert len(recent) == 3
        # Most recent first
        assert recent[0]["config_path"] == "config-4.yaml"
        assert recent[2]["config_path"] == "config-2.yaml"

    def test_empty_log(self, tmp_path: Path) -> None:
        self._setup_log(tmp_path)
        assert total_spend() == 0.0
        assert spend_by_model() == {}
        assert last_runs() == []

    def test_log_path(self, tmp_path: Path) -> None:
        path = self._setup_log(tmp_path)
        assert log_path() == path
