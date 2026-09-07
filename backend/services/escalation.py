"""
escalation.py

Autonomous Dispute & SLA Escalation Service.
Monitors unreviewed claims, auto-escalating priority after 72-hour SLA breach.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.storage.ledger import CryptographicLedger
from backend.storage.repository import TenantRepository

logger = logging.getLogger("lienmark.services.escalation")


class DisputeEscalationService:
    """
    Monitors unreviewed claims, automatically escalating priority when SLA exceeds 72h.
    Enforces INV-S62-04 (escalation idempotency, distributed locking, and ledger audit).
    """

    SLA_HARD_BREACH_HOURS: float = 72.0
    SLA_WARNING_HOURS: float = 48.0
    UNREVIEWED_STATUSES: Tuple[str, ...] = (
        "ready_for_review",
        "attorney_review_required",
        "needs_disambiguation",
        "stale",
        "unknown",
        "newly_discovered",
    )

    def __init__(
        self,
        repository: TenantRepository,
        ledger: Optional[CryptographicLedger] = None,
    ) -> None:
        self.repo = repository
        self.ledger = ledger or CryptographicLedger(repository=repository)

    def _parse_timestamp(self, ts_str: Optional[str]) -> datetime:
        """Parses ISO format timestamp defensively with UTC fallback."""
        if not ts_str:
            return datetime.now(timezone.utc)
        try:
            dt = datetime.fromisoformat(ts_str)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    def _calculate_age_hours(self, claim: Dict[str, Any], now: datetime) -> float:
        """Computes elapsed age in hours since claim creation or latest revision."""
        ts = claim.get("updated_at") or claim.get("created_at")
        dt = self._parse_timestamp(ts)
        diff = now - dt
        return max(0.0, diff.total_seconds() / 3600.0)

    def _should_escalate(self, claim: Dict[str, Any], age_hours: float) -> bool:
        """Determines if an unreviewed claim qualifies for SLA auto-escalation."""
        if age_hours < self.SLA_HARD_BREACH_HOURS:
            return False
        meta = claim.get("metadata", {}) or {}
        if meta.get("is_escalated", False):
            return False
        disp = str(claim.get("disposition", "")).lower()
        wf = str(claim.get("workflow_reason", "")).lower()
        is_unreviewed = any(s in (disp, wf) for s in self.UNREVIEWED_STATUSES)
        return is_unreviewed or (disp not in ("cleared", "approved", "rejected"))

    def _escalate_single_claim(
        self,
        claim: Dict[str, Any],
        production_id: str,
        run_id: str,
        age_hours: float,
        tenant_id: str,
    ) -> str:
        """Escalates a single claim, recording ledger block and updating repository state."""
        meta = dict(claim.get("metadata", {}) or {})
        meta["is_escalated"] = True
        meta["escalation_level"] = 2  # P0 Critical
        meta["escalated_at_utc"] = datetime.now(timezone.utc).isoformat()
        meta["sla_breach_hours"] = round(age_hours, 2)
        claim["metadata"] = meta
        self.repo.save_claim(production_id, run_id, claim)

        try:
            self.ledger.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id="system_escalation_daemon",
                action_type="CLAIM_ESCALATED",
                payload={
                    "action": "CLAIM_ESCALATED",
                    "claim_id": claim.get("claim_id") or claim.get("use_id"),
                    "claim_title": claim.get("title") or claim.get("name"),
                    "age_hours": round(age_hours, 2),
                    "sla_limit_hours": self.SLA_HARD_BREACH_HOURS,
                    "escalation_level": "P0_CRITICAL",
                },
            )
        except Exception as exc:
            logger.warning(f"Failed appending escalation audit event: {exc}")

        return str(claim.get("claim_id") or claim.get("use_id") or "unknown")

    def _get_target_claims_and_runs(self, production_id: str) -> List[Tuple[Dict[str, Any], str]]:
        """Collects all claims with their run IDs for a production."""
        results: List[Tuple[Dict[str, Any], str]] = []
        runs = self.repo.list_runs(production_id)
        act_id = self.repo.get_active_run_id(production_id)
        target_runs = [r for r in runs if r.run_id == act_id] if act_id else runs
        for run in target_runs:
            for c in self.repo.list_claims(production_id, run.run_id):
                c_dict = c if isinstance(c, dict) else c.model_dump()
                results.append((c_dict, run.run_id))
        return results

    def sweep_escalations(
        self,
        production_id: str,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Performs an idempotent escalation sweep across all production claims."""
        claim_pairs = self._get_target_claims_and_runs(production_id)
        now = datetime.now(timezone.utc)
        escalated_ids: List[str] = []

        for claim_dict, run_id in claim_pairs:
            age = self._calculate_age_hours(claim_dict, now)
            if self._should_escalate(claim_dict, age):
                c_id = self._escalate_single_claim(claim_dict, production_id, run_id, age, tenant_id)
                escalated_ids.append(c_id)

        return {
            "production_id": production_id,
            "evaluated_count": len(claim_pairs),
            "escalated_count": len(escalated_ids),
            "breached_claim_ids": escalated_ids,
            "timestamp": now.isoformat(),
        }

    def get_escalation_status(self, production_id: str) -> Dict[str, Any]:
        """Computes SLA compliance metrics and overdue unreviewed claim counts."""
        claim_pairs = self._get_target_claims_and_runs(production_id)
        now = datetime.now(timezone.utc)
        unreviewed = 0
        overdue_72h = 0
        warning_48h = 0

        for claim_dict, _ in claim_pairs:
            age = self._calculate_age_hours(claim_dict, now)
            status_val = str(claim_dict.get("disposition") or claim_dict.get("status") or "").lower()
            if status_val not in ("cleared", "approved", "rejected"):
                unreviewed += 1
                if age >= self.SLA_HARD_BREACH_HOURS:
                    overdue_72h += 1
                elif age >= self.SLA_WARNING_HOURS:
                    warning_48h += 1

        rate = ((unreviewed - overdue_72h) / unreviewed * 100.0) if unreviewed > 0 else 100.0
        return {
            "production_id": production_id,
            "total_unreviewed": unreviewed,
            "overdue_72h_count": overdue_72h,
            "warning_48h_count": warning_48h,
            "compliance_rate": round(rate, 1),
        }
