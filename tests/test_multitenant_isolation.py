"""
Unit and Integration Tests for Sprint 1.1:
Multi-Tenant Isolation, Cross-Tenant Attack Resistance, and Zero-Trust Security Gates.
Asserts that Tenant A can NEVER read, mutate, or delete Tenant B's assets under any circumstance.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.domain.models import (
    Organization,
    Production,
    ProductionVersion,
    DocumentRecord,
    InvestigationRun,
    RunStatus,
)
from backend.storage.repository import (
    TenantRepository,
    InMemoryTenantRepository,
    get_tenant_repository,
    TenantSecurityViolation,
    TenantContextMissingError,
    TenantMismatchViolation,
    FailClosedSecurityViolation,
)
from backend.middleware.tenant import (
    TenantContext,
    TenantContextMiddleware,
    get_current_tenant,
)
from tests.test_tenant_middleware import create_test_jwt, build_test_app

# Use test app instrumented in strict mode for HTTP security tests
strict_app = build_test_app(strict_mode=True, allow_header_auth=True)
client = TestClient(strict_app)


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset repository in-memory storage before each test."""
    InMemoryTenantRepository.reset_global_storage()


# =============================================================================
# 1. Repository-Level Hermetic Data Isolation Tests
# =============================================================================

class TestRepositoryDataIsolation:
    """Verifies that separate tenant repositories cannot read, mutate, or access each other's data."""

    def test_cross_tenant_production_isolation(self):
        repo_a = get_tenant_repository("org_paramount", force_in_memory=True)
        repo_b = get_tenant_repository("org_columbia", force_in_memory=True)

        # 1. Tenant A persists a production
        prod_a = Production(
            production_id="prod_top_gun_3",
            organization_id="org_paramount",
            title="Top Gun 3",
            budget_cap_usd=10000.0,
        )
        repo_a.save_production(prod_a)

        # 2. Tenant B attempts to read Tenant A's production -> None
        assert repo_b.get_production("prod_top_gun_3") is None

        # 3. Tenant B lists productions -> empty
        assert len(repo_b.list_productions()) == 0

        # 4. Tenant B attempts to delete Tenant A's production -> False
        assert repo_b.delete_production("prod_top_gun_3") is False
        assert repo_a.get_production("prod_top_gun_3") is not None

    def test_cross_tenant_run_and_subcollections_isolation(self):
        repo_a = get_tenant_repository("org_a24", force_in_memory=True)
        repo_b = get_tenant_repository("org_neon", force_in_memory=True)

        prod_id = "prod_everything_everywhere"
        run_id = "run_multiverse_v8"

        # Tenant A creates run, claim, decision, and audit event
        run_a = InvestigationRun(
            run_id=run_id,
            organization_id="org_a24",
            production_id=prod_id,
            base_version_id="v7",
            target_version_id="v8",
            status=RunStatus.INVESTIGATING,
        )
        repo_a.save_run(run_a)
        repo_a.save_claim(prod_id, run_id, {
            "stable_lineage_key": "googly_eyes_poster",
            "asset_type": "artwork",
            "status": "APPROVED",
        })
        repo_a.save_decision(prod_id, run_id, {
            "stable_lineage_key": "googly_eyes_poster",
            "status": "APPROVED",
            "reviewer_name": "Counsel A",
        })
        e_a = repo_a.append_audit_event(prod_id, run_id, {"action": "INITIAL_SIGN_OFF"})

        # Tenant B queries Tenant A's entities
        assert repo_b.get_run(prod_id, run_id) is None
        assert repo_b.list_runs(prod_id) == []
        assert repo_b.get_claim(prod_id, run_id, "googly_eyes_poster") is None
        assert repo_b.list_claims(prod_id, run_id) == []
        assert repo_b.get_decision(prod_id, run_id, "googly_eyes_poster") is None
        assert repo_b.list_decisions(prod_id, run_id) == {}
        assert repo_b.list_audit_events(prod_id, run_id) == []

        # Assert Tenant B's sequencer is pristine (sequence 0)
        e_b = repo_b.append_audit_event("prod_b_01", "run_b_01", {"action": "TENANT_B_FIRST_EVENT"})
        assert e_b["sequence_number"] == 1
        assert e_b["parent_event_hash"] == "0" * 64
        # Tenant A's event was sequence 1 with a different hash
        assert e_b["organization_id"] == "org_neon"
        assert e_a["organization_id"] == "org_a24"

    def test_cross_tenant_document_isolation(self):
        repo_a = get_tenant_repository("org_disney", force_in_memory=True)
        repo_b = get_tenant_repository("org_dreamworks", force_in_memory=True)

        doc_a = DocumentRecord(
            doc_id="doc_lion_king_script",
            organization_id="org_disney",
            production_id="prod_lion_king",
            filename="lion_king_v8.pdf",
            content_hash="f" * 64,
            doc_type="screenplay",
        )
        repo_a.save_document(doc_a)

        assert repo_b.get_document("doc_lion_king_script") is None
        assert repo_b.list_documents() == []


