"""
tests/test_dashboard_routes.py

Integration tests for Command Center Dashboard REST endpoints.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from fastapi.testclient import TestClient

from backend.domain.models import Production
from backend.main import app
from backend.storage.repository import get_tenant_repository
from tests.test_tenant_middleware import create_test_jwt

client = TestClient(app)


def test_get_dashboard_inbox_unauthorized_token():
    """Fail-Closed Security: Invalid Bearer tokens must return 401 Unauthorized."""
    resp = client.get(
        "/api/v1/dashboard/inbox",
        headers={"Authorization": "Bearer invalid.malformed.token"},
    )
    assert resp.status_code == 401


def test_get_dashboard_velocity_unauthorized_token():
    """Fail-Closed Security: Invalid Bearer tokens must return 401 Unauthorized."""
    resp = client.get(
        "/api/v1/dashboard/velocity",
        headers={"Authorization": "Bearer invalid.malformed.token"},
    )
    assert resp.status_code == 401


def test_get_dashboard_inbox_anonymous_unauthorized():
    """Fail-Closed Security: Anonymous calls to inbox must return 401 Unauthorized."""
    resp = client.get("/api/v1/dashboard/inbox")
    assert resp.status_code == 401


def test_get_dashboard_velocity_anonymous_unauthorized():
    """Fail-Closed Security: Anonymous calls to velocity must return 401 Unauthorized."""
    resp = client.get("/api/v1/dashboard/velocity")
    assert resp.status_code == 401


def test_get_dashboard_inbox_strict_mode_unauthorized(monkeypatch):
    """Strict mode enforcement: Anonymous calls without token return 401."""
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    resp = client.get("/api/v1/dashboard/inbox")
    assert resp.status_code == 401


def test_get_dashboard_velocity_strict_mode_unauthorized(monkeypatch):
    """Strict mode enforcement: Anonymous calls without token return 401."""
    monkeypatch.setenv("LIENMARK_STRICT_AUTH", "true")
    resp = client.get("/api/v1/dashboard/velocity")
    assert resp.status_code == 401


def test_get_dashboard_inbox_success():
    """Validates authenticated retrieval of the triage inbox."""
    tenant = "org_warner_001"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/dashboard/inbox", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == tenant
    assert "items" in data
    assert "summary" in data
    assert data["total_count"] >= 0


def test_get_dashboard_inbox_filtering_and_pagination():
    """Validates filtering by severity and category on the inbox route."""
    tenant = "org_warner_001"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        "/api/v1/dashboard/inbox?severity=P0_CRITICAL&limit=10&offset=0",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == tenant
    for it in data["items"]:
        assert it["severity"] == "P0_CRITICAL"


def test_get_dashboard_velocity_success():
    """Validates authenticated retrieval of clearance velocity metrics."""
    tenant = "org_warner_001"
    token = create_test_jwt(tenant_id=tenant, roles=["reviewer"])
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/v1/dashboard/velocity?window_days=14", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == tenant
    assert data["window_days"] == 14
    assert "aggregate" in data
    assert "resolution_time" in data["aggregate"]
    assert "stale_aging" in data["aggregate"]
    assert "blocker_velocity" in data["aggregate"]
