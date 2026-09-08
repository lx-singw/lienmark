"""
backend/core/reviewer_loop.py

Reviewer Rejection & Directed Re-Investigation Loop Coordinator.
Milestone D: Coordinates counsel rejection, immutable ledger audit, Attempt 2 increment,
transitive downstream invalidation via DependencyGraph, and budgeted directed research.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

from backend.core.dependency_graph import DependencyGraph, get_dependency_graph
from backend.core.directed_research import DirectedResearchCoordinator
from backend.core.reviewer_decision_adapter import DecisionApiMixin
from backend.core.reviewer_ledger import ReviewerLedgerHelper
from backend.core.reviewer_types import (
    AttemptLineage, AttemptRecord, ClaimSignOffResult, CounselDirective,
    ReinvestigationDispatch, ResearchFinding, ReviewerAction,
)
from backend.domain.models import AtomicRightsClaim, CensusDisposition, WorkflowReason
from backend.storage.ledger import AuditEvent, CryptographicLedger

__all__ = [
    "CounselReviewLoopCoordinator",
    "DirectedResearchCoordinator",
    "get_reviewer_loop_coordinator",
]


class CounselReviewLoopCoordinator(DecisionApiMixin):
    """Coordinates counsel review cycles, rejection, downstream invalidation, and sign-off."""

    def __init__(
        self,
        ledger: Optional[CryptographicLedger] = None,
        directed_coordinator: Optional[DirectedResearchCoordinator] = None,
        dependency_graph: Optional[DependencyGraph] = None,
    ) -> None:
        self.ledger = ledger or CryptographicLedger()
        self.ledger_helper = ReviewerLedgerHelper(self.ledger)
        self.directed_coordinator = directed_coordinator or DirectedResearchCoordinator(ledger=self.ledger)
        self.dependency_graph = dependency_graph or get_dependency_graph()
        self._lineages: Dict[str, AttemptLineage] = {}

    def get_lineage(self, claim_id: str) -> Optional[AttemptLineage]:
        """Retrieves attempt lineage for a given claim ID."""
        return self._lineages.get(claim_id)

    def _resolve_claim_context(self, claim: object) -> Tuple[str, int, int]:
        """Extracts claim ID and calculates previous and next attempt numbers."""
        is_dict = isinstance(claim, dict)
        cid = str(claim.get("claim_id", "") if is_dict else getattr(claim, "claim_id", ""))
        prior = int(claim.get("attempt_number", 1) if is_dict else getattr(claim, "attempt_number", 1))
        return cid, prior, prior + 1

    def _update_claim_for_rejection(
        self, claim: object, new_att: int, directive_text: str, constraints: List[str],
        prior_finding: object, counsel_name: str, counsel_id: str,
    ) -> None:
        """Stores original directive text, structured constraints, and archives recommendation."""
        entry = {
            "action": "reject_and_direct", "counsel_id": counsel_id, "counsel_name": counsel_name,
            "directive": directive_text, "mandatory_constraints": constraints,
            "prior_finding": str(prior_finding), "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if isinstance(claim, dict):
            claim.update({
                "attempt_number": new_att, "disposition": CensusDisposition.NEEDS_REVIEW,
                "workflow_reason": WorkflowReason.REINVESTIGATION_REQUESTED, "counsel_directive": directive_text,
            })
            claim.setdefault("metadata", {})["mandatory_constraints"] = constraints
            claim.setdefault("archived_recommendations", []).append(entry)
        else:
            claim.attempt_number = new_att  # type: ignore[misc]
            claim.disposition = CensusDisposition.NEEDS_REVIEW  # type: ignore[misc]
            claim.workflow_reason = WorkflowReason.REINVESTIGATION_REQUESTED  # type: ignore[misc]
            claim.counsel_directive = directive_text  # type: ignore[misc]
            if hasattr(claim, "metadata") and isinstance(claim.metadata, dict):
                claim.metadata["mandatory_constraints"] = constraints
            if hasattr(claim, "archived_recommendations"):
                claim.archived_recommendations.append(entry)

    def _reopen_downstream_claim(
        self, downstream_id: str, upstream_id: str,
        claims_lookup: Optional[Dict[str, Union[AtomicRightsClaim, Dict[str, object]]]] = None,
    ) -> None:
        """Reopens a downstream claim whose upstream assumption was invalidated."""
        if not claims_lookup or downstream_id not in claims_lookup:
            return
        target = claims_lookup[downstream_id]
        note = f"[Transitive Invalidation]: Upstream claim '{upstream_id}' rejected by counsel. Reopened."
        if isinstance(target, dict):
            target.update({
                "disposition": CensusDisposition.NEEDS_REVIEW,
                "workflow_reason": WorkflowReason.REINVESTIGATION_REQUESTED,
                "notes": f"{str(target.get('notes', ''))}\n{note}".strip(),
            })
        else:
            target.disposition = CensusDisposition.NEEDS_REVIEW  # type: ignore[misc]
            target.workflow_reason = WorkflowReason.REINVESTIGATION_REQUESTED  # type: ignore[misc]
            if hasattr(target, "notes"):
                target.notes = f"{target.notes}\n{note}".strip()  # type: ignore[misc]

    def _propagate_downstream_reopen(
        self, cid: str, production_id: str,
        claims_lookup: Optional[Dict[str, Union[AtomicRightsClaim, Dict[str, object]]]] = None,
    ) -> List[str]:
        """Traverses and reopens invalidated transitive downstream dependencies via DependencyGraph."""
        downstream_ids = self.dependency_graph.get_transitive_downstream_dependents(cid, production_id)
        for d_id in downstream_ids:
            self._reopen_downstream_claim(d_id, cid, claims_lookup)
        return downstream_ids

    def _record_rejection_lineage(
        self, cid: str, prior_att: int, counsel_id: str, directive_text: str, p_fid: Optional[str]
    ) -> Tuple[AttemptLineage, AttemptRecord]:
        """Appends rejection record preserving Attempt 1 immutably in lineage."""
        lineage = self._lineages.setdefault(
            cid, AttemptLineage(claim_id=cid, current_attempt_number=prior_att)
        )
        rec = AttemptRecord(
            attempt_number=prior_att, action=ReviewerAction.REJECT_AND_DIRECT,
            counsel_id=counsel_id, directive_text=directive_text, prior_finding_id=p_fid,
        )
        lineage.append_attempt(rec)
        return lineage, rec

    def _create_dispatch(
        self, claim: object, cid: str, tid: str, pid: str, directive: CounselDirective,
        new_att: int, prior_f: object, p_fid: Optional[str], revised: ResearchFinding,
        lineage: AttemptLineage, rej_evt: AuditEvent, downstream_ids: List[str],
    ) -> ReinvestigationDispatch:
        """Constructs the ReinvestigationDispatch outcome."""
        return ReinvestigationDispatch(
            claim_id=cid, tenant_id=tid, production_id=pid, directive=directive,
            attempt_number=new_att, disposition=CensusDisposition.NEEDS_REVIEW,
            prior_finding=prior_f, prior_finding_id=p_fid, revised_finding_id=revised.finding_id,
            reinvestigation_result=revised, lineage=lineage, ledger_event=rej_evt, claim=claim,
            invalidated_downstream_claim_ids=downstream_ids,
        )

    def reject_and_reopen_investigation(
        self,
        claim: Union[AtomicRightsClaim, Dict[str, object]],
        prior_finding: Union[str, Dict[str, object], ResearchFinding],
        directive_text: str,
        counsel_id: str,
        counsel_name: str,
        tenant_id: str,
        production_id: str,
        mandatory_constraints: Optional[List[str]] = None,
        prior_finding_id: Optional[str] = None,
        claims_lookup: Optional[Dict[str, Union[AtomicRightsClaim, Dict[str, object]]]] = None,
    ) -> ReinvestigationDispatch:
        """Rejects finding, updates lineage, reopens downstream dependencies, and dispatches research."""
        cid, prior_att, new_att = self._resolve_claim_context(claim)
        constraints = mandatory_constraints or [directive_text]
        directive = CounselDirective(
            claim_id=cid, counsel_id=counsel_id, counsel_name=counsel_name,
            directive_text=directive_text, mandatory_constraints=constraints,
        )
        prior_str = prior_finding.evidence_summary if isinstance(prior_finding, ResearchFinding) else str(prior_finding)
        rej_evt = self.ledger_helper.log_rejection(
            directive, tenant_id, production_id, prior_finding_id, prior_att, new_att, prior_str
        )
        self._update_claim_for_rejection(claim, new_att, directive_text, constraints, prior_finding, counsel_name, counsel_id)
        lineage, rec = self._record_rejection_lineage(cid, prior_att, counsel_id, directive_text, prior_finding_id)
        downstream_ids = self._propagate_downstream_reopen(cid, production_id, claims_lookup)
        revised = self.directed_coordinator.dispatch_reinvestigation(
            claim=claim, directive=directive, tenant_id=tenant_id,
            production_id=production_id, prior_finding_id=prior_finding_id,
        )
        rec.revised_finding_id = revised.finding_id
        return self._create_dispatch(
            claim, cid, tenant_id, production_id, directive, new_att,
            prior_finding, prior_finding_id, revised, lineage, rej_evt, downstream_ids,
        )

    def _resolve_signoff_context(
        self, claim: object, tenant_id: Optional[str], production_id: Optional[str]
    ) -> Tuple[str, str, str, int]:
        """Resolves claim ID, tenant, production, and attempt count for sign-off."""
        is_dict = isinstance(claim, dict)
        cid = str(claim.get("claim_id", "") if is_dict else getattr(claim, "claim_id", ""))
        tid = tenant_id or str(claim.get("tenant_id", "default_tenant") if is_dict else getattr(claim, "tenant_id", "default_tenant"))
        pid = production_id or str(claim.get("production_id", "default_production") if is_dict else getattr(claim, "production_id", "default_production"))
        att = int(claim.get("attempt_number", 1) if is_dict else getattr(claim, "attempt_number", 1))
        return cid, tid, pid, att

    def _update_claim_for_signoff(
        self, claim: object, citation_text: Optional[str], conditions: List[str]
    ) -> None:
        """Applies APPROVED disposition and records conditions/citations on claim."""
        note_str = f"[Sign-off Citation]: {citation_text}" if citation_text else ""
        if isinstance(claim, dict):
            claim["disposition"] = CensusDisposition.APPROVED
            claim["decision_conditions"] = conditions
            if note_str:
                claim["notes"] = f"{claim.get('notes', '')}\n{note_str}".strip()
        else:
            claim.disposition = CensusDisposition.APPROVED  # type: ignore[misc]
            claim.decision_conditions = conditions  # type: ignore[misc]
            if note_str and hasattr(claim, "notes"):
                claim.notes = f"{claim.notes}\n{note_str}".strip()  # type: ignore[misc]

    def sign_off_claim(
        self,
        claim: Union[AtomicRightsClaim, Dict[str, object]],
        counsel_id: str,
        counsel_name: str,
        citation_text: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> ClaimSignOffResult:
        """Authoritative counsel sign-off: updates disposition to APPROVED and logs to ledger."""
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
