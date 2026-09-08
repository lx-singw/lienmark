"""
tests/test_dashboard_service.py

Verification tests for DashboardService business logic and aggregation.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timezone
import pytest

from backend.domain.models import ClarificationRequest, InvestigationRun, Production, RunStatus
from backend.orchestration.budget_governor import ExecutionBudgetGovernor
from backend.services.dashboard_service import DashboardService
from backend.storage.clarification_store import ClarificationStore
from backend.storage.repository import InMemoryTenantRepository


@pytest.fixture
def clean_env(tmp_path):
    """Provides isolated in-memory stores for clean testing."""
    InMemoryTenantRepository.reset_global_storage()
    repo = InMemoryTenantRepository(organization_id="org_test_01")
    clrf_store = ClarificationStore(base_dir=str(tmp_path / "clarifications"))
    budget_gov = ExecutionBudgetGovernor()
    svc = DashboardService(
        repo_factory=lambda org_id: repo,
        clarification_store=clrf_store,
        budget_gov=budget_gov,
    )
    yield repo, clrf_store, budget_gov, svc
    InMemoryTenantRepository.reset_global_storage()


def test_empty_inbox_returns_zero_items_not_mock(clean_env):
    """Safety Invariant: Empty state must return zero items, never synthetic fixtures."""
    repo, clrf_store, budget_gov, svc = clean_env
    inbox = svc.get_inbox(tenant_id="org_test_01")
    assert inbox.total_count == 0
    assert len(inbox.items) == 0
    assert inbox.summary.total_active_blockers == 0
    assert inbox.summary.p0_count == 0


def test_stale_claim_blocker_extraction(clean_env):
    """Asserts that unresolved stale claims surface as P0/P1 blockers."""
    repo, clrf_store, budget_gov, svc = clean_env
    repo.save_production(Production(production_id="prod_01", title="Shadows", organization_id="org_test_01"))
    run = InvestigationRun(
        run_id="run_01",
        production_id="prod_01",
        organization_id="org_test_01",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.COMPLETED,
    )
    repo.save_run(run)
    repo.set_active_run_id("prod_01", "run_01")

    repo.save_claim("prod_01", "run_01", {
        "stable_lineage_key": "poster_noir_detective",
        "description": "Noir Detective Poster",
        "asset_type": "prop_brand",
        "duration_or_prominence": "14s focal frame",
        "status": "NEEDS_REVIEW",
    })
    repo.save_decision("prod_01", "run_01", {
        "decision_id": "dec_01",
        "stable_lineage_key": "poster_noir_detective",
        "state": "STALE",
        "rationale": "Prominence shift from background blur to focal frame.",
    })

    inbox = svc.get_inbox(tenant_id="org_test_01")
    assert inbox.total_count == 1
    item = inbox.items[0]
    assert item.stable_lineage_key == "poster_noir_detective"
    assert item.severity.value == "P0_CRITICAL"  # focal prominence
    assert item.quick_action == "review_claim"


def test_open_clarification_blocker_extraction(clean_env):
    """Asserts that pending clarification requests surface as P2 items."""
    repo, clrf_store, budget_gov, svc = clean_env
    clrf_store.save_clarification(
        ClarificationRequest(
            request_id="clrf_99",
            run_id="run_01",
            production_id="prod_01",
            claim_id="prop_whiskey_label",
            stable_lineage_key="prop_whiskey_label",
            question_text="Need bill of sale receipt from props coordinator.",
            suggested_options=["Bill of Sale", "Fair Use Affidavit"],
            status="pending",
        ),
        tenant_id="org_test_01",
        production_id="prod_01",
    )

    inbox = svc.get_inbox(tenant_id="org_test_01")
    assert inbox.total_count == 1
    item = inbox.items[0]
    assert item.category.value == "clarification_pending"
    assert item.severity.value == "P2_MEDIUM"
    assert item.quick_action == "answer_clarification"


def test_budget_exhaustion_blocker_extraction(clean_env):
    """Asserts that runs paused in WAITING_FOR_BUDGET surface as P0 blockers."""
    repo, clrf_store, budget_gov, svc = clean_env
    repo.save_production(Production(production_id="prod_01", title="Shadows", organization_id="org_test_01"))
    run = InvestigationRun(
        run_id="run_budget_01",
        production_id="prod_01",
        organization_id="org_test_01",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.WAITING_FOR_BUDGET,
    )
    repo.save_run(run)
    repo.set_active_run_id("prod_01", "run_budget_01")

    inbox = svc.get_inbox(tenant_id="org_test_01")
    assert inbox.total_count == 1
    item = inbox.items[0]
    assert item.category.value == "budget_alert"
    assert item.severity.value == "P0_CRITICAL"
    assert item.quick_action == "approve_budget"


def test_velocity_metrics_with_audit_pairs_and_p0_safeguard(clean_env):
    """Validates truthful resolution time math and P0 safeguard flag."""
    repo, clrf_store, budget_gov, svc = clean_env
    repo.save_production(Production(production_id="prod_01", title="Shadows", organization_id="org_test_01"))
    run = InvestigationRun(
        run_id="run_01",
        production_id="prod_01",
        organization_id="org_test_01",
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.COMPLETED,
    )
    repo.save_run(run)

    # 1 resolved pair: 2 hours duration
    repo.append_audit_event("prod_01", "run_01", {
        "event_id": "ev_1", "action_type": "CLAIM_INVALIDATED", "claim_id": "clm_1",
        "timestamp_utc": "2026-09-07T10:00:00Z",
    })
    repo.append_audit_event("prod_01", "run_01", {
        "event_id": "ev_2", "action_type": "CLAIM_COUNSEL_SIGNED_OFF", "claim_id": "clm_1",
        "timestamp_utc": "2026-09-07T12:00:00Z",
    })
    # 1 active unresolved claim
    repo.save_claim("prod_01", "run_01", {
        "stable_lineage_key": "clm_active", "status": "NEEDS_REVIEW", "created_at": "2026-09-07T10:00:00Z",
    })

    vel = svc.get_velocity(tenant_id="org_test_01", window_days=30)
    assert vel.aggregate.resolution_time.sample_count == 1
    assert vel.aggregate.resolution_time.median_hours == 2.0
    assert vel.aggregate.has_active_high_severity_blockers is True
    assert vel.aggregate.unresolved_blocker_count == 1
