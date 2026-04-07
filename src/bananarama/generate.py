"""Async orchestration: parallel image generation, saving, and reporting."""

from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.table import Table

from bananarama.config import (
    ImageConfig,
    parse_image_config,
    resolve_config_path,
)
from bananarama.costs.log import append_run
from bananarama.costs.pricing import compute_cost, estimate_cost
from bananarama.images import split_image
from bananarama.models.base import ImageRequest, ImageResult
from bananarama.models.registry import get_provider
from bananarama.tasks import (
    Task,
    all_output_paths,
    build_tasks,
    compute_output_paths,
    group_tasks,
    preprocess_task,
)

console = Console()


async def bananarama(
    path: str | Path = "bananarama.yaml",
    output_dir: str | None = None,
    force: bool = False,
    max_pixels: int = 4096 * 4096,
    dry_run: bool = False,
) -> list[Path]:
    """Generate presentation images from a YAML configuration.

    Args:
        path: Path to a YAML config file or directory containing one.
        output_dir: Override output directory (relative to YAML or absolute).
        force: If True, regenerate all images even if they exist.
        max_pixels: Maximum pixels per output file. Images exceeding this are
            split into tiles.
        dry_run: If True, show what would be generated without calling APIs.

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
    # Build tasks
    paths = compute_output_paths(config.images, out_path)
    tasks = build_tasks(config.images, paths, force=force)

    if not tasks:
        if dry_run:
            console.print("[dim]Nothing to generate (all images already exist).[/dim]")
        return all_output_paths(paths)

    # Dry-run: show what would be generated and estimated costs (no side effects)
    if dry_run:
        _print_dry_run(tasks)
        return all_output_paths(paths)

    # Create output directory only when we are actually generating
    out_path.mkdir(parents=True, exist_ok=True)

    # Preprocess tasks (resolve placeholders, load reference images)
    for task in tasks:
        preprocess_task(task, config.base_dir)

    # Group tasks by model config for batching
    groups = group_tasks(tasks)

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
    cost_by_model: dict[str, tuple[int, float]] = {}  # model -> (count, cost)

    for i, task in enumerate(tasks):
        result = results[i]
        label = task.output_path.name

        if isinstance(result, BaseException):
            console.print(f"[red]✗[/red] Failed to generate {label}: {result}")
            continue

        cost = compute_cost(result)
        total_cost += cost

        # Accumulate per-model stats for cost log
        model_name = task.image.model
        prev_count, prev_cost = cost_by_model.get(model_name, (0, 0.0))
        cost_by_model[model_name] = (prev_count + 1, prev_cost + cost)

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

    # Append to persistent cost log
    for model_name, (count, model_cost) in cost_by_model.items():
        append_run(
            config_path=str(config_path),
            model=model_name,
            images_generated=count,
            total_cost=model_cost,
        )

    return all_output_paths(paths)


def _print_dry_run(tasks: list[Task]) -> None:
    """Print a table of what would be generated without calling APIs."""
    table = Table(title="Dry Run — What Would Be Generated")
    table.add_column("Image", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Est. Cost", justify="right")

    total_est = 0.0
    for task in tasks:
        est = estimate_cost(task.image.model)
        cost_str = f"~${est:.3f}" if est is not None else "—"
        if est is not None:
            total_est += est
        table.add_row(task.output_path.name, task.image.model, cost_str)

    console.print(table)
    console.print(f"\n[bold]Estimated total: ~${total_est:.3f}[/bold]")
    console.print(f"[dim]{len(tasks)} image(s) would be generated.[/dim]")


def run_sync(
    path: str | Path = "bananarama.yaml",
    output_dir: str | None = None,
    force: bool = False,
    max_pixels: int = 4096 * 4096,
    dry_run: bool = False,
) -> list[Path]:
    """Synchronous wrapper around the async bananarama function."""
    return asyncio.run(
        bananarama(
            path,
            output_dir=output_dir,
            force=force,
            max_pixels=max_pixels,
            dry_run=dry_run,
        )
    )
