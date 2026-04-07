"""Template gallery: built-in YAML templates for common presentation styles."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import yaml


@dataclass
class TemplateInfo:
    """Metadata about a built-in template."""

    name: str
    description: str
    recommended_model: str
    image_count: int


def _templates_dir() -> Path:
    """Return the path to the built-in templates data directory."""
    ref = resources.files("bananarama.templates") / "data"
    # resources.files returns a Traversable; for on-disk packages this is a Path
    return Path(str(ref))


def list_templates() -> list[TemplateInfo]:
    """List all available built-in templates with metadata."""
    templates_path = _templates_dir()
    result: list[TemplateInfo] = []

    for yaml_file in sorted(templates_path.glob("*.yaml")):
        info = _parse_template_metadata(yaml_file)
        if info is not None:
            result.append(info)

    return result


def get_template_path(name: str) -> Path:
    """Return the path to a named template file.

    Raises:
        ValueError: If the template name is not found.
    """
    templates_path = _templates_dir()
    template_file = templates_path / f"{name}.yaml"
    if not template_file.exists():
        available = [t.name for t in list_templates()]
        msg = (
            f"Template '{name}' not found. Available templates: {', '.join(available)}"
        )
        raise ValueError(msg)
    return template_file


def init_project(
    template_name: str,
    dest_dir: Path,
    *,
    overwrite: bool = False,
) -> Path:
    """Scaffold a new project directory from a template.

    Args:
        template_name: Name of the built-in template to use.
        dest_dir: Destination directory to create.
        overwrite: If True, overwrite existing bananarama.yaml.

    Returns:
        Path to the created bananarama.yaml file.

    Raises:
        ValueError: If the template is not found.
        FileExistsError: If destination config exists and overwrite is False.
    """
    template_path = get_template_path(template_name)
    dest_dir = dest_dir.resolve()
    dest_config = dest_dir / "bananarama.yaml"

    if dest_config.exists() and not overwrite:
        msg = f"'{dest_config}' already exists. Use --overwrite to replace it."
        raise FileExistsError(msg)

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, dest_config)
    return dest_config


def _parse_template_metadata(yaml_path: Path) -> TemplateInfo | None:
    """Extract metadata from a template YAML file."""
    try:
        with open(yaml_path) as f:
            raw = yaml.safe_load(f)
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    # Extract description from the first comment block
    description = _extract_description(yaml_path)

    defaults = raw.get("defaults", {})
    model = defaults.get("model", "gemini-3.1-flash-image-preview")
    images = raw.get("images", [])

    return TemplateInfo(
        name=yaml_path.stem,
        description=description,
        recommended_model=model,
        image_count=len(images) if isinstance(images, list) else 0,
    )


def _extract_description(yaml_path: Path) -> str:
    """Extract the template description from YAML comment header."""
    with open(yaml_path) as f:
        lines = f.readlines()

    # Look for the second comment line (first is "# Bananarama Template: ...")
    # which contains the one-line style description
    for line in lines[1:]:
        line = line.strip()
        if line.startswith("#") and not line.startswith("# Bananarama Template"):
            # Skip empty comment lines
            text = line.lstrip("# ").strip()
            if text:
                return text
        elif not line.startswith("#"):
            break

    return "No description available."
