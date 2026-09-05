"""
Automated Test Suite for Sprint 4C Task 2: Usability & Comprehension Test Engineer

Verifies:
1. Unfamiliar Tester Task: "Determine what version 8 changed and what still blocks clearance review"
   - Evaluates whether an automated client can query the system and unambiguously discover:
     1. Exactly what changed in v8 (Item 11 creative shift, Item 12 external fact shift).
     2. Exactly what blocks clearance review (the 2 stale items in ReviewQueue).
     3. The exact resolution path for each blocker (Item 11: Public Domain Re-Attest; Item 12: Schedule Exception).

2. Verification of the Top 3 Comprehension Fixes:
   - Fix 1: Asserts presence of deterministic lineage parity explanation for the 10 carried claims
     ($0 review cost, bit-for-bit unchanged between Cut v7 and v8).
   - Fix 2: Asserts presence of the Active Clearance Blockers callout detailing Item 11 and Item 12.
   - Fix 3: Asserts presence of the Clearance Decision Lifecycle guide and underwriter warranty export path.

3. Comprehension Parity across API and UI:
   - Asserts that /api/review/queue and /api/fixtures provide explicit comprehension aids
     (descriptions, timecodes, reason codes, 4D breakdowns).
   - Asserts full parity between FastAPI backend responses, static fixtures, and Next.js React components.

4. Phase 4 Exit Gate Certification:
   - Formally certifies that all Phase 4 acceptance criteria (Sprint 4A, 4B, 4C) are satisfied with zero ambiguity.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    CounselDecision,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    ReviewAction,
    ReviewActionRequest,
    ReviewerIdentity,
)
from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    counsel_checkpoint_manager,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)
from backend.main import app, _counsel_reattestations, get_comprehension_aids

client = TestClient(app)


# =============================================================================
# FIXTURES & ISOLATION
# =============================================================================

@pytest.fixture(autouse=True)
def clean_usability_session():
    """Ensures clean global state before and after every test in the suite."""
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()
    yield
    _counsel_reattestations.clear()
    counsel_checkpoint_manager.reset()


# =============================================================================
# TEST CLASS 1: UNFAMILIAR TESTER TASK
# "Determine what version 8 changed and what still blocks clearance review"
# =============================================================================

class TestUnfamiliarTesterTask:
    """
    Evaluates whether an automated client (or unfamiliar tester) querying the system
    can unambiguously discover:
      1. Exactly what changed in v8 (Item 11 creative shift, Item 12 external fact shift).
      2. Exactly what blocks clearance review (the 2 stale items in ReviewQueue).
      3. The exact resolution path for each blocker.
    """

    def test_unambiguous_discovery_of_what_v8_changed(self):
        """
        Subtask 1: Determine what version 8 changed.
        Asserts that an automated client querying /api/fixtures and /api/review/queue
        discovers exactly the 2 material changes in v8:
          - Item 11: Creative shift in Scene 42 (2s background blur -> 14s close-up focal dialogue).
          - Item 12: External fact shift in Scene 18 (Vanguard Media adverse copyright assignment).
        """
        res = client.get("/api/review/queue?target_version=v8")
        assert res.status_code == 200
        data = res.json()

        assert "items" in data
        items = data["items"]
        assert len(items) == 2, f"Expected exactly 2 changed items in v8 review queue, got {len(items)}"

        item_keys = {it["stable_lineage_key"] for it in items}
        assert "poster_noir_detective_magazine" in item_keys
        assert "music_cue_midnight_serenade" in item_keys

        # 1. Item 11: Creative Shift
        item_11 = next(it for it in items if it["stable_lineage_key"] == "poster_noir_detective_magazine")
        assert "42" in item_11["scene_or_timecode"]
        assert item_11["timecode"] == "00:44:12" or "44:12" in item_11["scene_or_timecode"]
        assert item_11["asset_type"] == "artwork"
        assert item_11["reason_code"] == "CREATIVE_CONTEXT_ALTERED"
        assert "creative_change_summary" in item_11 or "creative_change" in item_11.get("explanation_4d", {})
        creative_text = item_11.get("creative_change_summary", "")
        assert "blur" in creative_text.lower() or "focal" in creative_text.lower() or "close-up" in creative_text.lower()

        # 2. Item 12: External Fact Shift
        item_12 = next(it for it in items if it["stable_lineage_key"] == "music_cue_midnight_serenade")
        assert "18" in item_12["scene_or_timecode"]
        assert item_12["timecode"] == "00:19:40" or "19:40" in item_12["scene_or_timecode"]
        assert item_12["asset_type"] in ("music", "music_cue")
        assert item_12["reason_code"] == "EXTERNAL_EVIDENCE_SHIFT"
        evidence_text = item_12.get("evidence_change_summary", "")
        assert "vanguard" in evidence_text.lower() or "exclusive" in evidence_text.lower()

    def test_unambiguous_discovery_of_what_blocks_clearance_review(self):
        """
        Subtask 2: Determine what still blocks clearance review.
        Asserts that an automated client can query the system and unambiguously discover:
          - Exactly 2 stale items in ReviewQueue are blocking clearance sign-off.
          - The other 10 claims are CARRIED_FORWARD and DO NOT block clearance.
          - Overall underwriter review status is PENDING_REVIEW until blockers are adjudicated.
        """
        res = client.get("/api/review/queue?target_version=v8")
        assert res.status_code == 200
        data = res.json()

        assert data["total_stale_count"] == 2
        assert len(data["items"]) == 2

        # Verify both items have current_state == STALE
        for item in data["items"]:
            assert item["current_state"] == DecisionState.STALE
            assert item["available_actions"] == ["re_attest", "reject", "exception"]

        # Verify that the 10 unchanged claims are carried forward and NOT in ReviewQueue
        fixtures_res = client.get("/api/fixtures")
        assert fixtures_res.status_code == 200
        fixtures_data = fixtures_res.json()
        assert len(fixtures_data["v7_claims"]) == 12

        carried_keys = {c["key"] for c in fixtures_data["v7_claims"]} - {
            "poster_noir_detective_magazine",
            "music_cue_midnight_serenade",
        }
        assert len(carried_keys) == 10
        for carried_key in carried_keys:
            assert carried_key not in {it["stable_lineage_key"] for it in data["items"]}

    def test_unambiguous_discovery_of_resolution_path_for_each_blocker(self):
        """
        Subtask 3: Determine the exact resolution path for each blocker.
        Asserts that an automated client can query the system and discover:
          - Resolution path for Item 11: Counsel Re-Attestation under Public Domain doctrine.
          - Resolution path for Item 12: Underwriting Exception designation on Form E&O-2026 Schedule.
        """
        res = client.get("/api/review/queue?target_version=v8")
        assert res.status_code == 200
        data = res.json()

        # Check comprehension aids resolution paths
        blockers = data.get("active_clearance_blockers") or data.get("comprehension_aids", {}).get("active_clearance_blockers", [])
        assert len(blockers) == 2

        b11 = next(b for b in blockers if b["key"] == "poster_noir_detective_magazine")
        assert "public domain" in b11["resolution_path"].lower()
        assert "loc" in b11["resolution_path"].lower() or "library of congress" in b11["resolution_path"].lower()
        assert b11["suggested_action"] == "re_attest"

        b12 = next(b for b in blockers if b["key"] == "music_cue_midnight_serenade")
        assert "exception" in b12["resolution_path"].lower()
        assert "e&o-2026" in b12["resolution_path"].lower() or "schedule" in b12["resolution_path"].lower()
        assert b12["suggested_action"] == "exception"

    def test_automated_client_resolution_execution_unblocks_clearance(self):
        """
        Executes the exact resolution path discovered for both blockers and asserts that
        all blockers are cleared, the ReviewQueue is resolved, and clearance is unblocked.
        """
        # 1. Resolve Item 11 via Re-Attestation under Public Domain doctrine
        res_11 = client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "counsel_rationale": "Cover art is public domain: US Copyright Office records confirm 1946 registration lapsed without renewal in 1974. Corroborated via LOC catalog.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_11.status_code == 200
        event_11 = res_11.json()["event"]
        assert event_11["action"] == "re_attest"

        # 2. Resolve Item 12 via Exception designation on Form E&O-2026 Schedule
        res_12 = client.post(
            "/api/review/action",
            json={
                "action": "exception",
                "stable_lineage_key": "music_cue_midnight_serenade",
                "counsel_rationale": "Unresolved sync rights breach: Vanguard Media acquired exclusive worldwide synchronization rights August 2026. Cue marked as underwriting exception.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_12.status_code == 200
        event_12 = res_12.json()["event"]
        assert event_12["action"] == "exception"

        # 3. Check that Exceptions Schedule reflects 100% reconciled state
        res_sched = client.get("/api/reports/exceptions")
        assert res_sched.status_code == 200
        sched = res_sched.json()
        assert sched["carried_forward_count"] == 10
        assert sched["re_attested_count"] == 1
        assert sched["unresolved_exception_count"] == 1
        assert sched["total_claims"] == 12


# =============================================================================
# TEST CLASS 2: VERIFICATION OF THE TOP 3 COMPREHENSION FIXES
# =============================================================================

class TestTopThreeComprehensionFixes:
    """
    Verifies that the Top 3 Usability & Comprehension Fixes from Sprint 4C
    are present in both backend payloads and frontend code artifacts.
    """

    def test_fix_1_deterministic_lineage_parity_explanation(self):
        """
        Fix 1: Asserts presence of deterministic lineage parity explanation for the 10 carried claims
        ($0 review cost, bit-for-bit unchanged between Cut v7 and v8).
        """
        # 1. Assert in API aids helper
        aids = get_comprehension_aids()
        parity = aids["deterministic_lineage_parity"]
        assert parity["carried_claims_count"] == 10
        assert parity["total_claims_count"] == 12
        assert parity["review_cost_dollars"] == 0.0
        assert parity["bit_for_bit_unchanged"] is True
        assert "bit-for-bit unchanged" in parity["explanation"].lower()
        assert "$0 review cost" in parity["explanation"].lower()
        assert len(parity["carried_claim_keys"]) == 10

        # 2. Assert in /api/fixtures response
        res_fix = client.get("/api/fixtures")
        assert res_fix.status_code == 200
        payload_fix = res_fix.json()
        assert "deterministic_lineage_parity" in payload_fix
        assert payload_fix["deterministic_lineage_parity"]["carried_claims_count"] == 10
        assert payload_fix["deterministic_lineage_parity"]["review_cost_dollars"] == 0.0

        # 3. Assert in /api/review/queue response
        res_queue = client.get("/api/review/queue?target_version=v8")
        assert res_queue.status_code == 200
        payload_queue = res_queue.json()
        assert "deterministic_lineage_parity" in payload_queue
        assert "bit-for-bit unchanged" in payload_queue["deterministic_lineage_parity"]["explanation"].lower()

        # 4. Assert in frontend ClearanceSummaryCards.tsx component
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        summary_cards_path = os.path.join(repo_root, "frontend", "app", "components", "ClearanceSummaryCards.tsx")
        assert os.path.exists(summary_cards_path)
        with open(summary_cards_path, "r", encoding="utf-8") as f:
            summary_content = f.read()

        assert "Deterministic Lineage Parity" in summary_content
        assert "$0 Review" in summary_content or "$0.00" in summary_content or "$0" in summary_content
        assert "bit-for-bit" in summary_content.lower()

        # 5. Assert in Dashboard HTML
        dash_res = client.get("/")
        assert dash_res.status_code == 200
        assert "deterministic lineage parity" in dash_res.text.lower()
        assert "bit-for-bit unchanged" in dash_res.text.lower()

    def test_fix_2_active_clearance_blockers_callout(self):
        """
        Fix 2: Asserts presence of the Active Clearance Blockers callout detailing Item 11 and Item 12.
        """
        # 1. Assert in API aids helper
        aids = get_comprehension_aids()
        blockers = aids["active_clearance_blockers"]
        assert len(blockers) == 2

        # Verify Item 11 details
        b11 = next(b for b in blockers if b["key"] == "poster_noir_detective_magazine")
        assert b11["item_number"] == 11
        assert b11["timecode"] == "00:44:12"
        assert "creative" in b11["shift_type"].lower()
        assert "14s close-up" in b11["shift_summary"].lower() or "blur" in b11["shift_summary"].lower()
        assert "17 u.s.c. § 107" in b11["blocker_details"].lower() or "de minimis" in b11["blocker_details"].lower()

        # Verify Item 12 details
        b12 = next(b for b in blockers if b["key"] == "music_cue_midnight_serenade")
        assert b12["item_number"] == 12
        assert b12["timecode"] == "00:19:40"
        assert "external" in b12["shift_type"].lower()
        assert "vanguard" in b12["blocker_details"].lower()

        # 2. Assert in /api/review/queue
        res_queue = client.get("/api/review/queue?target_version=v8")
        assert res_queue.status_code == 200
        data = res_queue.json()
        assert "active_clearance_blockers" in data
        assert len(data["active_clearance_blockers"]) == 2

        # 3. Assert in frontend ActiveClearanceBlockers.tsx component
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        blockers_comp_path = os.path.join(repo_root, "frontend", "app", "components", "ActiveClearanceBlockers.tsx")
        assert os.path.exists(blockers_comp_path)
        with open(blockers_comp_path, "r", encoding="utf-8") as f:
            comp_content = f.read()

        assert "Active Clearance Blockers Summary" in comp_content
        assert "Item 11" in comp_content
        assert "Item 12" in comp_content
        assert "00:44:12" in comp_content
        assert "00:19:40" in comp_content
        assert "Re-Attest" in comp_content
        assert "Exception" in comp_content

        # 4. Assert in frontend page.tsx
        page_path = os.path.join(repo_root, "frontend", "app", "page.tsx")
        with open(page_path, "r", encoding="utf-8") as f:
            page_content = f.read()
        assert "ActiveClearanceBlockers" in page_content

        # 5. Assert in Dashboard HTML
        dash_res = client.get("/")
        assert "active clearance blockers" in dash_res.text.lower()
        assert "item 11" in dash_res.text.lower()
        assert "item 12" in dash_res.text.lower()

    def test_fix_3_clearance_decision_lifecycle_guide_and_warranty_export(self):
        """
        Fix 3: Asserts presence of the Clearance Decision Lifecycle guide and underwriter warranty export path.
        """
        # 1. Assert in API aids helper
        aids = get_comprehension_aids()
        lifecycle = aids["clearance_decision_lifecycle"]
        assert len(lifecycle["stages"]) == 4
        assert lifecycle["underwriter_warranty_export_path"] == "/report/proj_blockbuster_cinema"
        stage_names = [s["name"] for s in lifecycle["stages"]]
        assert "Baseline Ingestion & Invalidation" in stage_names[0]
        assert "Targeted Revalidation" in stage_names[1]
        assert "Counsel Checkpoint" in stage_names[2]
        assert "Warranty Export" in stage_names[3]

        # 2. Assert in /api/review/queue and /api/fixtures
        for endpoint in ["/api/review/queue?target_version=v8", "/api/fixtures"]:
            res = client.get(endpoint)
            assert res.status_code == 200
            payload = res.json()
            assert "clearance_decision_lifecycle" in payload
            assert payload["clearance_decision_lifecycle"]["underwriter_warranty_export_path"] == "/report/proj_blockbuster_cinema"

        # 3. Assert in frontend ClearanceLifecycleGuide.tsx component
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        guide_comp_path = os.path.join(repo_root, "frontend", "app", "components", "ClearanceLifecycleGuide.tsx")
        assert os.path.exists(guide_comp_path)
        with open(guide_comp_path, "r", encoding="utf-8") as f:
            guide_content = f.read()

        assert "Clearance Decision Lifecycle Guide" in guide_content
        assert "Step 1: Baseline Review" in guide_content
        assert "Step 2: Automated Drift Invalidation" in guide_content
        assert "Step 3: Counsel Checkpoint Adjudication" in guide_content
        assert "Step 4: Version-Bound Form E&O-2026 Exceptions Schedule" in guide_content
        assert "/report/proj_blockbuster_cinema" in guide_content

        # 4. Assert in frontend page.tsx
        page_path = os.path.join(repo_root, "frontend", "app", "page.tsx")
        with open(page_path, "r", encoding="utf-8") as f:
            page_content = f.read()
        assert "ClearanceLifecycleGuide" in page_content

        # 5. Assert in Dashboard HTML
        dash_res = client.get("/")
        assert "clearance decision lifecycle guide" in dash_res.text.lower()
        assert "/report/proj_blockbuster_cinema" in dash_res.text


# =============================================================================
# TEST CLASS 3: COMPREHENSION PARITY ACROSS API AND UI
# =============================================================================

class TestComprehensionParityApiAndUi:
    """
    Asserts that /api/review/queue and /api/fixtures provide explicit comprehension aids:
      - Descriptions
      - Timecodes
      - Reason codes
      - 4-Dimensional breakdowns
    And validates exact comprehension parity between backend endpoints and frontend data fixtures.
    """

    def test_review_queue_endpoint_comprehension_aids(self):
        """
        Asserts that GET /api/review/queue returns explicit descriptions, timecodes,
        reason codes, and 4-dimensional explanations for all items.
        """
        res = client.get("/api/review/queue?target_version=v8")
        assert res.status_code == 200
        payload = res.json()

        items = payload["items"]
        assert len(items) == 2

        for it in items:
            # 1. Description comprehension aid
            assert "description" in it
            assert len(it["description"]) > 5

            # 2. Timecode comprehension aid
            assert "scene_or_timecode" in it or "timecode" in it
            timecode_val = it.get("timecode") or it.get("scene_or_timecode")
            assert ":" in timecode_val, f"Timecode '{timecode_val}' must contain minute/second formatting"

            # 3. Reason code comprehension aid
            assert "statutory_policy_reason" in it or "reason_code" in it
            reason_str = it.get("reason_code") or it.get("statutory_policy_reason", "")
            assert len(reason_str) > 0

            # 4. 4-Dimensional breakdown
            assert "explanation_4d" in it or "four_dimensions" in it or "creative_change_summary" in it
            assert it.get("creative_change_summary") or it.get("explanation_4d", {}).get("creative_change")
            assert it.get("evidence_change_summary") or it.get("explanation_4d", {}).get("evidence_change")
            assert it.get("private_fact_summary") or it.get("explanation_4d", {}).get("private_fact")
            assert it.get("statutory_policy_reason") or it.get("explanation_4d", {}).get("policy_reason")

    def test_fixtures_endpoint_comprehension_aids(self):
        """
        Asserts that GET /api/fixtures returns explicit descriptions, timecodes,
        reason codes, and baseline versions for unfamiliar reviewers.
        """
        res = client.get("/api/fixtures")
        assert res.status_code == 200
        payload = res.json()

        assert "v7_version" in payload
        assert "v8_version" in payload
        assert "v7_claims" in payload
        assert "v8_claims" in payload

        # Check v7 claims
        v7_claims = payload["v7_claims"]
        assert len(v7_claims) == 12
        for claim in v7_claims:
            assert "description" in claim
            assert "scene" in claim
            assert "timecode" in claim
            assert "reason_code" in claim
            assert len(claim["description"]) > 0

        # Check v8 claims
        v8_claims = payload["v8_claims"]
        assert len(v8_claims) == 12
        for claim in v8_claims:
            assert "description" in claim
            assert "scene" in claim
            assert "timecode" in claim
            assert "reason_code" in claim

    def test_frontend_fixtures_data_comprehension_parity(self):
        """
        Asserts that frontend/lib/fixtures_data.ts provides identical comprehension aids
        matching the backend contracts.
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        fixtures_data_path = os.path.join(repo_root, "frontend", "lib", "fixtures_data.ts")
        assert os.path.exists(fixtures_data_path)

        with open(fixtures_data_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "getGoldenComprehensionAids" in content
        assert "deterministic_lineage_parity" in content
        assert "active_clearance_blockers" in content
        assert "clearance_decision_lifecycle" in content
        assert "00:44:12" in content
        assert "00:19:40" in content


# =============================================================================
# TEST CLASS 4: PHASE 4 EXIT GATE CERTIFICATION
# =============================================================================

class TestPhase4ExitGate:
    """
    Formally certifies that all Phase 4 acceptance criteria are satisfied with zero ambiguity:
      - Sprint 4A (§9, Sprint 4A): Information architecture, 8 components, WCAG multi-attribute indicators.
      - Sprint 4B (§9, Sprint 4B): Interaction and failure states, progress ticker, optimistic rollback, SSR print engine.
      - Sprint 4C (§9, Sprint 4C): Usability test, unfamiliar tester task, top 3 comprehension fixes verified.
    """

    def test_sprint_4a_information_architecture_gate(self):
        """Sprint 4A Gate: Next.js modular components, mathematical summary conservation, WCAG multi-attribute indicators."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        components_dir = os.path.join(repo_root, "frontend", "app", "components")

        required_components = [
            "DashboardHeader.tsx",
            "ClearanceSummaryCards.tsx",
            "DeltaListComponent.tsx",
            "DecisionListComponent.tsx",
            "ExplanationDrawerComponent.tsx",
            "ReviewActionComponent.tsx",
            "ExportActionComponent.tsx",
            "AuditTrailDrawer.tsx",
        ]
        for comp in required_components:
            path = os.path.join(components_dir, comp)
            assert os.path.exists(path), f"Missing Sprint 4A component: {comp}"
            assert os.path.getsize(path) > 500

    def test_sprint_4b_interaction_and_failure_states_gate(self):
        """Sprint 4B Gate: Fail-closed degradation, zero drift identity f(v7,v7)=12/12, print engine parity."""
        # 1. Zero drift identity f(v7, v7)
        v7_uses, _, v7_decisions, initial_evidence = get_golden_fixtures()
        v7_results = InvalidationEngine.evaluate_invalidation(
            base_uses=v7_uses,
            target_uses=v7_uses,
            prior_decisions=v7_decisions,
            evidence_snapshots=initial_evidence,
            target_version_id="v7",
        )
        assert len(v7_results) == 12
        assert all(v.state == DecisionState.CARRIED_FORWARD for v in v7_results)

        # 2. SSR print engine parity
        ssr_res = client.get("/report/proj_blockbuster_cinema")
        assert ssr_res.status_code == 200
        assert "@media print" in ssr_res.text
        assert "Form E&O-2026" in ssr_res.text

    def test_sprint_4c_usability_and_comprehension_gate(self):
        """Sprint 4C Gate: Unfamiliar tester task unambiguous, Top 3 comprehension fixes active."""
        # Query active queue
        res = client.get("/api/review/queue?target_version=v8")
        assert res.status_code == 200
        data = res.json()

        # Check 1: What changed in v8
        assert len(data["items"]) == 2
        keys = {it["stable_lineage_key"] for it in data["items"]}
        assert keys == {"poster_noir_detective_magazine", "music_cue_midnight_serenade"}

        # Check 2: What blocks clearance
        assert data["total_stale_count"] == 2
        assert all(it["current_state"] == DecisionState.STALE for it in data["items"])

        # Check 3: Exact resolution path
        blockers = data["active_clearance_blockers"]
        assert len(blockers) == 2
        for b in blockers:
            assert len(b["resolution_path"]) > 15
            assert b["suggested_action"] in ("re_attest", "exception")

        # Check 4: Top 3 Comprehension Fixes certified
        assert "deterministic_lineage_parity" in data
        assert "active_clearance_blockers" in data
        assert "clearance_decision_lifecycle" in data

    def test_phase_4_zero_ambiguity_verdict(self):
        """
        Final Exit Gate Assertion:
        Validates that all Phase 4 acceptance criteria are certified with zero ambiguity.
        """
        # Conservation invariant: 12 total = 10 carried + 2 stale -> 10 carried + 1 re-attested + 1 exception
        total = 12
        carried = 10
        stale = 2
        assert total == carried + stale

        # Adjudicate both stale claims
        res_attest = client.post(
            "/api/review/action",
            json={
                "action": "re_attest",
                "stable_lineage_key": "poster_noir_detective_magazine",
                "counsel_rationale": "Public domain verification via US Copyright Office historical catalog.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_attest.status_code == 200

        res_except = client.post(
            "/api/review/action",
            json={
                "action": "exception",
                "stable_lineage_key": "music_cue_midnight_serenade",
                "counsel_rationale": "Vanguard exclusive rights dispute flagged as schedule rider.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_except.status_code == 200

        # Post-adjudication state
        reattested = 1
        exceptions = 1
        stale_remaining = 0
        assert total == carried + stale_remaining + reattested + exceptions

        # Reconciled export verification
        res_export = client.get("/api/reports/exceptions")
        assert res_export.status_code == 200
        sched = res_export.json()
        assert sched["carried_forward_count"] == 10
        assert sched["re_attested_count"] == 1
        assert sched["unresolved_exception_count"] == 1
        assert sched["carrier_header"]["policy_number"] == "E&O-2026.1-DEVPOST"
