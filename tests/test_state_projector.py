"""Tests for StateProjector: deterministic event replay and state projection."""
from __future__ import annotations

import copy
from typing import Any, Dict, List
import pytest

from backend.core.projector import (
    AuditEvent as CoreAuditEvent,
    InvalidEventError,
    ProductionStateProjection,
    StateProjector,
    compute_state_digest,
)
from backend.storage.ledger import CryptographicLedger


class TestEventSequenceReplay:
    """Validates full event replay across claims, findings, risk scores, and decisions."""

    def test_replay_claims_findings_scores_decisions(self) -> None:
        p = "p_rep_1"
        events = [
            CoreAuditEvent(production_id=p, action="CLAIM_RECORDED", sequence_number=1, claim_id="c_101", payload={"claim_id": "c_101", "claim_text": "Batman"}),
            CoreAuditEvent(production_id=p, action="FINDING_DISCOVERED", sequence_number=2, claim_id="c_101", payload={"finding_id": "f_501", "risk_level": "HIGH"}),
            CoreAuditEvent(production_id=p, action="RISK_SCORED", sequence_number=3, claim_id="c_101", payload={"composite_score": 0.82}),
            CoreAuditEvent(production_id=p, action="ATTORNEY_APPROVED", sequence_number=4, claim_id="c_101", payload={"decision": "APPROVED"}),
            CoreAuditEvent(production_id=p, action="BUDGET_SPEND_RECORDED", sequence_number=5, payload={"amount": 0.035}),
        ]
        state = StateProjector.project_events(events)
        assert state.production_id == p and state.total_events_projected == 5
        assert state.claims["c_101"]["claim_text"] == "Batman"
        assert state.findings["c_101"][0]["finding_id"] == "f_501"
        assert state.risk_scores["c_101"]["composite_score"] == 0.82
        assert state.attorney_decisions["c_101"]["decision"] == "APPROVED"
        assert state.budget_events[0]["amount"] == 0.035
        assert len(state.state_digest) == 64


    def test_finding_updates_in_place_by_id(self) -> None:
        events = [
            {
                "production_id": "p_f_upd",
                "action": "FINDING_DISCOVERED",
                "sequence_number": 1,
                "claim_id": "c_1",
                "payload": {"finding_id": "f_1", "status": "PENDING"},
            },
            {
                "production_id": "p_f_upd",
                "action": "FINDING_UPDATED",
                "sequence_number": 2,
                "claim_id": "c_1",
                "payload": {"finding_id": "f_1", "status": "CONFIRMED"},
            },
        ]
        state = StateProjector.project_events(events)
        assert len(state.findings["c_1"]) == 1
        assert state.findings["c_1"][0]["status"] == "CONFIRMED"

    def test_attorney_override_event_updates_decision(self) -> None:
        events = [
            {"production_id": "p_ov", "action": "ATTORNEY_APPROVAL", "sequence_number": 1, "claim_id": "c_9", "payload": {"decision": "CLEARED"}},
            {"production_id": "p_ov", "action": "ATTORNEY_OVERRIDE", "sequence_number": 2, "claim_id": "c_9", "payload": {"decision": "REJECTED"}},
        ]
        state = StateProjector.project_events(events)
        assert state.attorney_decisions["c_9"]["decision"] == "REJECTED"


