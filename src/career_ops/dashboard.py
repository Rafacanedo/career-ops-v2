"""
dashboard.py — Static applications dashboard generator.

Reads pipeline state from SQLite via CareerOpsRepository, shapes a
dashboard-oriented view model, and writes a self-contained HTML artifact
for local use.
"""

from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import click

from .config import get_db_path, load_states
from .context import CareerOpsContext, pass_ctx
from .repository import CareerOpsRepository
from .utils import validate_status

HIGH_SCORE_THRESHOLD = 4.5
RECENT_APPLICATION_LIMIT = 7


def _status_to_dashboard_group(status: str, states: dict) -> str:
    if status.strip().lower() == "queued":
        return "queued"
    normalized = validate_status(status)
    lowered = normalized.lower()
    for state_id, meta in states.items():
        if state_id == lowered or meta["label"].lower() == lowered:
            return meta["dashboard_group"]
    return lowered


def _report_reference_to_href(root: Path, report_value: str, output_path: Path) -> str | None:
    report_value = report_value.strip()
    if not report_value:
        return None

    md_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", report_value)
    if md_match:
        raw_path = md_match.group(2).strip()
    elif report_value.startswith("local:"):
        raw_path = report_value.split(":", 1)[1].strip()
    else:
        raw_path = report_value

    candidates = [
        root / raw_path,
        root / "output" / "reports" / Path(raw_path).name,
        root / "workspace" / raw_path,
        root / raw_path.replace("workspace/", "", 1),
    ]
    report_path = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    relative = Path(os.path.relpath(report_path, output_path.parent))
    return relative.as_posix()


def _report_reference_label(report_value: str) -> str:
    report_value = report_value.strip()
    if not report_value:
        return "Report"
    md_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", report_value)
    if md_match:
        return md_match.group(1).strip() or "Report"
    return "Open"


def _build_dashboard_data(root: Path, output_path: Path) -> dict:
    db_path = get_db_path(root)
    repo = CareerOpsRepository(db_path=db_path, auto_init=True)
    rows = repo.list_vagas(limit=10000)
    states = load_states(root)

    applications = []
    counts_by_status = Counter()
    counts_by_group = Counter()

    for row in rows:
        raw_status = str(row.get("status") or row.get("status_triagem") or "Evaluated")
        if raw_status.strip().lower() == "queued":
            status_label = "Queued"
        else:
            status_label = validate_status(raw_status)
        dashboard_group = _status_to_dashboard_group(status_label, states)

        score_raw = row.get("score")
        score_value = float(score_raw) if score_raw is not None else 0.0
        score_text = f"{score_value:.1f}/5" if score_raw is not None else ""

        report_raw = str(row.get("report_path") or "")
        report_href = _report_reference_to_href(root, report_raw, output_path)
        cv_raw = str(row.get("cv_pdf_path") or "")
        pdf_ready = bool(cv_raw.strip())
        report_available = bool(report_raw.strip())
        date_str = str(row.get("application_date") or row.get("created_at") or "")[:10]

        seq_val = row.get("seq_num")
        record = {
            "id": row["id"],
            "seq_num": seq_val,
            "seq_label": f"#{seq_val:03d}" if seq_val is not None else "",
            "date": date_str,
            "company": row["company"],
            "role": row["role"],
            "status": status_label,
            "dashboard_group": dashboard_group,
            "score_text": score_text,
            "score_value": score_value,
            "pdf_ready": pdf_ready,
            "report_path": report_href,
            "report_label": _report_reference_label(report_raw),
            "report_available": report_available,
            "notes": str(row.get("notes") or ""),
        }
        applications.append(record)
        counts_by_status[record["status"]] += 1
        counts_by_group[dashboard_group] += 1

    applications.sort(key=lambda item: (item["date"], str(item["id"])), reverse=True)

    scored = [item["score_value"] for item in applications if item["score_text"].strip()]
    average_score = round(sum(scored) / len(scored), 2) if scored else 0.0
    recent = applications[:RECENT_APPLICATION_LIMIT]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(db_path),
        "summary": {
            "total_applications": len(applications),
            "average_score": average_score,
            "high_score_count": sum(1 for item in applications if item["score_value"] >= HIGH_SCORE_THRESHOLD),
            "recent_application_count": len(recent),
            "counts_by_status": dict(sorted(counts_by_status.items())),
            "counts_by_group": dict(sorted(counts_by_group.items())),
        },
        "recent_applications": recent,
        "applications": applications,
    }


