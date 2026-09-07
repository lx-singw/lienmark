"""
tests/test_projector.py

Tests for Lienmark Core State Projector Engine.
Verifies event-sourcing state reconstruction, pure functional folding,
SUPERSEDED handling, and bit-for-bit determinism over 100+ events.
"""

from __future__ import annotations

import copy
from typing import List
import pytest

from backend.core.projector import (
    AuditEvent,
    InvalidEventError,
    ProductionStateProjection,
    StateProjector,
)
from backend.storage.ledger import CryptographicLedger


def test_empty_event_stream() -> None:
    """Verify projecting an empty event stream produces a valid default projection."""
    proj = StateProjector.project_events([])
    assert isinstance(proj, ProductionStateProjection)
    assert proj.production_id == "" and proj.total_events_projected == 0
    assert len(proj.state_digest) == 64
    assert StateProjector.verify_projection_determinism([]) is True


def test_single_claim_lifecycle() -> None:
    """Verify claim creation and subsequent update correctly fold into state."""
    events = [
        AuditEvent(event_id="evt_01", production_id="p101", action="CLAIM_CREATED", sequence_number=1, claim_id="c1", payload={"scene": 12}),
        AuditEvent(event_id="evt_02", production_id="p101", action="CLAIM_UPDATED", sequence_number=2, claim_id="c1", payload={"scene": 14}),
    ]
    proj = StateProjector.project_events(events)
    assert proj.production_id == "p101" and proj.total_events_projected == 2
    assert proj.claims["c1"]["scene"] == 14 and "last_updated_at" in proj.claims["c1"]


def test_findings_attachment_and_update() -> None:
    """Verify finding attachment and finding deduplication/updates on a claim."""
    events = [
        AuditEvent(event_id="e1", production_id="p1", action="CLAIM_CREATED", sequence_number=1, claim_id="c1", payload={"asset": "art"}),
        AuditEvent(event_id="e2", production_id="p1", action="FINDING_ATTACHED", sequence_number=2, claim_id="c1", payload={"finding_id": "f1", "status": "MATCH"}),
        AuditEvent(event_id="e3", production_id="p1", action="FINDING_ATTACHED", sequence_number=3, claim_id="c1", payload={"finding_id": "f1", "status": "CONFIRMED"}),
        AuditEvent(event_id="e4", production_id="p1", action="FINDING_ATTACHED", sequence_number=4, claim_id="c1", payload={"finding_id": "f2", "status": "CLEAR"}),
    ]
    findings = StateProjector.project_events(events).findings["c1"]
    assert len(findings) == 2
    assert next(f for f in findings if f["finding_id"] == "f1")["status"] == "CONFIRMED"


def test_risk_score_and_attorney_decisions() -> None:
    """Verify risk scores and attorney decisions materialize on the projected state."""
    events = [
        AuditEvent(event_id="e1", production_id="pt", action="CLAIM_CREATED", sequence_number=1, claim_id="cm", payload={"title": "Song"}),
        AuditEvent(event_id="e2", production_id="pt", action="SCORE_ASSIGNED", sequence_number=2, claim_id="cm", payload={"score": "LOW_RISK"}),
        AuditEvent(event_id="e3", production_id="pt", action="ATTORNEY_APPROVAL", sequence_number=3, claim_id="cm", payload={"status": "CLEARED"}),
    ]
    proj = StateProjector.project_events(events)
    assert proj.risk_scores["cm"]["score"] == "LOW_RISK"
    assert proj.attorney_decisions["cm"]["status"] == "CLEARED"


def test_superseded_claim_handling() -> None:
    """Verify SUPERSEDED actions mark claims, findings, and decisions as superseded."""
    orig = AuditEvent(event_id="es", production_id="pc", action="SUPERSEDED", sequence_number=3, claim_id="co", payload={"new_claim_id": "cn"})
    snapshot = copy.deepcopy(orig.payload)
    events = [
        AuditEvent(event_id="ec", production_id="pc", action="CLAIM_CREATED", sequence_number=1, claim_id="co", payload={"scene": 22}),
        AuditEvent(event_id="ef", production_id="pc", action="FINDING_ATTACHED", sequence_number=2, claim_id="co", payload={"finding_id": "f9"}),
        orig,
    ]
    proj = StateProjector.project_events(events)
    assert "co" in proj.superseded_claims and proj.claims["co"]["is_superseded"] is True
    assert proj.claims["co"]["superseded_by"] == "cn"
    assert proj.findings["co"][0]["is_superseded"] is True
    assert orig.payload == snapshot


def test_pure_functional_folding_immutability() -> None:
    """Verify that applying an event produces a new state without mutating prior state."""
    s0 = ProductionStateProjection(production_id="pi")
    evt = AuditEvent(event_id="e1", production_id="pi", action="CLAIM_CREATED", sequence_number=1, claim_id="ci", payload={"asset": "car"})
    s1 = StateProjector.apply_event(s0, evt)
    assert s0.total_events_projected == 0 and len(s0.claims) == 0
    assert s1.total_events_projected == 1 and "ci" in s1.claims
    assert s1.state_digest != s0.state_digest