class TestProjectionDeterminism:
    """Validates bit-for-bit identical state digest generation."""

    def test_identical_event_stream_yields_identical_digest(self) -> None:
        events = [
            CoreAuditEvent(
                production_id="p_det",
                action="CLAIM_RECORDED",
                sequence_number=i,
                claim_id=f"c_{i}",
                payload={"index": i, "title": f"Asset {i}"},
                timestamp="2026-01-01T00:00:00Z",
            )
            for i in range(1, 11)
        ]
        proj_1 = StateProjector.project_events(events)
        proj_2 = StateProjector.project_events(events)
        assert proj_1.state_digest == proj_2.state_digest
        assert len(proj_1.state_digest) == 64
        assert StateProjector.verify_projection_determinism(events) is True

    def test_empty_event_stream_determinism(self) -> None:
        empty_state = StateProjector.project_events([])
        assert empty_state.total_events_projected == 0
        assert len(empty_state.state_digest) == 64
        assert empty_state.state_digest == compute_state_digest(ProductionStateProjection())

    def test_out_of_order_sequence_sorted_deterministically(self) -> None:
        ts = "2026-01-01T00:00:00Z"
        e1 = {"event_id": "e1", "production_id": "p_sort", "action": "CLAIM", "sequence_number": 1, "claim_id": "c1", "payload": {}, "timestamp": ts}
        e2 = {"event_id": "e2", "production_id": "p_sort", "action": "CLAIM", "sequence_number": 2, "claim_id": "c2", "payload": {}, "timestamp": ts}
        e3 = {"event_id": "e3", "production_id": "p_sort", "action": "CLAIM", "sequence_number": 3, "claim_id": "c3", "payload": {}, "timestamp": ts}

        in_order = StateProjector.project_events([e1, e2, e3])
        shuffled = StateProjector.project_events([e3, e1, e2])

        assert in_order.state_digest == shuffled.state_digest
        assert in_order.last_sequence_number == 3

    def test_different_payloads_yield_different_digests(self) -> None:
        ev1 = [{"event_id": "e1", "production_id": "p1", "action": "CLAIM", "sequence_number": 1, "payload": {"val": 10}, "timestamp": "2026-01-01T00:00:00Z"}]
        ev2 = [{"event_id": "e1", "production_id": "p1", "action": "CLAIM", "sequence_number": 1, "payload": {"val": 99}, "timestamp": "2026-01-01T00:00:00Z"}]
        digest1 = StateProjector.project_events(ev1).state_digest
        digest2 = StateProjector.project_events(ev2).state_digest
        assert digest1 != digest2


class TestSupersessionStateHandling:
    """Validates supersession marking without historical event alteration."""

    def test_claim_supersession_marks_state_superseded(self) -> None:
        events = [
            {"production_id": "p_sup", "action": "CLAIM_RECORDED", "sequence_number": 1, "claim_id": "c_old", "payload": {"claim_id": "c_old"}},
            {"production_id": "p_sup", "action": "FINDING_DISCOVERED", "sequence_number": 2, "claim_id": "c_old", "payload": {"finding_id": "f_old"}},
            {"production_id": "p_sup", "action": "SUPERSEDED_CLAIM", "sequence_number": 3, "claim_id": "c_old", "payload": {"superseded_claim_id": "c_old", "new_claim_id": "c_new"}},
        ]
        state = StateProjector.project_events(events)
        assert "c_old" in state.superseded_claims
        assert state.claims["c_old"]["is_superseded"] is True
        assert state.claims["c_old"]["superseded_by"] == "c_new"
        assert state.findings["c_old"][0]["is_superseded"] is True

    def test_supersession_preserves_input_events_unmutated(self) -> None:
        raw_events = [
            {"production_id": "p", "action": "CLAIM", "sequence_number": 1, "claim_id": "c1", "payload": {"k": "v"}},
            {"production_id": "p", "action": "SUPERSEDED", "sequence_number": 2, "claim_id": "c1", "payload": {"superseded_claim_id": "c1"}},
        ]
        snapshot_before = copy.deepcopy(raw_events)
        StateProjector.project_events(raw_events)
        assert raw_events == snapshot_before

    def test_finding_supersession_by_finding_id(self) -> None:
        events = [
            {"production_id": "p_fs", "action": "FINDING_RECORDED", "sequence_number": 1, "claim_id": "c_s", "payload": {"finding_id": "f_tgt"}},
            {"production_id": "p_fs", "action": "SUPERSEDED_FINDING", "sequence_number": 2, "payload": {"superseded_finding_id": "f_tgt"}},
        ]
        state = StateProjector.project_events(events)
        target = next(f for f in state.findings["c_s"] if f["finding_id"] == "f_tgt")
        assert target["is_superseded"] is True


class TestEventNormalizationAndErrors:
    """Validates compatibility with raw dicts, CoreAuditEvent, and CryptographicLedger events."""

    def test_cryptographic_ledger_audit_event_compatibility(self) -> None:
        ledger = CryptographicLedger()
        g = ledger.initialize_production_ledger("org_test", "prod_ledger_norm", "actor_0")
        c1 = ledger.append_event(
            tenant_id="org_test",
            production_id="prod_ledger_norm",
            actor_id="actor_0",
            action_type="CLAIM_INGESTED",
            payload={"claim_id": "c_crypt", "name": "Audio Stem"},
        )
        state = StateProjector.project_events([g, c1])
        assert state.production_id == "prod_ledger_norm"
        assert "c_crypt" in state.claims
        assert state.total_events_projected == 2

    def test_invalid_event_type_raises_error(self) -> None:
        with pytest.raises(InvalidEventError, match="Unsupported event type"):
            StateProjector.project_events([12345])  # type: ignore[list-item]
