"""
Unit tests for StorageWatcherService, DistributedLockManager, and Poller.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from typing import Any, Dict, List, Optional
import pytest

from backend.domain.models import RunStatus
from backend.services.ingestion_pipeline import IngestionPipelineService
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
    assert lock1 is not None and lock1.fence_token == 1
    assert clean_lock_manager.acquire("ingest:bucket:file1:etag1", ttl_seconds=60.0) is None
    lock3 = clean_lock_manager.acquire("ingest:bucket:file2:etag2", ttl_seconds=60.0)
    assert lock3 is not None and lock3.fence_token == 1
    assert clean_lock_manager.release(lock1) is True
    reacquired = clean_lock_manager.acquire("ingest:bucket:file1:etag1", ttl_seconds=60.0)
    assert reacquired is not None and reacquired.fence_token == 2


def test_distributed_lock_expiry(clean_lock_manager: DistributedLockManager) -> None:
    """Verifies lock expiration logic."""
    lock = clean_lock_manager.acquire("temp_key", ttl_seconds=0.01)
    assert lock is not None and lock.is_expired(current_time=lock.expires_at + 1.0) is True


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
    saved = clean_repository.get_run("prod_alpha_01", "run_test_override")
    assert saved is not None and saved.status == RunStatus.QUEUED
    assert saved.base_version_id == "v7" and saved.target_version_id == "v8"


def test_process_storage_event_dispatches_listener(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies live listener receives dispatch on event ingestion."""
    received: List[Dict[str, Any]] = []
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda org_id: clean_repository,
    )
    service.register_listener(lambda data: received.append(data))
    event = StorageEvent(
        event_id="evt_valid_02",
        bucket="scripts_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_alpha_01/locked/script_v8.pdf",
        etag="etag_hash_999",
        size_bytes=1024,
        time_created_utc="2026-09-07T08:30:00Z",
    )
    service.process_storage_event(event, run_id_override="run_listener_test")
    assert len(received) == 1 and received[0]["run_id"] == "run_listener_test"


def test_process_storage_event_rejected_out_of_scope(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies rejection of events outside locked production directory."""
    service = StorageWatcherService(lock_manager=clean_lock_manager, repository_factory=lambda o: clean_repository)
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
    service = StorageWatcherService(lock_manager=clean_lock_manager, repository_factory=lambda o: clean_repository)
    event = StorageEvent(
        event_id="evt_dup_01",
        bucket="scripts_bucket",
        object_name="organizations/org_studio_alpha/productions/prod_01/locked/script_v8.pdf",
        etag="etag_fixed",
        size_bytes=1000,
        time_created_utc="2026-09-07T08:30:00Z",
    )
    res1 = service.process_storage_event(event)
    assert res1["status"] == IngestionStatus.QUEUED.value
    res2 = service.process_storage_event(event)
    assert res2["status"] == "skipped_concurrent_lease"
    assert "lease_details" in res2


def test_poll_bucket_once_deduplication_and_batch_limits(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies poll_bucket_once filters unseen ETags and honors max_batch_size."""
    service = StorageWatcherService(
        lock_manager=clean_lock_manager,
        config=WatcherConfig(max_batch_size=2),
        repository_factory=lambda o: clean_repository,
    )
    objs = [
        {"name": f"organizations/org_studio_alpha/productions/prod_01/locked/script_{i}.pdf", "etag": f"e_{i}"}
        for i in range(1, 4)
    ]
    res1 = service.poll_bucket_once("test_bucket", objs)
    assert len(res1) == 2 and all(r["status"] == IngestionStatus.QUEUED.value for r in res1)
    res2 = service.poll_bucket_once("test_bucket", objs)
    assert len(res2) == 1 and res2[0]["status"] == IngestionStatus.QUEUED.value


def test_poll_bucket_once_gcs_client_paginated(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies real paginated GCS blob listing via storage_client with max_results and prefix."""
    listed: Dict[str, Any] = {}

    class MockBlob:
        def __init__(self, name: str, etag: str, gen: str = "1"):
            self.name = name
            self.etag = etag
            self.size = 1024
            self.generation = gen
            self.time_created = "2026-09-08T08:00:00Z"
            self.content_type = "application/pdf"
            self.id = f"{name}#{gen}"

    class MockGcsClient:
        def list_blobs(self, bucket: str, prefix: Optional[str] = None, max_results: Optional[int] = None):
            listed["bucket"], listed["prefix"], listed["max_results"] = bucket, prefix, max_results
            return [
                MockBlob("organizations/org_studio_alpha/productions/prod_gcs/locked/script_v8.pdf", "etag_1", "101"),
                MockBlob("organizations/org_studio_alpha/productions/prod_gcs/drafts/draft.pdf", "etag_2", "102"),
            ]

    pipe = IngestionPipelineService()
    svc = StorageWatcherService(
        lock_manager=clean_lock_manager,
        repository_factory=lambda o: clean_repository,
        pipeline_service=pipe,
        storage_client=MockGcsClient(),
    )
    res = svc.poll_bucket_once("bucket_alpha", prefix="organizations/org_studio_alpha/")
    assert len(res) == 1 and res[0]["status"] == IngestionStatus.QUEUED.value
    assert listed["bucket"] == "bucket_alpha" and listed["prefix"] == "organizations/org_studio_alpha/"
    assert listed["max_results"] == svc.config.max_batch_size
    assert len(pipe.get_queued_runs()) == 1


def test_poll_bucket_once_generation_tracking(
    clean_lock_manager: DistributedLockManager,
    clean_repository: InMemoryTenantRepository,
) -> None:
    """Verifies generation/etag tracking allows new generations while skipping identical."""
    service = StorageWatcherService(lock_manager=clean_lock_manager, repository_factory=lambda o: clean_repository)
    name = "organizations/org_studio_alpha/productions/prod_01/locked/script_v8.pdf"
    r1 = service.poll_bucket_once("bkt", [{"name": name, "etag": "etag_same", "generation": "1"}])
    assert len(r1) == 1
    r2 = service.poll_bucket_once("bkt", [{"name": name, "etag": "etag_same", "generation": "1"}])
    assert len(r2) == 0
    clean_lock_manager.reset()
    r3 = service.poll_bucket_once("bkt", [{"name": name, "etag": "etag_same", "generation": "2"}])
    assert len(r3) == 1


def test_derive_version_ids() -> None:
    """Verifies derivation of base and target version IDs from various filenames."""
    assert StorageWatcherService._derive_version_ids("script_v8.pdf") == ("v7", "v8")
    assert StorageWatcherService._derive_version_ids("locked_v10.pdf") == ("v9", "v10")
    assert StorageWatcherService._derive_version_ids("scene42.pdf") == ("v7", "v8")
    assert StorageWatcherService._derive_version_ids("") == ("v7", "v8")
