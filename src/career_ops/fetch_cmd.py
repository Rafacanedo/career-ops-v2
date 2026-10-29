import click
from pathlib import Path

from .context import CareerOpsContext, pass_ctx
from .fetcher.orchestrator import FetchOrchestrator

@click.command()
@click.option(
    "--config",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to the fetch configuration file (YAML or JSON). Defaults to config/portals.yml.",
)
@click.option(
    "--source",
    type=click.Choice(["all", "ats", "serp"]),
    default="all",
    help="Which source type to fetch from (all, ats, or serp).",
)
@pass_ctx
def fetch_cmd(ctx: CareerOpsContext, config: Path | None, source: str) -> None:
    """Fetch job postings via ATS and Google Search APIs."""
    root = ctx.root
    
    if config is None:
        config = root / "config" / "portals.yml"
        
    if not config.exists():
        click.secho(f"[ERROR] Config file not found: {config}", fg="red")
        return

    click.echo(f"Starting Job Fetcher Cycle using config: {config.name} (Source: {source})")
    try:
        orchestrator = FetchOrchestrator(root_dir=root, config_path=config, source=source)
        stats = orchestrator.run()
        
        click.echo("\n--- Fetch Cycle Complete ---")
        click.echo(f"Total jobs fetched:  {stats['fetched']}")
        click.echo(f"Jobs filtered out:   {stats['filtered']}")
        click.echo(f"New jobs saved:      {stats['saved']}")
        if stats['errors'] > 0:
            click.echo(f"Errors encountered:  {stats['errors']}")
            
        if stats['saved'] > 0:
            click.echo("\nRun '/career-ops-pipeline' to evaluate your new pipeline offers!")
            
    except Exception as e:
        click.secho(f"[ERROR] Fetch failed: {e}", fg="red")
        import traceback
        traceback.print_exc()
