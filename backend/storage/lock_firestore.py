"""
Lienmark Google Cloud Firestore Distributed Lock Store.

Provides transactional document-level locking under /locks/{lock_key}
using Google Cloud Firestore transactions and monotonic fence tokens.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.storage.lock_types import (
    DistributedLockRecord,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
)

try:
    from google.cloud import firestore as gcp_firestore  # type: ignore

    _transactional = gcp_firestore.transactional
except ImportError:
    def _transactional(fn: Any) -> Any:
        return fn


class FirestoreLockStore:
    """Firestore transactional lock store operating on /locks/{lock_key} documents."""

    def __init__(self, db: Any) -> None:
        self._db = db

    def acquire(
        self,
        lock_key: str,
        owner_id: str,
        ttl_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DistributedLockRecord:
        """Atomically acquires lock or extends lease in a Firestore transaction."""
        doc_ref = self._db.collection("locks").document(lock_key)
        txn = self._db.transaction()

        @_transactional
        def _txn_acquire(transaction: Any) -> DistributedLockRecord:
            snapshot = doc_ref.get(transaction=transaction)
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()
            exp_iso = (now + timedelta(seconds=ttl_seconds)).isoformat()

            if snapshot.exists:
                data = snapshot.to_dict() or {}
                is_rel = data.get("is_released", False)
                prev_token = int(data.get("fence_token", 0))
                rec = DistributedLockRecord.model_validate(data)
                if not is_rel and not rec.is_expired():
                    if rec.owner_id == owner_id:
                        rec.expires_at_utc = exp_iso
                        if metadata is not None:
                            rec.metadata.update(copy.deepcopy(metadata))
                        payload = rec.model_dump()
                        payload["is_released"] = False
                        transaction.set(doc_ref, payload, merge=True)
                        return rec
                    raise LockAcquisitionError(
                        f"Lock '{lock_key}' is held by '{rec.owner_id}' until {rec.expires_at_utc}"
                    )
            else:
                prev_token = 0

            new_token = prev_token + 1
            new_rec = DistributedLockRecord(
                lock_key=lock_key,
                owner_id=owner_id,
                acquired_at_utc=now_iso,
                expires_at_utc=exp_iso,
                fence_token=new_token,
                metadata=copy.deepcopy(metadata) if metadata else {},
            )
            data_to_set = new_rec.model_dump()
            data_to_set["is_released"] = False
            transaction.set(doc_ref, data_to_set)
            return new_rec

        return _txn_acquire(txn)

    def renew(
        self,
        lock_key: str,
        owner_id: str,
        extension_seconds: float,
    ) -> DistributedLockRecord:
        """Transactionally extends lease of an unexpired held lock."""
        doc_ref = self._db.collection("locks").document(lock_key)
        txn = self._db.transaction()

        @_transactional
        def _txn_renew(transaction: Any) -> DistributedLockRecord:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                raise LockReleaseError(f"Cannot renew lock '{lock_key}': document not found.")
            data = snapshot.to_dict() or {}
            if data.get("is_released", False):
                raise LockReleaseError(f"Cannot renew lock '{lock_key}': lock is already released.")

            rec = DistributedLockRecord.model_validate(data)
            if rec.owner_id != owner_id:
                raise LockReleaseError(
                    f"Cannot renew lock '{lock_key}': held by '{rec.owner_id}', not '{owner_id}'."
                )
            if rec.is_expired():
                raise LockExpiredError(
                    f"Cannot renew lock '{lock_key}': lock expired at {rec.expires_at_utc}."
                )

            now = datetime.now(timezone.utc)
            new_exp = (now + timedelta(seconds=extension_seconds)).isoformat()
            rec.expires_at_utc = new_exp
            transaction.update(doc_ref, {"expires_at_utc": new_exp})
            return rec

        return _txn_renew(txn)

    def release(self, lock_key: str, owner_id: str) -> bool:
        """Transactionally marks lock released if owned by owner_id and not expired."""
        doc_ref = self._db.collection("locks").document(lock_key)
        txn = self._db.transaction()

        @_transactional
        def _txn_release(transaction: Any) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict() or {}
            if data.get("is_released", False):
                return False
            rec = DistributedLockRecord.model_validate(data)
            if rec.owner_id != owner_id or rec.is_expired():
                return False
            transaction.update(doc_ref, {"is_released": True})
            return True

        return _txn_release(txn)

    def get_lock(self, lock_key: str) -> Optional[DistributedLockRecord]:
        """Retrieves active unexpired lock record from Firestore, or None."""
        doc_ref = self._db.collection("locks").document(lock_key)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict() or {}
        if data.get("is_released", False):
            return None
        rec = DistributedLockRecord.model_validate(data)
        if rec.is_expired():
            return None
        return rec

    def get_fencing_token(self, lock_key: str) -> int:
        """Retrieves current fence token stored in Firestore document."""
        doc_ref = self._db.collection("locks").document(lock_key)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return 0
        data = snapshot.to_dict() or {}
        return int(data.get("fence_token", 0))


__all__ = ["FirestoreLockStore"]
