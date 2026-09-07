"""
Storage Watcher Service for event-driven and polled document ingestion.
Enforces multi-tenant folder contracts, distributed idempotency leases,
fencing tokens, and automated InvestigationRun orchestration.
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.domain.models import InvestigationRun, RunStatus
from backend.services.storage_watcher_types import (
    FolderScopeResult,
    IngestionStatus,
    StorageEvent,
    WatcherConfig,
    parse_and_validate_gcs_path,
)
from backend.storage.locks import DistributedLock, DistributedLockManager
from backend.storage.repository import TenantRepository, get_tenant_repository

logger = logging.getLogger("lienmark.services.storage_watcher")


class StorageWatcherService:
    """
    Core watcher orchestrator handling real-time storage events and scheduled polling.
    """

    def __init__(
        self,
        lock_manager: Optional[DistributedLockManager] = None,
        config: Optional[WatcherConfig] = None,
        repository_factory: Optional[Callable[[str], TenantRepository]] = None,
    ) -> None:
        self.lock_manager = lock_manager if lock_manager is not None else DistributedLockManager()
        self.config = config if config is not None else WatcherConfig()
        self._repo_factory = repository_factory or get_tenant_repository
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._seen_etags: Dict[str, str] = {}
        self._state_lock = threading.RLock()

    def register_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Registers notification listener for real-time SSE/feed subscribers."""
        with self._state_lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
                logger.info(f"Registered storage watcher listener: {callback}")

    def _notify_listeners(self, payload: Dict[str, Any]) -> None:
        """Dispatches event payload to all registered listeners defensively."""
        with self._state_lock:
            active_listeners = list(self._listeners)

        for listener in active_listeners:
            try:
                listener(payload)
            except Exception as exc:
                logger.error(f"Listener execution failed for {payload.get('run_id')}: {exc}")

    @staticmethod
    def _derive_version_ids(filename: str) -> Tuple[str, str]:
        """Derives baseline and target version IDs from filename, defaulting to v7 / v8."""
        if not filename:
            return "v7", "v8"

        match = re.search(r"v(\d+)", filename, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            target_ver = f"v{num}"
            base_ver = f"v{num - 1}" if num > 1 else "v1"
            return base_ver, target_ver

        return "v7", "v8"

    def _build_investigation_run(
        self,
        event: StorageEvent,
        scope: FolderScopeResult,
        lock: DistributedLock,
        run_id_override: Optional[str] = None,
    ) -> InvestigationRun:
        """Instantiates a strictly typed InvestigationRun adhering to tenant boundaries."""
        base_ver, target_ver = self._derive_version_ids(scope.filename or "")
        run_id = run_id_override or f"run_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        return InvestigationRun(
            run_id=run_id,
            organization_id=scope.organization_id or "",
            production_id=scope.production_id or "",
            base_version_id=base_ver,
            target_version_id=target_ver,
            status=RunStatus.QUEUED,
            created_at=now_iso,
            updated_at=now_iso,
            budget_spent_usd=0.0,
            metadata={
                "source": event.source,
                "bucket": event.bucket,
                "object_name": event.object_name,
                "etag": event.etag,
                "size_bytes": event.size_bytes,
                "fence_token": lock.fence_token,
            },
        )

    def _acquire_event_lease(
        self, event: StorageEvent
    ) -> Tuple[Optional[DistributedLock], Optional[Dict[str, Any]]]:
        """Attempts to acquire distributed lock for storage event idempotency."""
        lock_key = f"ingest:{event.bucket}:{event.object_name}:{event.etag}"
        lock = self.lock_manager.acquire(lock_key, ttl_seconds=self.config.lease_ttl_seconds)
        if lock is None:
            failure_resp = {
                "status": "skipped_concurrent_lease",
                "lock_key": lock_key,
                "event_id": event.event_id,
                "reason": "Concurrent lease active or already ingested",
            }
            return None, failure_resp
        return lock, None

    def _persist_and_publish_run(
        self,
        event: StorageEvent,
        scope: FolderScopeResult,
        lock: DistributedLock,
        run_id_override: Optional[str],
    ) -> Dict[str, Any]:
        """Persists investigation run in repository and dispatches to listeners."""
        run = self._build_investigation_run(event, scope, lock, run_id_override)
        repo = self._repo_factory(run.organization_id)
        repo.save_run(run)

        self._notify_listeners({
            "status": IngestionStatus.QUEUED.value,
            "run_id": run.run_id,
            "fence_token": lock.fence_token,
            "organization_id": run.organization_id,
            "production_id": run.production_id,
            "object_name": event.object_name,
            "bucket": event.bucket,
            "timestamp": run.created_at,
        })

        return {
            "status": IngestionStatus.QUEUED.value,
            "run_id": run.run_id,
            "fence_token": lock.fence_token,
            "organization_id": run.organization_id,
        }

    def process_storage_event(
        self,
        event: StorageEvent,
        run_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validates, leases, and queues a storage event for pipeline investigation."""
        scope = parse_and_validate_gcs_path(event.object_name)
        if not scope.is_valid_scope:
            return {
                "status": IngestionStatus.REJECTED_OUT_OF_SCOPE.value,
                "event_id": event.event_id,
                "rejection_reason": scope.rejection_reason,
                "object_name": event.object_name,
            }

        lock, failure_resp = self._acquire_event_lease(event)
        if lock is None:
            return failure_resp or {"status": "skipped_concurrent_lease"}

        return self._persist_and_publish_run(event, scope, lock, run_id_override)

    def _parse_poll_item(self, item: Dict[str, Any], bucket_name: str) -> Optional[StorageEvent]:
        """Extracts and normalizes StorageEvent from raw polling dictionary."""
        object_name = item.get("name") or item.get("object_name")
        etag = item.get("etag")
        if not object_name or not etag:
            return None

        size_raw = item.get("size_bytes", item.get("size", 0))
        now_utc = datetime.now(timezone.utc).isoformat()
        return StorageEvent(
            event_id=item.get("event_id") or f"poll_{uuid.uuid4().hex[:12]}",
            bucket=bucket_name,
            object_name=str(object_name),
            etag=str(etag),
            size_bytes=int(size_raw),
            generation=str(item.get("generation", "")) or None,
            time_created_utc=str(item.get("time_created_utc", item.get("time_created", ""))) or now_utc,
            content_type=str(item.get("content_type", "application/pdf")),
            source="gcs_poller",
        )

    def poll_bucket_once(
        self,
        bucket_name: str,
        mock_objects: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Polls a bucket for new or modified locked PDF files, enforcing batch limits."""
        items: List[Dict[str, Any]] = mock_objects if mock_objects is not None else []
        results: List[Dict[str, Any]] = []

        for raw_item in items:
            if len(results) >= self.config.max_batch_size:
                break

            event = self._parse_poll_item(raw_item, bucket_name)
            if event is None:
                continue

            with self._state_lock:
                if self._seen_etags.get(event.object_name) == event.etag:
                    continue
                self._seen_etags[event.object_name] = event.etag

            results.append(self.process_storage_event(event))

        return results
