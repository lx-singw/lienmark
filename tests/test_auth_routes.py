"""
tests/test_auth_routes.py

Acceptance tests exercising real authentication middleware, routes, and SessionStore.
Tests invite redemption, replay prevention, cookie signing/tampering, logout revocation, and RBAC.
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
from backend.storage.session_store import get_session_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_env():
    os.environ["USE_LOCAL_STORAGE"] = "true"
    os.environ["CLEARANCE_SQLITE_PATH"] = ".data/test_auth.sqlite3"


def test_invite_redemption_and_signed_cookie():
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invite_store = get_invite_store()
    invite_store.create_invite(h_token, role="producer", tenant_id="tenant_alpha", production_id="prod_alpha")

    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res.status_code == 200
    assert "lienmark_session" in res.cookies
    assert "." in res.cookies["lienmark_session"]

    # Verify session profile matches
    sess_res = client.get("/api/auth/session", cookies=res.cookies)
    assert sess_res.status_code == 200
    data = sess_res.json()
    assert data["role"] == "producer"
    assert data["tenant_id"] == "tenant_alpha"


def test_replay_prevention():
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invite_store = get_invite_store()
    invite_store.create_invite(h_token, role="producer", tenant_id="tenant_alpha", production_id="prod_alpha")

    res1 = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res1.status_code == 200

    # Replay must fail with 401
    res2 = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res2.status_code == 401


def test_tampered_cookie_rejected():
    tampered_cookies = {"lienmark_session": "sess_fake123.invalidsignature"}
    res = client.get("/api/auth/session", cookies=tampered_cookies)
    assert res.status_code == 401


def test_session_revocation_on_logout():
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    get_invite_store().create_invite(h_token, role="reviewer", tenant_id="tenant_beta", production_id="prod_beta")

    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res.status_code == 200
    cookies = res.cookies

    # Logout
    logout_res = client.post("/api/auth/logout", cookies=cookies)
    assert logout_res.status_code == 200

    # Request after logout must fail
    follow_up = client.get("/api/auth/session", cookies=cookies)
    assert follow_up.status_code == 401


def test_producer_decision_forbidden():
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    get_invite_store().create_invite(h_token, role="producer", tenant_id="tenant_test", production_id="prod_test")

    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res.status_code == 200
    cookies = res.cookies
    sess_id = res.json()["session_id"]

    # Producer attempting to sign off or reject on decisions endpoint
    dec_res = client.post(
        "/api/clearance/productions/prod_test/claims/claim_item_11/decision",
        json={
            "action": "sign_off",
            "revision_id": "revision_test",
            "expected_snapshot_id": "snapshot_test",
            "rationale": "Producer attempting illegal signoff",
        },
        cookies=cookies,
        headers={"X-CSRF-Token": sess_id},
    )
    assert dec_res.status_code == 403


def test_token_alias_redemption_and_replay():
    raw_token = f"inv_{secrets.token_urlsafe(32)}"
    h_token = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invite_store = get_invite_store()
    invite_store.create_invite(h_token, role="reviewer", tenant_id="tenant_gamma", production_id="prod_gamma")

    # Redeem using "token" instead of "invite_token"
    res1 = client.post("/api/auth/redeem-invite", json={"token": raw_token})
    assert res1.status_code == 200
    assert "lienmark_session" in res1.cookies
    assert res1.json()["role"] == "reviewer"

    # Verify server-side session persistence in SessionStore
    sess_id = res1.json()["session_id"]
    sess_rec = get_session_store().get_session(sess_id)
    assert sess_rec is not None
    assert sess_rec.tenant_id == "tenant_gamma"

    # Replay with "token" or "invite_token" must return 401
    res2 = client.post("/api/auth/redeem-invite", json={"token": raw_token})
    assert res2.status_code == 401


def test_invalid_and_empty_invite_rejection():
    # Non-existent token returns 401
    res_fake = client.post("/api/auth/redeem-invite", json={"token": "non_existent_token_123"})
    assert res_fake.status_code == 401

    # Empty payload returns 422
    res_empty = client.post("/api/auth/redeem-invite", json={})
    assert res_empty.status_code == 422
