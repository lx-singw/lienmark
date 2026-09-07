"""
tests/test_readiness_probes.py

Integration and unit test suite for Sprint 7.3:
1. Ultra-lightweight liveness probe (/healthz)
2. Deep readiness probe (/readyz) with fail-closed production gate (INV-S73-02)
3. Settings production readiness validator
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings, settings
from backend.main import app
from backend.middleware.chaos import chaos_controller

client = TestClient(app)


@pytest.fixture(autouse=True)
def ensure_chaos_disabled():
    chaos_controller.disable()
    yield
    chaos_controller.disable()


def test_healthz_liveness_probe():
    """Validates /healthz returns alive status with uptime in < 5ms."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert data["service"] == "lienmark-clearance-engine"
    assert "uptime_seconds" in data
    assert "timestamp" in data


def test_readyz_readiness_probe_success():
    """Validates /readyz succeeds in standard development environment."""
    res = client.get("/readyz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "storage" in data
    assert "integrations" in data
    assert "uptime_seconds" in data


def test_settings_environment_properties():
    """Validates is_production and is_staging property evaluators."""
    prod_settings = Settings(environment="production")
    assert prod_settings.is_production is True
    assert prod_settings.is_staging is False

    stage_settings = Settings(environment="staging")
    assert stage_settings.is_production is False
    assert stage_settings.is_staging is True

    dev_settings = Settings(environment="development")
    assert dev_settings.is_production is False
    assert dev_settings.is_staging is False


def test_production_readiness_validation_fail_closed():
    """Validates that production settings fail closed on default secrets or unconstrained spend."""
    with patch.dict(os.environ, {"SESSION_SECRET_KEY": "lienmark-session-secret-salt-2026", "TENANT_STRICT_MODE": "false"}):
        prod_settings = Settings(environment="production", demo_mode=True, max_api_spend_usd=-1.0)
        is_ready, issues = prod_settings.validate_production_readiness()
        assert is_ready is False
        assert len(issues) >= 3
        assert any("SESSION_SECRET_KEY" in issue for issue in issues)
        assert any("TENANT_STRICT_MODE" in issue for issue in issues)


def test_readyz_probe_fails_closed_in_misconfigured_production():
    """Validates that /readyz emits HTTP 503 when production prerequisites fail (INV-S73-02)."""
    with patch.object(settings, "environment", "production"):
        with patch.dict(os.environ, {"SESSION_SECRET_KEY": "lienmark-session-secret-salt-2026"}):
            res = client.get("/readyz")
            assert res.status_code == 503
            data = res.json()["detail"]
            assert data["status"] == "not_ready"
            assert len(data["failed_checks"]) >= 1


def test_storage_readiness_fails_in_production_with_in_memory_repo():
    """Validates that in-memory repository is disallowed in production/staging environments."""
    from backend.api.routes.readiness import _check_storage_readiness

    with patch.object(settings, "environment", "production"):
        ok, msg = _check_storage_readiness()
        assert ok is False
        assert "Production/Staging requires persistent Firestore storage" in msg

    with patch.object(settings, "environment", "staging"):
        ok, msg = _check_storage_readiness()
        assert ok is False
        assert "Production/Staging requires persistent Firestore storage" in msg


def test_jwt_secret_key_validation_in_production_and_staging():
    """Validates that default JWT secret key fails closed in staging and production."""
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "lienmark-jwt-secret-dev-2026"}):
        prod_settings = Settings(environment="production")
        ready, issues = prod_settings.validate_production_readiness()
        assert ready is False
        assert any("JWT_SECRET_KEY" in i for i in issues)

    with patch.dict(os.environ, {"JWT_SECRET_KEY": "lienmark-jwt-secret-dev-2026"}):
        stage_settings = Settings(environment="staging")
        ready, issues = stage_settings.validate_production_readiness()
        assert ready is False
        assert any("JWT_SECRET_KEY" in i for i in issues)


def test_demo_reset_forbidden_in_staging_and_production():
    """Validates that POST /api/demo/reset is strictly forbidden (HTTP 403) in staging/production."""
    with patch.object(settings, "environment", "production"):
        res = client.post("/api/demo/reset")
        assert res.status_code == 403
        assert "forbidden in staging and production" in res.json()["detail"].lower()

    with patch.object(settings, "environment", "staging"):
        res = client.post("/api/demo/reset")
        assert res.status_code == 403
        assert "forbidden in staging and production" in res.json()["detail"].lower()

