"""
tests/test_recording_build.py

Sprint 6B Task 2: Recording Build & Preflight Verifier Automated Test Suite
In accordance with Sprint 6B in docs/winning/04-build-roadmap.md (§11, Sprint 6B):
  "Seed/reset mechanism. Stable demo account. Clean browser profile and notification suppression.
   Large readable UI. Backup hosted deployment. Preflight API quotas and credentials.
   Controlled fictional search scenario that still performs real Parallel runtime calls."

Exhaustive verification suite:
1. Test Demo Reset Endpoint:
   - Asserts POST /api/demo/reset clears prior review mutations and restores 12 V7 baseline approvals.
2. Test Demo Seed Endpoint:
   - Asserts POST /api/demo/seed?mode=drifted and POST /api/demo/seed?mode=resolved transition
     state correctly with exact claim counts (10 carried / 2 stale; 10 carried / 1 re-attested / 1 exception).
3. Test Clean Session State Isolation:
   - Asserts that running reset multiple times is idempotent and produces zero state leakage.
4. Test Stable Demo Account Authentication:
   - Asserts demo counsel token 'sarah_jenkins_token_2026' succeeds on mutating endpoints
     while unauthorized requests are handled properly with HTTP 401/403.
5. Test Controlled Fictional Search Scenario:
   - Asserts Item 11 and Item 12 queries return attributable evidence with valid URLs and source titles.
6. Test Preflight Script Report:
   - Asserts scripts/preflight_recording.py executes and produces valid JSON report at
     output/recording_preflight_report.json with status: "READY_FOR_RECORDING".

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.domain.models import (
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    ReviewAction,
    ReviewerIdentity,
    ReviewActionRequest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    counsel_checkpoint_manager,
)
from backend.core.security import (
    VALID_DEMO_COUNSEL_TOKENS,
    mask_credential,
    get_masked_preview,
)
from backend.services.parallel_service import ParallelSearchService
from backend.main import (
    app,
    _counsel_reattestations,
)
from scripts.preflight_recording import RecordingPreflightRunner, REPORT_FILE


@pytest.fixture
def client() -> TestClient:
    """Provides a fresh FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_state():
    """Guarantees pristine session state before and after each test."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


# ==============================================================================
# 1. TEST DEMO RESET ENDPOINT
# ==============================================================================

class TestDemoResetEndpoint:
    """
    Asserts POST /api/demo/reset clears prior review mutations and restores 12 V7 baseline approvals.
    """

    def test_demo_reset_clears_mutations_and_restores_twelve_baseline_approvals(self, client: TestClient):
        # 1. First inject review mutations via seed?mode=resolved
        auth_header = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        seed_resp = client.post("/api/demo/seed?mode=resolved", headers=auth_header)
        assert seed_resp.status_code == 200
        assert seed_resp.json()["re_attested_count"] == 1
        assert len(_counsel_reattestations) >= 1
        assert len(counsel_checkpoint_manager.get_audit_trail()) >= 1

        # 2. Call POST /api/demo/reset
        reset_resp = client.post("/api/demo/reset", headers=auth_header)
        assert reset_resp.status_code == 200
        data = reset_resp.json()

        # 3. Assert baseline invariant properties
        assert data.get("status") in ("reset_successful", "RESET_SUCCESS")
        assert data.get("mode") == "baseline"
        assert data.get("total_claims") == 12
        assert data.get("approved_count") == 12
        assert data.get("stale_count") == 0
        assert data.get("reopened_count") == 0
        assert data.get("exceptions_count") == 0
        assert data.get("re_attested_count") == 0
        assert data.get("mutations_count") == 0
        assert data.get("counsel_audit_trail_count") == 0
        assert data.get("active_reviewer") == "Sarah Jenkins, Esq."

        # 4. Verify all 12 decisions have APPROVED status
        decisions = data.get("decisions", [])
        assert len(decisions) == 12
        for dec in decisions:
            assert dec["status"] == "APPROVED"
            assert "stable_lineage_key" in dec
            assert "decision_id" in dec

        # 5. Verify GET /api/demo/state also reflects baseline
        state_resp = client.get("/api/demo/state")
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert state_data["mode"] == "baseline"
        assert state_data["approved_count"] == 12
        assert state_data["stale_count"] == 0


# ==============================================================================
# 2. TEST DEMO SEED ENDPOINT
# ==============================================================================

class TestDemoSeedEndpoint:
    """
    Asserts POST /api/demo/seed?mode=drifted and POST /api/demo/seed?mode=resolved
    transition state correctly with exact claim counts.
    """

    def test_demo_seed_drifted_state(self, client: TestClient):
        auth_header = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        resp = client.post("/api/demo/seed?mode=drifted", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()

        # Exact mathematical counts for drifted state
        assert data.get("status") in ("seeded_drifted", "SEED_SUCCESS")
        assert data.get("mode") == "drifted"
        assert data.get("total_claims") == 12
        assert data.get("carried_count") == 10
        assert data.get("approved_count") == 10
        assert data.get("stale_count") == 2
        assert data.get("reopened_count") == 2
        assert data.get("needs_review_count") == 2
        assert data.get("exceptions_count") == 0
        assert data.get("re_attested_count") == 0

        # Verify the 2 reopened items are Item 11 (poster) and Item 12 (music cue)
        decisions = {d["stable_lineage_key"]: d for d in data.get("decisions", [])}
        assert len(decisions) == 12

        poster_dec = decisions["poster_noir_detective_magazine"]
        assert poster_dec["status"] == "NEEDS_REVIEW"
        assert poster_dec["state"] == "STALE"

        music_dec = decisions["music_cue_midnight_serenade"]
        assert music_dec["status"] == "NEEDS_REVIEW"
        assert music_dec["state"] == "STALE"

        # Verify other 10 claims are CARRIED_FORWARD and APPROVED
        carried_keys = [
            "prop_vintage_telephone", "poster_paris_expo_1937", "car_ford_sedan_1949",
            "trademark_acme_coffee", "artwork_abstract_expressionist", "likeness_mayor_cameo",
            "architecture_tribunal_facade", "text_headline_gazette", "wardrobe_fedora_brand",
            "music_incidental_radio_static"
        ]
        for k in carried_keys:
            assert decisions[k]["status"] == "APPROVED"
            assert decisions[k]["state"] == "CARRIED_FORWARD"

        # Verify GET /api/demo/state reflects drifted state
        state_resp = client.get("/api/demo/state")
        assert state_resp.status_code == 200
        sdata = state_resp.json()
        assert sdata["mode"] == "drifted"
        assert sdata["carried_count"] == 10
        assert sdata["stale_count"] == 2

    def test_demo_seed_resolved_state(self, client: TestClient):
        auth_header = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        resp = client.post("/api/demo/seed?mode=resolved", headers=auth_header)
        assert resp.status_code == 200
        data = resp.json()

        # Exact mathematical counts for resolved state: 10 carried, 1 re-attested, 1 exception
        assert data.get("status") in ("seeded_resolved", "SEED_SUCCESS")
        assert data.get("mode") == "resolved"
        assert data.get("total_claims") == 12
        assert data.get("carried_count") == 10
        assert data.get("re_attested_count") == 1
        assert data.get("approved_count") == 11  # 10 carried + 1 re-attested
        assert data.get("stale_count") == 0
        assert data.get("needs_review_count") == 0
        assert data.get("exceptions_count") == 1
        assert data.get("unresolved_exception_count") == 1

        # Check Item 11 is re-attested and Item 12 is exception
        decisions = {d["stable_lineage_key"]: d for d in data.get("decisions", [])}
        assert len(decisions) == 12

        poster_dec = decisions["poster_noir_detective_magazine"]
        assert poster_dec["status"] == "APPROVED"
        assert poster_dec["state"] == "RE_ATTESTED"
        assert "public domain" in poster_dec["rationale"].lower()

        music_dec = decisions["music_cue_midnight_serenade"]
        assert music_dec["status"] in ("REJECTED", "NEEDS_REVIEW")
        assert music_dec["state"] == "EXCEPTION"
        assert "vanguard media" in music_dec["rationale"].lower()

        # Verify audit trail has recorded events
        assert len(counsel_checkpoint_manager.get_audit_trail()) == 2

    def test_demo_seed_invalid_mode_rejected(self, client: TestClient):
        auth_header = {"Authorization": "Bearer sarah_jenkins_token_2026"}
        resp = client.post("/api/demo/seed?mode=invalid_state_xyz", headers=auth_header)
        assert resp.status_code == 400
        assert "invalid demo seed mode" in resp.json()["detail"].lower()


# ==============================================================================
# 3. TEST CLEAN SESSION STATE ISOLATION & IDEMPOTENCY
# ==============================================================================

class TestCleanSessionStateIsolation:
    """
    Asserts that running reset multiple times is idempotent and produces zero state leakage.
    """

    def test_multiple_resets_are_idempotent_and_leak_free(self, client: TestClient):
        auth_header = {"Authorization": "Bearer sarah_jenkins_token_2026"}

        # Run 5 consecutive resets
        for i in range(5):
            resp = client.post("/api/demo/reset", headers=auth_header)
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "baseline"
            assert data["approved_count"] == 12
            assert data["stale_count"] == 0
            assert data["exceptions_count"] == 0
            assert data["mutations_count"] == 0
            assert data["counsel_audit_trail_count"] == 0

        # Advance state to resolved (adds audit events and reattestations)
        client.post("/api/demo/seed?mode=resolved", headers=auth_header)
        assert len(_counsel_reattestations) == 2
        assert len(counsel_checkpoint_manager.get_audit_trail()) == 2

        # Reset again: verify complete eradication of lingering state
        reset_resp = client.post("/api/demo/reset", headers=auth_header)
        assert reset_resp.status_code == 200
        clean_data = reset_resp.json()

        assert clean_data["approved_count"] == 12
        assert clean_data["stale_count"] == 0
        assert clean_data["exceptions_count"] == 0
        assert clean_data["mutations_count"] == 0
        assert len(_counsel_reattestations) == 0
        assert len(counsel_checkpoint_manager.get_audit_trail()) == 0


# ==============================================================================
# 4. TEST STABLE DEMO ACCOUNT AUTHENTICATION
# ==============================================================================

class TestStableDemoAccountAuthentication:
    """
    Asserts demo counsel token 'sarah_jenkins_token_2026' succeeds on mutating endpoints
    while unauthorized requests are handled properly with HTTP 401/403.
    """

    def test_sarah_jenkins_token_succeeds_on_mutating_endpoints(self, client: TestClient):
        token = "sarah_jenkins_token_2026"
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Reset
        r1 = client.post("/api/demo/reset", headers=auth_headers)
        assert r1.status_code == 200

        # 2. Seed drifted
        r2 = client.post("/api/demo/seed?mode=drifted", headers=auth_headers)
        assert r2.status_code == 200

        # 3. Custom X-Counsel-Token header also supported
        custom_header = {"X-Counsel-Token": token}
        r3 = client.post("/api/demo/seed?mode=resolved", headers=custom_header)
        assert r3.status_code == 200

    def test_unauthorized_and_invalid_tokens_rejected(self, client: TestClient):
        # 1. Invalid token raises HTTP 401 or 403
        bad_headers = {"Authorization": "Bearer invalid_counsel_token_fake_999"}
        r1 = client.post("/api/demo/seed?mode=drifted", headers=bad_headers)
        assert r1.status_code in (401, 403)

        r2 = client.post("/api/demo/reset", headers=bad_headers)
        assert r2.status_code in (401, 403)

        # 2. Malformed token raises 401
        malformed_headers = {"Authorization": "Bearer "}
        r3 = client.post("/api/demo/reset", headers=malformed_headers)
        assert r3.status_code == 401

        # 3. Strict authentication check without token raises 401
        strict_headers = {"X-Require-Counsel-Auth": "true"}
        r4 = client.post("/api/demo/reset", headers=strict_headers)
        assert r4.status_code == 401
        assert "missing counsel authentication token" in r4.json()["detail"].lower()


# ==============================================================================
# 5. TEST CONTROLLED FICTIONAL SEARCH SCENARIO
# ==============================================================================

class TestControlledFictionalSearchScenario:
    """
    Asserts Item 11 and Item 12 queries return attributable evidence with valid URLs and source titles.
    """

    @pytest.mark.asyncio
    async def test_item_11_noir_poster_attributable_search(self):
        service = ParallelSearchService()
        query = "Crime Detective Magazine 1946 Shadows Over Broadway copyright renewal"

        snapshot = await service.search(
            query=query,
            use_id="use_v8_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
        )

        # Attributable evidence assertions
        assert snapshot.source_url.startswith("http")
        assert "cocatalog.loc.gov" in snapshot.source_url
        assert "US Copyright Office Historical Catalog" in snapshot.source_title
        assert snapshot.domain == "cocatalog.loc.gov"
        assert snapshot.stance == EvidenceStance.SUPPORTING
        assert "public domain" in snapshot.excerpt.lower()
        assert snapshot.raw_payload_hash is not None
        assert len(snapshot.raw_payload_hash) == 64
        assert snapshot.provider_call_id is not None

    @pytest.mark.asyncio
    async def test_item_12_midnight_serenade_attributable_search(self):
        service = ParallelSearchService()
        query = "Midnight Serenade jazz sync rights copyright owner 2026"

        snapshot = await service.search(
            query=query,
            use_id="use_v8_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
        )

        # Attributable evidence assertions
        assert snapshot.source_url.startswith("http")
        assert "ascap.com" in snapshot.source_url
        assert "ASCAP ACE Repertory" in snapshot.source_title
        assert snapshot.domain == "ascap.com"
        assert snapshot.stance == EvidenceStance.CONTRADICTORY
        assert "vanguard media" in snapshot.excerpt.lower()
        assert snapshot.raw_payload_hash is not None
        assert len(snapshot.raw_payload_hash) == 64
        assert snapshot.provider_call_id is not None


# ==============================================================================
# 6. TEST PREFLIGHT SCRIPT REPORT
# ==============================================================================

class TestPreflightScriptReport:
    """
    Asserts scripts/preflight_recording.py executes and produces valid JSON report.
    """

    def test_preflight_script_produces_ready_for_recording_report(self):
        runner = RecordingPreflightRunner(verbose=False)
        passed, report = runner.run_all_checks()

        assert passed is True
        assert report["status"] == "READY_FOR_RECORDING"
        assert report["total_checks"] == 7
        assert report["passed_checks"] == 7
        assert report["failed_checks"] == 0

        # Assert valid ISO 8601 UTC timestamp
        ts_str = report["timestamp"]
        parsed_ts = datetime.fromisoformat(ts_str)
        assert parsed_ts is not None

        # Assert report file exists on disk and matches
        assert REPORT_FILE.is_file()
        file_report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        assert file_report["status"] == "READY_FOR_RECORDING"
        assert file_report["policy_version"] == InvalidationEngine.POLICY_VERSION

        # Verify all 7 check IDs present and passed
        expected_check_ids = {
            "CHECK_1_CREDENTIALS",
            "CHECK_2_BACKEND_HEALTH",
            "CHECK_3_FRONTEND_READINESS",
            "CHECK_4_PARALLEL_SEARCH",
            "CHECK_5_GEMINI_DELTA_CONTRACT",
            "CHECK_6_DEMO_SEED_RESET_CYCLE",
            "CHECK_7_DISPLAY_AUDIO_CHECKPOINT",
        }
        actual_check_ids = {c["check_id"] for c in file_report["checks"]}
        assert expected_check_ids == actual_check_ids

        for c in file_report["checks"]:
            assert c["passed"] is True
            assert c["status"] == "PASSED"

        # Assert credential safety in check 1
        check_1 = next(c for c in file_report["checks"] if c["check_id"] == "CHECK_1_CREDENTIALS")
        assert check_1["metadata"]["secret_masking_enforced"] is True
        for d in check_1["details"]:
            assert "AIzaSy" not in d
            assert "sk-proj" not in d
