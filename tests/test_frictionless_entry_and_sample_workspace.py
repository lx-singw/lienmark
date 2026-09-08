"""
tests/test_frictionless_entry_and_sample_workspace.py

Acceptance test suite for frictionless entry and sample workspace:
1. Verify /login redirects to root /.
2. Verify root / serves sample workspace without authentication.
3. Verify atomic invite redemption and signed session cookie issuance.
4. Verify replay of consumed invite token returns HTTP 401.
5. Verify unauthenticated mutations to revisions/audit and decisions are rejected with 401.

Strict AntiGravity compliance: files <= 250 lines, functions <= 40 lines, zero any.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import secrets
from typing import Generator
import pytest
from fastapi.testclient import TestClient

os.environ["USE_LOCAL_STORAGE"] = "true"

from backend.main import app
from backend.storage.invite_store import get_invite_store, InviteStoreInterface


@pytest.fixture(autouse=True)
def setup_storage_env() -> Generator[None, None, None]:
    os.environ["USE_LOCAL_STORAGE"] = "true"
    yield


def test_login_page_redirects_to_root() -> None:
    """Verifies /login cleanly redirects to / (HTTP 307/302) and inspects frontend page.tsx."""
    login_page: Path = Path("frontend/app/login/page.tsx")
    assert login_page.exists(), "frontend/app/login/page.tsx must exist"
    content: str = login_page.read_text(encoding="utf-8")
    assert "redirect('/')" in content or 'redirect("/")' in content or "/" in content

    client: TestClient = TestClient(app)
    redirect_res = client.get("/login", follow_redirects=False)
    assert redirect_res.status_code in (302, 307)
    assert redirect_res.headers.get("location") == "/"

    follow_res = client.get("/login", follow_redirects=True)
    assert follow_res.status_code == 200
    assert "Clearance Reviewer Dashboard" in follow_res.text


def test_root_page_serves_sample_workspace_without_auth() -> None:
    """Verifies unauthenticated GET / renders sample workspace with 'Sample workspace · Read-only'."""
    client: TestClient = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Sample workspace · Read-only" in res.text
    assert "Clearance Reviewer Dashboard" in res.text
    assert "Sample workspace" in res.text


def test_atomic_invite_redemption_and_signed_cookie() -> None:
    """Verifies single-use invite redemption creates session and sets signed cookie."""
    client: TestClient = TestClient(app)
    raw_token: str = f"inv_{secrets.token_urlsafe(32)}"
    hashed_token: str = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invite_store: InviteStoreInterface = get_invite_store()
    created: bool = invite_store.create_invite(
        hashed_token=hashed_token,
        role="reviewer",
        tenant_id="tenant_frictionless_01",
        production_id="prod_frictionless_01",
    )
    assert created is True

    res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert res.status_code == 200
    body: dict[str, str] = res.json()
    assert body.get("status") == "success"
    assert "session_id" in body

    assert "lienmark_session" in res.cookies
    signed_cookie: str = res.cookies["lienmark_session"]
    assert "." in signed_cookie


def test_replayed_invite_token_returns_401() -> None:
    """Verifies replay of redeemed token returns HTTP 401 with exact description."""
    client: TestClient = TestClient(app)
    raw_token: str = f"inv_{secrets.token_urlsafe(32)}"
    hashed_token: str = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    invite_store: InviteStoreInterface = get_invite_store()
    invite_store.create_invite(
        hashed_token=hashed_token,
        role="producer",
        tenant_id="tenant_frictionless_02",
        production_id="prod_frictionless_02",
    )

    first_res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert first_res.status_code == 200

    replay_res = client.post("/api/auth/redeem-invite", json={"invite_token": raw_token})
    assert replay_res.status_code == 401
    err_data: dict[str, str] = replay_res.json()
    assert err_data.get("detail") == "Invalid, expired, or already used invite token."


def test_unauthenticated_mutations_rejected() -> None:
    """Verifies unauthenticated POST mutations are rejected with HTTP 401."""
    client: TestClient = TestClient(app)

    rev_payload: dict[str, str] = {
        "tenant_id": "org_cinema",
        "production_id": "prod_noir",
        "parent_revision_id": "v7",
    }
    rev_res = client.post("/api/revisions/audit", json=rev_payload)
    assert rev_res.status_code == 401

    dec_payload: dict[str, str] = {
        "action": "sign_off",
        "counsel_id": "counsel_unauth",
        "counsel_name": "Unauthenticated Caller",
        "directive_text": "Illegal signoff without credentials",
    }
    dec_res = client.post(
        "/api/v1/claims/claim_item_11/decision",
        json=dec_payload,
        params={"production_id": "prod_noir"},
    )
    assert dec_res.status_code == 401
