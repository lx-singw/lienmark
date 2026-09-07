"""
Lienmark In-Memory Distributed Lock Store.

Provides thread-safe in-memory state coordination for distributed locks,
monotonic fencing tokens, and leases during testing and single-instance execution.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import threading
from typing import Any, Dict, Optional, Set

from backend.storage.lock_types import (
    DistributedLockRecord,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
)


class InMemoryLockStore:
    """Thread-safe in-memory lock store managing leases and strictly monotonic tokens."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._locks: Dict[str, DistributedLockRecord] = {}
        self._tokens: Dict[str, int] = {}
        self._released: Set[str] = set()

    def acquire(
        self,
        lock_key: str,
        owner_id: str,
        ttl_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DistributedLockRecord:
        """Atomically acquires lock lease or extends lease if reentrant by same owner."""
        with self._lock:
            existing = self._locks.get(lock_key)
            is_released = lock_key in self._released
            now = datetime.now(timezone.utc)
            now_iso = now.isoformat()
            exp_iso = (now + timedelta(seconds=ttl_seconds)).isoformat()

            if existing is not None and not is_released and not existing.is_expired():
                if existing.owner_id == owner_id:
                    existing.expires_at_utc = exp_iso
                    if metadata is not None:
                        existing.metadata.update(copy.deepcopy(metadata))
                    return copy.deepcopy(existing)
                raise LockAcquisitionError(
                    f"Lock '{lock_key}' is held by '{existing.owner_id}' until {existing.expires_at_utc}"
                )

            token = self._tokens.get(lock_key, 0) + 1
            self._tokens[lock_key] = token
            self._released.discard(lock_key)
            record = DistributedLockRecord(
                lock_key=lock_key,
                owner_id=owner_id,
                acquired_at_utc=now_iso,
                expires_at_utc=exp_iso,
                fence_token=token,
                metadata=copy.deepcopy(metadata) if metadata else {},
            )
            self._locks[lock_key] = record
            return copy.deepcopy(record)

    def renew(
        self,
        lock_key: str,
        owner_id: str,
        extension_seconds: float,
    ) -> DistributedLockRecord:
        """Renews active lock TTL for the given owner."""
        with self._lock:
            existing = self._locks.get(lock_key)
            if existing is None or lock_key in self._released:
                raise LockReleaseError(f"Cannot renew lock '{lock_key}': lock is not held.")
            if existing.owner_id != owner_id:
                raise LockReleaseError(
                    f"Cannot renew lock '{lock_key}': held by '{existing.owner_id}', not '{owner_id}'."
                )
            if existing.is_expired():
                raise LockExpiredError(
                    f"Cannot renew lock '{lock_key}': lock expired at {existing.expires_at_utc}."
                )

            now = datetime.now(timezone.utc)
            new_exp = (now + timedelta(seconds=extension_seconds)).isoformat()
            existing.expires_at_utc = new_exp
            return copy.deepcopy(existing)

    def release(self, lock_key: str, owner_id: str) -> bool:
        """Releases lock lease if owner matches and lock is not expired."""
        with self._lock:
            existing = self._locks.get(lock_key)
            if existing is None or lock_key in self._released:
                return False
            if existing.owner_id != owner_id or existing.is_expired():
                return False
            self._released.add(lock_key)
            return True

    def get_lock(self, lock_key: str) -> Optional[DistributedLockRecord]:
        """Retrieves active unexpired lock record, or None."""
        with self._lock:
            if lock_key in self._released:
                return None
            record = self._locks.get(lock_key)
            if record is None or record.is_expired():
                return None
            return copy.deepcopy(record)

    def get_fencing_token(self, lock_key: str) -> int:
        """Retrieves strictly monotonic fence token for lock key."""
        with self._lock:
            return self._tokens.get(lock_key, 0)

    def clear(self) -> None:
        """Clears all in-memory lock state."""
        with self._lock:
            self._locks.clear()
            self._tokens.clear()
            self._released.clear()


__all__ = ["InMemoryLockStore"]
