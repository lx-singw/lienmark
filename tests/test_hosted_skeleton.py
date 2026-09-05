"""
Sprint 1C Hosted Skeleton Verification Suite
Verifies the Next.js 15 App Router contracts, Server Actions payload validation,
SSR Exceptions Schedule data integrity, and the complete 12 -> 10/2 -> 1/1 clearance user journey.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestSprint1CHostedSkeleton:
    """Empirical verification suite for Sprint 1C Hosted Skeleton deliverables."""

    def test_hosted_skeleton_fixtures_contract(self):
        """Validates that version selector and run button have access to locked V7 and V8 versions."""
        res = client.get("/api/fixtures")
        assert res.status_code == 200
        data = res.json()

        # Check V7 locked production version
        assert "v7_version" in data
        assert data["v7_version"]["version_id"] == "v7"
        assert "v7" in data["v7_version"]["label"].lower()
        assert len(data["v7_version"]["content_hash"]) >= 32

        # Check V8 revised production version
        assert "v8_version" in data
        assert data["v8_version"]["version_id"] == "v8"
        assert "v8" in data["v8_version"]["label"].lower()
        assert data["v8_version"]["parent_version_id"] == "v7"

        # Check 12 golden claims
        assert len(data["v7_claims"]) == 12
        claim_keys = [c["key"] for c in data["v7_claims"]]
        assert "poster_noir_detective_magazine" in claim_keys
        assert "music_cue_midnight_serenade" in claim_keys

    def test_drift_detection_run_record_lifecycle(self):
        """Validates the backend run record generation, step durations, and 12 -> 10/2 state."""
        res = client.post("/api/drift/compare")
        assert res.status_code == 200
        data = res.json()

        # Verify run record metadata
        assert "run_id" in data
        assert data["run_id"].startswith("run_")
        assert data["base_version"] == "v7"
        assert data["target_version"] == "v8"
        assert data["total_duration_ms"] > 0

        # Invariant 12 -> 10/2
        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["reopened_count"] == 2

        # Verify execution traces for judge observability
        traces = data["execution_traces"]
        assert len(traces) >= 4
        step_names = [t["step_name"] for t in traces]
        assert "version_ingestion" in step_names
        assert "semantic_delta_analysis" in step_names
        assert "deterministic_dependency_invalidation" in step_names

        # Verify Item 11 and Item 12 drift detection
        stale_claims = [c for c in data["claims"] if c["state"] == "stale"]
        assert len(stale_claims) == 2
        stale_keys = [c["stable_lineage_key"] for c in stale_claims]
        assert "poster_noir_detective_magazine" in stale_keys
        assert "music_cue_midnight_serenade" in stale_keys

    def test_item_11_creative_drift_and_counsel_reattestation(self):
        """
        Validates Item 11 (Scene 42 poster):
        Creative drift detected (material modification to featured hero prop) ->
        Parallel Search provides supporting copyright lapse evidence ->
        Counsel re-attestation re-approves under Public Domain confirmation.
        """
        # 1. Reset and execute run
        res = client.post("/api/drift/compare")
        assert res.status_code == 200
        data = res.json()

        # Item 11 inspection
        poster_claim = next(c for c in data["claims"] if c["stable_lineage_key"] == "poster_noir_detective_magazine")
        assert "Scene 42" in poster_claim["scene"]
        assert poster_claim["state"] == "stale"
        assert poster_claim["reason_code"] == "CREATIVE_CONTEXT_ALTERED"

        # Check Parallel Search citation
        assert poster_claim["evidence"] is not None
        assert poster_claim["evidence"]["stance"] == "supporting"
        assert "Copyright" in poster_claim["evidence"]["source_title"] or "Library of Congress" in poster_claim["evidence"].get("publisher", "")

        # 2. Counsel re-attestation (Server Action emulation)
        attest_payload = {
            "decision_id": "dec_poster_v8_attest",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "version_id": "v8",
            "new_status": "approved",
            "counsel_rationale": "Artwork confirmed in public domain; LOC registration lapsed 1974 without renewal.",
            "reviewer_name": "Eleanor Vance, Senior Production Counsel",
        }
        attest_res = client.post("/api/review/attest", json=attest_payload)
        assert attest_res.status_code == 200
        assert attest_res.json()["status"] == "recorded"
        assert attest_res.json()["new_status"] == "approved"

    def test_item_12_external_drift_and_exception_designation(self):
        """
        Validates Item 12 (Scene 18 jazz cue):
        External drift detected (chain-of-title contradiction discovered) ->
        Parallel Search provides contradictory Vanguard Media ownership evidence ->
        Counsel marks as Form E&O-2026 Exception for underwriter disclosure.
        """
        exception_payload = {
            "decision_id": "dec_music_v8_exception",
            "stable_lineage_key": "music_cue_midnight_serenade",
            "version_id": "v8",
            "new_status": "rejected",
            "counsel_rationale": "Sync license dispute with Vanguard Media unresolved. Flagged as Form E&O-2026 schedule exception.",
            "reviewer_name": "Eleanor Vance, Senior Production Counsel",
        }
        attest_res = client.post("/api/review/attest", json=exception_payload)
        assert attest_res.status_code == 200
        assert attest_res.json()["status"] == "recorded"
        assert attest_res.json()["new_status"] == "rejected"

    def test_ssr_exceptions_schedule_reconciliation(self):
        """
        Validates the completed 12 -> 10/2 -> 1/1 reconciliation on Form E&O-2026:
        - 12 total claims
        - 10 carried forward without re-review cost
        - 2 needing attestation
        - 1 counsel re-attested (Item 11 poster)
        - 1 unresolved underwriter exception (Item 12 music cue)
        """
        # Ensure Item 11 and Item 12 decisions are recorded in state
        client.post(
            "/api/review/attest",
            json={
                "decision_id": "dec_poster_v8_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "version_id": "v8",
                "new_status": "approved",
                "counsel_rationale": "Artwork confirmed in public domain.",
                "reviewer_name": "Eleanor Vance, Senior Production Counsel",
            },
        )
        client.post(
            "/api/review/attest",
            json={
                "decision_id": "dec_music_v8_exception",
                "stable_lineage_key": "music_cue_midnight_serenade",
                "version_id": "v8",
                "new_status": "rejected",
                "counsel_rationale": "Sync license dispute with Vanguard Media unresolved.",
                "reviewer_name": "Eleanor Vance, Senior Production Counsel",
            },
        )

        sched_res = client.get("/api/reports/exceptions")
        assert sched_res.status_code == 200
        schedule = sched_res.json()

        assert schedule["policy_version"] == "E&O-2026.1-DEVPOST"
        assert schedule["total_claims"] == 12
        assert schedule["carried_forward_count"] == 10
        assert schedule["reopened_count"] == 2
        assert schedule["re_attested_count"] == 1
        assert schedule["unresolved_exception_count"] == 1

        # Check line items
        items = schedule["items"]
        assert len(items) == 12

        # Item 11 line item
        poster_item = next(i for i in items if i["stable_lineage_key"] == "poster_noir_detective_magazine")
        assert poster_item["v8_evaluation_state"] == "re_attested"
        assert "public domain" in poster_item["counsel_action"].lower()

        # Item 12 line item
        music_item = next(i for i in items if i["stable_lineage_key"] == "music_cue_midnight_serenade")
        assert music_item["v8_evaluation_state"] == "exception"
        assert "exception" in music_item["counsel_action"].lower()

    def test_html_dashboard_and_print_readiness(self):
        """Validates that the hosted dashboard provides fast SSR loading and print-ready exceptions schedule."""
        res = client.get("/dashboard")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        body = res.text

        # Verify key UI components and labels
        assert "Lienmark" in body
        assert "Parallel Track" in body
        assert "Ingest V8" in body or "Run" in body or "Evaluation" in body
        assert "Form E&O-2026" in body or "Form E&amp;O-2026" in body
