"""
test_staging_cutover.py

Sprint 7.3: Staging Deployment, User Acceptance Testing & Operational Cutover.
Strict invariants: files <= 250 lines, functions <= 40 lines, zero mock fallbacks.
"""

import json
import os
import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.config.settings import Settings, settings
from backend.main import app
from backend.middleware.chaos import chaos_controller
from backend.orchestration.workflow import LienmarkWorkflow

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_system_state():
    """Ensures chaos injection is disabled and environment is clean before each test."""
    chaos_controller.disable()
    yield
    chaos_controller.disable()


def test_liveness_healthz_fast_response():
    """Validates GET /healthz responds in < 20ms with status alive."""
    client.get("/healthz")  # Warmup routing table
    start = time.perf_counter()
    res = client.get("/healthz")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "alive"
    assert data["service"] == "lienmark-clearance-engine"
    assert "uptime_seconds" in data
    assert elapsed_ms < 20.0, f"Liveness probe exceeded 20ms SLA: {elapsed_ms:.2f}ms"


def test_readiness_readyz_healthy_state():
    """Validates GET /readyz returns 200 with all dependency checks healthy."""
    res = client.get("/readyz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    checks = data.get("dependencies") or data.get("checks")
    assert isinstance(checks, dict)
    for dep in ("firestore", "settings", "parallel_search", "gemini"):
        assert dep in checks, f"Missing dependency probe: {dep}"
        assert checks[dep] in ("ready", "valid", "connected")


def test_readiness_readyz_degraded_returns_503():
    """Validates simulating an unready dependency fails-closed with HTTP 503."""
    with patch("backend.api.routes.readiness._check_storage_readiness", return_value=(False, "Firestore timeout")):
        res = client.get("/readyz")
        assert res.status_code == 503
        detail = res.json().get("detail", {})
        assert detail.get("status") == "not_ready"
        assert any("Firestore" in chk for chk in detail.get("failed_checks", []))

    with patch("backend.api.routes.readiness._check_credentials_readiness", return_value={"gemini": "degraded"}):
        res = client.get("/readyz")
        assert res.status_code == 503
        assert res.json().get("detail", {}).get("status") == "not_ready"


def test_production_settings_validation_rules():
    """Validates settings.validate_production_readiness flags default secrets and strict mode."""
    with patch.dict(os.environ, {"SESSION_SECRET_KEY": "lienmark-session-secret-salt-2026", "TENANT_STRICT_MODE": "false"}):
        bad_cfg = Settings(environment="production", demo_mode=True, max_api_spend_usd=-1.0)
        is_ready, issues = bad_cfg.validate_production_readiness()
        assert is_ready is False
        assert any("SESSION_SECRET_KEY" in issue for issue in issues)
        assert any("TENANT_STRICT_MODE" in issue for issue in issues)
        assert any("DEMO_MODE" in issue for issue in issues)

    with patch.dict(os.environ, {
        "SESSION_SECRET_KEY": "prod-crypto-salt-vault-secure-991",
        "JWT_SECRET_KEY": "prod-jwt-secure-token-vault-992",
        "TENANT_STRICT_MODE": "true",
    }):
        good_cfg = Settings(environment="production", demo_mode=False, max_api_spend_usd=100.0)
        is_ready, issues = good_cfg.validate_production_readiness()
        assert is_ready is True
        assert len(issues) == 0


def test_frontend_security_headers_configured():
    """Verifies Next.js enterprise security headers in frontend/next.config.js."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    next_cfg = os.path.join(base_dir, "frontend", "next.config.js")
    assert os.path.isfile(next_cfg), f"next.config.js missing at {next_cfg}"
    with open(next_cfg, "r", encoding="utf-8") as f:
        content = f.read()

    required_headers = [
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ]
    for hdr in required_headers:
        assert hdr in content, f"Header {hdr} missing from next.config.js"


@pytest.mark.asyncio
async def test_end_to_end_acceptance_workflow_under_15s():
    """Runs LienmarkWorkflow on golden baseline V7 -> V8 and asserts execution < 15s."""
    workflow = LienmarkWorkflow()
    start_time = time.perf_counter()
    result = await workflow.execute_drift_detection()
    duration_s = time.perf_counter() - start_time

    assert duration_s < 15.0, f"Workflow execution exceeded 15s SLA: {duration_s:.2f}s"
    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2
    assert "poster_noir_detective_magazine" in result.counsel_briefings
    assert "music_cue_midnight_serenade" in result.counsel_briefings


def test_final_release_metadata_and_invariants():
    """Verifies release version 1.0.0 and roadmap invariants across tiers."""
    assert app.version == "1.0.0"

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg_json = os.path.join(base_dir, "frontend", "package.json")
    with open(pkg_json, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert pkg_data.get("version") == "1.0.0"

    roadmap_file = os.path.join(base_dir, "docs", "roadmap", "01_exhaustive_engineering_build_roadmap.md")
    with open(roadmap_file, "r", encoding="utf-8") as f:
        roadmap_content = f.read()
    assert "v1.0.0-production" in roadmap_content
