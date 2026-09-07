"""
tests/test_decision_routes.py

Verification test suite for Counsel Decision API endpoints.
Sprint 4.3 - Reviewer Rejection & Directed Re-Investigation Loop.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.core.reviewer_loop import get_reviewer_loop_coordinator
from backend.main import app
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_coordinator_state():
    """Resets coordinator state before and after each test."""
    coordinator = get_reviewer_loop_coordinator()
    coordinator.clear_state()
    yield
    coordinator.clear_state()


def _post_decision(claim_id: str, payload: dict, token: str):
    """Convenience helper to POST claim decision."""
    return client.post(
        f"/api/v1/claims/{claim_id}/decision",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def test_decision_sign_off_success_reviewer():
    """Reviewer role successfully executes unconditional sign-off adjudication."""
    tenant = "org_paramount_001"
    token = create_test_jwt(tenant_id=tenant, user_id="usr_counsel_sarah", roles=["reviewer"])
    claim_id = "claim_poster_42"
    payload = {
        "action": "sign_off",
        "counsel_id": "counsel_sarah_01",
        "counsel_name": "Sarah Jenkins, Esq.",
        "citation_text": "17 U.S.C. § 107 Fair Use doctrine verified.",
    }
    res = _post_decision(claim_id, payload, token)
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    assert data["status"] == "approved"
    assert data["disposition"] == "approved"
    assert data["attempt_number"] == 1
    assert data["reinvestigation_run_id"] is None
    assert data["audit_event_id"].startswith("evt_")


def test_decision_sign_off_conditional_producer():
    """Producer role successfully executes conditional sign-off with clear caveats."""
    tenant = "org_warner_002"
    token = create_test_jwt(tenant_id=tenant, user_id="usr_prod_mike", roles=["producer"])
    claim_id = "claim_music_sync_10"
    conditions = ["Theatrical release only", "Must not exceed 30 seconds"]
    payload = {
        "action": "sign_off",
        "counsel_id": "counsel_rep_02",
        "counsel_name": "Michael Chang, Producer",
        "conditions": conditions,
    }
    res = _post_decision(claim_id, payload, token)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "conditional"
    assert data["disposition"] == "conditional"
    assert data["attempt_number"] == 1


def test_decision_reject_creates_reinvestigation_admin():
    """Admin role rejects claim with directive, triggering child reinvestigation run."""
    tenant = "org_universal_003"
    token = create_test_jwt(tenant_id=tenant, user_id="usr_admin_elena", roles=["admin"])
    claim_id = "claim_serenade_jazz_12"
    payload = {
        "action": "reject",
        "counsel_id": "counsel_elena_03",
        "counsel_name": "Elena Vance, Studio Counsel",
        "directive_text": "Re-search ASCAP catalog for 1972 synchronization rights splits.",
    }
    res = _post_decision(claim_id, payload, token)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "reinvestigation_requested"
    assert data["disposition"] == "rejected"
    assert data["reinvestigation_run_id"] is not None
    assert "reinv_" in data["reinvestigation_run_id"]


def test_decision_unauthorized_roles_rejected_403():
    """Viewer and Analyst roles are strictly rejected with HTTP 403 Forbidden."""
    tenant = "org_columbia_004"
    claim_id = "claim_statue_07"
    payload = {"action": "sign_off", "counsel_id": "counsel_anon", "counsel_name": "Unauthorized Actor"}
    for unauth_role in ["viewer", "analyst", "guest"]:
        token = create_test_jwt(tenant_id=tenant, roles=[unauth_role])
        res = _post_decision(claim_id, payload, token)
        assert res.status_code == 403
        assert "Access denied" in res.json()["detail"]


def test_decision_invalid_action_rejected_422():
    """Invalid actions outside ('sign_off', 'reject') trigger 422 Unprocessable Entity."""
    tenant = "org_paramount_001"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    bad_payload = {"action": "defer_decision", "counsel_id": "counsel_001", "counsel_name": "Sarah Jenkins"}
    res = _post_decision("claim_test_422", bad_payload, token)
    assert res.status_code == 422


def test_decision_tenant_isolation_forbidden_403():
    """Cross-tenant adjudication on another organization's claim is rejected with 403."""
    claim_id = "claim_shared_isolated"
    token_a = create_test_jwt(tenant_id="org_tenant_A", roles=["reviewer"])
    token_b = create_test_jwt(tenant_id="org_tenant_B", roles=["reviewer"])
    res_a = _post_decision(claim_id, {"action": "sign_off", "counsel_id": "c_a", "counsel_name": "A"}, token_a)
    assert res_a.status_code == 200
    res_b = _post_decision(claim_id, {"action": "reject", "counsel_id": "c_b", "counsel_name": "B"}, token_b)
    assert res_b.status_code == 403
    assert "Cross-tenant access forbidden" in res_b.json()["detail"]


def test_get_attempts_chronological_lineage():
    """Chronological attempt lineage correctly records rejection followed by sign-off."""
    tenant = "org_paramount_001"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    claim_id = "claim_multi_attempt_01"
    p1 = {
        "action": "reject", "counsel_id": "c1", "counsel_name": "Sarah",
        "directive_text": "Verify renewal with LOC.",
    }
    assert _post_decision(claim_id, p1, token).status_code == 200
    p2 = {
        "action": "sign_off", "counsel_id": "c1", "counsel_name": "Sarah",
        "citation_text": "Renewal verified in LOC.", "conditions": ["Background only"],
    }
    assert _post_decision(claim_id, p2, token).status_code == 200

    res = client.get(f"/api/v1/claims/{claim_id}/attempts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    lineage = res.json()
    assert lineage["claim_id"] == claim_id and lineage["total_attempts"] == 2
    att1, att2 = lineage["attempts"][0], lineage["attempts"][1]
    assert att1["attempt_number"] == 1 and att1["action"] == "reject"
    assert att1["status"] == "reinvestigation_requested"
    assert att2["attempt_number"] == 2 and att2["action"] == "sign_off"
    assert att2["status"] == "conditional"


def test_get_attempts_cross_tenant_forbidden_403():
    """Attempt lineage retrieval strictly prohibits cross-tenant snooping."""
    claim_id = "claim_secret_lineage"
    token_a = create_test_jwt(tenant_id="org_tenant_A", roles=["reviewer"])
    token_b = create_test_jwt(tenant_id="org_tenant_B", roles=["reviewer"])
    _post_decision(claim_id, {"action": "sign_off", "counsel_id": "c_a", "counsel_name": "A"}, token_a)

    res = client.get(f"/api/v1/claims/{claim_id}/attempts", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403


def test_get_citation_suggestions():
    """Citation suggestion endpoint returns pre-populated statutory and case templates."""
    tenant = "org_universal_003"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    claim_id = "claim_artwork_noir_11"

    res = client.get(f"/api/v1/claims/{claim_id}/citation-suggestions", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["claim_id"] == claim_id
    tmpl_ids = [s["template_id"] for s in data["suggestions"]]
    assert "tmpl_fair_use_incidental" in tmpl_ids
    assert "tmpl_public_domain_pre1928" in tmpl_ids
    assert "tmpl_sync_standard_warranty" in tmpl_ids
