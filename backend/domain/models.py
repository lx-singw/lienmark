"""
Lienmark Domain Models
Canonical Pydantic v2 schemas for version-bound clearance change control.
Strictly authored under Google AntiGravity for Agentic Cinema compliance.
"""

import hashlib
import json
import uuid
from urllib.parse import urlsplit
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Union
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
        elif not self.raw_payload_hash and not self.payload_hash:
            payload = {"query": self.query, "max_results": 3, "include_metadata": True}
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            self.raw_payload_hash = h
            self.payload_hash = h
        if not self.domain and self.source_url:
            netloc = urlsplit(self.source_url).netloc
            if netloc:
                self.domain = netloc
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
    disclaimer: str = Field(
        default="NON-BINDING RISK ASSESSMENT: This schedule does not constitute an insurance binder or policy. Clearance exceptions and warranties are subject to carrier underwriting review.",
        description="Statutory non-binding underwriter disclaimer",
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
    disclaimer: str = Field(
        default="NON-BINDING CLEARANCE SCHEDULE: Form E&O-2026 is an informational risk assessment schedule for errors and omissions underwriting. It does not bind insurance coverage or certify legal certainty.",
        description="Statutory non-binding and legal disclaimer",
    )
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
                "disclaimer": self.disclaimer,
            }
        elif "disclaimer" not in self.production_metadata:
            self.production_metadata["disclaimer"] = self.disclaimer
        exceptions_list = [
            item for item in self.items if item.v8_evaluation_state in ("exception", DecisionState.EXCEPTION.value)
        ]
        if not self.unresolved_exceptions_schedule and exceptions_list:
            self.unresolved_exceptions_schedule = exceptions_list
        if not self.unresolved_exceptions and exceptions_list:
            self.unresolved_exceptions = exceptions_list
        elif self.unresolved_exceptions_schedule and not self.unresolved_exceptions:
            self.unresolved_exceptions = self.unresolved_exceptions_schedule
        return self


class PlannedRevalidationRequest(BaseModel):
    request_id: str = Field(..., description="Unique revalidation request ID")
    stable_lineage_key: str = Field(..., description="Claim / asset stable lineage key")
    decision_id: str = Field(..., description="Prior counsel decision ID being evaluated")
    query: str = Field(..., description="Formulated targeted query tailored for Parallel Search API")
    reason_code: str = Field(..., description="Reason code triggering revalidation, e.g. CREATIVE_CONTEXT_ALTERED")
    asset_type: str = Field(default="unknown", description="Asset type: artwork, music, prop, etc.")
    priority: str = Field(default="high", description="Research priority: high, standard, low")
    expected_stance: Optional[EvidenceStance] = Field(None, description="Expected stance if predetermined")
    rationale: str = Field(default="", description="Causal justification for external search")
    target_use_id: Optional[str] = Field(None, description="Target version creative use ID")


class RevalidationPlan(BaseModel):
    plan_id: str = Field(..., description="Unique revalidation plan ID")
    target_version_id: str = Field(default="v8", description="Target version evaluated")
    planned_requests: List[PlannedRevalidationRequest] = Field(default_factory=list)
    skipped_lineage_keys: List[str] = Field(default_factory=list)
    total_claims_evaluated: int = Field(default=0)
    planned_count: int = Field(default=0)
    skipped_count: int = Field(default=0)
    api_call_budget_enforced: bool = Field(default=True)

    @model_validator(mode="after")
    def sync_counts(self) -> "RevalidationPlan":
        self.planned_count = len(self.planned_requests)
        self.skipped_count = len(self.skipped_lineage_keys)
        self.total_claims_evaluated = self.planned_count + self.skipped_count
        return self

    @property
    def call_reduction_percentage(self) -> float:
        if self.total_claims_evaluated == 0:
            return 0.0
        return round((self.skipped_count / self.total_claims_evaluated) * 100, 1)

    @property
    def call_count(self) -> int:
        return self.planned_count

    @property
    def revalidation_requests(self) -> List[PlannedRevalidationRequest]:
        return self.planned_requests

    @property
    def carried_forward_claims(self) -> List[str]:
        return self.skipped_lineage_keys

    def __len__(self) -> int:
        return len(self.planned_requests)

    def __iter__(self):
        return iter(self.planned_requests)

    def __getitem__(self, idx):
        return self.planned_requests[idx]


