"""
Unit and integration tests for CloudEvent Webhook Ingestion Router.
Tests structured mode, binary mode, error handling, feed streaming,
and integration with backend.main FastAPI application.
"""

from typing import Any, Dict
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.webhooks.storage import (
    clear_feed_activity,
    set_storage_watcher_service,
    storage_webhook_router,
)
from backend.main import app as main_app
from backend.services.ingestion_pipeline import (
    get_ingestion_pipeline_service,
    reset_ingestion_pipeline_service,
)
from backend.services.storage_watcher import StorageWatcherService
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import (
    InMemoryTenantRepository,
    get_tenant_repository,
)


@pytest.fixture
def webhook_client() -> TestClient:
    """Fixture providing an isolated router client with clean in-memory state."""
    InMemoryTenantRepository.reset_global_storage()
    clear_feed_activity()
    reset_ingestion_pipeline_service()
    lock_mgr = DistributedLockManager(in_memory=True)
    lock_mgr.clear_memory_state()

    service = StorageWatcherService(
        lock_manager=lock_mgr,
        repository_factory=lambda org_id: get_tenant_repository(org_id, force_in_memory=True),
    )
    set_storage_watcher_service(service)

    test_app = FastAPI()
    test_app.include_router(storage_webhook_router)
    return TestClient(test_app)


def test_eventarc_empty_body_rejected(webhook_client: TestClient) -> None:
    """Asserts that an empty request body returns 400 Bad Request."""
    resp = webhook_client.post(
        "/api/webhooks/storage/eventarc",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert "Request body cannot be empty" in resp.json()["detail"]


def test_eventarc_invalid_json_rejected(webhook_client: TestClient) -> None:
    """Asserts that malformed JSON returns 400 Bad Request."""
    resp = webhook_client.post(
        "/api/webhooks/storage/eventarc",
        content=b"not-valid-json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert "Malformed JSON" in resp.json()["detail"]


def test_eventarc_unsupported_event_type_rejected(webhook_client: TestClient) -> None:
    """Asserts that unhandled event types return 400 Bad Request."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.deleted",
        "source": "//storage.googleapis.com/buckets/test",
        "id": "evt_del_01",
        "data": {"bucket": "test", "name": "locked/script.pdf"},
    }
    resp = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 400
    assert "Invalid event type" in resp.json()["detail"]


def test_eventarc_missing_bucket_rejected(webhook_client: TestClient) -> None:
    """Asserts that missing bucket in data returns 400 Bad Request."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/test",
        "id": "evt_no_bkt",
        "data": {"name": "organizations/org1/productions/p1/locked/script.pdf"},
    }
    resp = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 400
    assert "'bucket' is required" in resp.json()["detail"]


def test_eventarc_missing_name_rejected(webhook_client: TestClient) -> None:
    """Asserts that missing object name in data returns 400 Bad Request."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/test",
        "id": "evt_no_name",
        "data": {"bucket": "my-bucket"},
    }
    resp = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 400
    assert "'name' is required" in resp.json()["detail"]


def test_feed_polling_returns_recent_activities(webhook_client: TestClient) -> None:
    """Asserts that GET /feed returns recorded events in reverse chronological order."""
    # 1. Send out-of-scope event (which records to feed)
    out_payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/test",
        "id": "evt_out_feed",
        "data": {
            "bucket": "test-bucket",
            "name": "organizations/org_a/productions/p_a/sandbox/draft.pdf",
            "etag": "etag_out_feed",
        },
    }
    resp_out = webhook_client.post("/api/webhooks/storage/eventarc", json=out_payload)
    assert resp_out.status_code == 202

    # 2. Query feed endpoint
    resp_feed = webhook_client.get("/api/webhooks/storage/feed")
    assert resp_feed.status_code == 200
    feed_data = resp_feed.json()
    assert feed_data["status"] == "ok"
    assert feed_data["count"] >= 1
    assert feed_data["feed"][0]["status"] == "rejected_out_of_scope"


def test_feed_sse_stream_mode(webhook_client: TestClient) -> None:
    """Asserts that GET /feed with stream=True or text/event-stream returns SSE."""
    resp = webhook_client.get(
        "/api/webhooks/storage/feed?stream=true",
        headers={"Accept": "text/event-stream"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert b": keepalive" in resp.content


def test_main_app_mounts_storage_webhook_router() -> None:
    """Asserts that storage_webhook_router is mounted directly in main backend app."""
    paths = []
    for route in main_app.routes:
        if hasattr(route, "path"):
            paths.append(route.path)
        elif hasattr(route, "original_router"):
            for sub_route in route.original_router.routes:
                if hasattr(sub_route, "path"):
                    paths.append(sub_route.path)
    assert "/api/webhooks/storage/eventarc" in paths
    assert "/api/webhooks/storage/feed" in paths

    client = TestClient(main_app)
    resp = client.get("/api/webhooks/storage/feed")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_eventarc_webhook_enqueues_task_and_returns_run_details(webhook_client: TestClient) -> None:
    """Verifies valid CloudEvent enqueues run to IngestionPipelineService and returns details."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/pipeline-bkt",
        "id": "evt_pipe_01",
        "data": {
            "bucket": "pipeline-bkt",
            "name": "organizations/org_webhook/productions/prod_hook/locked/script_v8.pdf",
            "etag": "etag_pipe_111",
            "size": 4096,
        },
    }
    resp = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["run_id"].startswith("run_")
    assert data["organization_id"] == "org_webhook"
    assert data["production_id"] == "prod_hook"

    pipe = get_ingestion_pipeline_service()
    queued = pipe.get_queued_runs()
    assert len(queued) >= 1
    assert any(q["run_id"] == data["run_id"] for q in queued)


def test_eventarc_webhook_conflict_returns_lease_details(webhook_client: TestClient) -> None:
    """Verifies that concurrent lease returns HTTP 409 with lease details."""
    payload = {
        "specversion": "1.0",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/pipeline-bkt",
        "id": "evt_conflict_01",
        "data": {
            "bucket": "pipeline-bkt",
            "name": "organizations/org_webhook/productions/prod_hook/locked/script_v8.pdf",
            "etag": "etag_conflict_222",
            "size": 2048,
        },
    }
    r1 = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert r1.status_code == 200

    r2 = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert r2.status_code == 409
    data = r2.json()
    assert data["status"] == "conflict"
    assert "lease_details" in data
    assert "lock_key" in data["lease_details"]

