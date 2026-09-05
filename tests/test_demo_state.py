"""
Demo State Management & Instantaneous Take Recovery Integration Tests
Sprint 6B Task 1: Tests /api/demo/reset, /api/demo/seed, and /api/demo/state endpoints.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app, counsel_checkpoint_manager
from backend.core.security import idempotency_key_manager

client = TestClient(app)


def test_demo_reset_endpoint():
    """
    POST /api/demo/reset:
    - Fully resets in-memory workflow state, counsel decisions, queues, and supersession audit trail via counsel_checkpoint_manager.reset().
    - Re-initializes baseline Script Cut V7 state (12 approved claims under policy E&O-2026.1-DEVPOST by Sarah Jenkins, Esq.).
    - Clears idempotency cache.
    - Returns: {"status": "RESET_SUCCESS", "message": "Demo state reset to clean V7 baseline", "total_claims": 12, "approved_claims": 12, "timestamp": ...}.
    """
    # 1. Populate some dummy idempotency record and review action
    idempotency_key_manager.set(
        key="test_dummy_key",
        status_code=200,
        content=b'{"cached": true}',
        headers={},
    )
    assert len(idempotency_key_manager) >= 1

    # 2. Invoke reset
    res = client.post("/api/demo/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RESET_SUCCESS"
    assert "Demo state reset to clean V7 baseline" in data["message"]
    assert data["total_claims"] == 12
    assert data["approved_claims"] == 12
    assert "timestamp" in data

    # 3. Verify idempotency cache is cleared
    assert len(idempotency_key_manager) == 0

    # 4. Verify audit trail is empty
    assert len(counsel_checkpoint_manager.get_audit_trail()) == 0

    # 5. Verify demo state reflects baseline
    state_res = client.get("/api/demo/state")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["mode"] == "baseline"
    assert state_data["total_claims"] == 12
    assert state_data["carried_forward_count"] == 12
    assert state_data["reopened_count"] == 0
    assert state_data["reattested_count"] == 0
    assert state_data["exception_count"] == 0
    assert state_data["reviewer_identity"]["name"] == "Sarah Jenkins, Esq."
    assert state_data["reviewer_identity"]["reviewer_id"] == "counsel_sjenkins_001"


def test_demo_seed_modes():
    """
    POST /api/demo/seed:
    - mode="baseline": 12 approved claims
    - mode="drifted": V8 ingested, 10 carried, 2 reopened (poster item 11 and jazz item 12)
    - mode="resolved": Item 11 re-attested, Item 12 rejected exception (10 + 1 + 1 = 12 completed)
    """
    # 1. Test Seed Drifted
    drifted_res = client.post("/api/demo/seed?mode=drifted")
    assert drifted_res.status_code == 200
    drifted_data = drifted_res.json()
    assert drifted_data["status"] == "SEED_SUCCESS"
    assert drifted_data["mode"] == "drifted"
    assert drifted_data["total_claims"] == 12
    assert drifted_data["carried_forward_count"] == 10
    assert drifted_data["reopened_count"] == 2
    assert drifted_data["reattested_count"] == 0
    assert drifted_data["exception_count"] == 0

    # Check state endpoint after drifted
    state_res = client.get("/api/demo/state")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["mode"] == "drifted"
    assert state_data["carried_forward_count"] == 10
    assert state_data["reopened_count"] == 2

    # Check review queue has 2 stale items
    queue_res = client.get("/api/review/queue")
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert len(queue_data["items"]) == 2
    keys = {item["stable_lineage_key"] for item in queue_data["items"]}
    assert "poster_noir_detective_magazine" in keys
    assert "music_cue_midnight_serenade" in keys

    # 2. Test Seed Resolved
    resolved_res = client.post("/api/demo/seed", json={"mode": "resolved"})
    assert resolved_res.status_code == 200
    resolved_data = resolved_res.json()
    assert resolved_data["status"] == "SEED_SUCCESS"
    assert resolved_data["mode"] == "resolved"
    assert resolved_data["total_claims"] == 12
    assert resolved_data["carried_forward_count"] == 10
    assert resolved_data["reopened_count"] == 0
    assert resolved_data["reattested_count"] == 1
    assert resolved_data["exception_count"] == 1
    assert resolved_data["completed_claims"] == 12

    # Check state endpoint after resolved
    state_res = client.get("/api/demo/state")
    state_data = state_res.json()
    assert state_data["mode"] == "resolved"
    assert state_data["carried_forward_count"] == 10
    assert state_data["reopened_count"] == 0
    assert state_data["reattested_count"] == 1
    assert state_data["exception_count"] == 1
    assert state_data["completed_claims"] == 12
    assert state_data["audit_events_count"] == 2
    assert state_data["ledger_integrity"] is True

    # Check Exceptions Schedule reflects 10 carried, 1 re-attested, 1 exception
    sched_res = client.get("/api/reports/exceptions")
    assert sched_res.status_code == 200
    sched = sched_res.json()
    assert sched["total_claims"] == 12
    assert sched["carried_forward_count"] == 10
    assert sched["re_attested_count"] == 1
    assert sched["unresolved_exception_count"] == 1

    # 3. Test Seed Baseline (Take recovery back to start)
    base_res = client.post("/api/demo/seed?mode=baseline")
    assert base_res.status_code == 200
    base_data = base_res.json()
    assert base_data["status"] == "SEED_SUCCESS"
    assert base_data["mode"] == "baseline"
    assert base_data["total_claims"] == 12
    assert base_data["carried_forward_count"] == 12
    assert base_data["reopened_count"] == 0


def test_demo_seed_invalid_mode():
    """Invalid modes should return HTTP 400 Bad Request."""
    res = client.post("/api/demo/seed?mode=invalid_take")
    assert res.status_code == 400
    assert "Invalid demo seed mode" in res.json()["detail"]
