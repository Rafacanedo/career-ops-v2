"""
utils.py — Shared utility functions for career-ops-python.

Consolidates duplicated logic from the original .mjs scripts:
  - normalizeCompany()     → normalize_company()
  - roleFuzzyMatch()       → role_fuzzy_match()
  - parseScore()           → parse_score()
  - validateStatus()       → validate_status()
  - extractReportNum()     → extract_report_num()
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .config import CANONICAL_STATUSES, STATUS_RANK

# ---------------------------------------------------------------------------
# Status aliases — maps non-canonical → canonical
# ---------------------------------------------------------------------------

_STATUS_ALIASES: dict[str, str] = {
    # Spanish legacy
    "evaluada": "Evaluated",
    "condicional": "Evaluated",
    "hold": "Evaluated",
    "evaluar": "Evaluated",
    "verificar": "Evaluated",
    "monitor": "Evaluated",
    "aplicado": "Applied",
    "enviada": "Applied",
    "aplicada": "Applied",
    "sent": "Applied",
    "entrevista": "Interview",
    "oferta": "Offer",
    "cerrada": "Discarded",
    "descartada": "Discarded",
    "cancelada": "Discarded",
    "descartado": "Discarded",
    "rechazada": "Rejected",
    "rechazado": "Rejected",
    "no aplicar": "SKIP",
    "no_aplicar": "SKIP",
    "geo blocker": "SKIP",
    "skip": "SKIP",
}


def validate_status(raw: str) -> str:
    """
    Normalise a raw status string to a canonical value.
    Falls back to 'Evaluated' with a warning print if unknown.
    """
    # Strip markdown bold and trailing date patterns
    clean = re.sub(r"\*\*", "", raw).strip()
    clean = re.sub(r"\s+\d{4}-\d{2}-\d{2}.*$", "", clean).strip()
    lower = clean.lower()

    # Already canonical (case-insensitive match)
    for c in CANONICAL_STATUSES:
        if lower == c.lower():
            return c

    # Alias lookup
    if lower in _STATUS_ALIASES:
        return _STATUS_ALIASES[lower]

    # DUPLICADO / Repost variants → Discarded
    if re.match(r"^(duplicado|dup\b|repost)", lower):
        return "Discarded"

    # Unknown — warn and default
    print(f"⚠️  Non-canonical status \"{raw}\" → defaulting to \"Evaluated\"")
    return "Evaluated"


def normalize_company(name: str) -> str:
    """
    Normalise a company name to a comparable key.
    Strips punctuation, whitespace, and lowercases.
    """
    s = name.lower()
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s.strip()


def normalize_role(role: str) -> str:
    """Normalise a role title for fuzzy comparison."""
    s = role.lower()
    s = re.sub(r"[()]", " ", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9 /]", "", s)
    return s.strip()


def role_fuzzy_match(a: str, b: str) -> bool:
    """
    Return True if roles a and b share at least 2 meaningful words.
    Ignores words shorter than 4 characters.
    """
    words_a = [w for w in normalize_role(a).split() if len(w) > 3]
    words_b = [w for w in normalize_role(b).split() if len(w) > 3]
    overlap = [
        w for w in words_a
        if any(wb in w or w in wb for wb in words_b)
    ]
    return len(overlap) >= 2


def parse_score(raw: str) -> float:
    """
    Extract numeric score from strings like '4.2/5', '**3.8/5**', 'N/A'.
    Returns 0.0 if not parseable.
    """
    cleaned = re.sub(r"\*\*", "", raw)
    m = re.search(r"([\d.]+)", cleaned)
    return float(m.group(1)) if m else 0.0


def extract_report_num(report_str: str) -> Optional[int]:
    """
    Extract the numeric report ID from a markdown link like [142](reports/142-...).
    Returns None if not found.
    """
    m = re.search(r"\[(\d+)\]", report_str)
    return int(m.group(1)) if m else None


def normalize_url(url: str) -> str:
    """
    Normalise a URL for strict deduplication.
    - Strips query parameters and fragments.
    - Extracts platform-specific IDs (LinkedIn, Gupy, Greenhouse, Inhire).
    - Lowercases everything.
    """
    # Remove markdown escapes that might be in pipeline.md
    s = url.replace("\\", "")
    s = s.strip().lower().rstrip("/")
    
    # 1. Platform-specific ID extraction
    # LinkedIn: .../view/123456789 or .../jobs/view/123456789
    m = re.search(r"linkedin\.com/jobs/view/(\d+)", s)
    if not m: m = re.search(r"linkedin\.com/view/(\d+)", s)
    if m: return f"linkedin:{m.group(1)}"
    
    # Gupy: company.gupy.io/jobs/123456 or /job/BASE64
    m = re.search(r"([a-z0-9-]+)\.gupy\.io/jobs?/(\d+)", s)
    if m: return f"gupy:{m.group(1)}:{m.group(2)}"
    m = re.search(r"([a-z0-9-]+)\.gupy\.io/job/([a-z0-9=_-]+)", s)
    if m: return f"gupy:{m.group(1)}:{m.group(2)}"
    
    # Inhire: company.inhire.app/vagas/UUID
    m = re.search(r"([a-z0-9-]+)\.inhire\.app/vagas/([a-z0-9-]+)", s)
    if m: return f"inhire:{m.group(1)}:{m.group(2)}"
    
    # Greenhouse: job-boards.greenhouse.io/company/jobs/123456
    m = re.search(r"greenhouse\.io/([a-z0-9-]+)/jobs/(\d+)", s)
    if m: return f"greenhouse:{m.group(1)}:{m.group(2)}"

    # Ashby / Deel (Custom domain or ashbyhq.com)
    # Pattern: jobs.ashbyhq.com/COMPANY/UUID
    m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9-]+)/([a-z0-9-]+)", s)
    if m: return f"ashby:{m.group(1)}:{m.group(2)}"
    # Pattern: company.com/careers/position/?ashby_jid=UUID
    m = re.search(r"ashby_jid=([a-z0-9-]+)", s)
    if m: return f"ashby:unknown:{m.group(1)}"

    # HireWithNear
    m = re.search(r"jobs\.hirewithnear\.com/#/jobs/(\d+)", s)
    if m: return f"hirewithnear:{m.group(1)}"

    # Indeed
    m = re.search(r"indeed\.com/.*?[?&]jk=([a-z0-9]+)", s)
    if m: return f"indeed:{m.group(1)}"

    # Glassdoor
    m = re.search(r"glassdoor\..*?[?&]jl=(\d+)", s)
    if m: return f"glassdoor:{m.group(1)}"

    # Mercado Libre: careers-meli.mercadolibre.com/pt/positions?id=43349639
    m = re.search(r"mercadolibre\.com/.*?[?&]id=(\d+)", s)
    if m: return f"mercadolibre:{m.group(1)}"

    # 2. Fallback: Strip query and fragment
    s = s.split("?")[0].split("#")[0]
    return s


def days_between(date_str_a: str, date_str_b: str) -> int:
    """Calculate absolute days between two ISO date strings (YYYY-MM-DD)."""
    try:
        fmt = "%Y-%m-%d"
        dt_a = datetime.strptime(date_str_a[:10], fmt)
        dt_b = datetime.strptime(date_str_b[:10], fmt)
        return abs((dt_a - dt_b).days)
    except (ValueError, TypeError):
        return 999  # Large number if unparseable


def get_status_rank(status: str) -> int:
    """Return the pipeline advancement rank for a status string."""
    return STATUS_RANK.get(status.lower(), 0)
