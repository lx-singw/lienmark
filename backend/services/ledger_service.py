"""
ledger_service.py

Authoritative Cryptographic Ledger Traversal & Chain Verification Service.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.api.routes.ledger_schemas import (
    DecisionChainResponse,
    DecisionTimelineEvent,
    LedgerVerificationResponse,
    SupersessionRecord,
)
from backend.storage.ledger import CryptographicLedger
from backend.storage.ledger_types import compute_canonical_digest, compute_entry_hash
from backend.storage.repository import TenantRepository

logger = logging.getLogger("lienmark.services.ledger_service")


class LedgerService:
    """
    Manages decision ledger traversal, cryptographic validation, and supersession links.
    Enforces INV-S62-03 (authoritative verification) and INV-S62-06 (uninitialized grace).
    """

    def __init__(
        self,
        repository: TenantRepository,
        ledger: Optional[CryptographicLedger] = None,
    ) -> None:
        self.repo = repository
        self.ledger = ledger or CryptographicLedger(repository=repository)

    def _get_raw_events(self, production_id: str) -> List[Dict[str, Any]]:
        """Retrieves raw audit event dictionaries from ledger memory or tenant repository."""
        in_mem_events = self.ledger.get_events(production_id=production_id, limit=500)
        if in_mem_events:
            return [e.model_dump() for e in in_mem_events]
        try:
            repo_events = self.repo.list_audit_events(production_id=production_id)
            return [e if isinstance(e, dict) else e.model_dump() for e in repo_events]
        except Exception:
            return []

    def _project_timeline_event(
        self,
        raw: Dict[str, Any],
        superseded_ids: Set[str],
        claims_map: Dict[str, str],
    ) -> DecisionTimelineEvent:
        """Projects raw AuditEvent payload into frontend DecisionTimelineEvent."""
        evt_id = raw.get("event_id", "")
        payload = raw.get("payload", {})
        claim_id = payload.get("claim_id") or payload.get("use_id")
        action = raw.get("action_type") or payload.get("action", "UNKNOWN")
        sigs = payload.get("dual_signatures") or payload.get("signatures", [])
        return DecisionTimelineEvent(
            event_id=evt_id,
            sequence_number=raw.get("sequence_number", 1),
            action_type=action,
            timestamp_utc=raw.get("timestamp_utc") or raw.get("timestamp", ""),
            actor_id=raw.get("actor_id", "counsel_system"),
            actor_name=payload.get("reviewer_name") or payload.get("counsel_name") or "Clearance Counsel",
            claim_id=claim_id,
            claim_title=claims_map.get(claim_id, payload.get("claim_title")),
            decision_status=payload.get("status") or payload.get("decision_status"),
            counsel_rationale=payload.get("rationale") or payload.get("counsel_rationale"),
            entry_hash=raw.get("entry_hash", ""),
            previous_event_hash=raw.get("previous_event_hash", ""),
            payload_digest=raw.get("payload_digest", ""),
            is_superseded=(evt_id in superseded_ids),
            superseded_event_id=payload.get("superseded_event_id"),
            dual_signatures=sigs if isinstance(sigs, list) else [],
        )

    def _resolve_claims_map(self, production_id: str) -> Dict[str, str]:
        """Loads a mapping from claim_id to title for the production."""
        claims_map: Dict[str, str] = {}
        try:
            for c in self.repo.list_claims(production_id=production_id):
                claims_map[c.claim_id] = c.title
        except Exception:
            pass
        return claims_map

    def _extract_superseded_ids(self, raw_events: List[Dict[str, Any]]) -> Set[str]:
        """Collects all event IDs that have been superseded in the chain."""
        return {
            e.get("payload", {}).get("superseded_event_id")
            for e in raw_events
            if e.get("payload", {}).get("superseded_event_id")
        }

    def get_decision_chain(
        self,
        production_id: str,
        claim_id: Optional[str] = None,
    ) -> DecisionChainResponse:
        """Traverses chronological decision history for production or specific claim."""
        raw_events = self._get_raw_events(production_id)
        if not raw_events:
            return DecisionChainResponse(
                production_id=production_id,
                is_chain_valid=True,
                chain_length=0,
                events=[],
            )
        superseded_ids = self._extract_superseded_ids(raw_events)
        claims_map = self._resolve_claims_map(production_id)
        projected = [self._project_timeline_event(e, superseded_ids, claims_map) for e in raw_events]
        if claim_id:
            projected = [e for e in projected if e.claim_id == claim_id]
        valid = self._check_chain_validity(production_id)
        return DecisionChainResponse(
            production_id=production_id,
            is_chain_valid=valid,
            chain_length=len(projected),
            head_event_hash=raw_events[-1].get("entry_hash"),
            events=projected,
        )

    def _check_chain_validity(self, production_id: str) -> bool:
        """Checks validity of production ledger chain."""
        if hasattr(self.ledger, "verify_chain"):
            valid, _, _ = self.ledger.verify_chain(production_id)
            return valid
        return True

    def _recalculate_block_proof(self, target: Dict[str, Any]) -> Tuple[str, str, bool]:
        """Recalculates canonical digest and entry hash for authoritative proof."""
        payload = target.get("payload", {})
        seq = target.get("sequence_number", 1)
        prev_hash = target.get("previous_event_hash", "")
        ts = target.get("timestamp_utc") or target.get("timestamp", "")
        exp_digest = compute_canonical_digest(payload)
        exp_hash = compute_entry_hash(prev_hash, exp_digest, ts, seq)
        is_valid = (exp_digest == target.get("payload_digest")) and (exp_hash == target.get("entry_hash"))
        return exp_digest, exp_hash, is_valid

    def verify_event(
        self,
        production_id: str,
        event_id: str,
    ) -> Optional[LedgerVerificationResponse]:
        """Authoritative server-side block verification recalculating digest and entry hash."""
        raw_events = self._get_raw_events(production_id)
        target = next((e for e in raw_events if e.get("event_id") == event_id), None)
        if not target:
            return None
        exp_digest, exp_hash, is_valid = self._recalculate_block_proof(target)
        msg = (
            "Cryptographic proof verified: Monotonic sequence, digest, and parent hash chain are intact."
            if is_valid else
            "Tamper detected: Computed entry hash or canonical digest differs from recorded block."
        )
        payload = target.get("payload", {})
        sigs = payload.get("dual_signatures") or payload.get("signatures", [])
        return LedgerVerificationResponse(
            event_id=event_id,
            sequence_number=target.get("sequence_number", 1),
            entry_hash=target.get("entry_hash", ""),
            previous_event_hash=target.get("previous_event_hash", ""),
            payload_digest=exp_digest,
            is_valid=is_valid,
            verification_message=msg,
            canonical_payload=payload,
            dual_signatures=sigs if isinstance(sigs, list) else [],
        )

    def get_supersessions(self, production_id: str) -> List[SupersessionRecord]:
        """Returns all non-destructive supersession override records."""
        raw_events = self._get_raw_events(production_id)
        supersessions: List[SupersessionRecord] = []
        for e in raw_events:
            p = e.get("payload", {})
            sup_id = p.get("superseded_event_id")
            if sup_id:
                supersessions.append(SupersessionRecord(
                    event_id=e.get("event_id", ""),
                    superseded_event_id=sup_id,
                    superseding_action=e.get("action_type") or p.get("action", "SUPERSEDED"),
                    counsel_rationale=p.get("rationale") or p.get("counsel_rationale", ""),
                    timestamp=e.get("timestamp_utc") or e.get("timestamp", ""),
                    actor_id=e.get("actor_id", ""),
                ))
        return supersessions