class EvidenceReconciliationResult(BaseModel):
    stable_lineage_key: str = Field(..., description="Lineage key of the reconciled claim")
    decision_id: str = Field(..., description="Decision identifier being reconciled")
    raw_stance: EvidenceStance = Field(..., description="Raw stance determined from external search")
    reconciled_stance: EvidenceStance = Field(..., description="Final reconciled stance after contract analysis")
    has_contract: bool = Field(default=False, description="Whether an active private contract exists for this claim")
    contract_shield_applied: bool = Field(default=False, description="Whether the contract protected against public catalog shift")
    contract_id: Optional[str] = Field(None, description="Associated contract agreement ID")
    decision_state: DecisionState = Field(..., description="Reconciled decision state: carried_forward, stale, exception")
    revalidation_action: str = Field(default="carry", description="Action: carry, revalidate, manual, close")
    reason_code: str = Field(..., description="Explanatory reason code")
    explanation: str = Field(..., description="Human-readable legal reasoning explaining reconciliation")
    evidence_snapshot: Optional[PublicEvidenceSnapshot] = None
    citations: List[Dict[str, str]] = Field(default_factory=list)
    is_license_voided: bool = Field(default=False, description="Whether the license is voided by unshielded contradictory evidence or revocation")
    requires_counsel_rider: bool = Field(default=False, description="Whether an underwriting exception rider is required")


class ReviewAction(str, Enum):
    RE_ATTEST = "re_attest"
    REJECT = "reject"
    EXCEPTION = "exception"


class ReviewerIdentity(BaseModel):
    reviewer_id: str = Field(
        default="counsel_sjenkins_001",
        description="Unique identifier for the reviewing attorney",
    )
    name: str = Field(
        default="Sarah Jenkins, Esq.",
        description="Full legal name of the clearance counsel",
    )
    title: str = Field(
        default="Lead Production Clearance Counsel",
        description="Professional title on the production clearance team",
    )
    organization: str = Field(
        default="Lienmark Legal Partners LLP",
        description="Fictional law firm or clearance agency",
    )
    is_fictional_demo: bool = Field(
        default=True,
        description="Immutable flag denoting demonstration / simulated legal identity",
    )
    disclaimer: str = Field(
        default="DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE",
        description="Mandatory disclaimer attached to all demo review decisions",
    )
    disclaimers: List[str] = Field(
        default_factory=lambda: ["DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE"],
        description="Demo counsel statutory disclaimers list",
    )

    @model_validator(mode="after")
    def sync_disclaimers(self) -> "ReviewerIdentity":
        if self.disclaimer and self.disclaimer not in self.disclaimers:
            self.disclaimers.append(self.disclaimer)
        return self


DemoReviewer = ReviewerIdentity


class FourDimensionalExplanation(BaseModel):
    stable_lineage_key: str = Field(..., description="Stable lineage key for the claim")
    decision_id: str = Field(..., description="Prior decision ID evaluated")
    creative_change: str = Field(..., description="Dimension 1: Creative change summary or stability")
    evidence_change: str = Field(..., description="Dimension 2: Public registry or search excerpt")
    private_fact: str = Field(..., description="Dimension 3: Private contract terms or contract absence")
    policy_reason: str = Field(..., description="Dimension 4: Statutory policy reason code and citation")
    system_recommendation: str = Field(default="REVALIDATE", description="AI system recommendation")

    @property
    def creative_change_summary(self) -> str:
        return self.creative_change

    @property
    def creative_stability(self) -> str:
        return self.creative_change

    @property
    def loc_public_domain_search_excerpt(self) -> str:
        return self.evidence_change

    @property
    def adverse_assignment_excerpt(self) -> str:
        return self.evidence_change

    @property
    def contract_absence(self) -> str:
        return self.private_fact

    @property
    def contract_terms(self) -> str:
        return self.private_fact

    @property
    def policy_reason_code(self) -> str:
        return self.policy_reason

    @property
    def statutory_policy_reason(self) -> str:
        return self.policy_reason


