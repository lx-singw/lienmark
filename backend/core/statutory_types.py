"""
backend/core/statutory_types.py

Domain models, enums, typed exceptions, and immutable data contracts
for the deterministic statutory rule engine.
Sprint 3.3 - 100% pure, deterministic Python with zero freehand drift.
"""

from __future__ import annotations

from enum import Enum
import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class StatutoryRuleError(Exception):
    """Base exception for statutory rule evaluation failures."""
    pass


class InvalidPublicationYearError(StatutoryRuleError):
    """Raised when publication year is outside valid physical or statutory range."""
    pass


class InvalidDurationError(StatutoryRuleError):
    """Raised when media duration is negative or non-numeric."""
    pass


class InvalidProminenceError(StatutoryRuleError):
    """Raised when focal prominence descriptor is empty or invalid."""
    pass


class InvalidFactorScoreError(StatutoryRuleError):
    """Raised when a fair use factor score falls outside statutory limits."""
    pass


class StatutoryEra(str, Enum):
    """Statutory copyright regime eras under U.S. Copyright Act."""
    PRE_1923 = "pre_1923"
    YEARS_1923_TO_1977 = "1923_to_1977"
    POST_1977 = "post_1977"


class FairUseOutcome(str, Enum):
    """Deterministic statutory outcome recommendation under 17 U.S.C. § 107."""
    FAIR_USE_LIKELY = "FAIR_USE_LIKELY"
    FAIR_USE_UNCERTAIN = "FAIR_USE_UNCERTAIN"
    FAIR_USE_UNLIKELY = "FAIR_USE_UNLIKELY"


class FocalProminence(str, Enum):
    """Standardized focal prominence levels under Ringgold de minimis doctrine."""
    OUT_OF_FOCUS = "out_of_focus"
    BACKGROUND_FLEETING = "background_fleeting"
    OBSCURED = "obscured"
    IN_FOCUS = "in_focus"
    FOREGROUND = "foreground"
    HERO = "hero"
    PROMINENT = "prominent"


class PublicDomainEvaluation(BaseModel):
    """Immutable evaluation result for 95-year rolling public domain test."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_public_domain: bool = Field(..., description="Whether work is in the U.S. public domain")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Deterministic confidence score")
    publication_year: int = Field(..., description="Year work was published")
    reference_year: int = Field(..., description="Reference calendar year evaluated against")
    threshold_year: int = Field(..., description="Rolling threshold year (reference_year - 95)")
    statutory_era: StatutoryEra = Field(..., description="Governing copyright era")
    statutory_citation: str = Field(..., description="Exact statutory citation")
    rationale: str = Field(..., description="Deterministic legal explanation")
    is_work_made_for_hire: bool = Field(default=False, description="Work made for hire flag")
    author_death_year: Optional[int] = Field(default=None, description="Author year of death if known")
    evaluation_date: datetime.date = Field(..., description="Explicit evaluation date")
    jurisdiction: str = Field(default="US", description="Jurisdiction")
    work_type: str = Field(default="unspecified", description="Work type")
    applicable_term: str = Field(..., description="Applicable term")
    verified_facts: bool = Field(default=True, description="Whether facts are verified")


class DeMinimisEvaluation(BaseModel):
    """Immutable evaluation result for 3-second de minimis visual prominence metric."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_de_minimis: bool = Field(..., description="Whether visual use qualifies as non-actionable de minimis")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Deterministic confidence score")
    duration_sec: float = Field(..., ge=0.0, description="Duration in seconds of visual appearance")
    focal_prominence: str = Field(..., description="Observed visual prominence level")
    total_work_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Ratio of appearance to full work")
    legal_precedent: str = Field(..., description="Controlling legal authority")
    rationale: str = Field(..., description="Deterministic legal reasoning")
    actionable_risk: str = Field(..., description="Clearance risk categorization")


class FairUseFactors(BaseModel):
    """
    Structured 4-factor statutory inputs under 17 U.S.C. § 107.
    Enforces exact statutory mathematical bounds on all four factors.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    purpose_and_character: int = Field(
        ...,
        ge=-2,
        le=2,
        description="Factor 1: -2 (commercial verbatim) to +2 (transformative educational/non-profit)",
    )
    nature_of_work: int = Field(
        ...,
        ge=-1,
        le=1,
        description="Factor 2: -1 (highly creative/fictional) to +1 (published factual/historical)",
    )
    amount_and_substantiality: int = Field(
        ...,
        ge=-2,
        le=2,
        description="Factor 3: -2 (heart of work/substantial) to +2 (minimal excerpt/de minimis)",
    )
    market_harm: int = Field(
        ...,
        ge=-3,
        le=2,
        description="Factor 4: -3 (direct market substitute) to +2 (no discernible market impact)",
    )


class FairUseEvaluation(BaseModel):
    """Immutable evaluation result for structured 4-factor fair use scorecard."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    aggregate_score: int = Field(..., ge=-8, le=7, description="Pure aggregate mathematical score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Deterministic confidence metric")
    recommendation: FairUseOutcome = Field(..., description="Statutory outcome recommendation")
    factor_breakdown: Dict[str, int] = Field(..., description="Exact individual factor scores")
    statutory_citation: str = Field(..., description="Governing statutory citation")
    rationale: str = Field(..., description="Deterministic legal factor balancing rationale")
