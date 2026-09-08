"""
backend/services/ingestion_pipeline.py

Autonomous background pipeline runner for Lienmark Clearance Ingestion.
Acquires fencing worker and content leases, detects deduplication cache hits,
orchestrates multi-format parsing, claims extraction with self-reflection,
confidentiality sanitization, baseline snapshots, and budget settlement.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from backend.agents.intake.agent import IntakeAgent
from backend.agents.intake.confidentiality import ConfidentialityFilter
from backend.core.lifecycle import CACHE_HIT_REASON, transition_run
from backend.domain.models import InvestigationRun, RunStatus
from backend.orchestration.adk_pipeline import EvidenceDrivenCoordinator
from backend.orchestration.budget_governor import ExecutionBudgetGovernor
from backend.services.hasher import StreamingHasher
from backend.services.ingestion_pipeline_steps import (
    check_baseline_approval, coordinate_drifted_claims, extract_raw_text,
    retrieve_document_bytes, sanitize_extracted_claims, save_baseline_snapshot,
)
from backend.storage.baseline_store import BaselineStoreInterface, get_default_baseline_store
from backend.storage.document_store import DocumentStore
from backend.storage.document_store_parser import parse_document_with_factory
from backend.storage.document_store_types import DocumentProcessingStatus, IngestedDocumentRecord
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import TenantRepository, get_tenant_repository

logger = logging.getLogger("lienmark.services.ingestion_pipeline")
_pipeline_instance: Optional[IngestionPipelineService] = None


class IngestionPipelineService:
    """Autonomous background pipeline runner for screenplay document clearance."""

    def __init__(
        self, run_id: Optional[str] = None, organization_id: Optional[str] = None,
        production_id: Optional[str] = None, bucket: Optional[str] = None,
        object_name: Optional[str] = None, etag: Optional[str] = None,
        generation: Optional[str] = None, lock_manager: Optional[DistributedLockManager] = None,
        document_store: Optional[DocumentStore] = None,
        baseline_store: Optional[BaselineStoreInterface] = None,
        budget_governor: Optional[ExecutionBudgetGovernor] = None,
        storage_client: Optional[Any] = None, intake_agent: Optional[IntakeAgent] = None,
        confidentiality_filter: Optional[ConfidentialityFilter] = None,
        coordinator: Optional[EvidenceDrivenCoordinator] = None,
        repository_factory: Optional[Callable[[str], TenantRepository]] = None,
    ) -> None:
        self.run_id, self.organization_id = run_id, organization_id
        self.production_id, self.bucket = production_id, bucket
        self.object_name, self.etag, self.generation = object_name, etag, generation
        self.lock_manager = lock_manager or DistributedLockManager()
        self.document_store = document_store or DocumentStore()
        self.baseline_store = baseline_store or get_default_baseline_store(force_in_memory=True)
        self.budget_governor = budget_governor or ExecutionBudgetGovernor()
        self.storage_client, self.intake_agent = storage_client, intake_agent or IntakeAgent(use_fallback=True)
        self.confidentiality_filter = confidentiality_filter or ConfidentialityFilter()
        self.coordinator = coordinator or EvidenceDrivenCoordinator(use_fallback=True)
        self._repo_factory = repository_factory or (lambda org: get_tenant_repository(org, force_in_memory=True))
        self._queue, self._lock = [], threading.RLock()

    async def __call__(self, *args: Any, **kwargs: Any) -> InvestigationRun:
        return await self.process_run(*args, **kwargs)

    def run(self, *args: Any, **kwargs: Any) -> InvestigationRun:
        """Synchronous wrapper for executing pipeline runner."""
        try:
            return asyncio.get_running_loop().run_until_complete(self.process_run(*args, **kwargs))
        except RuntimeError:
            return asyncio.run(self.process_run(*args, **kwargs))

    def _resolve_params(self, r_id: Optional[str], org_id: Optional[str], prod_id: Optional[str],
                         bkt: Optional[str], obj: Optional[str], et: Optional[str], gen: Optional[str]):
        return (
            r_id or self.run_id or f"run_{uuid.uuid4().hex[:10]}",
            org_id or self.organization_id or "org_default",
            prod_id or self.production_id or "prod_default",
            bkt or self.bucket or "lienmark-intake",
            obj or self.object_name or "screenplay.pdf",
            et or self.etag or f"etag_{uuid.uuid4().hex[:8]}",
            gen or self.generation,
        )

    async def _await_content_lease(self, org_id: str, prod_id: str, raw_sha: str,
                                   sem_sha: Optional[str], lock_key: str) -> Optional[IngestedDocumentRecord]:
        for _ in range(25):
            await asyncio.sleep(0.05)
            matched = self.document_store.lookup_by_hash(org_id, raw_sha, sem_sha)
            if matched is not None and matched.production_id == prod_id:
                return matched
            if self.lock_manager.acquire(lock_key, ttl_seconds=300.0) is not None:
                return None
        return self.document_store.lookup_by_hash(org_id, raw_sha, sem_sha)

    def _emit_feed_event(self, run: InvestigationRun, matched_id: Optional[str],
                          status_str: str, reason: str) -> None:
        try:
            from backend.api.webhooks.storage import record_feed_activity
            record_feed_activity({
                "run_id": run.run_id, "organization_id": run.organization_id,
                "production_id": run.production_id, "status": status_str,
                "reason": reason, "matched_document_id": matched_id,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            logger.debug(f"Feed activity emission: {exc}")

    def _handle_dedup_hit(self, run: InvestigationRun, matched: IngestedDocumentRecord,
                          repo: TenantRepository, raw_sha: str) -> InvestigationRun:
        all_appr = check_baseline_approval(matched, self.baseline_store, repo)
        tgt_state = RunStatus.COMPLETED if all_appr else RunStatus.READY_FOR_REVIEW
        meta = {
            "baseline_id": matched.version_id, "reused_baseline_id": matched.version_id,
            "all_claims_approved": all_appr, "unapproved_claims_count": 0 if all_appr else max(1, matched.claims_count),
            "dedup_cache_hit": True, "content_hash": raw_sha,
        }
        run = transition_run(run, tgt_state, reason=CACHE_HIT_REASON, metadata=meta)
        run.budget_spent_usd = 0.0
        repo.save_run(run)
        self._emit_feed_event(run, matched.document_id, tgt_state.value, CACHE_HIT_REASON)
        return run

    def _reserve_intake_budget(self, org_id: str, prod_id: str, run_id: str) -> Any:
        period_id = f"period_{datetime.now(timezone.utc).strftime('%Y_%m')}"
        return self.budget_governor.reserve(
            org_id=org_id, production_id=prod_id, run_id=run_id, period_id=period_id,
            action_id="intake_reflection", provider="gemini", model_or_mode="gemini-2.5-flash",
            max_cost_micros=500000,
        )

    async def _execute_new_document_flow(
        self, run: InvestigationRun, repo: TenantRepository, org_id: str,
        prod_id: str, obj: str, content_bytes: bytes, raw_sha: str,
    ) -> InvestigationRun:
        run = transition_run(run, RunStatus.INVESTIGATING, reason="New document investigation")
        repo.save_run(run)
        try:
            res = self._reserve_intake_budget(org_id, prod_id, run.run_id)
        except Exception as exc:
            logger.warning(f"Budget breached: {exc}")
            run = transition_run(run, RunStatus.WAITING_FOR_BUDGET, reason="Budget breached on reserve")
            repo.save_run(run)
            return run

        doc_fmt, pages, scenes, meta = parse_document_with_factory(obj, content_bytes)
        raw_text = extract_raw_text(obj, content_bytes)
        norm_hash = StreamingHasher.compute_semantic_digest(raw_text)
        ext_out = await self.intake_agent.extract_claims(raw_text)
        nodes = sanitize_extracted_claims(ext_out.claims, self.confidentiality_filter)
        ver_id = run.target_version_id or "v8"
        save_baseline_snapshot(org_id, prod_id, ver_id, raw_sha, doc_fmt, obj, nodes, run.base_version_id, self.baseline_store)
        await coordinate_drifted_claims(nodes, prod_id, ver_id, self.coordinator, repo, run.run_id)

        settlement = self.budget_governor.settle(res.reservation_id, actual_usage={"mode": "gemini-2.5-flash", "tokens_prompt": 1200, "tokens_completion": 400})
        run.budget_spent_usd = round(settlement.actual_cost_micros / 1_000_000, 4)

        doc_rec = IngestedDocumentRecord(
            document_id=f"doc_{uuid.uuid4().hex[:12]}", tenant_id=org_id, production_id=prod_id,
            filename=obj, content_hash=raw_sha, semantic_hash=norm_hash, format=doc_fmt,
            page_count=pages, scene_count=scenes, version_id=ver_id, claims_count=len(nodes),
            processing_status=DocumentProcessingStatus.COMMITTED, linked_baseline_version_id=ver_id, metadata=meta,
        )
        self.document_store.commit_document_baseline(doc_rec)
        run = transition_run(run, RunStatus.READY_FOR_REVIEW, reason="Pipeline complete", metadata={"baseline_id": ver_id})
        repo.save_run(run)
        return run

    async def process_run(
        self, run_id: Optional[str] = None, organization_id: Optional[str] = None,
        production_id: Optional[str] = None, bucket: Optional[str] = None,
        object_name: Optional[str] = None, etag: Optional[str] = None,
        generation: Optional[str] = None,
    ) -> InvestigationRun:
        """Executes full autonomous background ingestion pipeline runner."""
        r_id, org_id, prod_id, bkt, obj, et, gen = self._resolve_params(
            run_id, organization_id, production_id, bucket, object_name, etag, generation
        )
        w_lock = self.lock_manager.acquire(f"worker_lease:run:{r_id}", ttl_seconds=300.0)
        repo = self._repo_factory(org_id)
        run = repo.get_run(prod_id, r_id) or InvestigationRun(
            run_id=r_id, organization_id=org_id, production_id=prod_id, base_version_id="v7",
            target_version_id="v8", status=RunStatus.QUEUED, metadata={"bucket": bkt, "object_name": obj, "etag": et},
        )
        run.metadata["worker_fencing_token"] = getattr(w_lock, "fence_token", 1)
        repo.save_run(run)
        content_bytes = retrieve_document_bytes(bkt, obj, storage_client=self.storage_client)
        hasher = StreamingHasher()
        dig = hasher.digest_bytes(content_bytes, compute_semantic=True)
        raw_sha, sem_sha = dig.raw_sha256, dig.semantic_sha256
        c_key = f"content_lock:{org_id}:{prod_id}:{raw_sha}"
        c_lock = self.lock_manager.acquire(c_key, ttl_seconds=300.0)
        matched = None if c_lock else await self._await_content_lease(org_id, prod_id, raw_sha, sem_sha, c_key)
        try:
            matched = matched or self.document_store.lookup_by_hash(org_id, raw_sha, sem_sha)
            if matched is not None and matched.production_id == prod_id:
                return self._handle_dedup_hit(run, matched, repo, raw_sha)
            return await self._execute_new_document_flow(run, repo, org_id, prod_id, obj, content_bytes, raw_sha)
        finally:
            if c_lock: self.lock_manager.release_lock(c_lock)
            if w_lock: self.lock_manager.release_lock(w_lock)

    def enqueue_run(self, run: Union[InvestigationRun, str, Dict[str, Any]],
                    organization_id: Optional[str] = None, production_id: Optional[str] = None,
                    **kwargs: Any) -> Dict[str, Any]:
        """Idempotently enqueues investigation run descriptor."""
        r_id = run.run_id if isinstance(run, InvestigationRun) else (run.get("run_id") if isinstance(run, dict) else str(run))
        o_id = organization_id or (run.organization_id if isinstance(run, InvestigationRun) else "org_default")
        p_id = production_id or (run.production_id if isinstance(run, InvestigationRun) else "prod_default")
        with self._lock:
            for it in self._queue:
                if it.get("run_id") == r_id: return it
            desc = {"run_id": r_id, "organization_id": o_id, "production_id": p_id, "status": "queued",
                    "enqueued_at": datetime.now(timezone.utc).isoformat(), **kwargs}
            self._queue.append(desc)
            return desc

    def get_queued_runs(self) -> List[Dict[str, Any]]:
        with self._lock: return list(self._queue)

    def clear(self) -> None:
        with self._lock: self._queue.clear()


def get_ingestion_pipeline_service() -> IngestionPipelineService:
    global _pipeline_instance
    if _pipeline_instance is None: _pipeline_instance = IngestionPipelineService()
    return _pipeline_instance


def set_ingestion_pipeline_service(service: Optional[IngestionPipelineService]) -> None:
    global _pipeline_instance
    _pipeline_instance = service


def reset_ingestion_pipeline_service() -> None:
    global _pipeline_instance
    if _pipeline_instance is not None: _pipeline_instance.clear()
    _pipeline_instance = None
