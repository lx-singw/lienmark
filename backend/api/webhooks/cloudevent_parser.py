"""
CloudEvents v1.0 Parser and Normalizer for Google Cloud Storage Eventarc Webhooks.

Decomposes and validates incoming HTTP requests in both Binary Mode (CloudEvent
metadata carried in HTTP headers) and Structured Mode (CloudEvent JSON envelope),
producing strictly typed and validated StorageEvent instances.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import uuid

from fastapi import HTTPException, Request, status

from backend.services.storage_watcher_types import StorageEvent

EXPECTED_EVENT_TYPE = "google.cloud.storage.object.v1.finalized"


def extract_cloudevent_envelope(
    request: Request,
    body: Dict[str, Any],
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Extracts CloudEvent attributes and data dictionary across binary and structured modes.

    In binary mode, attributes are read from 'ce-*' headers.
    In structured mode, attributes are read from the top-level JSON body envelope.
    """
    ce_type_header = request.headers.get("ce-type")

    # Mode 1: Binary CloudEvents mode (headers hold event metadata)
    if ce_type_header:
        event_type = ce_type_header.strip()
        attrs = {
            "event_id": request.headers.get("ce-id") or f"ce_{uuid.uuid4().hex[:12]}",
            "source": request.headers.get("ce-source") or "eventarc",
            "time": request.headers.get("ce-time"),
        }
        # In binary mode, body may be either raw data dict or wrapped in {"data": ...}
        data_dict = body.get("data") if isinstance(body.get("data"), dict) else body
        return event_type, attrs, data_dict

    # Mode 2: Structured CloudEvents mode (JSON envelope holds metadata)
    event_type = str(body.get("type", "")).strip()
    attrs = {
        "event_id": str(body.get("id") or f"ce_{uuid.uuid4().hex[:12]}"),
        "source": str(body.get("source") or "eventarc"),
        "time": body.get("time"),
    }
    raw_data = body.get("data")
    if not isinstance(raw_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed structured CloudEvent: 'data' property must be a JSON object.",
        )
    return event_type, attrs, raw_data


def parse_payload_size(raw_size: Any) -> int:
    """Safely converts payload size to a non-negative integer."""
    try:
        val = int(raw_size)
        return max(0, val)
    except (ValueError, TypeError):
        return 0


def validate_storage_target(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Asserts presence and validity of bucket and object_name in event data.
    """
    bucket = data.get("bucket")
    object_name = data.get("name") or data.get("object_name")

    if not bucket or not isinstance(bucket, str) or not bucket.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed CloudEvent data: 'bucket' is required and must be non-empty.",
        )

    if not object_name or not isinstance(object_name, str) or not object_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed CloudEvent data: 'name' is required and must be non-empty.",
        )

    return bucket.strip(), object_name.strip()


def construct_storage_event(
    attrs: Dict[str, Any],
    data: Dict[str, Any],
) -> StorageEvent:
    """
    Validates required payload fields and constructs an immutable StorageEvent.

    Raises HTTPException 400 if mandatory GCS attributes (bucket, name) are missing.
    """
    bucket, object_name = validate_storage_target(data)

    raw_size = data.get("size", data.get("size_bytes", data.get("sizeBytes", 0)))
    size_bytes = parse_payload_size(raw_size)

    now_iso = datetime.now(timezone.utc).isoformat()
    time_created = str(attrs.get("time") or data.get("timeCreated") or now_iso)
    generation = str(data.get("generation")) if data.get("generation") is not None else None

    return StorageEvent(
        event_id=attrs.get("event_id") or f"evt_{uuid.uuid4().hex[:12]}",
        bucket=bucket,
        object_name=object_name,
        etag=str(data.get("etag") or data.get("eTag") or "missing_etag"),
        size_bytes=size_bytes,
        generation=generation,
        time_created_utc=time_created,
        content_type=str(data.get("contentType", "application/pdf")),
        source=str(attrs.get("source") or "eventarc"),
    )
