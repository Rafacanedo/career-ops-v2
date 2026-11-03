"""
config.py — Path resolution and configuration loading for career-ops-python.

Resolves CAREER_OPS_ROOT from environment variable or CLI argument.
Loads states.yml for canonical status definitions.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def _is_project_root(path: Path) -> bool:
    """Return True if path contains known career-ops project root markers."""
    return (
        (path / "data" / "career_ops.db").exists()
        or (path / "config" / "states.yml").exists()
        or (path / "pyproject.toml").exists()
    )


def resolve_root(root: str | None = None) -> Path:
    """
    Resolve the path to the career-ops project root.

    Priority order:
    1. The explicitly passed `root` argument (from --root CLI flag)
    2. CAREER_OPS_ROOT environment variable
    3. Current working directory — works when you `cd career-ops-python && uv run career-ops`
    4. Package install location ancestor — src/career_ops/config.py → ../../.. = project root
    """
    if root:
        return Path(root).resolve()

    env = os.environ.get("CAREER_OPS_ROOT")
    if env:
        return Path(env).resolve()

    # cwd fallback — the standard case when running from the project directory
    cwd = Path.cwd()
    if _is_project_root(cwd):
        return cwd

    # Package location fallback — src/career_ops/config.py → go 3 levels up = project root
    pkg_root = Path(__file__).resolve().parent.parent.parent
    if _is_project_root(pkg_root):
        return pkg_root

    # Last resort: cwd (no data files found, commands will handle gracefully)
    return cwd


def get_db_path(root: Path | None = None) -> Path:
    """Return the path to data/career_ops.db."""
    resolved = root if root is not None else resolve_root()
    return resolved / "data" / "career_ops.db"


def get_output_dir(root: Path) -> Path:
    """Return the standard output directory for generated artifacts."""
    return root / "workspace" / "output"


def get_cv_output_dir(root: Path) -> Path:
    """Return the standard output directory for generated ATS resumes."""
    return root / "output" / "cv"


def get_reports_dir(root: Path) -> Path:
    """Return the standard deliverable path to evaluation reports."""
    return root / "output" / "reports"


def get_states_file(root: Path) -> Path:
    """
    Return the path to states.yml.
    Only config/states.yml is supported.
    """
    return root / "config" / "states.yml"


def load_states(root: Path) -> dict:
    """
    Load canonical states from states.yml.
    Returns a dict: {id: {label, aliases, description, dashboard_group}}
    """
    states_file = get_states_file(root)
    if not states_file.exists():
        return {}
    with open(states_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result = {}
    for state in data.get("states", []):
        result[state["id"]] = {
            "label": state["label"],
            "aliases": [a.lower() for a in state.get("aliases", [])],
            "description": state.get("description", ""),
            "dashboard_group": state.get("dashboard_group", state["id"]),
        }
    return result


# Canonical statuses (hardcoded for scripts that don't need states.yml)
CANONICAL_STATUSES = [
    "Evaluated", "Applied", "Interview",
    "Offer", "Rejected", "Discarded", "SKIP",
]

# Status rank for advancement comparison (higher = further in pipeline)
STATUS_RANK: dict[str, int] = {
    "skip": 0, "no aplicar": 0,
    "discarded": 0, "descartado": 0,
    "rejected": 1, "rechazado": 1,
    "evaluated": 2, "evaluada": 2,
    "applied": 3, "aplicado": 3,
    "interview": 4, "entrevista": 4,
    "offer": 5, "oferta": 5,
}
