"""
backend/core/policy_outbox_types.py

Data contracts, enums, and models for Transactional Outbox Policy Invalidation Cascade.
Sprint 5.3: Asynchronous Policy Dispatch, Rule Dependencies, and Golden Demo.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DispatchIntentStatus(str, Enum):
    """Lifecycle status for asynchronous policy change dispatch intents."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CascadeAction(str, Enum):
    """Action taken on a claim during policy invalidation cascade."""
    NO_ACTION_HISTORICAL_PRESERVED = "no_action_historical_preserved"
    NO_ACTION_NOT_AFFECTED = "no_action_not_affected"
    PACKAGE_INVALIDATED_AND_ROUTED = "package_invalidated_and_routed"
    PACKAGE_CREATED_FOR_REVIEW = "package_created_for_review"


class CascadeTargetFilter(BaseModel):
    """Criteria matching claims affected by specific policy rule modifications."""
    model_config = ConfigDict(extra="ignore")

    rule_code: str = Field(..., description="Governing policy rule code")
    target_right_categories: List[str] = Field(
        default_factory=list, description="Claim right categories (e.g. music, trademark)"
    )
    target_media_scopes: List[str] = Field(
        default_factory=list, description="Media scopes (e.g. promotional_trailer, theatrical)"
    )
    target_territories: List[str] = Field(
        default_factory=list, description="Territory codes (e.g. worldwide, north_america)"
    )
    requires_second_review: bool = Field(
        default=False, description="Whether this filter triggers mandatory second review"
    )


class PolicyDiffSummary(BaseModel):
    """Structured delta between two studio policy configurations."""
    model_config = ConfigDict(extra="ignore")

    from_version: Optional[str] = Field(default=None, description="Preceding policy version")
    to_version: str = Field(..., description="Target policy version")
    added_rules: List[str] = Field(default_factory=list, description="Newly introduced rule codes")
    modified_rules: List[str] = Field(default_factory=list, description="Altered rule codes")
    removed_rules: List[str] = Field(default_factory=list, description="Deprecated rule codes")
    target_filters: List[CascadeTargetFilter] = Field(
        default_factory=list, description="Calculated claim target filters"
    )


class ClaimCascadeResult(BaseModel):
    """Result of evaluating a single claim against a policy cascade."""
    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(..., description="Target atomic rights claim ID")
    production_id: str = Field(..., description="Target production ID")
    action_taken: CascadeAction = Field(..., description="Action applied to this claim")
    prior_package_id: Optional[str] = Field(default=None, description="Superseded package ID")
    new_package_id: Optional[str] = Field(default=None, description="Newly routed package ID")
    reason: str = Field(..., description="Rationale for cascade outcome")
    requires_second_review: bool = Field(
        default=False, description="True if new package mandates dual review"
    )


class DispatchExecutionReport(BaseModel):
    """Comprehensive execution telemetry emitted after processing a dispatch intent."""
    model_config = ConfigDict(extra="ignore")

    report_id: str = Field(
        default_factory=lambda: f"rep_{uuid.uuid4().hex[:12]}",
        description="Unique execution report identifier",
    )
    intent_id: str = Field(..., description="Processed dispatch intent ID")
    org_id: str = Field(..., description="Target studio organization ID")
    from_version: Optional[str] = Field(default=None, description="Preceding policy version")
    to_version: str = Field(..., description="Activated policy version")
    status: DispatchIntentStatus = Field(..., description="Final dispatch status")
    claims_scanned: int = Field(default=0, ge=0, description="Total claims inspected")
    claims_affected: int = Field(default=0, ge=0, description="Claims matching rule criteria")
    historical_preserved: int = Field(default=0, ge=0, description="Past approved packages untouched")
    packages_invalidated: int = Field(default=0, ge=0, description="In-progress packages superseded")
    packages_routed: int = Field(default=0, ge=0, description="Fresh packages routed for review")
    claim_results: List[ClaimCascadeResult] = Field(
        default_factory=list, description="Per-claim cascade outcomes"
    )
    ledger_event_id: Optional[str] = Field(default=None, description="Ledger audit event identifier")
    executed_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC execution timestamp",
    )
    execution_duration_ms: float = Field(default=0.0, ge=0.0, description="Elapsed execution time in ms")
