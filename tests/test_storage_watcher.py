"""
Storage Watcher & Ingestion Service Test Suite.
Tests StorageWatcherService, parse_and_validate_gcs_path, and Eventarc webhook processing:
- Valid and invalid GCS paths
- Structured and binary CloudEvent processing into InvestigationRun
- Out-of-scope rejection with zero run creation
- Idempotency via distributed lock
- Poller single-execution and skip-seen logic
- Tenant boundary and strict organization_id isolation
Authored strictly under Google AntiGravity architectural guidelines.
"""

from typing import Any, Dict, List
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.domain.models import RunStatus
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import (
    IngestionStatus,
    parse_and_validate_gcs_path,
)
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import (
    InMemoryTenantRepository,
    get_tenant_repository,
)
from backend.api.webhooks.storage import (
    storage_webhook_router,
    set_storage_watcher_service,
    clear_feed_activity,
)


@pytest.fixture
def clean_environment() -> TestClient:
    """Fixture providing an isolated watcher, in-memory repository, and test client."""
    InMemoryTenantRepository.reset_global_storage()
    clear_feed_activity()
    lock_mgr = DistributedLockManager(in_memory=True)
    lock_mgr.clear_memory_state()

    service = StorageWatcherService(
        lock_manager=lock_mgr,
        repository_factory=lambda org_id: get_tenant_repository(org_id, force_in_memory=True),
    )
    set_storage_watcher_service(service)
    app = FastAPI()
    app.include_router(storage_webhook_router)
    return TestClient(app)


def test_parse_and_validate_gcs_path_valid() -> None:
    """Verifies valid path in locked/ extracts organization_id, production_id, filename."""
    path = "organizations/org_paramount/productions/prod_matrix/locked/script_v8.pdf"
    res = parse_and_validate_gcs_path(path)
    assert res.is_valid_scope is True
    assert res.organization_id == "org_paramount"
    assert res.production_id == "prod_matrix"
    assert res.filename == "script_v8.pdf"
    assert res.rejection_reason is None

    # Path with leading slash
    res_slash = parse_and_validate_gcs_path(f"/{path}")
    assert res_slash.is_valid_scope is True
    assert res_slash.organization_id == "org_paramount"


