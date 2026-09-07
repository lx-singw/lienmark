"""
Distributed Lock Manager Test Suite.
Tests DistributedLockManager for lease acquisition, reentrancy, contention,
expiration recovery, unauthorized release rejection, and multi-thread concurrency.
Authored strictly under Google AntiGravity architectural guidelines.
"""

import threading
import time
from typing import List
import pytest

from backend.storage.lock_types import (
    DistributedLockRecord,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
)
from backend.storage.locks import DistributedLockManager


@pytest.fixture
def lock_manager() -> DistributedLockManager:
    """Fixture providing an isolated in-memory DistributedLockManager instance."""
    mgr = DistributedLockManager(in_memory=True)
    mgr.clear_memory_state()
    return mgr


def test_successful_lock_acquisition(lock_manager: DistributedLockManager) -> None:
    """Verifies lock acquisition with initial monotonic fence token."""
    rec = lock_manager.acquire_lock(
        lock_key="lock:prod:001",
        owner_id="worker_alpha",
        ttl_seconds=30.0,
        metadata={"priority": "high"},
    )
    assert isinstance(rec, DistributedLockRecord)
    assert rec.lock_key == "lock:prod:001"
    assert rec.owner_id == "worker_alpha"
    assert rec.fence_token == 1
    assert rec.metadata.get("priority") == "high"
    assert rec.is_expired() is False

    active_rec = lock_manager.get_lock("lock:prod:001")
    assert active_rec is not None
    assert active_rec.owner_id == "worker_alpha"
    assert active_rec.fence_token == 1
    assert lock_manager.get_fencing_token("lock:prod:001") == 1


def test_reentrant_renewal_by_same_owner(lock_manager: DistributedLockManager) -> None:
    """Verifies reentrant acquisition and renew_lock extend TTL without error."""
    rec1 = lock_manager.acquire_lock(
        lock_key="lock:prod:002",
        owner_id="worker_alpha",
        ttl_seconds=10.0,
    )
    initial_expiry = rec1.expires_at_utc

    # 1. Reentrant acquire extends expiration without incrementing token
    rec2 = lock_manager.acquire_lock(
        lock_key="lock:prod:002",
        owner_id="worker_alpha",
        ttl_seconds=60.0,
    )
    assert rec2.expires_at_utc > initial_expiry
    assert rec2.fence_token == 1

    # 2. renew_lock extends TTL for the holding owner
    rec3 = lock_manager.renew_lock(
        lock_key="lock:prod:002",
        owner_id="worker_alpha",
        extension_seconds=120.0,
    )
    assert rec3.expires_at_utc > rec2.expires_at_utc
    assert rec3.fence_token == 1


def test_contention_rejection_raises_error(lock_manager: DistributedLockManager) -> None:
    """Verifies second owner attempting acquisition raises LockAcquisitionError."""
    lock_manager.acquire_lock(
        lock_key="lock:prod:003",
        owner_id="worker_alpha",
        ttl_seconds=30.0,
    )

    with pytest.raises(LockAcquisitionError) as exc_info:
        lock_manager.acquire_lock(
            lock_key="lock:prod:003",
            owner_id="worker_beta",
            ttl_seconds=30.0,
        )

    assert "is held by 'worker_alpha'" in str(exc_info.value)
    active = lock_manager.get_lock("lock:prod:003")
    assert active is not None
    assert active.owner_id == "worker_alpha"


def test_expiration_and_auto_recovery(lock_manager: DistributedLockManager) -> None:
    """Verifies expired lock can be acquired by a new owner, incrementing fence token."""
    rec1 = lock_manager.acquire_lock(
        lock_key="lock:prod:004",
        owner_id="worker_alpha",
        ttl_seconds=0.05,
    )
    assert rec1.fence_token == 1

    # Wait for the short TTL to lapse
    time.sleep(0.06)
    assert lock_manager.get_lock("lock:prod:004") is None

    # Renewal attempt on expired lock fails
    with pytest.raises(LockExpiredError):
        lock_manager.renew_lock(
            lock_key="lock:prod:004",
            owner_id="worker_alpha",
            extension_seconds=30.0,
        )

    # New owner acquires expired lock, triggering auto-recovery with incremented fence
    rec2 = lock_manager.acquire_lock(
        lock_key="lock:prod:004",
        owner_id="worker_gamma",
        ttl_seconds=30.0,
    )
    assert rec2.owner_id == "worker_gamma"
    assert rec2.fence_token == 2
    assert lock_manager.get_fencing_token("lock:prod:004") == 2


def test_release_lock_lifecycle_and_unauthorized_rejection(
    lock_manager: DistributedLockManager,
) -> None:
    """Verifies release_lock releases held lock and prevents unauthorized release."""
    lock_manager.acquire_lock(
        lock_key="lock:prod:005",
        owner_id="worker_alpha",
        ttl_seconds=30.0,
    )

    # Wrong owner attempt returns False and does not release lock
    assert lock_manager.release_lock("lock:prod:005", "wrong_owner") is False
    assert lock_manager.get_lock("lock:prod:005") is not None

    # Legitimate owner releases lock
    assert lock_manager.release_lock("lock:prod:005", "worker_alpha") is True
    assert lock_manager.get_lock("lock:prod:005") is None

    # Redundant release returns False
    assert lock_manager.release_lock("lock:prod:005", "worker_alpha") is False


def test_thread_concurrency_single_winner(lock_manager: DistributedLockManager) -> None:
    """Verifies 10 concurrent threads attempting acquisition: exactly 1 succeeds."""
    barrier = threading.Barrier(10)
    successes: List[DistributedLockRecord] = []
    rejections: List[int] = []
    lock_res = threading.Lock()

    def _worker_attempt(worker_idx: int) -> None:
        barrier.wait()
        try:
            rec = lock_manager.acquire_lock(
                lock_key="lock:prod:concurrent",
                owner_id=f"thread_worker_{worker_idx}",
                ttl_seconds=60.0,
            )
            with lock_res:
                successes.append(rec)
        except LockAcquisitionError:
            with lock_res:
                rejections.append(worker_idx)

    threads = [threading.Thread(target=_worker_attempt, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 1
    assert len(rejections) == 9
    winner = successes[0]
    active = lock_manager.get_lock("lock:prod:concurrent")
    assert active is not None
    assert active.owner_id == winner.owner_id
    assert active.fence_token == 1
