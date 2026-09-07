"""
backend/core/decision_package_types.py

Domain models and status enums for the immutable DecisionPackage subsystem.
Sprint 5.2: Clearance Decision Packages & Dual-Review Sign-Off.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DualReviewStatus(str, Enum):
    """Lifecycle and audit status for dual-review sign-off workflow."""

    PENDING_FIRST_REVIEW = "pending_first_review"
    FIRST_REVIEW_APPROVED = "first_review_approved"
    FINAL_APPROVED = "final_approved"
    STALE_INVALIDATED = "stale_invalidated"
    REJECTED = "rejected"


class PackageApprovalRecord(BaseModel):
    """Cryptographically anchored approval record logged by an authorized reviewer."""

    model_config = ConfigDict(extra="ignore")

    approval_id: str = Field(
        default_factory=lambda: f"appr_{uuid.uuid4().hex[:12]}",
        description="Unique approval record identifier",
    )
    package_id: str = Field(..., description="Target decision package ID")
    package_version: int = Field(default=1, ge=1, description="Target package version")
    package_digest: str = Field(
        ..., min_length=16, description="Canonical SHA-256 digest of approved package"
    )
    reviewer_id: str = Field(..., description="Authenticated counsel / reviewer ID")
    reviewer_name: str = Field(..., description="Full legal name of the reviewer")
    reviewer_role: str = Field(
        ..., description="Role of reviewer (e.g. lead_counsel, reviewer)"
    )
    is_primary_or_secondary: str = Field(
        default="primary", description="'primary' or 'secondary' review tier"
    )
    conflict_attestation: bool = Field(
        default=True, description="Attestation confirming no conflicts of interest"
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of sign-off",
    )
    ledger_event_id: str = Field(
        default="", description="Cryptographic audit ledger event identifier"
    )
    audit_event_id: Optional[str] = Field(
        default=None, description="Audit event identifier alias"
    )
    notes: Optional[str] = Field(
        default=None, description="Optional reviewer commentary or scope caveats"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_approval_record(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "stage" in data and "is_primary_or_secondary" not in data:
                data["is_primary_or_secondary"] = str(data["stage"]).lower()
            if "conflict_attested" in data and "conflict_attestation" not in data:
                data["conflict_attestation"] = bool(data["conflict_attested"])
            if "audit_event_id" in data and not data.get("ledger_event_id"):
                data["ledger_event_id"] = str(data["audit_event_id"])
            elif "ledger_event_id" in data and not data.get("audit_event_id"):
                data["audit_event_id"] = str(data["ledger_event_id"])
        return data

    @property
    def conflict_attested(self) -> bool:
        return self.conflict_attestation

    @property
    def stage(self) -> str:
        return self.is_primary_or_secondary.upper()

    @field_validator("is_primary_or_secondary")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        cleaned = str(v).strip().lower()
        if cleaned not in ("primary", "secondary"):
            raise ValueError("is_primary_or_secondary must be 'primary' or 'secondary'")
        return cleaned


class DecisionPackage(BaseModel):
    """Immutable clearance decision package binding claim, evidence, and dual approvals."""

    model_config = ConfigDict(extra="ignore")

    package_id: str = Field(
        default_factory=lambda: f"pkg_{uuid.uuid4().hex[:12]}",
        description="Unique clearance decision package identifier",
    )
    version: int = Field(
        default=1, ge=1, description="Monotonically increasing version number"
    )
    claim_id: str = Field(..., description="Bound atomic rights claim identifier")
    occurrence_id: str = Field(
        default="", description="Bound creative occurrence identifier"
    )
    cut_revision: str = Field(
        default="cut_v1", description="Source script cut revision identifier"
    )
    license_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Material licensing data"
    )
    evidence_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Material evidence data"
    )
    policy_version: Optional[str] = Field(
        default=None, description="Policy version identifier"
    )
    claim_data: Dict[str, Any] = Field(
        default_factory=dict, description="Snapshot of claim attributes"
    )
    intended_scope: Dict[str, Any] = Field(
        default_factory=dict, description="Intended commercial exploitation scope"
    )
    proposed_disposition: str = Field(
        default="CLEARED", description="Proposed disposition (e.g. CLEARED, RESTRICTED)"
    )
    rationale: str = Field(
        default="", description="Legal analysis rationale for proposed disposition"
    )
    conditions: List[str] = Field(
        default_factory=list, description="Binding operational or clearance conditions"
    )
    evidence_bundle: List[Dict[str, Any]] = Field(
        default_factory=list, description="Evidence documents, licenses, and fair use"
    )
    applicability_assessments: List[Dict[str, Any]] = Field(
        default_factory=list, description="Contract applicability assessment results"
    )
    effective_policy_version: str = Field(
        default="v1.0", description="Effective studio policy configuration version"
    )
    effective_policy_digest: str = Field(
        default="", description="SHA-256 digest of governing studio policy"
    )
    required_reviewer_roles: List[str] = Field(
        default_factory=list, description="Reviewer roles required for final approval"
    )
    canonical_digest: str = Field(
        default="", description="Deterministic SHA-256 canonical digest over package"
    )
    status: DualReviewStatus = Field(
        default=DualReviewStatus.PENDING_FIRST_REVIEW, description="Workflow status"
    )
    primary_approval: Optional[PackageApprovalRecord] = Field(
        default=None, description="Primary counsel approval record"
    )
    secondary_approval: Optional[PackageApprovalRecord] = Field(
        default=None, description="Secondary counsel approval record"
    )
    entity_names: List[str] = Field(
        default_factory=list, description="Entities involved for ethical conflict screening"
    )
    tenant_id: str = Field(
        default="tenant_default", description="Tenant isolation identifier"
    )
    production_id: str = Field(
        default="prod_default", description="Production isolation identifier"
    )
    comments: List[str] = Field(
        default_factory=list, description="Review commentary and annotations"
    )
    notes: Optional[str] = Field(default=None, description="General package notes")
    formatting_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Cosmetic and display formatting metadata"
    )
    supersedes_package_id: Optional[str] = Field(
        default=None, description="Identifier of predecessor package if superseded"
    )
    license_data: Optional[Dict[str, Any]] = Field(
        default=None, description="License agreement details"
    )
    evidence_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Evidence bundle details"
    )
    policy_version: Optional[str] = Field(
        default=None, description="Governing policy version"
    )
    claim_data: Dict[str, Any] = Field(
        default_factory=dict, description="Underlying claim data"
    )
    license_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Material licensing data"
    )
    evidence_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Material evidence data"
    )
    claim_data: Dict[str, Any] = Field(
        default_factory=dict, description="Snapshot of claim attributes"
    )
    policy_version: Optional[str] = Field(
        default=None, description="Policy version identifier"
    )
    policy_digest: Optional[str] = Field(
        default=None, description="Policy digest identifier"
    )
    claim: Optional[Any] = Field(
        default=None, description="Underlying claim domain model reference"
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_pkg(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("cut_revision"):
                data["cut_revision"] = data.get("cut_version") or "cut_v1"
            if not data.get("effective_policy_version"):
                data["effective_policy_version"] = data.get("policy_version") or "v1.0"
            if not data.get("policy_version"):
                data["policy_version"] = data.get("effective_policy_version") or "v1.0"
        return data

    @property
    def disposition(self) -> str:
        return self.proposed_disposition

    @disposition.setter
    def disposition(self, val: Any) -> None:
        self.proposed_disposition = getattr(val, "value", str(val))

    def compute_digest(self) -> str:
        """Computes deterministic canonical digest for this package."""
        from backend.core.decision_package import compute_package_canonical_digest
        return compute_package_canonical_digest(self)
