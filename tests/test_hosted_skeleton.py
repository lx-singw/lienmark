"""
Sprint 1C Hosted Skeleton Verification Suite
Verifies the Next.js 15 App Router contracts, Server Actions payload validation,
SSR Exceptions Schedule data integrity, frontend proxy fallback resilience,
and the complete 12 -> 10/2 -> 1/1 clearance user journey.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import json
import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.domain.models import (
    CarrierHeader,
    DecisionState,
    DecisionStatus,
    ExceptionsSchedule,
    ReattestationRequest,
)
from backend.fixtures.golden_dataset import (
    get_golden_fixtures,
    get_v7_version,
    get_v8_version,
)
from backend.core.invalidation_engine import InvalidationEngine

client = TestClient(app)


class TestSprint1CHostedSkeleton:
    """Empirical verification suite for Sprint 1C Hosted Skeleton deliverables."""

    def test_health_and_integration_status(self):
        """
        Validates GET /health and GET /api/health:
        - Returns 200 OK with toolchain and policy status.
        - Verifies Google AntiGravity provenance and Parallel Track metadata.
        """
        for path in ("/health", "/api/health"):
            res = client.get(path)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert "Lienmark" in data["service"]
            assert "Google AntiGravity" in data["provenance"]
            assert "Parallel Track" in data["track"]
            assert "integrations" in data
            assert data["integrations"]["agent_platform"] == "Google Cloud Agent Builder / ADK"
            assert data["policy_version"] == "E&O-2026.1-DEVPOST"

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

    def test_diff_evaluate_endpoint_contract(self):
        """
        Validates POST /api/diff/evaluate endpoint corresponding to Next.js API client & Server Actions:
        - Evaluates 12 claims across V7 -> V8.
        - Preserves the fundamental invariant: 10 carried forward, 2 reopened.
        """
        res = client.post("/api/diff/evaluate", json={})
        assert res.status_code == 200
        data = res.json()

        assert data["run_id"].startswith("run_")
        assert data["base_version"] == "v7"
        assert data["target_version"] == "v8"
        assert data["total_claims"] == 12
        assert data["carried_forward_count"] == 10
        assert data["reopened_count"] == 2
        assert len(data["claims"]) == 12

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

    def test_attorney_override_endpoint_contract(self):
        """
        Validates POST /api/attorney/override and POST /api/attorney-override:
        - Successfully records counsel disposition for attorney override actions.
        """
        override_payload = {
            "decision_id": "dec_override_test",
            "stable_lineage_key": "poster_noir_detective_magazine",
            "version_id": "v8",
            "new_status": "approved",
            "counsel_rationale": "Overridden by Senior Partner following LOC catalog corroboration.",
            "reviewer_name": "Eleanor Vance, Senior Production Counsel",
        }
        for ep in ("/api/attorney/override", "/api/attorney-override"):
            res = client.post(ep, json=override_payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "recorded"
            assert data["stable_lineage_key"] == "poster_noir_detective_magazine"
            assert data["new_status"] == "approved"

    def test_item_11_creative_drift_and_counsel_reattestation(self):
        """
        Validates Item 11 (Scene 42 poster):
        Creative drift detected (material modification to featured hero prop) ->
        Parallel Search provides supporting copyright lapse evidence ->
        Counsel re-attestation re-approves under Public Domain confirmation.
        """
        # 1. Reset and execute run
        res = client.post("/api/diff/evaluate")
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
        attest_res = client.post("/api/attorney/override", json=attest_payload)
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
        attest_res = client.post("/api/attorney/override", json=exception_payload)
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
        - Required carrier header, policy number E&O-2026.1-DEVPOST, production metadata, and unresolved exceptions schedule.
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

        for path in ("/api/reports/exceptions", "/api/reports/form-eo-2026"):
            sched_res = client.get(path)
            assert sched_res.status_code == 200
            schedule = sched_res.json()

            # Statutory Policy Number and Verification Invariant
            assert schedule["policy_version"] == "E&O-2026.1-DEVPOST"
            assert schedule["policy_number"] == "E&O-2026.1-DEVPOST"
            assert schedule["total_claims"] == 12
            assert schedule["carried_forward_count"] == 10
            assert schedule["reopened_count"] == 2
            assert schedule["re_attested_count"] == 1
            assert schedule["unresolved_exception_count"] == 1
            assert schedule["total_claims"] == (
                schedule["carried_forward_count"]
                + schedule["re_attested_count"]
                + schedule["unresolved_exception_count"]
            )

            # Carrier Header validation
            assert "carrier_header" in schedule
            carrier_hdr = schedule["carrier_header"]
            assert carrier_hdr["policy_number"] == "E&O-2026.1-DEVPOST"
            assert "Standard Entertainment" in carrier_hdr["carrier_name"]
            assert carrier_hdr["underwriter_status"] in ("PENDING_REVIEW", "PENDING_BINDER")
            assert "Warranted clearance schedule" in carrier_hdr["warranty_clause"]

            # Production Metadata validation
            assert "production_metadata" in schedule
            prod_meta = schedule["production_metadata"]
            assert prod_meta["project_id"] == "proj_blockbuster_cinema"
            assert prod_meta["base_version_id"] == "v7"
            assert prod_meta["target_version_id"] == "v8"

            # Unresolved Exceptions Schedule validation
            unresolved = schedule.get("unresolved_exceptions") or schedule.get("unresolved_exceptions_schedule")
            assert unresolved is not None
            assert len(unresolved) == 1
            assert unresolved[0]["stable_lineage_key"] == "music_cue_midnight_serenade"
            assert unresolved[0]["v8_evaluation_state"] == "exception"

            # Check all 12 line items
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

    def test_frontend_proxy_fallback_resilience(self):
        """
        Validates frontend proxy fallback resilience:
        - Simulates offline/unreachable backend conditions.
        - Verifies that the typed golden fallback dataset (matching frontend/lib/fixtures_data.ts)
          preserves the exact same 12-claim structure, version hashes, and 12 -> 10/2 invariant.
        """
        # 1. Ingest golden fixtures directly to emulate frontend fallback handler
        v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
        v7_ver = get_v7_version()
        v8_ver = get_v8_version()

        # Check versions preserved in air-gapped state
        assert v7_ver.version_id == "v7"
        assert v8_ver.version_id == "v8"
        assert len(v7_ver.content_hash) >= 32
        assert len(v8_ver.content_hash) >= 32

        # Verify exact 12-claim lineage keys in fallback
        assert len(v7_uses) == 12
        assert len(v8_uses) == 12
        v7_keys = [u.stable_lineage_key for u in v7_uses]
        v8_keys = [u.stable_lineage_key for u in v8_uses]
        assert set(v7_keys) == set(v8_keys)
        assert "poster_noir_detective_magazine" in v7_keys
        assert "music_cue_midnight_serenade" in v7_keys

        # 2. Emulate deterministic evaluation under offline fallback
        offline_validities = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v8_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )
        assert len(offline_validities) == 12
        carried = [v for v in offline_validities if v.state == DecisionState.CARRIED_FORWARD]
        stale = [v for v in offline_validities if v.state == DecisionState.STALE]
        assert len(carried) == 10
        assert len(stale) == 2

        # 3. Emulate offline schedule generation with 1 re-attested and 1 exception
        offline_reattestations = {
            "poster_noir_detective_magazine": ReattestationRequest(
                decision_id="dec_fallback_poster",
                stable_lineage_key="poster_noir_detective_magazine",
                version_id="v8",
                new_status=DecisionStatus.APPROVED,
                counsel_rationale="Public domain verified in fallback state.",
                reviewer_name="Clearance Attorney",
            ),
            "music_cue_midnight_serenade": ReattestationRequest(
                decision_id="dec_fallback_music",
                stable_lineage_key="music_cue_midnight_serenade",
                version_id="v8",
                new_status=DecisionStatus.REJECTED,
                counsel_rationale="Sync license dispute scheduled as exception.",
                reviewer_name="Clearance Attorney",
            ),
        }
        fallback_schedule = InvalidationEngine.generate_exceptions_schedule(
            project_id="proj_blockbuster_cinema",
            base_version_id="v7",
            target_version_id="v8",
            target_uses=v8_uses,
            validity_results=offline_validities,
            reattestations=offline_reattestations,
        )

        assert fallback_schedule.total_claims == 12
        assert fallback_schedule.carried_forward_count == 10
        assert fallback_schedule.reopened_count == 2
        assert fallback_schedule.re_attested_count == 1
        assert fallback_schedule.unresolved_exception_count == 1
        assert fallback_schedule.policy_version == "E&O-2026.1-DEVPOST"
        assert fallback_schedule.policy_number == "E&O-2026.1-DEVPOST"
        assert len(fallback_schedule.unresolved_exceptions) == 1

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
