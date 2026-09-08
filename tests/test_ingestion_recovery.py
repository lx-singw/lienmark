"""
tests/test_ingestion_recovery.py

Automated test suite for IngestionRecoveryService.
Tests recovery of stranded QUEUED runs, abandoned INVESTIGATING runs,
retry bounds (3 max then FAILED), and startup/periodic sweeps.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from backend.domain.models import InvestigationRun, RunStatus
from backend.services.ingestion_recovery import IngestionRecoveryService
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository, get_tenant_repository


@pytest.fixture(autouse=True)
def clean_env():
    InMemoryTenantRepository.reset_global_storage()
    yield


def _create_test_run(run_id: str, org_id: str, prod_id: str, status: RunStatus, age_secs: int = 0, retries: int = 0):
    iso = (datetime.now(timezone.utc) - timedelta(seconds=age_secs)).isoformat()
    return InvestigationRun(
        run_id=run_id, organization_id=org_id, production_id=prod_id,
        base_version_id="v7", target_version_id="v8", status=status,
        created_at=iso, updated_at=iso, metadata={"recovery_retries": retries} if retries else {},
    )


def test_recover_stranded_queued_runs():
    """Verifies recovery sweeps stranded QUEUED runs without active worker leases."""
    org_id, prod_id = "org_recovery_01", "prod_rec_01"
    repo = get_tenant_repository(org_id, force_in_memory=True)
    lock_mgr = DistributedLockManager(in_memory=True)

    repo.save_run(_create_test_run("run_stranded_old", org_id, prod_id, RunStatus.QUEUED, age_secs=150))
    repo.save_run(_create_test_run("run_stranded_recent", org_id, prod_id, RunStatus.QUEUED))
    locked_run = _create_test_run("run_stranded_locked", org_id, prod_id, RunStatus.QUEUED, age_secs=150)
    repo.save_run(locked_run)
    lock_mgr.acquire(f"worker_lease:run:{locked_run.run_id}", ttl_seconds=300.0)

    dispatched = []
    service = IngestionRecoveryService(
        lock_manager=lock_mgr,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
        dispatcher=lambda r: dispatched.append(r.run_id),
        known_tenants=[org_id],
    )
    service.register_tenant(org_id, prod_id)

    recovered = service.recover_stranded_runs(max_age_seconds=120)
    assert recovered == ["run_stranded_old"]
    assert dispatched == ["run_stranded_old"]


def test_recover_abandoned_investigations_retry_bound():
    """Verifies abandoned INVESTIGATING runs retry up to 3 times, then transition to FAILED."""
    org_id, prod_id = "org_recovery_02", "prod_rec_02"
    repo = get_tenant_repository(org_id, force_in_memory=True)
    lock_mgr = DistributedLockManager(in_memory=True)

    repo.save_run(_create_test_run("run_abandoned_1", org_id, prod_id, RunStatus.INVESTIGATING, age_secs=400, retries=0))
    repo.save_run(_create_test_run("run_abandoned_max", org_id, prod_id, RunStatus.INVESTIGATING, age_secs=400, retries=3))

    service = IngestionRecoveryService(
        lock_manager=lock_mgr,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
        known_tenants=[org_id],
    )
    service.register_tenant(org_id, prod_id)

    recovered = service.recover_abandoned_investigations(lease_timeout_seconds=300)
    assert "run_abandoned_1" in recovered and "run_abandoned_max" in recovered

    updated1 = repo.get_run(prod_id, "run_abandoned_1")
    assert updated1.status == RunStatus.QUEUED and updated1.metadata.get("recovery_retries") == 1
    updated2 = repo.get_run(prod_id, "run_abandoned_max")
    assert updated2.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_startup_sweep_and_periodic_cycle():
    """Verifies startup sweep and periodic recovery cycle invocation."""
    org_id = "org_recovery_03"
    prod_id = "prod_rec_03"
    repo = get_tenant_repository(org_id, force_in_memory=True)
    lock_mgr = DistributedLockManager(in_memory=True)

    old_iso = (datetime.now(timezone.utc) - timedelta(seconds=500)).isoformat()
    run = InvestigationRun(
        run_id="run_sweep_test", organization_id=org_id, production_id=prod_id,
        base_version_id="v7", target_version_id="v8", status=RunStatus.QUEUED,
        created_at=old_iso, updated_at=old_iso,
    )
    repo.save_run(run)

    service = IngestionRecoveryService(
        lock_manager=lock_mgr,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
        known_tenants=[org_id],
    )
    service.register_tenant(org_id, prod_id)

    res_startup = service.startup_sweep()
    assert "stranded_runs" in res_startup
    assert "run_sweep_test" in res_startup["stranded_runs"]

    res_cycle = await service.run_periodic_cycle()
    assert "stranded_runs" in res_cycle
