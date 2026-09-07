"""
backend/storage/clarification_store.py

Multi-tenant storage and cryptographic ledger integration for ClarificationRequests.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import copy
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.domain.models import ClarificationRequest
from backend.storage.ledger import CryptographicLedger
from backend.storage.ledger_types import AuditEvent

logger = logging.getLogger("lienmark.storage.clarifications")


def _append_to_ledger_defensively(
    ledger: CryptographicLedger,
    tenant_id: str,
    production_id: str,
    actor_id: str,
    action_type: str,
    payload: Dict[str, Any],
) -> Optional[AuditEvent]:
    """Appends an event to the ledger, initializing genesis if chain is missing."""
    try:
        return ledger.append_event(
            tenant_id=tenant_id,
            production_id=production_id,
            actor_id=actor_id,
            action_type=action_type,
            payload=payload,
        )
    except Exception as initial_exc:
        logger.debug(f"Initial ledger append failed ({initial_exc}); attempting genesis initialization.")
        try:
            ledger.initialize_production_ledger(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
            )
            return ledger.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
                action_type=action_type,
                payload=payload,
            )
        except Exception as retry_exc:
            logger.error(f"Failed to record audit event in ledger: {retry_exc}")
            return None


class ClarificationStore:
    """Thread-safe multi-tenant store for ClarificationRequests and ledger auditing."""

    def __init__(self, ledger: Optional[CryptographicLedger] = None) -> None:
        self._ledger = ledger or CryptographicLedger()
        self._records: Dict[str, ClarificationRequest] = {}
        self._tenant_index: Dict[str, Dict[str, str]] = {}
        self._lock = threading.RLock()

    def save_clarification(
        self,
        clarification: ClarificationRequest,
        tenant_id: str,
        production_id: Optional[str] = None,
    ) -> ClarificationRequest:
        """Stores or updates a ClarificationRequest scoped by tenant_id."""
        with self._lock:
            clrf = clarification.model_copy(deep=True)
            clrf.tenant_id = tenant_id
            if production_id:
                clrf.production_id = production_id
            elif not clrf.production_id:
                clrf.production_id = "prod_default"

            self._records[clrf.request_id] = clrf
            run_map = self._tenant_index.setdefault(tenant_id, {})
            run_map[clrf.request_id] = clrf.run_id
            return clrf.model_copy(deep=True)

    def get_clarification(
        self,
        request_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[ClarificationRequest]:
        """Retrieves a ClarificationRequest enforcing strict tenant isolation."""
        with self._lock:
            clrf = self._records.get(request_id)
            if clrf is None:
                return None
            if tenant_id and clrf.tenant_id != tenant_id:
                logger.warning(
                    f"Cross-tenant access rejected: {clrf.tenant_id} != {tenant_id}"
                )
                return None
            return clrf.model_copy(deep=True)

    def list_clarifications_for_run(
        self,
        run_id: str,
        tenant_id: str,
        status_filter: Optional[str] = None,
    ) -> List[ClarificationRequest]:
        """Lists clarification requests for a given run strictly within the tenant boundary."""
        norm_filter = status_filter.strip().lower() if status_filter else None
        with self._lock:
            results: List[ClarificationRequest] = []
            for clrf in self._records.values():
                if clrf.tenant_id != tenant_id or clrf.run_id != run_id:
                    continue
                if norm_filter:
                    clrf_status = clrf.status.lower()
                    if norm_filter == "cancelled" and "cancelled" in clrf_status:
                        results.append(clrf.model_copy(deep=True))
                    elif clrf_status == norm_filter:
                        results.append(clrf.model_copy(deep=True))
                else:
                    results.append(clrf.model_copy(deep=True))
            return sorted(results, key=lambda c: c.created_at)

    def _apply_resolution(
        self,
        clrf: ClarificationRequest,
        actor_id: str,
        role: str,
        timestamp: str,
        resp_text: Optional[str],
        doc_id: Optional[str],
        sel_opt: Optional[str],
    ) -> Dict[str, Any]:
        """Applies response values to clarification and builds audit payload."""
        clrf.status = "resolved"
        clrf.resolved_at = timestamp
        clrf.resolved_by = actor_id
        clrf.responder_role = role
        if resp_text is not None:
            clrf.response_text = resp_text
        if doc_id is not None:
            clrf.attached_document_ref = doc_id
        if sel_opt is not None:
            clrf.selected_option = sel_opt

        return {
            "action": "CLARIFICATION_RESOLVED",
            "request_id": clrf.request_id,
            "claim_id": clrf.claim_id,
            "run_id": clrf.run_id,
            "response_text": resp_text,
            "attached_document_id": doc_id,
            "selected_option": sel_opt,
            "responder_role": role,
            "resolved_at": timestamp,
            "actor_id": actor_id,
        }

    def resolve_clarification(
        self,
        request_id: str,
        tenant_id: str,
        actor_id: str,
        responder_role: str,
        response_text: Optional[str] = None,
        attached_document_id: Optional[str] = None,
        selected_option: Optional[str] = None,
    ) -> Tuple[ClarificationRequest, Optional[AuditEvent]]:
        """Resolves a clarification, marks timestamp/actor, and emits cryptographic audit event."""
        with self._lock:
            clrf = self._records.get(request_id)
            if not clrf:
                raise KeyError(f"Clarification request '{request_id}' not found.")
            if clrf.tenant_id != tenant_id:
                raise PermissionError(f"Cross-tenant access forbidden for request '{request_id}'.")

            ts = datetime.now(timezone.utc).isoformat()
            payload = self._apply_resolution(
                clrf, actor_id, responder_role, ts, response_text, attached_document_id, selected_option
            )
            audit_event = _append_to_ledger_defensively(
                ledger=self._ledger,
                tenant_id=tenant_id,
                production_id=clrf.production_id or "prod_default",
                actor_id=actor_id,
                action_type="CLARIFICATION_RESOLVED",
                payload=payload,
            )
            return clrf.model_copy(deep=True), audit_event

    def clear_store(self) -> None:
        """Clears in-memory records (primarily for test fixture cleanup)."""
        with self._lock:
            self._records.clear()
            self._tenant_index.clear()


_default_clarification_store: Optional[ClarificationStore] = None


def get_clarification_store() -> ClarificationStore:
    """Provides or lazily initializes the default singleton ClarificationStore."""
    global _default_clarification_store
    if _default_clarification_store is None:
        _default_clarification_store = ClarificationStore()
    return _default_clarification_store


def set_clarification_store(store: Optional[ClarificationStore]) -> None:
    """Overrides or resets the ClarificationStore (useful for test fixtures)."""
    global _default_clarification_store
    _default_clarification_store = store
