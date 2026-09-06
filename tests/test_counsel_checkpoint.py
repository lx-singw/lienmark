"""
Automated Test Suite for Sprint 3A Task 4: Counsel Checkpoint
Tests:
1. Review Queue Construction:
   - Evaluates golden dataset (v7 -> v8).
   - Asserts review queue contains strictly stale decisions (exactly 2 items:
     'poster_noir_detective_magazine' and 'music_cue_midnight_serenade').
   - Asserts 10 unchanged carried-forward claims are NOT in the review queue.
2. 4-Dimensional Explanation Presentation:
   - For Item 11: verifies creative change summary, LOC public domain search excerpt,
     contract absence, and policy reason code.
   - For Item 12: verifies creative stability, Vanguard Media adverse assignment excerpt,
     contract terms, and statutory policy reason.
3. Three Review Actions:
   - re_attest on Item 11: transitions state to RE_ATTESTED, status to APPROVED, generates SupersessionEvent.
   - reject on Item 12: transitions state to EXCEPTION, status to REJECTED, generates SupersessionEvent.
   - exception (leave as exception): marks state as EXCEPTION, generates SupersessionEvent.
4. Named Demo Reviewer:
   - Reviewer identity contains name, title, and is_fictional_demo == True.
   - Disclaimers state 'DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE'.
5. Append-Only Supersession Event & Inspectability:
   - event_id is unique.
   - prior_decision_id links back to original V7 decision and prior decision remains fully inspectable.
   - Audit trail distinguishes AI recommendation (system_recommendation='REVALIDATE') from human counsel decision (action=ReviewAction.RE_ATTEST).
   - event_hash is a valid 64-character SHA-256 hexadecimal string.
6. Fail-Closed Safety Invariant:
   - Asserts that the system cannot label a stale decision approved without an allowed carry-forward rule or explicit human action (raises error or rejects unauthenticated approval).
7. FastAPI Review Endpoints:
   - GET /api/review/queue
   - POST /api/review/action
   - GET /api/review/history
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import re
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    ContractAgreement,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    DemoReviewer,
    FourDimensionalExplanation,
    ReviewAction,
    ReviewActionRequest,
    ReviewQueue,
    ReviewQueueItem,
    SupersessionEvent,
    UnauthorizedApprovalError,
    FailClosedSecurityViolation,
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
from backend.main import app

client = TestClient(app)


# =============================================================================
# 1. TEST REVIEW QUEUE CONSTRUCTION
# =============================================================================

class TestReviewQueueConstruction:
    """
    Evaluates golden dataset (v7 -> v8) and verifies that the review queue contains
    strictly stale decisions (exactly 2 items) and that 10 unchanged carried-forward
    claims are NOT in the review queue.
    """

    def test_golden_dataset_queue_contains_strictly_stale_decisions(self):
        """Review queue contains strictly stale decisions (exactly 2 items)."""
        manager = CounselCheckpointManager()
        queue = manager.build_review_queue()

        assert isinstance(queue, ReviewQueue)
        assert len(queue) == 2, f"Review queue must contain exactly 2 items, got {len(queue)}"
        assert queue.total_stale_count == 2

        enqueued_keys = {item.stable_lineage_key for item in queue}
        expected_stale_keys = {"poster_noir_detective_magazine", "music_cue_midnight_serenade"}
        assert enqueued_keys == expected_stale_keys

        for item in queue:
            assert isinstance(item, ReviewQueueItem)
            assert item.current_state == DecisionState.STALE
            assert item.system_recommendation == "REVALIDATE"
            assert item.prior_decision is not None
            assert item.prior_decision_id.startswith("dec_v7_")

    def test_ten_unchanged_carried_forward_claims_are_not_in_review_queue(self):
        """Asserts 10 unchanged carried-forward claims are NOT in the review queue."""
        manager = CounselCheckpointManager()
        queue = manager.build_review_queue()

        enqueued_keys = {item.stable_lineage_key for item in queue}
        unchanged_keys = [
            "prop_vintage_telephone",
            "poster_paris_expo_1937",
            "car_ford_sedan_1949",
            "trademark_acme_coffee",
            "artwork_abstract_expressionist",
            "likeness_mayor_cameo",
            "architecture_tribunal_facade",
            "text_headline_gazette",
            "wardrobe_fedora_brand",
            "music_incidental_radio_static",
        ]

        assert len(unchanged_keys) == 10
        for key in unchanged_keys:
            assert key not in enqueued_keys, f"Carried-forward claim '{key}' must NOT be in the review queue"

    def test_review_queue_indexing_and_lookup(self):
        """Verifies dictionary-like and integer indexing on ReviewQueue."""
        manager = CounselCheckpointManager()
        queue = manager.build_review_queue()

        item_poster = queue["poster_noir_detective_magazine"]
        assert item_poster.stable_lineage_key == "poster_noir_detective_magazine"

        item_music = queue["music_cue_midnight_serenade"]
        assert item_music.stable_lineage_key == "music_cue_midnight_serenade"

        assert queue[0] is not None
        assert queue[1] is not None

        with pytest.raises(KeyError):
            _ = queue["non_existent_claim"]


# =============================================================================
# 2. TEST 4-DIMENSIONAL EXPLANATION PRESENTATION
# =============================================================================

class TestFourDimensionalExplanationPresentation:
    """
    Verifies that the 4-dimensional explanation presents:
    For Item 11: creative change summary, LOC public domain search excerpt, contract absence, policy reason code.
    For Item 12: creative stability, Vanguard Media adverse assignment excerpt, contract terms, statutory policy reason.
    """

    def test_item_11_four_dimensional_explanation(self):
        """Item 11: verifies creative change summary, LOC search excerpt, contract absence, policy reason code."""
        manager = CounselCheckpointManager()
        queue = manager.build_review_queue()
        item11 = queue["poster_noir_detective_magazine"]
        exp = item11.explanation_4d

        assert isinstance(exp, FourDimensionalExplanation)
        assert exp.stable_lineage_key == "poster_noir_detective_magazine"

        # Dimension 1: Creative Change Summary
        assert exp.creative_change, "Creative change summary must not be empty"
        assert exp.creative_change_summary == exp.creative_change
        creative_text = exp.creative_change.lower()
        assert any(term in creative_text for term in ["escalat", "focal", "dialogue", "close-up", "14s"])

        # Dimension 2: LOC Public Domain Search Excerpt
        assert exp.evidence_change, "LOC search excerpt must not be empty"
        assert exp.loc_public_domain_search_excerpt == exp.evidence_change
        evidence_text = exp.evidence_change.lower()
        assert any(term in evidence_text for term in ["public domain", "loc", "expired", "renewal", "b-1946"])

        # Dimension 3: Contract Absence
        assert exp.private_fact, "Contract fact must not be empty"
        assert exp.contract_absence == exp.private_fact
        contract_text = exp.private_fact.lower()
        assert any(term in contract_text for term in ["no private", "absence", "no contract", "relies on public domain"])

        # Dimension 4: Policy Reason Code
        assert exp.policy_reason, "Policy reason code must not be empty"
        assert exp.policy_reason_code == exp.policy_reason
        policy_text = exp.policy_reason
        assert "CREATIVE_CONTEXT_ALTERED" in policy_text
        assert "107" in policy_text  # 17 U.S.C. § 107 fair use / de minimis reference

        # System recommendation
        assert exp.system_recommendation == "REVALIDATE"

    def test_item_12_four_dimensional_explanation(self):
        """Item 12: verifies creative stability, Vanguard Media adverse assignment excerpt, contract terms, statutory policy reason."""
        manager = CounselCheckpointManager()
        queue = manager.build_review_queue()
        item12 = queue["music_cue_midnight_serenade"]
        exp = item12.explanation_4d

        assert isinstance(exp, FourDimensionalExplanation)
        assert exp.stable_lineage_key == "music_cue_midnight_serenade"

        # Dimension 1: Creative Stability
        assert exp.creative_change, "Creative stability description must not be empty"
        assert exp.creative_stability == exp.creative_change
        creative_text = exp.creative_change.lower()
        assert any(term in creative_text for term in ["identical", "stable", "remain", "scene 18", "20s"])

        # Dimension 2: Vanguard Media Adverse Assignment Excerpt
        assert exp.evidence_change, "Adverse assignment excerpt must not be empty"
        assert exp.adverse_assignment_excerpt == exp.evidence_change
        evidence_text = exp.evidence_change.lower()
        assert any(term in evidence_text for term in ["vanguard media", "assigned", "disputed", "synchronization"])

        # Dimension 3: Contract Terms
        assert exp.private_fact, "Contract terms description must not be empty"
        assert exp.contract_terms == exp.private_fact
        contract_text = exp.private_fact.lower()
        assert any(term in contract_text for term in ["contract terms", "synchronization", "perpetuity", "license", "shield"])

        # Dimension 4: Statutory Policy Reason
        assert exp.policy_reason, "Statutory policy reason must not be empty"
        assert exp.statutory_policy_reason == exp.policy_reason
        policy_text = exp.policy_reason
        assert any(term in policy_text for term in ["EXTERNAL_EVIDENCE_SHIFT", "UNRESOLVED_RIGHTS_DISPUTE"])
        assert "205" in policy_text  # 17 U.S.C. § 205 copyright assignment recording

        # System recommendation
        assert exp.system_recommendation == "REVALIDATE"


# =============================================================================
# 3. TEST THREE REVIEW ACTIONS
# =============================================================================

class TestThreeReviewActions:
    """
    Tests the three distinct review actions:
    - re_attest on Item 11: transitions state to RE_ATTESTED, status to APPROVED, generates SupersessionEvent.
    - reject on Item 12: transitions state to EXCEPTION, status to REJECTED, generates SupersessionEvent.
    - exception (leave as exception): marks state as EXCEPTION, generates SupersessionEvent.
    """

    def test_re_attest_action_transitions_item_11_to_re_attested_and_approved(self):
        """re_attest on Item 11: transitions state to RE_ATTESTED, status to APPROVED, generates SupersessionEvent."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            reviewer=DemoReviewer(name="Sarah Jenkins, Esq."),
            counsel_rationale="Artwork verified in public domain via Library of Congress renewal records; re-attested.",
        )

        assert isinstance(event, SupersessionEvent)
        assert event.action == ReviewAction.RE_ATTEST
        assert event.new_state == DecisionState.RE_ATTESTED
        assert event.new_status == DecisionStatus.APPROVED
        assert event.prior_decision_id == "dec_v7_poster_noir"
        assert event.stable_lineage_key == "poster_noir_detective_magazine"
        assert "public domain" in event.counsel_rationale.lower()

    def test_reject_action_transitions_item_12_to_exception_and_rejected(self):
        """reject on Item 12: transitions state to EXCEPTION, status to REJECTED, generates SupersessionEvent."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="music_cue_midnight_serenade",
            action=ReviewAction.REJECT,
            reviewer=DemoReviewer(name="Sarah Jenkins, Esq."),
            counsel_rationale="Adverse Vanguard Media rights assignment confirmed; cue rejected and excluded from master audio.",
        )

        assert isinstance(event, SupersessionEvent)
        assert event.action == ReviewAction.REJECT
        assert event.new_state == DecisionState.EXCEPTION
        assert event.new_status == DecisionStatus.REJECTED
        assert event.prior_decision_id == "dec_v7_music_midnight"
        assert event.stable_lineage_key == "music_cue_midnight_serenade"
        assert "rejected" in event.counsel_rationale.lower()

    def test_exception_action_leaves_claim_as_exception(self):
        """exception (leave as exception): marks state as EXCEPTION, generates SupersessionEvent."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="music_cue_midnight_serenade",
            action=ReviewAction.EXCEPTION,
            reviewer=DemoReviewer(name="Sarah Jenkins, Esq."),
            counsel_rationale="Rights dispute pending publisher resolution; leaving as unresolved exception on Form E&O-2026.",
        )

        assert isinstance(event, SupersessionEvent)
        assert event.action == ReviewAction.EXCEPTION
        assert event.new_state == DecisionState.EXCEPTION
        assert event.prior_decision_id == "dec_v7_music_midnight"


