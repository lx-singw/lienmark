"""
Edge case and defensive behavior tests for StorageWatcherService and locks.
"""

from typing import Any, Dict
import pytest

from backend.domain.models import RunStatus
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import IngestionStatus, StorageEvent
from backend.storage.locks import DistributedLock, DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository


def test_lock_manager_empty_key_rejection() -> None:
    """Verifies that acquire rejects empty or whitespace-only keys."""
    mgr = DistributedLockManager()
    with pytest.raises(ValueError):
        mgr.acquire("")
    with pytest.raises(ValueError):
        mgr.acquire("   ")


def test_lock_manager_stale_release_and_query() -> None:
    """Verifies lock manager state queries and rejection of stale releases."""
    mgr = DistributedLockManager()
    mgr.reset()

    assert mgr.is_locked("sample_key") is False
    assert mgr.get_lock("sample_key") is None

    lock = mgr.acquire("sample_key", ttl_seconds=30.0)
    assert lock is not None
    assert mgr.is_locked("sample_key") is True
    assert mgr.get_lock("sample_key") is not None

    # Stale release with wrong fence token
    stale_lock = DistributedLock(
        lock_key="sample_key",
        fence_token=9999,
        owner_id="imposter",
        acquired_at=lock.acquired_at,
        expires_at=lock.expires_at,
    )
    assert mgr.release(stale_lock) is False
    assert mgr.is_locked("sample_key") is True

    # Non-existent lock release
    untracked = DistributedLock(
        lock_key="ghost_key",
        fence_token=1,
        owner_id="ghost",
        acquired_at=1.0,
        expires_at=2.0,
    )
    assert mgr.release(untracked) is False


def test_storage_watcher_listener_exception_resilience() -> None:
    """Verifies that an exception in a listener does not crash event processing."""
    mgr = DistributedLockManager()
    repo = InMemoryTenantRepository("org_studio_alpha")
    service = StorageWatcherService(lock_manager=mgr, repository_factory=lambda org: repo)

    def crashing_listener(payload: Dict[str, Any]) -> None:
        raise RuntimeError("Simulated listener explosion")

    dispatched = False

    def healthy_listener(payload: Dict[str, Any]) -> None:
        nonlocal dispatched
        dispatched = True

    service.register_listener(crashing_listener)
    service.register_listener(healthy_listener)

    event = StorageEvent(
        event_id="evt_resilient",
        bucket="test_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_01/locked/script_v8.pdf",
        etag="etag_resilient",
        size_bytes=100,
        time_created_utc="2026-09-07T08:00:00Z",
    )

    result = service.process_storage_event(event)
    assert result["status"] == IngestionStatus.QUEUED.value
    assert dispatched is True


def test_poll_bucket_once_skips_malformed_items() -> None:
    """Verifies poll_bucket_once gracefully skips items missing name or etag."""
    mgr = DistributedLockManager()
    repo = InMemoryTenantRepository("org_studio_alpha")
    service = StorageWatcherService(lock_manager=mgr, repository_factory=lambda org: repo)

    malformed = [
        {"size_bytes": 100},  # missing name and etag
        {"name": "organizations/org_studio_alpha/productions/prod_01/locked/file.pdf"},  # missing etag
        {"etag": "etag_only"},  # missing name
    ]

    results = service.poll_bucket_once("test_bucket", mock_objects=malformed)
    assert results == []


def test_process_storage_event_default_run_id_generation() -> None:
    """Verifies that omitting run_id_override generates a valid uuid-based run_id."""
    mgr = DistributedLockManager()
    repo = InMemoryTenantRepository("org_studio_alpha")
    service = StorageWatcherService(lock_manager=mgr, repository_factory=lambda org: repo)

    event = StorageEvent(
        event_id="evt_auto_id",
        bucket="test_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_01/locked/script_v8.pdf",
        etag="etag_auto",
        size_bytes=500,
        time_created_utc="2026-09-07T08:00:00Z",
    )

    result = service.process_storage_event(event)
    assert result["status"] == IngestionStatus.QUEUED.value
    assert result["run_id"].startswith("run_")
