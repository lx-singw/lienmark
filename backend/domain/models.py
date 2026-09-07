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
from pydantic import BaseModel, Field, model_validator, field_validator


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


class CensusDisposition(str, Enum):
    APPROVED = "approved"
    CONDITIONAL = "conditional"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ApprovalOrigin(str, Enum):
    INITIAL_APPROVAL = "initial_approval"
    CARRIED_FORWARD = "carried_forward"
    RENEWED_APPROVAL = "renewed_approval"
    NONE = "none"


class WorkflowReason(str, Enum):
    NEWLY_DISCOVERED = "newly_discovered"
    CREATIVE_CHANGE = "creative_change"
    EVIDENCE_CHANGE = "evidence_change"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    WAITING_FOR_BUDGET = "waiting_for_budget"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_OFFLINE = "provider_offline"
    NORMAL_OPERATION = "normal_operation"
    REINVESTIGATION_REQUESTED = "reinvestigation_requested"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScopeMatchStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class RetentionClass(str, Enum):
    INTAKE_COPIES = "intake_copies"
    RETAINED_EVIDENCE = "retained_evidence"
    EXTRACTED_PASSAGES = "extracted_passages"
    EMBEDDINGS = "embeddings"
    AUDIT_METADATA = "audit_metadata"


class EvidenceAvailability(str, Enum):
    AVAILABLE = "available"
    SOURCE_PURGED_PER_POLICY = "source_purged_per_policy"
    RESTRICTED_ACCESS = "restricted_access"


class OrganizationTier(str, Enum):
    INDIE = "indie"
    STUDIO = "studio"
    ENTERPRISE = "enterprise"


class StorageProvider(str, Enum):
    GCS = "gcs"
    S3 = "s3"
    DROPBOX = "dropbox"
    BOX = "box"
    FRAME_IO = "frame_io"
    LOCAL_VOLUME = "local_volume"


class ConnectionStatus(str, Enum):
    ACTIVE = "active"
    SYNCING = "syncing"
    PAUSED = "paused"
    ERROR = "error"


class Organization(BaseModel):
    org_id: str = Field(..., min_length=1, description="Unique organization identifier, e.g. org_studio_alpha")
    name: str = Field(..., min_length=1, description="Legal entity name of the organization")
    tier: Union[OrganizationTier, str] = Field(default=OrganizationTier.STUDIO, description="Subscription tier: indie, studio, enterprise")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    settings: Dict[str, Any] = Field(default_factory=dict, description="Tenant configuration settings, policy profiles, limits")

    @property
    def organization_id(self) -> str:
        return self.org_id

    @field_validator("org_id")
    @classmethod
    def validate_org_id(cls, v: Any) -> str:
        if v is None:
            raise ValueError("organization_id / org_id cannot be None")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("organization_id / org_id must be a non-empty string")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def validate_organization_boundary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "organization_id" in data and data["organization_id"] is None:
                raise ValueError("organization_id cannot be None")
            if "org_id" in data and data["org_id"] is None:
                raise ValueError("org_id cannot be None")
            org_id = data.get("org_id")
            organization_id = data.get("organization_id")
            resolved = org_id or organization_id
            if resolved is None or not str(resolved).strip():
                raise ValueError("Organization requires non-nullable, non-empty organization_id / org_id")
            data["org_id"] = str(resolved).strip()
        return data


class Production(BaseModel):
    production_id: str = Field(..., min_length=1, description="Unique production identifier, e.g. prod_broadway_01")
    organization_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    title: str = Field(..., min_length=1, description="Working title of the cinematic production")
    status: str = Field(default="active", description="Production status: active, paused, archived, completed")
    budget_cap_usd: float = Field(default=5000.0, ge=0.0, description="Total authorized budget cap in USD")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def org_id(self) -> str:
        return self.organization_id

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id_non_empty(cls, v: Any) -> str:
        if v is None:
            raise ValueError("organization_id cannot be None")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("organization_id must be a non-empty string")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def validate_tenant_boundary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "organization_id" in data and data["organization_id"] is None:
                raise ValueError("organization_id cannot be None")
            if "org_id" in data and data["org_id"] is None:
                raise ValueError("organization_id cannot be None")
            organization_id = data.get("organization_id")
            org_id = data.get("org_id")
            resolved = organization_id or org_id
            if resolved is None or not str(resolved).strip():
                raise ValueError("Production requires non-nullable, non-empty organization_id")
            data["organization_id"] = str(resolved).strip()
        return data


