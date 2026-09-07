"""
backend/core/policy_types.py

Canonical Pydantic v2 data models and enums for studio policy evaluation.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RuleEvaluationStatus(str, Enum):
    """4-state policy rule evaluation lifecycle states."""
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class PolicyActionRequirement(str, Enum):
    """Actionable mitigation next-steps mandated by policy evaluation."""
    CLARIFICATION = "clarification"
    AGREEMENT_AMENDMENT = "agreement_amendment"
    COUNSEL_REVIEW = "counsel_review"
    SECOND_REVIEW = "second_review"
    AUTHORIZED_POLICY_WAIVER = "authorized_policy_waiver"


PolicyAction = PolicyActionRequirement
CLARIFICATION = PolicyActionRequirement.CLARIFICATION
COUNSEL_REVIEW = PolicyActionRequirement.COUNSEL_REVIEW


class LicensingScope(str, Enum):
    """Media licensing and distribution exhibition scopes."""
    THEATRICAL = "theatrical"
    SVOD = "svod"
    AVOD = "avod"
    LINEAR_BROADCAST = "linear_broadcast"
    IN_FLIGHT = "in_flight"
    PROMOTIONAL_TRAILER = "promotional_trailer"


class TerritoryScope(str, Enum):
    """Canonical geopolitical distribution territories."""
    WORLDWIDE = "worldwide"
    NORTH_AMERICA = "north_america"
    EMEA = "emea"
    LATAM = "latam"
    APAC = "apac"


class StudioProfileType(str, Enum):
    """Tiered studio risk and distribution profile archetypes."""
    MAJOR_THEATRICAL = "major_theatrical"
    STREAMER_EXCLUSIVE = "streamer_exclusive"
    FESTIVAL_ACQUISITION = "festival_acquisition"
    CUSTOM = "custom"


class StudioPolicyConfig(BaseModel):
    """Studio organization baseline policy configuration."""
    model_config = ConfigDict(extra="ignore")

    policy_id: str = Field(..., description="Unique studio policy identifier")
    org_id: str = Field(..., description="Studio organization tenant boundary")
    profile_type: StudioProfileType = Field(
        default=StudioProfileType.MAJOR_THEATRICAL,
        description="Preset archetype or custom configuration",
    )
    version: str = Field(default="1.0", description="Policy semantic version string")
    required_media_scopes: List[LicensingScope] = Field(
        default_factory=list, description="Mandatory media exhibition windows",
    )
    distribution_territories: List[TerritoryScope] = Field(
        default_factory=list, description="Mandatory distribution territories",
    )
    mandatory_perpetual_for_theatrical: bool = Field(
        default=True, description="Enforce perpetual term on theatrical sync grants",
    )
    prohibit_unvetted_trademark_fair_use: bool = Field(
        default=True, description="Disallow trademark fair use without executed release or vetting",
    )
    require_promotional_trailer_second_review: bool = Field(
        default=True, description="Mandate secondary counsel review for promotional trailer cues",
    )
    risk_tolerance_threshold: float = Field(
        default=0.70, ge=0.0, le=1.0, description="Maximum permissible composite risk score threshold",
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )
    updated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 last updated timestamp",
    )


class ProductionPolicyOverride(BaseModel):
    """Production-level policy override signed off by an authorized studio admin."""
    model_config = ConfigDict(extra="ignore")

    override_id: str = Field(..., description="Unique override record ID")
    production_id: str = Field(..., description="Bound production identifier")
    org_id: str = Field(..., description="Parent studio organization ID")
    admin_actor_id: str = Field(..., description="Admin principal user ID")
    admin_actor_name: str = Field(..., description="Admin principal display name")
    rationale: str = Field(..., description="Business or legal rationale for override")
    overridden_media_scopes: Optional[List[LicensingScope]] = Field(
        default=None, description="Optional scope override for this production",
    )
    overridden_territories: Optional[List[TerritoryScope]] = Field(
        default=None, description="Optional territory override for this production",
    )
    allow_trademark_fair_use: Optional[bool] = Field(
        default=None, description="Explicit waiver permitting unvetted trademark fair use",
    )
    require_promotional_trailer_second_review: Optional[bool] = Field(
        default=None, description="Override trailer second review requirement",
    )
    waiver_notes: Optional[str] = Field(
        default=None, description="Detailed legal notes or policy waiver parameters",
    )
    ledger_event_id: Optional[str] = Field(
        default=None, description="Cryptographic ledger event ID linking this override",
    )
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp",
    )


class PolicyViolation(BaseModel):
    """Defensible policy or statutory clearance breach details."""
    model_config = ConfigDict(extra="ignore")

    rule_code: str = Field(..., description="Standardized statutory or policy rule code")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, or LOW")
    message: str = Field(..., description="Human-readable defect description")
    remedy: str = Field(..., description="Actionable counsel guidance or cure")


class RuleEvaluationItem(BaseModel):
    """Individual rule evaluation outcome within composite policy gate."""
    model_config = ConfigDict(extra="ignore")

    rule_code: str = Field(..., description="Standardized policy rule code identifier")
    status: RuleEvaluationStatus = Field(..., description="Rule evaluation outcome state")
    required_actions: List[PolicyActionRequirement] = Field(
        default_factory=list, description="Actionable remediation steps mandated by this rule",
    )
    relevant_facts: Dict[str, Any] = Field(
        default_factory=dict, description="Claim attributes and policy facts evaluated",
    )
    source_clauses: List[str] = Field(
        default_factory=list, description="Source agreement or policy clauses referenced",
    )
    explanation: str = Field(..., description="Defensible rationale for evaluation outcome")
    applicability_reason: Optional[str] = Field(
        default=None, description="Reason why rule was deemed applicable or not applicable",
    )


class PolicyEvaluationResult(BaseModel):
    """Composite outcome of evaluating a claim against an effective studio policy."""
    model_config = ConfigDict(extra="ignore")

    overall_status: RuleEvaluationStatus = Field(
        ..., description="Aggregate composite evaluation status across all rules",
    )
    is_compliant: bool = Field(
        ..., description="True strictly if all applicable rules are SATISFIED, False if any NOT_SATISFIED or UNKNOWN",
    )
    rule_evaluations: List[RuleEvaluationItem] = Field(
        default_factory=list, description="Evaluations for each independent policy rule",
    )
    required_actions: List[PolicyActionRequirement] = Field(
        default_factory=list, description="Consolidated actionable next steps across all failing or unknown rules",
    )
    effective_policy_id: str = Field(..., description="Identifier of effective policy evaluated against")
    effective_policy_version: str = Field(default="1.0", description="Version string of effective policy")
    effective_policy_digest: str = Field(
        default="", description="Deterministic SHA-256 cryptographic digest of effective policy",
    )
    requires_special_waiver: bool = Field(
        default=False, description="Whether an executive or legal waiver is required to proceed",
    )
    violations: List[PolicyViolation] = Field(
        default_factory=list, description="List of detected policy infractions for backwards compatibility",
    )
    provenance: Dict[str, Any] = Field(
        default_factory=dict, description="Full provenance including policy version, SHA-256 digest, and tenant scope",
    )


def compute_policy_digest(policy: StudioPolicyConfig) -> str:
    """Computes deterministic SHA-256 digest of effective policy configuration."""
    canonical = {
        "policy_id": policy.policy_id,
        "org_id": policy.org_id,
        "profile_type": policy.profile_type.value if hasattr(policy.profile_type, "value") else str(policy.profile_type),
        "version": getattr(policy, "version", "1.0"),
        "required_media_scopes": sorted([s.value if hasattr(s, "value") else str(s) for s in policy.required_media_scopes]),
        "distribution_territories": sorted([t.value if hasattr(t, "value") else str(t) for t in policy.distribution_territories]),
        "mandatory_perpetual_for_theatrical": policy.mandatory_perpetual_for_theatrical,
        "prohibit_unvetted_trademark_fair_use": policy.prohibit_unvetted_trademark_fair_use,
        "require_promotional_trailer_second_review": getattr(policy, "require_promotional_trailer_second_review", True),
        "risk_tolerance_threshold": policy.risk_tolerance_threshold,
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