def _render_summary_cards(summary: dict) -> str:
    return f"""
    <section class="cards">
      <article class="card"><span>Total</span><strong>{summary["total_applications"]}</strong></article>
      <article class="card"><span>Average Score</span><strong>{summary["average_score"]:.2f}</strong></article>
      <article class="card"><span>High Score (>= {HIGH_SCORE_THRESHOLD:.1f})</span><strong>{summary["high_score_count"]}</strong></article>
      <article class="card"><span>Recent</span><strong>{summary["recent_application_count"]}</strong></article>
    </section>
    """


def _render_group_chips(summary: dict) -> str:
    chips = []
    for group, count in summary["counts_by_group"].items():
        chips.append(
            f'<button class="chip" type="button" data-group="{html.escape(group)}">{html.escape(group.title())} <strong>{count}</strong></button>'
        )
    return '<section class="chip-row">' + "".join(chips) + "</section>"


def _render_recent_list(recent_applications: list[dict]) -> str:
    items = []
    for item in recent_applications:
        items.append(
            "<li>"
            f"<span>{html.escape(item['date'])}</span>"
            f"<strong>{html.escape(item['company'])}</strong>"
            f"<em>{html.escape(item['role'])}</em>"
            "</li>"
        )
    return '<section class="recent"><h2>Recent Applications</h2><ul>' + "".join(items) + "</ul></section>"


