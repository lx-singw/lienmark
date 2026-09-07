"""
tests/test_statutory_fair_use.py

Unit tests for Structured 4-Factor Fair Use Scorecard (17 U.S.C. § 107).
Sprint 3.3 - Pure deterministic mathematical scoring matrix without LLM drift.
"""

from pydantic import ValidationError
import pytest

from backend.core.statutory_rules import eval_fair_use_scorecard
from backend.core.statutory_types import (
    FairUseEvaluation,
    FairUseFactors,
    FairUseOutcome,
    InvalidFactorScoreError,
)


def test_fair_use_likely_strong_transformative():
    """Highly transformative, factual, minimal excerpt, beneficial market use."""
    factors = FairUseFactors(
        purpose_and_character=2,
        nature_of_work=1,
        amount_and_substantiality=2,
        market_harm=2,
    )
    res = eval_fair_use_scorecard(factors)
    assert isinstance(res, FairUseEvaluation)
    assert res.aggregate_score == 7
    assert res.recommendation == FairUseOutcome.FAIR_USE_LIKELY
    assert res.confidence == 0.94
    assert res.factor_breakdown["purpose_and_character"] == 2


def test_fair_use_unlikely_commercial_piracy():
    """Verbatim commercial exploitation, creative work, full copy, market substitution."""
    factors = FairUseFactors(
        purpose_and_character=-2,
        nature_of_work=-1,
        amount_and_substantiality=-2,
        market_harm=-3,
    )
    res = eval_fair_use_scorecard(factors)
    assert res.aggregate_score == -8
    assert res.recommendation == FairUseOutcome.FAIR_USE_UNLIKELY
    assert res.confidence == 1.0


def test_fair_use_uncertain_boundary_scores():
    """Scores of -1, 0, and +1 map deterministically to FAIR_USE_UNCERTAIN."""
    # Score 0
    f_zero = FairUseFactors(
        purpose_and_character=1,
        nature_of_work=-1,
        amount_and_substantiality=1,
        market_harm=-1,
    )
    res_zero = eval_fair_use_scorecard(f_zero)
    assert res_zero.aggregate_score == 0
    assert res_zero.recommendation == FairUseOutcome.FAIR_USE_UNCERTAIN
    assert res_zero.confidence == 0.50

    # Score +1
    f_plus1 = FairUseFactors(
        purpose_and_character=1,
        nature_of_work=0,
        amount_and_substantiality=0,
        market_harm=0,
    )
    assert eval_fair_use_scorecard(f_plus1).recommendation == FairUseOutcome.FAIR_USE_UNCERTAIN

    # Score -1
    f_minus1 = FairUseFactors(
        purpose_and_character=-1,
        nature_of_work=0,
        amount_and_substantiality=0,
        market_harm=0,
    )
    assert eval_fair_use_scorecard(f_minus1).recommendation == FairUseOutcome.FAIR_USE_UNCERTAIN


def test_outcome_threshold_boundaries():
    """Tests exact score thresholds at +2 (LIKELY) and -2 (UNLIKELY)."""
    # Score +2: LIKELY
    f2 = FairUseFactors(
        purpose_and_character=1,
        nature_of_work=0,
        amount_and_substantiality=1,
        market_harm=0,
    )
    assert eval_fair_use_scorecard(f2).recommendation == FairUseOutcome.FAIR_USE_LIKELY

    # Score -2: UNLIKELY
    f_neg2 = FairUseFactors(
        purpose_and_character=-1,
        nature_of_work=0,
        amount_and_substantiality=-1,
        market_harm=0,
    )
    assert eval_fair_use_scorecard(f_neg2).recommendation == FairUseOutcome.FAIR_USE_UNLIKELY


def test_pydantic_factor_bounds_validation():
    """Asserts that invalid factor inputs outside statutory limits fail validation."""
    with pytest.raises(ValidationError):
        FairUseFactors(purpose_and_character=3, nature_of_work=0, amount_and_substantiality=0, market_harm=0)

    with pytest.raises(ValidationError):
        FairUseFactors(purpose_and_character=0, nature_of_work=2, amount_and_substantiality=0, market_harm=0)

    with pytest.raises(ValidationError):
        FairUseFactors(purpose_and_character=0, nature_of_work=0, amount_and_substantiality=-3, market_harm=0)

    with pytest.raises(ValidationError):
        FairUseFactors(purpose_and_character=0, nature_of_work=0, amount_and_substantiality=0, market_harm=-4)


def test_eval_fair_use_scorecard_type_guard():
    """Asserts InvalidFactorScoreError on non-FairUseFactors argument."""
    with pytest.raises(InvalidFactorScoreError):
        eval_fair_use_scorecard({"purpose_and_character": 1})  # type: ignore
