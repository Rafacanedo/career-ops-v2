"""
Deterministic evaluation scoring engine for Career-Ops v2.
"""

from __future__ import annotations

from typing import List, Tuple
from ..schemas.eval import EvaluationPayload

BLOCKER_SCORE_CAP = 3.2

# Dimension scores (1.0 - 5.0 scale)
CV_MATCH_SCORES = {
    "exact": 5.0,
    "high": 4.5,
    "medium": 3.0,
    "low": 1.5,
}

STRATEGIC_SCORES = {
    "north_star": 5.0,
    "adjacent": 3.5,
    "distraction": 1.0,
}

LEVEL_SCORES = {
    "target": 5.0,
    "stretch": 4.0,
    "overqualified": 3.0,
}

COMP_SCORES = {
    "above_range": 5.0,
    "in_range": 4.5,
    "unverified": 3.5,
    "below_range": 1.0,
}

# Dimension weights summing to 1.0
WEIGHT_CV = 0.40
WEIGHT_STRATEGIC = 0.25
WEIGHT_LEVEL = 0.20
WEIGHT_COMP = 0.15


def calculate_score(payload: EvaluationPayload) -> Tuple[float, List[str]]:
    """
    Calculate deterministic weighted score (1.0 - 5.0) and enforce blocker caps.
    
    Returns:
        tuple of (final_score, effective_blockers)
    """
    s_cv = CV_MATCH_SCORES[payload.cv_match]
    s_strat = STRATEGIC_SCORES[payload.strategic_alignment]
    s_level = LEVEL_SCORES[payload.level_alignment]
    s_comp = COMP_SCORES[payload.comp_alignment]

    weighted_score = (
        (WEIGHT_CV * s_cv)
        + (WEIGHT_STRATEGIC * s_strat)
        + (WEIGHT_LEVEL * s_level)
        + (WEIGHT_COMP * s_comp)
    )

    effective_blockers = list(payload.blockers)
    if payload.cultural_signals == "red_flags":
        red_flag_note = "Cultural red flags detected"
        if red_flag_note not in effective_blockers:
            effective_blockers.append(red_flag_note)

    if effective_blockers:
        final_score = min(weighted_score, BLOCKER_SCORE_CAP)
    else:
        final_score = weighted_score

    return round(final_score, 2), effective_blockers
