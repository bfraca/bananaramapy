"""Command-line interface for bananarama."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from bananarama.ci import scaffold_workflow
from bananarama.costs.log import last_runs, log_path, spend_by_model, total_spend
from bananarama.costs.pricing import estimate_cost
from bananarama.generate import CostLimitExceededError, bananarama
from bananarama.models.registry import (
    ProviderStatus,
    check_provider_status,
    get_provider_name,
    list_models,
)
from bananarama.templates import get_template_path, init_project, list_templates

console = Console()
error_console = Console(stderr=True)


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
@click.option(
    "--concurrency",
    "-c",
    default=5,
    type=click.IntRange(min=1),
    show_default=True,
    help="Maximum number of concurrent API calls.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for --dry-run results (json is useful for CI/CD).",
)
@click.option(
    "--max-cost",
    type=float,
    default=None,
    help="Abort if estimated cost exceeds this amount (in USD).",
)
def generate(
    path: str,
    output_dir: str | None,
    force: bool,
    max_pixels: int,
    dry_run: bool,
    concurrency: int,
    output_format: str,
    max_cost: float | None,
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
                concurrency=concurrency,
                output_format=output_format,
                max_cost=max_cost,
            )
        )
    except FileNotFoundError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e
    except CostLimitExceededError as e:
        error_console.print(f"[red]Cost limit exceeded:[/red] {e}")
        raise SystemExit(2) from e
    except ValueError as e:
        error_console.print(f"[red]Configuration error:[/red] {e}")
        raise SystemExit(1) from e


@main.command("models")
@click.option(
    "--provider",
    "-p",
    default=None,
    help="Filter by provider name (e.g. google, openai, flux).",
)
def models_cmd(provider: str | None) -> None:
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
        provider_display = get_provider_name(model_name)

        # Filter by provider if requested
        if provider is not None and provider.lower() not in provider_display.lower():
            continue

        status_enum = check_provider_status(model_name)
        status = status_style[status_enum]

        est = estimate_cost(model_name)
        price_str = f"~${est:.3f}" if est is not None else "—"

        table.add_row(model_name, provider_display, price_str, status)

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


@main.command("templates")
def templates_cmd() -> None:
    """List available built-in project templates."""
    templates = list_templates()
    if not templates:
        console.print("[dim]No templates found.[/dim]")
        return

    table = Table(title="Available Templates")
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Model", style="green")
    table.add_column("Images", justify="right")

    for tmpl in templates:
        table.add_row(
            tmpl.name,
            tmpl.description,
            tmpl.recommended_model,
            str(tmpl.image_count),
        )

    console.print(table)
    console.print(
        "\n[dim]Use [bold]bananarama init --template NAME my-project/[/bold] "
        "to scaffold a new project.[/dim]"
    )


@main.command("init")
@click.option(
    "--template",
    "-t",
    default="editorial",
    show_default=True,
    help="Template to use. Run 'bananarama templates' to see options.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing bananarama.yaml in the destination.",
)
@click.option(
    "--preview",
    is_flag=True,
    default=False,
    help="Preview the template with a dry-run (no API calls).",
)
@click.argument("dest", default=".")
def init_cmd(template: str, overwrite: bool, preview: bool, dest: str) -> None:
    """Scaffold a new project from a built-in template.

    DEST is the target directory (created if it doesn't exist).
    Defaults to the current directory.
    """
    if preview:
        # Just dry-run the template YAML in-place
        try:
            tmpl_path = get_template_path(template)
        except ValueError as e:
            error_console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1) from e

        console.print(f"[bold]Previewing template '{template}'...[/bold]\n")
        try:
            asyncio.run(bananarama(tmpl_path, dry_run=True))
        except (FileNotFoundError, ValueError) as e:
            error_console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1) from e
        return

    try:
        dest_path = Path(dest).resolve()
        config_path = init_project(template, dest_path, overwrite=overwrite)
    except ValueError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1) from e
    except FileExistsError as e:
        error_console.print(f"[yellow]Warning:[/yellow] {e}")
        raise SystemExit(1) from e

    console.print(f"[green]Created[/green] {config_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. cd {dest_path}")
    console.print(
        "  2. Edit bananarama.yaml — customize descriptions and add your own images"
    )
    console.print(
        "  3. Add reference images (e.g. logo.png) and use [logo] in descriptions"
    )
    console.print("  4. Run: bananarama generate")
    console.print(
        "\n[dim]Tip: Run [bold]bananarama generate --dry-run[/bold] "
        "to preview costs before generating.[/dim]"
    )


@main.group("ci")
def ci_group() -> None:
    """CI/CD integration commands."""


@ci_group.command("init")
@click.option(
    "--config",
    default="bananarama.yaml",
    show_default=True,
    help="Path to the bananarama config (relative to repo root).",
)
@click.option(
    "--concurrency",
    "-c",
    default=5,
    type=click.IntRange(min=1),
    show_default=True,
    help="Max concurrent API calls in CI.",
)
@click.option(
    "--max-cost",
    type=float,
    default=None,
    help="Cost threshold in USD — CI aborts if estimate exceeds this.",
)
@click.option(
    "--extra-deps",
    default="",
    help="Optional extras to install in CI (e.g. 'all', 'openai', 'flux').",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing workflow file.",
)
@click.argument("dest", default=".")
def ci_init_cmd(
    config: str,
    concurrency: int,
    max_cost: float | None,
    extra_deps: str,
    overwrite: bool,
    dest: str,
) -> None:
    """Scaffold a GitHub Actions workflow for bananarama.

    DEST is the root of the target repository. Defaults to current directory.
    Creates .github/workflows/bananarama.yaml with sensible defaults.
    """
    try:
        dest_path = Path(dest).resolve()
        workflow_path = scaffold_workflow(
            dest_path,
            config=config,
            concurrency=concurrency,
            max_cost=max_cost,
            extra_deps=extra_deps,
            overwrite=overwrite,
        )
    except FileExistsError as e:
        error_console.print(f"[yellow]Warning:[/yellow] {e}")
        raise SystemExit(1) from e

    console.print(f"[green]Created[/green] {workflow_path}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Add your API keys as GitHub repository secrets:")
    console.print("     - GEMINI_API_KEY")
    console.print("     - OPENAI_API_KEY (if using OpenAI models)")
    console.print("     - TOGETHER_API_KEY (if using FLUX models)")
    console.print("  2. Commit and push the workflow file")
    console.print(
        "  3. PRs will get cost estimates; pushes to main will generate images"
    )
    console.print("\n[dim]Tip: Set --max-cost to prevent runaway costs in CI.[/dim]")