def render_dashboard_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Applications Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4efe6;
      --panel: rgba(255, 252, 247, 0.92);
      --ink: #14213d;
      --muted: #5f6b7a;
      --accent: #b85c38;
      --accent-soft: #f0c7a7;
      --line: #dbcdb8;
      --ok: #2f855a;
      --warn: #b7791f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(184, 92, 56, 0.12), transparent 32%),
        linear-gradient(180deg, #f8f2e7 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      margin-bottom: 24px;
    }}
    h1, h2 {{ margin: 0; }}
    p {{ margin: 0; color: var(--muted); }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
      margin: 20px 0;
    }}
    .card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 30px rgba(20, 33, 61, 0.06);
    }}
    .card span {{
      display: block;
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 8px;
    }}
    .card strong {{
      font-size: 1.85rem;
      letter-spacing: -0.03em;
    }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin: 16px 0 24px;
    }}
    .chip {{
      border: 1px solid var(--line);
      background: #fff8ef;
      border-radius: 999px;
      padding: 10px 14px;
      cursor: pointer;
      color: var(--ink);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 18px;
    }}
    .recent ul {{
      list-style: none;
      padding: 0;
      margin: 16px 0 0;
      display: grid;
      gap: 12px;
    }}
    .recent li {{
      border-top: 1px solid var(--line);
      padding-top: 12px;
      display: grid;
      gap: 3px;
    }}
    .recent li:first-child {{
      border-top: 0;
      padding-top: 0;
    }}
    .recent span, .meta {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .recent em {{
      font-style: normal;
      color: var(--muted);
    }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    label {{
      display: grid;
      gap: 6px;
      font-size: 0.92rem;
      color: var(--muted);
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: #fffdf9;
      color: var(--ink);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-top: 1px solid var(--line);
      vertical-align: top;
    }}
    th button {{
      border: 0;
      background: transparent;
      color: inherit;
      font: inherit;
      padding: 0;
      cursor: pointer;
    }}
    tbody tr:hover {{
      background: rgba(240, 199, 167, 0.18);
    }}
    .status {{
      display: inline-block;
      border-radius: 999px;
      padding: 4px 9px;
      background: var(--accent-soft);
      font-size: 0.84rem;
    }}
    .flag-ok {{ color: var(--ok); font-weight: 700; }}
    .flag-warn {{ color: var(--warn); font-weight: 700; }}
    .empty {{
      padding: 20px 0 8px;
      color: var(--muted);
      display: none;
    }}
    .hidden {{ display: none; }}
    a {{ color: var(--accent); }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns: 1fr; }}
      table, thead, tbody, th, td, tr {{ display: block; }}
      thead {{ display: none; }}
      tbody tr {{
        border-top: 1px solid var(--line);
        padding: 10px 0;
      }}
      td {{
        border-top: 0;
        padding: 6px 0;
      }}
      td::before {{
        content: attr(data-label);
        display: block;
        color: var(--muted);
        font-size: 0.84rem;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <p class="meta">Source: {html.escape(data["source_file"])}</p>
        <h1>Applications Dashboard</h1>
      </div>
      <p class="meta">Generated {html.escape(data["generated_at"])}</p>
    </header>
    {_render_summary_cards(data["summary"])}
    {_render_group_chips(data["summary"])}
    <section class="layout">
      <aside class="panel">
        {_render_recent_list(data["recent_applications"])}
      </aside>
      <section class="panel">
        <div class="filters">
          <label>Search
            <input id="search" type="search" placeholder="company, role, notes">
          </label>
          <label>Status Group
            <select id="groupFilter"><option value="">All groups</option></select>
          </label>
          <label>Status
            <select id="statusFilter"><option value="">All statuses</option></select>
          </label>
          <label>Company
            <select id="companyFilter"><option value="">All companies</option></select>
          </label>
          <label>Min Score
            <select id="scoreFilter">
              <option value="">Any score</option>
              <option value="4.5">4.5+</option>
              <option value="4.0">4.0+</option>
              <option value="3.5">3.5+</option>
              <option value="3.0">3.0+</option>
            </select>
          </label>
          <label>PDF Ready
            <select id="pdfFilter">
              <option value="">Any</option>
              <option value="true">Ready</option>
              <option value="false">Pending</option>
            </select>
          </label>
          <label>Report Link
            <select id="reportFilter">
              <option value="">Any</option>
              <option value="true">Available</option>
              <option value="false">Missing</option>
            </select>
          </label>
        </div>
        <div class="meta" id="resultCount"></div>
        <div class="empty" id="emptyState">No applications match the current filters.</div>
        <table>
          <thead>
            <tr>
              <th><button data-sort="date">Date</button></th>
              <th><button data-sort="company">Company</button></th>
              <th><button data-sort="role">Role</button></th>
              <th><button data-sort="status">Status</button></th>
              <th><button data-sort="score_value">Score</button></th>
              <th>PDF</th>
              <th>Report</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody id="rows"></tbody>
        </table>
      </section>
    </section>
  </main>
  <script>
    const dashboardData = {payload};
    const state = {{ sortKey: "date", sortDirection: "desc", activeGroup: "" }};
    const rowsEl = document.getElementById("rows");
    const emptyEl = document.getElementById("emptyState");
    const resultCountEl = document.getElementById("resultCount");
    const filters = {{
      search: document.getElementById("search"),
      group: document.getElementById("groupFilter"),
      status: document.getElementById("statusFilter"),
      company: document.getElementById("companyFilter"),
      score: document.getElementById("scoreFilter"),
      pdf: document.getElementById("pdfFilter"),
      report: document.getElementById("reportFilter")
    }};

    function populateSelect(select, values) {{
      values.forEach((value) => {{
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }});
    }}

    populateSelect(filters.group, [...new Set(dashboardData.applications.map((item) => item.dashboard_group))].sort());
    populateSelect(filters.status, [...new Set(dashboardData.applications.map((item) => item.status))].sort());
    populateSelect(filters.company, [...new Set(dashboardData.applications.map((item) => item.company))].sort());

    document.querySelectorAll(".chip").forEach((chip) => {{
      chip.addEventListener("click", () => {{
        state.activeGroup = state.activeGroup === chip.dataset.group ? "" : chip.dataset.group;
        filters.group.value = state.activeGroup;
        render();
      }});
    }});

    document.querySelectorAll("[data-sort]").forEach((button) => {{
      button.addEventListener("click", () => {{
        const key = button.dataset.sort;
        if (state.sortKey === key) {{
          state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
        }} else {{
          state.sortKey = key;
          state.sortDirection = key === "date" ? "desc" : "asc";
        }}
        render();
      }});
    }});

    Object.values(filters).forEach((input) => input.addEventListener("input", render));

    function matches(item) {{
      const search = filters.search.value.trim().toLowerCase();
      const groupFilter = filters.group.value;
      const statusFilter = filters.status.value;
      const companyFilter = filters.company.value;
      const minScore = filters.score.value ? parseFloat(filters.score.value) : null;
      const pdfFilter = filters.pdf.value;
      const reportFilter = filters.report.value;

      if (search) {{
        const haystack = [item.company, item.role, item.notes].join(" ").toLowerCase();
        if (!haystack.includes(search)) return false;
      }}
      if (groupFilter && item.dashboard_group !== groupFilter) return false;
      if (statusFilter && item.status !== statusFilter) return false;
      if (companyFilter && item.company !== companyFilter) return false;
      if (minScore !== null && item.score_value < minScore) return false;
      if (pdfFilter && String(item.pdf_ready) !== pdfFilter) return false;
      if (reportFilter && String(item.report_available) !== reportFilter) return false;
      return true;
    }}

    function compare(a, b) {{
      const key = state.sortKey;
      const direction = state.sortDirection === "asc" ? 1 : -1;
      const left = a[key];
      const right = b[key];
      if (left < right) return -1 * direction;
      if (left > right) return 1 * direction;
      return 0;
    }}

    function render() {{
      const filtered = dashboardData.applications.filter(matches).sort(compare);
      rowsEl.innerHTML = "";
      filtered.forEach((item) => {{
        const row = document.createElement("tr");
        const reportCell = item.report_path
          ? `<a href="${{item.report_path}}">${{item.report_label || "Open"}}</a>`
          : "";
        row.innerHTML = `
          <td data-label="Date">${{item.date}}</td>
          <td data-label="Company">${{item.company}}</td>
          <td data-label="Role">${{item.role}}</td>
          <td data-label="Status"><span class="status">${{item.status}}</span></td>
          <td data-label="Score">${{item.score_text}}</td>
          <td data-label="PDF"><span class="${{item.pdf_ready ? "flag-ok" : "flag-warn"}}">${{item.pdf_ready ? "Ready" : "Pending"}}</span></td>
          <td data-label="Report">${{reportCell}}</td>
          <td data-label="Notes">${{item.notes || ""}}</td>
        `;
        rowsEl.appendChild(row);
      }});
      resultCountEl.textContent = `${{filtered.length}} matching application(s)`;
      emptyEl.style.display = filtered.length ? "none" : "block";
    }}

    render();
  </script>
</body>
</html>
"""


@click.group()
def dashboard_cmd() -> None:
    """Generate static dashboard artifacts from SQLite database."""


@dashboard_cmd.command("build")
@click.option(
    "--output",
    default=None,
    metavar="FILE",
    help="Output HTML file. Defaults to workspace/output/dashboard.html.",
)
@pass_ctx
def dashboard_build_cmd(ctx: CareerOpsContext, output: str | None) -> None:
    """Build a self-contained HTML dashboard."""
    root = ctx.root
    output_path = Path(output) if output else root / "workspace" / "output" / "dashboard.html"
    data = _build_dashboard_data(root, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard_html(data), encoding="utf-8")
    click.echo(f"[OK] dashboard.html -> {output_path}")
