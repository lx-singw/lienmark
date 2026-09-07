"""
Lienmark Distributed Lock Coordinator.

Provides thread-safe and distributed locking across workers with support
for both in-memory state and Google Cloud Firestore persistence.
Enforces monotonic fencing tokens for split-brain protection.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from backend.storage.firestore_client import get_firestore_client
from backend.storage.lock_firestore import FirestoreLockStore
from backend.storage.lock_memory import InMemoryLockStore
from backend.storage.lock_types import (
    DistributedLock,
    DistributedLockRecord,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
)

logger = logging.getLogger("lienmark.storage.locks")


class DistributedLockManager:
    """
    Thread-safe distributed locking coordinator.

    Coordinates locks with strictly monotonic fencing tokens across worker processes.
    Supports in-memory state for testing/local execution and native Google Cloud
    Firestore (/locks/{lock_key}) documents for multi-worker production clusters.
    """

    def __init__(
        self,
        firestore_client: Optional[Any] = None,
        in_memory: bool = False,
    ) -> None:
        self._mem_store = InMemoryLockStore()
        self._fs_store: Optional[FirestoreLockStore] = None
        self._legacy_counter: int = 0
        self._mgr_lock = threading.RLock()

        if not in_memory:
            self._init_backend(firestore_client)

    def _init_backend(self, client: Optional[Any]) -> None:
        """Initializes backend Firestore connection or falls back to in-memory mode."""
        if client is not None:
            db = client if hasattr(client, "collection") else getattr(client, "db", client)
            self._fs_store = FirestoreLockStore(db)
            return
        try:
            active_client = get_firestore_client()
            if hasattr(active_client, "db") and getattr(active_client, "db") is not None:
                self._fs_store = FirestoreLockStore(active_client.db)
        except Exception as exc:
            logger.warning(
                f"Could not connect to Firestore for distributed locks ({exc}). "
                "Using in-memory store."
            )

    def acquire_lock(
        self,
        lock_key: str,
        owner_id: str,
        ttl_seconds: float = 30.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DistributedLockRecord:
        """Atomically acquires a distributed lock or extends lease if reentrant."""
        if not lock_key or not owner_id:
            raise ValueError("lock_key and owner_id must be non-empty strings")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        if self._fs_store is not None:
            return self._fs_store.acquire(lock_key, owner_id, ttl_seconds, metadata)
        return self._mem_store.acquire(lock_key, owner_id, ttl_seconds, metadata)

    def renew_lock(
        self,
        lock_key: str,
        owner_id: str,
        extension_seconds: float = 30.0,
    ) -> DistributedLockRecord:
        """Extends the expiration lease for a currently held lock."""
        if not lock_key or not owner_id:
            raise ValueError("lock_key and owner_id must be non-empty strings")
        if extension_seconds <= 0:
            raise ValueError("extension_seconds must be positive")

        if self._fs_store is not None:
            return self._fs_store.renew(lock_key, owner_id, extension_seconds)
        return self._mem_store.renew(lock_key, owner_id, extension_seconds)

    def release_lock(self, lock_key: str, owner_id: str) -> bool:
        """Releases lock if owner matches and lock is not expired."""
        if not lock_key or not owner_id:
            return False
        if self._fs_store is not None:
            return self._fs_store.release(lock_key, owner_id)
        return self._mem_store.release(lock_key, owner_id)

    def get_lock(self, lock_key: str) -> Optional[DistributedLockRecord]:
        """Returns the currently active lock record, or None if expired or not held."""
        if not lock_key:
            return None
        if self._fs_store is not None:
            return self._fs_store.get_lock(lock_key)
        return self._mem_store.get_lock(lock_key)

    def get_fencing_token(self, lock_key: str) -> int:
        """Returns the latest strictly monotonic fence token for this lock key."""
        if not lock_key:
            return 0
        if self._fs_store is not None:
            return self._fs_store.get_fencing_token(lock_key)
        return self._mem_store.get_fencing_token(lock_key)

    def clear_memory_state(self) -> None:
        """Resets all in-memory lock state for testing isolation."""
        with self._mgr_lock:
            self._legacy_counter = 0
            self._mem_store.clear()

    # ── Legacy / Compatibility Interface ─────────────────────────────────────────

    def acquire(
        self,
        lock_key: str,
        ttl_seconds: float = 60.0,
        owner_id: Optional[str] = None,
    ) -> Optional[DistributedLock]:
        """Compatibility wrapper for acquire_lock returning legacy DistributedLock."""
        clean_key = lock_key.strip()
        eff_owner = owner_id or f"worker_{uuid.uuid4().hex[:8]}"
        with self._mgr_lock:
            try:
                rec = self.acquire_lock(clean_key, eff_owner, ttl_seconds=ttl_seconds)
                now = time.time()
                return DistributedLock(
                    lock_key=rec.lock_key,
                    fence_token=rec.fence_token,
                    owner_id=rec.owner_id,
                    acquired_at=now,
                    expires_at=now + ttl_seconds,
                )
            except LockAcquisitionError:
                return None

    def release(self, lock: Any) -> bool:
        """Compatibility wrapper for release_lock accepting a lock object."""
        if not lock or not getattr(lock, "lock_key", None):
            return False
        return self.release_lock(lock.lock_key, getattr(lock, "owner_id", ""))

    def is_locked(self, lock_key: str) -> bool:
        """Compatibility check whether a lock is currently active."""
        return self.get_lock(lock_key) is not None

    def reset(self) -> None:
        """Compatibility alias for clear_memory_state."""
        self.clear_memory_state()


_lock_manager_instance: Optional[DistributedLockManager] = None
_lock_manager_mutex = threading.Lock()


def get_distributed_lock_manager(
    in_memory: bool = False,
    force_new: bool = False,
) -> DistributedLockManager:
    """Factory function providing active singleton DistributedLockManager."""
    global _lock_manager_instance
    with _lock_manager_mutex:
        if _lock_manager_instance is not None and not force_new:
            return _lock_manager_instance
        _lock_manager_instance = DistributedLockManager(in_memory=in_memory)
        return _lock_manager_instance


__all__ = [
    "DistributedLock",
    "DistributedLockRecord",
    "DistributedLockManager",
    "get_distributed_lock_manager",
    "LockAcquisitionError",
    "LockExpiredError",
    "LockReleaseError",
]
