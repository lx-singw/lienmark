"""
tests/test_clarification_routes.py

Verification test suite for Clarification REST API endpoints.
Tests GET /api/v1/runs/{run_id}/clarifications and POST /api/v1/clarifications/{request_id}/respond.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.domain.models import ClarificationRequest
from backend.main import app
from backend.storage.clarification_store import get_clarification_store
from backend.storage.ledger import CryptographicLedger
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_clarification_store():
    """Resets clarification store state between test runs."""
    store = get_clarification_store()
    store.clear_store()
    yield
    store.clear_store()


def _make_clrf(
    req_id: str,
    run_id: str,
    status: str = "pending",
    assigned_role: str = "producer",
) -> ClarificationRequest:
    return ClarificationRequest(
        request_id=req_id,
        run_id=run_id,
        claim_id=f"clm_{req_id}",
        revision_id="v8",
        stable_lineage_key=f"lineage_{req_id}",
        question_text=f"Clarification needed for {req_id}?",
        suggested_options=["Option A (License)", "Option B (Fair Use)"],
        required_document_type="Executed Synchronization License",
        assigned_role=assigned_role,
        status=status,
    )


def test_list_run_clarifications_success_and_filtering():
    store = get_clarification_store()
    tenant = "org_warner_001"
    run_id = "run_alpha_01"

    store.save_clarification(_make_clrf("clrf_1", run_id, "pending"), tenant)
    store.save_clarification(_make_clrf("clrf_2", run_id, "resolved"), tenant)
    store.save_clarification(_make_clrf("clrf_3", run_id, "cancelled"), tenant)

    token = create_test_jwt(tenant_id=tenant, roles=["producer"])
    headers = {"Authorization": f"Bearer {token}"}

    # All items
    res = client.get(f"/api/v1/runs/{run_id}/clarifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

    # Filter: pending
    res_p = client.get(f"/api/v1/runs/{run_id}/clarifications?status=pending", headers=headers)
    assert res_p.status_code == 200
    assert len(res_p.json()) == 1
    assert res_p.json()[0]["request_id"] == "clrf_1"

    # Filter: resolved
    res_r = client.get(f"/api/v1/runs/{run_id}/clarifications?status=resolved", headers=headers)
    assert res_r.status_code == 200
    assert len(res_r.json()) == 1
    assert res_r.json()[0]["request_id"] == "clrf_2"


def test_list_run_clarifications_tenant_isolation():
    store = get_clarification_store()
    run_id = "run_shared_99"

    store.save_clarification(_make_clrf("clrf_t1", run_id, "pending"), "org_tenant_one")
    store.save_clarification(_make_clrf("clrf_t2", run_id, "pending"), "org_tenant_two")

    # Tenant One call
    token_1 = create_test_jwt(tenant_id="org_tenant_one", roles=["producer"])
    res_1 = client.get(f"/api/v1/runs/{run_id}/clarifications", headers={"Authorization": f"Bearer {token_1}"})
    assert res_1.status_code == 200
    items_1 = res_1.json()
    assert len(items_1) == 1
    assert items_1[0]["request_id"] == "clrf_t1"

    # Tenant Two call
    token_2 = create_test_jwt(tenant_id="org_tenant_two", roles=["producer"])
    res_2 = client.get(f"/api/v1/runs/{run_id}/clarifications", headers={"Authorization": f"Bearer {token_2}"})
    assert res_2.status_code == 200
    items_2 = res_2.json()
    assert len(items_2) == 1
    assert items_2[0]["request_id"] == "clrf_t2"


def test_respond_to_clarification_producer_success():
    store = get_clarification_store()
    tenant = "org_warner_001"
    req_id = "clrf_music_sync_01"
    store.save_clarification(_make_clrf(req_id, "run_music_01", "pending"), tenant, "prod_music_01")

    token = create_test_jwt(tenant_id=tenant, user_id="usr_producer_jane", roles=["producer"])
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "response_text": "Commercial track cleared under Universal master use license.",
        "attached_document_id": "doc_sync_license_4492.pdf",
        "selected_option": "Option A (License)",
        "responder_role": "Producer",
    }

    res = client.post(f"/api/v1/clarifications/{req_id}/respond", json=payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["request_id"] == req_id
    assert body["status"] == "resolved"
    assert body["resolved_by"] == "usr_producer_jane"
    assert body["event_id"] is not None
    assert body["clarification"]["attached_document_ref"] == "doc_sync_license_4492.pdf"

    # Verify Cryptographic Ledger Integrity
    ledger: CryptographicLedger = store._ledger
    is_valid, err, count = ledger.verify_chain("prod_music_01")
    assert is_valid is True
    assert count >= 1


def test_respond_to_clarification_roles_reviewer_and_admin():
    store = get_clarification_store()
    tenant = "org_universal_002"

    for r_id, role, role_str in [
        ("clrf_rev", "reviewer", "Reviewer"),
        ("clrf_adm", "admin", "Admin"),
    ]:
        store.save_clarification(_make_clrf(r_id, "run_roles_01", "pending"), tenant)
        token = create_test_jwt(tenant_id=tenant, user_id=f"usr_{role}", roles=[role])
        payload = {
            "response_text": f"Resolved by authorized {role_str}",
            "responder_role": role_str,
        }
        res = client.post(
            f"/api/v1/clarifications/{r_id}/respond",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "resolved"


def test_respond_to_clarification_unauthorized_role_rejected():
    store = get_clarification_store()
    tenant = "org_warner_001"
    req_id = "clrf_unauth_01"
    store.save_clarification(_make_clrf(req_id, "run_unauth_01", "pending"), tenant)

    # 1. Declared role is invalid
    token_prod = create_test_jwt(tenant_id=tenant, roles=["producer"])
    bad_payload = {"response_text": "Illegal role", "responder_role": "Viewer"}
    res = client.post(
        f"/api/v1/clarifications/{req_id}/respond",
        json=bad_payload,
        headers={"Authorization": f"Bearer {token_prod}"},
    )
    assert res.status_code == 403

    # 2. Principal only has viewer role attempting to declare producer
    token_viewer = create_test_jwt(tenant_id=tenant, roles=["viewer"])
    valid_role_payload = {"response_text": "I am not producer", "responder_role": "Producer"}
    res_2 = client.post(
        f"/api/v1/clarifications/{req_id}/respond",
        json=valid_role_payload,
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert res_2.status_code == 403


def test_respond_to_clarification_cross_tenant_forbidden():
    store = get_clarification_store()
    req_id = "clrf_tenant_a_01"
    store.save_clarification(_make_clrf(req_id, "run_isolation_01", "pending"), "org_tenant_A")

    # Tenant B tries to respond to Tenant A's clarification
    token_b = create_test_jwt(tenant_id="org_tenant_B", roles=["producer"])
    payload = {"response_text": "Attempt cross tenant response", "responder_role": "Producer"}
    res = client.post(
        f"/api/v1/clarifications/{req_id}/respond",
        json=payload,
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code in (403, 404)


def test_respond_to_clarification_not_found():
    token = create_test_jwt(tenant_id="org_warner_001", roles=["producer"])
    payload = {"response_text": "Missing request", "responder_role": "Producer"}
    res = client.post(
        "/api/v1/clarifications/clrf_non_existent_404/respond",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
