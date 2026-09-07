"""
backend/core/policy_types.py

Canonical Pydantic v2 data models and enums for studio policy inheritance.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
    """
    Studio organization baseline policy configuration.
    Defines default mandatory scopes, distribution territories, and risk gates.
    """
    model_config = ConfigDict(extra="ignore")

    policy_id: str = Field(..., description="Unique studio policy identifier")
    org_id: str = Field(..., description="Studio organization tenant boundary")
    profile_type: StudioProfileType = Field(
        default=StudioProfileType.MAJOR_THEATRICAL,
        description="Preset archetype or custom configuration",
    )
    required_media_scopes: List[LicensingScope] = Field(
        default_factory=list,
        description="Mandatory media exhibition windows",
    )
    distribution_territories: List[TerritoryScope] = Field(
        default_factory=list,
        description="Mandatory distribution territories",
    )
    mandatory_perpetual_for_theatrical: bool = Field(
        default=True,
        description="Enforce perpetual term on theatrical sync grants",
    )
    prohibit_unvetted_trademark_fair_use: bool = Field(
        default=True,
        description="Disallow trademark fair use without executed release or vetting",
    )
    risk_tolerance_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Maximum permissible composite risk score threshold",
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
    """
    Production-level policy override signed off by an authorized studio admin.
    Selectively supersedes studio baseline policy constraints for a production.
    """
    model_config = ConfigDict(extra="ignore")

    override_id: str = Field(..., description="Unique override record ID")
    production_id: str = Field(..., description="Bound production identifier")
    org_id: str = Field(..., description="Parent studio organization ID")
    admin_actor_id: str = Field(..., description="Admin principal user ID")
    admin_actor_name: str = Field(..., description="Admin principal display name")
    rationale: str = Field(..., description="Business or legal rationale for override")
    overridden_media_scopes: Optional[List[LicensingScope]] = Field(
        default=None,
        description="Optional scope override for this production",
    )
    overridden_territories: Optional[List[TerritoryScope]] = Field(
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
    ledger_event_id: Optional[str] = Field(
        default=None,
        description="Cryptographic ledger event ID linking this override",
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


class PolicyEvaluationResult(BaseModel):
    """Composite outcome of evaluating a claim against an effective studio policy."""
    model_config = ConfigDict(extra="ignore")

    is_compliant: bool = Field(..., description="True if no blocking violations exist")
    violations: List[PolicyViolation] = Field(
        default_factory=list,
        description="List of detected policy or statutory infractions",
    )
    effective_policy_id: str = Field(
        ...,
        description="Identifier of effective policy evaluated against",
    )
    requires_special_waiver: bool = Field(
        default=False,
        description="Whether an executive or legal waiver is required to proceed",
    )
