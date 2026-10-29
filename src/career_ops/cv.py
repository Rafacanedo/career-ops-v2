"""
cv.py — Python wrapper for generate-pdf.mjs
"""

from __future__ import annotations

import os
import subprocess
import sys
import click
from .context import pass_ctx, CareerOpsContext

@click.command()
@click.argument("input_html", type=click.Path(exists=True))
@click.argument("output_pdf", type=click.Path())
@click.option("--format", type=click.Choice(["a4", "letter"]), default="a4", help="PDF page format.")
@click.option("--keep-html", is_flag=True, help="Keep the temporary HTML file after generation.")
@pass_ctx
def cv_cmd(ctx: CareerOpsContext, input_html: str, output_pdf: str, format: str, keep_html: bool) -> None:
    """Generate a clean, ATS-parseable PDF from HTML using Node.js/Playwright."""
    
    # Path to the .mjs script relative to the project root
    # Since this logic is running from src/career_ops/pdf.py, 
    # and generate-pdf.mjs is in the root:
    script_path = os.path.join(ctx.root, "generate-pdf.mjs")
    
    if not os.path.exists(script_path):
        click.secho(f"Error: Could not find {script_path}", fg="red")
        sys.exit(1)
        
    env = os.environ.copy()
    node_fallback_dir = os.path.expanduser("~/.cache/ms-playwright-go/1.57.0")
    if os.path.exists(node_fallback_dir):
        env["PATH"] = f"{env.get('PATH', '')}:{node_fallback_dir}"

    cmd = ["node", script_path, input_html, output_pdf, f"--format={format}"]
    if keep_html:
        cmd.append("--keep-html")
        
    click.echo(f"Running: {' '.join(cmd)}")
    
    try:
        # Run node script and inherit stdout/stderr
        result = subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        click.secho("PDF generation failed.", fg="red")
        sys.exit(1)
    except FileNotFoundError:
        click.secho("Error: 'node' command not found. Please install Node.js.", fg="red")
        sys.exit(1)

    if result.returncode == 0:
        click.secho(f"Successfully generated {output_pdf}", fg="green")
