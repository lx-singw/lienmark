"""
Storage Watcher Service for event-driven and polled document ingestion.
Enforces multi-tenant folder contracts, distributed idempotency leases,
fencing tokens, and automated InvestigationRun orchestration.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from backend.domain.models import InvestigationRun, RunStatus
from backend.services.storage_watcher_types import (
    FolderScopeResult,
    IngestionStatus,
    LOCKED_DRAFT_REGEX,
    StorageEvent,
    WatcherConfig,
    parse_and_validate_gcs_path,
)
from backend.storage.locks import DistributedLock, DistributedLockManager
from backend.storage.repository import TenantRepository, get_tenant_repository

if TYPE_CHECKING:
    from backend.services.ingestion_pipeline import IngestionPipelineService

logger = logging.getLogger("lienmark.services.storage_watcher")


class StorageWatcherService:
    """Core watcher orchestrator handling real-time storage events and scheduled polling."""

    def __init__(
        self,
        lock_manager: Optional[DistributedLockManager] = None,
        config: Optional[WatcherConfig] = None,
        repository_factory: Optional[Callable[[str], TenantRepository]] = None,
        pipeline_service: Optional[Any] = None,
        storage_client: Optional[Any] = None,
    ) -> None:
        self.lock_manager = lock_manager if lock_manager is not None else DistributedLockManager()
        self.config = config if config is not None else WatcherConfig()
        self._repo_factory = repository_factory or get_tenant_repository
        if pipeline_service is not None:
            self.pipeline_service = pipeline_service
        else:
            try:
                from backend.services.ingestion_pipeline import get_ingestion_pipeline_service
                self.pipeline_service = get_ingestion_pipeline_service()
            except Exception:
                self.pipeline_service = None
        self._storage_client = storage_client
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._seen_etags: Dict[str, str] = {}
        self._seen_generations: Dict[str, str] = {}
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
            active = list(self._listeners)
        for listener in active:
            try:
                listener(payload)
            except Exception as exc:
                logger.error(f"Listener failed for {payload.get('run_id')}: {exc}")

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
        self, event: StorageEvent, scope: FolderScopeResult, lock: DistributedLock, run_id_override: Optional[str] = None
    ) -> InvestigationRun:
        """Instantiates a strictly typed InvestigationRun adhering to tenant boundaries."""
        base_ver, target_ver = self._derive_version_ids(scope.filename or "")
        run_id = run_id_override or f"run_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        return InvestigationRun(
            run_id=run_id, organization_id=scope.organization_id or "", production_id=scope.production_id or "",
            base_version_id=base_ver, target_version_id=target_ver, status=RunStatus.QUEUED,
            created_at=now_iso, updated_at=now_iso, budget_spent_usd=0.0,
            metadata={
                "source": event.source, "bucket": event.bucket, "object_name": event.object_name,
                "etag": event.etag, "size_bytes": event.size_bytes, "fence_token": lock.fence_token,
            },
        )

    def _acquire_event_lease(
        self, event: StorageEvent
    ) -> Tuple[Optional[DistributedLock], Optional[Dict[str, Any]]]:
        """Attempts to acquire distributed lock for storage event idempotency."""
        lock_key = f"ingest:{event.bucket}:{event.object_name}:{event.etag}"
        lock = self.lock_manager.acquire(lock_key, ttl_seconds=self.config.lease_ttl_seconds)
        if lock is None:
            return None, {
                "status": "skipped_concurrent_lease", "lock_key": lock_key,
                "event_id": event.event_id, "reason": "Concurrent lease active or already ingested",
                "lease_details": {"lock_key": lock_key, "ttl_seconds": self.config.lease_ttl_seconds},
            }
        return lock, None

    def _persist_and_publish_run(
        self, event: StorageEvent, scope: FolderScopeResult, lock: DistributedLock, run_id_override: Optional[str]
    ) -> Dict[str, Any]:
        """Persists investigation run in repository and dispatches to listeners."""
        run = self._build_investigation_run(event, scope, lock, run_id_override)
        self._repo_factory(run.organization_id).save_run(run)
        if self.pipeline_service is not None:
            self.pipeline_service.enqueue_run(run)
        self._notify_listeners({
            "status": IngestionStatus.QUEUED.value, "run_id": run.run_id,
            "fence_token": lock.fence_token, "organization_id": run.organization_id,
            "production_id": run.production_id, "object_name": event.object_name,
            "bucket": event.bucket, "timestamp": run.created_at,
        })
        return {
            "status": IngestionStatus.QUEUED.value, "run_id": run.run_id,
            "fence_token": lock.fence_token, "organization_id": run.organization_id,
            "production_id": run.production_id, "base_version_id": run.base_version_id,
            "target_version_id": run.target_version_id,
        }

    def process_storage_event(
        self, event: StorageEvent, run_id_override: Optional[str] = None
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

    def _fetch_gcs_blobs(self, bucket_name: str, prefix: Optional[str]) -> List[Any]:
        """Lists blobs from GCS using google.cloud.storage client if available."""
        client = self._storage_client
        if client is None:
            try:
                from google.cloud import storage
                client = self._storage_client = storage.Client()
            except Exception as exc:
                logger.warning(f"GCS client unavailable: {exc}")
                return []
        try:
            if hasattr(client, "list_blobs"):
                return list(client.list_blobs(bucket_name, prefix=prefix, max_results=self.config.max_batch_size))
            if hasattr(client, "bucket"):
                return list(client.bucket(bucket_name).list_blobs(prefix=prefix, max_results=self.config.max_batch_size))
        except Exception as exc:
            logger.error(f"Failed to list GCS blobs in {bucket_name}: {exc}")
        return []

    def _parse_poll_item(self, item: Any, bucket: str) -> Optional[StorageEvent]:
        """Extracts and normalizes StorageEvent from dict or GCS Blob object."""
        d = item if isinstance(item, dict) else {}
        name = d.get("name") or d.get("object_name") or getattr(item, "name", None)
        etag = d.get("etag") or getattr(item, "etag", None)
        if not name or not etag:
            return None
        size = d.get("size_bytes", d.get("size")) or getattr(item, "size", 0) or 0
        gen = d.get("generation") or getattr(item, "generation", None)
        tc = d.get("time_created_utc", d.get("time_created")) or getattr(item, "time_created", None)
        iso = tc.isoformat() if hasattr(tc, "isoformat") else (str(tc) if tc else datetime.now(timezone.utc).isoformat())
        eid = d.get("event_id") or getattr(item, "id", None) or f"poll_{uuid.uuid4().hex[:12]}"
        return StorageEvent(
            event_id=str(eid), bucket=bucket, object_name=str(name), etag=str(etag),
            size_bytes=int(size), generation=str(gen) if gen is not None else None,
            time_created_utc=iso, content_type=str(d.get("content_type") or getattr(item, "content_type", "application/pdf")),
            source="gcs_poller",
        )

    def _is_unseen_and_mark(self, obj_name: str, etag: str, generation: Optional[str]) -> bool:
        """Checks if generation/etag was already ingested, marking as seen if new."""
        with self._state_lock:
            seen_etag = self._seen_etags.get(obj_name)
            seen_gen = self._seen_generations.get(obj_name)
            if seen_etag == etag and (generation is None or seen_gen == generation):
                return False
            self._seen_etags[obj_name] = etag
            if generation is not None:
                self._seen_generations[obj_name] = generation
            return True

    def poll_bucket_once(
        self,
        bucket_name: str,
        mock_objects: Optional[List[Dict[str, Any]]] = None,
        prefix: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Polls a bucket for new or modified locked PDF files, enforcing batch limits."""
        if mock_objects is not None:
            items: List[Any] = [
                it for it in mock_objects
                if not prefix or (it.get("name") or it.get("object_name", "")).startswith(prefix)
            ]
        else:
            items = self._fetch_gcs_blobs(bucket_name, prefix)

        results: List[Dict[str, Any]] = []
        for raw_item in items:
            if len(results) >= self.config.max_batch_size:
                break
            event = self._parse_poll_item(raw_item, bucket_name)
            if event is None or not LOCKED_DRAFT_REGEX.match(event.object_name.lstrip("/")):
                continue
            if not self._is_unseen_and_mark(event.object_name, event.etag, event.generation):
                continue
            results.append(self.process_storage_event(event))
        return results