def test_parse_and_validate_gcs_path_invalid_rejected() -> None:
    """Verifies rejection of /sandbox/, /drafts/, /temp/, traversal, and non-pdf files."""
    base = "organizations/org_1/productions/prod_1"

    # Sandboxes
    assert parse_and_validate_gcs_path(f"{base}/sandbox/script.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path(f"{base}/drafts/script.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path(f"{base}/temp/script.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path(f"{base}/scratch/script.pdf").is_valid_scope is False

    # Path traversal and non-PDF extensions
    assert parse_and_validate_gcs_path(f"{base}/locked/../../script.pdf").is_valid_scope is False
    assert parse_and_validate_gcs_path(f"{base}/locked/script.docx").is_valid_scope is False
    assert parse_and_validate_gcs_path(f"{base}/locked/storyboard.png").is_valid_scope is False
    assert parse_and_validate_gcs_path("").is_valid_scope is False


def test_eventarc_structured_cloudevent_queues_run(clean_environment: TestClient) -> None:
    """Verifies structured CloudEvent creates InvestigationRun with RunStatus.QUEUED."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/projects/_/buckets/prod-intake",
        "id": "evt_struct_001",
        "time": "2026-09-07T08:00:00Z",
        "data": {
            "bucket": "prod-intake",
            "name": "organizations/org_warner/productions/prod_batman/locked/screenplay_v8.pdf",
            "etag": "etag_struct_111",
            "size": 4096,
        },
    }
    resp = clean_environment.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["organization_id"] == "org_warner"

    repo = get_tenant_repository("org_warner", force_in_memory=True)
    run = repo.get_run("prod_batman", data["run_id"])
    assert run is not None
    assert run.status == RunStatus.QUEUED
    assert run.organization_id == "org_warner"
    assert run.production_id == "prod_batman"
    assert run.base_version_id == "v7"
    assert run.target_version_id == "v8"


def test_eventarc_binary_mode_cloudevent_processing(clean_environment: TestClient) -> None:
    """Verifies binary mode CloudEvent with ce-* headers processes correctly."""
    headers = {
        "ce-type": "google.cloud.storage.object.v1.finalized",
        "ce-id": "evt_bin_002",
        "ce-source": "//storage.googleapis.com/projects/_/buckets/prod-intake",
        "ce-time": "2026-09-07T08:05:00Z",
    }
    body = {
        "bucket": "prod-intake",
        "name": "organizations/org_warner/productions/prod_batman/locked/revision_v9.pdf",
        "etag": "etag_bin_222",
        "size": 8192,
    }
    resp = clean_environment.post("/api/webhooks/storage/eventarc", json=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["organization_id"] == "org_warner"

    repo = get_tenant_repository("org_warner", force_in_memory=True)
    run = repo.get_run("prod_batman", data["run_id"])
    assert run is not None
    assert run.status == RunStatus.QUEUED
    assert run.target_version_id == "v9"


def test_out_of_scope_event_returns_rejected_zero_runs(clean_environment: TestClient) -> None:
    """Verifies out-of-scope event returns rejected_out_of_scope with zero run creation."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/projects/_/buckets/prod-intake",
        "id": "evt_out_003",
        "data": {
            "bucket": "prod-intake",
            "name": "organizations/org_warner/productions/prod_batman/drafts/script.pdf",
            "etag": "etag_out_333",
            "size": 1024,
        },
    }
    resp = clean_environment.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 202
    assert resp.json()["status"] == "rejected_out_of_scope"

    repo = get_tenant_repository("org_warner", force_in_memory=True)
    runs = repo.list_runs("prod_batman")
    assert len(runs) == 0


def test_idempotency_duplicate_event_blocked_by_lock(clean_environment: TestClient) -> None:
    """Verifies duplicate event delivery with identical ETag is blocked by distributed lock."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/projects/_/buckets/prod-intake",
        "id": "evt_dup_001",
        "data": {
            "bucket": "prod-intake",
            "name": "organizations/org_warner/productions/prod_batman/locked/script_v8.pdf",
            "etag": "etag_same_444",
            "size": 1024,
        },
    }
    resp1 = clean_environment.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "queued"

    # Duplicate delivery with identical ETag encounters active lease lock
    resp2 = clean_environment.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["status"] == "conflict"


def test_poller_processes_new_files_and_skips_seen(clean_environment: TestClient) -> None:
    """Verifies poll_bucket_once processes new files and skips already processed ETags."""
    repo = get_tenant_repository("org_sony", force_in_memory=True)
    lock_mgr = DistributedLockManager(in_memory=True)
    service = StorageWatcherService(
        lock_manager=lock_mgr,
        repository_factory=lambda org_id: repo,
    )

    mock_objects = [
        {
            "name": "organizations/org_sony/productions/prod_spider/locked/script_v8.pdf",
            "etag": "etag_poller_001",
            "size_bytes": 2048,
        },
    ]

    # First poll processes new object
    res1 = service.poll_bucket_once("bucket_vault", mock_objects)
    assert len(res1) == 1
    assert res1[0]["status"] == IngestionStatus.QUEUED.value

    # Second poll skips already processed ETag
    res2 = service.poll_bucket_once("bucket_vault", mock_objects)
    assert len(res2) == 0


def test_tenant_isolation_non_null_organization_id(clean_environment: TestClient) -> None:
    """Verifies that every created run contains strict non-null organization_id."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/projects/_/buckets/prod-intake",
        "id": "evt_iso_005",
        "data": {
            "bucket": "prod-intake",
            "name": "organizations/org_universal/productions/prod_dino/locked/script_v8.pdf",
            "etag": "etag_iso_555",
            "size": 4096,
        },
    }
    resp = clean_environment.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    repo = get_tenant_repository("org_universal", force_in_memory=True)
    run = repo.get_run("prod_dino", run_id)
    assert run is not None
    assert run.organization_id is not None
    assert run.organization_id == "org_universal"
    assert len(run.organization_id) > 0
