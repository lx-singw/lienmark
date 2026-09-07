"""
backend/api/routes/policy_schemas.py

Pydantic v2 schemas for Studio Policy Inheritance & Production Overrides.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.policy_types import (
    LicensingScope,
    PolicyEvaluationResult,
    PolicyViolation,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)


class StudioPolicyRequest(BaseModel):
    """Payload for creating or updating studio policy configuration templates."""

    profile_type: Optional[str] = Field(
        default="major_theatrical",
        description="Preset archetype: 'major_theatrical', 'streamer_exclusive', 'festival_acquisition', 'custom'",
    )
    required_media_scopes: Optional[List[str]] = Field(
        default=None,
        description="Mandatory media exhibition windows (theatrical, svod, avod, linear_broadcast, in_flight, promotional_trailer)",
    )
    distribution_territories: Optional[List[str]] = Field(
        default=None,
        description="Mandatory distribution territories (worldwide, north_america, emea, latam, apac)",
    )
    mandatory_perpetual_for_theatrical: Optional[bool] = Field(
        default=True,
        description="Enforce perpetual term on theatrical sync grants",
    )
    prohibit_unvetted_trademark_fair_use: Optional[bool] = Field(
        default=True,
        description="Disallow trademark fair use without executed release or vetting",
    )
    risk_tolerance_threshold: Optional[float] = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Maximum permissible composite risk score threshold",
    )

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: Any) -> Any:
        """Harmonizes field aliases like profile_name and required_territories."""
        if not isinstance(data, dict):
            return data
        if "profile_name" in data and "profile_type" not in data:
            data["profile_type"] = data["profile_name"]
        if "required_territories" in data and "distribution_territories" not in data:
            data["distribution_territories"] = data["required_territories"]
        if "allow_trademark_fair_use" in data and "prohibit_unvetted_trademark_fair_use" not in data:
            data["prohibit_unvetted_trademark_fair_use"] = not data["allow_trademark_fair_use"]
        return data


class StudioPolicyResponse(BaseModel):
    """Studio policy template response envelope returning StudioPolicyConfig."""

    policy: StudioPolicyConfig = Field(..., description="Active studio baseline policy configuration")
    policy_id: str = Field(..., description="Unique policy identifier")
    org_id: str = Field(..., description="Studio organization tenant identifier")
    profile_type: str = Field(default="major_theatrical", description="Preset archetype or custom configuration")
    required_media_scopes: List[str] = Field(default_factory=list, description="Mandatory media exhibition windows")
    distribution_territories: List[str] = Field(default_factory=list, description="Mandatory distribution territories")
    mandatory_perpetual_for_theatrical: bool = Field(default=True, description="Enforce perpetual term on theatrical sync grants")
    prohibit_unvetted_trademark_fair_use: bool = Field(default=True, description="Disallow trademark fair use without vetting")
    risk_tolerance_threshold: float = Field(default=0.70, description="Risk tolerance threshold")
    created_at_utc: str = Field(default="", description="ISO 8601 creation timestamp")
    updated_at_utc: str = Field(default="", description="ISO 8601 update timestamp")

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def sync_policy_fields(cls, data: Any) -> Any:
        """Populates top-level response fields from nested policy object."""
        if isinstance(data, dict) and "policy" in data:
            pol = data["policy"]
            p_dict = pol.model_dump() if hasattr(pol, "model_dump") else (pol if isinstance(pol, dict) else {})
            data.setdefault("policy_id", p_dict.get("policy_id", ""))
            data.setdefault("org_id", p_dict.get("org_id", ""))
            pt = p_dict.get("profile_type", "major_theatrical")
            pt_val = pt.value if hasattr(pt, "value") else (str(pt).split(".")[-1].lower() if "StudioProfileType" in str(pt) else str(pt))
            data.setdefault("profile_type", pt_val)
            data.setdefault("required_media_scopes", [str(s.value if hasattr(s, "value") else s) for s in p_dict.get("required_media_scopes", [])])
            data.setdefault("distribution_territories", [str(t.value if hasattr(t, "value") else t) for t in p_dict.get("distribution_territories", [])])
            data.setdefault("mandatory_perpetual_for_theatrical", p_dict.get("mandatory_perpetual_for_theatrical", True))
            data.setdefault("prohibit_unvetted_trademark_fair_use", p_dict.get("prohibit_unvetted_trademark_fair_use", True))
            data.setdefault("risk_tolerance_threshold", p_dict.get("risk_tolerance_threshold", 0.70))
            data.setdefault("created_at_utc", p_dict.get("created_at_utc", ""))
            data.setdefault("updated_at_utc", p_dict.get("updated_at_utc", ""))
        return data


class ProductionOverrideRequest(BaseModel):
    """Payload for submitting production policy overrides signed off by Admin."""

    admin_actor_id: str = Field(..., min_length=1, description="Admin principal user identifier")
    admin_actor_name: str = Field(..., min_length=1, description="Admin principal display name")
    rationale: str = Field(..., min_length=1, description="Business or legal rationale for policy override")
    actor_role: str = Field(..., min_length=1, description="Role of principal authorizing the override")
    overridden_media_scopes: Optional[List[str]] = Field(
        default=None,
        description="Optional scope override for this production",
    )
    overridden_territories: Optional[List[str]] = Field(
        default=None,
        description="Optional territory override for this production",
    )
    allow_trademark_fair_use: Optional[bool] = Field(
        default=None,
        description="Explicit waiver permitting unvetted trademark fair use",
    )
    waiver_notes: Optional[str] = Field(
        default=None,
        description="Detailed legal notes or policy waiver parameters",
    )

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ProductionOverrideResponse(BaseModel):
    """Response returned upon successful production policy override application."""

    effective_policy: StudioPolicyConfig = Field(..., description="Resolved effective policy configuration post-override")
    audit_event_id: str = Field(..., description="Cryptographic SHA-256 chained audit ledger event identifier")
    override_id: str = Field(..., description="Unique override record identifier")
    production_id: str = Field(..., description="Target production identifier")
    org_id: str = Field(..., description="Studio organization tenant identifier")
    status: str = Field(default="applied", description="Override processing status")
    message: str = Field(
        default="Production policy override applied and recorded to ledger.",
        description="Outcome confirmation message",
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of override application",
    )

    model_config = ConfigDict(extra="ignore")


class PolicyEvaluationResponse(BaseModel):
    """Outcome envelope returning PolicyEvaluationResult for a claim."""

    result: PolicyEvaluationResult = Field(..., description="Underlying policy evaluation outcome")
    is_compliant: bool = Field(..., description="True if no blocking policy violations exist")
    violations: List[PolicyViolation] = Field(default_factory=list, description="List of detected policy infractions")
    effective_policy_id: str = Field(..., description="Identifier of effective policy evaluated against")
    requires_special_waiver: bool = Field(default=False, description="True if an executive or legal waiver is required")
    claim_id: Optional[str] = Field(default=None, description="Evaluated claim identifier")

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def sync_result_fields(cls, data: Any) -> Any:
        """Synchronizes top-level evaluation fields from PolicyEvaluationResult."""
        if isinstance(data, dict) and "result" in data:
            res = data["result"]
            r_dict = res.model_dump() if hasattr(res, "model_dump") else (res if isinstance(res, dict) else {})
            data.setdefault("is_compliant", r_dict.get("is_compliant", True))
            data.setdefault("violations", r_dict.get("violations", []))
            data.setdefault("effective_policy_id", r_dict.get("effective_policy_id", ""))
            data.setdefault("requires_special_waiver", r_dict.get("requires_special_waiver", False))
        return data


class ClaimEvaluationRequest(BaseModel):
    """Optional claim metadata for policy compliance evaluation."""

    asset_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    term: Optional[str] = None
    territory: Optional[str] = None
    is_perpetual: Optional[bool] = None
    fair_use_claimed: Optional[bool] = None
    has_executed_release: Optional[bool] = None
    is_nominative_exemption: Optional[bool] = None
    excluded_territories: Optional[List[str]] = None
    territories: Optional[List[str]] = None

    model_config = ConfigDict(extra="allow")

