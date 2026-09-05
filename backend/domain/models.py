"""
Lienmark Domain Models
Canonical Pydantic v2 schemas for version-bound clearance change control.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


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
    REMOVED = "removed"
    NEW = "new"


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
    is_material: bool = Field(default=False, description="Flag indicating whether this delta constitutes material creative drift")

    @model_validator(mode="after")
    def sync_material_flag(self) -> "CreativeDelta":
        if self.materiality in ("high", "medium") or self.change_kind == ChangeKind.MATERIALLY_MODIFIED:
            self.is_material = True
        return self



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
    domain: Optional[str] = None
    citation: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    http_status: Optional[int] = None
    call_count: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload_hash: Optional[str] = Field(None, description="SHA-256 hash of search request payload for tamper-evident provenance")
    snippet: Optional[str] = Field(None, description="Attributable snippet or excerpt from search hit")

    @model_validator(mode="after")
    def sync_snippet_and_hashes(self) -> "PublicEvidenceSnapshot":
        if self.snippet is None and self.excerpt:
            self.snippet = self.excerpt
        elif self.excerpt is None and self.snippet:
            self.excerpt = self.snippet
        if not self.raw_payload_hash and self.payload_hash:
            self.raw_payload_hash = self.payload_hash
        elif not self.payload_hash and self.raw_payload_hash:
            self.payload_hash = self.raw_payload_hash
        return self


class ContractAgreement(BaseModel):
    agreement_id: str = Field(..., description="Unique clearance contract or license agreement identifier")
    stable_lineage_key: str = Field(..., description="Lineage key connecting this contract to a creative use/claim")
    licensor: str = Field(..., description="Party granting rights or license")
    licensee: str = Field(default="Production Co.", description="Party receiving rights")
    scope: str = Field(default="Worldwide, all media in perpetuity", description="Permitted scope and distribution rights")
    term: str = Field(default="Perpetuity", description="Duration or expiration term of agreement")
    agreement_hash: str = Field(..., description="Cryptographic hash of the contract terms and covenants")
    is_active: bool = Field(default=True, description="Whether the contract is currently active and in effect")
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    explanation: Optional[str] = Field(default=None, description="Detailed human-readable explanation naming specific changed dependencies")


class ReattestationRequest(BaseModel):
    decision_id: Optional[str] = None
    stable_lineage_key: str
    version_id: str = "v8"
    new_status: DecisionStatus  # APPROVED or REJECTED
    counsel_rationale: str
    reviewer_name: str = "Clearance Attorney"

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "stable_lineage_key" not in data and "claim_id" in data:
                data["stable_lineage_key"] = data["claim_id"]
            if "counsel_rationale" not in data and "rationale" in data:
                data["counsel_rationale"] = data["rationale"]
            if "decision_id" not in data or not data["decision_id"]:
                data["decision_id"] = f"dec_{data.get('stable_lineage_key', 'unknown')}"
            if "version_id" not in data or not data["version_id"]:
                data["version_id"] = "v8"
            if "new_status" in data and isinstance(data["new_status"], str):
                data["new_status"] = data["new_status"].lower()
        return data


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


class CarrierHeader(BaseModel):
    carrier_name: str = Field(
        default="Standard Entertainment & Media Underwriters Syndicate",
        description="Underwriting insurance carrier or syndicate entity",
    )
    policy_number: str = Field(
        default="E&O-2026.1-DEVPOST",
        description="Policy binder reference number",
    )
    broker_name: str = Field(
        default="Gallagher / Front Row Insurance Brokers",
        description="Packaging entertainment broker",
    )
    warranty_clause: str = Field(
        default="Warranted clearance schedule of exceptions; uncleared and unlisted rights are excluded from coverage.",
        description="Statutory policy warranty clause",
    )
    underwriter_status: str = Field(
        default="PENDING_REVIEW",
        description="Current status of policy underwriting review",
    )


class ExceptionsSchedule(BaseModel):
    schedule_id: str
    project_id: str
    project_name: str = "Lienmark Production Digital Twin"
    target_version_id: str
    base_version_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    policy_version: str = "E&O-2026.1-DEVPOST"
    policy_number: str = "E&O-2026.1-DEVPOST"
    carrier_header: CarrierHeader = Field(default_factory=CarrierHeader)
    production_metadata: Dict[str, Any] = Field(default_factory=dict)
    total_claims: int
    carried_forward_count: int
    reopened_count: int
    re_attested_count: int
    unresolved_exception_count: int
    items: List[ExceptionsScheduleItem] = Field(default_factory=list)
    unresolved_exceptions_schedule: List[ExceptionsScheduleItem] = Field(default_factory=list)
    unresolved_exceptions: List[ExceptionsScheduleItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_schedule_fields(self) -> "ExceptionsSchedule":
        if not self.policy_number and self.policy_version:
            self.policy_number = self.policy_version
        elif not self.policy_version and self.policy_number:
            self.policy_version = self.policy_number
        if not self.production_metadata:
            self.production_metadata = {
                "project_id": self.project_id,
                "project_name": self.project_name,
                "base_version_id": self.base_version_id,
                "target_version_id": self.target_version_id,
                "target_cut_hash": "f9e8d7c6b5a43210fedcba9876543210",
                "generated_at": self.generated_at,
            }
        exceptions_list = [
            item for item in self.items if item.v8_evaluation_state in ("exception", DecisionState.EXCEPTION.value)
        ]
        if not self.unresolved_exceptions_schedule and exceptions_list:
            self.unresolved_exceptions_schedule = exceptions_list
        if not self.unresolved_exceptions and exceptions_list:
            self.unresolved_exceptions = exceptions_list
        elif self.unresolved_exceptions_schedule and not self.unresolved_exceptions:
            self.unresolved_exceptions = self.unresolved_exceptions_schedule
        elif self.unresolved_exceptions and not self.unresolved_exceptions_schedule:
            self.unresolved_exceptions_schedule = self.unresolved_exceptions
        return self