class ProductionVersion(BaseModel):
    version_id: str = Field(..., min_length=1, description="Unique version identifier, e.g. v7, v8")
    production_id: str = Field(default="prod_broadway_01", min_length=1, description="Parent production container ID")
    organization_id: str = Field(default="org_studio_alpha", min_length=1, description="Owning tenant organization boundary")
    version_tag: str = Field(default="", description="Version tag / release descriptor, e.g. 'Scene 42 - Cut v7'")
    script_digest: Optional[str] = Field(None, description="SHA-256 cryptographic digest of script document")
    cut_hash: Optional[str] = Field(None, description="SHA-256 cryptographic digest of video/EDL cut")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Backwards compatibility fields for golden fixtures and existing tests
    project_id: Optional[str] = Field(None, description="Legacy project identifier, synced with production_id")
    label: Optional[str] = Field(None, description="Legacy human-readable label, synced with version_tag")
    content_hash: Optional[str] = Field(None, description="Legacy content hash, synced with script_digest / cut_hash")
    parent_version_id: Optional[str] = Field(None, description="Direct predecessor version identifier")
    source_type: str = Field(default="screenplay", description="Source kind: screenplay, edl, cut")

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id_non_empty(cls, v: Any) -> str:
        if v is None:
            raise ValueError("organization_id cannot be None")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("organization_id must be a non-empty string")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def validate_production_version_invariants(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Validate non-nullable organization_id
            if "organization_id" in data and data["organization_id"] is None:
                raise ValueError("ProductionVersion requires non-nullable, non-empty organization_id")
            if "org_id" in data:
                if data["org_id"] is None:
                    raise ValueError("ProductionVersion requires non-nullable, non-empty organization_id")
                data["organization_id"] = str(data["org_id"]).strip()
            elif "organization_id" in data:
                data["organization_id"] = str(data["organization_id"]).strip()

            # 2. Synchronize production_id and project_id
            prod_id = data.get("production_id")
            proj_id = data.get("project_id")
            if proj_id and not prod_id:
                data["production_id"] = str(proj_id)
            elif prod_id and not proj_id:
                data["project_id"] = str(prod_id)

            # 3. Synchronize label and version_tag
            lbl = data.get("label")
            vtag = data.get("version_tag")
            if lbl and not vtag:
                data["version_tag"] = str(lbl)
            elif vtag and not lbl:
                data["label"] = str(vtag)

            # 4. Synchronize content_hash, script_digest, cut_hash
            c_hash = data.get("content_hash")
            s_digest = data.get("script_digest")
            c_cut = data.get("cut_hash")
            source_type = data.get("source_type", "screenplay")

            if c_hash:
                if not s_digest and source_type != "video_cut":
                    data["script_digest"] = str(c_hash)
                if not c_cut and source_type == "video_cut":
                    data["cut_hash"] = str(c_hash)
            elif s_digest:
                data["content_hash"] = str(s_digest)
            elif c_cut:
                data["content_hash"] = str(c_cut)
            else:
                # Missing all payload hashes
                raise ValueError("content_hash (or script_digest / cut_hash) is required for ProductionVersion")

        return data


class DocumentRecord(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Unique document record identifier, e.g. doc_8a92")
    organization_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    production_id: str = Field(..., min_length=1, description="Bound cinematic production ID")
    filename: str = Field(..., min_length=1, description="Original ingested document file name")
    content_hash: str = Field(..., min_length=16, description="Cryptographic hash (SHA-256) of document payload")
    doc_type: str = Field(default="screenplay", description="Document type: screenplay, edl, cut, license, agreement, cue_sheet")
    uploaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 UTC upload timestamp")

    @property
    def org_id(self) -> str:
        return self.organization_id

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id_non_empty(cls, v: Any) -> str:
        if v is None:
            raise ValueError("organization_id cannot be None")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("organization_id must be a non-empty string")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def validate_tenant_boundary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "organization_id" in data and data["organization_id"] is None:
                raise ValueError("organization_id cannot be None")
            if "org_id" in data and data["org_id"] is None:
                raise ValueError("organization_id cannot be None")
            organization_id = data.get("organization_id")
            org_id = data.get("org_id")
            resolved = organization_id or org_id
            if resolved is None or not str(resolved).strip():
                raise ValueError("DocumentRecord requires non-nullable, non-empty organization_id")
            data["organization_id"] = str(resolved).strip()
        return data


class RunStatus(str, Enum):
    QUEUED = "queued"
    INVESTIGATING = "investigating"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    WAITING_FOR_BUDGET = "waiting_for_budget"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"

    # Legacy sub-phase states preserved for backwards compatibility
    INITIALIZING = "initializing"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"


class InvestigationRun(BaseModel):
    run_id: str = Field(..., min_length=1, description="Unique investigation run ID, e.g. run_2026_09_v8_001")
    organization_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    production_id: str = Field(..., min_length=1, description="Bound cinematic production ID")
    base_version_id: str = Field(..., min_length=1, description="Baseline production revision ID (e.g. v7)")
    target_version_id: str = Field(..., min_length=1, description="Target cut revision ID (e.g. v8)")
    status: RunStatus = Field(default=RunStatus.QUEUED, description="Lifecycle status of the investigation run")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    budget_spent_usd: float = Field(default=0.0, ge=0.0, description="Cumulative compute & API expenditure in USD")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary run telemetry, goals, execution steps, and audit log")

    @property
    def org_id(self) -> str:
        return self.organization_id

    @field_validator("organization_id")
    @classmethod
    def validate_organization_id_non_empty(cls, v: Any) -> str:
        if v is None:
            raise ValueError("organization_id cannot be None")
        if not isinstance(v, str) or not v.strip():
            raise ValueError("organization_id must be a non-empty string")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def validate_tenant_boundary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "organization_id" in data and data["organization_id"] is None:
                raise ValueError("organization_id cannot be None")
            if "org_id" in data and data["org_id"] is None:
                raise ValueError("organization_id cannot be None")
            organization_id = data.get("organization_id")
            org_id = data.get("org_id")
            resolved = organization_id or org_id
            if resolved is None or not str(resolved).strip():
                raise ValueError("InvestigationRun requires non-nullable, non-empty organization_id")
            data["organization_id"] = str(resolved).strip()
        return data


class ScopeStatus(str, Enum):
    UNKNOWN = "unknown"
    PARTIALLY_SPECIFIED = "partially_specified"
    FULLY_SPECIFIED = "fully_specified"
    UNLICENSED_EXPOSURE = "unlicensed_exposure"


class StorageProvider(str, Enum):
    GCS = "gcs"
    DROPBOX = "dropbox"
    GOOGLE_DRIVE = "google_drive"
    S3 = "s3"


class ConnectionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    REVOKED = "revoked"


class StorageConnection(BaseModel):
    connection_id: str = Field(..., description="Unique connection ID, e.g. conn_gcs_broadway_01")
    org_id: str = Field(default="org_studio_alpha", description="Owning organization boundary")
    production_id: str = Field(default="prod_broadway_01", description="Bound production container ID")
    provider: StorageProvider = Field(default=StorageProvider.GCS)
    bucket_or_vault_uri: str = Field(..., description="Bucket or folder URI, e.g. gs://lienmark-vault-prod/cuts/")
    watch_prefix: str = Field(default="", description="Optional directory prefix to filter ingested documents")
    discovery_cursor: Optional[str] = Field(None, description="Opaque directory scanning cursor for pagination across large object listings")
    checkpoint_token: Optional[str] = Field(None, description="High-watermark pagination/delta token from object storage API")
    last_sync_timestamp: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of last completed poll or webhook sync")
    sync_interval_seconds: int = Field(default=60, ge=10, le=3600)
    status: ConnectionStatus = Field(default=ConnectionStatus.ACTIVE)
    secret_manager_credential_ref: Optional[str] = Field(None, description="Google Secret Manager URI to service account or OAuth credentials")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvestigationGoal(BaseModel):
    goal_id: str = Field(..., description="Unique goal ID, e.g. goal_poster_loc_pd")
    stable_lineage_key: str = Field(..., description="Target claim lineage key")
    objective: str = Field(..., description="Targeted legal research goal e.g. 'Verify 1946 LOC renewal expiration'")
    priority: str = Field(default="high", description="critical, high, medium, low")
    status: str = Field(default="pending", description="pending, in_progress, completed, failed, budget_halted")


class ExecutedStep(BaseModel):
    step_id: str = Field(..., description="Unique step execution ID")
    step_name: str = Field(..., description="Canonical step name e.g. parallel_search_evidence")
    tool_name: str = Field(..., description="ADK tool invoked")
    input_summary: str = Field(..., description="Sanitized non-identifying query or parameter summary")
    status: str = Field(default="success", description="success, failed, timed_out, circuit_opened")
    duration_ms: float = Field(default=0.0)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolExecutionResult(BaseModel):
    result_id: str = Field(..., description="Unique result ID")
    step_id: str = Field(..., description="Corresponding step_id")
    tool_name: str = Field(...)
    raw_payload_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash of tool response")
    execution_status: str = Field(default="completed")
    latency_ms: float = Field(default=0.0)
    dollar_cost: float = Field(default=0.0)
    tokens_consumed: int = Field(default=0)
    result_summary: str = Field(..., description="Condensed result summary e.g. 'LOC Catalog record B-1946-8821: Expired'")
    stance: Optional[EvidenceStance] = None


class InvestigationPlan(BaseModel):
    plan_id: str = Field(..., description="Unique investigation plan ID, e.g. plan_v8_drift_eval")
    run_id: str = Field(..., description="Owning Run ID")
    target_version_id: str = Field(..., description="Target script revision ID, e.g. v8")
    status: str = Field(default="planning", description="planning, executing, paused_clarification, completed, budget_exhausted")
    goals: List[InvestigationGoal] = Field(default_factory=list)
    executed_steps: List[ExecutedStep] = Field(default_factory=list)
    tool_results: List[ToolExecutionResult] = Field(default_factory=list)
    allocated_dollar_budget: float = Field(default=50.0, ge=0.0)
    remaining_dollar_budget: float = Field(default=50.0, ge=0.0)
    allocated_token_budget: int = Field(default=100000, ge=0)
    remaining_token_budget: int = Field(default=100000, ge=0)
    allocated_call_budget: int = Field(default=15, ge=0)
    remaining_call_budget: int = Field(default=15, ge=0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Run(BaseModel):
    run_id: str = Field(..., description="Unique workflow run ID, e.g. run_2026_09_v8_001")
    production_id: str = Field(default="prod_broadway_01", description="Bound production ID")
    org_id: str = Field(default="org_studio_alpha", description="Owning organization boundary")
    source_revision_id: str = Field(default="v7", description="Baseline script revision ID, e.g. v7")
    target_revision_id: str = Field(default="v8", description="Target script revision ID, e.g. v8")
    content_digest: str = Field(default="0" * 64, description="SHA-256 digest of ingested document payload")
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}", description="Bound Google ADK Session ID backed by durable FirestoreSessionService")
    status: RunStatus = Field(default=RunStatus.INITIALIZING)
    trigger_source: str = Field(default="storage_event", description="storage_event, webhook, api_dispatch, manual")
    plan_id: Optional[str] = Field(None, description="Bound InvestigationPlan ID")
    claims_evaluated_count: int = Field(default=0, ge=0)
    carried_forward_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    unresolved_exceptions_count: int = Field(default=0, ge=0)
    total_dollar_spend_usd: float = Field(default=0.0, ge=0.0)
    total_tokens_consumed: int = Field(default=0, ge=0)
    parallel_api_calls_count: int = Field(default=0, ge=0)
    llm_inferences_count: int = Field(default=0, ge=0)
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class ClarificationRequest(BaseModel):
    request_id: str = Field(..., description="Unique request ID, e.g. clrf_8a92")
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}", description="Active ADK workflow run ID")
    claim_id: str = Field(..., description="Target claim instance identifier, e.g. clm_v8_poster_noir")
    revision_id: str = Field(default="v8", description="ScriptCut / ProductionVersion ID this request is strictly bound to (e.g. 'v8')")
    stable_lineage_key: str = Field(..., description="Persistent lineage key across drafts")
    scope_field_missing: Optional[str] = Field(None, description="Missing scope attribute triggering this clarification, e.g. 'intended_territory', 'licensed_media'")
    question_text: str = Field(..., description="Targeted legal clarification question")
    suggested_options: Optional[List[str]] = None
    required_document_type: Optional[str] = Field(None, description="e.g. 'Executed Master Use License'")
    assigned_role: str = Field(default="producer")
    assigned_user_id: Optional[str] = None
    status: str = Field(default="pending")
    response_text: Optional[str] = None
    attached_document_ref: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


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
    
    # -------------------------------------------------------------------------
    # 1. INTENDED PRODUCTION EXPLOITATION USE (Production Intent)
    # Must NEVER default to permissive values. None indicates UNKNOWN.
    # -------------------------------------------------------------------------
    intended_territory: Optional[List[str]] = Field(default=None, description="Territories planned for distribution (e.g. ['US', 'CA']). None indicates UNKNOWN.")
    intended_media: Optional[List[str]] = Field(default=None, description="Media channels planned (e.g. ['theatrical', 'svod']). None indicates UNKNOWN.")
    intended_duration: Optional[float] = Field(default=None, description="Planned exposure duration in seconds. None indicates UNKNOWN.")
    distribution_window: Optional[str] = Field(default=None, description="Planned distribution window. None indicates UNKNOWN.")
    intended_context: str = Field(default="feature", description="feature, trailer, promotional_clip, marketing")

    # -------------------------------------------------------------------------
    # 2. DOCUMENTED LICENSED SCOPE (Executed Legal Grants on File)
    # Must NEVER default to worldwide perpetual grants. None indicates UNKNOWN.
    # -------------------------------------------------------------------------
    licensed_territory: Optional[List[str]] = Field(default=None, description="Territories legally granted. None indicates UNKNOWN.")
    licensed_media: Optional[List[str]] = Field(default=None, description="Media scope granted. None indicates UNKNOWN.")
    licensed_term: Optional[str] = Field(default=None, description="Duration of license grant. None indicates UNKNOWN.")
    licensor_grant_confirmed: bool = Field(default=False, description="True ONLY if supported by an executed license agreement")

    # Domain-specific clearance parameters
    is_docudrama_context: bool = Field(default=False, description="First Amendment docudrama / living portrayal context")
    union_option_expires_at: Optional[str] = Field(default=None, description="Option expiry timestamp for SAG/WGA")
    drm_protected: bool = Field(default=False, description="DMCA Section 1201 anti-circumvention boundary")
    estimated_licensing_cost_min: Optional[float] = Field(default=None, description="Lower bound of rate card licensing estimate")
    estimated_licensing_cost_max: Optional[float] = Field(default=None, description="Upper bound of rate card licensing estimate")
    occurrence_id: Optional[str] = Field(default=None, description="Bound creative occurrence ID")
    asset_id: Optional[str] = Field(default=None, description="Shared asset / work identity")

    # Scope Evaluation & Clarification Dispatch Trigger
    scope_status: ScopeStatus = Field(default=ScopeStatus.UNKNOWN, description="Evaluated scope status")
    needs_clarification: bool = Field(default=False, description="Flag indicating clarification is required")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata and tracking references")

    @model_validator(mode="after")
    def evaluate_scope_fail_closed(self) -> "CreativeUse":
        # If intended scope or licensed scope are partially set or missing when required, flag clarification
        if (self.intended_territory is not None and self.intended_media is None) or \
           (self.licensed_territory is not None and self.licensed_media is None):
            self.scope_status = ScopeStatus.PARTIALLY_SPECIFIED
            self.needs_clarification = True
        elif self.intended_territory is not None and self.licensed_territory is not None:
            unlicensed_territories = set(self.intended_territory) - set(self.licensed_territory)
            if unlicensed_territories:
                self.scope_status = ScopeStatus.UNLICENSED_EXPOSURE
                self.needs_clarification = True
            else:
                self.scope_status = ScopeStatus.FULLY_SPECIFIED
        return self


Claim = CreativeUse


class SceneContext(BaseModel):
    """
    Screenplay scene boundary container for spatial-temporal clearance co-occurrence.
    """
    scene_id: str = Field(..., description="Unique scene identifier, e.g. scene_042")
    version_id: str = Field(default="v7", description="Screenplay revision version, e.g. v7, v8")
    scene_number: str = Field(default="", description="Normalized scene number, e.g. '42'")
    slugline: str = Field(..., description="Full slugline, e.g. 'INT. DETECTIVE OFFICE - NIGHT'")
    setting_type: str = Field(default="INT.", description="INT., EXT., INT/EXT.")
    location: str = Field(default="", description="e.g. 'DETECTIVE OFFICE'")
    time_of_day: str = Field(default="", description="e.g. 'NIGHT', 'DAY'")
    scene_hash: str = Field(..., description="Deterministic hash of scene heading, setting, and text")
    stable_lineage_key: str = Field(..., description="Persistent lineage key across revisions, e.g. scene_42")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScriptBeat(BaseModel):
    """
    Narrative sub-unit within a scene grouping dramatic action and dialogue.
    """
    beat_id: str = Field(..., description="Unique beat identifier, e.g. beat_042_01")
    scene_id: str = Field(..., description="Parent scene ID")
    version_id: str = Field(default="v7", description="Screenplay revision version")
    beat_index: int = Field(default=0, description="Zero-based sequence order within the scene")
    title: str = Field(default="", description="Action beat descriptor")
    action_text: str = Field(default="", description="Action / description lines in this beat")
    dialogue_snippets: List[str] = Field(default_factory=list)
    beat_hash: str = Field(..., description="SHA-256 hash of beat action and dialogue")
    stable_lineage_key: str = Field(..., description="Persistent beat lineage key, e.g. beat_42_entry")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreativeOccurrence(BaseModel):
    """
    Level 1 Accounting: Identifies what appears, where, and how in a specific revision.
    """
    occurrence_id: str = Field(..., description="Unique occurrence ID for this cut revision")
    occurrence_lineage_id: str = Field(..., description="Continuity lineage across cut revisions")
    asset_id: Optional[str] = Field(None, description="Shared asset / work identity, e.g. work_midnight_serenade")
    version_id: str = Field(..., description="Version this occurrence belongs to, e.g. v7, v8")
    scene_or_timecode: str = Field(..., description="Location in script or cut, e.g. Scene 42, 00:14:08-00:14:32")
    asset_type: str = Field(..., description="music, trademark, artwork, likeness, text, prop")
    description: str = Field(..., description="Detailed description of the use")
    duration_or_prominence: str = Field(..., description="Duration or visual prominence")
    context: str = Field(..., description="Narrative context / dialogue")
    context_hash: str = Field(..., description="Deterministic hash of context and prominence")
    source_span: Optional[str] = Field(None, description="Script span / dialogue lines")
    is_docudrama_context: bool = Field(default=False, description="First Amendment docudrama / living portrayal context")
    drm_protected: bool = Field(default=False, description="DMCA Section 1201 anti-circumvention boundary")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AtomicRightsClaim(BaseModel):
    """
    Level 2 Accounting: The schedule's accounting unit.
    One clearance requirement concerning one rights subject, one right/use category,
    one occurrence, and one intended exploitation scope.
    """
    claim_id: str = Field(..., description="Unique atomic rights claim ID")
    occurrence_id: str = Field(..., description="Parent creative occurrence ID")
    occurrence_lineage_id: str = Field(..., description="Continuity lineage ID")
    asset_id: Optional[str] = Field(None, description="Shared asset identifier")
    right_category: str = Field(..., description="composition, master_recording, copyright, trademark, publicity")
    rights_subject: str = Field(..., description="Subject entity, e.g. 'Composer / Music Publisher', 'Record Label'")
    
    # Intended exploitation scope
    intended_territory: Optional[List[str]] = Field(default=None, description="Planned territories. None = UNKNOWN.")
    intended_media: Optional[List[str]] = Field(default=None, description="Planned media channels. None = UNKNOWN.")
    intended_duration: Optional[float] = Field(default=None, description="Planned exposure duration seconds.")
    distribution_window: Optional[str] = Field(default=None, description="Theatrical, streaming, linear.")
    intended_context: str = Field(default="feature", description="feature, trailer, promotional_clip, marketing")

    # Documented licensed scope
    licensed_territory: Optional[List[str]] = Field(default=None, description="Granted territories. None = UNKNOWN.")
    licensed_media: Optional[List[str]] = Field(default=None, description="Granted media scope. None = UNKNOWN.")
    licensed_term: Optional[str] = Field(default=None, description="Granted duration. None = UNKNOWN.")
    licensor_grant_confirmed: bool = Field(default=False, description="True ONLY if executed license on file")
    union_option_expires_at: Optional[str] = Field(default=None, description="Option expiry timestamp for SAG/WGA")
    is_docudrama_context: bool = Field(default=False, description="First Amendment docudrama / living portrayal context")

    # Census Disposition & Workflow
    disposition: CensusDisposition = Field(default=CensusDisposition.UNKNOWN, description="Mutually exclusive census disposition")
    approval_origin: ApprovalOrigin = Field(default=ApprovalOrigin.NONE, description="initial, carried_forward, renewed")
    workflow_reason: WorkflowReason = Field(default=WorkflowReason.NEWLY_DISCOVERED, description="Workflow/operational reason")
    
    # Provenance links
    decision_id: Optional[str] = Field(None, description="Applied counsel decision ID")
    decision_conditions: List[str] = Field(default_factory=list, description="Conditions if CONDITIONAL")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting or contradictory evidence IDs")
    clarification_request_id: Optional[str] = Field(None, description="Active clarification request ID if waiting")
    notes: str = Field(default="")
    evidence_availability: EvidenceAvailability = Field(default=EvidenceAvailability.AVAILABLE)
    archived_recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="Archived prior findings / recommendations")
    counsel_directive: Optional[str] = Field(None, description="Active counsel directive or investigation constraint")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary claim metadata")


