"""
backend/core/reviewer_decision_adapter.py

REST API integration adapter for Counsel Reviewer Decision endpoints.
Sprint 4.3: Milestone D - Human-in-the-Loop Clarification & Reviewer Reinvestigation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException


class DecisionApiMixin:
    """Provides REST adapter methods for decision endpoints and multi-tenant isolation."""

    _tenant_claims: Dict[str, str] = {}
    _api_lineages: Dict[str, List[Dict[str, Any]]] = {}
    _claim_productions: Dict[str, str] = {}

    def clear_state(self) -> None:
        """Resets all in-memory coordinator state for clean testing."""
        if hasattr(self, "_lineages"):
            getattr(self, "_lineages").clear()
        self._tenant_claims.clear()
        self._api_lineages.clear()
        self._claim_productions.clear()
        if hasattr(self, "ledger") and hasattr(getattr(self, "ledger"), "_chains"):
            getattr(self, "ledger")._chains.clear()

    def get_claim_production(self, claim_id: str) -> Optional[str]:
        """Returns the registered production_id for a claim, if known."""
        return self._claim_productions.get(claim_id)

    def set_claim_production(self, claim_id: str, production_id: str) -> None:
        """Registers the production_id for a claim."""
        self._claim_productions[claim_id] = production_id


    def verify_tenant_ownership(self, tenant_id: str, claim_id: str) -> None:
        """Enforces strict multi-tenant boundary checks on claims."""
        owner = self._tenant_claims.get(claim_id)
        if owner is not None and owner != tenant_id:
            raise HTTPException(
                status_code=403,
                detail=f"Cross-tenant access forbidden: Claim '{claim_id}' belongs to another organization.",
            )
        self._tenant_claims[claim_id] = tenant_id

    def get_attempts(self, tenant_id: str, claim_id: str) -> Any:
        """Returns historical attempt lineage formatted for API responses."""
        from backend.api.routes.decision_schemas import AttemptLineageResponse, AttemptRecord as ApiAttemptRecord
        self.verify_tenant_ownership(tenant_id, claim_id)
        raw_list = self._api_lineages.get(claim_id, [])
        records = [ApiAttemptRecord(**item) for item in raw_list]
        return AttemptLineageResponse(claim_id=claim_id, total_attempts=len(records), attempts=records)

    def _record_sign_off_decision(
        self, tenant_id: str, prod_id: str, claim_id: str, att_num: int, request: Any, now: str
    ) -> Any:
        """Executes sign-off branch and formats API response."""
        from backend.api.routes.decision_schemas import CounselDecisionResponse
        conds = request.conditions or []
        st_val = "conditional" if conds else "approved"
        claim_dict = {"claim_id": claim_id, "attempt_number": att_num, "tenant_id": tenant_id, "production_id": prod_id}
        sign_res = getattr(self, "sign_off_claim")(
            claim=claim_dict, counsel_id=request.counsel_id, counsel_name=request.counsel_name,
            citation_text=request.citation_text, conditions=conds, tenant_id=tenant_id, production_id=prod_id,
        )
        evt_id = getattr(sign_res.ledger_event, "event_id", f"evt_{uuid.uuid4().hex[:8]}")
        self._api_lineages[claim_id].append({
            "attempt_number": att_num, "action": "sign_off", "status": st_val, "disposition": st_val,
            "counsel_id": request.counsel_id, "counsel_name": request.counsel_name,
            "citation_text": request.citation_text, "conditions": conds, "audit_event_id": evt_id,
            "timestamp_utc": now,
        })
        return CounselDecisionResponse(
            claim_id=claim_id, status=st_val, disposition=st_val, attempt_number=att_num,
            reinvestigation_run_id=None, audit_event_id=evt_id, timestamp_utc=now,
        )

    def _record_reject_decision(
        self, tenant_id: str, prod_id: str, claim_id: str, att_num: int, request: Any, now: str
    ) -> Any:
        """Executes rejection branch, dispatches reinvestigation, and formats API response."""
        from backend.api.routes.decision_schemas import CounselDecisionResponse
        run_id = f"reinv_{uuid.uuid4().hex[:12]}"
        claim_dict = {"claim_id": claim_id, "attempt_number": att_num, "tenant_id": tenant_id, "production_id": prod_id}
        disp_res = getattr(self, "reject_and_reopen_investigation")(
            claim=claim_dict, prior_finding=request.directive_text or "Automated finding",
            directive_text=request.directive_text or "Reinvestigate claim", counsel_id=request.counsel_id,
            counsel_name=request.counsel_name, tenant_id=tenant_id, production_id=prod_id,
        )
        evt_id = getattr(disp_res.ledger_event, "event_id", f"evt_{uuid.uuid4().hex[:8]}")
        self._api_lineages[claim_id].append({
            "attempt_number": att_num, "action": "reject", "status": "reinvestigation_requested",
            "disposition": "rejected", "counsel_id": request.counsel_id, "counsel_name": request.counsel_name,
            "directive_text": request.directive_text, "reinvestigation_run_id": run_id,
            "audit_event_id": evt_id, "timestamp_utc": now,
        })
        return CounselDecisionResponse(
            claim_id=claim_id, status="reinvestigation_requested", disposition="rejected",
            attempt_number=att_num, reinvestigation_run_id=run_id, audit_event_id=evt_id, timestamp_utc=now,
        )

    def record_decision(
        self, tenant_id: str, production_id: Optional[str], claim_id: str, actor_id: str, request: Any
    ) -> Any:
        """Handles decision request routing, verification, and persistence."""
        self.verify_tenant_ownership(tenant_id, claim_id)
        prod_id = production_id or self._claim_productions.get(claim_id) or f"prod_{claim_id}"
        self._claim_productions[claim_id] = prod_id
        attempts = self._api_lineages.setdefault(claim_id, [])
        att_num = len(attempts) + 1
        now = datetime.now(timezone.utc).isoformat()
        if request.action.lower().strip() == "sign_off":
            return self._record_sign_off_decision(tenant_id, prod_id, claim_id, att_num, request, now)
        return self._record_reject_decision(tenant_id, prod_id, claim_id, att_num, request, now)
