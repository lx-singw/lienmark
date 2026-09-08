"""
backend/core/reviewer_ledger.py

Cryptographic ledger audit dispatch helpers for counsel reviewer actions.
Sprint 4.3: Milestone D - Human-in-the-Loop Clarification & Reviewer Reinvestigation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from typing import Any, List, Optional
from backend.core.reviewer_types import CounselDirective, ResearchFinding
from backend.domain.models import CensusDisposition
from backend.storage.ledger import AuditEvent, CryptographicLedger


class ReviewerLedgerHelper:
    """Encapsulates immutable audit ledger emissions for reviewer lifecycle events."""

    def __init__(self, ledger: CryptographicLedger) -> None:
        self.ledger = ledger

    def ensure_genesis(self, tenant_id: str, production_id: str, actor_id: str) -> None:
        """Initializes genesis event if ledger chain for production is empty."""
        chains = getattr(self.ledger, "_chains", {})
        if production_id not in chains or len(chains[production_id]) == 0:
            self.ledger.initialize_production_ledger(tenant_id, production_id, actor_id)

    def log_rejection(
        self,
        d: CounselDirective,
        tid: str,
        pid: str,
        p_fid: Optional[str],
        prior_att: int,
        new_att: int,
        prior_finding_text: Optional[str] = None,
    ) -> AuditEvent:
        """Appends CLAIM_REJECTED_BY_COUNSEL event to the cryptographic ledger."""
        self.ensure_genesis(tid, pid, d.counsel_id)
        payload = {
            "claim_id": d.claim_id,
            "action": "CLAIM_REJECTED_BY_COUNSEL",
            "counsel_id": d.counsel_id,
            "counsel_name": d.counsel_name,
            "directive_id": d.directive_id,
            "directive_text": d.directive_text,
            "mandatory_constraints": d.mandatory_constraints,
            "sanitized_keywords": d.sanitized_keywords,
            "prior_finding_id": p_fid,
            "previous_attempt": prior_att,
            "new_attempt": new_att,
            "prior_finding": prior_finding_text,
            "rationale": prior_finding_text,
        }
        return self.ledger.append_event(
            tenant_id=tid, production_id=pid, actor_id=d.counsel_id,
            action_type="CLAIM_REJECTED_BY_COUNSEL", payload=payload,
        )

    def log_revised_finding(
        self, r: ResearchFinding, tid: str, pid: str, actor: str, p_fid: Optional[str]
    ) -> AuditEvent:
        """Appends REVISED_FINDING_LOGGED event to the cryptographic ledger."""
        self.ensure_genesis(tid, pid, actor)
        payload = {
            "claim_id": r.claim_id,
            "revised_finding_id": r.finding_id,
            "prior_finding_id": p_fid,
            "directive_id": r.directive_id,
            "attempt_number": r.attempt_number,
            "constraints_applied": r.constraints_applied,
            "evidence_summary": r.evidence_summary,
        }
        return self.ledger.append_event(
            tenant_id=tid, production_id=pid, actor_id=actor,
            action_type="REVISED_FINDING_LOGGED", payload=payload,
        )

    def log_signoff(
        self,
        cid: str,
        tid: str,
        pid: str,
        counsel_id: str,
        counsel_name: str,
        citation: Optional[str],
        conditions: List[str],
        att: int,
    ) -> AuditEvent:
        """Appends CLAIM_COUNSEL_SIGNED_OFF event to the cryptographic ledger."""
        self.ensure_genesis(tid, pid, counsel_id)
        payload = {
            "claim_id": cid,
            "action": "CLAIM_COUNSEL_SIGNED_OFF",
            "counsel_id": counsel_id,
            "counsel_name": counsel_name,
            "citation_text": citation,
            "conditions": conditions,
            "disposition": CensusDisposition.APPROVED.value,
            "attempt_number": att,
        }
        return self.ledger.append_event(
            tenant_id=tid, production_id=pid, actor_id=counsel_id,
            action_type="CLAIM_COUNSEL_SIGNED_OFF", payload=payload,
        )
