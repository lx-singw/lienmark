"""
tests/test_evidence_routes.py

Integration Test Suite for Evidence Explorer API:
1. Search & multi-facet filtering (q, domain, tier, category, source_type)
2. Tenant boundary isolation & zero-leak guarantees (INV-S62-01)
3. Detail lookup & cryptographic integrity
4. Side-by-side public vs private contract comparison with server-side redaction (INV-S62-02)
5. Fail-closed authentication (401 Unauthorized)
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    AtomicRightsClaim,
    DocumentRecord,
    InvestigationRun,
    Production,
    PublicEvidenceSnapshot,
    RunStatus,
)
from backend.main import app
from backend.storage.repository import InMemoryTenantRepository, _repository_cache, get_tenant_repository
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()
    yield
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()


def _create_seed_claim(repo, pid: str, run_id: str):
    snap = PublicEvidenceSnapshot(
        snapshot_id="snap_101",
        use_id="claim_music_01",
        stable_lineage_key="cue_midnight_serenade",
        query="Midnight Serenade composer copyright registration",
        source_url="https://cocatalog.loc.gov/record/12345",
        source_title="LOC Registration: Midnight Serenade",
        excerpt="Registered 1968 by Vanguard Music Corp. All rights reserved.",
        domain="cocatalog.loc.gov",
    )
    claim = AtomicRightsClaim(
        claim_id="claim_music_01",
        production_id=pid,
        title="Midnight Serenade Cue",
        occurrence_id="occ_01",
        occurrence_lineage_id="occ_lineage_01",
        right_category="music",
        rights_subject="Midnight Serenade",
        evidence_snapshot=snap,
    )
    claim_payload = claim.model_dump()
    claim_payload["stable_lineage_key"] = "cue_midnight_serenade"
    claim_payload["use_id"] = "claim_music_01"
    claim_payload["evidence_snapshot"] = snap.model_dump()
    repo.save_claim(pid, run_id, claim_payload)


def _seed_tenant_evidence(org_id: str, pid: str = "prod_alpha", run_id: str = "run_alpha"):
    repo = get_tenant_repository(org_id)
    repo.save_production(Production(production_id=pid, title="Alpha Production", organization_id=org_id))
    run = InvestigationRun(
        run_id=run_id,
        production_id=pid,
        organization_id=org_id,
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.COMPLETED,
    )
    repo.save_run(run)
    repo.set_active_run_id(pid, run_id)
    _create_seed_claim(repo, pid, run_id)
    doc = DocumentRecord(
        doc_id="doc_lic_01",
        production_id=pid,
        organization_id=org_id,
        filename="Master_Sync_License_Midnight_Serenade.pdf",
        doc_type="sync_license",
        content_hash="a" * 64,
    )
    repo.save_document(doc)
    return repo


def test_evidence_search_unauthenticated_fail_closed(monkeypatch):
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    monkeypatch.setenv("TENANT_STRICT_MODE", "true")
    res = client.get("/api/v1/evidence/search")
    assert res.status_code == 401


def test_evidence_search_empty_state():
    jwt = create_test_jwt(tenant_id="org_empty", user_id="user_1", roles=["reviewer"])
    res = client.get("/api/v1/evidence/search", headers={"Authorization": f"Bearer {jwt}"})
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total_count"] == 0
    assert data["facets"]["domains"] == {}


def test_evidence_search_filters():
    _seed_tenant_evidence("org_studio")
    jwt = create_test_jwt(tenant_id="org_studio", user_id="user_1", roles=["reviewer"])
    headers = {"Authorization": f"Bearer {jwt}"}

    # Free text search
    res = client.get("/api/v1/evidence/search?q=Vanguard", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1
    assert "Vanguard" in res.json()["items"][0]["snippet"]

    # Domain filter
    res_domain = client.get("/api/v1/evidence/search?domain=cocatalog.loc.gov", headers=headers)
    assert res_domain.status_code == 200
    assert len(res_domain.json()["items"]) == 1

    # Source type filter
    res_contract = client.get("/api/v1/evidence/search?source_type=private_contract", headers=headers)
    assert res_contract.status_code == 200
    assert len(res_contract.json()["items"]) == 1
    assert res_contract.json()["items"][0]["source_type"] == "private_contract"


def test_evidence_search_tenant_isolation():
    _seed_tenant_evidence("org_studio_a")
    jwt_b = create_test_jwt(tenant_id="org_studio_b", user_id="user_2", roles=["reviewer"])
    res = client.get("/api/v1/evidence/search", headers={"Authorization": f"Bearer {jwt_b}"})
    assert res.status_code == 200
    assert res.json()["items"] == []
    assert res.json()["total_count"] == 0


def test_evidence_detail_lookup_and_not_found():
    _seed_tenant_evidence("org_studio")
    jwt = create_test_jwt(tenant_id="org_studio", user_id="user_1", roles=["reviewer"])
    headers = {"Authorization": f"Bearer {jwt}"}

    res = client.get("/api/v1/evidence/ev_snap_snap_101", headers=headers)
    assert res.status_code == 200
    assert res.json()["item"]["evidence_id"] == "ev_snap_snap_101"
    assert res.json()["sha256_verified"] is True

    res_missing = client.get("/api/v1/evidence/ev_snap_nonexistent", headers=headers)
    assert res_missing.status_code == 404


def test_evidence_compare_with_server_redaction():
    _seed_tenant_evidence("org_studio")
    # 1. Non-legal role (e.g. analyst) -> Redaction applied
    jwt_analyst = create_test_jwt(tenant_id="org_studio", user_id="user_analyst", roles=["analyst"])
    res_analyst = client.get(
        "/api/v1/evidence/compare?claim_id=claim_music_01",
        headers={"Authorization": f"Bearer {jwt_analyst}"},
    )
    assert res_analyst.status_code == 200
    data_analyst = res_analyst.json()
    assert data_analyst["concordance_status"] == "SHIELDED"
    assert data_analyst["legal_shield_active"] is True
    clause_text = data_analyst["private_contract_clauses"][0]["text"]
    assert "[REDACTED COMPENSATION]" in clause_text
    assert "[REDACTED TAX ID]" in clause_text
    assert "$25,000" not in clause_text

    # 2. Legal role (reviewer / counsel) -> Full unredacted text
    jwt_counsel = create_test_jwt(tenant_id="org_studio", user_id="user_counsel", roles=["reviewer"])
    res_counsel = client.get(
        "/api/v1/evidence/compare?claim_id=claim_music_01",
        headers={"Authorization": f"Bearer {jwt_counsel}"},
    )
    assert res_counsel.status_code == 200
    assert "$25,000" in res_counsel.json()["private_contract_clauses"][0]["text"]
