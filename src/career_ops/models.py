"""
models.py — Dataclasses for career-ops data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AppEntry:
    """
    Represents a single row in applications.md.

    Column order in the markdown table:
    | # | Date | Company | Role | Score | Status | PDF | Report | Notes |
    """
    num: int
    date: str
    company: str
    role: str
    score: str
    status: str
    pdf: str
    report: str
    notes: str
    raw: str = field(default="", repr=False)  # original line (for in-place edits)


@dataclass
class TrackerAddition:
    """
    Represents a single pending tracker addition from a .tsv file.

    TSV column order (status BEFORE score):
    num | date | company | role | status | score | pdf | report | notes
    """
    num: int
    date: str
    company: str
    role: str
    status: str
    score: str
    pdf: str
    report: str
    notes: str = ""
