"""Tests for the generation orchestration."""

from __future__ import annotations

from pathlib import Path

from bananarama.config import ImageSpec
from bananarama.generate import build_tasks, compute_output_paths


class TestComputeOutputPaths:
    def test_single_image(self):
        images = [ImageSpec(name="img1", description="desc", n=1)]
        result = compute_output_paths(images, Path("/tmp/output"))
        assert result["img1"] == [Path("/tmp/output/img1.png")]

    def test_multiple_variants(self):
        images = [ImageSpec(name="img2", description="desc", n=3)]
        result = compute_output_paths(images, Path("/tmp/output"))
        assert result["img2"] == [
            Path("/tmp/output/img2-1.png"),
            Path("/tmp/output/img2-2.png"),
            Path("/tmp/output/img2-3.png"),
        ]

    def test_mixed(self):
        images = [
            ImageSpec(name="bicycle", description="desc", n=3),
            ImageSpec(name="car", description="desc", n=1),
        ]
        result = compute_output_paths(images, Path("/tmp/output"))
        assert result["bicycle"] == [
            Path("/tmp/output/bicycle-1.png"),
            Path("/tmp/output/bicycle-2.png"),
            Path("/tmp/output/bicycle-3.png"),
        ]
        assert result["car"] == [Path("/tmp/output/car.png")]


class TestBuildTasks:
    def test_skips_existing(self, tmp_path):
        existing = tmp_path / "img1.png"
        existing.write_text("fake")

        images = [ImageSpec(name="img1", description="desc")]
        paths = {"img1": [existing]}

        tasks = build_tasks(images, paths)
        assert len(tasks) == 0

    def test_force_overrides_skip(self, tmp_path):
        existing = tmp_path / "img1.png"
        existing.write_text("fake")

        images = [ImageSpec(name="img1", description="desc")]
        paths = {"img1": [existing]}

        tasks = build_tasks(images, paths, force=True)
        assert len(tasks) == 1

    def test_new_images_included(self, tmp_path):
        images = [
            ImageSpec(name="img1", description="desc1"),
            ImageSpec(name="img2", description="desc2"),
        ]
        paths = {
            "img1": [tmp_path / "img1.png"],
            "img2": [tmp_path / "img2.png"],
        }

        tasks = build_tasks(images, paths)
        assert len(tasks) == 2