class ReviewQueueItem(BaseModel):
    stable_lineage_key: str = Field(..., description="Lineage key connecting this use across versions")
    asset_type: str = Field(default="unknown", description="Asset type")
    description: str = Field(default="", description="Detailed description")
    scene_or_timecode: str = Field(default="", description="Scene or timecode")
    current_state: DecisionState = Field(default=DecisionState.STALE, description="Current decision state")
    prior_decision: CounselDecision = Field(..., description="Inspectable prior counsel decision")
    creative_change_summary: str = Field(default="", description="Before vs after context, prominence, dialogue")
    evidence_change_summary: str = Field(default="", description="Provider, stance, citations, snippet")
    private_fact_summary: str = Field(default="", description="Licensor, scope, term, active status")
    statutory_policy_reason: str = Field(default="", description="Reason code, statutory basis e.g. 17 U.S.C. § 504(c), § 205(e)")
    system_recommendation: str = Field(default="REVALIDATE", description="AI system recommendation")
    available_actions: List[ReviewAction] = Field(
        default_factory=lambda: [ReviewAction.RE_ATTEST, ReviewAction.REJECT, ReviewAction.EXCEPTION],
        description="Available actions for counsel review",
    )
    # Compatibility fields
    queue_id: str = Field(default_factory=lambda: f"qitem_{uuid.uuid4().hex[:8]}")
    prior_decision_id: str = ""
    current_status: DecisionStatus = DecisionStatus.APPROVED
    explanation_4d: Optional[FourDimensionalExplanation] = None
    evidence_snapshot: Optional[PublicEvidenceSnapshot] = None
    contract: Optional[ContractAgreement] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def sync_explanation_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("queue_id"):
                data["queue_id"] = f"qitem_{data.get('stable_lineage_key', uuid.uuid4().hex[:8])}"
            if "explanation_4d" in data and data["explanation_4d"]:
                exp = data["explanation_4d"]
                if isinstance(exp, dict):
                    if not data.get("creative_change_summary"):
                        data["creative_change_summary"] = exp.get("creative_change", "")
                    if not data.get("evidence_change_summary"):
                        data["evidence_change_summary"] = exp.get("evidence_change", "")
                    if not data.get("private_fact_summary"):
                        data["private_fact_summary"] = exp.get("private_fact", "")
                    if not data.get("statutory_policy_reason"):
                        data["statutory_policy_reason"] = exp.get("policy_reason", "")
                elif hasattr(exp, "creative_change"):
                    if not data.get("creative_change_summary"):
                        data["creative_change_summary"] = getattr(exp, "creative_change", "")
                    if not data.get("evidence_change_summary"):
                        data["evidence_change_summary"] = getattr(exp, "evidence_change", "")
                    if not data.get("private_fact_summary"):
                        data["private_fact_summary"] = getattr(exp, "private_fact", "")
                    if not data.get("statutory_policy_reason"):
                        data["statutory_policy_reason"] = getattr(exp, "policy_reason", "")
        return data

    @model_validator(mode="after")
    def sync_fields_after(self) -> "ReviewQueueItem":
        if not self.prior_decision_id and self.prior_decision:
            self.prior_decision_id = self.prior_decision.decision_id
        if self.current_status is None and self.prior_decision:
            self.current_status = self.prior_decision.status
        if self.explanation_4d is None:
            self.explanation_4d = FourDimensionalExplanation(
                stable_lineage_key=self.stable_lineage_key,
                decision_id=self.prior_decision_id or (self.prior_decision.decision_id if self.prior_decision else ""),
                creative_change=self.creative_change_summary,
                evidence_change=self.evidence_change_summary,
                private_fact=self.private_fact_summary,
                policy_reason=self.statutory_policy_reason,
                system_recommendation=self.system_recommendation,
            )
        return self


class ReviewQueue(BaseModel):
    queue_id: str = Field(default_factory=lambda: f"queue_{uuid.uuid4().hex[:8]}")
    target_version_id: str = "v8"
    base_version_id: str = "v7"
    items: List[ReviewQueueItem] = Field(default_factory=list)
    total_stale_count: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="after")
    def sync_stale_count(self) -> "ReviewQueue":
        self.total_stale_count = len(self.items)
        return self

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, idx: Union[int, str]):
        if isinstance(idx, int):
            return self.items[idx]
        for it in self.items:
            if it.stable_lineage_key == idx or it.prior_decision_id == idx:
                return it
        raise KeyError(f"Item '{idx}' not found in review queue")


class SupersessionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    stable_lineage_key: str = Field(..., description="Asset lineage key")
    action: ReviewAction = Field(..., description="Review action taken: re_attest, reject, exception")
    prior_decision_id: str = Field(..., description="ID of prior decision being superseded")
    new_decision_id: str = Field(default="", description="ID of new decision created")
    prior_status: DecisionStatus = Field(default=DecisionStatus.APPROVED, description="Status prior to review")
    new_status: DecisionStatus = Field(default=DecisionStatus.APPROVED, description="Status after review")
    prior_state: DecisionState = Field(default=DecisionState.STALE, description="State prior to review")
    new_state: DecisionState = Field(default=DecisionState.RE_ATTESTED, description="State after review")
    reviewer: ReviewerIdentity = Field(default_factory=ReviewerIdentity, description="Identity of reviewing counsel")
    rationale: str = Field(default="", description="Counsel explanation")
    system_recommendation: str = Field(default="REVALIDATE", description="AI recommendation")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    changed_dependencies: List[str] = Field(default_factory=list)
    evidence_citations: List[Dict[str, str]] = Field(default_factory=list)
    event_hash: str = Field(default="", description="SHA-256 tamper-evident hash of event contents")
    # Compatibility fields
    target_version_id: str = Field(default="v8")
    parent_event_hash: Optional[str] = Field(default=None)
    prior_decision: Optional[CounselDecision] = Field(default=None)
    new_decision: Optional[CounselDecision] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def counsel_rationale(self) -> str:
        return self.rationale

    @model_validator(mode="before")
    @classmethod
    def normalize_event_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("rationale") and data.get("counsel_rationale"):
                data["rationale"] = data["counsel_rationale"]
            elif not data.get("counsel_rationale") and data.get("rationale"):
                data["counsel_rationale"] = data["rationale"]
            if not data.get("new_decision_id"):
                ver = data.get("target_version_id", "v8")
                key = data.get("stable_lineage_key", "claim")
                data["new_decision_id"] = f"dec_{ver}_{key}_{uuid.uuid4().hex[:6]}"
            if not data.get("event_id"):
                data["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
        return data

    @model_validator(mode="after")
    def compute_event_hash(self) -> "SupersessionEvent":
        if not self.event_hash or len(self.event_hash) != 64:
            action_val = self.action.value if hasattr(self.action, "value") else str(self.action)
            state_val = self.new_state.value if hasattr(self.new_state, "value") else str(self.new_state)
            status_val = self.new_status.value if hasattr(self.new_status, "value") else str(self.new_status)
            reviewer_name = self.reviewer.name if isinstance(self.reviewer, ReviewerIdentity) else getattr(self.reviewer, "name", str(self.reviewer))

            payload = {
                "action": action_val,
                "counsel_rationale": self.rationale,
                "event_id": self.event_id,
                "new_state": state_val,
                "new_status": status_val,
                "prior_decision_id": self.prior_decision_id,
                "reviewer_name": reviewer_name,
                "stable_lineage_key": self.stable_lineage_key,
                "system_recommendation": self.system_recommendation,
                "target_version_id": self.target_version_id,
                "timestamp": self.timestamp,
            }
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            self.event_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return self

    @staticmethod
    def compute_canonical_hash(
        event_id: str,
        prior_decision_id: str,
        target_version_id: str,
        stable_lineage_key: str,
        action: str,
        reviewer_name: str,
        counsel_rationale: str,
        new_state: str,
        new_status: str,
        system_recommendation: str,
        timestamp: str,
    ) -> str:
        payload = {
            "action": action,
            "counsel_rationale": counsel_rationale,
            "event_id": event_id,
            "new_state": new_state,
            "new_status": new_status,
            "prior_decision_id": prior_decision_id,
            "reviewer_name": reviewer_name,
            "stable_lineage_key": stable_lineage_key,
            "system_recommendation": system_recommendation,
            "target_version_id": target_version_id,
            "timestamp": timestamp,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class ReviewActionRequest(BaseModel):
    stable_lineage_key: Optional[str] = None
    decision_id: Optional[str] = None
    action: ReviewAction
    counsel_rationale: Optional[str] = None
    rationale: Optional[str] = None
    reviewer: Optional[Union[ReviewerIdentity, Dict[str, Any]]] = None
    reviewer_name: Optional[str] = None
    version_id: str = "v8"

    @model_validator(mode="before")
    @classmethod
    def normalize_action_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("counsel_rationale") and data.get("rationale"):
                data["counsel_rationale"] = data["rationale"]
            elif not data.get("rationale") and data.get("counsel_rationale"):
                data["rationale"] = data["counsel_rationale"]
            if not data.get("stable_lineage_key") and data.get("claim_id"):
                data["stable_lineage_key"] = data["claim_id"]
            if "action" in data and isinstance(data["action"], str):
                data["action"] = data["action"].lower()
        return data


class UnauthorizedApprovalError(ValueError):
    """Raised when an unauthenticated approval or unauthorized auto-approval of a stale claim is attempted."""
    pass


class FailClosedSecurityViolation(RuntimeError):
    """Raised when fail-closed safety invariants are breached."""
    pass


