"""
backend/services/ingestion_recovery.py

Autonomous recovery engine for stranded and abandoned clearance runs.
Detects unleased QUEUED runs and expired INVESTIGATING runs, recovering state
or retrying with bounded attempts (3 max) before marking as FAILED.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from backend.core.lifecycle import transition_run
from backend.domain.models import InvestigationRun, RunStatus
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import TenantRepository, get_tenant_repository

logger = logging.getLogger("lienmark.services.ingestion_recovery")


def _parse_iso_timestamp(ts: Optional[str]) -> datetime:
    """Parses ISO timestamp safely into a UTC datetime object."""
    if not ts:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(ts)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


class IngestionRecoveryService:
    """
    Autonomous recovery service sweeping stranded and abandoned clearance runs.
    """

    def __init__(
        self,
        lock_manager: Optional[DistributedLockManager] = None,
        repository_factory: Optional[Callable[[str], TenantRepository]] = None,
        pipeline_service: Optional[Any] = None,
        dispatcher: Optional[Callable[[InvestigationRun], Any]] = None,
        known_tenants: Optional[List[str]] = None,
    ) -> None:
        self.lock_manager = lock_manager or DistributedLockManager()
        self._repo_factory = repository_factory or (lambda org: get_tenant_repository(org, force_in_memory=True))
        self.pipeline_service = pipeline_service
        self.dispatcher = dispatcher
        self._known_tenants: Set[str] = set(known_tenants or ["org_default"])
        self._known_productions: Dict[str, Set[str]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_tenant(self, organization_id: str, production_id: Optional[str] = None) -> None:
        """Registers tenant and optional production boundary for recovery sweeps."""
        clean_org = organization_id.strip()
        self._known_tenants.add(clean_org)
        if production_id:
            self._known_productions.setdefault(clean_org, set()).add(production_id.strip())

    def _find_runs_by_status(
        self,
        status: RunStatus,
        organization_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> List[InvestigationRun]:
        """Collects runs matching given status across tenant partitions."""
        orgs = [organization_id.strip()] if organization_id else list(self._known_tenants)
        matched_runs: List[InvestigationRun] = []
        for org in orgs:
            repo = self._repo_factory(org)
            prods = [production_id.strip()] if production_id else list(
                self._known_productions.get(org, set()) | {p.production_id for p in repo.list_productions()} | {"prod_default"}
            )
            for prod in prods:
                runs = repo.list_runs(prod)
                for r in runs:
                    if r.status == status:
                        matched_runs.append(r)
        return matched_runs

    def _dispatch_run(self, run: InvestigationRun) -> None:
        """Re-dispatches a recovered run to the pipeline or external dispatcher."""
        if self.dispatcher is not None:
            self.dispatcher(run)
            return
        if self.pipeline_service is not None:
            if hasattr(self.pipeline_service, "enqueue_run"):
                self.pipeline_service.enqueue_run(run)
            elif hasattr(self.pipeline_service, "process_run"):
                asyncio.create_task(self.pipeline_service.process_run(
                    run_id=run.run_id, organization_id=run.organization_id,
                    production_id=run.production_id, bucket=run.metadata.get("bucket", "lienmark-intake"),
                    object_name=run.metadata.get("object_name", "screenplay.pdf"), etag=run.metadata.get("etag", "v1"),
                ))

    def recover_stranded_runs(
        self,
        max_age_seconds: float = 120,
        organization_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> List[str]:
        """Sweeps QUEUED runs that have no active worker lease, re-dispatching them."""
        runs = self._find_runs_by_status(RunStatus.QUEUED, organization_id, production_id)
        now = datetime.now(timezone.utc)
        recovered: List[str] = []
        for run in runs:
            created = _parse_iso_timestamp(run.created_at)
            age = max(0.0, (now - created).total_seconds())
            if age < max_age_seconds:
                continue
            lease_key = f"worker_lease:run:{run.run_id}"
            if self.lock_manager.is_locked(lease_key):
                continue
            self._dispatch_run(run)
            recovered.append(run.run_id)
            logger.info(f"Recovered stranded run {run.run_id} (age: {age:.1f}s)")
        return recovered

    def recover_abandoned_investigations(
        self,
        lease_timeout_seconds: float = 300,
        organization_id: Optional[str] = None,
        production_id: Optional[str] = None,
    ) -> List[str]:
        """Sweeps INVESTIGATING runs whose leases expired, retrying or failing (3 max)."""
        runs = self._find_runs_by_status(RunStatus.INVESTIGATING, organization_id, production_id)
        now = datetime.now(timezone.utc)
        recovered: List[str] = []
        for run in runs:
            last_ts = _parse_iso_timestamp(
                run.metadata.get("heartbeat_timestamp") or run.updated_at or run.created_at
            )
            elapsed = max(0.0, (now - last_ts).total_seconds())
            lease_key = f"worker_lease:run:{run.run_id}"
            is_active = self.lock_manager.is_locked(lease_key)
            if is_active and elapsed < lease_timeout_seconds:
                continue
            repo = self._repo_factory(run.organization_id)
            retries = int(run.metadata.get("recovery_retries", 0))
            if retries < 3:
                run.metadata["recovery_retries"] = retries + 1
                run = transition_run(
                    run, RunStatus.QUEUED,
                    reason=f"Recovered abandoned investigation (attempt {retries + 1}/3)",
                )
                repo.save_run(run)
                self._dispatch_run(run)
            else:
                run = transition_run(
                    run, RunStatus.FAILED, reason="Exceeded maximum recovery retries (3)",
                )
                repo.save_run(run)
            recovered.append(run.run_id)
            logger.info(f"Processed abandoned investigation {run.run_id} (attempt {retries})")
        return recovered

    def startup_sweep(self) -> Dict[str, List[str]]:
        """Runs an immediate cold-start sweep on application startup."""
        return {
            "stranded_runs": self.recover_stranded_runs(),
            "abandoned_investigations": self.recover_abandoned_investigations(),
        }

    async def run_periodic_cycle(self) -> Dict[str, List[str]]:
        """Executes a single periodic recovery cycle for cron or timer scheduling."""
        return self.startup_sweep()

    def start_periodic_sweep(self, interval_seconds: float = 30.0) -> None:
        """Starts background thread executing periodic recovery sweeps."""
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            while self._running:
                try:
                    self.startup_sweep()
                except Exception as exc:
                    logger.error(f"Error in periodic recovery sweep: {exc}")
                time.sleep(interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_periodic_sweep(self) -> None:
        """Stops background recovery sweep thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
