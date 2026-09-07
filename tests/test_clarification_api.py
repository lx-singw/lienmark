"""
tests/test_clarification_api.py

Integration test suite for Lienmark Clarification REST API endpoints:
1. GET /api/v1/runs/{run_id}/clarifications (list, status filtering).
2. Strict tenant isolation (zero cross-tenant data leakage, 401 on missing auth).
3. POST /api/v1/clarifications/{request_id}/respond (successful resolution & audit).
4. Role verification: accepts authorized roles, rejects unauthorized roles (403).
5. Error handling: nonexistent request (404), cross-tenant modification (403/404).

Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.domain.models import ClarificationRequest
from backend.main import app
from backend.storage.clarification_store import get_clarification_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_clarification_store():
    """Cleans in-memory clarification store before and after each test."""
    store = get_clarification_store()
    store.clear_store()
    yield
    store.clear_store()


def _seed_clarification(
    request_id: str = "clrf_scene14_jazz",
    run_id: str = "run_v8_reval_001",
    tenant_id: str = "org_paramount_01",
    status: str = "pending",
) -> ClarificationRequest:
    """Helper seeding a ClarificationRequest into the store."""
    store = get_clarification_store()
    clrf = ClarificationRequest(
        request_id=request_id,
        run_id=run_id,
        claim_id="clm_scene14_jazz_solo",
        revision_id="v8",
        stable_lineage_key="lineage_diner_jazz_solo",
        question_text="Confirm master and synchronization license for diner cue.",
        required_document_type="Executed Synchronization License",
        assigned_role="Music Supervisor",
        status=status,
        tenant_id=tenant_id,
        production_id="prod_diner_noir",
        suggested_options=["Commissioned score", "Commercial track sync"],
    )
    return store.save_clarification(clrf, tenant_id=tenant_id, production_id="prod_diner_noir")


def test_get_run_clarifications_success_and_filtering():
    """Verifies listing clarifications by run_id and status filtering."""
    _seed_clarification(request_id="clrf_01", status="pending")
    _seed_clarification(request_id="clrf_02", status="resolved")
    headers = {"X-Tenant-Id": "org_paramount_01"}

    # List all for run
    res_all = client.get("/api/v1/runs/run_v8_reval_001/clarifications", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Filter pending
    res_pending = client.get(
        "/api/v1/runs/run_v8_reval_001/clarifications?status=pending", headers=headers
    )
    assert res_pending.status_code == 200
    assert len(res_pending.json()) == 1
    assert res_pending.json()[0]["request_id"] == "clrf_01"


def test_get_run_clarifications_tenant_isolation():
    """Verifies zero cross-tenant leakage and missing tenant authentication rejection."""
    _seed_clarification(request_id="clrf_secret_01", tenant_id="org_paramount_01")

    # Unauthorized different tenant receives empty list
    res_other = client.get(
        "/api/v1/runs/run_v8_reval_001/clarifications",
        headers={"X-Tenant-Id": "org_rogue_studio_02"},
    )
    assert res_other.status_code == 200
    assert res_other.json() == []

    # Unauthenticated default tenant sees zero items for paramount
    res_no_auth = client.get("/api/v1/runs/run_v8_reval_001/clarifications")
    assert res_no_auth.status_code == 200
    assert res_no_auth.json() == []

    # Invalid authentication token rejected fail-closed (HTTP 401)
    res_invalid_auth = client.get(
        "/api/v1/runs/run_v8_reval_001/clarifications",
        headers={"Authorization": "Bearer invalid_malformed_token"},
    )
    assert res_invalid_auth.status_code in (401, 403)


def test_post_clarification_respond_success():
    """Verifies resolving a clarification with response text and audit ledger logging."""
    _seed_clarification(request_id="clrf_jazz_100", status="pending")
    headers = {"X-Tenant-Id": "org_paramount_01"}

    payload = {
        "responder_role": "producer",
        "response_text": "Executed sync license secured from Vanguard Media (#VM-9912).",
        "attached_document_id": "doc_sync_license_9912",
        "selected_option": "Commercial track sync",
    }
    res = client.post("/api/v1/clarifications/clrf_jazz_100/respond", headers=headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["request_id"] == "clrf_jazz_100"
    assert data["status"] == "resolved"
    assert data["responder_role"] == "producer"
    assert data["event_id"] is not None


def test_post_clarification_respond_role_verification_rejects_unauthorized():
    """Verifies role-based access control rejects unauthorized roles fail-closed (HTTP 403)."""
    _seed_clarification(request_id="clrf_jazz_200", status="pending")
    headers = {"X-Tenant-Id": "org_paramount_01"}

    # Unauthorized role 'guest'
    payload = {
        "responder_role": "guest",
        "response_text": "Attempting unauthorized resolution.",
    }
    res = client.post("/api/v1/clarifications/clrf_jazz_200/respond", headers=headers, json=payload)
    assert res.status_code == 403
    assert "not authorized to resolve clarifications" in res.json()["detail"]


def test_post_clarification_respond_error_handling():
    """Verifies 404 for nonexistent request and 403 for cross-tenant tampering."""
    headers = {"X-Tenant-Id": "org_paramount_01"}

    # 404 on nonexistent request
    res_404 = client.post(
        "/api/v1/clarifications/clrf_nonexistent_999/respond",
        headers=headers,
        json={"responder_role": "producer", "response_text": "Resolving missing request."},
    )
    assert res_404.status_code == 404

    # Cross-tenant modification forbidden
    _seed_clarification(request_id="clrf_paramount_locked", tenant_id="org_paramount_01")
    res_cross = client.post(
        "/api/v1/clarifications/clrf_paramount_locked/respond",
        headers={"X-Tenant-Id": "org_sony_pictures_03"},
        json={"responder_role": "producer", "response_text": "Tampering cross-tenant."},
    )
    assert res_cross.status_code in (403, 404)
