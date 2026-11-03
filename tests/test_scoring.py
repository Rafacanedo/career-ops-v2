import pytest
from career_ops.schemas.eval import EvaluationPayload
from career_ops.eval.scoring import calculate_score, BLOCKER_SCORE_CAP


def test_perfect_fit_score():
    payload = EvaluationPayload(
        vaga_id="vaga_1",
        cv_match="exact",
        level_alignment="target",
        comp_alignment="above_range",
        cultural_signals="positive",
        strategic_alignment="north_star",
        blockers=[],
    )
    score, blockers = calculate_score(payload)
    assert score == 5.0
    assert len(blockers) == 0


def test_standard_high_fit_score():
    payload = EvaluationPayload(
        vaga_id="vaga_2",
        cv_match="high",  # 4.5 * 0.40 = 1.80
        level_alignment="target",  # 5.0 * 0.20 = 1.00
        comp_alignment="in_range",  # 4.5 * 0.15 = 0.675
        cultural_signals="positive",
        strategic_alignment="north_star",  # 5.0 * 0.25 = 1.25
        blockers=[],
    )
    # Total = 1.80 + 1.00 + 0.675 + 1.25 = 4.725 -> 4.72
    score, blockers = calculate_score(payload)
    assert score == 4.72
    assert len(blockers) == 0


def test_blocker_capping():
    payload = EvaluationPayload(
        vaga_id="vaga_3",
        cv_match="exact",
        level_alignment="target",
        comp_alignment="above_range",
        cultural_signals="positive",
        strategic_alignment="north_star",
        blockers=["Must be physically located in London"],
    )
    score, blockers = calculate_score(payload)
    assert score == BLOCKER_SCORE_CAP
    assert score == 3.2
    assert len(blockers) == 1


def test_cultural_red_flags_auto_blocker():
    payload = EvaluationPayload(
        vaga_id="vaga_4",
        cv_match="exact",
        level_alignment="target",
        comp_alignment="above_range",
        cultural_signals="red_flags",
        strategic_alignment="north_star",
        blockers=[],
    )
    score, blockers = calculate_score(payload)
    assert score == BLOCKER_SCORE_CAP
    assert "Cultural red flags detected" in blockers


def test_low_fit_unblocked():
    payload = EvaluationPayload(
        vaga_id="vaga_5",
        cv_match="low",  # 1.5 * 0.40 = 0.60
        level_alignment="stretch",  # 4.0 * 0.20 = 0.80
        comp_alignment="below_range",  # 1.0 * 0.15 = 0.15
        cultural_signals="neutral",
        strategic_alignment="distraction",  # 1.0 * 0.25 = 0.25
        blockers=[],
    )
    # Total = 0.60 + 0.80 + 0.15 + 0.25 = 1.80
    score, blockers = calculate_score(payload)
    assert score == 1.80
    assert len(blockers) == 0
