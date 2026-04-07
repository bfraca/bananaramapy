"""Command-line interface for bananarama."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from bananarama.costs.log import last_runs, log_path, spend_by_model, total_spend
from bananarama.costs.pricing import estimate_cost
from bananarama.generate import bananarama
from bananarama.models.registry import (
    ProviderStatus,
    check_provider_status,
    get_provider_name,
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
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be generated and estimated costs, without calling APIs.",
)
def generate(
    path: str,
    output_dir: str | None,
    force: bool,
    max_pixels: int,
    dry_run: bool,
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
                dry_run=dry_run,
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

    status_style: dict[ProviderStatus, str] = {
        ProviderStatus.READY: "[green]Ready[/green]",
        ProviderStatus.NO_KEY: "[yellow]No Key[/yellow]",
        ProviderStatus.NO_SDK: "[red]No SDK[/red]",
    }

    for model_name in list_models():
        provider = get_provider_name(model_name)
        status_enum = check_provider_status(model_name)
        status = status_style[status_enum]

        est = estimate_cost(model_name)
        price_str = f"~${est:.3f}" if est is not None else "—"

        table.add_row(model_name, provider, price_str, status)

    console.print(table)


@main.command("costs")
def costs_cmd() -> None:
    """Show a summary of historical image generation costs."""
    path = log_path()
    if not path.exists():
        console.print("[dim]No cost log found yet. Generate some images first![/dim]")
        return

    # Total spend
    total = total_spend()
    console.print(f"\n[bold]Total spend to date:[/bold] ${total:.4f}")

    # Spend by model
    by_model = spend_by_model()
    if by_model:
        model_table = Table(title="Spend by Model")
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Total Cost", justify="right")
        for model, cost in sorted(by_model.items(), key=lambda x: -x[1]):
            model_table.add_row(model, f"${cost:.4f}")
        console.print(model_table)

    # Last 10 runs
    recent = last_runs(10)
    if recent:
        runs_table = Table(title="Last 10 Runs")
        runs_table.add_column("Timestamp", style="dim")
        runs_table.add_column("Config")
        runs_table.add_column("Model", style="cyan")
        runs_table.add_column("Images", justify="right")
        runs_table.add_column("Cost", justify="right")
        for row in recent:
            runs_table.add_row(
                row["timestamp"],
                row["config_path"],
                row["model"],
                row["images_generated"],
                f"${float(row['total_cost']):.4f}",
            )
        console.print(runs_table)

    console.print(f"\n[dim]Log file: {path}[/dim]")