# =============================================================================
# 2. Parameter Manipulation & Confused Deputy Rejection Tests
# =============================================================================

class TestConfusedDeputyAndTamperingRejection:
    """Verifies that injecting an alien organization_id into parameters or payloads fails closed."""

    def test_tampered_payload_entity_raises_tenant_mismatch(self):
        repo_a = get_tenant_repository("org_sony", force_in_memory=True)

        # Alien production declaring org_fox
        alien_prod = Production(
            production_id="prod_avatar_3",
            organization_id="org_fox",
            title="Avatar 3",
        )

        with pytest.raises(TenantMismatchViolation):
            repo_a.save_production(alien_prod)

    def test_tampered_document_entity_raises_tenant_mismatch(self):
        repo_a = get_tenant_repository("org_sony", force_in_memory=True)

        alien_doc = DocumentRecord(
            doc_id="doc_alien_01",
            organization_id="org_fox",
            production_id="prod_sony_01",
            filename="alien.pdf",
            content_hash="1" * 64,
            doc_type="screenplay",
        )

        with pytest.raises(TenantMismatchViolation):
            repo_a.save_document(alien_doc)

    def test_empty_or_none_repo_constructor_fails_closed(self):
        with pytest.raises(TenantContextMissingError):
            get_tenant_repository(None)  # type: ignore

        with pytest.raises(TenantContextMissingError):
            get_tenant_repository("")

        with pytest.raises(TenantContextMissingError):
            get_tenant_repository("   ")


# =============================================================================
# 3. HTTP Boundary & Middleware Isolation Tests
# =============================================================================

class TestHttpBoundaryTenantIsolation:
    """Verifies fail-closed HTTP 401/403 rejections when accessing API endpoints across tenants."""

    def test_url_path_organization_mismatch_returns_403_forbidden(self):
        # Create JWT for org_lionsgate
        token_lionsgate = create_test_jwt(
            tenant_id="org_lionsgate",
            user_id="user_john_wick",
            roles=["Reviewer"],
        )

        # Attacker authenticated as org_lionsgate attempts to access org_universal URL
        res = client.get(
            "/api/organizations/org_universal/runs",
            headers={"Authorization": f"Bearer {token_lionsgate}"},
        )
        # Middleware intercepts URL mismatch against authenticated JWT context
        assert res.status_code == 403
        data = res.json()
        assert "Cross-tenant access" in data["detail"] or "not match" in data["detail"].lower()

    def test_matching_url_path_and_jwt_succeeds(self):
        token_lionsgate = create_test_jwt(
            tenant_id="org_lionsgate",
            user_id="user_john_wick",
            roles=["Reviewer"],
        )

        # Request matching organization in URL path
        res = client.get(
            "/api/organizations/org_lionsgate/runs",
            headers={"Authorization": f"Bearer {token_lionsgate}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["authenticated_tenant"] == "org_lionsgate"

    def test_header_spoofing_conflict_in_strict_mode_returns_403(self):
        token_org_a = create_test_jwt(
            tenant_id="org_legitimate_a",
            user_id="user_a",
            roles=["Reviewer"],
        )

        # Attacker injects spoofed X-Organization-Id header for org_victim_b
        res = client.get(
            "/api/clearance/evaluate",
            headers={
                "Authorization": f"Bearer {token_org_a}",
                "X-Organization-Id": "org_victim_b",
            },
        )
        # In strict mode, conflict between JWT and header triggers HTTP 403
        assert res.status_code == 403
        assert "mismatch" in res.json()["detail"].lower()