def _generate_100_events(prod_id: str) -> List[AuditEvent]:
    """Generates 100 diverse synthetic clearance events."""
    evts: List[AuditEvent] = []
    for i in range(1, 101):
        ck = f"claim_{i % 10}"
        if i <= 30:
            evts.append(AuditEvent(event_id=f"e_{i:03d}", production_id=prod_id, action="CLAIM_CREATED", sequence_number=i, claim_id=ck, payload={"idx": i}))
        elif i <= 60:
            evts.append(AuditEvent(event_id=f"e_{i:03d}", production_id=prod_id, action="FINDING_ATTACHED", sequence_number=i, claim_id=ck, payload={"finding_id": f"f_{i}"}))
        elif i <= 80:
            evts.append(AuditEvent(event_id=f"e_{i:03d}", production_id=prod_id, action="SCORE_ASSIGNED", sequence_number=i, claim_id=ck, payload={"score": "CLEARED"}))
        elif i <= 90:
            evts.append(AuditEvent(event_id=f"e_{i:03d}", production_id=prod_id, action="SUPERSEDED", sequence_number=i, claim_id=ck, payload={"superseded_claim_id": ck}))
        else:
            evts.append(AuditEvent(event_id=f"e_{i:03d}", production_id=prod_id, action="BUDGET_SPENT", sequence_number=i, payload={"amount_usd": 0.04}))
    return evts


def test_100_historical_events_determinism() -> None:
    """Simulate 100 chronological clearance events and verify bit-for-bit determinism."""
    p_id = "prod_feature_alpha"
    events = _generate_100_events(p_id)
    assert len(events) == 100

    p1 = StateProjector.project_events(events)
    p2 = StateProjector.project_events(events)
    assert StateProjector.verify_projection_determinism(events) is True
    assert p1.state_digest == p2.state_digest and len(p1.state_digest) == 64
    assert p1.total_events_projected == 100 and p1.last_sequence_number == 100
    assert len(p1.budget_events) == 10 and len(p1.superseded_claims) > 0


def test_budget_events_tracking() -> None:
    """Verify budget spend events are recorded chronologically in projected state."""
    events = [
        AuditEvent(event_id="eb1", production_id="pb", action="BUDGET_SPENT", sequence_number=1, payload={"amount_usd": 0.05}),
        AuditEvent(event_id="eb2", production_id="pb", action="BUDGET_CAP_INCREASED", sequence_number=2, payload={"amount_usd": 500.0}),
    ]
    proj = StateProjector.project_events(events)
    assert len(proj.budget_events) == 2 and proj.budget_events[0]["amount_usd"] == 0.05


def test_duck_typed_and_dict_events() -> None:
    """Verify StateProjector accepts dictionaries and duck-typed objects."""
    devts = [
        {"event_id": "ed1", "production_id": "pduck", "action": "CLAIM_CREATED", "sequence_number": 1, "claim_id": "cd1", "payload": {"title": "Poster"}},
        {"event_id": "ed2", "production_id": "pduck", "action": "SCORE_ASSIGNED", "sequence_number": 2, "claim_id": "cd1", "payload": {"score": "CLEARED"}},
    ]
    proj = StateProjector.project_events(devts)
    assert proj.production_id == "pduck" and proj.total_events_projected == 2
    assert "cd1" in proj.claims and proj.risk_scores["cd1"]["score"] == "CLEARED"


def test_invalid_event_error() -> None:
    """Verify invalid event objects raise InvalidEventError."""
    with pytest.raises(InvalidEventError):
        StateProjector.apply_event(ProductionStateProjection(), 12345)


def test_cryptographic_ledger_stream_projection() -> None:
    """Verify direct projection of event streams produced by CryptographicLedger."""
    ledger = CryptographicLedger()
    pid, tid = "prod_ledger_stream", "tenant_hollywood"
    ledger.initialize_production_ledger(tenant_id=tid, production_id=pid, actor_id="admin")
    e1 = ledger.append_event(tenant_id=tid, production_id=pid, actor_id="a1", action_type="CLAIM_CREATED", payload={"claim_id": "c_led", "desc": "Sign"})
    ledger.append_event(tenant_id=tid, production_id=pid, actor_id="a2", action_type="FINDING_ATTACHED", payload={"claim_id": "c_led", "finding_id": "f_led"})
    ledger.record_supersession(tenant_id=tid, production_id=pid, actor_id="c1", superseded_event_id=e1.event_id, superseding_payload={"claim_id": "c_led"})

    events = ledger.get_events(pid)
    assert len(events) == 4
    proj = StateProjector.project_events(events)
    assert proj.production_id == pid and proj.total_events_projected == 4
    assert proj.claims["c_led"]["is_superseded"] is True
    assert StateProjector.verify_projection_determinism(events) is True
