"""
tests/test_revision_audit_pipeline.py

Acceptance tests for revision audit pipeline using real mounted FastAPI application.
Proves: authenticated Producer -> immutable revision -> durable dispatch -> selective investigation -> persisted result.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
import os
import secrets
import hashlib
from fastapi.testclient import TestClient

os.environ["USE_LOCAL_STORAGE"] = "true"
from backend.main import app
from backend.storage.invite_store import get_invite_store
from backend.storage.revision_store import get_revision_store

client = TestClient(app)


def _get_auth_cookies(role: str = "producer", tenant_id: str = "org_cinema", prod_id: str = "prod_noir"):
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    get_invite_store().create_invite(h_token, role=role, tenant_id=tenant_id, production_id=prod_id)
    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    return res.cookies, res.json()["session_id"]


def test_complete_producer_audit_flow():
    cookies, sess_id = _get_auth_cookies("producer", "org_cinema", "prod_noir")

    payload = {
        "tenant_id": "org_cinema",
        "production_id": "prod_noir",
        "parent_revision_id": "v7",
        "idempotency_key": f"idem_{secrets.token_hex(8)}",
        "revised_uses": [],
    }
    res = client.post(
        "/api/revisions/audit",
        json=payload,
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert "audit_id" in data
    assert "revision_id" in data

    # Verify snapshot_0 was committed and readable from route
    snap_url = data["status_url"]
    snap_res = client.get(snap_url, cookies=cookies)
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert snap_data["snapshot_id"] == "snapshot_0"
    assert int(snap_data["telemetry"]["total_claims"]) >= 12


def test_single_claim_modification_selective_reopen():
    cookies, sess_id = _get_auth_cookies("producer", "org_cinema", "prod_noir")

    # Supply an altered version of Scene 42 Poster (escalated prominence)
    modified_use = {
        "use_id": "use_noir_poster_v8",
        "stable_lineage_key": "poster_noir_detective_magazine",
        "asset_name": "Scene 42 Noir Detective Magazine Poster",
        "version_id": "v8",
        "scene_or_timecode": "Scene 42 - 00:44:10",
        "context": "Detective reads headline; camera holds on logo.",
        "duration_or_prominence": "14s focal interaction",
        "context_hash": "altered_hash_v8",
    }
    payload = {
        "tenant_id": "org_cinema",
        "production_id": "prod_noir",
        "parent_revision_id": "v7",
        "idempotency_key": f"idem_{secrets.token_hex(8)}",
        "revised_uses": [modified_use],
    }
    res = client.post(
        "/api/revisions/audit",
        json=payload,
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert res.status_code == 202
    audit_id = res.json()["audit_id"]
    rev_id = res.json()["revision_id"]

    # Inspect snapshot
    snap_res = client.get(
        f"/api/tenants/org_cinema/productions/prod_noir/revisions/{rev_id}/audits/{audit_id}/snapshots/snapshot_0",
        cookies=cookies,
    )
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert int(snap_data["telemetry"]["reopened_count"]) >= 1


def test_external_evidence_drift_revalidation():
    cookies, sess_id = _get_auth_cookies("producer", "org_cinema", "prod_noir")
    res = client.post(
        "/api/revisions/rev_existing/revalidate-evidence",
        json={
            "tenant_id": "org_cinema",
            "production_id": "prod_noir",
            "target_key": "music_cue_midnight_serenade",
            "snapshot": {"source": "USCO Registry", "status": "adverse_claim"},
        },
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert res.status_code == 200
    assert res.json()["snapshot_id"] == "snapshot_0"
