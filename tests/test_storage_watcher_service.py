"""
Unit tests for StorageWatcherService and DistributedLockManager.
"""

from typing import Any, Dict, List
import pytest

from backend.domain.models import RunStatus
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import (
    IngestionStatus,
    StorageEvent,
    WatcherConfig,
)
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository


@pytest.fixture
def clean_lock_manager() -> DistributedLockManager:
    """Fixture providing an isolated distributed lock manager."""
    mgr = DistributedLockManager()
    mgr.reset()
    return mgr


@pytest.fixture
def clean_repository() -> InMemoryTenantRepository:
    """Fixture providing a fresh in-memory repository."""
    InMemoryTenantRepository.reset_global_storage()
    return InMemoryTenantRepository("org_studio_alpha")


def test_distributed_lock_lifecycle(clean_lock_manager: DistributedLockManager) -> None:
    """Verifies lock acquisition, fence token monotonicity, and release."""
    lock1 = clean_lock_manager.acquire("ingest:bucket:file1:etag1", ttl_seconds=60.0)
    assert lock1 is not None
    assert lock1.fence_token == 1

    # Concurrent attempt fails
    lock2 = clean_lock_manager.acquire("ingest:bucket:file1:etag1", ttl_seconds=60.0)
    assert lock2 is None

    # Distinct resource has its own initial fence token
    lock3 = clean_lock_manager.acquire("ingest:bucket:file2:etag2", ttl_seconds=60.0)
    assert lock3 is not None
    assert lock3.fence_token == 1

    # Release allows re-acquisition with incremented fence token for this resource
    assert clean_lock_manager.release(lock1) is True
    reacquired = clean_lock_manager.acquire("ingest:bucket:file1:etag1", ttl_seconds=60.0)
    assert reacquired is not None
    assert reacquired.fence_token == 2


def test_distributed_lock_expiry(clean_lock_manager: DistributedLockManager) -> None:
    """Verifies lock expiration logic."""
    lock = clean_lock_manager.acquire("temp_key", ttl_seconds=0.01)
    assert lock is not None
    assert lock.is_expired(current_time=lock.expires_at + 1.0) is True


def test_process_storage_event_success(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies full successful ingestion pipeline and persistence for valid event."""
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda org_id: clean_repository,
    )
    event = StorageEvent(
        event_id="evt_valid_01",
        bucket="scripts_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_alpha_01/locked/script_v8.pdf",
        etag="etag_hash_12345",
        size_bytes=2048,
        time_created_utc="2026-09-07T08:30:00Z",
        source="eventarc",
    )
    result = service.process_storage_event(event, run_id_override="run_test_override")
    assert result["status"] == IngestionStatus.QUEUED.value
    assert result["run_id"] == "run_test_override"
    assert result["fence_token"] == 1
    assert result["organization_id"] == "org_studio_alpha"

    saved_run = clean_repository.get_run("prod_alpha_01", "run_test_override")
    assert saved_run is not None
    assert saved_run.status == RunStatus.QUEUED
    assert saved_run.base_version_id == "v7"
    assert saved_run.target_version_id == "v8"
    assert saved_run.metadata["fence_token"] == 1
    assert saved_run.metadata["etag"] == "etag_hash_12345"


def test_process_storage_event_dispatches_listener(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies live listener receives dispatch on event ingestion."""
    received_events: List[Dict[str, Any]] = []
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda org_id: clean_repository,
    )
    service.register_listener(lambda data: received_events.append(data))

    event = StorageEvent(
        event_id="evt_valid_02",
        bucket="scripts_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_alpha_01/locked/script_v8.pdf",
        etag="etag_hash_999",
        size_bytes=1024,
        time_created_utc="2026-09-07T08:30:00Z",
    )
    service.process_storage_event(event, run_id_override="run_listener_test")
    assert len(received_events) == 1
    assert received_events[0]["run_id"] == "run_listener_test"


def test_process_storage_event_rejected_out_of_scope(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies rejection of events outside locked production directory."""
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda org_id: clean_repository,
    )

    event = StorageEvent(
        event_id="evt_invalid_01",
        bucket="scripts_bucket",
        object_name="organizations/org_alpha/productions/prod_01/drafts/draft.docx",
        etag="etag_draft",
        size_bytes=100,
        time_created_utc="2026-09-07T08:30:00Z",
    )

    result = service.process_storage_event(event)
    assert result["status"] == IngestionStatus.REJECTED_OUT_OF_SCOPE.value
    assert "sandbox" in result["rejection_reason"].lower()


def test_process_storage_event_concurrent_lease_skip(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies that duplicate or concurrent events are skipped cleanly."""
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda org_id: clean_repository,
    )

    event = StorageEvent(
        event_id="evt_dup_01",
        bucket="scripts_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_01/locked/script_v8.pdf",
        etag="etag_fixed",
        size_bytes=1000,
        time_created_utc="2026-09-07T08:30:00Z",
    )

    # First attempt acquires lease
    res1 = service.process_storage_event(event)
    assert res1["status"] == IngestionStatus.QUEUED.value

    # Second attempt encounters active lease
    res2 = service.process_storage_event(event)
    assert res2["status"] == "skipped_concurrent_lease"
    assert "Concurrent lease active" in res2["reason"]


def test_poll_bucket_once_deduplication_and_batch_limits(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies poll_bucket_once filters unseen ETags and honors max_batch_size."""
    cfg = WatcherConfig(max_batch_size=2)
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        config=cfg,
        repository_factory=lambda org_id: clean_repository,
    )

    mock_objects = [
        {
            "name": "organizations/org_studio_alpha/productions/prod_01/locked/script_1.pdf",
            "etag": "etag_1",
            "size_bytes": 100,
        },
        {
            "name": "organizations/org_studio_alpha/productions/prod_01/locked/script_2.pdf",
            "etag": "etag_2",
            "size_bytes": 200,
        },
        {
            "name": "organizations/org_studio_alpha/productions/prod_01/locked/script_3.pdf",
            "etag": "etag_3",
            "size_bytes": 300,
        },
    ]

    # First poll processes capped batch of 2
    res_poll_1 = service.poll_bucket_once("test_bucket", mock_objects)
    assert len(res_poll_1) == 2
    assert all(r["status"] == IngestionStatus.QUEUED.value for r in res_poll_1)

    # Second poll with identical objects skips already seen ETags
    res_poll_2 = service.poll_bucket_once("test_bucket", mock_objects)
    # Only the third object was unread in poll 1; objects 1 & 2 have same ETag
    assert len(res_poll_2) == 1
    assert res_poll_2[0]["status"] == IngestionStatus.QUEUED.value


def test_derive_version_ids() -> None:
    """Verifies derivation of base and target version IDs from various filenames."""
    assert StorageWatcherService._derive_version_ids("script_v8.pdf") == ("v7", "v8")
    assert StorageWatcherService._derive_version_ids("locked_v10.pdf") == ("v9", "v10")
    assert StorageWatcherService._derive_version_ids("scene42.pdf") == ("v7", "v8")
    assert StorageWatcherService._derive_version_ids("") == ("v7", "v8")
