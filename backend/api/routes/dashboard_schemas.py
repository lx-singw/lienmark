"""
backend/api/routes/dashboard_schemas.py

Pydantic v2 domain schemas for Command Center Dashboard (Inbox & Velocity).
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BlockerSeverity(str, Enum):
    """Urgency tiers for triage routing."""
    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_MEDIUM = "P2_MEDIUM"
    P3_STANDARD = "P3_STANDARD"


class InboxItemCategory(str, Enum):
    """Categorization for actionable clearance items."""
    REOPENED_CREATIVE_DRIFT = "reopened_creative_drift"
    ADVERSE_EXTERNAL_EVIDENCE = "adverse_external_evidence"
    CLARIFICATION_PENDING = "clarification_pending"
    BUDGET_ALERT = "budget_alert"
    UNASSIGNED_INTAKE = "unassigned_intake"
    DELIVERY_DEADLINE_BREACH = "delivery_deadline_breach"


class InboxItem(BaseModel):
    """Individual actionable clearance blocker or task in the Command Center."""
    inbox_id: str = Field(..., description="Unique inbox item ID e.g. inb_abc123")
    production_id: str = Field(..., description="Bound production container ID")
    production_title: str = Field(..., description="Human-readable title of production")
    stable_lineage_key: str = Field(..., description="Lineage identifier of asset or claim")
    asset_name: str = Field(..., description="Asset identifier or title")
    asset_type: str = Field(
        ...,
        description="script_dialogue, music_sync, prop_brand, archival_footage, talent_likeness",
    )
    severity: BlockerSeverity = Field(..., description="Assigned urgency tier")
    category: InboxItemCategory = Field(..., description="Blocker root cause category")
    summary_headline: str = Field(..., description="Brief summary headline for triage list")
    detailed_context: str = Field(..., description="Full contextual description and legal rationale")
    assigned_to_user_id: Optional[str] = Field(None, description="Assigned legal team member ID")
    assigned_to_name: Optional[str] = Field(None, description="Assigned legal team member name")
    created_at: str = Field(..., description="ISO 8601 UTC creation timestamp")
    age_hours: float = Field(default=0.0, ge=0.0, description="Aging in hours since surfacing")
    delivery_deadline: Optional[str] = Field(None, description="ISO 8601 UTC delivery deadline")
    time_to_deadline_hours: Optional[float] = Field(None, description="Hours remaining to deadline")
    target_version_id: Optional[str] = Field(None, description="Active script revision version ID")
    baseline_version_id: Optional[str] = Field(None, description="Prior locked baseline version ID")
    requires_counsel_signoff: bool = Field(default=True, description="Whether counsel action is required")
    active_investigation_run_id: Optional[str] = Field(None, description="Associated investigation run ID")
    quick_action: str = Field(
        ...,
        description="review_claim | answer_clarification | approve_budget | assign_intake",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom context and IDs")


class InboxSummaryMetrics(BaseModel):
    """Aggregated operational triage metrics for zero-inbox tracking."""
    total_active_blockers: int = Field(default=0, ge=0)
    p0_count: int = Field(default=0, ge=0)
    p1_count: int = Field(default=0, ge=0)
    p2_count: int = Field(default=0, ge=0)
    p3_count: int = Field(default=0, ge=0)
    waiting_clarifications_count: int = Field(default=0, ge=0)
    budget_alerts_count: int = Field(default=0, ge=0)
    avg_resolution_time_hours: float = Field(default=0.0, ge=0.0)


class InboxResponse(BaseModel):
    """Paginated response contract for the Command Center Inbox."""
    tenant_id: str = Field(..., description="Verified organization / tenant boundary")
    organization_id: str = Field(..., description="Canonical organization ID")
    items: List[InboxItem] = Field(default_factory=list, description="Actionable inbox items")
    summary: InboxSummaryMetrics = Field(..., description="Aggregated metric summary")
    total_count: int = Field(default=0, ge=0, description="Total matching items count")
    timestamp: str = Field(..., description="ISO 8601 UTC query execution timestamp")


class ResolutionTimeMetric(BaseModel):
    """Statistical clearance resolution latency across counsel decisions."""
    median_hours: float = Field(default=0.0, ge=0.0)
    p90_hours: float = Field(default=0.0, ge=0.0)
    min_hours: float = Field(default=0.0, ge=0.0)
    max_hours: float = Field(default=0.0, ge=0.0)
    sample_count: int = Field(default=0, ge=0)


class StaleClaimAgingMetric(BaseModel):
    """Aging distribution of unresolved stale claims."""
    avg_stale_hours: float = Field(default=0.0, ge=0.0)
    max_stale_hours: float = Field(default=0.0, ge=0.0)
    stale_count: int = Field(default=0, ge=0)
    distribution_under_24h: int = Field(default=0, ge=0)
    distribution_24_to_72h: int = Field(default=0, ge=0)
    distribution_over_72h: int = Field(default=0, ge=0)


class BlockerVelocityMetric(BaseModel):
    """24-hour burn rate and resolution velocity."""
    new_blockers_24h: int = Field(default=0, ge=0)
    resolved_blockers_24h: int = Field(default=0, ge=0)
    net_burn_rate: float = Field(default=0.0, description="resolved - new in past 24h")
    resolution_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class ProductionVelocityStats(BaseModel):
    """Comprehensive clearance velocity metrics for a production container."""
    production_id: str = Field(..., description="Target production identifier")
    production_title: str = Field(..., description="Human-readable title")
    resolution_time: ResolutionTimeMetric = Field(..., description="Historical sign-off latency")
    stale_aging: StaleClaimAgingMetric = Field(..., description="Unresolved stale claim aging")
    blocker_velocity: BlockerVelocityMetric = Field(..., description="Recent 24h burn rate")
    has_active_high_severity_blockers: bool = Field(
        default=False,
        description="True if unresolved P0 or P1 blockers exist (triggers UI safeguard)",
    )
    unresolved_blocker_count: int = Field(default=0, ge=0)


class VelocityResponse(BaseModel):
    """Response contract for the Clearance Velocity & Risk Regression endpoint."""
    tenant_id: str = Field(..., description="Verified organization / tenant boundary")
    organization_id: str = Field(..., description="Canonical organization ID")
    aggregate: ProductionVelocityStats = Field(..., description="Tenant-wide aggregate velocity")
    by_production: List[ProductionVelocityStats] = Field(
        default_factory=list,
        description="Per-production velocity breakdown",
    )
    window_days: int = Field(default=30, ge=1, le=365)
    calculated_at: str = Field(..., description="ISO 8601 UTC calculation timestamp")
