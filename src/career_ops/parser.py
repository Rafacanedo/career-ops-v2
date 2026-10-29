"""
parser.py — Parsing utilities for applications.md and .tsv tracker additions.

Consolidates duplicated parsing logic from merge-tracker.mjs,
dedup-tracker.mjs, and verify-pipeline.mjs into reusable functions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import AppEntry, TrackerAddition
from .utils import validate_status


def _looks_like_score(value: str) -> bool:
    value = value.strip()
    if value in ("N/A", "DUP"):
        return True
    import re
    return bool(re.match(r"^\d+\.?\d*/5$", value))


def parse_app_line(line: str) -> Optional[AppEntry]:
    """
    Parse a single pipe-delimited row from applications.md.

    Format: | # | Date | Company | Role | Score | Status | PDF | Report | Notes |

    Returns None for header, separator, and malformed lines.
    """
    if not line.startswith("|"):
        return None
    parts = [p.strip() for p in line.split("|")]
    # parts[0] is empty (before first |), parts[-1] is empty (after last |)
    if len(parts) < 11:  # empty + 9 cols + empty = 11
        return None

    try:
        num = int(parts[1])
    except ValueError:
        return None

    if num <= 0:
        return None

    col5 = parts[5]
    col6 = parts[6]
    if _looks_like_score(col5) and not _looks_like_score(col6):
        score, status = col5, col6
    else:
        status, score = col5, col6

    return AppEntry(
        num=num,
        date=parts[2],
        company=parts[3],
        role=parts[4],
        status=status,
        score=score,
        pdf=parts[7],
        report=parts[8],
        notes=parts[9] if len(parts) > 10 else "",
        raw=line,
    )


def read_applications(apps_file: Path) -> tuple[list[str], list[AppEntry]]:
    """
    Read and parse applications.md.

    Returns:
        lines    — raw file lines (for in-place editing)
        entries  — parsed AppEntry list (data rows only)
    """
    content = apps_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    entries: list[AppEntry] = []

    for line in lines:
        if not line.startswith("|"):
            continue
        if "---" in line or "Company" in line or "Empresa" in line:
            continue
        entry = parse_app_line(line)
        if entry:
            entries.append(entry)

    return lines, entries


def parse_tsv_content(content: str, filename: str = "<unknown>") -> Optional[TrackerAddition]:
    """
    Parse a .tsv file into a TrackerAddition.

    Handles three input formats:
      1. 9-col TSV:  num\\tdate\\tcompany\\trole\\tstatus\\tscore\\tpdf\\treport\\tnotes
      2. 8-col TSV:  num\\tdate\\tcompany\\trole\\tstatus\\tscore\\tpdf\\treport
      3. Pipe-delimited markdown row: | col | col | ... |

    Includes heuristic column-order detection (status/score may be swapped).
    Returns None on malformed input.
    """
    content = content.strip()
    if not content:
        return None

    # --- Pipe-delimited markdown row ---
    if content.startswith("|"):
        parts = [p.strip() for p in content.split("|") if p.strip()]
        if len(parts) < 8:
            print(f"⚠️  Skipping malformed pipe-delimited {filename}: {len(parts)} fields")
            return None
        # Format: num | date | company | role | score | status | pdf | report | notes
        try:
            num = int(parts[0])
        except ValueError:
            print(f"⚠️  Skipping {filename}: invalid entry number")
            return None
        return TrackerAddition(
            num=num,
            date=parts[1],
            company=parts[2],
            role=parts[3],
            score=parts[4],
            status=validate_status(parts[5]),
            pdf=parts[6],
            report=parts[7],
            notes=parts[8] if len(parts) > 8 else "",
        )

    # --- Tab-separated ---
    parts = content.split("\t")
    if len(parts) < 8:
        print(f"⚠️  Skipping malformed TSV {filename}: {len(parts)} fields")
        return None

    col4 = parts[4].strip()
    col5 = parts[5].strip()

    # Heuristic: detect whether col4 is status or score
    _score_pat = r"^\d+\.?\d*/5$"
    import re
    _status_candidates = (
        r"^(evaluated|applied|interview|offer|rejected|discarded|skip"
        r"|evaluada|aplicado|entrevista|oferta|rechazado|descartado"
        r"|no aplicar|cerrada|duplicado|repost|condicional|hold|monitor|verificar)"
    )

    col4_is_score = bool(re.match(_score_pat, col4)) or col4 in ("N/A", "DUP")
    col5_is_score = bool(re.match(_score_pat, col5)) or col5 in ("N/A", "DUP")
    col4_is_status = bool(re.match(_status_candidates, col4, re.IGNORECASE))
    col5_is_status = bool(re.match(_status_candidates, col5, re.IGNORECASE))

    if col4_is_status and not col4_is_score:
        status_val, score_val = col4, col5
    elif col4_is_score and col5_is_status:
        status_val, score_val = col5, col4
    elif col5_is_score and not col4_is_score:
        status_val, score_val = col4, col5
    else:
        # Default: col4=status, col5=score
        status_val, score_val = col4, col5

    try:
        num = int(parts[0])
    except ValueError:
        print(f"⚠️  Skipping {filename}: invalid entry number")
        return None

    if num <= 0:
        print(f"⚠️  Skipping {filename}: invalid entry number")
        return None

    return TrackerAddition(
        num=num,
        date=parts[1].strip(),
        company=parts[2].strip(),
        role=parts[3].strip(),
        status=validate_status(status_val),
        score=score_val,
        pdf=parts[6].strip() if len(parts) > 6 else "",
        report=parts[7].strip() if len(parts) > 7 else "",
        notes=parts[8].strip() if len(parts) > 8 else "",
    )