# =============================================================================
# 4. TEST NAMED DEMO REVIEWER
# =============================================================================

class TestNamedDemoReviewer:
    """
    Reviewer identity contains name, title, and is_fictional_demo == True.
    Disclaimers state 'DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE'.
    """

    def test_reviewer_identity_contains_name_title_and_fictional_flag(self):
        """Reviewer identity contains name, title, and is_fictional_demo == True."""
        reviewer = DemoReviewer(
            name="Sarah Jenkins, Esq.",
            title="Clearance Counsel (Demo)",
            is_fictional_demo=True,
        )

        assert reviewer.name == "Sarah Jenkins, Esq."
        assert reviewer.title == "Clearance Counsel (Demo)"
        assert reviewer.is_fictional_demo is True
        assert reviewer.is_fictional_demo == True

    def test_reviewer_disclaimers_state_statutory_demo_notice(self):
        """Disclaimers state 'DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE'."""
        reviewer = DemoReviewer()

        expected_disclaimer = "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE"
        assert reviewer.disclaimer == expected_disclaimer
        assert expected_disclaimer in reviewer.disclaimers

    def test_supersession_event_embeds_demo_reviewer_with_disclaimer(self):
        """SupersessionEvent embeds reviewer identity and disclaimers."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Public domain verified.",
        )

        assert event.reviewer.name
        assert event.reviewer.title
        assert event.reviewer.is_fictional_demo is True
        assert "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE" in event.reviewer.disclaimer


# =============================================================================
# 5. TEST APPEND-ONLY SUPERSESSION EVENT & INSPECTABILITY
# =============================================================================

class TestAppendOnlySupersessionEventAndInspectability:
    """
    - event_id is unique.
    - prior_decision_id links back to original V7 decision and prior decision remains fully inspectable.
    - Audit trail distinguishes AI recommendation (system_recommendation='REVALIDATE') from human counsel decision.
    - event_hash is a valid 64-character SHA-256 hexadecimal string.
    """

    def test_supersession_event_id_uniqueness(self):
        """event_id is unique across multiple events."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event1 = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Public domain approved.",
        )
        event2 = manager.process_review_action(
            stable_lineage_key="music_cue_midnight_serenade",
            action=ReviewAction.REJECT,
            counsel_rationale="Adverse rights assignment.",
        )

        assert event1.event_id != event2.event_id
        assert event1.event_id.startswith("evt_")
        assert event2.event_id.startswith("evt_")

    def test_prior_decision_link_and_inspectability(self):
        """prior_decision_id links back to original V7 decision and prior decision remains fully inspectable."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Approved public domain.",
        )

        # Links back to original V7 decision
        assert event.prior_decision_id == "dec_v7_poster_noir"

        # Prior decision remains fully inspectable
        prior_dec = event.prior_decision or manager.get_prior_decision(event.prior_decision_id)
        assert prior_dec is not None
        assert isinstance(prior_dec, CounselDecision)
        assert prior_dec.decision_id == "dec_v7_poster_noir"
        assert prior_dec.applicable_version_id == "v7"
        assert prior_dec.status == DecisionStatus.APPROVED
        assert "de minimis" in prior_dec.rationale.lower() or "incidental" in prior_dec.rationale.lower()

    def test_audit_trail_distinguishes_ai_recommendation_from_human_action(self):
        """Audit trail distinguishes AI recommendation (system_recommendation='REVALIDATE') from human counsel decision."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Confirmed public domain via Library of Congress renewal records.",
        )

        # AI Recommendation vs Human Decision
        assert event.system_recommendation == "REVALIDATE"
        assert event.action == ReviewAction.RE_ATTEST
        assert event.reviewer.name == "Sarah Jenkins, Esq."
        assert event.action != event.system_recommendation

    def test_event_hash_is_valid_64_character_sha256_hex_string(self):
        """event_hash is a valid 64-character SHA-256 hexadecimal string."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        event = manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Verified.",
        )

        assert isinstance(event.event_hash, str)
        assert len(event.event_hash) == 64, f"Expected 64-char hash, got {len(event.event_hash)}"
        assert re.match(r"^[0-9a-f]{64}$", event.event_hash) is not None

    def test_append_only_event_history_ledger(self):
        """Verifies immutable append-only event ledger and query capability."""
        manager = CounselCheckpointManager()
        manager.clear_history()
        manager.build_review_queue()

        manager.process_review_action(
            stable_lineage_key="poster_noir_detective_magazine",
            action=ReviewAction.RE_ATTEST,
            counsel_rationale="Poster approved.",
        )
        manager.process_review_action(
            stable_lineage_key="music_cue_midnight_serenade",
            action=ReviewAction.REJECT,
            counsel_rationale="Music rejected.",
        )

        history = manager.get_history()
        assert len(history) == 2
        assert history[0].stable_lineage_key == "poster_noir_detective_magazine"
        assert history[1].stable_lineage_key == "music_cue_midnight_serenade"

        # Filter by key
        poster_events = manager.get_history(stable_lineage_key="poster_noir_detective_magazine")
        assert len(poster_events) == 1
        assert poster_events[0].action == ReviewAction.RE_ATTEST


# =============================================================================
# 6. TEST FAIL-CLOSED SAFETY INVARIANT
# =============================================================================

class TestFailClosedSafetyInvariant:
    """
    Asserts that the system cannot label a stale decision approved without an allowed
    carry-forward rule or explicit human action (raises error or rejects unauthenticated approval).
    """

    def test_unauthenticated_approval_attempt_raises_error(self):
        """Asserts unauthenticated approval attempt raises UnauthorizedApprovalError."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        with pytest.raises(UnauthorizedApprovalError):
            manager.apply_unauthenticated_approval("poster_noir_detective_magazine")

    def test_empty_reviewer_name_fails_closed(self):
        """Attempting re-attestation with empty reviewer name raises UnauthorizedApprovalError."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        with pytest.raises(UnauthorizedApprovalError):
            manager.process_review_action(
                stable_lineage_key="poster_noir_detective_magazine",
                action=ReviewAction.RE_ATTEST,
                reviewer=DemoReviewer(name=""),
                counsel_rationale="Valid rationale.",
            )

    def test_blank_rationale_on_re_attest_fails_closed(self):
        """Attempting re-attest with empty rationale raises UnauthorizedApprovalError."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        with pytest.raises(UnauthorizedApprovalError):
            manager.process_review_action(
                stable_lineage_key="poster_noir_detective_magazine",
                action=ReviewAction.RE_ATTEST,
                counsel_rationale="   ",  # whitespace only
            )

    def test_invalid_action_fails_closed(self):
        """Passing an invalid or automated approval action raises ValueError or FailClosedSecurityViolation."""
        manager = CounselCheckpointManager()
        manager.build_review_queue()

        with pytest.raises((ValueError, FailClosedSecurityViolation)):
            manager.process_review_action(
                stable_lineage_key="poster_noir_detective_magazine",
                action="auto_approve_bypass",
                counsel_rationale="Automated bypass attempt.",
            )


