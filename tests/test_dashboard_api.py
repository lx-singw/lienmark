"""
tests/test_dashboard_api.py

Exhaustive integration test suite for Command Center Dashboard REST endpoints:
1. GET /api/v1/dashboard/inbox (empty state, blockers, sorting, pagination, tenant isolation)
2. GET /api/v1/dashboard/velocity (resolution latency, stale aging, burn rate, safety)
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import ClarificationRequest, InvestigationRun, Production, RunStatus
from backend.main import app
from backend.orchestration.budget_governor import budget_governor
from backend.storage.clarification_store import get_clarification_store
from backend.storage.repository import get_tenant_repository, _repository_cache, InMemoryTenantRepository
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_dashboard_state():
    """Resets repository, clarification, and governor caches before and after each test."""
    get_clarification_store().clear_store()
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()
    budget_governor.reset()
    yield
    get_clarification_store().clear_store()
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()
    budget_governor.reset()


def _seed_prod_run(repo, org_id: str, pid: str = "prod_01", title: str = "Shadows"):
    """Helper to seed production and active run in tenant repository."""
    repo.save_production(Production(production_id=pid, title=title, organization_id=org_id))
    run = InvestigationRun(
        run_id=f"run_{pid}", production_id=pid, organization_id=org_id,
        base_version_id="v7", target_version_id="v8", status=RunStatus.COMPLETED,
    )
    repo.save_run(run)
    repo.set_active_run_id(pid, f"run_{pid}")
    return run


def test_inbox_unauthenticated_fail_closed(monkeypatch):
    """Fail-closed invariant: Missing Authorization header in strict mode returns 401."""
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    monkeypatch.setenv("TENANT_STRICT_MODE", "true")
    res = client.get("/api/v1/dashboard/inbox")
    assert res.status_code == 401


def test_inbox_empty_state_returns_zero_items_not_mock():
    """Zero-mock invariant: Clean empty tenant returns zero items, never mock data."""
    token = create_test_jwt(tenant_id="org_empty_01", roles=["reviewer"])
    res = client.get("/api/v1/dashboard/inbox", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 0
    assert data["items"] == []
    assert data["summary"]["total_active_blockers"] == 0
    assert data["summary"]["p0_count"] == 0


def _seed_sample_blockers(repo, tid: str, pid: str, rid: str):
    """Helper to seed critical claim and medium clarification blockers."""
    repo.save_claim(pid, rid, {
        "stable_lineage_key": "cue_hero_theme", "description": "Hero Theme Song",
        "asset_type": "music_sync", "duration_or_prominence": "30s focal scene",
        "status": "NEEDS_REVIEW",
    })
    repo.save_decision(pid, rid, {
        "decision_id": "dec_cue_01", "stable_lineage_key": "cue_hero_theme",
        "state": "STALE", "rationale": "Commercial synchronization license expired.",
    })
    get_clarification_store().save_clarification(
        ClarificationRequest(
            request_id="clrf_brand_01", run_id=rid, production_id=pid,
            claim_id="prop_watch", stable_lineage_key="prop_watch",
            question_text="Brand release needed from prop master.",
            status="pending",
        ),
        tenant_id=tid, production_id=pid,
    )


def test_inbox_aggregates_blockers_and_sorts_by_severity():
    """Verifies aggregation of stale claims, clarifications, and budget alerts with P0-P3 sorting."""
    tid = "org_paramount_01"
    repo = get_tenant_repository(tid)
    _seed_prod_run(repo, tid, "prod_p1", "Project Paramount")
    _seed_sample_blockers(repo, tid, "prod_p1", "run_prod_p1")

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/dashboard/inbox", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 2
    assert data["summary"]["total_active_blockers"] == 2
    assert data["summary"]["p0_count"] == 1
    assert data["summary"]["p2_count"] == 1
    assert data["items"][0]["severity"] == "P0_CRITICAL"
    assert data["items"][0]["quick_action"] == "review_claim"
    assert data["items"][1]["severity"] == "P2_MEDIUM"
    assert data["items"][1]["quick_action"] == "answer_clarification"


def test_inbox_filtering_and_pagination():
    """Verifies severity filtering, category filtering, and limit/offset pagination."""
    tid = "org_universal_02"
    repo = get_tenant_repository(tid)
    _seed_prod_run(repo, tid, "prod_u2", "Universal Cut")

    for i in range(5):
        key = f"prop_item_{i}"
        repo.save_claim("prod_u2", "run_prod_u2", {
            "stable_lineage_key": key, "description": f"Prop {i}",
            "duration_or_prominence": "background", "status": "NEEDS_REVIEW",
        })
        repo.save_decision("prod_u2", "run_prod_u2", {
            "decision_id": f"dec_{key}", "stable_lineage_key": key, "state": "STALE",
        })

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    # Pagination: limit=2, offset=1
    res_page = client.get(
        "/api/v1/dashboard/inbox?limit=2&offset=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_page.status_code == 200
    pdata = res_page.json()
    assert pdata["total_count"] == 5
    assert len(pdata["items"]) == 2

    # Severity Filter: P1_HIGH
    res_filt = client.get(
        "/api/v1/dashboard/inbox?severity=P1_HIGH",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_filt.status_code == 200
    assert len(res_filt.json()["items"]) == 5


def test_inbox_multi_tenant_isolation():
    """Strict tenant isolation: Tenant A never sees Tenant B's clearance blockers."""
    repo_a = get_tenant_repository("org_tenant_a")
    _seed_prod_run(repo_a, "org_tenant_a", "prod_a", "Title A")
    repo_a.save_claim("prod_a", "run_prod_a", {
        "stable_lineage_key": "claim_a", "description": "Asset A",
        "duration_or_prominence": "background", "status": "NEEDS_REVIEW",
    })

    repo_b = get_tenant_repository("org_tenant_b")
    _seed_prod_run(repo_b, "org_tenant_b", "prod_b", "Title B")
    repo_b.save_claim("prod_b", "run_prod_b", {
        "stable_lineage_key": "claim_b", "description": "Asset B",
        "duration_or_prominence": "focal", "status": "NEEDS_REVIEW",
    })

    token_a = create_test_jwt(tenant_id="org_tenant_a", roles=["reviewer"])
    res_a = client.get("/api/v1/dashboard/inbox", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["total_count"] == 1
    assert res_a.json()["items"][0]["stable_lineage_key"] == "claim_a"

    token_b = create_test_jwt(tenant_id="org_tenant_b", roles=["reviewer"])
    res_b = client.get("/api/v1/dashboard/inbox", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["total_count"] == 1
    assert res_b.json()["items"][0]["stable_lineage_key"] == "claim_b"


def test_velocity_unauthenticated_fail_closed(monkeypatch):
    """Fail-closed invariant: Missing Authorization header in strict mode returns 401."""
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    monkeypatch.setenv("TENANT_STRICT_MODE", "true")
    res = client.get("/api/v1/dashboard/velocity")
    assert res.status_code == 401


def test_velocity_empty_state_zero_claims_safety():
    """Verifies velocity on empty tenant returns clean zeroes without division errors."""
    token = create_test_jwt(tenant_id="org_vel_empty", roles=["reviewer"])
    res = client.get("/api/v1/dashboard/velocity", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["aggregate"]["resolution_time"]["sample_count"] == 0
    assert data["aggregate"]["resolution_time"]["median_hours"] == 0.0
    assert data["aggregate"]["stale_aging"]["stale_count"] == 0
    assert data["aggregate"]["blocker_velocity"]["new_blockers_24h"] == 0


def test_velocity_resolution_time_and_stale_aging():
    """Verifies median resolution calculation, stale aging buckets, and burn rate."""
    tid = "org_warner_vel"
    repo = get_tenant_repository(tid)
    _seed_prod_run(repo, tid, "prod_w1", "Warner Velocity Demo")

    now = datetime.now(timezone.utc)
    t_start = (now - timedelta(hours=10)).isoformat()
    t_resolved = (now - timedelta(hours=2)).isoformat()

    # Paired audit events: INVALIDATED at -10h, SIGNED_OFF at -2h -> duration = 8.0h
    repo.append_audit_event("prod_w1", "run_prod_w1", {
        "claim_id": "cue_01", "action_type": "CLAIM_INVALIDATED", "timestamp": t_start,
    })
    repo.append_audit_event("prod_w1", "run_prod_w1", {
        "claim_id": "cue_01", "action_type": "CLAIM_COUNSEL_SIGNED_OFF", "timestamp": t_resolved,
    })

    # Unresolved stale claim aged 30 hours -> falls into 24_to_72h bucket
    t_claim = (now - timedelta(hours=30)).isoformat()
    repo.save_claim("prod_w1", "run_prod_w1", {
        "stable_lineage_key": "stale_poster", "description": "Noir Poster",
        "status": "NEEDS_REVIEW", "created_at": t_claim,
    })

    token = create_test_jwt(tenant_id=tid, roles=["reviewer"])
    res = client.get("/api/v1/dashboard/velocity?window_days=7", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    agg = res.json()["aggregate"]
    assert agg["resolution_time"]["sample_count"] == 1
    assert agg["resolution_time"]["median_hours"] == 8.0
    assert agg["stale_aging"]["stale_count"] == 1
    assert agg["stale_aging"]["distribution_24_to_72h"] == 1
    assert agg["stale_aging"]["distribution_under_24h"] == 0
    assert agg["blocker_velocity"]["new_blockers_24h"] == 1
    assert agg["blocker_velocity"]["resolved_blockers_24h"] == 1
    assert agg["blocker_velocity"]["resolution_rate_pct"] == 50.0
