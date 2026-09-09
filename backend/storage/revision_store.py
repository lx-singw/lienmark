"""
backend/storage/revision_store.py

Multi-tenant persistence for RevisionRecord, RevisionAuditDispatch, and ResultSnapshot.
Uses Firestore Native mode in deployed environments; LocalRevisionStore when USE_LOCAL_STORAGE=true.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict
from google.cloud import firestore

from backend.domain.revision_models import (
    RevisionRecord,
    RevisionAuditDispatch,
    ResultSnapshot,
)


class RevisionStoreError(Exception):
    pass


class RevisionConflictError(RevisionStoreError):
    pass


class RevisionNotFoundError(RevisionStoreError):
    pass


class RevisionStoreInterface(ABC):
    @abstractmethod
    def save_revision_and_dispatch(self, record: RevisionRecord, dispatch: RevisionAuditDispatch) -> RevisionAuditDispatch:
        pass

    @abstractmethod
    def get_dispatch_by_idempotency_key(self, tenant_id: str, production_id: str, idempotency_key: str) -> Optional[RevisionAuditDispatch]:
        pass

    @abstractmethod
    def get_dispatch(self, tenant_id: str, production_id: str, audit_id: str) -> Optional[RevisionAuditDispatch]:
        pass

    @abstractmethod
    def update_dispatch(self, tenant_id: str, production_id: str, dispatch: RevisionAuditDispatch) -> bool:
        pass

    @abstractmethod
    def save_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot) -> None:
        pass

    @abstractmethod
    def get_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot_id: str) -> Optional[ResultSnapshot]:
        pass

    @abstractmethod
    def list_abandoned_dispatches(self, tenant_id: str, production_id: str) -> List[RevisionAuditDispatch]:
        pass


class LocalRevisionStore(RevisionStoreInterface):
    def __init__(self, base_path: str = ".local_storage") -> None:
        self.base_path = base_path
        self._dispatches: Dict[str, Dict[str, Any]] = {}
        self._revisions: Dict[str, Dict[str, Any]] = {}
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def get_dispatch_by_idempotency_key(self, tenant_id: str, production_id: str, idempotency_key: str) -> Optional[RevisionAuditDispatch]:
        for d in self._dispatches.values():
            if d.get("tenant_id") == tenant_id and d.get("production_id") == production_id and d.get("idempotency_key") == idempotency_key:
                return RevisionAuditDispatch(**{k: v for k, v in d.items() if k not in ("tenant_id", "production_id")})
        return None

    def get_dispatch(self, tenant_id: str, production_id: str, audit_id: str) -> Optional[RevisionAuditDispatch]:
        d = self._dispatches.get(audit_id)
        if d and d.get("tenant_id") == tenant_id and d.get("production_id") == production_id:
            return RevisionAuditDispatch(**{k: v for k, v in d.items() if k not in ("tenant_id", "production_id")})
        return None

    def save_revision_and_dispatch(self, record: RevisionRecord, dispatch: RevisionAuditDispatch) -> RevisionAuditDispatch:
        existing = self.get_dispatch_by_idempotency_key(record.tenant_id, record.production_id, dispatch.idempotency_key)
        if existing:
            if existing.payload_hash != dispatch.payload_hash:
                raise RevisionConflictError(f"Idempotency key {dispatch.idempotency_key} used with different payload")
            return existing

        r_dict = getattr(record, "model_dump", getattr(record, "dict", lambda: {}))()
        d_dict = getattr(dispatch, "model_dump", getattr(dispatch, "dict", lambda: {}))()
        d_dict["tenant_id"] = record.tenant_id
        d_dict["production_id"] = record.production_id

        self._revisions[record.revision_id] = r_dict
        self._dispatches[dispatch.audit_id] = d_dict
        return dispatch

    def update_dispatch(self, tenant_id: str, production_id: str, dispatch: RevisionAuditDispatch) -> bool:
        d_dict = getattr(dispatch, "model_dump", getattr(dispatch, "dict", lambda: {}))()
        d_dict["tenant_id"] = tenant_id
        d_dict["production_id"] = production_id
        self._dispatches[dispatch.audit_id] = d_dict
        return True

    def save_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot) -> None:
        key = f"{tenant_id}:{production_id}:{revision_id}:snapshot_{snapshot.version_number}"
        if key in self._snapshots:
            raise RevisionConflictError(f"Snapshot version {snapshot.version_number} already exists")
        s_dict = getattr(snapshot, "model_dump", getattr(snapshot, "dict", lambda: {}))()
        self._snapshots[key] = s_dict

    def get_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot_id: str) -> Optional[ResultSnapshot]:
        key = f"{tenant_id}:{production_id}:{revision_id}:{snapshot_id}"
        data = self._snapshots.get(key)
        return ResultSnapshot(**data) if data else None

    def list_abandoned_dispatches(self, tenant_id: str, production_id: str) -> List[RevisionAuditDispatch]:
        now_epoch = time.time()
        abandoned = []
        for d in self._dispatches.values():
            if d.get("tenant_id") == tenant_id and d.get("production_id") == production_id:
                st = d.get("status")
                lease = d.get("lease_expires_at")
                lease_ts = lease.timestamp() if lease and hasattr(lease, "timestamp") else 0
                if st == "QUEUED" or (st == "PROCESSING" and lease_ts < now_epoch):
                    clean_d = {k: v for k, v in d.items() if k not in ("tenant_id", "production_id")}
                    abandoned.append(RevisionAuditDispatch(**clean_d))
        return abandoned


class FirestoreRevisionStore(RevisionStoreInterface):
    def __init__(self) -> None:
        from backend.storage.firestore_client import get_firestore_client
        client = get_firestore_client()
        self.db = getattr(client, "db", client)

    def _prod_ref(self, t_id: str, p_id: str) -> Any:
        return self.db.collection("organizations").document(t_id).collection("productions").document(p_id)

    def get_dispatch_by_idempotency_key(self, tenant_id: str, production_id: str, idempotency_key: str) -> Optional[RevisionAuditDispatch]:
        doc = self._prod_ref(tenant_id, production_id).collection("idempotency_keys").document(idempotency_key).get()
        return RevisionAuditDispatch(**doc.to_dict()) if doc.exists else None

    def get_dispatch(self, tenant_id: str, production_id: str, audit_id: str) -> Optional[RevisionAuditDispatch]:
        doc = self._prod_ref(tenant_id, production_id).collection("revision_audits").document(audit_id).get()
        return RevisionAuditDispatch(**doc.to_dict()) if doc.exists else None

    def save_revision_and_dispatch(self, record: RevisionRecord, dispatch: RevisionAuditDispatch) -> RevisionAuditDispatch:
        prod_ref = self._prod_ref(record.tenant_id, record.production_id)
        idem_ref = prod_ref.collection("idempotency_keys").document(dispatch.idempotency_key)
        rev_ref = prod_ref.collection("revisions").document(record.revision_id)
        audit_ref = prod_ref.collection("revision_audits").document(dispatch.audit_id)

        doc = idem_ref.get()
        if doc.exists:
            existing = doc.to_dict() or {}
            if existing.get("payload_hash") != dispatch.payload_hash:
                raise RevisionConflictError(f"Idempotency key {dispatch.idempotency_key} used with different payload")
            return RevisionAuditDispatch(**existing)

        batch = self.db.batch()
        batch.set(rev_ref, getattr(record, "model_dump", getattr(record, "dict", lambda: {}))())
        d_dict = getattr(dispatch, "model_dump", getattr(dispatch, "dict", lambda: {}))()
        batch.set(audit_ref, d_dict)
        batch.set(idem_ref, d_dict)
        batch.commit()
        return dispatch

    def update_dispatch(self, tenant_id: str, production_id: str, dispatch: RevisionAuditDispatch) -> bool:
        ref = self._prod_ref(tenant_id, production_id).collection("revision_audits").document(dispatch.audit_id)
        ref.set(getattr(dispatch, "model_dump", getattr(dispatch, "dict", lambda: {}))())
        return True

    def save_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot) -> None:
        ref = self._prod_ref(tenant_id, production_id).collection("revisions").document(revision_id)\
            .collection("snapshots").document(f"snapshot_{snapshot.version_number}")
        if ref.get().exists:
            raise RevisionConflictError(f"Snapshot version {snapshot.version_number} already exists")
        ref.set(getattr(snapshot, "model_dump", getattr(snapshot, "dict", lambda: {}))())

    def get_result_snapshot(self, tenant_id: str, production_id: str, revision_id: str, snapshot_id: str) -> Optional[ResultSnapshot]:
        doc = self._prod_ref(tenant_id, production_id).collection("revisions").document(revision_id)\
            .collection("snapshots").document(snapshot_id).get()
        return ResultSnapshot(**doc.to_dict()) if doc.exists else None

    def list_abandoned_dispatches(self, tenant_id: str, production_id: str) -> List[RevisionAuditDispatch]:
        now = time.time()
        docs = self._prod_ref(tenant_id, production_id).collection("revision_audits").stream()
        abandoned = []
        for d in docs:
            data = d.to_dict() or {}
            st = data.get("status")
            lease = data.get("lease_expires_at")
            lease_ts = lease.timestamp() if lease and hasattr(lease, "timestamp") else 0
            if st == "QUEUED" or (st == "PROCESSING" and lease_ts < now):
                abandoned.append(RevisionAuditDispatch(**data))
        return abandoned


_GLOBAL_REVISION_STORE: Optional[RevisionStoreInterface] = None


def get_revision_store() -> RevisionStoreInterface:
    global _GLOBAL_REVISION_STORE
    if _GLOBAL_REVISION_STORE is not None:
        return _GLOBAL_REVISION_STORE

    is_cloud_run = bool(os.getenv("K_SERVICE") or os.getenv("K_REVISION") or os.getenv("GOOGLE_CLOUD_PROJECT"))
    use_local = os.getenv("USE_LOCAL_STORAGE", "").lower() in ("true", "1")

    if is_cloud_run and not use_local:
        try:
            _GLOBAL_REVISION_STORE = FirestoreRevisionStore()
            return _GLOBAL_REVISION_STORE
        except Exception as exc:
            pass
    _GLOBAL_REVISION_STORE = LocalRevisionStore()
    return _GLOBAL_REVISION_STORE