# =============================================================================
# 7. TEST FASTAPI REVIEW ENDPOINTS
# =============================================================================

class TestFastAPIReviewEndpoints:
    """
    Tests FastAPI Review Endpoints:
    - GET /api/review/queue
    - POST /api/review/action
    - GET /api/review/history
    """

    @pytest.fixture(autouse=True, scope="class")
    def ensure_clean_state(self):
        counsel_checkpoint_manager.reset()
        yield
        counsel_checkpoint_manager.reset()

    def test_get_review_queue_endpoint(self):
        """GET /api/review/queue returns strictly stale claims with 4D explanations."""
        res = client.get("/api/review/queue")
        assert res.status_code == 200
        data = res.json()

        assert "items" in data
        assert data["total_stale_count"] == 2
        assert len(data["items"]) == 2

        keys = [item["stable_lineage_key"] for item in data["items"]]
        assert "poster_noir_detective_magazine" in keys
        assert "music_cue_midnight_serenade" in keys

        for item in data["items"]:
            assert item["current_state"] == "stale"
            assert "explanation_4d" in item
            assert "prior_decision" in item
            assert item["explanation_4d"]["system_recommendation"] == "REVALIDATE"

    def test_post_review_action_endpoint_re_attest(self):
        """POST /api/review/action executes re_attest on Item 11."""
        payload = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "Verified public domain via LOC historical records; cleared under Copyright Act.",
            "reviewer": {
                "name": "Sarah Jenkins, Esq.",
                "title": "Clearance Counsel (Demo)",
                "is_fictional_demo": True,
                "disclaimer": "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE",
            },
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["action"] == "re_attest"
        assert data["stable_lineage_key"] == "poster_noir_detective_magazine"
        assert data["new_state"] == "re_attested"
        assert data["new_status"] == "approved"
        assert data["event_id"].startswith("evt_")
        assert len(data["event_hash"]) == 64
        assert data["system_recommendation"] == "REVALIDATE"

    def test_post_review_action_endpoint_reject(self):
        """POST /api/review/action executes reject on Item 12."""
        payload = {
            "stable_lineage_key": "music_cue_midnight_serenade",
            "action": "reject",
            "counsel_rationale": "Adverse sync rights assignment to Vanguard Media; cue rejected and excluded.",
            "reviewer": {
                "name": "Sarah Jenkins, Esq.",
                "title": "Clearance Counsel (Demo)",
                "is_fictional_demo": True,
            },
        }
        res = client.post("/api/review/action", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "success"
        assert data["action"] == "reject"
        assert data["new_state"] == "exception"
        assert data["new_status"] == "rejected"

    def test_post_review_action_fail_closed_validation(self):
        """POST /api/review/action rejects unauthenticated or empty rationale approvals."""
        # Missing rationale
        payload_empty_rationale = {
            "stable_lineage_key": "poster_noir_detective_magazine",
            "action": "re_attest",
            "counsel_rationale": "",
        }
        res_empty = client.post("/api/review/action", json=payload_empty_rationale)
        assert res_empty.status_code == 403

        # Missing stable_lineage_key
        payload_missing_key = {
            "action": "re_attest",
            "counsel_rationale": "Some rationale",
        }
        res_key = client.post("/api/review/action", json=payload_missing_key)
        assert res_key.status_code == 400

    def test_get_review_history_endpoint(self):
        """GET /api/review/history returns append-only audit trail."""
        res = client.get("/api/review/history")
        assert res.status_code == 200
        history = res.json()

        assert isinstance(history, list)
        assert len(history) >= 2

        for event in history:
            assert "event_id" in event
            assert "prior_decision_id" in event
            assert "action" in event
            assert "event_hash" in event
            assert len(event["event_hash"]) == 64
            assert event["system_recommendation"] == "REVALIDATE"
            assert event["reviewer"]["is_fictional_demo"] is True