class InvestigationTask(BaseModel):
    """
    Level 3 Accounting: Work toward resolving a claim.
    Execution state is strictly independent of claim legal disposition.
    """
    task_id: str = Field(..., description="Unique task execution ID")
    claim_ids: List[str] = Field(default_factory=list, description="Linked atomic claims served by this task")
    task_type: str = Field(..., description="retrieve_agreement, search_public, inspect_source, clarify, disambiguate")
    status: TaskStatus = Field(default=TaskStatus.QUEUED)
    target_provider: str = Field(default="parallel", description="parallel, internal_vault, uspto, copyright_office")
    query_or_ref: str = Field(..., description="Search query or document vault URI")
    attempt_count: int = Field(default=0)
    max_attempts: int = Field(default=3)
    cost_usd: float = Field(default=0.0)
    result_payload: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None
    counsel_directive: Optional[str] = Field(None, description="Explicit counsel directive instructing the task")
    investigation_constraints: List[str] = Field(default_factory=list, description="Explicit search/investigation constraints")


class ContractGrant(BaseModel):
    """
    Defines who grants which rights, for which asset, media, territory, and permitted uses.
    """
    grant_id: str = Field(..., description="Unique grant ID")
    agreement_id: str = Field(..., description="Parent agreement ID")
    agreement_version: str = Field(default="v1")
    asset_id: str = Field(..., description="Target asset")
    grantor: str = Field(..., description="Grantor entity")
    grantee: str = Field(..., description="Grantee entity")
    permitted_media: List[str] = Field(default_factory=list)
    permitted_territories: List[str] = Field(default_factory=list)
    term_expiry: Optional[str] = Field(None)
    allows_promotional_trailers: bool = Field(default=True, description="Whether grant permits promotional trailers/clips")
    source_clause: str = Field(..., description="Exact quoted clause text")
    source_page: Optional[int] = None
    verification_status: str = Field(default="UNVERIFIED", description="VERIFIED_BY_REVIEWER, EXTRACTED_UNVERIFIED, UNKNOWN")


