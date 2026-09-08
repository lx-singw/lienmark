"""
tests/test_revision_worker_durability.py

Durability and recovery tests exercising real RevisionStore, mounted application routes,
fencing token enforcement, idempotency hash conflict rejection, and sweeper recovery.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
import os
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

os.environ["USE_LOCAL_STORAGE"] = "true"
from backend.main import app
from backend.storage.revision_store import get_revision_store
from backend.storage.invite_store import get_invite_store
from backend.domain.revision_models import RevisionRecord, RevisionAuditDispatch
from backend.orchestration.revision_audit_pipeline import RevisionAuditPipelineService

client = TestClient(app)


def _get_auth_cookies(role: str = "producer", tenant_id: str = "org_durable", prod_id: str = "prod_durable"):
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    get_invite_store().create_invite(h_token, role=role, tenant_id=tenant_id, production_id=prod_id)
    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    return res.cookies, res.json()["session_id"]


def test_idempotency_key_identical_and_modified_payload():
    cookies, sess_id = _get_auth_cookies("producer", "org_durable", "prod_durable")
    shared_key = f"idem_fixed_{secrets.token_hex(6)}"

    payload1 = {
        "tenant_id": "org_durable",
        "production_id": "prod_durable",
        "parent_revision_id": "v7",
        "idempotency_key": shared_key,
        "revised_uses": [{"name": "Asset A"}],
    }
    # First submission
    res1 = client.post("/api/revisions/audit", json=payload1, cookies=cookies, headers={"X-CSRF-Token": sess_id})
    assert res1.status_code == 202
    audit_id_1 = res1.json()["audit_id"]

    # Identical replay returns existing dispatch (idempotent)
    res2 = client.post("/api/revisions/audit", json=payload1, cookies=cookies, headers={"X-CSRF-Token": sess_id})
    assert res2.status_code == 202
    assert res2.json()["audit_id"] == audit_id_1

    # Modified payload with same idempotency key must be rejected with 409 Conflict
    payload_modified = dict(payload1)
    payload_modified["revised_uses"] = [{"name": "Asset Altered"}]
    res3 = client.post("/api/revisions/audit", json=payload_modified, cookies=cookies, headers={"X-CSRF-Token": sess_id})
    assert res3.status_code == 409


def test_fencing_token_rejects_stale_worker():
    store = get_revision_store()
    rev_id = f"rev_{secrets.token_hex(4)}"
    audit_id = f"audit_{secrets.token_hex(4)}"

    rec = RevisionRecord(
        revision_id=rev_id, created_at=datetime.now(timezone.utc),
        user_provenance="test", tenant_id="t1", production_id="p1", parent_baseline_version_id="v7",
    )
    disp = RevisionAuditDispatch(
        audit_id=audit_id, revision_id=rev_id, status="QUEUED",
        fencing_token=0, idempotency_key=f"idem_{audit_id}", payload_hash="hash1", retry_count=0,
    )
    store.save_revision_and_dispatch(rec, disp)

    pipeline = RevisionAuditPipelineService(store=store)
    token_1 = pipeline.acquire_lease("t1", "p1", audit_id)
    assert token_1 == 1

    # Worker 2 acquires lease before Worker 1 finishes (simulating network partition or restart)
    token_2 = pipeline.acquire_lease("t1", "p1", audit_id)
    assert token_2 == 2

    # Worker 1's token is now stale and rejected
    assert pipeline.validate_fencing_token("t1", "p1", audit_id, token_1) is False
    assert pipeline.validate_fencing_token("t1", "p1", audit_id, token_2) is True


def test_recovery_sweeper_reclaims_stranded_dispatch():
    store = get_revision_store()
    rev_id = f"rev_{secrets.token_hex(4)}"
    audit_id = f"audit_stranded_{secrets.token_hex(4)}"

    rec = RevisionRecord(
        revision_id=rev_id, created_at=datetime.now(timezone.utc),
        user_provenance="test", tenant_id="t_sweep", production_id="p_sweep", parent_baseline_version_id="v7",
    )
    # Simulate a crashed worker with an expired lease
    disp = RevisionAuditDispatch(
        audit_id=audit_id, revision_id=rev_id, status="PROCESSING",
        lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        fencing_token=1, idempotency_key=f"idem_{audit_id}", payload_hash="hash_s", retry_count=0,
    )
    store.save_revision_and_dispatch(rec, disp)

    cookies, sess_id = _get_auth_cookies("producer", "t_sweep", "p_sweep")
    res = client.post(
        "/api/tasks/recovery/sweep",
        json={"tenant_id": "t_sweep", "production_id": "p_sweep"},
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert audit_id in data["recovered_audits"]

    # Verify status is now COMPLETED
    updated = store.get_dispatch("t_sweep", "p_sweep", audit_id)
    assert updated.status == "COMPLETED"
