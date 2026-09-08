"""
CloudEvent Webhook Ingestion Router for Cloud Storage & Eventarc.
Supports binary and structured CloudEvents v1.0 specifications,
fail-closed path filtering, and real-time ingestion feed notifications.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse

from backend.api.webhooks.cloudevent_parser import (
    EXPECTED_EVENT_TYPE,
    construct_storage_event,
    extract_cloudevent_envelope,
)
from backend.services.ingestion_pipeline import (
    IngestionPipelineService,
    get_ingestion_pipeline_service,
    set_ingestion_pipeline_service,
)
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import (
    IngestionStatus,
    StorageEvent,
)
from backend.storage.lock_types import LockAcquisitionError

logger = logging.getLogger("lienmark.webhooks.storage")
_MAX_FEED_ENTRIES = 100

storage_webhook_router = APIRouter(
    prefix="/api/webhooks/storage",
    tags=["webhooks"],
)

_storage_watcher_service: Optional[StorageWatcherService] = None
_feed_activity_log: deque[Dict[str, Any]] = deque(maxlen=_MAX_FEED_ENTRIES)


def record_feed_activity(record: Dict[str, Any]) -> None:
    """Appends an ingestion event record to the rolling activity log."""
    _feed_activity_log.append(record)


def clear_feed_activity() -> None:
    """Clears the rolling feed activity log (primarily for test fixtures)."""
    _feed_activity_log.clear()


def get_storage_watcher_service() -> StorageWatcherService:
    """Provides or initializes the singleton StorageWatcherService."""
    global _storage_watcher_service
    if _storage_watcher_service is None:
        _storage_watcher_service = StorageWatcherService()
        _storage_watcher_service.register_listener(record_feed_activity)
    return _storage_watcher_service


def set_storage_watcher_service(service: Optional[StorageWatcherService]) -> None:
    """Overrides or resets the StorageWatcherService instance for tests."""
    global _storage_watcher_service
    _storage_watcher_service = service
    if service is not None:
        service.register_listener(record_feed_activity)


def _process_event_outcome(outcome: Dict[str, Any], event: StorageEvent) -> JSONResponse:
    """Translates StorageWatcherService outcome into strict HTTP status codes."""
    status_val = outcome.get("status")
    if status_val == IngestionStatus.QUEUED.value:
        return JSONResponse(status_code=status.HTTP_200_OK, content=outcome)

    if status_val == IngestionStatus.REJECTED_OUT_OF_SCOPE.value:
        reason = outcome.get("rejection_reason") or outcome.get("reason") or "Object out of scope"
        res_data = {
            "status": "rejected_out_of_scope", "reason": reason, "rejection_reason": reason,
            "object_name": event.object_name, "event_id": event.event_id,
        }
        record_feed_activity({
            **res_data, "bucket": event.bucket,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(), "source": event.source,
        })
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=res_data)

    lease_info = outcome.get("lease_details") or {
        "lock_key": outcome.get("lock_key"),
        "reason": outcome.get("reason", "Concurrent ingestion lock is actively held"),
    }
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "status": "conflict",
            "detail": outcome.get("reason", "Concurrent ingestion lock is actively held"),
            "lock_key": outcome.get("lock_key"),
            "event_id": event.event_id,
            "lease_details": lease_info,
        },
    )


def _dispatch_to_pipeline(
    outcome: Dict[str, Any],
    pipeline_service: Optional[IngestionPipelineService],
    background_tasks: Optional[BackgroundTasks],
) -> None:
    """Enqueues run to background task runner or pipeline service."""
    if outcome.get("status") != IngestionStatus.QUEUED.value:
        return
    active_pipe = pipeline_service or get_ingestion_pipeline_service()
    run_id = outcome.get("run_id", "")
    org_id = outcome.get("organization_id", "")
    prod_id = outcome.get("production_id", "")
    if background_tasks is not None:
        background_tasks.add_task(
            active_pipe.enqueue_run,
            run=run_id,
            organization_id=org_id,
            production_id=prod_id,
        )
    else:
        active_pipe.enqueue_run(
            run=run_id,
            organization_id=org_id,
            production_id=prod_id,
        )


async def _parse_request_body(request: Request) -> Dict[str, Any]:
    """Decodes and parses JSON body from request defensively."""
    raw = await request.body()
    if not raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request body cannot be empty.")
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Malformed JSON payload: {exc}") from exc


@storage_webhook_router.post("/eventarc")
async def handle_eventarc_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    pipeline_service: IngestionPipelineService = Depends(get_ingestion_pipeline_service),
) -> JSONResponse:
    """Receives, validates, and processes Cloud Storage object.v1.finalized events."""
    body_json = await _parse_request_body(request)
    event_type, attrs, data_dict = extract_cloudevent_envelope(request, body_json)
    if event_type != EXPECTED_EVENT_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type '{event_type}'. Expected '{EXPECTED_EVENT_TYPE}'.",
        )

    storage_event = construct_storage_event(attrs, data_dict)
    watcher = get_storage_watcher_service()
    try:
        outcome = watcher.process_storage_event(storage_event)
    except LockAcquisitionError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": "conflict", "detail": str(exc)},
        )

    _dispatch_to_pipeline(outcome, pipeline_service, background_tasks)
    return _process_event_outcome(outcome, storage_event)


@storage_webhook_router.get("/feed")
async def get_ingestion_feed(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    stream: bool = Query(default=False),
) -> Any:
    """Returns recent ingestion activity records for SSE streaming or polling."""
    accept_hdr = request.headers.get("accept", "")
    wants_stream = stream or "text/event-stream" in accept_hdr
    if wants_stream:
        async def sse_generator() -> AsyncGenerator[str, None]:
            current_items = list(_feed_activity_log)[-limit:]
            for entry in current_items:
                yield f"data: {json.dumps(entry)}\n\n"
            yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    recent_items = list(_feed_activity_log)[-limit:]
    recent_items.reverse()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "feed": recent_items,
            "events": recent_items,
            "count": len(recent_items),
        },
    )
