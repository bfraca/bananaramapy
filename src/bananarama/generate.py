"""Orchestration: task building, parallel image generation, and saving."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from bananarama.config import (
    ImageConfig,
    ImageSpec,
    parse_image_config,
    resolve_config_path,
)
from bananarama.costs.pricing import compute_cost
from bananarama.images import resize_reference_image, resolve_placeholders, split_image
from bananarama.models.base import ImageRequest, ImageResult
from bananarama.models.registry import get_provider

console = Console()


@dataclass
class Task:
    """A single image generation task."""

    image: ImageSpec
    output_path: Path
    prompt: str = ""
    reference_images: list[bytes] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.reference_images is None:
            self.reference_images = []


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
    ref_bytes: list[bytes] = []
    for img_path in all_image_paths:
        resize_reference_image(img_path)
        ref_bytes.append(img_path.read_bytes())
    task.reference_images = ref_bytes


async def bananarama(
    path: str | Path = "bananarama.yaml",
    output_dir: str | None = None,
    force: bool = False,
    max_pixels: int = 4096 * 4096,
) -> list[Path]:
    """Generate presentation images from a YAML configuration.

    Args:
        path: Path to a YAML config file or directory containing one.
        output_dir: Override output directory (relative to YAML or absolute).
        force: If True, regenerate all images even if they exist.
        max_pixels: Maximum pixels per output file. Images exceeding this are
            split into tiles.

    Returns:
        List of all output file paths.
    """
    config_path = resolve_config_path(path)
    config: ImageConfig = parse_image_config(config_path)

    # Resolve output directory
    default_dir = config_path.stem
    resolved_output_dir = output_dir or config.output_dir or default_dir
    out_path = Path(resolved_output_dir)
    if not out_path.is_absolute():
        out_path = config.base_dir / out_path
    out_path.mkdir(parents=True, exist_ok=True)

    # Build tasks
    all_paths = compute_output_paths(config.images, out_path)
    tasks = build_tasks(config.images, all_paths, force=force)

    if not tasks:
        return _all_output_paths(all_paths)

    # Preprocess tasks (resolve placeholders, load reference images)
    for task in tasks:
        preprocess_task(task, config.base_dir)

    # Group tasks by model config for batching
    groups = _group_tasks(tasks)

    console.print(f"[bold]Generating {len(tasks)} image(s) in parallel...[/bold]")

    # Generate all groups
    results: dict[int, ImageResult | BaseException] = {}
    for group in groups.values():
        model = group[0].image.model
        provider = get_provider(model)

        requests = [
            ImageRequest(
                prompt=t.prompt,
                reference_images=t.reference_images,
                aspect_ratio=t.image.aspect_ratio,
                resolution=t.image.resolution,
                seed=t.image.seed,
            )
            for t in group
        ]

        group_results = await provider.generate_batch(requests)

        for task_item, result in zip(group, group_results, strict=True):
            task_idx = tasks.index(task_item)
            results[task_idx] = result

    # Save results and report costs
    total_cost = 0.0
    all_saved: list[Path] = []

    for i, task in enumerate(tasks):
        result = results[i]
        label = task.output_path.name

        if isinstance(result, BaseException):
            console.print(f"[red]✗[/red] Failed to generate {label}: {result}")
            continue

        cost = compute_cost(result)
        total_cost += cost

        # Split large images if needed
        saved_paths = split_image(
            result.image_data,
            task.output_path.parent,
            task.output_path.stem,
            max_pixels=max_pixels,
        )
        all_saved.extend(saved_paths)

        if len(saved_paths) > 1:
            console.print(
                f"[green]✓[/green] Generated {label} "
                f"(split into {len(saved_paths)} tiles, ${cost:.3f})"
            )
        else:
            console.print(f"[green]✓[/green] Generated {label} (${cost:.3f})")

    if total_cost > 0:
        console.print(f"\n[bold]Total cost: ${total_cost:.3f}[/bold]")

    return _all_output_paths(all_paths)


def _group_tasks(tasks: list[Task]) -> dict[str, list[Task]]:
    """Group tasks by model + seed + aspect-ratio + resolution."""
    groups: dict[str, list[Task]] = {}
    for task in tasks:
        img = task.image
        key = f"{img.model}|{img.seed}|{img.aspect_ratio}|{img.resolution}"
        groups.setdefault(key, []).append(task)
    return groups


def _all_output_paths(paths: dict[str, list[Path]]) -> list[Path]:
    """Flatten the output paths dict."""
    result: list[Path] = []
    for path_list in paths.values():
        result.extend(path_list)
    return result


def run_sync(
    path: str | Path = "bananarama.yaml",
    output_dir: str | None = None,
    force: bool = False,
    max_pixels: int = 4096 * 4096,
) -> list[Path]:
    """Synchronous wrapper around the async bananarama function."""
    return asyncio.run(
        bananarama(path, output_dir=output_dir, force=force, max_pixels=max_pixels)
    )