class ContractObligation(BaseModel):
    """
    Defines required attribution, payment, consent, delivery, or promotional restrictions.
    """
    obligation_id: str = Field(..., description="Unique obligation ID")
    agreement_id: str = Field(..., description="Parent agreement ID")
    obligation_type: str = Field(..., description="attribution, promotional_restriction, option_expiry, payment")
    restriction_text: str = Field(..., description="Exact restriction or condition text")
    source_clause: str = Field(...)
    source_page: Optional[int] = None
    deadline_or_expiry: Optional[str] = None
    fulfillment_evidence: Optional[str] = None
    is_fulfilled: bool = False


class ApplicabilityAssessment(BaseModel):
    """
    Evaluates how agreement terms relate to a particular occurrence, rights claim, and intended scope.
    """
    assessment_id: str = Field(default_factory=lambda: f"assess_{uuid.uuid4().hex[:12]}")
    claim_id: str = Field(...)
    agreement_id: str = Field(...)
    media_match: ScopeMatchStatus = Field(default=ScopeMatchStatus.UNKNOWN)
    territory_match: ScopeMatchStatus = Field(default=ScopeMatchStatus.UNKNOWN)
    term_match: ScopeMatchStatus = Field(default=ScopeMatchStatus.UNKNOWN)
    promotional_match: ScopeMatchStatus = Field(default=ScopeMatchStatus.UNKNOWN)
    overall_match: ScopeMatchStatus = Field(default=ScopeMatchStatus.UNKNOWN)
    conflicting_clauses: List[str] = Field(default_factory=list)
    unresolved_questions: List[str] = Field(default_factory=list)


