"""
Storage Watcher Service for event-driven and polled document ingestion.
Enforces multi-tenant folder contracts, distributed idempotency leases,
fencing tokens, and automated InvestigationRun or DocumentMatcher routing.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple, Union

from backend.domain.models import InvestigationRun, RunStatus
from backend.services.document_matcher_types import DocumentArrivalEvent
from backend.services.storage_watcher_types import (
    FolderScopeResult,
    IngestionStatus,
    LOCKED_DRAFT_REGEX,
    StorageEvent,
    WatcherConfig,
    compute_streaming_sha256,
    derive_version_ids,
    fetch_blob_bytes,
    fetch_gcs_blobs,
    parse_and_validate_gcs_path,
    parse_poll_storage_event,
    validate_bucket_tenant_binding,
    validate_production_authorization,
)
from backend.storage.locks import DistributedLock, DistributedLockManager
from backend.storage.repository import TenantRepository, get_tenant_repository

if TYPE_CHECKING:
    from backend.services.document_matcher import DocumentMatcherService
    from backend.services.ingestion_pipeline import IngestionPipelineService

logger = logging.getLogger("lienmark.services.storage_watcher")


class StorageWatcherService:
    """Core watcher orchestrator handling real-time storage events and scheduled polling."""

    def __init__(
        self,
        lock_manager: Optional[DistributedLockManager] = None,
        config: Optional[WatcherConfig] = None,
        repository_factory: Optional[Callable[[str], TenantRepository]] = None,
        pipeline_service: Optional[IngestionPipelineService] = None,
        storage_client: Optional[object] = None, document_matcher: Optional[DocumentMatcherService] = None,
    ) -> None:
        self.lock_manager = lock_manager or DistributedLockManager()
        self.config = config or WatcherConfig()
        self._repo_factory = repository_factory or get_tenant_repository
        self.pipeline_service = pipeline_service
        self._storage_client = storage_client
        self._document_matcher = document_matcher
        self._listeners: List[Callable[[Dict[str, Union[str, int, float, bool, None]]], None]] = []
        self._seen_etags: Dict[str, str] = {}
        self._seen_generations: Dict[str, str] = {}
        self._state_lock = threading.RLock()

    @property
    def document_matcher(self) -> Optional[DocumentMatcherService]:
        """Lazily initializes DocumentMatcherService if not injected."""
        if self._document_matcher is None:
            try:
                from backend.services.document_matcher import DocumentMatcherService
                self._document_matcher = DocumentMatcherService()
            except Exception:
                pass
        return self._document_matcher

    def register_listener(self, callback: Callable[[Dict[str, Union[str, int, float, bool, None]]], None]) -> None:
        """Registers notification listener for real-time SSE/feed subscribers."""
        with self._state_lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def _notify_listeners(self, payload: Dict[str, Union[str, int, float, bool, None]]) -> None:
        """Dispatches event payload to all registered listeners defensively."""
        with self._state_lock:
            active = list(self._listeners)
        for listener in active:
            try:
                listener(payload)
            except Exception as exc:
                logger.error(f"Listener failed: {exc}")

    _derive_version_ids = staticmethod(derive_version_ids)

    def _build_investigation_run(
        self, event: StorageEvent, scope: FolderScopeResult, lock: DistributedLock, run_id_override: Optional[str] = None
    ) -> InvestigationRun:
        base_ver, target_ver = derive_version_ids(scope.filename or "")
        run_id = run_id_override or f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        return InvestigationRun(
            run_id=run_id, organization_id=scope.organization_id or "", production_id=scope.production_id or "",
            base_version_id=base_ver, target_version_id=target_ver, status=RunStatus.QUEUED,
            created_at=now, updated_at=now, budget_spent_usd=0.0,
            metadata={
                "source": event.source, "bucket": event.bucket, "object_name": event.object_name,
                "etag": event.etag, "size_bytes": event.size_bytes, "fence_token": lock.fence_token,
            },
        )

    def _acquire_event_lease(
        self, lock_key: str, event_id: str
    ) -> Tuple[Optional[DistributedLock], Optional[Dict[str, Union[str, Dict[str, Union[str, float]]]]]]:
        lock = self.lock_manager.acquire(lock_key, ttl_seconds=self.config.lease_ttl_seconds)
        if lock is None:
            return None, {
                "status": "skipped_concurrent_lease", "lock_key": lock_key, "event_id": event_id,
                "reason": "Concurrent lease active or already ingested",
                "lease_details": {"lock_key": lock_key, "ttl_seconds": self.config.lease_ttl_seconds},
            }
        return lock, None

    def _persist_and_publish_run(
        self, event: StorageEvent, scope: FolderScopeResult, lock: DistributedLock, run_id_override: Optional[str]
    ) -> Dict[str, Union[str, int, float, bool, None]]:
        run = self._build_investigation_run(event, scope, lock, run_id_override)
        self._repo_factory(run.organization_id).save_run(run)
        if self.pipeline_service is not None:
            self.pipeline_service.enqueue_run(run)
        self._notify_listeners({
            "status": IngestionStatus.QUEUED.value, "run_id": run.run_id, "fence_token": lock.fence_token,
            "organization_id": run.organization_id, "production_id": run.production_id,
            "object_name": event.object_name, "bucket": event.bucket, "timestamp": run.created_at,
        })
        return {
            "status": IngestionStatus.QUEUED.value, "run_id": run.run_id, "fence_token": lock.fence_token,
            "organization_id": run.organization_id, "production_id": run.production_id,
            "base_version_id": run.base_version_id, "target_version_id": run.target_version_id,
        }

    def _process_agreement_event(
        self, event: StorageEvent, scope: FolderScopeResult, file_content: Optional[Union[bytes, str]] = None
    ) -> Dict[str, Union[str, float, bool, None]]:
        """Routes agreement arrivals to DocumentMatcherService without creating InvestigationRun."""
        raw_bytes = file_content.encode("utf-8") if isinstance(file_content, str) else (
            file_content if file_content is not None else fetch_blob_bytes(self._storage_client, event.bucket, event.object_name)
        )
        raw_hash = compute_streaming_sha256(raw_bytes)
        gen = event.generation or "0"
        lock_key = f"ingest:agreement:{event.bucket}:{event.object_name}:{gen}"
        lock, lease_err = self._acquire_event_lease(lock_key, event.event_id)
        if lock is None:
            return lease_err or {"status": "skipped_concurrent_lease"}

        arrival = DocumentArrivalEvent(
            event_id=event.event_id, file_path=event.object_name, tenant_id=scope.organization_id or "",
            production_id=scope.production_id, gcs_uri=f"gs://{event.bucket}/{event.object_name}",
            file_hash=raw_hash, file_size_bytes=len(raw_bytes), mime_type=event.content_type,
        )
        matcher = self.document_matcher
        match_res = matcher.on_document_arrival(arrival, file_content=raw_bytes) if matcher else None
        doc_id = match_res.document_id if match_res else f"doc_{uuid.uuid4().hex[:10]}"
        decision = match_res.decision.value if match_res else "unmatched"

        self._notify_listeners({
            "status": "agreement_processed", "event_id": event.event_id, "document_id": doc_id,
            "organization_id": scope.organization_id, "production_id": scope.production_id,
            "object_name": event.object_name, "generation": gen, "file_hash": raw_hash,
        })
        return {
            "status": "agreement_processed", "decision": decision, "document_id": doc_id,
            "confidence_score": match_res.confidence_score if match_res else 0.0,
            "organization_id": scope.organization_id, "production_id": scope.production_id,
            "generation": gen, "file_hash": raw_hash, "pipeline_resumed": match_res.pipeline_resumed if match_res else False,
        }

    def process_storage_event(
        self, event: StorageEvent, run_id_override: Optional[str] = None, file_content: Optional[Union[bytes, str]] = None
    ) -> Dict[str, Union[str, int, float, bool, None, Dict[str, Union[str, float]]]]:
        """Validates scope, tenant bucket binding, and routes to screenplay or agreement flow."""
        scope = parse_and_validate_gcs_path(event.object_name)
        if not scope.is_valid_scope:
            return {
                "status": IngestionStatus.REJECTED_OUT_OF_SCOPE.value, "event_id": event.event_id,
                "rejection_reason": scope.rejection_reason, "object_name": event.object_name,
            }

        valid_bkt, b_err = validate_bucket_tenant_binding(event.bucket, scope.organization_id or "", self.config.bucket_tenant_bindings)
        if not valid_bkt:
            return {"status": IngestionStatus.REJECTED_OUT_OF_SCOPE.value, "event_id": event.event_id, "rejection_reason": b_err, "object_name": event.object_name}

        valid_prod, p_err = validate_production_authorization(scope.production_id or "")
        if not valid_prod:
            return {"status": IngestionStatus.REJECTED_OUT_OF_SCOPE.value, "event_id": event.event_id, "rejection_reason": p_err, "object_name": event.object_name}

        if scope.is_agreement:
            return self._process_agreement_event(event, scope, file_content)

        lock_key = f"ingest:{event.bucket}:{event.object_name}:{event.etag}"
        lock, failure_resp = self._acquire_event_lease(lock_key, event.event_id)
        if lock is None:
            return failure_resp or {"status": "skipped_concurrent_lease"}
        return self._persist_and_publish_run(event, scope, lock, run_id_override)

    def _is_unseen_and_mark(self, obj_name: str, etag: str, generation: Optional[str], is_agreement: bool = False) -> bool:
        """Checks if generation/etag was already ingested, marking as seen if new."""
        with self._state_lock:
            if is_agreement and generation is not None:
                if self._seen_generations.get(obj_name) == generation:
                    return False
                self._seen_generations[obj_name] = generation
                return True
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
        mock_objects: Optional[List[Dict[str, Union[str, int, bytes]]]] = None,
        prefix: Optional[str] = None,
    ) -> List[Dict[str, Union[str, int, float, bool, None, Dict[str, Union[str, float]]]]]:
        """Polls a bucket for new or modified locked PDF or agreement files, enforcing batch limits."""
        if mock_objects is not None:
            items: List[object] = [
                it for it in mock_objects
                if not prefix or str(it.get("name") or it.get("object_name") or "").startswith(prefix)
            ]
        else:
            items = fetch_gcs_blobs(self._storage_client, bucket_name, prefix, self.config.max_batch_size)

        results: List[Dict[str, Union[str, int, float, bool, None, Dict[str, Union[str, float]]]]] = []
        for raw_item in items:
            if len(results) >= self.config.max_batch_size:
                break
            event = parse_poll_storage_event(raw_item, bucket_name)
            if event is None or not LOCKED_DRAFT_REGEX.match(event.object_name.lstrip("/")):
                continue
            is_agr = "/agreements/" in event.object_name
            if not self._is_unseen_and_mark(event.object_name, event.etag, event.generation, is_agreement=is_agr):
                continue
            content = raw_item.get("content") if isinstance(raw_item, dict) else None
            results.append(self.process_storage_event(event, file_content=content))
        return results

