"""
cli.py — Click entry-point for career-ops-python.

All subcommands share the global --root option, which points to
the career-ops project directory (or CAREER_OPS_ROOT env var).
"""

from __future__ import annotations

import io
import os
import sys
import click
from dotenv import load_dotenv

load_dotenv()

# Enable UTF-8 mode on Windows so emojis render correctly in terminal.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass

from .context import CareerOpsContext, pass_ctx  # noqa: F401 (re-exported)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--root",
    envvar="CAREER_OPS_ROOT",
    default=None,
    metavar="PATH",
    help="Path to the career-ops project root. Defaults to CAREER_OPS_ROOT env var or cwd.",
)
@click.version_option(package_name="career-ops-python")
@click.pass_context
def cli(ctx: click.Context, root: str | None) -> None:
    """career-ops Python tools — pipeline integrity, tracker management, and more."""
    ctx.obj = CareerOpsContext(root)


# ---------------------------------------------------------------------------
# Subcommand imports
# ---------------------------------------------------------------------------

from .normalize import normalize_cmd          # noqa: E402
from .verify import verify_cmd                # noqa: E402
from .sync_check import sync_check_cmd        # noqa: E402
from .dedup import dedup_cmd                  # noqa: E402
from .cv import cv_cmd                       # noqa: E402
from .export import export_cmd                # noqa: E402
from .scan_csv import scan_csv_cmd            # noqa: E402
from .dashboard import dashboard_cmd          # noqa: E402
from .fetch_cmd import fetch_cmd              # noqa: E402
from .unapplied import unapplied_cmd          # noqa: E402
from .tracker import tracker_cmd              # noqa: E402


cli.add_command(normalize_cmd, name="normalize")
cli.add_command(verify_cmd, name="verify")
cli.add_command(sync_check_cmd, name="sync-check")
cli.add_command(dedup_cmd, name="dedup")
cli.add_command(cv_cmd, name="cv")
cli.add_command(export_cmd, name="export")
cli.add_command(scan_csv_cmd, name="scan-csv")
cli.add_command(dashboard_cmd, name="dashboard")
cli.add_command(fetch_cmd, name="fetch")
cli.add_command(unapplied_cmd, name="unapplied")
cli.add_command(tracker_cmd, name="tracker")


if __name__ == "__main__":
    cli()
