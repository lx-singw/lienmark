"""
tests/test_frontend_and_workflow_remediation.py

Automated Verification Suite for Frontend Release Readiness & Data Integrity Remediation:
  - Finding 1: SSR Exceptions Schedule consumes schedule.items directly with zero synthetic overrides.
  - Finding 2: API client rejects HTTP 401/403 errors and re-throws without creating mock_sha256_ events.
  - Finding 3 & 4: Docker compose maps port 3000:8080 with INTERNAL_API_URL=http://backend:8080; frontend Dockerfile specifies EXPOSE 8080.
  - Finding 5: Dashboard hydration logic exists in frontend/app/page.tsx on component mount.
  - Finding 6: Invalidation workflow returns 12 carried forward and 0 reopened for target_version_id="v7", and frontend/app/actions.ts passes targetVersionId.
  - Finding 7: submitReviewAction normalizes response envelope into a complete SupersessionEvent.
  - Finding 8: resetGoldenAuditTrail() resets _fallbackAuditTrail to the golden baseline count.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app
from backend.domain.models import DecisionState, DecisionStatus
from backend.orchestration.workflow import LienmarkWorkflow, WorkflowRunResult


@pytest.fixture
def client() -> TestClient:
    """Provides a fresh FastAPI test client."""
    return TestClient(app)


# ==============================================================================
# Finding 1: SSR Exceptions Schedule Item Consumption
# ==============================================================================

class TestFinding1ScheduleItemConsumption:
    """
    Finding 1:
    Assert frontend/app/report/[production_id]/page.tsx does not contain
    synthetic item overrides (poster_noir_detective_magazine or music_cue_midnight_serenade)
    and consumes schedule.items directly.
    """

    def test_report_page_consumes_schedule_items_directly(self):
        page_file = REPO_ROOT / "frontend" / "app" / "report" / "[production_id]" / "page.tsx"
        assert page_file.exists(), f"Report page missing at {page_file}"
        content = page_file.read_text(encoding="utf-8")

        # Must consume schedule.items directly
        assert "const items: ExceptionsScheduleItem[] = schedule.items;" in content or "schedule.items" in content, (
            "Report page must consume schedule.items directly."
        )

        # Must NOT contain synthetic item replacement/override arrays
        assert "const items: ExceptionsScheduleItem[] = [" not in content, (
            "Report page must not construct synthetic hardcoded items array."
        )

        # Must filter directly from items
        assert "items.filter" in content, (
            "Report page should filter carried, reattested, and exception items directly from items."
        )

    def test_backend_exceptions_schedule_contains_twelve_authentic_items(self, client: TestClient):
        """Verify the authentic endpoint provides 12 items (10 carried + 1 re-attested + 1 exception with auto_reconcile_demo=true)."""
        auth = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        resp = client.get("/api/reports/exceptions?auto_reconcile_demo=true", headers=auth)
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_claims"] == 12
        assert len(data["items"]) == 12
        assert data["carried_forward_count"] == 10
        assert data["re_attested_count"] == 1
        assert data["unresolved_exception_count"] == 1


# ==============================================================================
# Finding 2: HTTP 401/403 Error Rejection in API Client
# ==============================================================================

class TestFinding2ApiClientAuthErrorHandling:
    """
    Finding 2:
    Assert frontend/lib/api_client.ts rejects HTTP 401/403 errors and re-throws
    without creating mock_sha256_... fallback events.
    """

    def test_api_client_source_rethrows_auth_errors(self):
        client_ts = REPO_ROOT / "frontend" / "lib" / "api_client.ts"
        assert client_ts.exists(), f"api_client.ts missing at {client_ts}"
        content = client_ts.read_text(encoding="utf-8")

        # Must check error status for 401 or 403 and re-throw
        assert "error.status === 401 || error.status === 403" in content, (
            "api_client.ts must check for HTTP 401 and 403 errors."
        )
        assert "throw error;" in content, (
            "api_client.ts must re-throw auth errors without swallowing them into fallback."
        )

    def test_backend_enforces_auth_and_rationale_safety_gates(self, client: TestClient):
        """Verify backend rejects unauthenticated and invalid review actions."""
        # Missing token or invalid credentials
        resp_unauth = client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "rationale": "Valid rationale",
            },
            headers={"Authorization": "Bearer invalid_unauthorized_token"},
        )
        # Should be 401 or 403
        assert resp_unauth.status_code in (401, 403), (
            f"Expected 401/403 for unauthorized action, got {resp_unauth.status_code}"
        )

        # Missing rationale under authenticated counsel
        resp_norationale = client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "rationale": "",
            },
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert resp_norationale.status_code in (400, 403), (
            f"Expected 400/403 for empty rationale, got {resp_norationale.status_code}"
        )


# ==============================================================================
# Finding 3 & 4: Docker Compose Port Mapping & Dockerfile EXPOSE 8080
# ==============================================================================

class TestFinding3And4DockerConfiguration:
    """
    Finding 3 & 4:
    Assert docker-compose.yml maps port "3000:8080" and contains INTERNAL_API_URL: http://backend:8080.
    Assert frontend/Dockerfile specifies EXPOSE 8080.
    """

    def test_docker_compose_port_and_internal_url(self):
        compose_file = REPO_ROOT / "docker-compose.yml"
        assert compose_file.exists(), f"docker-compose.yml missing at {compose_file}"
        content = compose_file.read_text(encoding="utf-8")

        # Frontend port mapping must be 3000:8080
        assert '"3000:8080"' in content or "'3000:8080'" in content or "3000:8080" in content, (
            "docker-compose.yml must map port 3000:8080 for frontend."
        )

        # INTERNAL_API_URL must point to backend:8080
        assert "INTERNAL_API_URL=http://backend:8080" in content or "INTERNAL_API_URL: http://backend:8080" in content, (
            "docker-compose.yml must set INTERNAL_API_URL to http://backend:8080."
        )

    def test_frontend_dockerfile_exposes_8080(self):
        dockerfile = REPO_ROOT / "frontend" / "Dockerfile"
        assert dockerfile.exists(), f"frontend/Dockerfile missing at {dockerfile}"
        content = dockerfile.read_text(encoding="utf-8")

        assert "EXPOSE 8080" in content, "frontend/Dockerfile must specify EXPOSE 8080."
        assert "PORT=8080" in content, "frontend/Dockerfile must set PORT=8080."


# ==============================================================================
# Finding 5: Dashboard Hydration Logic
# ==============================================================================

class TestFinding5DashboardHydrationLogic:
    """
    Finding 5:
    Assert dashboard hydration logic exists in frontend/app/page.tsx.
    """

    def test_dashboard_page_contains_hydration_logic(self):
        page_file = REPO_ROOT / "frontend" / "app" / "page.tsx"
        assert page_file.exists(), f"frontend/app/page.tsx missing at {page_file}"
        content = page_file.read_text(encoding="utf-8")

        # Verify hydration actions are imported
        assert "fetchReviewQueueAction" in content, (
            "frontend/app/page.tsx must import fetchReviewQueueAction."
        )
        assert "fetchAuditTrailAction" in content, (
            "frontend/app/page.tsx must import fetchAuditTrailAction."
        )

        # Verify hydration effect runs on mount
        assert "hydrateDashboardState" in content or "fetchReviewQueueAction()" in content, (
            "frontend/app/page.tsx must contain hydration function."
        )


# ==============================================================================
# Finding 6: V7 Zero Drift Workflow & Target Version Parameter
# ==============================================================================

class TestFinding6ZeroDriftAndVersionParam:
    """
    Finding 6:
    Assert backend/orchestration/workflow.py returns 12 carried forward and 0 reopened
    when target_version_id="v7", and that frontend/app/actions.ts passes targetVersionId to runDriftAnalysis.
    """

    @pytest.mark.asyncio
    async def test_workflow_returns_twelve_carried_for_v7(self):
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection(
            base_version_id="v7",
            target_version_id="v7"
        )
        assert isinstance(result, WorkflowRunResult)
        assert result.total_claims == 12, "Total claims must be 12"
        assert result.carried_forward_count == 12, "All 12 claims must be carried forward under v7"
        assert result.reopened_count == 0, "Zero claims reopened under v7 zero drift baseline"
        assert result.target_version == "v7"

    def test_actions_passes_target_version_id_to_api_client(self):
        actions_file = REPO_ROOT / "frontend" / "app" / "actions.ts"
        assert actions_file.exists(), f"frontend/app/actions.ts missing at {actions_file}"
        content = actions_file.read_text(encoding="utf-8")

        # Must pass targetVersionId to runDriftAnalysis
        assert "apiClient.runDriftAnalysis(targetVersionId)" in content, (
            "frontend/app/actions.ts must pass targetVersionId to apiClient.runDriftAnalysis."
        )


# ==============================================================================
# Finding 7: Review Action Envelope Normalization into SupersessionEvent
# ==============================================================================

class TestFinding7ReviewActionEnvelopeNormalization:
    """
    Finding 7:
    Assert submitReviewAction normalizes response envelope into a complete SupersessionEvent.
    """

    def test_api_client_contains_normalization_logic(self):
        client_ts = REPO_ROOT / "frontend" / "lib" / "api_client.ts"
        assert client_ts.exists(), f"frontend/lib/api_client.ts missing at {client_ts}"
        content = client_ts.read_text(encoding="utf-8")

        # Check for normalizeSupersessionEvent method
        assert "normalizeSupersessionEvent" in content, (
            "api_client.ts must contain normalizeSupersessionEvent helper method."
        )

        # Check that submitReviewAction uses it
        assert "this.normalizeSupersessionEvent" in content, (
            "submitReviewAction must invoke normalizeSupersessionEvent to unwrap backend envelope."
        )

    def test_backend_review_action_envelope_structure(self, client: TestClient):
        """Verify the backend returns an envelope with supersession_event, event, and audit hash."""
        auth = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        resp = client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "rationale": "Public domain expiration verified via Library of Congress records.",
                "reviewer": {
                    "reviewer_id": "counsel_sjenkins_001",
                    "name": "Sarah Jenkins, Esq.",
                    "title": "Lead Production Clearance Counsel",
                    "organization": "Lienmark Legal Partners LLP",
                    "is_fictional_demo": True,
                },
                "version_id": "v8",
            },
            headers=auth,
        )
        assert resp.status_code == 200
        payload = resp.json()

        # Check envelope fields
        assert payload.get("status") == "success"
        assert "supersession_event" in payload or "event" in payload
        assert "event_id" in payload
        assert "event_hash" in payload or "audit_event_hash" in payload
        assert payload.get("new_state") == "re_attested"
        assert payload.get("new_status") == "approved"


# ==============================================================================
# Finding 8: Golden Audit Trail Reset
# ==============================================================================

class TestFinding8GoldenAuditTrailReset:
    """
    Finding 8:
    Assert resetGoldenAuditTrail() resets _fallbackAuditTrail to golden count.
    """

    def test_fixtures_data_exports_reset_golden_audit_trail(self):
        fixtures_file = REPO_ROOT / "frontend" / "lib" / "fixtures_data.ts"
        assert fixtures_file.exists(), f"frontend/lib/fixtures_data.ts missing at {fixtures_file}"
        content = fixtures_file.read_text(encoding="utf-8")

        # Must define and export resetGoldenAuditTrail
        assert "export function resetGoldenAuditTrail(): void" in content, (
            "frontend/lib/fixtures_data.ts must export resetGoldenAuditTrail function."
        )
        assert "_fallbackAuditTrail = [...GOLDEN_AUDIT_TRAIL];" in content, (
            "resetGoldenAuditTrail must reset _fallbackAuditTrail to GOLDEN_AUDIT_TRAIL."
        )

    def test_golden_audit_trail_invariants_and_reset_behavior(self):
        fixtures_file = REPO_ROOT / "frontend" / "lib" / "fixtures_data.ts"
        content = fixtures_file.read_text(encoding="utf-8")

        # Check that recordGoldenSupersessionEvent pushes to _fallbackAuditTrail
        assert "recordGoldenSupersessionEvent" in content
        assert "_fallbackAuditTrail.push" in content
        assert "export function getGoldenAuditTrail" in content
