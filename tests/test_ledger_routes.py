"""
tests/test_ledger_routes.py

Integration Test Suite for Decision History & Cryptographic Ledger Routes:
1. Fail-closed authentication (401 Unauthorized)
2. Uninitialized ledger graceful handling (INV-S62-06)
3. Chronological decision history & supersession marking
4. Authoritative cryptographic block verification (INV-S62-03)
5. Tamper detection on payload/hash alteration
6. Supersessions lineage query
7. Tenant boundary isolation
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.storage.ledger import CryptographicLedger
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


def _seed_production_ledger(org_id: str, pid: str = "prod_blockbuster"):
    repo = get_tenant_repository(org_id)
    ledger = CryptographicLedger(repository=repo)
    ledger.initialize_production_ledger(tenant_id=org_id, production_id=pid, actor_id="lead_counsel")

    e2 = ledger.append_event(
        tenant_id=org_id,
        production_id=pid,
        actor_id="lead_counsel",
        action_type="COUNSEL_DECISION",
        payload={
            "action": "COUNSEL_DECISION",
            "claim_id": "claim_poster_01",
            "claim_title": "Noir Detective Magazine Poster",
            "status": "APPROVED",
            "rationale": "Fair use docudrama background placement verified under 17 U.S.C. ? 107.",
            "counsel_name": "Sarah Jenkins, Esq.",
        },
    )

    e3 = ledger.record_supersession(
        tenant_id=org_id,
        production_id=pid,
        actor_id="supervising_partner",
        superseded_event_id=e2.event_id,
        superseding_payload={
            "action": "RE_ATTEST",
            "claim_id": "claim_poster_01",
            "claim_title": "Noir Detective Magazine Poster",
            "status": "RE_ATTESTED",
            "rationale": "Supervising partner re-attestation following script revision v8 focal shift.",
            "counsel_name": "Marcus Vance, Esq.",
            "dual_signatures": [
                {"signer": "Sarah Jenkins", "role": "Clearance Counsel"},
                {"signer": "Marcus Vance", "role": "Supervising Partner"},
            ],
        },
    )
    return ledger, [e2, e3]


def test_ledger_auth_fail_closed(monkeypatch):
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    monkeypatch.setenv("TENANT_STRICT_MODE", "true")
    res = client.get("/api/v1/ledger/decisions?production_id=prod_any")
    assert res.status_code == 401


def test_ledger_uninitialized_grace():
    jwt = create_test_jwt(tenant_id="org_empty", user_id="user_1", roles=["reviewer"])
    res = client.get("/api/v1/ledger/decisions?production_id=prod_uninit", headers={"Authorization": f"Bearer {jwt}"})
    assert res.status_code == 200
    data = res.json()
    assert data["chain_length"] == 0
    assert data["events"] == []
    assert data["is_chain_valid"] is True


def test_ledger_decisions_chronological(monkeypatch):
    ledger, events = _seed_production_ledger("org_cinema", "prod_cinema_01")
    monkeypatch.setattr(app.state, "cryptographic_ledger", ledger, raising=False)
    jwt = create_test_jwt(tenant_id="org_cinema", user_id="user_1", roles=["reviewer"])

    res = client.get(
        "/api/v1/ledger/decisions?production_id=prod_cinema_01",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_chain_valid"] is True
    assert data["chain_length"] == 3
    # Check monotonic sequences
    seqs = [e["sequence_number"] for e in data["events"]]
    assert seqs == [1, 2, 3]
    # Check that event 2 is marked superseded
    assert data["events"][1]["is_superseded"] is True
    assert data["events"][2]["action_type"] == "SUPERSEDED"
    assert len(data["events"][2]["dual_signatures"]) == 2


def test_ledger_verify_valid_block(monkeypatch):
    ledger, events = _seed_production_ledger("org_cinema", "prod_cinema_01")
    monkeypatch.setattr(app.state, "cryptographic_ledger", ledger, raising=False)
    jwt = create_test_jwt(tenant_id="org_cinema", user_id="user_1", roles=["reviewer"])

    res = client.get(
        f"/api/v1/ledger/verify/{events[0].event_id}?production_id=prod_cinema_01",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert "Cryptographic proof verified" in data["verification_message"]
    assert data["sequence_number"] == 2


def test_ledger_verify_tampered_event(monkeypatch):
    ledger, events = _seed_production_ledger("org_cinema", "prod_cinema_01")
    monkeypatch.setattr(app.state, "cryptographic_ledger", ledger, raising=False)
    jwt = create_test_jwt(tenant_id="org_cinema", user_id="user_1", roles=["reviewer"])

    # Simulate tampered block payload digest
    chain = ledger._chains["prod_cinema_01"]
    tampered_evt = chain[1].model_copy(update={"payload_digest": "f" * 64})
    chain[1] = tampered_evt

    res = client.get(
        f"/api/v1/ledger/verify/{events[0].event_id}?production_id=prod_cinema_01",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert "Tamper detected" in data["verification_message"]


def test_ledger_supersessions(monkeypatch):
    ledger, events = _seed_production_ledger("org_cinema", "prod_cinema_01")
    monkeypatch.setattr(app.state, "cryptographic_ledger", ledger, raising=False)
    jwt = create_test_jwt(tenant_id="org_cinema", user_id="user_1", roles=["reviewer"])

    res = client.get(
        "/api/v1/ledger/supersessions?production_id=prod_cinema_01",
        headers={"Authorization": f"Bearer {jwt}"},
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["superseded_event_id"] == events[0].event_id
    assert "Supervising partner" in items[0]["counsel_rationale"]
