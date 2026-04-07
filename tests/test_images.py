"""Tests for image handling."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

from bananarama.images import (
    find_image_file,
    resize_reference_image,
    resolve_placeholders,
    split_image,
)


def _create_png(path: Path, width: int = 1, height: int = 1) -> None:
    """Create a minimal PNG at the given path."""
    img = Image.new("RGB", (width, height), color="red")
    img.save(path, format="PNG")


class TestResolvePlaceholders:
    def test_no_placeholders(self, tmp_path):
        text, images = resolve_placeholders("A simple description", tmp_path)
        assert text == "A simple description"
        assert images == []

    def test_none_input(self, tmp_path):
        text, images = resolve_placeholders(None, tmp_path)
        assert text is None
        assert images == []

    def test_replaces_placeholders(self, tmp_path):
        (tmp_path / "hadley.jpg").touch()
        (tmp_path / "robot.png").touch()

        text, images = resolve_placeholders(
            "Draw [hadley] with [robot] in a garden", tmp_path
        )

        assert (
            text
            == "Draw hadley (shown in image 1) with robot (shown in image 2) in a garden"
        )
        assert images == [
            tmp_path / "hadley.jpg",
            tmp_path / "robot.png",
        ]

    def test_repeated_placeholders(self, tmp_path):
        (tmp_path / "robot.png").touch()

        text, images = resolve_placeholders("A [robot] meets another [robot]", tmp_path)

        assert (
            text == "A robot (shown in image 1) meets another robot (shown in image 2)"
        )
        assert len(images) == 2

    def test_start_index(self, tmp_path):
        (tmp_path / "cat.png").touch()

        text, images = resolve_placeholders("A [cat] sitting", tmp_path, start_index=2)

        assert text == "A cat (shown in image 3) sitting"
        assert len(images) == 1


class TestFindImageFile:
    def test_finds_png(self, tmp_path):
        (tmp_path / "test.png").touch()
        assert find_image_file("test", tmp_path) == tmp_path / "test.png"

    def test_finds_jpg(self, tmp_path):
        (tmp_path / "test.jpg").touch()
        assert find_image_file("test", tmp_path) == tmp_path / "test.jpg"

    def test_errors_on_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Cannot find"):
            find_image_file("nonexistent", tmp_path)


class TestResizeReferenceImage:
    def test_no_resize_needed(self, tmp_path):
        path = tmp_path / "small.png"
        _create_png(path, 100, 100)
        assert resize_reference_image(path) is False

    def test_resize_large_image(self, tmp_path):
        path = tmp_path / "large.png"
        _create_png(path, 1024, 1024)
        assert resize_reference_image(path) is True

        resized = Image.open(path)
        assert resized.width <= 512
        assert resized.height <= 512


class TestSplitImage:
    def test_small_image_no_split(self, tmp_path):
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        paths = split_image(buf.getvalue(), tmp_path, "small")
        assert len(paths) == 1
        assert paths[0] == tmp_path / "small.png"
        assert paths[0].exists()

    def test_large_image_splits(self, tmp_path):
        # Create an image that exceeds the max_pixels limit
        img = Image.new("RGB", (200, 200), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        # Use a very small max_pixels to force splitting
        paths = split_image(buf.getvalue(), tmp_path, "large", max_pixels=100 * 100)
        assert len(paths) > 1
        for p in paths:
            assert p.exists()
