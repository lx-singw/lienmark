"""
backend/core/policy_outbox.py

Transactional Outbox Dispatcher for Policy Invalidation Cascades.
Sprint 5.3: Asynchronous Policy Dispatch, Rule Dependencies, and Golden Demo.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.core.decision_package import create_decision_package
from backend.core.decision_package_types import DecisionPackage, DualReviewStatus
from backend.core.dual_review import DualReviewCoordinator, get_dual_review_coordinator
from backend.core.policy_outbox_types import (
    CascadeAction,
    CascadeTargetFilter,
    ClaimCascadeResult,
    DispatchExecutionReport,
    DispatchIntentStatus,
    PolicyDiffSummary,
)
from backend.domain.models import CensusDisposition
from backend.storage.policy_store import PolicyStore, get_policy_store
from backend.storage.policy_store_types import PolicyChangeDispatchIntent

logger = logging.getLogger("lienmark.core.policy_outbox")


class PolicyOutboxDispatcher:
    """Consumes atomic dispatch intents, cascades policy changes, and routes packages."""

    def __init__(
        self,
        policy_store: Optional[PolicyStore] = None,
        coordinator: Optional[DualReviewCoordinator] = None,
        ledger: Optional[Any] = None,
        claims_provider: Optional[Callable[[str], List[Any]]] = None,
    ) -> None:
        self._policy_store = policy_store or get_policy_store()
        self._coordinator = coordinator or get_dual_review_coordinator()
        self._ledger = ledger
        self._claims_provider = claims_provider

    def compute_policy_diff(
        self,
        from_cfg: Optional[Dict[str, Any]],
        to_cfg: Dict[str, Any],
        from_v: Optional[str],
        to_v: str,
    ) -> PolicyDiffSummary:
        """Determines rule changes and computes claim target filters between revisions."""
        old = from_cfg or {}
        added: List[str] = []
        modified: List[str] = []
        for k, v in to_cfg.items():
            if k not in old:
                added.append(k)
            elif old.get(k) != v:
                modified.append(k)
        removed = [k for k in old if k not in to_cfg]
        filters = self._build_target_filters(old, to_cfg)
        return PolicyDiffSummary(
            from_version=from_v, to_version=to_v, added_rules=added,
            modified_rules=modified, removed_rules=removed, target_filters=filters,
        )

    def _build_target_filters(self, old: Dict[str, Any], new: Dict[str, Any]) -> List[CascadeTargetFilter]:
        """Constructs target filters for specific changed policy constraints."""
        filters: List[CascadeTargetFilter] = []
        new_trailer_rule = (
            new.get("require_promotional_trailer_second_review")
            or "RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW" in new.get("rules", [])
            or ("promotional_trailer" in new.get("required_media_scopes", []) and not old.get("required_media_scopes"))
        )
        if new_trailer_rule and not old.get("require_promotional_trailer_second_review"):
            filters.append(CascadeTargetFilter(
                rule_code="RULE_PROMOTIONAL_TRAILER_SECOND_REVIEW",
                target_right_categories=["music", "composition", "sound_recording"],
                target_media_scopes=["promotional_trailer"],
                requires_second_review=True,
            ))
        if new.get("mandatory_perpetual_for_theatrical") and not old.get("mandatory_perpetual_for_theatrical"):
            filters.append(CascadeTargetFilter(
                rule_code="RULE_THEATRICAL_SYNC_PERPETUAL",
                target_right_categories=["music", "composition"],
                target_media_scopes=["theatrical"],
                requires_second_review=False,
            ))
        return filters

    def matches_claim_filter(self, claim: Any, flt: CascadeTargetFilter) -> bool:
        """Evaluates whether an atomic claim matches a cascade target filter."""
        cat = str(getattr(claim, "right_category", None) or (claim.get("right_category") if isinstance(claim, dict) else "")).lower()
        if flt.target_right_categories and not any(r in cat for r in flt.target_right_categories):
            return False
        scope = getattr(claim, "intended_scope", None) or (claim.get("intended_scope") if isinstance(claim, dict) else {})
        if isinstance(scope, str):
            scope = {"description": scope}
        media_scopes = [str(s).lower() for s in (scope.get("media_scopes") or [])]
        desc = str(scope.get("description", "")).lower()
        subject = str(getattr(claim, "rights_subject", None) or (claim.get("rights_subject") if isinstance(claim, dict) else "")).lower()
        for target_scope in flt.target_media_scopes:
            t = target_scope.lower()
            if t in media_scopes or scope.get(t) is True or t in desc or "trailer" in desc or "trailer" in subject:
                return True
        return False

    def evaluate_claim_cascade(
        self, claim: Any, filters: List[CascadeTargetFilter], to_version: str, ledger: Any,
    ) -> ClaimCascadeResult:
        """Applies cascade logic to an individual claim: preserves history or invalidates pending."""
        cid = str(getattr(claim, "claim_id", None) or (claim.get("claim_id") if isinstance(claim, dict) else "unknown"))
        pid = str(getattr(claim, "production_id", None) or (claim.get("production_id") if isinstance(claim, dict) else "prod_default"))
        matching = [f for f in filters if self.matches_claim_filter(claim, f)]
        if not matching:
            return ClaimCascadeResult(claim_id=cid, production_id=pid, action_taken=CascadeAction.NO_ACTION_NOT_AFFECTED, reason="Claim unaffected by changed rules.")
        active = self._coordinator.get_active_package_for_claim(cid)
        if not active:
            return ClaimCascadeResult(claim_id=cid, production_id=pid, action_taken=CascadeAction.NO_ACTION_NOT_AFFECTED, reason="No active decision package for claim.")
        if active.status == DualReviewStatus.FINAL_APPROVED:
            return ClaimCascadeResult(claim_id=cid, production_id=pid, action_taken=CascadeAction.NO_ACTION_HISTORICAL_PRESERVED, prior_package_id=active.package_id, reason=f"Historical approved package '{active.package_id}' preserved.")
        reason = f"Studio policy updated to {to_version}: {matching[0].rule_code} required."
        old_pkg, new_pkg = self._coordinator.invalidate_package_if_material_change(
            package_id=active.package_id, updated_package_data={"policy_version": to_version, "effective_policy_version": to_version}, reason=reason, ledger=ledger,
        )
        if hasattr(claim, "disposition"):
            claim.disposition = CensusDisposition.NEEDS_REVIEW
        elif isinstance(claim, dict):
            claim["disposition"] = CensusDisposition.NEEDS_REVIEW.value
        return ClaimCascadeResult(
            claim_id=cid, production_id=pid, action_taken=CascadeAction.PACKAGE_INVALIDATED_AND_ROUTED,
            prior_package_id=old_pkg.package_id, new_package_id=new_pkg.package_id if new_pkg else None,
            reason=reason, requires_second_review=matching[0].requires_second_review,
        )

    def process_single_intent(
        self, intent: PolicyChangeDispatchIntent, claims: List[Any], ledger: Optional[Any] = None,
    ) -> DispatchExecutionReport:
        """Executes full invalidation cascade for a single dispatch intent."""
        start = time.perf_counter()
        target_ledger = ledger or self._ledger
        self._policy_store.update_dispatch_intent_status(intent.intent_id, DispatchIntentStatus.PROCESSING.value)
        from_rec = self._policy_store.get_policy_revision(intent.org_id, intent.from_version) if intent.from_version else None
        to_rec = self._policy_store.get_policy_revision(intent.org_id, intent.to_version)
        to_cfg = to_rec.policy_config if to_rec else {}
        from_cfg = from_rec.policy_config if from_rec else {}
        diff = self.compute_policy_diff(from_cfg, to_cfg, intent.from_version, intent.to_version)
        results: List[ClaimCascadeResult] = []
        for c in claims:
            res = self.evaluate_claim_cascade(c, diff.target_filters, intent.to_version, target_ledger)
            results.append(res)
        hist_count = sum(1 for r in results if r.action_taken == CascadeAction.NO_ACTION_HISTORICAL_PRESERVED)
        inval_count = sum(1 for r in results if r.action_taken == CascadeAction.PACKAGE_INVALIDATED_AND_ROUTED)
        evt_id = self._emit_cascade_audit(intent, len(claims), inval_count, target_ledger)
        self._policy_store.update_dispatch_intent_status(intent.intent_id, DispatchIntentStatus.COMPLETED.value)
        return DispatchExecutionReport(
            intent_id=intent.intent_id, org_id=intent.org_id, from_version=intent.from_version, to_version=intent.to_version,
            status=DispatchIntentStatus.COMPLETED, claims_scanned=len(claims), claims_affected=inval_count + hist_count,
            historical_preserved=hist_count, packages_invalidated=inval_count, packages_routed=inval_count,
            claim_results=results, ledger_event_id=evt_id, execution_duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    def _emit_cascade_audit(self, intent: PolicyChangeDispatchIntent, scanned: int, inval: int, ledger: Any) -> Optional[str]:
        if not ledger or not hasattr(ledger, "append_event"):
            return None
        chains = getattr(ledger, "_chains", None)
        prod_id = "prod_default"
        if isinstance(chains, dict) and len(chains.get(prod_id, [])) == 0 and hasattr(ledger, "initialize_production_ledger"):
            ledger.initialize_production_ledger(intent.org_id, prod_id, "policy_outbox_dispatcher")
        evt = ledger.append_event(
            intent.org_id, prod_id, "policy_outbox_dispatcher", "POLICY_CASCADE_APPLIED",
            {"intent_id": intent.intent_id, "from_version": intent.from_version, "to_version": intent.to_version, "claims_scanned": scanned, "packages_invalidated": inval},
        )
        return getattr(evt, "event_id", None)

    def process_pending_intents(self, org_id: str, claims: Optional[List[Any]] = None) -> List[DispatchExecutionReport]:
        """Dispatches all PENDING intents for organization and returns execution reports."""
        intents = self._policy_store.list_dispatch_intents(org_id, status=DispatchIntentStatus.PENDING.value)
        active_claims = claims if claims is not None else (self._claims_provider(org_id) if self._claims_provider else [])
        reports: List[DispatchExecutionReport] = []
        for item in intents:
            rep = self.process_single_intent(item, active_claims, self._ledger)
            reports.append(rep)
        return reports

    def recover_abandoned_intents(self, org_id: str) -> int:
        """Resets dangling PROCESSING intents back to PENDING after worker restarts."""
        interrupted = self._policy_store.list_dispatch_intents(org_id, status=DispatchIntentStatus.PROCESSING.value)
        for item in interrupted:
            self._policy_store.update_dispatch_intent_status(item.intent_id, DispatchIntentStatus.PENDING.value)
        return len(interrupted)


_GLOBAL_OUTBOX_DISPATCHER: Optional[PolicyOutboxDispatcher] = None


def get_policy_outbox_dispatcher(
    policy_store: Optional[PolicyStore] = None,
    coordinator: Optional[DualReviewCoordinator] = None,
    ledger: Optional[Any] = None,
    claims_provider: Optional[Callable[[str], List[Any]]] = None,
) -> PolicyOutboxDispatcher:
    """Dependency provider returning singleton PolicyOutboxDispatcher instance."""
    global _GLOBAL_OUTBOX_DISPATCHER
    if _GLOBAL_OUTBOX_DISPATCHER is None:
        _GLOBAL_OUTBOX_DISPATCHER = PolicyOutboxDispatcher(
            policy_store=policy_store, coordinator=coordinator, ledger=ledger, claims_provider=claims_provider,
        )
    return _GLOBAL_OUTBOX_DISPATCHER
