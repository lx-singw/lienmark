"""
tests/test_chaos_recovery.py

Sprint 7.2: End-to-End Performance, Cold-Start & Chaos Resilience Test Suite.
Verifies stale run detection after worker SIGKILL, cold-start rehydration from
CheckpointStore with monotonic fencing tokens (INV-S72-01), duplicate worker
locking rejection, circuit breaker 3-state degradation (INV-S72-03), and sub-100ms
deduplication cache hit latency.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
import pytest

from backend.core.circuit_breaker import (
    DEGRADED_CIRCUIT_STANCE,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from backend.core.recovery import (
    is_run_stale,
    rehydrate_stale_run,
    scan_stale_runs,
)
from backend.domain.models import InvestigationRun, Production, RunStatus
from backend.storage.checkpoint_store import CheckpointStore
from backend.storage.checkpoint_types import AgentStateVector
from backend.storage.document_store import DocumentStore
from backend.storage.ledger import CryptographicLedger
from backend.storage.lock_types import LockAcquisitionError
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository, get_tenant_repository


def test_worker_sigkill_simulation_and_stale_detection() -> None:
    """Scan for runs in INVESTIGATING with stale heartbeats (> 60s) for recovery."""
    repo = InMemoryTenantRepository("org_chaos_tenant")
    pid = "prod_sigkill_01"
    repo.save_production(Production(production_id=pid, title="Sigkill Prod", organization_id="org_chaos_tenant"))

    stale_hb = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    fresh_hb = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()

    r1 = InvestigationRun(
        run_id="run_stale_sigkill", production_id=pid, organization_id="org_chaos_tenant",
        base_version_id="v1", target_version_id="v2", status=RunStatus.INVESTIGATING,
        metadata={"heartbeat_timestamp": stale_hb},
    )
    r2 = InvestigationRun(
        run_id="run_fresh_active", production_id=pid, organization_id="org_chaos_tenant",
        base_version_id="v1", target_version_id="v2", status=RunStatus.INVESTIGATING,
        metadata={"heartbeat_timestamp": fresh_hb},
    )
    r3 = InvestigationRun(
        run_id="run_completed_old", production_id=pid, organization_id="org_chaos_tenant",
        base_version_id="v1", target_version_id="v2", status=RunStatus.COMPLETED,
        metadata={"heartbeat_timestamp": stale_hb},
    )
    repo.save_run(r1)
    repo.save_run(r2)
    repo.save_run(r3)

    is_stale, dur = is_run_stale(r1, stale_threshold_sec=60.0)
    assert is_stale is True and dur >= 60.0

    stale_list = scan_stale_runs(repo, pid, stale_threshold_sec=60.0)
    assert len(stale_list) == 1
    assert stale_list[0][0].run_id == "run_stale_sigkill"
    assert stale_list[0][1] >= 60.0


def test_cold_start_rehydration_resumes_to_completion(tmp_path) -> None:
    """Verify state rehydration from CheckpointStore with monotonic fencing tokens (INV-S72-01)."""
    org_id, pid, rid = "org_rehydrate", "prod_rehydrate", "run_rehydrate_01"
    repo = InMemoryTenantRepository(org_id)
    repo.save_production(Production(production_id=pid, title="Rehydrate Cut", organization_id=org_id))
    stale_hb = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    run = InvestigationRun(
        run_id=rid, production_id=pid, organization_id=org_id,
        base_version_id="v1", target_version_id="v2", status=RunStatus.INVESTIGATING,
        metadata={"heartbeat_timestamp": stale_hb},
    )
    repo.save_run(run)

    cp_store = CheckpointStore(force_local=True, base_output_dir=str(tmp_path / "checkpoints"))
    state = AgentStateVector(
        current_step="research",
        completed_claim_ids=["claim_01", "claim_02"],
        active_hypotheses={"claim_03": "fair_use"},
    )
    ckpt = cp_store.create_checkpoint(org_id, pid, rid, state)
    cp_store.save_checkpoint(ckpt)

    ledger = CryptographicLedger(repository=repo)
    ledger.initialize_production_ledger(tenant_id=org_id, production_id=pid, actor_id="lead_counsel")
    lock_mgr = DistributedLockManager(in_memory=True)
    res = rehydrate_stale_run(repo, run, stale_duration_sec=90.0, ledger=ledger, lock_manager=lock_mgr, checkpoint_store=cp_store)

    assert res.status == "REHYDRATED"
    assert res.fencing_token >= 1
    assert res.checkpoint_id == ckpt.checkpoint_id

    updated_run = repo.get_run(pid, rid)
    assert updated_run.status == RunStatus.COMPLETED
    assert updated_run.metadata.get("recovery_fencing_token") == res.fencing_token


def test_idempotent_recovery_locking_rejects_duplicate_worker() -> None:
    """Verify duplicate worker attempts fail with LockAcquisitionError to prevent split-brain."""
    lock_mgr = DistributedLockManager(in_memory=True)
    lock_key = "recovery_lease_org_prod_run_01"

    rec1 = lock_mgr.acquire_lock(lock_key, owner_id="worker_alpha", ttl_seconds=60.0)
    assert rec1.owner_id == "worker_alpha"
    assert rec1.fence_token == 1

    with pytest.raises(LockAcquisitionError) as exc_info:
        lock_mgr.acquire_lock(lock_key, owner_id="worker_beta", ttl_seconds=60.0)
    assert "held by 'worker_alpha'" in str(exc_info.value)

    assert lock_mgr.acquire(lock_key, owner_id="worker_beta") is None

    assert lock_mgr.release_lock(lock_key, "worker_alpha") is True
    rec2 = lock_mgr.acquire_lock(lock_key, owner_id="worker_beta", ttl_seconds=60.0)
    assert rec2.owner_id == "worker_beta"
    assert rec2.fence_token == 2


def test_chaos_fault_injection_circuit_breaker_degradation() -> None:
    """Verify network failures trigger 3-state transitions and fail-closed truthfulness (INV-S72-03)."""
    cb = CircuitBreaker(name="external_search_api", failure_threshold=3, recovery_timeout=0.05)
    assert cb.state == CircuitState.CLOSED

    # Simulate 3 consecutive network failures (HTTP 502/504 or 429 rate limit)
    cb.record_failure(Exception("HTTP 502 Bad Gateway"))
    cb.record_failure(Exception("HTTP 429 Rate Limit Exceeded"))
    cb.record_failure(Exception("HTTP 504 Gateway Timeout"))
    assert cb.state == CircuitState.OPEN

    # Fail-closed truthfulness check: must raise UNVERIFIED_CIRCUIT_DEGRADED stance
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        cb.call_sync(lambda: "CLEARED")
    assert DEGRADED_CIRCUIT_STANCE in str(exc_info.value)
    assert exc_info.value.stance == DEGRADED_CIRCUIT_STANCE

    # Cooldown expires: transition OPEN -> HALF_OPEN
    cb._last_state_change = time.monotonic() - (cb._current_recovery_delay + 5.0)
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe restores circuit: HALF_OPEN -> CLOSED
    result = cb.call_sync(lambda: "VALIDATED_PROBE_SUCCESS")
    assert result == "VALIDATED_PROBE_SUCCESS"
    assert cb.state == CircuitState.CLOSED


def test_deduplication_cache_hit_latency_benchmark() -> None:
    """Measure and assert sub-100ms deduplication cache hit latency."""
    store = DocumentStore()
    payload = b"%PDF-1.4\n1 0 obj << /Title (Cinema Script) >> endobj\ntrailer << >>\n%%EOF"

    doc1, res1 = store.lookup_or_register(
        tenant_id="org_perf", production_id="prod_perf", file_path_or_name="script_v1.pdf",
        content_bytes=payload, version_id="v1", claims_count=8,
    )
    assert not res1.is_duplicate
    store.commit_document_baseline("org_perf", doc1.document_id, "v1")

    t_start = time.perf_counter()
    doc2, res2 = store.lookup_or_register(
        tenant_id="org_perf", production_id="prod_perf", file_path_or_name="script_renamed_copy.pdf",
        content_bytes=payload, version_id="v1", claims_count=8,
    )
    latency_ms = (time.perf_counter() - t_start) * 1000.0

    assert res2.is_duplicate is True
    assert doc2.document_id == doc1.document_id
    assert latency_ms < 100.0, f"Cache hit latency {latency_ms:.2f}ms exceeded 100ms SLA"
