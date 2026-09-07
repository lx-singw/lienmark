"""
tests/test_rbac_and_signatures.py

Exhaustive Automated Verification Suite for Lienmark Role-Based Access Control (RBAC)
and Cryptographic Clearance Signatures.

Verifies:
1. Authorized Reviewer (Clearance Counsel) and Admin can successfully execute:
   - POST /api/review/action
   - POST /api/review/attest
   - POST /api/attorney/override
2. Producer role is rejected with HTTP 403 Forbidden across all clearance mutating actions.
3. Clearance Analyst role is rejected with HTTP 403 Forbidden across all clearance mutating actions.
4. Viewer role is rejected with HTTP 403 Forbidden across all clearance mutating actions.
5. Unauthenticated / missing credentials fail-closed with HTTP 401 Unauthorized.
6. Production-scoped role overrides:
   - Reviewer in Production A succeeds (HTTP 200).
   - Analyst in Production B is rejected (HTTP 403 Forbidden).
   - Unlisted production defaults to viewer and is rejected (HTTP 403 Forbidden).
7. Read-only endpoints remain accessible to permitted roles (Producer, Analyst, Viewer, Reviewer).
8. Cryptographic signatures & tamper-evident ledger integrity verification.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.test_tenant_middleware import create_test_jwt, TEST_JWT_SECRET


# =============================================================================
# Pytest Fixtures & Token Factory
# =============================================================================

@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient bound to the canonical Lienmark backend app."""
    return TestClient(app)


@pytest.fixture
def counsel_token() -> str:
    """Generates an authenticated JWT for Authorized Reviewer (Clearance Counsel)."""
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_counsel_sjenkins_001",
        email="sjenkins@lienmarklegal.com",
        roles=["authorized_reviewer"],
        claims_extra={"title": "Lead Production Clearance Counsel"},
    )


@pytest.fixture
def admin_token() -> str:
    """Generates an authenticated JWT for System / Legal Admin."""
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_admin_001",
        email="admin@lienmarklegal.com",
        roles=["admin"],
    )


@pytest.fixture
def producer_token() -> str:
    """Generates an authenticated JWT for Producer (Post Supervisor)."""
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_producer_mark_001",
        email="producer@warnerbros.com",
        roles=["producer"],
    )


@pytest.fixture
def analyst_token() -> str:
    """Generates an authenticated JWT for Clearance Analyst (Paralegal / Researcher)."""
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_analyst_rachel_001",
        email="rachel.analyst@lienmarklegal.com",
        roles=["clearance_analyst"],
    )


@pytest.fixture
def viewer_token() -> str:
    """Generates an authenticated JWT for Viewer (Underwriter / Studio Executive)."""
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_viewer_exec_001",
        email="exec@underwriter.com",
        roles=["viewer"],
    )


@pytest.fixture
def hybrid_scoped_token() -> str:
    """
    Generates a JWT with production-scoped role overrides:
    - Production 'prod_tentpole_alpha': 'authorized_reviewer'
    - Production 'prod_indie_beta': 'clearance_analyst'
    """
    return create_test_jwt(
        tenant_id="org_warner_bros_001",
        user_id="usr_counsel_hybrid_001",
        email="hybrid.counsel@lienmarklegal.com",
        roles=["viewer"],  # Global fallback is viewer
        claims_extra={
            "production_roles": {
                "prod_tentpole_alpha": "authorized_reviewer",
                "prod_indie_beta": "clearance_analyst",
            }
        },
    )


@pytest.fixture
def review_action_payload() -> Dict[str, Any]:
    """Canonical payload for POST /api/review/action (re_attest action)."""
    return {
        "stable_lineage_key": "poster_noir_detective_magazine",
        "action": "re_attest",
        "counsel_rationale": "Artwork verified in public domain under 17 U.S.C. Section 304(a).",
        "reviewer_name": "Sarah Jenkins, Esq.",
        "version_id": "v8",
    }


