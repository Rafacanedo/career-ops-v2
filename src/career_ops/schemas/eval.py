from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class EvaluationPayload(BaseModel):
    vaga_id: str
    cv_match: Literal["exact", "high", "medium", "low"]
    level_alignment: Literal["stretch", "target", "overqualified"]
    comp_alignment: Literal["above_range", "in_range", "below_range", "unverified"]
    cultural_signals: Literal["positive", "neutral", "red_flags"]
    strategic_alignment: Literal["north_star", "adjacent", "distraction"]
    blockers: List[str] = Field(default_factory=list)
    archetype: Optional[str] = None
    report_path: Optional[str] = None
    notes: Optional[str] = None
