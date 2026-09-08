"""
tests/test_statutory_de_minimis.py

Unit tests for 3-Second De Minimis Visual Prominence Metric (Ringgold v. BET).
Sprint 3.3 - Invariant: Deterministic observability thresholds.
"""

import pytest

from backend.core.statutory_rules import eval_de_minimis
from backend.core.statutory_types import (
    DeMinimisEvaluation,
    InvalidDurationError,
    InvalidProminenceError,
    StatutoryRuleError,
)


def test_qualifying_de_minimis_uses():
    """Duration under 3.0s and qualifying non-prominent visibility qualify as de minimis."""
    for prominence in ["out_of_focus", "background_fleeting", "obscured"]:
        for dur in [0.1, 1.0, 2.5, 2.99]:
            res = eval_de_minimis(duration_sec=dur, focal_prominence=prominence)
            assert isinstance(res, DeMinimisEvaluation)
            assert res.is_de_minimis is True
            assert res.actionable_risk == "TRIAGE_FAVORABLE_DE_MINIMIS"
            assert res.confidence == 0.70
            assert "Ringgold v. Black Entertainment Television" in res.legal_precedent


def test_duration_threshold_boundary():
    """At exactly 3.0s or above, de minimis does not qualify regardless of prominence."""
    for dur in [3.0, 3.01, 4.0, 10.0]:
        res = eval_de_minimis(duration_sec=dur, focal_prominence="out_of_focus")
        assert res.is_de_minimis is False
        assert res.actionable_risk == "ACTIONABLE_COPYRIGHT_RISK"
        assert "exceeds" in res.rationale


def test_non_qualifying_prominence():
    """In-focus, foreground, or hero prominence fails de minimis even with duration < 3.0s."""
    for prominence in ["in_focus", "foreground", "hero", "prominent", "center_screen"]:
        res = eval_de_minimis(duration_sec=1.5, focal_prominence=prominence)
        assert res.is_de_minimis is False
        assert res.actionable_risk == "ACTIONABLE_COPYRIGHT_RISK"


def test_prominence_case_and_whitespace_normalization():
    """Prominence matching is case-insensitive and trims leading/trailing whitespace."""
    res1 = eval_de_minimis(duration_sec=1.2, focal_prominence="  OUT_OF_FOCUS  ")
    assert res1.is_de_minimis is True
    assert res1.focal_prominence == "out_of_focus"

    res2 = eval_de_minimis(duration_sec=2.0, focal_prominence="Background_Fleeting")
    assert res2.is_de_minimis is True
    assert res2.focal_prominence == "background_fleeting"


def test_total_work_ratio_inclusion():
    """Optional total_work_ratio is validated and preserved in evaluation."""
    res = eval_de_minimis(
        duration_sec=1.0, focal_prominence="obscured", total_work_ratio=0.02
    )
    assert res.is_de_minimis is True
    assert res.total_work_ratio == 0.02
    assert "2.0%" in res.rationale


def test_invalid_input_exceptions():
    """Rejects negative duration, empty prominence, and invalid work ratio."""
    with pytest.raises(InvalidDurationError):
        eval_de_minimis(duration_sec=-0.5, focal_prominence="obscured")

    with pytest.raises(InvalidProminenceError):
        eval_de_minimis(duration_sec=1.0, focal_prominence="")

    with pytest.raises(InvalidProminenceError):
        eval_de_minimis(duration_sec=1.0, focal_prominence="   ")

    with pytest.raises(StatutoryRuleError):
        eval_de_minimis(duration_sec=1.0, focal_prominence="obscured", total_work_ratio=1.5)

    with pytest.raises(StatutoryRuleError):
        eval_de_minimis(duration_sec=1.0, focal_prominence="obscured", total_work_ratio=-0.1)
