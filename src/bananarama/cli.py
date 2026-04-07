"""Command-line interface for bananarama."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from bananarama.costs.pricing import estimate_cost
from bananarama.generate import bananarama
from bananarama.models.registry import (
    get_provider_name,
    is_provider_available,
    list_models,
)

console = Console()


@click.group()
@click.version_option(package_name="bananarama")
def main() -> None:
    """Generate presentation images from YAML configs using AI models."""


@main.command()
@click.argument("path", default="bananarama.yaml")
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Output directory (overrides YAML config).",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Regenerate all images, even if they exist.",
)
@click.option(
    "--max-pixels",
    default=4096 * 4096,
    type=int,
    help="Max pixels per output image. Larger images are split into tiles.",
    show_default=True,
)
def generate(
    path: str,
    output_dir: str | None,
    force: bool,
    max_pixels: int,
) -> None:
    """Generate images from a YAML configuration file.

    PATH is the path to a bananarama.yaml file or a directory containing one.
    Defaults to 'bananarama.yaml' in the current directory.
    """
    try:
        asyncio.run(
            bananarama(
                path,
                output_dir=output_dir,
                force=force,
                max_pixels=max_pixels,
            )
        )
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1) from e


@main.command("models")
def models_cmd() -> None:
    """List all available image generation models with pricing and status."""
    table = Table(title="Available Models")
    table.add_column("Model", style="cyan")
    table.add_column("Provider", style="green")
    table.add_column("Est. $/img", justify="right")
    table.add_column("Status")

    for model_name in list_models():
        provider = get_provider_name(model_name)
        available = is_provider_available(model_name)
        status = "[green]Ready[/green]" if available else "[red]No SDK[/red]"

        est = estimate_cost(model_name)
        price_str = f"~${est:.3f}" if est is not None else "—"

        table.add_row(model_name, provider, price_str, status)

    console.print(table)