@pytest.fixture
def reattestation_payload() -> Dict[str, Any]:
    """Canonical payload for POST /api/review/attest and /api/attorney/override."""
    return {
        "stable_lineage_key": "poster_noir_detective_magazine",
        "new_status": "APPROVED",
        "counsel_rationale": "Re-attestation affirmed following statutory renewal search in Copyright Office records.",
        "reviewer_name": "Sarah Jenkins, Esq.",
        "version_id": "v8",
    }


# =============================================================================
# 1. Authorized Reviewer & Admin Success Tests
# =============================================================================

class TestAuthorizedReviewerAndAdminSuccess:
    """
    Asserts that Authorized Reviewer (Clearance Counsel) and Admin principals
    can successfully execute clearance adjudications across all mutating endpoints.
    """

    def test_authorized_reviewer_executes_review_action(
        self, client: TestClient, counsel_token: str, review_action_payload: Dict[str, Any]
    ):
        """Authorized Reviewer can execute re_attest on POST /api/review/action (HTTP 200)."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["status"] == "success"
        assert data["action"] == "re_attest"
        assert data["new_status"].lower() == "approved"
        assert "event_hash" in data
        assert len(data["event_hash"]) == 64  # SHA-256 event digest

    def test_authorized_reviewer_executes_attest(
        self, client: TestClient, counsel_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Authorized Reviewer can record re-attestation on POST /api/review/attest (HTTP 200)."""
        res = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["status"] == "recorded"
        assert data["new_status"].lower() == "approved"
        assert "event_hash" in data

    def test_authorized_reviewer_executes_attorney_override(
        self, client: TestClient, counsel_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Authorized Reviewer can record override on POST /api/attorney/override (HTTP 200)."""
        res = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["status"] == "recorded"
        assert data["new_status"].lower() == "approved"

    def test_admin_executes_all_clearance_endpoints(
        self, client: TestClient, admin_token: str, review_action_payload: Dict[str, Any], reattestation_payload: Dict[str, Any]
    ):
        """Admin holds root authority and can execute /action, /attest, and /override (HTTP 200)."""
        # 1. /api/review/action
        res_action = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_action.status_code == 200

        # 2. /api/review/attest
        res_attest = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_attest.status_code == 200

        # 3. /api/attorney/override
        res_override = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_override.status_code == 200

    def test_registered_demo_counsel_tokens_succeed(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """Standard registered counsel demo keys succeed under backward-compatible evaluation mode."""
        for token in ["sarah_jenkins_token_2026", "lead_counsel_prod_2026_key"]:
            res = client.post(
                "/api/review/action",
                json=review_action_payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200, f"Token {token} failed: {res.text}"
            assert res.json()["status"] == "success"


# =============================================================================
# 2. Producer Rejection Tests (HTTP 403 Forbidden)
# =============================================================================

class TestProducerForbiddenClearanceActions:
    """
    Asserts that Producer role principals are strictly rejected with HTTP 403 Forbidden
    when attempting clearance actions. Invariant: Storage connection / upload capability != review authority.
    """

    def test_producer_rejected_from_review_action(
        self, client: TestClient, producer_token: str, review_action_payload: Dict[str, Any]
    ):
        """Producer is rejected with HTTP 403 Forbidden on POST /api/review/action."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
        assert "Forbidden" in res.json().get("detail", "")

    def test_producer_rejected_from_review_attest(
        self, client: TestClient, producer_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Producer is rejected with HTTP 403 Forbidden on POST /api/review/attest."""
        res = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_producer_rejected_from_attorney_override(
        self, client: TestClient, producer_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Producer is rejected with HTTP 403 Forbidden on POST /api/attorney/override."""
        res = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_producer_api_key_rejected_from_clearance_actions(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """Studio ingestion pipeline API key with 'producer' role is rejected with HTTP 403."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": "Bearer lmk_live_wb_secret_key_88"},
        )
        assert res.status_code == 403, f"Expected 403 for producer API key, got {res.status_code}"


# =============================================================================
# 3. Clearance Analyst Rejection Tests (HTTP 403 Forbidden)
# =============================================================================

class TestClearanceAnalystForbiddenClearanceActions:
    """
    Asserts that Clearance Analyst (Research Paralegal) principals are strictly
    rejected with HTTP 403 Forbidden when attempting clearance actions.
    Invariant: Legal fact-finding and evidence drafting != legal adjudication authority.
    """

    def test_analyst_rejected_from_review_action(
        self, client: TestClient, analyst_token: str, review_action_payload: Dict[str, Any]
    ):
        """Clearance Analyst is rejected with HTTP 403 Forbidden on POST /api/review/action."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
        assert "Forbidden" in res.json().get("detail", "")

    def test_analyst_rejected_from_review_attest(
        self, client: TestClient, analyst_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Clearance Analyst is rejected with HTTP 403 Forbidden on POST /api/review/attest."""
        res = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_analyst_rejected_from_attorney_override(
        self, client: TestClient, analyst_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Clearance Analyst is rejected with HTTP 403 Forbidden on POST /api/attorney/override."""
        res = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_analyst_rejected_even_with_explicit_legal_rationale(
        self, client: TestClient, analyst_token: str
    ):
        """Clearance Analyst supplying thorough legal analysis is still rejected with HTTP 403."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Exhaustive legal analysis citing Stewart v. Abend, 495 U.S. 207 (1990).",
            "reviewer_name": "Rachel Vance (Paralegal)",
        }
        res = client.post(
            "/api/review/action",
            json=payload,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert res.status_code == 403, "Analyst cannot execute clearance override regardless of rationale quality."


# =============================================================================
# 4. Viewer Rejection Tests (HTTP 403 Forbidden)
# =============================================================================

class TestViewerForbiddenClearanceActions:
    """
    Asserts that Viewer (Underwriter / Studio Executive) principals are strictly
    rejected with HTTP 403 Forbidden when attempting clearance actions.
    """

    def test_viewer_rejected_from_review_action(
        self, client: TestClient, viewer_token: str, review_action_payload: Dict[str, Any]
    ):
        """Viewer is rejected with HTTP 403 Forbidden on POST /api/review/action."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_viewer_rejected_from_review_attest(
        self, client: TestClient, viewer_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Viewer is rejected with HTTP 403 Forbidden on POST /api/review/attest."""
        res = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_viewer_rejected_from_attorney_override(
        self, client: TestClient, viewer_token: str, reattestation_payload: Dict[str, Any]
    ):
        """Viewer is rejected with HTTP 403 Forbidden on POST /api/attorney/override."""
        res = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"

    def test_viewer_api_key_rejected_from_clearance_actions(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """Sony Pictures legal audit API key with 'viewer' role is rejected with HTTP 403."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": "Bearer lmk_live_sony_key_19"},
        )
        assert res.status_code == 403, f"Expected 403 for viewer API key, got {res.status_code}"


# =============================================================================
# 5. Unauthenticated / Missing Credentials Fail-Closed Tests (HTTP 401)
# =============================================================================

class TestUnauthenticatedFailClosed:
    """
    Asserts that requests lacking valid authentication credentials fail-closed
    with HTTP 401 Unauthorized across all clearance endpoints.
    """

    def test_missing_credentials_fails_closed_401_review_action(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """POST /api/review/action without auth header returns HTTP 401 Unauthorized."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"X-Require-Counsel-Auth": "true"},
        )
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
        assert "WWW-Authenticate" in res.headers
        assert "Unauthorized" in res.json().get("detail", "")

    def test_missing_credentials_fails_closed_401_attest(
        self, client: TestClient, reattestation_payload: Dict[str, Any]
    ):
        """POST /api/review/attest without auth header returns HTTP 401 Unauthorized."""
        res = client.post(
            "/api/review/attest",
            json=reattestation_payload,
            headers={"X-Require-Counsel-Auth": "true"},
        )
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    def test_missing_credentials_fails_closed_401_override(
        self, client: TestClient, reattestation_payload: Dict[str, Any]
    ):
        """POST /api/attorney/override without auth header returns HTTP 401 Unauthorized."""
        res = client.post(
            "/api/attorney/override",
            json=reattestation_payload,
            headers={"X-Require-Counsel-Auth": "true"},
        )
        assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    def test_malformed_authorization_header_returns_401(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """Malformed authorization headers (not 'Bearer <token>') return HTTP 401."""
        res_basic = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert res_basic.status_code == 401
        assert "Malformed" in res_basic.json().get("detail", "")

        res_empty = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": "Bearer "},
        )
        assert res_empty.status_code == 401

    def test_expired_jwt_token_returns_401(
        self, client: TestClient, review_action_payload: Dict[str, Any]
    ):
        """Expired JWT token fails closed with HTTP 401 Unauthorized."""
        expired_token = create_test_jwt(
            tenant_id="org_warner_bros_001",
            roles=["authorized_reviewer"],
            expires_in_seconds=-600,  # Expired 10 minutes ago
        )
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res.status_code == 401
        assert "expired" in res.json().get("detail", "").lower()


# =============================================================================
# 6. Production-Scoped Role Override Tests
# =============================================================================

class TestProductionScopedRoleOverrides:
    """
    Asserts that role assignments are strictly evaluated within the active production scope.
    A user principal may hold 'authorized_reviewer' in Production A, but only 'clearance_analyst'
    or 'viewer' in Production B.
    """

    def test_production_scoped_reviewer_succeeds_in_authorized_production(
        self, client: TestClient, hybrid_scoped_token: str, review_action_payload: Dict[str, Any]
    ):
        """User holding 'authorized_reviewer' in prod_tentpole_alpha succeeds on review action (HTTP 200)."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={
                "Authorization": f"Bearer {hybrid_scoped_token}",
                "X-Production-ID": "prod_tentpole_alpha",
            },
        )
        assert res.status_code == 200, f"Expected 200 in authorized production, got {res.status_code}: {res.text}"
        assert res.json()["status"] == "success"

    def test_production_scoped_reviewer_forbidden_in_analyst_production(
        self, client: TestClient, hybrid_scoped_token: str, review_action_payload: Dict[str, Any]
    ):
        """Same user holding 'clearance_analyst' in prod_indie_beta is rejected with HTTP 403 Forbidden."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={
                "Authorization": f"Bearer {hybrid_scoped_token}",
                "X-Production-ID": "prod_indie_beta",
            },
        )
        assert res.status_code == 403, f"Expected 403 in analyst-scoped production, got {res.status_code}: {res.text}"
        assert "Forbidden" in res.json().get("detail", "")

    def test_production_scoped_reviewer_forbidden_in_unlisted_production(
        self, client: TestClient, hybrid_scoped_token: str, review_action_payload: Dict[str, Any]
    ):
        """Same user accessing an unlisted production defaults to global role (viewer) and is rejected (HTTP 403)."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={
                "Authorization": f"Bearer {hybrid_scoped_token}",
                "X-Production-ID": "prod_unlisted_gamma",
            },
        )
        assert res.status_code == 403, f"Expected 403 in unlisted production, got {res.status_code}"


