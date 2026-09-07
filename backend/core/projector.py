"""
backend/core/projector.py

Deterministic event-sourcing state projector for Lienmark clearance records.
Sprint 1.3 / Security Specification SEC-SPEC-03-AUDIT-CRYPTO.
"""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Sequence, Set, Union

from backend.core.projector_types import (  # noqa: F401
    AuditEvent,
    InvalidEventError,
    ProductionStateProjection,
    ProjectorError,
    compute_state_digest,
)

logger = logging.getLogger("lienmark.core.projector")


def _to_plain_dict(val: Any) -> Any:
    """Converts immutable payloads or model instances into plain mutable dictionaries."""
    if hasattr(val, "model_dump"):
        return _to_plain_dict(val.model_dump())
    if isinstance(val, dict):
        return {k: _to_plain_dict(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_plain_dict(item) for item in val]
    return val


def _normalize_event(raw: Union[AuditEvent, Dict[str, Any], Any]) -> AuditEvent:
    """Defensively normalizes raw dictionary or external ledger events into an AuditEvent."""
    if isinstance(raw, AuditEvent):
        return raw
    if hasattr(raw, "model_dump"):
        return _normalize_event(_to_plain_dict(raw.model_dump()))
    if hasattr(raw, "__dict__") and not isinstance(raw, dict):
        return _normalize_event(_to_plain_dict(raw.__dict__))
    if isinstance(raw, dict):
        d = _to_plain_dict(raw)
        act = d.get("action") or d.get("action_type") or "ACTION"
        pid = d.get("production_id") or "prod_default"
        payload = d.get("payload", {})
        return AuditEvent(
            production_id=pid,
            action=act,
            sequence_number=d.get("sequence_number", 0),
            claim_id=d.get("claim_id") or payload.get("claim_id"),
            payload=payload,
            actor_id=d.get("actor_id", "system"),
            parent_event_hash=d.get("parent_event_hash") or d.get("previous_event_hash"),
            event_hash=d.get("event_hash") or d.get("entry_hash"),
            event_id=d.get("event_id") or f"evt_{d.get('sequence_number', 0)}",
            timestamp=d.get("timestamp") or d.get("timestamp_utc") or "",
        )
    raise InvalidEventError(f"Unsupported event type for projection: {type(raw)}")



def _apply_claim(claims: Dict[str, Dict[str, Any]], evt: AuditEvent) -> None:
    cid = evt.claim_id or evt.payload.get("claim_id") or evt.payload.get("stable_lineage_key") or evt.event_id
    claims.setdefault(cid, {"claim_id": cid, "history": []}).update({
        **copy.deepcopy(evt.payload),
        "claim_id": cid,
        "last_action": evt.action,
        "last_updated_at": evt.timestamp,
        "is_superseded": False,
    })


def _apply_finding(findings: Dict[str, List[Dict[str, Any]]], evt: AuditEvent) -> None:
    cid = evt.claim_id or evt.payload.get("claim_id") or evt.payload.get("target_claim_id") or "unattached"
    claim_findings = findings.setdefault(cid, [])
    fdata = {**copy.deepcopy(evt.payload), "recorded_at": evt.timestamp, "is_superseded": False}
    fid = fdata.get("finding_id")
    for idx, f in enumerate(claim_findings):
        if f.get("finding_id") == fid:
            claim_findings[idx] = {**f, **fdata}
            break
    else:
        claim_findings.append(fdata)
    findings[cid] = claim_findings


def _apply_superseded(
    claims: Dict[str, Dict[str, Any]],
    findings: Dict[str, List[Dict[str, Any]]],
    decisions: Dict[str, Dict[str, Any]],
    superseded: Set[str],
    evt: AuditEvent,
) -> None:
    cid = evt.claim_id or evt.payload.get("claim_id") or evt.payload.get("superseded_claim_id") or evt.payload.get("stable_lineage_key")
    if cid:
        superseded.add(cid)
        if cid in claims:
            claims[cid].update({"is_superseded": True, "superseded_at": evt.timestamp})
            if "new_claim_id" in evt.payload:
                claims[cid]["superseded_by"] = evt.payload["new_claim_id"]
        for f in findings.get(cid, []):
            f.update({"is_superseded": True, "superseded_at": evt.timestamp})
        if cid in decisions:
            decisions[cid].update({"is_superseded": True, "decision_state": "SUPERSEDED", "superseded_at": evt.timestamp})
    tgt_finding = evt.payload.get("superseded_finding_id") or evt.payload.get("finding_id")
    if tgt_finding and not cid:
        for f_list in findings.values():
            for f in f_list:
                if f.get("finding_id") == tgt_finding:
                    f.update({"is_superseded": True, "superseded_at": evt.timestamp})


def _dispatch_action(
    action_upper: str,
    claims: Dict[str, Dict[str, Any]],
    findings: Dict[str, List[Dict[str, Any]]],
    risk_scores: Dict[str, Dict[str, Any]],
    decisions: Dict[str, Dict[str, Any]],
    superseded: Set[str],
    budget: List[Dict[str, Any]],
    evt: AuditEvent,
) -> None:
    s_ref = evt.payload.get("supersedes_claim_id") or evt.payload.get("supersedes_entry_id")
    if s_ref:
        superseded.add(s_ref)
        if s_ref in claims:
            claims[s_ref]["is_superseded"] = True

    cid = evt.claim_id or evt.payload.get("claim_id") or evt.payload.get("stable_lineage_key") or evt.event_id
    if "SUPERSEDED" in action_upper:
        _apply_superseded(claims, findings, decisions, superseded, evt)
    elif any(k in action_upper for k in ("CLAIM", "INLINE_CLAIM")):
        _apply_claim(claims, evt)
    elif "FINDING" in action_upper:
        _apply_finding(findings, evt)
    elif any(k in action_upper for k in ("SCORE", "RISK")):
        risk_scores[cid] = {**copy.deepcopy(evt.payload), "assessed_at": evt.timestamp}
    elif any(k in action_upper for k in ("ATTORNEY", "DECISION", "APPROVAL", "OVERRIDE", "RE_ATTEST", "REJECT")):
        decisions[cid] = {**copy.deepcopy(evt.payload), "decided_at": evt.timestamp}
    elif "BUDGET" in action_upper or "SPEND" in action_upper:
        budget.append({**copy.deepcopy(evt.payload), "event_id": evt.event_id, "action": evt.action, "timestamp": evt.timestamp})
    elif evt.claim_id:
        claims.setdefault(evt.claim_id, {"claim_id": evt.claim_id}).update(copy.deepcopy(evt.payload))


class StateProjector:
    """
    Deterministic event-sourcing state projector for Lienmark clearance records.
    Implements pure functional folding over immutable audit event streams.
    """

    @classmethod
    def apply_event(
        cls, state: ProductionStateProjection, event: Union[AuditEvent, Dict[str, Any], Any]
    ) -> ProductionStateProjection:
        """Pure functional folding step: folds a single event without mutating inputs."""
        evt = _normalize_event(event)
        claims = {k: copy.deepcopy(v) for k, v in state.claims.items()}
        findings = {k: copy.deepcopy(v) for k, v in state.findings.items()}
        risk_scores = {k: copy.deepcopy(v) for k, v in state.risk_scores.items()}
        decisions = {k: copy.deepcopy(v) for k, v in state.attorney_decisions.items()}
        superseded = set(state.superseded_claims)
        budget = [copy.deepcopy(b) for b in state.budget_events]

        _dispatch_action(evt.action.strip().upper(), claims, findings, risk_scores, decisions, superseded, budget, evt)

        new_proj = ProductionStateProjection(
            production_id=state.production_id or evt.production_id,
            claims=claims,
            findings=findings,
            risk_scores=risk_scores,
            attorney_decisions=decisions,
            superseded_claims=superseded,
            budget_events=budget,
            total_events_projected=state.total_events_projected + 1,
            last_sequence_number=max(state.last_sequence_number, evt.sequence_number),
            state_digest="",
        )
        new_proj.state_digest = compute_state_digest(new_proj)
        return new_proj

    @classmethod
    def project_events(
        cls, events: Sequence[Union[AuditEvent, Dict[str, Any], Any]]
    ) -> ProductionStateProjection:
        """Projects an event stream into a materialized snapshot via pure functional fold."""
        if not events:
            empty = ProductionStateProjection()
            empty.state_digest = compute_state_digest(empty)
            return empty

        norm_events = [_normalize_event(e) for e in events]
        sorted_events = sorted(norm_events, key=lambda e: e.sequence_number)
        prod_id = sorted_events[0].production_id if sorted_events else ""

        current_state = ProductionStateProjection(production_id=prod_id)
        for ev in sorted_events:
            current_state = cls.apply_event(current_state, ev)
        return current_state

    @classmethod
    def verify_projection_determinism(
        cls, events: Sequence[Union[AuditEvent, Dict[str, Any], Any]]
    ) -> bool:
        """Runs the projection twice over the same stream and verifies bit-for-bit digest equality."""
        p1 = cls.project_events(events)
        p2 = cls.project_events(events)
        return p1.state_digest == p2.state_digest and len(p1.state_digest) == 64
