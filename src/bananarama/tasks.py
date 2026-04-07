"""Task building, output path computation, and preprocessing.

A *task* pairs an :class:`~bananarama.config.ImageSpec` with the concrete
file path it should be written to.  This module is intentionally free of any
API or async logic — it only needs the filesystem and the parsed config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console

from bananarama.images import (
    mime_type_for_path,
    resize_reference_image,
    resolve_placeholders,
)
from bananarama.models.base import ReferenceImage

if TYPE_CHECKING:
    from pathlib import Path

    from bananarama.config import ImageSpec

console = Console()


@dataclass
class Task:
    """A single image generation task."""

    image: ImageSpec
    output_path: Path
    prompt: str = ""
    reference_images: list[ReferenceImage] = field(default_factory=list)


def compute_output_paths(
    images: list[ImageSpec], output_dir: Path
) -> dict[str, list[Path]]:
    """Compute output file paths for all images.

    Returns a dict mapping image name to its list of output paths.
    """
    result: dict[str, list[Path]] = {}
    for image in images:
        if image.n > 1:
            names = [f"{image.name}-{i + 1}" for i in range(image.n)]
        else:
            names = [image.name]
        result[image.name] = [output_dir / f"{n}.png" for n in names]
    return result


def build_tasks(
    images: list[ImageSpec],
    output_paths: dict[str, list[Path]],
    force: bool = False,
) -> list[Task]:
    """Build the list of generation tasks, skipping existing files."""
    tasks: list[Task] = []
    n_skipped = 0

    for image in images:
        for path in output_paths[image.name]:
            if not force and not image.force and path.exists():
                n_skipped += 1
                continue
            tasks.append(Task(image=image, output_path=path))

    if n_skipped > 0:
        console.print(f"[dim]Skipping {n_skipped} image(s) (already exist)[/dim]")

    return tasks


def preprocess_task(task: Task, base_dir: Path) -> None:
    """Resolve placeholders and load reference images for a task."""
    image = task.image

    # Resolve style placeholders first (they get earlier image indices)
    style_text, style_images = resolve_placeholders(image.style, base_dir)
    start_index = len(style_images)

    # Then resolve description placeholders
    desc_text, desc_images = resolve_placeholders(
        image.description, base_dir, start_index
    )

    # Build prompt
    parts: list[str] = []
    if desc_text:
        parts.append(desc_text)
    if style_text:
        parts.append(f"Style: {style_text}")
    task.prompt = "\n\n".join(parts)

    # Load and resize reference images
    all_image_paths = style_images + desc_images
    refs: list[ReferenceImage] = []
    for img_path in all_image_paths:
        resize_reference_image(img_path)
        refs.append(
            ReferenceImage(
                data=img_path.read_bytes(),
                mime_type=mime_type_for_path(img_path),
            )
        )
    task.reference_images = refs


def all_output_paths(paths: dict[str, list[Path]]) -> list[Path]:
    """Flatten the output paths dict into a single list."""
    result: list[Path] = []
    for path_list in paths.values():
        result.extend(path_list)
    return result


def group_tasks(tasks: list[Task]) -> dict[str, list[Task]]:
    """Group tasks by model + seed + aspect-ratio + resolution."""
    groups: dict[str, list[Task]] = {}
    for task in tasks:
        img = task.image
        key = f"{img.model}|{img.seed}|{img.aspect_ratio}|{img.resolution}"
        groups.setdefault(key, []).append(task)
    return groups
