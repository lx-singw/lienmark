"""
Comprehensive test suite for Lienmark Distributed Lock Coordinator and Types.

Validates Sprint 2.1 distributed lock implementation:
1. lock_types: exceptions, models, ISO 8601 parsing, expiration checks.
2. locks: in-memory & Firestore test-and-set, reentrancy, fencing tokens, concurrency.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import time
from unittest.mock import MagicMock
import pytest

from backend.storage.lock_types import (
    DistributedLockRecord,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
    parse_utc_timestamp,
)
from backend.storage.locks import (
    DistributedLockManager,
    get_distributed_lock_manager,
)


@pytest.fixture
def lock_mgr() -> DistributedLockManager:
    """Fixture providing a clean in-memory DistributedLockManager instance."""
    mgr = DistributedLockManager(in_memory=True)
    mgr.clear_memory_state()
    return mgr


def test_lock_types_exceptions_and_parsing() -> None:
    """Verifies domain exception hierarchy and timestamp parsing."""
    assert issubclass(LockAcquisitionError, Exception)
    assert issubclass(LockExpiredError, Exception)
    assert issubclass(LockReleaseError, Exception)

    dt_z = parse_utc_timestamp("2026-09-07T12:00:00Z")
    assert dt_z.tzinfo is not None
    dt_offset = parse_utc_timestamp("2026-09-07T12:00:00+00:00")
    assert dt_z == dt_offset

    with pytest.raises(ValueError, match="Invalid timestamp"):
        parse_utc_timestamp("")


def test_distributed_lock_record_expiry() -> None:
    """Verifies DistributedLockRecord model fields and is_expired helper."""
    now = datetime.now(timezone.utc)
    rec = DistributedLockRecord(
        lock_key="res_alpha",
        owner_id="worker_1",
        acquired_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(seconds=10)).isoformat(),
        fence_token=1,
        metadata={"priority": "high"},
    )
    assert rec.metadata == {"priority": "high"}
    assert rec.is_expired(now.isoformat()) is False
    assert rec.is_expired((now + timedelta(seconds=15)).isoformat()) is True


def test_acquire_lock_lifecycle_and_reentrancy(lock_mgr: DistributedLockManager) -> None:
    """Verifies atomic acquisition, conflict rejection, and reentrancy lease extension."""
    rec = lock_mgr.acquire_lock("doc:101", "worker_a", ttl_seconds=30.0)
    assert rec.fence_token == 1
    assert rec.owner_id == "worker_a"

    with pytest.raises(LockAcquisitionError, match="held by 'worker_a'"):
        lock_mgr.acquire_lock("doc:101", "worker_b", ttl_seconds=30.0)

    # Reentrant lease extension by worker_a preserves fence_token
    reentrant = lock_mgr.acquire_lock("doc:101", "worker_a", ttl_seconds=60.0)
    assert reentrant.fence_token == 1
    assert reentrant.expires_at_utc > rec.expires_at_utc


def test_renew_lock_lifecycle(lock_mgr: DistributedLockManager) -> None:
    """Verifies renewal success, unauthorized renewals, and expired renewals."""
    lock_mgr.acquire_lock("job:99", "worker_x", ttl_seconds=10.0)

    # Wrong owner raises LockReleaseError
    with pytest.raises(LockReleaseError, match="held by 'worker_x', not 'worker_y'"):
        lock_mgr.renew_lock("job:99", "worker_y", extension_seconds=30.0)

    # Valid renewal extends lease
    renewed = lock_mgr.renew_lock("job:99", "worker_x", extension_seconds=45.0)
    assert renewed.fence_token == 1

    # Unheld lock raises LockReleaseError
    with pytest.raises(LockReleaseError, match="not held"):
        lock_mgr.renew_lock("job:unknown", "worker_x")


def test_release_and_monotonic_fencing_tokens(lock_mgr: DistributedLockManager) -> None:
    """Verifies release logic and strictly monotonic fence token increments per key."""
    assert lock_mgr.get_fencing_token("task:7") == 0

    lock_mgr.acquire_lock("task:7", "w1", ttl_seconds=60.0)
    assert lock_mgr.get_fencing_token("task:7") == 1

    # Non-owner release returns False
    assert lock_mgr.release_lock("task:7", "w2") is False
    assert lock_mgr.get_lock("task:7") is not None

    # Owner release returns True
    assert lock_mgr.release_lock("task:7", "w1") is True
    assert lock_mgr.get_lock("task:7") is None
    # Fencing token remains 1 after release
    assert lock_mgr.get_fencing_token("task:7") == 1

    # Next acquisition gets strictly monotonic token 2
    rec2 = lock_mgr.acquire_lock("task:7", "w2", ttl_seconds=60.0)
    assert rec2.fence_token == 2
    assert lock_mgr.get_fencing_token("task:7") == 2


def test_lock_expiration_and_renewal_errors(lock_mgr: DistributedLockManager) -> None:
    """Verifies behavior when a lock expires."""
    lock_mgr.acquire_lock("ephemeral:1", "owner_e", ttl_seconds=0.01)
    time.sleep(0.02)

    # Expired lock returns None from get_lock
    assert lock_mgr.get_lock("ephemeral:1") is None

    # Attempting to renew expired lock raises LockExpiredError
    with pytest.raises(LockExpiredError, match="expired"):
        lock_mgr.renew_lock("ephemeral:1", "owner_e")

    # Attempting to release expired lock returns False
    assert lock_mgr.release_lock("ephemeral:1", "owner_e") is False

    # Acquiring after expiration increments fence token
    reacquired = lock_mgr.acquire_lock("ephemeral:1", "owner_new", ttl_seconds=30.0)
    assert reacquired.fence_token == 2


def test_concurrent_lock_contention(lock_mgr: DistributedLockManager) -> None:
    """Verifies atomic test-and-set mutual exclusion under high thread contention."""
    num_threads = 20
    results: list[str] = []
    errors: list[Exception] = []

    def try_acquire(worker_id: str) -> None:
        try:
            lock_mgr.acquire_lock("shared_resource", worker_id, ttl_seconds=30.0)
            results.append(worker_id)
        except LockAcquisitionError as err:
            errors.append(err)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        for idx in range(num_threads):
            executor.submit(try_acquire, f"worker_{idx}")

    assert len(results) == 1
    assert len(errors) == num_threads - 1


def test_firestore_lock_mock_integration() -> None:
    """Verifies Firestore transaction path using a mock Firestore client."""
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_snapshot = MagicMock()
    mock_txn = MagicMock()

    mock_db.collection.return_value.document.return_value = mock_doc
    mock_db.transaction.return_value = mock_txn
    mock_snapshot.exists = False
    mock_doc.get.return_value = mock_snapshot

    mgr = DistributedLockManager(firestore_client=mock_db)
    rec = mgr.acquire_lock("fs_key", "worker_fs", ttl_seconds=30.0)
    assert rec.lock_key == "fs_key"
    assert rec.fence_token == 1
    assert mock_txn.set.called or mock_doc.set.called

    assert get_distributed_lock_manager(in_memory=True) is not None
