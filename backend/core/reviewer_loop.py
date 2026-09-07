"""
backend/core/reviewer_loop.py

Reviewer Rejection & Directed Re-Investigation Loop Coordinator.
Sprint 4.3: Milestone D - Human-in-the-Loop Clarification & Reviewer Reinvestigation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status

from backend.core.directed_research import DirectedResearchCoordinator
from backend.core.reviewer_decision_adapter import DecisionApiMixin
from backend.core.reviewer_ledger import ReviewerLedgerHelper
from backend.core.reviewer_types import (
    AttemptLineage,
    AttemptRecord,
    ClaimSignOffResult,
    CounselDirective,
    ReinvestigationDispatch,
    ResearchFinding,
    ReviewerAction,
)
from backend.domain.models import AtomicRightsClaim, CensusDisposition, WorkflowReason
from backend.storage.ledger import AuditEvent, CryptographicLedger

__all__ = [
    "CounselReviewLoopCoordinator",
    "DirectedResearchCoordinator",
    "get_reviewer_loop_coordinator",
]


class CounselReviewLoopCoordinator(DecisionApiMixin):
    """
    Coordinates counsel review cycles, rejection & directed re-investigation,
    attempt lineage preservation, and final sign-off to CryptographicLedger.
    """

    def __init__(
        self,
        ledger: Optional[CryptographicLedger] = None,
        directed_coordinator: Optional[DirectedResearchCoordinator] = None,
    ) -> None:
        self.ledger = ledger or CryptographicLedger()
        self.ledger_helper = ReviewerLedgerHelper(self.ledger)
        self.directed_coordinator = directed_coordinator or DirectedResearchCoordinator(
            ledger=self.ledger
        )
        self._lineages: Dict[str, AttemptLineage] = {}

    def get_lineage(self, claim_id: str) -> Optional[AttemptLineage]:
        """Retrieves attempt lineage for a given claim ID."""
        return self._lineages.get(claim_id)

    def _resolve_claim_context(self, claim: Any) -> Tuple[str, int, int]:
        """Extracts claim ID and calculates previous and next attempt numbers."""
        is_dict = isinstance(claim, dict)
        cid = claim.get("claim_id", "") if is_dict else getattr(claim, "claim_id", "")
        prior = claim.get("attempt_number", 1) if is_dict else getattr(claim, "attempt_number", 1)
        return cid, prior, prior + 1

    def _update_claim_for_rejection(
        self, claim: Any, new_att: int, directive_text: str, prior_finding: Any,
        counsel_name: str, counsel_id: str,
    ) -> None:
        """Updates claim disposition and archives prior recommendation."""
        entry = {
            "action": "reject_and_direct",
            "counsel_id": counsel_id,
            "counsel_name": counsel_name,
            "directive": directive_text,
            "prior_finding": prior_finding if isinstance(prior_finding, (str, dict)) else str(prior_finding),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if isinstance(claim, dict):
            claim["attempt_number"] = new_att
            claim["disposition"] = CensusDisposition.NEEDS_REVIEW
            claim["workflow_reason"] = WorkflowReason.REINVESTIGATION_REQUESTED
            claim["counsel_directive"] = directive_text
            claim.setdefault("archived_recommendations", []).append(entry)
        else:
            claim.attempt_number = new_att
            claim.disposition = CensusDisposition.NEEDS_REVIEW
            claim.workflow_reason = WorkflowReason.REINVESTIGATION_REQUESTED
            claim.counsel_directive = directive_text
            claim.archived_recommendations.append(entry)

    def _record_rejection_lineage(
        self, cid: str, prior_att: int, counsel_id: str, directive_text: str, p_fid: Optional[str]
    ) -> Tuple[AttemptLineage, AttemptRecord]:
        """Appends rejection record to claim lineage."""
        lineage = self._lineages.setdefault(
            cid, AttemptLineage(claim_id=cid, current_attempt_number=prior_att)
        )
        rec = AttemptRecord(
            attempt_number=prior_att,
            action=ReviewerAction.REJECT_AND_DIRECT,
            counsel_id=counsel_id,
            directive_text=directive_text,
            prior_finding_id=p_fid,
        )
        lineage.append_attempt(rec)
        return lineage, rec

    def _create_dispatch(
        self, claim: Any, cid: str, tid: str, pid: str, directive: CounselDirective,
        new_att: int, prior_f: Any, p_fid: Optional[str], revised: ResearchFinding,
        lineage: AttemptLineage, rej_evt: AuditEvent,
    ) -> ReinvestigationDispatch:
        """Constructs the ReinvestigationDispatch outcome."""
        return ReinvestigationDispatch(
            claim_id=cid, tenant_id=tid, production_id=pid, directive=directive,
            attempt_number=new_att, disposition=CensusDisposition.NEEDS_REVIEW,
            prior_finding=prior_f, prior_finding_id=p_fid, revised_finding_id=revised.finding_id,
            reinvestigation_result=revised, lineage=lineage, ledger_event=rej_evt, claim=claim,
        )

    def reject_and_reopen_investigation(
        self,
        claim: Union[AtomicRightsClaim, Dict[str, Any]],
        prior_finding: Union[str, Dict[str, Any], ResearchFinding],
        directive_text: str,
        counsel_id: str,
        counsel_name: str,
        tenant_id: str,
        production_id: str,
        mandatory_constraints: Optional[List[str]] = None,
        prior_finding_id: Optional[str] = None,
    ) -> ReinvestigationDispatch:
        """
        Archives prior finding, formulates directive, increments attempt,
        resets disposition to NEEDS_REVIEW, and dispatches directed research.
        """
        cid, prior_att, new_att = self._resolve_claim_context(claim)
        directive = CounselDirective(
            claim_id=cid, counsel_id=counsel_id, counsel_name=counsel_name,
            directive_text=directive_text,
            mandatory_constraints=mandatory_constraints or [directive_text],
        )
        rej_evt = self.ledger_helper.log_rejection(
            directive, tenant_id, production_id, prior_finding_id, prior_att, new_att
        )
        self._update_claim_for_rejection(claim, new_att, directive_text, prior_finding, counsel_name, counsel_id)
        lineage, rec = self._record_rejection_lineage(cid, prior_att, counsel_id, directive_text, prior_finding_id)
        revised = self.directed_coordinator.dispatch_reinvestigation(
            claim=claim, directive=directive, tenant_id=tenant_id,
            production_id=production_id, prior_finding_id=prior_finding_id,
        )
        rec.revised_finding_id = revised.finding_id
        return self._create_dispatch(
            claim, cid, tenant_id, production_id, directive, new_att,
            prior_finding, prior_finding_id, revised, lineage, rej_evt,
        )

    def _resolve_signoff_context(
        self, claim: Any, tenant_id: Optional[str], production_id: Optional[str]
    ) -> Tuple[str, str, str, int]:
        """Resolves claim ID, tenant, production, and attempt count for sign-off."""
        is_dict = isinstance(claim, dict)
        cid = claim.get("claim_id", "") if is_dict else getattr(claim, "claim_id", "")
        tid = tenant_id or (claim.get("tenant_id", "default_tenant") if is_dict else getattr(claim, "tenant_id", "default_tenant"))
        pid = production_id or (claim.get("production_id", "default_production") if is_dict else getattr(claim, "production_id", "default_production"))
        att = claim.get("attempt_number", 1) if is_dict else getattr(claim, "attempt_number", 1)
        return cid, tid, pid, att

    def _update_claim_for_signoff(
        self, claim: Any, citation_text: Optional[str], conditions: List[str]
    ) -> None:
        """Applies APPROVED disposition and records conditions/citations on claim."""
        is_dict = isinstance(claim, dict)
        note_str = f"[Sign-off Citation]: {citation_text}" if citation_text else ""
        if is_dict:
            claim["disposition"] = CensusDisposition.APPROVED
            claim["decision_conditions"] = conditions
            if note_str:
                claim["notes"] = f"{claim.get('notes', '')}\n{note_str}".strip()
        else:
            claim.disposition = CensusDisposition.APPROVED
            claim.decision_conditions = conditions
            if note_str:
                claim.notes = f"{claim.notes}\n{note_str}".strip()

    def sign_off_claim(
        self,
        claim: Union[AtomicRightsClaim, Dict[str, Any]],
        counsel_id: str,
        counsel_name: str,
        citation_text: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> ClaimSignOffResult:
        """
        Authoritative counsel claim sign-off:
        Updates disposition to APPROVED and emits CLAIM_COUNSEL_SIGNED_OFF to ledger.
        """
        cid, tid, pid, att = self._resolve_signoff_context(claim, tenant_id, production_id)
        cond_list = conditions or []
        self._update_claim_for_signoff(claim, citation_text, cond_list)
        sign_evt = self.ledger_helper.log_signoff(
            cid, tid, pid, counsel_id, counsel_name, citation_text, cond_list, att
        )
        if cid in self._lineages:
            self._lineages[cid].append_attempt(
                AttemptRecord(attempt_number=att, action=ReviewerAction.SIGN_OFF, counsel_id=counsel_id)
            )
        return ClaimSignOffResult(
            claim_id=cid, action=ReviewerAction.SIGN_OFF, disposition=CensusDisposition.APPROVED,
            counsel_id=counsel_id, counsel_name=counsel_name, citation_text=citation_text,
            conditions=cond_list, ledger_event=sign_evt, claim=claim,
        )


_global_coordinator: Optional[CounselReviewLoopCoordinator] = None


def get_reviewer_loop_coordinator() -> CounselReviewLoopCoordinator:
    """Dependency provider returning singleton CounselReviewLoopCoordinator instance."""
    global _global_coordinator
    if _global_coordinator is None:
        _global_coordinator = CounselReviewLoopCoordinator()
    return _global_coordinator
