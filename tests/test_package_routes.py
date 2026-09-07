"""
tests/test_package_routes.py

Integration tests for Decision Package dual-review REST API endpoints.
Sprint 5.2: Two-Person Accountable Review Workflow.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.core.dual_review as dr_mod
from backend.core.decision_package_types import DualReviewStatus
from backend.main import app


# Lead Counsel Elena Vance: user_id=usr_counsel_evance_002, role=authorized_reviewer
HEADERS_REVIEWER_A = {"X-API-Key": "lead_counsel_prod_2026_key"}
# Associate Counsel Marcus Reed: user_id=usr_counsel_mreed_003, role=authorized_reviewer
HEADERS_REVIEWER_B = {"X-API-Key": "associate_counsel_prod_2026_key"}
# Sony Audit (viewer role only): user_id=svc_sony_audit
HEADERS_VIEWER = {"X-API-Key": "lmk_live_sony_key_19"}

CREATE_PAYLOAD = {"cut_revision": "cut_v1", "proposed_disposition": "CLEARED"}
APPROVE_PAYLOAD = {"conflict_attestation": True, "notes": "Reviewed and approved."}


@pytest.fixture(autouse=True)
def _reset_coordinator():
    """Reset the global dual review coordinator before each test."""
    dr_mod._global_dual_review_coordinator = None
    yield
    dr_mod._global_dual_review_coordinator = None


@pytest.fixture()
def client():
    """TestClient fixture."""
    return TestClient(app, raise_server_exceptions=False)


def test_create_package_success(client: TestClient) -> None:
    """POST /api/v1/claims/{claim_id}/packages creates a new package."""
    resp = client.post("/api/v1/claims/CLM001/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["claim_id"] == "CLM001"
    assert body["status"] == DualReviewStatus.PENDING_FIRST_REVIEW.value
    assert len(body["canonical_digest"]) >= 16
    assert body["package_id"].startswith("pkg_")


def test_create_package_returns_existing(client: TestClient) -> None:
    """POST a second time returns the existing active package (idempotent)."""
    r1 = client.post("/api/v1/claims/CLM002/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/claims/CLM002/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r2.status_code == 201
    assert r2.json()["package_id"] == r1.json()["package_id"]


def test_create_package_forbidden_role(client: TestClient) -> None:
    """POST with viewer-only role returns 403."""
    resp = client.post("/api/v1/claims/CLM004/packages", json=CREATE_PAYLOAD, headers=HEADERS_VIEWER)
    assert resp.status_code == 403


def test_approve_package_primary(client: TestClient) -> None:
    """First approval moves status to first_review_approved."""
    r1 = client.post("/api/v1/claims/CLM010/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    r2 = client.post(
        f"/api/v1/claims/CLM010/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == DualReviewStatus.FIRST_REVIEW_APPROVED.value
    assert r2.json()["primary_approval"] is not None
    assert r2.json()["primary_approval"]["reviewer_id"] == "usr_counsel_evance_002"


def test_approve_package_secondary_distinct_reviewer(client: TestClient) -> None:
    """Second approval by a distinct reviewer moves status to final_approved."""
    r1 = client.post("/api/v1/claims/CLM011/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    client.post(
        f"/api/v1/claims/CLM011/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    r3 = client.post(
        f"/api/v1/claims/CLM011/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_B,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == DualReviewStatus.FINAL_APPROVED.value
    assert r3.json()["secondary_approval"] is not None
    assert r3.json()["secondary_approval"]["reviewer_id"] == "usr_counsel_mreed_003"


def test_approve_package_same_reviewer_rejected(client: TestClient) -> None:
    """Same reviewer cannot approve both primary and secondary."""
    r1 = client.post("/api/v1/claims/CLM012/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    client.post(
        f"/api/v1/claims/CLM012/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    r3 = client.post(
        f"/api/v1/claims/CLM012/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    assert r3.status_code == 400
    assert "distinct" in r3.json()["detail"].lower()


def test_approve_package_no_attestation(client: TestClient) -> None:
    """Missing conflict attestation returns 400."""
    r1 = client.post("/api/v1/claims/CLM013/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    r2 = client.post(
        f"/api/v1/claims/CLM013/packages/{pkg_id}/approve",
        json={"conflict_attestation": False},
        headers=HEADERS_REVIEWER_A,
    )
    assert r2.status_code == 400
    assert "attestation" in r2.json()["detail"].lower()


def test_approve_package_not_found(client: TestClient) -> None:
    """Approve on nonexistent package returns 404."""
    r = client.post(
        "/api/v1/claims/CLM014/packages/pkg_nonexistent/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    assert r.status_code == 404


def test_approve_package_stale(client: TestClient) -> None:
    """Approve on stale-invalidated package returns 409."""
    from backend.core.dual_review import get_dual_review_coordinator

    r1 = client.post("/api/v1/claims/CLM015/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    coordinator = get_dual_review_coordinator()
    pkg = coordinator.get_package(pkg_id)
    assert pkg is not None
    pkg.status = DualReviewStatus.STALE_INVALIDATED
    r2 = client.post(
        f"/api/v1/claims/CLM015/packages/{pkg_id}/approve",
        json=APPROVE_PAYLOAD,
        headers=HEADERS_REVIEWER_A,
    )
    assert r2.status_code == 409


def test_get_package_success(client: TestClient) -> None:
    """GET returns the package with its approval lineage."""
    r1 = client.post("/api/v1/claims/CLM020/packages", json=CREATE_PAYLOAD, headers=HEADERS_REVIEWER_A)
    assert r1.status_code == 201
    pkg_id = r1.json()["package_id"]
    r2 = client.get(f"/api/v1/claims/CLM020/packages/{pkg_id}", headers=HEADERS_REVIEWER_A)
    assert r2.status_code == 200
    assert r2.json()["package_id"] == pkg_id
    assert r2.json()["claim_id"] == "CLM020"


def test_get_package_not_found(client: TestClient) -> None:
    """GET nonexistent package returns 404."""
    r = client.get("/api/v1/claims/CLM021/packages/pkg_missing", headers=HEADERS_REVIEWER_A)
    assert r.status_code == 404
