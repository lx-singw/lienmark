"""
tests/test_escalation_service.py

Test Suite for Autonomous Dispute & SLA Escalation Service:
1. Detection of unreviewed claims breaching 72-hour SLA
2. Bypassing recent unreviewed claims within SLA (< 72h)
3. Idempotency guarantee: repeat sweeps produce zero duplicate events (INV-S62-04)
4. Cryptographic ledger audit event emission (CLAIM_ESCALATED)
5. REST endpoints: POST /api/v1/escalation/sweep, GET /api/v1/escalation/status
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    InvestigationRun,
    Production,
    RunStatus,
    WorkflowReason,
)
from backend.main import app
from backend.services.escalation import DisputeEscalationService
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


def _seed_escalation_fixture(org_id: str, pid: str, run_id: str, age_hours: float, is_escalated: bool = False):
    repo = get_tenant_repository(org_id)
    repo.save_production(Production(production_id=pid, title="Thriller", organization_id=org_id))
    run = InvestigationRun(
        run_id=run_id, production_id=pid, organization_id=org_id,
        base_version_id="v7", target_version_id="v8", status=RunStatus.COMPLETED,
    )
    repo.save_run(run)
    repo.set_active_run_id(pid, run_id)

    ledger = CryptographicLedger(repository=repo)
    ledger.initialize_production_ledger(tenant_id=org_id, production_id=pid, actor_id="counsel")

    ts = (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat()
    claim = AtomicRightsClaim(
        claim_id=f"claim_age_{int(age_hours)}",
        production_id=pid,
        title="Unreviewed Trademark Prop",
        occurrence_id="occ_01",
        occurrence_lineage_id="occ_lineage_01",
        right_category="trademark",
        rights_subject="Vintage Soda Can",
        disposition=CensusDisposition.UNKNOWN,
        workflow_reason=WorkflowReason.NEWLY_DISCOVERED,
    )
    payload = claim.model_dump()
    payload["stable_lineage_key"] = f"key_prop_{int(age_hours)}"
    payload["use_id"] = claim.claim_id
    payload["updated_at"] = ts
    payload["created_at"] = ts
    if is_escalated:
        payload["metadata"] = {"is_escalated": True, "escalation_level": 2}
    repo.save_claim(pid, run_id, payload)
    return repo, ledger


def test_escalation_detects_overdue_claims():
    repo, ledger = _seed_escalation_fixture("org_sla", "prod_sla", "run_sla", age_hours=75.0)
    svc = DisputeEscalationService(repository=repo, ledger=ledger)

    result = svc.sweep_escalations(production_id="prod_sla", tenant_id="org_sla")
    assert result["evaluated_count"] == 1
    assert result["escalated_count"] == 1
    assert "claim_age_75" in result["breached_claim_ids"]

    # Verify claim state in repository
    claims = repo.list_claims("prod_sla", "run_sla")
    c_meta = claims[0].get("metadata", {})
    assert c_meta.get("is_escalated") is True
    assert c_meta.get("escalation_level") == 2

    # Verify CryptographicLedger block appended
    events = ledger.get_events(production_id="prod_sla")
    assert len(events) == 2  # Genesis + CLAIM_ESCALATED
    assert events[1].action_type == "CLAIM_ESCALATED"
    assert events[1].payload.get("escalation_level") == "P0_CRITICAL"


def test_escalation_ignores_recent_claims():
    repo, ledger = _seed_escalation_fixture("org_sla", "prod_sla", "run_sla", age_hours=24.0)
    svc = DisputeEscalationService(repository=repo, ledger=ledger)

    result = svc.sweep_escalations(production_id="prod_sla", tenant_id="org_sla")
    assert result["evaluated_count"] == 1
    assert result["escalated_count"] == 0
    assert result["breached_claim_ids"] == []

    # Verify no escalation block in ledger
    events = ledger.get_events(production_id="prod_sla")
    assert len(events) == 1  # Genesis only


def test_escalation_idempotent_sweep():
    repo, ledger = _seed_escalation_fixture("org_sla", "prod_sla", "run_sla", age_hours=80.0)
    svc = DisputeEscalationService(repository=repo, ledger=ledger)

    # First sweep: escalates
    r1 = svc.sweep_escalations(production_id="prod_sla", tenant_id="org_sla")
    assert r1["escalated_count"] == 1

    # Second sweep: idempotent no-op
    r2 = svc.sweep_escalations(production_id="prod_sla", tenant_id="org_sla")
    assert r2["escalated_count"] == 0

    # Events count in ledger remains exactly 2
    assert len(ledger.get_events(production_id="prod_sla")) == 2


def test_escalation_rest_sweep_and_status(monkeypatch):
    repo, ledger = _seed_escalation_fixture("org_rest", "prod_rest", "run_rest", age_hours=74.0)
    monkeypatch.setattr(app.state, "cryptographic_ledger", ledger, raising=False)
    jwt = create_test_jwt(tenant_id="org_rest", user_id="user_1", roles=["admin"])
    headers = {"Authorization": f"Bearer {jwt}"}

    # Trigger sweep via POST
    res_sweep = client.post("/api/v1/escalation/sweep?production_id=prod_rest", headers=headers)
    assert res_sweep.status_code == 200
    assert res_sweep.json()["escalated_count"] == 1

    # Check status via GET
    res_status = client.get("/api/v1/escalation/status?production_id=prod_rest", headers=headers)
    assert res_status.status_code == 200
    stat = res_status.json()
    assert stat["total_unreviewed"] == 1
    assert stat["overdue_72h_count"] == 1
    assert stat["compliance_rate"] == 0.0
