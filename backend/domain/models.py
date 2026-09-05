"""
Lienmark Domain Models
Canonical Pydantic v2 schemas for version-bound clearance change control.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChangeKind(str, Enum):
    ADDED = "added"
    MATERIALLY_MODIFIED = "materially_modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    UNCERTAIN = "uncertain"


class DecisionState(str, Enum):
    CARRIED_FORWARD = "carried_forward"
    STALE = "stale"
    RE_ATTESTED = "re_attested"
    EXCEPTION = "exception"


class DecisionStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITION = "approved_with_condition"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class EvidenceStance(str, Enum):
    SUPPORTING = "supporting"
    INFORMATIONAL = "informational"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT = "insufficient"


class ProductionVersion(BaseModel):
    version_id: str = Field(..., description="Unique version identifier, e.g. v7, v8")
    project_id: str = Field(..., description="Project / Production ID")
    label: str = Field(..., description="Human-readable label, e.g. 'Scene 42 - Cut v7'")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = Field(..., description="SHA-256 hash of script or cut contents")
    parent_version_id: Optional[str] = Field(None, description="Direct predecessor version")
    source_type: str = Field(default="screenplay", description="source kind: screenplay, edl, cut")


class CreativeUse(BaseModel):
    use_id: str = Field(..., description="Unique creative use instance ID")
    version_id: str = Field(..., description="Version this use instance belongs to")
    scene_or_timecode: str = Field(..., description="Location in script or cut, e.g. Scene 42")
    asset_type: str = Field(..., description="music, trademark, artwork, likeness, text, prop")
    description: str = Field(..., description="Detailed description of the use")
    duration_or_prominence: str = Field(..., description="Duration or visual prominence")
    context: str = Field(..., description="Narrative context / dialogue")
    stable_lineage_key: str = Field(..., description="Lineage key connecting this use across versions")
    source_span: Optional[str] = Field(None, description="Script span / dialogue lines")
    context_hash: str = Field(..., description="Deterministic hash of context and prominence")


class CreativeDelta(BaseModel):
    delta_id: str = Field(..., description="Delta identifier")
    before_use_id: Optional[str] = None
    after_use_id: Optional[str] = None
    stable_lineage_key: str
    change_kind: ChangeKind
    materiality: str = Field(default="none", description="none, low, high")
    match_confidence: float = Field(default=1.0)
    changed_fields: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)


class PublicEvidenceSnapshot(BaseModel):
    snapshot_id: str
    use_id: str
    stable_lineage_key: str
    query: str
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provider: str = Field(default="Parallel")
    source_url: str
    source_title: str
    excerpt: str
    publisher: Optional[str] = None
    stance: EvidenceStance = EvidenceStance.SUPPORTING
    cached_or_live: str = Field(default="live")
    provider_call_id: Optional[str] = None
    retrieval_latency_ms: Optional[float] = None


class CounselDecision(BaseModel):
    decision_id: str
    use_id: str
    stable_lineage_key: str
    applicable_version_id: str
    status: DecisionStatus
    rationale: str
    reviewer_display_name: str = Field(default="E&O Clearance Counsel")
    reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersedes_decision_id: Optional[str] = None
    dependency_ids: List[str] = Field(default_factory=list)
    system_recommendation: Optional[str] = None
    human_confirmed: bool = True


class DecisionValidity(BaseModel):
    decision_id: str
    evaluated_for_version_id: str
    stable_lineage_key: str
    state: DecisionState
    reason_code: str
    changed_dependency_ids: List[str] = Field(default_factory=list)
    revalidation_action: str = Field(default="carry")  # carry, revalidate, close, manual
    evidence_snapshot: Optional[PublicEvidenceSnapshot] = None
    creative_delta: Optional[CreativeDelta] = None


class ReattestationRequest(BaseModel):
    decision_id: str
    stable_lineage_key: str
    version_id: str
    new_status: DecisionStatus  # APPROVED or REJECTED
    counsel_rationale: str
    reviewer_name: str = "Clearance Attorney"


class ExceptionsScheduleItem(BaseModel):
    stable_lineage_key: str
    asset_type: str
    description: str
    scene_or_timecode: str
    v7_decision_status: str
    v8_evaluation_state: str  # carried_forward, re_attested, exception
    invalidation_reason: Optional[str] = None
    counsel_action: str
    evidence_citations: List[Dict[str, str]] = Field(default_factory=list)


class ExceptionsSchedule(BaseModel):
    schedule_id: str
    project_id: str
    project_name: str = "Lienmark Production Digital Twin"
    target_version_id: str
    base_version_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    policy_version: str = "E&O-2026.1-DEVPOST"
    total_claims: int
    carried_forward_count: int
    reopened_count: int
    re_attested_count: int
    unresolved_exception_count: int
    items: List[ExceptionsScheduleItem] = Field(default_factory=list)
