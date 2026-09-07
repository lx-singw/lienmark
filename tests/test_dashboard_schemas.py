"""
tests/test_dashboard_schemas.py

Verification tests for Command Center Dashboard Pydantic v2 schemas.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from backend.api.routes.dashboard_schemas import (
    BlockerSeverity,
    BlockerVelocityMetric,
    InboxItem,
    InboxItemCategory,
    InboxResponse,
    InboxSummaryMetrics,
    ProductionVelocityStats,
    ResolutionTimeMetric,
    StaleClaimAgingMetric,
    VelocityResponse,
)


def test_blocker_severity_enums():
    """Validates severity levels and enum serialization."""
    assert BlockerSeverity.P0_CRITICAL.value == "P0_CRITICAL"
    assert BlockerSeverity.P1_HIGH.value == "P1_HIGH"
    assert BlockerSeverity.P2_MEDIUM.value == "P2_MEDIUM"
    assert BlockerSeverity.P3_STANDARD.value == "P3_STANDARD"


def test_inbox_item_category_enums():
    """Validates inbox category enumeration values."""
    categories = {
        InboxItemCategory.REOPENED_CREATIVE_DRIFT,
        InboxItemCategory.ADVERSE_EXTERNAL_EVIDENCE,
        InboxItemCategory.CLARIFICATION_PENDING,
        InboxItemCategory.BUDGET_ALERT,
        InboxItemCategory.UNASSIGNED_INTAKE,
        InboxItemCategory.DELIVERY_DEADLINE_BREACH,
    }
    assert len(categories) == 6


def test_inbox_item_schema_serialization():
    """Validates required fields and deep copy / dump on InboxItem."""
    item = InboxItem(
        inbox_id="inb_test_001",
        production_id="prod_shadows_01",
        production_title="Shadows Over Broadway",
        stable_lineage_key="music_cue_midnight_serenade",
        asset_name="Midnight Serenade",
        asset_type="music_sync",
        severity=BlockerSeverity.P0_CRITICAL,
        category=InboxItemCategory.ADVERSE_EXTERNAL_EVIDENCE,
        summary_headline="Contradictory copyright registry finding",
        detailed_context="Adverse assignment to Vanguard Media Worldwide.",
        created_at="2026-09-07T12:00:00Z",
        age_hours=4.5,
        quick_action="review_claim",
    )
    dumped = item.model_dump()
    assert dumped["inbox_id"] == "inb_test_001"
    assert dumped["severity"] == "P0_CRITICAL"
    assert dumped["requires_counsel_signoff"] is True


def test_inbox_response_serialization():
    """Validates InboxResponse wrapping summary metrics and item lists."""
    summary = InboxSummaryMetrics(
        total_active_blockers=1,
        p0_count=1,
        p1_count=0,
        p2_count=0,
        p3_count=0,
        waiting_clarifications_count=0,
        budget_alerts_count=0,
        avg_resolution_time_hours=4.5,
    )
    resp = InboxResponse(
        tenant_id="org_warner_001",
        organization_id="org_warner_001",
        items=[],
        summary=summary,
        total_count=0,
        timestamp="2026-09-07T12:00:00Z",
    )
    assert resp.total_count == 0
    assert resp.summary.p0_count == 1


def test_velocity_response_serialization():
    """Validates statistical metrics nesting in VelocityResponse."""
    res_m = ResolutionTimeMetric(median_hours=3.2, p90_hours=6.5, min_hours=1.0, max_hours=8.0, sample_count=12)
    stale_m = StaleClaimAgingMetric(avg_stale_hours=14.2, max_stale_hours=28.0, stale_count=2, distribution_under_24h=1, distribution_24_to_72h=1, distribution_over_72h=0)
    burn_m = BlockerVelocityMetric(new_blockers_24h=2, resolved_blockers_24h=4, net_burn_rate=2.0, resolution_rate_pct=66.67)
    stats = ProductionVelocityStats(
        production_id="prod_shadows_01",
        production_title="Shadows Over Broadway",
        resolution_time=res_m,
        stale_aging=stale_m,
        blocker_velocity=burn_m,
        has_active_high_severity_blockers=True,
        unresolved_blocker_count=2,
    )
    resp = VelocityResponse(
        tenant_id="org_warner_001",
        organization_id="org_warner_001",
        aggregate=stats,
        by_production=[stats],
        window_days=30,
        calculated_at="2026-09-07T12:00:00Z",
    )
    assert resp.aggregate.resolution_time.median_hours == 3.2
    assert resp.aggregate.has_active_high_severity_blockers is True
