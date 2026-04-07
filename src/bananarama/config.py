"""YAML configuration parsing, defaults, and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_ASPECT_RATIOS = frozenset(
    ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
)
VALID_RESOLUTIONS = frozenset(["1K", "2K", "4K"])

DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1K"
DEFAULT_N = 1


@dataclass
class ImageSpec:
    """Specification for a single image to generate."""

    name: str
    description: str
    model: str = DEFAULT_MODEL
    style: str | None = None
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    resolution: str = DEFAULT_RESOLUTION
    n: int = DEFAULT_N
    force: bool = False
    seed: int | None = None


@dataclass
class ImageConfig:
    """Parsed configuration from a YAML file."""

    images: list[ImageSpec]
    base_dir: Path
    output_dir: str | None = None


@dataclass
class Defaults:
    """Default values for image specs."""

    model: str = DEFAULT_MODEL
    description: str | None = None
    style: str | None = None
    aspect_ratio: str = DEFAULT_ASPECT_RATIO
    resolution: str = DEFAULT_RESOLUTION
    n: int = DEFAULT_N
    force: bool = False
    seed: int | None = None


def resolve_config_path(path: str | Path) -> Path:
    """Resolve a config path, checking for directory or file."""
    resolved = Path(os.path.expanduser(path))
    if resolved.is_dir():
        resolved = resolved / "bananarama.yaml"
    if not resolved.exists():
        msg = f"Cannot find config file '{resolved}'."
        raise FileNotFoundError(msg)
    return resolved


def parse_image_config(config_path: Path) -> ImageConfig:
    """Parse a YAML configuration file into an ImageConfig."""
    with open(config_path) as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    defaults = _parse_defaults(raw.get("defaults"))
    images = _parse_images(raw.get("images"), defaults)

    return ImageConfig(
        images=images,
        base_dir=config_path.parent,
        output_dir=raw.get("output-dir"),
    )


def _parse_defaults(values: dict[str, Any] | None) -> Defaults:
    """Parse the defaults section of a config."""
    if values is None:
        return Defaults()

    return Defaults(
        model=values.get("model", DEFAULT_MODEL),
        description=values.get("description"),
        style=values.get("style"),
        aspect_ratio=values.get("aspect-ratio", DEFAULT_ASPECT_RATIO),
        resolution=values.get("resolution", DEFAULT_RESOLUTION),
        n=int(values.get("n", DEFAULT_N)),
        force=bool(values.get("force", False)),
        seed=values.get("seed"),
    )


def _parse_images(
    images: list[dict[str, Any]] | None, defaults: Defaults
) -> list[ImageSpec]:
    """Parse the images list from a config."""
    if images is None:
        msg = "Configuration must contain an 'images' field."
        raise ValueError(msg)

    return [_parse_image(img, defaults) for img in images]


def _parse_image(img: dict[str, Any], defaults: Defaults) -> ImageSpec:
    """Parse a single image entry."""
    name = img.get("name")
    if name is None:
        msg = "Each image must have a 'name' field."
        raise ValueError(msg)

    description = img.get("description", defaults.description)
    if description is None:
        msg = f"Image '{name}' must have a 'description' field."
        raise ValueError(msg)

    aspect_ratio = img.get("aspect-ratio", defaults.aspect_ratio)
    _check_aspect_ratio(aspect_ratio, name)

    resolution = img.get("resolution", defaults.resolution)
    _check_resolution(resolution, name)

    n = int(img.get("n", defaults.n))
    if n < 1:
        msg = f"Image '{name}' must have 'n' >= 1."
        raise ValueError(msg)

    seed_raw = img.get("seed", defaults.seed)
    seed = int(seed_raw) if seed_raw is not None else None

    return ImageSpec(
        name=name,
        description=description,
        model=img.get("model", defaults.model),
        style=img.get("style", defaults.style),
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        n=n,
        force=bool(img.get("force", defaults.force)),
        seed=seed,
    )


def _check_aspect_ratio(value: str, name: str) -> None:
    """Validate an aspect ratio value."""
    if value not in VALID_ASPECT_RATIOS:
        valid = ", ".join(sorted(VALID_ASPECT_RATIOS))
        msg = f"Image '{name}' has invalid aspect-ratio '{value}'. Must be one of: {valid}."
        raise ValueError(msg)


def _check_resolution(value: str, name: str) -> None:
    """Validate a resolution value."""
    if value not in VALID_RESOLUTIONS:
        valid = ", ".join(sorted(VALID_RESOLUTIONS))
        msg = (
            f"Image '{name}' has invalid resolution '{value}'. Must be one of: {valid}."
        )
        raise ValueError(msg)