class LegalHoldRecord(BaseModel):
    hold_id: str = Field(default_factory=lambda: f"hold_{uuid.uuid4().hex[:10]}")
    production_id: str
    claim_ids: List[str] = Field(default_factory=list)
    reason: str
    placed_by: str
    placed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    released_at: Optional[str] = None
    is_active: bool = True


class RetentionPolicy(BaseModel):
    policy_id: str = Field(default="policy_default_studio")
    org_id: str = Field(default="org_studio_alpha")
    retention_days_by_class: Dict[str, int] = Field(
        default_factory=lambda: {
            RetentionClass.INTAKE_COPIES.value: 90,
            RetentionClass.RETAINED_EVIDENCE.value: 365,
            RetentionClass.EXTRACTED_PASSAGES.value: 3650,
            RetentionClass.EMBEDDINGS.value: 90,
            RetentionClass.AUDIT_METADATA.value: 3650,
        }
    )


class DeletionRecord(BaseModel):
    deletion_id: str = Field(default_factory=lambda: f"del_{uuid.uuid4().hex[:10]}")
    target_uri: str = Field(default="")
    retention_class: RetentionClass = Field(default=RetentionClass.RETAINED_EVIDENCE)
    purged_at: Optional[str] = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    original_sha256: str = Field(default="")
    authorized_by_policy_id: str = Field(default="")
    availability_status: EvidenceAvailability = Field(default=EvidenceAvailability.SOURCE_PURGED_PER_POLICY)
    evidence_availability: EvidenceAvailability = Field(default=EvidenceAvailability.SOURCE_PURGED_PER_POLICY)
    status: str = Field(default="PURGED", description="PURGED, BLOCKED_BY_LEGAL_HOLD, ACTIVE_RETENTION, etc.")
    cryptographic_event_hash: Optional[str] = None
    event_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    purged_files: List[Dict[str, Any]] = Field(default_factory=list)
    blocked_by_hold_id: Optional[str] = None

    @model_validator(mode="after")
    def sync_availability(self) -> "DeletionRecord":
        if self.evidence_availability and not self.availability_status:
            self.availability_status = self.evidence_availability
        elif self.availability_status and not self.evidence_availability:
            self.evidence_availability = self.availability_status
        return self


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
            payload = {
                "objective": f"Clearance and intellectual property evidence verification for production asset '{self.stable_lineage_key}': {self.query}",
                "search_queries": [self.query],
                "mode": "fast",
                "max_chars_total": 4000,
            }
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
    policy_version_id: str = Field(default="E&O-2026.1-DEVPOST", description="Policy version ruleset applied")
    evidence_snapshot_ids: List[str] = Field(default_factory=list, description="Array of PublicEvidenceSnapshot and PrivateContractRecord IDs relied upon")
    state: DecisionState = Field(default=DecisionState.NEW, description="Decision state")
    reviewer_user_id: str = Field(default="counsel_sjenkins_001", description="User ID of reviewing counsel")
    reviewer_display_name: str = Field(default="E&O Clearance Counsel")
    reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersedes_decision_id: Optional[str] = None
    dependency_ids: List[str] = Field(default_factory=list)
    system_recommendation: Optional[str] = None
    human_confirmed: bool = True
    evidence_snapshot: Optional[PublicEvidenceSnapshot] = Field(default=None, description="Persisted public evidence snapshot relied upon")

    @property
    def claim_id(self) -> str:
        return self.use_id


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

    # Universal Census Partition for Active Rights Claims
    census_approved_count: int = 0
    census_conditional_count: int = 0
    census_needs_review_count: int = 0
    census_rejected_count: int = 0
    census_unknown_count: int = 0
    atomic_claims: List[AtomicRightsClaim] = Field(default_factory=list)

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

        # Synchronize Universal Census Partition if atomic_claims are provided
        if self.atomic_claims:
            self.census_approved_count = sum(1 for c in self.atomic_claims if c.disposition == CensusDisposition.APPROVED)
            self.census_conditional_count = sum(1 for c in self.atomic_claims if c.disposition == CensusDisposition.CONDITIONAL)
            self.census_needs_review_count = sum(1 for c in self.atomic_claims if c.disposition == CensusDisposition.NEEDS_REVIEW)
            self.census_rejected_count = sum(1 for c in self.atomic_claims if c.disposition == CensusDisposition.REJECTED)
            self.census_unknown_count = sum(1 for c in self.atomic_claims if c.disposition == CensusDisposition.UNKNOWN)

        return self

    def verify_census_integrity(self) -> bool:
        """
        Asserts the Universal Census Equation:
        N_active_claims = N_approved + N_conditional + N_needs_review + N_rejected + N_unknown
        """
        if self.atomic_claims:
            sum_census = (
                self.census_approved_count
                + self.census_conditional_count
                + self.census_needs_review_count
                + self.census_rejected_count
                + self.census_unknown_count
            )
            return len(self.atomic_claims) == sum_census
        return True


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
    REQUEST_CORRECTION = "request_correction"
    APPROVE = "approve"
    REJECT_USE = "reject_use"


