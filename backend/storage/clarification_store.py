"""
backend/storage/clarification_store.py

Multi-tenant durable storage, checkpoint retention pinning, and ledger auditing.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from backend.domain.models import ClarificationRequest
from backend.storage.clarification_persistence import (
    append_ledger_event_safe,
    apply_clarification_resolution,
    atomic_save_run_clarifications,
    build_clarification_path,
    discover_clarifications_on_disk,
    read_run_clarifications_file,
    sync_clarification_to_firestore,
)
from backend.storage.ledger import CryptographicLedger
from backend.storage.ledger_types import AuditEvent

logger = logging.getLogger("lienmark.storage.clarifications")


class ClarificationStore:
    """Thread-safe multi-tenant durable store for ClarificationRequests."""

    def __init__(
        self,
        ledger: Optional[CryptographicLedger] = None,
        base_dir: str = "output/clarifications",
        firestore_client: Optional[object] = None,
    ) -> None:
        self._ledger = ledger or CryptographicLedger()
        self._base_dir = os.path.normpath(base_dir)
        self._firestore_client = firestore_client
        self._records: Dict[str, ClarificationRequest] = {}
        self._lock = threading.RLock()

    def _persist_to_disk(self, clrf: ClarificationRequest) -> None:
        """Writes clarification record to run file and triggers Firestore sync."""
        t_id, p_id = clrf.tenant_id or "default", clrf.production_id or "prod_default"
        file_path = build_clarification_path(self._base_dir, t_id, p_id, clrf.run_id)
        current = read_run_clarifications_file(file_path)
        current[clrf.request_id] = clrf
        atomic_save_run_clarifications(file_path, current)
        sync_clarification_to_firestore(self._firestore_client, clrf)

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
            clrf.production_id = production_id or clrf.production_id or "prod_default"
            self._records[clrf.request_id] = clrf
            self._persist_to_disk(clrf)
            return clrf.model_copy(deep=True)

    def _sync_disk_records(self, tenant_id: Optional[str] = None) -> None:
        """Synchronizes in-memory cache with persisted files on disk."""
        discovered = discover_clarifications_on_disk(self._base_dir, tenant_id)
        for req_id, clrf in discovered.items():
            if req_id not in self._records:
                self._records[req_id] = clrf

    def get_clarification(
        self, request_id: str, tenant_id: Optional[str] = None
    ) -> Optional[ClarificationRequest]:
        """Retrieves a ClarificationRequest enforcing strict tenant isolation."""
        with self._lock:
            if request_id not in self._records:
                self._sync_disk_records(tenant_id)
            clrf = self._records.get(request_id)
            if clrf is None:
                return None
            if tenant_id and clrf.tenant_id != tenant_id:
                logger.warning(f"Cross-tenant access rejected: {clrf.tenant_id} != {tenant_id}")
                return None
            return clrf.model_copy(deep=True)

    def list_clarifications_for_run(
        self, run_id: str, tenant_id: str, status_filter: Optional[str] = None
    ) -> List[ClarificationRequest]:
        """Lists clarification requests for a given run within tenant boundary."""
        with self._lock:
            self._sync_disk_records(tenant_id)
            flt = status_filter.strip().lower() if status_filter else None
            results: List[ClarificationRequest] = []
            for c in self._records.values():
                if c.tenant_id == tenant_id and c.run_id == run_id:
                    st = c.status.lower()
                    if not flt or (flt == "cancelled" and "cancelled" in st) or st == flt:
                        results.append(c.model_copy(deep=True))
            return sorted(results, key=lambda c: c.created_at)

    def list_open_clarifications(
        self, tenant_id: str, production_id: Optional[str] = None
    ) -> List[ClarificationRequest]:
        """Lists pending or unresolved clarifications for a tenant and production."""
        with self._lock:
            self._sync_disk_records(tenant_id)
            results: List[ClarificationRequest] = []
            for c in self._records.values():
                if c.tenant_id == tenant_id and (not production_id or c.production_id == production_id):
                    if c.status.lower() not in ("resolved", "cancelled", "expired"):
                        results.append(c.model_copy(deep=True))
            return sorted(results, key=lambda c: c.created_at)

    def resolve_clarification(
        self,
        request_id: str,
        tenant_id: str,
        actor_id: str,
        responder_role: str,
        response_text: Optional[str] = None,
        attached_document_id: Optional[str] = None,
        selected_option: Optional[str] = None,
        resolution_channel: Optional[str] = None,
    ) -> Tuple[ClarificationRequest, Optional[AuditEvent]]:
        """Resolves clarification, commits changes, and emits cryptographic audit event."""
        with self._lock:
            clrf = self.get_clarification(request_id, tenant_id)
            if not clrf:
                raise KeyError(f"Clarification request '{request_id}' not found.")
            if clrf.tenant_id != tenant_id:
                raise PermissionError(f"Cross-tenant access forbidden for request '{request_id}'.")
            _, payload = apply_clarification_resolution(
                clrf, actor_id, responder_role, response_text, attached_document_id, selected_option, resolution_channel
            )
            self._records[clrf.request_id] = clrf
            self._persist_to_disk(clrf)
            ev = append_ledger_event_safe(
                self._ledger, tenant_id, clrf.production_id or "prod_default",
                actor_id, "CLARIFICATION_RESOLVED", payload,
            )
            return clrf.model_copy(deep=True), ev

    def flag_candidate_document(
        self, request_id: str, tenant_id: str, candidate_document_ref: str, match_confidence: float
    ) -> ClarificationRequest:
        """Flags clarification as candidate_document_detected requiring human confirmation."""
        with self._lock:
            clrf = self.get_clarification(request_id, tenant_id)
            if not clrf:
                raise KeyError(f"Clarification request '{request_id}' not found.")
            if clrf.tenant_id != tenant_id:
                raise PermissionError(f"Cross-tenant access forbidden for request '{request_id}'.")
            clrf.status, clrf.candidate_document_ref, clrf.match_confidence = "candidate_document_detected", candidate_document_ref, match_confidence
            self._records[clrf.request_id] = clrf
            self._persist_to_disk(clrf)
            return clrf.model_copy(deep=True)

    def is_checkpoint_pinned(
        self, run_id: str, tenant_id: str, clarification_ids: Optional[List[str]] = None
    ) -> bool:
        """Retention pinning: returns True if linked clarifications remain PENDING."""
        with self._lock:
            if clarification_ids:
                for cid in clarification_ids:
                    c = self.get_clarification(cid, tenant_id)
                    if c and c.status.lower() == "pending":
                        return True
                return False
            pending = self.list_clarifications_for_run(run_id, tenant_id, status_filter="pending")
            return len(pending) > 0

    def expire_clarification(
        self, request_id: str, tenant_id: str, reason: str = "workflow_deadline_exceeded"
    ) -> Tuple[ClarificationRequest, Optional[AuditEvent]]:
        """Transitions clarification to EXPIRED, invalidating resume, and appends audit event."""
        with self._lock:
            clrf = self.get_clarification(request_id, tenant_id)
            if not clrf:
                raise KeyError(f"Clarification request '{request_id}' not found.")
            if clrf.tenant_id != tenant_id:
                raise PermissionError(f"Cross-tenant access forbidden for request '{request_id}'.")
            now_utc = datetime.now(timezone.utc).isoformat()
            clrf.status, clrf.expired_at = "expired", now_utc
            self._records[clrf.request_id] = clrf
            self._persist_to_disk(clrf)
            payload: Dict[str, object] = {
                "action": "CLARIFICATION_EXPIRED", "request_id": clrf.request_id,
                "claim_id": clrf.claim_id, "run_id": clrf.run_id, "expired_at": now_utc, "reason": reason,
            }
            ev = append_ledger_event_safe(
                self._ledger, tenant_id, clrf.production_id or "prod_default",
                "system_deadline_monitor", "CLARIFICATION_EXPIRED", payload,
            )
            return clrf.model_copy(deep=True), ev

    def check_and_expire_deadline(
        self, request_id: str, tenant_id: str, deadline_utc: Optional[str] = None
    ) -> Tuple[ClarificationRequest, bool]:
        """Checks configured workflow deadline and triggers expiration if exceeded."""
        clrf = self.get_clarification(request_id, tenant_id)
        if not clrf:
            raise KeyError(f"Clarification request '{request_id}' not found.")
        dl = deadline_utc or clrf.deadline_utc
        if dl and clrf.status.lower() == "pending" and datetime.now(timezone.utc).isoformat() > dl:
            exp_clrf, _ = self.expire_clarification(request_id, tenant_id, "deadline_exceeded")
            return exp_clrf, True
        return clrf, False

    def is_resume_eligible(
        self, run_id: str, tenant_id: str, clarification_ids: Optional[List[str]] = None
    ) -> bool:
        """Determines resume eligibility: returns False if any linked clarification has expired."""
        with self._lock:
            if clarification_ids:
                for cid in clarification_ids:
                    c = self.get_clarification(cid, tenant_id)
                    if c and c.status.lower() == "expired":
                        return False
            return not any(c.status.lower() == "expired" for c in self.list_clarifications_for_run(run_id, tenant_id))

    def clear_store(self) -> None:
        """Clears in-memory records and local storage files."""
        with self._lock:
            self._records.clear()
            if os.path.exists(self._base_dir):
                shutil.rmtree(self._base_dir, ignore_errors=True)

_default_clarification_store: Optional[ClarificationStore] = None

def get_clarification_store() -> ClarificationStore:
    """Provides or lazily initializes default ClarificationStore."""
    global _default_clarification_store
    if _default_clarification_store is None:
        _default_clarification_store = ClarificationStore()
    return _default_clarification_store

def set_clarification_store(store: Optional[ClarificationStore]) -> None:
    """Overrides or resets default ClarificationStore."""
    global _default_clarification_store
    _default_clarification_store = store
