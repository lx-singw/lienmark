"""
backend/agents/research/directed_research_types.py

Canonical Pydantic v2 schemas and taxonomy for counsel directives and directed clearance research.
Sprint 4.3: Counsel Rejection & Directed Re-Investigation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.domain.models import PublicEvidenceSnapshot


class DirectiveConstraintType(str, Enum):
    """Taxonomy of search constraints extracted from counsel directives."""
    REGISTRY = "REGISTRY"
    YEAR = "YEAR"
    TERRITORY = "TERRITORY"
    RIGHT_SCOPE = "RIGHT_SCOPE"
    KEYWORD = "KEYWORD"
    ENTITY = "ENTITY"


class DirectedSearchStatus(str, Enum):
    """Lifecycle status of directed research execution."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    PARTIAL = "partial"


class DirectedResearchError(Exception):
    """Base domain exception for directed research subsystem."""
    pass


class DirectiveSanitizationError(DirectedResearchError):
    """Raised when directive string fails parsing or sanitization invariants."""
    pass


class DirectedSearchTimeoutError(DirectedResearchError):
    """Raised when directed research exceeds execution latency budget."""
    pass


class DirectiveConstraint(BaseModel):
    """Atomic constraint extracted from counsel directive."""
    model_config = ConfigDict(frozen=True)

    constraint_type: Union[DirectiveConstraintType, str] = Field(
        ..., description="Taxonomy type of constraint (REGISTRY, YEAR, TERRITORY, RIGHT_SCOPE, KEYWORD, ENTITY)."
    )
    value: str = Field(..., min_length=1, description="Normalized constraint value.")
    is_mandatory: bool = Field(default=True, description="Whether constraint must appear in search queries.")


class SanitizedDirective(BaseModel):
    """Structured output of directive sanitization."""
    model_config = ConfigDict(frozen=True)

    raw_directive: str = Field(..., description="Original raw counsel directive text.")
    clean_directive: str = Field(..., description="Directive stripped of conversational filler.")
    extracted_constraints: List[DirectiveConstraint] = Field(
        default_factory=list, description="Structured constraints list."
    )
    extracted_entities: List[str] = Field(
        default_factory=list, description="Extracted corporate/organization entities."
    )
    extracted_years: List[int] = Field(
        default_factory=list, description="Extracted 4-digit calendar years."
    )
    extracted_territories: List[str] = Field(
        default_factory=list, description="Extracted jurisdiction/territory codes."
    )
    sanitized_query_addon: str = Field(
        default="", description="Optimized search engine query addon string."
    )


class DirectedSearchRequest(BaseModel):
    """Specification for directed research execution."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, description="Baseline asset title or mark.")
    raw_directive: str = Field(..., min_length=1, description="Raw counsel directive.")
    artist_or_author: Optional[str] = Field(default=None, description="Primary creator or claimant.")
    sanitized_directive: Optional[SanitizedDirective] = Field(
        default=None, description="Pre-sanitized directive if already parsed."
    )
    asset_id: Optional[str] = Field(default=None, description="Unique asset identifier.")
    stable_lineage_key: Optional[str] = Field(default=None, description="Lineage key for cache isolation.")
    claim_id: Optional[str] = Field(default=None, description="Claim identifier under re-investigation.")
    timeout_seconds: float = Field(default=15.0, gt=0.0, le=30.0, description="Hard timeout ceiling (max 15s standard).")
    target_registry: Optional[str] = Field(default=None, description="Specific registry domain target.")
    year: Optional[Union[int, str]] = Field(default=None, description="Baseline asset creation year.")
    catalog_id: Optional[str] = Field(default=None, description="Catalog or registration number.")
    asset_type: Optional[str] = Field(default=None, description="Asset class/type.")
    preliminary_findings: Optional[str] = Field(default=None, description="Summary of rejected finding.")
    use_cache: bool = Field(default=True, description="Whether to leverage disambiguated cache.")


class DirectedSearchResult(BaseModel):
    """Consolidated outcome of directed re-investigation search."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., description="Asset title investigated.")
    raw_directive: str = Field(..., description="Original counsel directive.")
    clean_directive: str = Field(..., description="Sanitized counsel directive.")
    reformulated_queries: List[str] = Field(
        default_factory=list, description="All reformulated queries generated."
    )
    primary_query: str = Field(default="", description="Primary executed query string.")
    snapshots: List[PublicEvidenceSnapshot] = Field(
        default_factory=list, description="Evidence snapshots returned from search."
    )
    constraints_applied: List[DirectiveConstraint] = Field(
        default_factory=list, description="Directive constraints injected into search."
    )
    execution_time_seconds: float = Field(
        default=0.0, ge=0.0, description="Total execution wall-clock time in seconds."
    )
    status: str = Field(default="success", description="Execution status: success, timeout, error.")
    error_message: Optional[str] = Field(default=None, description="Failure detail if non-success.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Audit telemetry.")
