"""
Unit and Integration Tests for Cluster 2 Remediation
Findings 2, 7 & 8:
- Tamper-Free SHA-256 Digest (Finding 8)
- Cryptographic Ledger Parent Chaining (Finding 8)
- Read-Only Review Queue & Preserved Supersession Chains (Finding 7)
"""

import json
import hashlib
import pytest
from backend.domain.models import (
    ReviewAction,
    ReviewerIdentity,
    SupersessionEvent,
    DecisionState,
    DecisionStatus,
    CounselDecision,
    UnauthorizedApprovalError,
)
from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    counsel_checkpoint_manager,
)


class TestTamperFreeSha256Digest:
    """Verifies that the canonical SHA-256 event digest covers all 15 critical fields."""

    def test_canonical_digest_payload_and_hashing(self):
        event_id = "evt_test_123"
        prior_dec = "dec_v7_test"
        new_dec = "dec_v8_test_999"
        target_v = "v8"
        lineage_key = "poster_noir_detective_magazine"
        action = "re_attest"
        new_st = "re_attested"
        new_stat = "approved"
        sys_rec = "REVALIDATE"
        rationale = "Legitimate clearance attestation."
        ts = "2026-09-06T12:00:00Z"
        parent_hash = "0" * 64
        reviewer = ReviewerIdentity(
            reviewer_id="counsel_001",
            name="Sarah Jenkins, Esq.",
            title="Lead Clearance Counsel",
            organization="Lienmark Legal Partners LLP",
        )
        citations = [
            {"source_url": "https://cocatalog.loc.gov/1", "payload_hash": "hash1", "provider_call_id": "p1"},
            {"source_url": "https://cocatalog.loc.gov/2", "payload_hash": "hash2", "provider_call_id": "p2"},
        ]
        deps = ["dep_b", "dep_a"]

        # Compute using static method
        computed_hash = SupersessionEvent.compute_canonical_hash(
            event_id=event_id,
            prior_decision_id=prior_dec,
            new_decision_id=new_dec,
            target_version_id=target_v,
            stable_lineage_key=lineage_key,
            action=action,
            new_state=new_st,
            new_status=new_stat,
            system_recommendation=sys_rec,
            counsel_rationale=rationale,
            timestamp=ts,
            parent_event_hash=parent_hash,
            reviewer=reviewer,
            evidence_citations=citations,
            changed_dependencies=deps,
        )

        assert len(computed_hash) == 64

        # Manually compute matching reference payload
        manual_reviewer = {
            "name": "Sarah Jenkins, Esq.",
            "organization": "Lienmark Legal Partners LLP",
            "reviewer_id": "counsel_001",
            "title": "Lead Clearance Counsel",
        }
        manual_citations = sorted(
            [
                {"payload_hash": "hash1", "provider_call_id": "p1", "source_url": "https://cocatalog.loc.gov/1"},
                {"payload_hash": "hash2", "provider_call_id": "p2", "source_url": "https://cocatalog.loc.gov/2"},
            ],
            key=lambda x: (x["source_url"], x["payload_hash"], x["provider_call_id"]),
        )
        manual_deps = sorted(["dep_b", "dep_a"])

        manual_payload = {
            "action": action,
            "changed_dependencies": manual_deps,
            "counsel_rationale": rationale,
            "event_id": event_id,
            "evidence_citations": manual_citations,
            "new_decision_id": new_dec,
            "new_state": new_st,
            "new_status": new_stat,
            "parent_event_hash": parent_hash,
            "prior_decision_id": prior_dec,
            "reviewer": manual_reviewer,
            "stable_lineage_key": lineage_key,
            "system_recommendation": sys_rec,
            "target_version_id": target_v,
            "timestamp": ts,
        }
        manual_json = json.dumps(manual_payload, sort_keys=True, separators=(",", ":"))
        manual_hash = hashlib.sha256(manual_json.encode("utf-8")).hexdigest()

        assert computed_hash == manual_hash

    def test_tampering_reviewer_fields_invalidates_hash(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_tamper_test")

        _, evt = manager.record_counsel_action(
            session_id="sess_tamper_test",
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Authentic legal rationale.",
        )

        assert manager.verify_ledger_integrity("sess_tamper_test")["is_valid"] is True

        # Tamper reviewer organization
        ctx = manager._get_or_create_run_context("sess_tamper_test")
        ctx.supersession_events[0].reviewer.organization = "Rogue Impersonator LLC"

        result = manager.verify_ledger_integrity("sess_tamper_test")
        assert result["is_valid"] is False
        assert "Tampered digest at index 0" in result["error"]

    def test_tampering_citations_or_dependencies_invalidates_hash(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_tamper_cites")

        _, evt = manager.record_counsel_action(
            session_id="sess_tamper_cites",
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Authentic legal rationale.",
            changed_dependencies=["dep1"],
        )

        assert manager.verify_ledger_integrity("sess_tamper_cites")["is_valid"] is True

        # Tamper changed_dependencies
        ctx = manager._get_or_create_run_context("sess_tamper_cites")
        ctx.supersession_events[0].changed_dependencies.append("forged_dependency")

        result = manager.verify_ledger_integrity("sess_tamper_cites")
        assert result["is_valid"] is False
        assert "Tampered digest at index 0" in result["error"]


class TestCryptographicLedgerParentChaining:
    """Verifies strict unbroken parent chaining and genesis hash enforcement."""

    def test_unbroken_parent_chaining_sequential_actions(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_chain_seq")

        _, evt1 = manager.record_counsel_action(
            session_id="sess_chain_seq",
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Pass 1",
        )
        _, evt2 = manager.record_counsel_action(
            session_id="sess_chain_seq",
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="Pass 2",
        )

        assert evt1.parent_event_hash == CounselCheckpointManager.GENESIS_PARENT_HASH
        assert evt2.parent_event_hash == evt1.event_hash

        integrity = manager.verify_ledger_integrity("sess_chain_seq")
        assert integrity["is_valid"] is True
        assert integrity["event_count"] == 2
        assert integrity["chain_head_hash"] == evt2.event_hash

    def test_none_or_empty_parent_hash_fails_verification_immediately(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_broken_parent")

        manager.record_counsel_action(
            session_id="sess_broken_parent",
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Pass 1",
        )

        ctx = manager._get_or_create_run_context("sess_broken_parent")
        # Mutate parent_event_hash to None
        ctx.supersession_events[0].parent_event_hash = None

        result = manager.verify_ledger_integrity("sess_broken_parent")
        assert result["is_valid"] is False
        assert "Broken chain link at index 0" in result["error"]

        # Mutate to empty string
        ctx.supersession_events[0].parent_event_hash = ""
        result_empty = manager.verify_ledger_integrity("sess_broken_parent")
        assert result_empty["is_valid"] is False
        assert "Broken chain link at index 0" in result_empty["error"]

    def test_mismatched_parent_hash_fails_verification(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_mismatch_parent")

        manager.record_counsel_action(
            session_id="sess_mismatch_parent",
            action=ReviewAction.RE_ATTEST,
            lineage_key="poster_noir_detective_magazine",
            rationale="Pass 1",
        )
        manager.record_counsel_action(
            session_id="sess_mismatch_parent",
            action=ReviewAction.EXCEPTION,
            lineage_key="music_cue_midnight_serenade",
            rationale="Pass 2",
        )

        ctx = manager._get_or_create_run_context("sess_mismatch_parent")
        # Break link 2
        ctx.supersession_events[1].parent_event_hash = "f" * 64

        result = manager.verify_ledger_integrity("sess_mismatch_parent")
        assert result["is_valid"] is False
        assert result["tampered_index"] == 1
        assert "Broken chain link at index 1" in result["error"]


class TestReadOnlyQueueAndPreservedSupersessionChains:
    """Verifies Finding 7: Queue inspection is strictly read-only and preserves supersession chains."""

    def test_queue_inspection_does_not_mutate_decision_states(self):
        manager = CounselCheckpointManager()
        sess_id = "sess_readonly_test"
        manager.reset(sess_id)
        ctx = manager._get_or_create_run_context(sess_id)

        # Baseline states before inspection
        states_before = dict(ctx.decision_states)

        # Inspect review queue multiple times
        q1 = manager.get_review_queue(session_id=sess_id)
        q2 = manager.get_review_queue(session_id=sess_id)

        assert len(q1.items) == 2
        assert len(q2.items) == 2

        # Decision states must remain identical and unmutated by read operations
        assert ctx.decision_states == states_before

    def test_queue_inspection_reflects_latest_counsel_decisions_without_overwriting(self):
        manager = CounselCheckpointManager()
        sess_id = "sess_supersession_preserve"
        manager.reset(sess_id)
        ctx = manager._get_or_create_run_context(sess_id)

        key = "poster_noir_detective_magazine"

        # Apply counsel action
        dec, evt = manager.record_counsel_action(
            session_id=sess_id,
            action=ReviewAction.RE_ATTEST,
            lineage_key=key,
            rationale="Counsel attestation verified in public domain.",
        )

        # Ensure ctx.prior_decisions holds the latest decision
        assert ctx.prior_decisions[key].decision_id == dec.decision_id
        latest_id = dec.decision_id

        # Inspect review queue
        q = manager.get_review_queue(session_id=sess_id)

        # Queue inspection MUST NOT overwrite ctx.prior_decisions with baseline fixtures!
        assert ctx.prior_decisions[key].decision_id == latest_id

        # The queue item must reflect the latest decision and counsel state
        item = next(it for it in q.items if it.stable_lineage_key == key)
        assert item.current_state == DecisionState.RE_ATTESTED
        assert item.prior_decision.decision_id == latest_id


class TestCounselActionValidationRules:
    """Verifies fail-closed validation on apply_review_action."""

    def test_empty_rationale_fails_closed(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_val_test")

        with pytest.raises(UnauthorizedApprovalError):
            manager.apply_review_action(
                session_id="sess_val_test",
                action=ReviewAction.RE_ATTEST,
                lineage_key="poster_noir_detective_magazine",
                rationale="   ",
            )

        with pytest.raises(ValueError):
            manager.apply_review_action(
                session_id="sess_val_test",
                action=ReviewAction.REJECT,
                lineage_key="music_cue_midnight_serenade",
                rationale="",
            )

    def test_empty_reviewer_name_fails_closed(self):
        manager = CounselCheckpointManager()
        manager.reset("sess_rev_test")

        with pytest.raises(UnauthorizedApprovalError):
            manager.apply_review_action(
                session_id="sess_rev_test",
                action=ReviewAction.RE_ATTEST,
                lineage_key="poster_noir_detective_magazine",
                rationale="Valid rationale",
                reviewer=ReviewerIdentity(name=""),
            )