class CounselDecisionResult(BaseModel):
    claim: Any
    action: ReviewAction
    disposition: CensusDisposition
    workflow_reason: WorkflowReason
    task: Optional[InvestigationTask] = None
    archived_record: Optional[Dict[str, Any]] = None
    counsel_directive: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __iter__(self):
        return iter((self.claim, self.task))


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

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, str):
            for it in self.items:
                if it.stable_lineage_key == key or it.prior_decision_id == key:
                    return True
            return False
        return key in self.items


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
    parent_event_hash: Optional[str] = Field(default="0" * 64, description="SHA-256 hash of direct parent SupersessionEvent or genesis hash")
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
            if "parent_event_hash" not in data or data.get("parent_event_hash") is None:
                data["parent_event_hash"] = "0" * 64
        return data

    @model_validator(mode="after")
    def compute_event_hash(self) -> "SupersessionEvent":
        if not self.event_hash or len(self.event_hash) != 64:
            action_val = self.action.value if hasattr(self.action, "value") else str(self.action)
            state_val = self.new_state.value if hasattr(self.new_state, "value") else str(self.new_state)
            status_val = self.new_status.value if hasattr(self.new_status, "value") else str(self.new_status)
            parent_hash = self.parent_event_hash or ("0" * 64)

            self.event_hash = self.compute_canonical_hash(
                event_id=self.event_id,
                prior_decision_id=self.prior_decision_id,
                new_decision_id=self.new_decision_id,
                target_version_id=self.target_version_id,
                stable_lineage_key=self.stable_lineage_key,
                action=action_val,
                new_state=state_val,
                new_status=status_val,
                system_recommendation=str(self.system_recommendation),
                counsel_rationale=str(self.rationale),
                timestamp=str(self.timestamp),
                parent_event_hash=parent_hash,
                reviewer=self.reviewer,
                evidence_citations=self.evidence_citations,
                changed_dependencies=self.changed_dependencies,
            )
        return self

    @staticmethod
    def compute_canonical_hash(
        event_id: str,
        prior_decision_id: str,
        new_decision_id: str = "",
        target_version_id: str = "v8",
        stable_lineage_key: str = "",
        action: str = "",
        new_state: str = "",
        new_status: str = "",
        system_recommendation: str = "REVALIDATE",
        counsel_rationale: str = "",
        timestamp: str = "",
        parent_event_hash: str = "0" * 64,
        reviewer: Optional[Union[ReviewerIdentity, Dict[str, Any], str]] = None,
        reviewer_name: Optional[str] = None,
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        changed_dependencies: Optional[List[str]] = None,
    ) -> str:
        # Canonical reviewer dict with reviewer_id, name, title, organization
        if isinstance(reviewer, ReviewerIdentity):
            canonical_reviewer = {
                "name": str(reviewer.name or ""),
                "organization": str(reviewer.organization or ""),
                "reviewer_id": str(reviewer.reviewer_id or ""),
                "title": str(reviewer.title or ""),
            }
        elif isinstance(reviewer, dict):
            canonical_reviewer = {
                "name": str(reviewer.get("name") or ""),
                "organization": str(reviewer.get("organization") or ""),
                "reviewer_id": str(reviewer.get("reviewer_id") or ""),
                "title": str(reviewer.get("title") or ""),
            }
        elif reviewer is not None:
            canonical_reviewer = {
                "name": str(getattr(reviewer, "name", reviewer) or ""),
                "organization": str(getattr(reviewer, "organization", "") or ""),
                "reviewer_id": str(getattr(reviewer, "reviewer_id", "") or ""),
                "title": str(getattr(reviewer, "title", "") or ""),
            }
        elif reviewer_name:
            canonical_reviewer = {
                "name": str(reviewer_name),
                "organization": "",
                "reviewer_id": "",
                "title": "",
            }
        else:
            canonical_reviewer = {
                "name": "",
                "organization": "",
                "reviewer_id": "",
                "title": "",
            }

        # Canonically sorted list of dicts with source_url, payload_hash, provider_call_id
        canonical_citations = sorted(
            [
                {
                    "payload_hash": str(c.get("payload_hash") or c.get("raw_payload_hash") or ""),
                    "provider_call_id": str(c.get("provider_call_id") or ""),
                    "source_url": str(c.get("source_url") or ""),
                }
                for c in (evidence_citations or [])
                if isinstance(c, dict)
            ],
            key=lambda x: (x["source_url"], x["payload_hash"], x["provider_call_id"]),
        )

        # Canonically sorted list of dependency strings
        canonical_dependencies = sorted([str(d) for d in (changed_dependencies or [])])

        eff_parent_event_hash = str(parent_event_hash or ("0" * 64))

        payload = {
            "action": str(action),
            "changed_dependencies": canonical_dependencies,
            "counsel_rationale": str(counsel_rationale),
            "event_id": str(event_id),
            "evidence_citations": canonical_citations,
            "new_decision_id": str(new_decision_id),
            "new_state": str(new_state),
            "new_status": str(new_status),
            "parent_event_hash": eff_parent_event_hash,
            "prior_decision_id": str(prior_decision_id),
            "reviewer": canonical_reviewer,
            "stable_lineage_key": str(stable_lineage_key),
            "system_recommendation": str(system_recommendation),
            "target_version_id": str(target_version_id),
            "timestamp": str(timestamp),
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
    run_id: Optional[str] = None
    session_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_action_payload(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("counsel_rationale") and data.get("rationale"):
                data["counsel_rationale"] = data["rationale"]
            elif not data.get("rationale") and data.get("counsel_rationale"):
                data["rationale"] = data["counsel_rationale"]
            if not data.get("stable_lineage_key") and (data.get("claim_id") or data.get("lineage_key")):
                data["stable_lineage_key"] = data.get("claim_id") or data.get("lineage_key")
            if "action" in data and isinstance(data["action"], str):
                data["action"] = data["action"].lower()
        return data


class UnauthorizedApprovalError(ValueError):
    """Raised when an unauthenticated approval or unauthorized auto-approval of a stale claim is attempted."""
    pass


class FailClosedSecurityViolation(RuntimeError):
    """Raised when fail-closed safety invariants are breached."""
    pass


class LegalHoldActiveError(RuntimeError):
    """Raised when an attempt to purge or delete materials is blocked by an active legal hold."""
    pass


