"""
Native CV compilation engine for Career-Ops v2 using Jinja2 and Playwright.
"""

from __future__ import annotations

import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from ..schemas.cv import CVPayload

# Conversion constants
MM_TO_PX = 3.7795275591
LINE_HEIGHT_PX = 18.0
PAGE_MARGIN_INCHES = 0.3
MARGIN_MM = PAGE_MARGIN_INCHES * 25.4
TOTAL_VERTICAL_MARGIN_MM = MARGIN_MM * 2  # top + bottom = 15.24mm

PAGE_DIMENSIONS_MM = {
    "a4": {"width": 210.0, "height": 297.0},
    "letter": {"width": 215.9, "height": 279.4},
}


class CVOverflowError(Exception):
    """Raised when CV content height exceeds single-page printable budget."""

    def __init__(self, telemetry: Dict[str, Any]):
        self.telemetry = telemetry
        super().__init__(
            f"CV content exceeds 1-page printable boundary by {telemetry.get('overflow_px', 0)}px "
            f"(~{telemetry.get('estimated_line_excess', 0)} lines)."
        )


@dataclass
class RenderResult:
    pdf_path: Path
    format: str
    page_count: int
    telemetry: Dict[str, Any]


def ensure_playwright_browsers() -> None:
    """Ensure Chromium browser binary is provisioned for Playwright."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            # Quick check if executable path resolves
            p.chromium.executable_path
    except Exception:
        # Attempt automated provisioning
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )


def get_default_template_path() -> Path:
    # Look in assets/templates/ats_clean.html relative to project root
    # or inside the package
    root = Path(__file__).resolve().parent.parent.parent.parent
    candidate = root / "assets" / "templates" / "ats_clean.html"
    if candidate.exists():
        return candidate
    return Path(__file__).parent / "templates" / "ats_clean.html"


def render_html(payload: CVPayload, template_path: Optional[Path | str] = None) -> str:
    tpl_path = Path(template_path) if template_path else get_default_template_path()
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template not found at: {tpl_path}")

    env = Environment(
        loader=FileSystemLoader(str(tpl_path.parent)),
        autoescape=True,
    )
    template = env.get_template(tpl_path.name)
    data = payload.model_dump()
    return template.render(**data)


def compile_cv(
    payload: CVPayload,
    out_path: Path | str,
    format: Optional[str] = None,
    template_path: Optional[Path | str] = None,
) -> RenderResult:
    """
    Compile a validated CVPayload into an ATS-compliant single-page PDF.
    
    Raises:
        CVOverflowError: if content exceeds the single-page printable area.
    """
    fmt = (format or payload.format).lower()
    if fmt not in PAGE_DIMENSIONS_MM:
        raise ValueError(f"Unsupported format: {fmt}. Must be 'a4' or 'letter'.")

    paper = PAGE_DIMENSIONS_MM[fmt]
    printable_height_mm = paper["height"] - TOTAL_VERTICAL_MARGIN_MM
    printable_width_mm = paper["width"]

    viewport_width_px = int(printable_width_mm * MM_TO_PX)
    viewport_height_px = int(printable_height_mm * MM_TO_PX)
    max_printable_height_px = printable_height_mm * MM_TO_PX

    html_content = render_html(payload, template_path)
    output_pdf = Path(out_path).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    ensure_playwright_browsers()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_viewport_size({"width": viewport_width_px, "height": viewport_height_px})
            page.set_content(html_content, wait_until="load")
            page.emulate_media(media="print")
            page.evaluate("() => document.fonts.ready")

            # Measure DOM bounding boxes and scroll height
            dom_check_script = """
            (maxHeight) => {
                const bodyHeight = document.body.scrollHeight;
                const sections = {};
                document.querySelectorAll('[data-section]').forEach(el => {
                    sections[el.getAttribute('data-section')] = Math.round(el.offsetHeight);
                });
                return {
                    body_height_px: Math.round(bodyHeight),
                    max_height_px: Math.round(maxHeight),
                    is_overflow: bodyHeight > maxHeight,
                    overflow_px: Math.max(0, Math.round(bodyHeight - maxHeight)),
                    section_heights: sections
                };
            }
            """
            telemetry = page.evaluate(dom_check_script, max_printable_height_px)

            if telemetry.get("is_overflow", False):
                overflow_px = telemetry.get("overflow_px", 0)
                telemetry["estimated_line_excess"] = math.ceil(overflow_px / LINE_HEIGHT_PX)
                telemetry["status"] = "overflow"
                raise CVOverflowError(telemetry)

            # Print to vector PDF with standard text layer
            page.pdf(
                path=str(output_pdf),
                format=fmt.upper(),
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": f"{PAGE_MARGIN_INCHES}in",
                    "bottom": f"{PAGE_MARGIN_INCHES}in",
                    "left": f"{PAGE_MARGIN_INCHES}in",
                    "right": f"{PAGE_MARGIN_INCHES}in",
                },
            )
        finally:
            browser.close()

    return RenderResult(
        pdf_path=output_pdf,
        format=fmt,
        page_count=1,
        telemetry=telemetry,
    )