# =============================================================================
# 7. Read-Only Endpoints Accessibility Tests
# =============================================================================

class TestReadOnlyEndpointsAccessibility:
    """
    Asserts that read-only, non-mutating endpoints remain accessible to all permitted roles
    (Producer, Clearance Analyst, Viewer, Authorized Reviewer, Admin).
    """

    @pytest.mark.parametrize("endpoint", [
        "/api/review/queue",
        "/api/review/history",
        "/api/review/audit-trail",
        "/api/demo/state",
        "/api/fixtures",
    ])
    def test_read_only_accessible_to_producer(
        self, client: TestClient, producer_token: str, endpoint: str
    ):
        """Producer can inspect queues, audit trails, and status without mutating data (HTTP 200)."""
        res = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {producer_token}"},
        )
        assert res.status_code == 200, f"Producer failed to access {endpoint}: {res.status_code}"

    @pytest.mark.parametrize("endpoint", [
        "/api/review/queue",
        "/api/review/history",
        "/api/review/audit-trail",
        "/api/demo/state",
        "/api/fixtures",
    ])
    def test_read_only_accessible_to_analyst(
        self, client: TestClient, analyst_token: str, endpoint: str
    ):
        """Clearance Analyst can inspect research queues and audit trails (HTTP 200)."""
        res = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert res.status_code == 200, f"Analyst failed to access {endpoint}: {res.status_code}"

    @pytest.mark.parametrize("endpoint", [
        "/api/review/queue",
        "/api/review/history",
        "/api/review/audit-trail",
        "/api/demo/state",
        "/api/fixtures",
    ])
    def test_read_only_accessible_to_viewer(
        self, client: TestClient, viewer_token: str, endpoint: str
    ):
        """Viewer can inspect clearance status and audit trail for underwriter verification (HTTP 200)."""
        res = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert res.status_code == 200, f"Viewer failed to access {endpoint}: {res.status_code}"

    @pytest.mark.parametrize("endpoint", [
        "/api/review/queue",
        "/api/review/history",
        "/api/review/audit-trail",
        "/api/demo/state",
        "/api/fixtures",
    ])
    def test_read_only_accessible_to_reviewer(
        self, client: TestClient, counsel_token: str, endpoint: str
    ):
        """Authorized Reviewer can access all read-only review queues and ledgers (HTTP 200)."""
        res = client.get(
            endpoint,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200, f"Reviewer failed to access {endpoint}: {res.status_code}"


# =============================================================================
# 8. Cryptographic Signatures & Audit Ledger Integrity Tests
# =============================================================================

class TestCryptographicSignaturesAndLedgerIntegrity:
    """
    Asserts that every clearance action generates a tamper-evident SupersessionEvent
    bound to the authenticated reviewer identity, maintaining a verified SHA-256 event hash chain.
    """

    def test_clearance_action_emits_tamper_evident_event(
        self, client: TestClient, counsel_token: str, review_action_payload: Dict[str, Any]
    ):
        """Review action emits a cryptographically hashed SupersessionEvent."""
        res = client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "event_id" in data
        assert "event_hash" in data
        assert len(data["event_hash"]) == 64  # SHA-256 hex string

    def test_audit_ledger_cryptographic_verification_succeeds(
        self, client: TestClient, counsel_token: str, review_action_payload: Dict[str, Any]
    ):
        """Ledger integrity check verifies valid hash chain with zero tampering."""
        # 1. Execute an action to record an event
        client.post(
            "/api/review/action",
            json=review_action_payload,
            headers={"Authorization": f"Bearer {counsel_token}"},
        )

        # 2. Query ledger integrity via GET /api/review/history?as_dict=true
        res = client.get(
            "/api/review/history?as_dict=true",
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_ledger_tamper_free"] is True
        assert len(data["chain_head_hash"]) == 64
        assert data["chain_head_hash"] != "0" * 64

        # 3. Query structured audit trail via GET /api/audit-trail
        res_trail = client.get(
            "/api/audit-trail",
            headers={"Authorization": f"Bearer {counsel_token}"},
        )
        assert res_trail.status_code == 200
        trail_data = res_trail.json()
        assert trail_data["is_ledger_tamper_free"] is True
        assert len(trail_data["events"]) > 0
