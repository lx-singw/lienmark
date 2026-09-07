"""
backend/agents/research/subgoal_types.py

Canonical Pydantic v2 schemas and taxonomy for clearance subgoal decomposition.
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.agents.intake.claim_types import ClaimCategory
from backend.services.parallel_types import DomainAuthorityTier


class SubgoalType(str, Enum):
    """Categorical types of investigative clearance subgoals."""

    # Music subgoals
    MUSIC_COMPOSITION_PUBLISHING = "music_composition_publishing"
    MUSIC_MASTER_RECORDING = "music_master_recording"
    MUSIC_SYNC_SCOPE = "music_sync_scope"
    MUSIC_SAMPLE_INTERPOLATION = "music_sample_interpolation"

    # Trademark / Brand subgoals
    BRAND_WORD_MARK = "brand_word_mark"
    BRAND_LOGO_STYLIZED = "brand_logo_stylized"
    BRAND_GOODS_SERVICES = "brand_goods_services"

    # Archival footage subgoals
    FOOTAGE_PUBLIC_DOMAIN_FEDERAL = "footage_public_domain_federal"
    FOOTAGE_BROADCASTER_MASTER = "footage_broadcaster_master"

    # Artwork subgoals
    ARTWORK_ORIGINAL_COPYRIGHT = "artwork_original_copyright"
    ARTWORK_PERIODICAL_PUBLICATION = "artwork_periodical_publication"
    ARTWORK_RENEWAL_STATUS = "artwork_renewal_status"

    # Likeness / Person subgoals
    LIKENESS_PUBLICITY_RIGHTS = "likeness_publicity_rights"
    LIKENESS_DEFAMATION_PRIVACY = "likeness_defamation_privacy"

    # Synthetic AI subgoals
    SYNTHETIC_TRAINING_PROVENANCE = "synthetic_training_provenance"
    SYNTHETIC_LIKENESS_CLONING = "synthetic_likeness_cloning"

    # Fallback / Generic subgoals
    GENERAL_TITLE_OWNERSHIP = "general_title_ownership"
    GENERAL_THIRD_PARTY_RIGHTS = "general_third_party_rights"


class SubgoalPriority(str, Enum):
    """Execution priority levels for clearance subgoals."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReadinessStatus(str, Enum):
    """Clearance readiness status based on retrieved search evidence."""

    READY = "ready"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    BLOCKED = "blocked"


class SubgoalDecompositionError(Exception):
    """Base domain exception for subgoal decomposition errors."""

    pass


class SubgoalReadinessError(SubgoalDecompositionError):
    """Raised when evidence evaluation for subgoal readiness fails."""

    pass


class InvestigationSubgoal(BaseModel):
    """Granular investigative objective decomposed from an extracted claim."""

    model_config = ConfigDict(frozen=True)

    subgoal_id: str = Field(..., description="Deterministic unique identifier.")
    claim_id: str = Field(..., description="Parent extracted claim identifier.")
    category: ClaimCategory = Field(..., description="Target legal clearance category.")
    subgoal_type: SubgoalType = Field(..., description="Specific rights investigation type.")
    title: str = Field(..., min_length=3, description="Succinct human-readable title.")
    description: str = Field(..., min_length=5, description="Clearance investigation query target.")
    required_identifiers: List[str] = Field(
        default_factory=list, description="Identifiers required to clear this rights facet."
    )
    target_registries: List[str] = Field(
        default_factory=list, description="Specific registries and domains relevant to this subgoal."
    )
    suggested_query_terms: List[str] = Field(
        default_factory=list, description="Targeted keyword terms suggested for search query formulation."
    )
    is_conditional: bool = Field(
        default=False, description="Whether this subgoal is conditionally activated."
    )
    condition_trigger: Optional[str] = Field(
        default=None, description="Reason or cue that triggered this conditional subgoal."
    )
    priority: SubgoalPriority = Field(
        default=SubgoalPriority.CRITICAL, description="Clearance priority level."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic and legal context metadata."
    )


class SubgoalReadiness(BaseModel):
    """Assessment of evidence completeness and clearance readiness for a subgoal."""

    model_config = ConfigDict(frozen=True)

    subgoal_id: str = Field(..., description="Assessed subgoal identifier.")
    claim_id: str = Field(..., description="Parent claim identifier.")
    is_ready: bool = Field(..., description="True if evidence is sufficient to clear or resolve.")
    readiness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized evidence completeness score."
    )
    status: ReadinessStatus = Field(..., description="Categorical readiness status.")
    matched_identifiers: Dict[str, str] = Field(
        default_factory=dict, description="Identifiers and registry values verified from evidence."
    )
    unresolved_identifiers: List[str] = Field(
        default_factory=list, description="Required identifiers missing from evidence."
    )
    authority_level: DomainAuthorityTier = Field(
        default=DomainAuthorityTier.TIER_4_GENERAL_WEB,
        description="Highest domain authority tier among supporting findings.",
    )
    supporting_urls: List[str] = Field(
        default_factory=list, description="Canonical URLs of corroborating evidence findings."
    )
    gap_analysis: List[str] = Field(
        default_factory=list, description="Specific identified gaps, unverified rights, or ambiguities."
    )
    recommended_action: str = Field(
        ..., description="Prescribed next step for research agent or clearance coordinator."
    )


class SubgoalTemplate(BaseModel):
    """Specification template for constructing an InvestigationSubgoal."""

    model_config = ConfigDict(frozen=True)

    suffix: str = Field(..., description="ID suffix for the subgoal.")
    subgoal_type: SubgoalType = Field(..., description="Categorical type.")
    title: str = Field(..., description="Human-readable title.")
    description_template: str = Field(..., description="Template for description.")
    required_identifiers: List[str] = Field(default_factory=list)
    target_registries: List[str] = Field(default_factory=list)
    suggested_query_terms: List[str] = Field(default_factory=list)
    priority: SubgoalPriority = Field(default=SubgoalPriority.CRITICAL)
    is_conditional: bool = Field(default=False)
    condition_trigger: Optional[str] = Field(default=None)
