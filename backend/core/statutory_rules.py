"""
backend/core/statutory_rules.py

Deterministic statutory legal rule engine implementing pure Python calculations
for Public Domain (17 U.S.C. § 304), De Minimis (Ringgold v. BET), and
4-Factor Fair Use Scorecard (17 U.S.C. § 107).
Authored strictly under Google AntiGravity architectural guidelines for Sprint 3.3.
"""

from __future__ import annotations

from typing import Optional

from backend.core.statutory_public_domain import eval_public_domain
from backend.core.statutory_types import (
    DeMinimisEvaluation,
    FairUseEvaluation,
    FairUseFactors,
    FairUseOutcome,
    FocalProminence,
    InvalidDurationError,
    InvalidFactorScoreError,
    InvalidProminenceError,
    PublicDomainEvaluation,
    StatutoryEra,
    StatutoryRuleError,
)

__all__ = [
    "eval_public_domain",
    "eval_de_minimis",
    "eval_fair_use_scorecard",
]

DE_MINIMIS_QUALIFYING_PROMINENCE = frozenset({
    FocalProminence.OUT_OF_FOCUS.value,
    FocalProminence.BACKGROUND_FLEETING.value,
    FocalProminence.OBSCURED.value,
})

RINGGOLD_PRECEDENT = "Ringgold v. Black Entertainment Television, Inc., 126 F.3d 70 (2d Cir. 1997)"
CITATION_FAIR_USE = "17 U.S.C. § 107 (Limitations on exclusive rights: Fair use)"


def _validate_de_minimis_params(
    duration_sec: float,
    focal_prominence: str,
    total_work_ratio: Optional[float],
) -> str:
    """Validates inputs for de minimis evaluation and returns normalized prominence."""
    if not isinstance(duration_sec, (int, float)) or duration_sec < 0.0:
        raise InvalidDurationError(f"duration_sec must be non-negative, got {duration_sec}")
    if not isinstance(focal_prominence, str) or not focal_prominence.strip():
        raise InvalidProminenceError("focal_prominence must be a non-empty string")
    if total_work_ratio is not None:
        if not isinstance(total_work_ratio, (int, float)) or not (0.0 <= total_work_ratio <= 1.0):
            raise StatutoryRuleError(f"total_work_ratio must be in [0.0, 1.0], got {total_work_ratio}")
    return focal_prominence.strip().lower()


def _build_de_minimis_rationale(
    is_de_minimis: bool,
    duration_sec: float,
    norm_prom: str,
    total_work_ratio: Optional[float],
) -> str:
    """Builds legal explanatory rationale under Ringgold v. BET observability doctrine."""
    if is_de_minimis:
        rat = (
            f"Visual appearance ({duration_sec:.2f}s < 3.0s, prominence '{norm_prom}') lacks "
            f"sufficient legal observability under Ringgold v. BET; non-actionable de minimis."
        )
    else:
        rat = (
            f"Visual appearance ({duration_sec:.2f}s, prominence '{norm_prom}') exceeds "
            f"Ringgold v. BET de minimis threshold; constitutes actionable observability."
        )
    if total_work_ratio is not None:
        rat += f" Total work ratio: {total_work_ratio:.1%}."
    return rat


def eval_de_minimis(
    duration_sec: float,
    focal_prominence: str,
    total_work_ratio: Optional[float] = None,
) -> DeMinimisEvaluation:
    """
    3-Second De Minimis Visual Prominence Metric (Ringgold v. Black Entertainment Television).
    Deterministic rule: duration_sec < 3.0 AND focal_prominence in qualifying set.
    """
    norm_prom = _validate_de_minimis_params(duration_sec, focal_prominence, total_work_ratio)
    is_de_minimis = (duration_sec < 3.0) and (norm_prom in DE_MINIMIS_QUALIFYING_PROMINENCE)
    risk = "NONE_DE_MINIMIS" if is_de_minimis else "ACTIONABLE_COPYRIGHT_RISK"
    rat = _build_de_minimis_rationale(is_de_minimis, duration_sec, norm_prom, total_work_ratio)

    return DeMinimisEvaluation(
        is_de_minimis=is_de_minimis,
        confidence=1.0,
        duration_sec=float(duration_sec),
        focal_prominence=norm_prom,
        total_work_ratio=float(total_work_ratio) if total_work_ratio is not None else None,
        legal_precedent=RINGGOLD_PRECEDENT,
        rationale=rat,
        actionable_risk=risk,
    )


def _compute_fair_use_confidence(aggregate_score: int) -> float:
    """Computes deterministic confidence based on absolute deviation from zero point."""
    return round(0.50 + 0.50 * (abs(aggregate_score) / 8.0), 2)


def _compute_fair_use_outcome(aggregate_score: int) -> FairUseOutcome:
    """Maps deterministic aggregate score to statutory recommendation."""
    if aggregate_score >= 2:
        return FairUseOutcome.FAIR_USE_LIKELY
    if aggregate_score <= -2:
        return FairUseOutcome.FAIR_USE_UNLIKELY
    return FairUseOutcome.FAIR_USE_UNCERTAIN


def _build_fair_use_rationale(
    factors: FairUseFactors, score: int, outcome: FairUseOutcome
) -> str:
    """Constructs deterministic explanatory rationale for the 4-factor scorecard."""
    return (
        f"Aggregate score {score} (range [-8, +7]). Factor 1: {factors.purpose_and_character}, "
        f"Factor 2: {factors.nature_of_work}, Factor 3: {factors.amount_and_substantiality}, "
        f"Factor 4: {factors.market_harm}. Outcome: {outcome.value} under 17 U.S.C. § 107."
    )


def eval_fair_use_scorecard(factors: FairUseFactors) -> FairUseEvaluation:
    """
    Structured 4-Factor Fair Use Scorecard (17 U.S.C. § 107).
    Pure mathematical scoring matrix with ZERO freehand LLM drift.
    """
    if not isinstance(factors, FairUseFactors):
        raise InvalidFactorScoreError(f"factors must be FairUseFactors, got {type(factors).__name__}")

    score = (
        factors.purpose_and_character
        + factors.nature_of_work
        + factors.amount_and_substantiality
        + factors.market_harm
    )
    outcome = _compute_fair_use_outcome(score)
    confidence = _compute_fair_use_confidence(score)
    breakdown = {
        "purpose_and_character": factors.purpose_and_character,
        "nature_of_work": factors.nature_of_work,
        "amount_and_substantiality": factors.amount_and_substantiality,
        "market_harm": factors.market_harm,
    }
    rationale = _build_fair_use_rationale(factors, score, outcome)

    return FairUseEvaluation(
        aggregate_score=score,
        confidence=confidence,
        recommendation=outcome,
        factor_breakdown=breakdown,
        statutory_citation=CITATION_FAIR_USE,
        rationale=rationale,
    )
