"""
tests/test_performance_and_resilience.py

Comprehensive test suite for Sprint 7.2:
1. 3-state Circuit Breaker (CLOSED, OPEN, HALF_OPEN) & fail-closed stance
2. Chaos resilience fault injection & latency jitter middleware
3. Cold-start recovery engine with stale run heartbeat scanning and ledger emission
4. Semaphore concurrency gating
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    DEGRADED_CIRCUIT_STANCE,
    compute_decorrelated_jitter,
)
from backend.core.recovery import (
    ColdStartRecoveryResult,
    execute_cold_start_recovery,
    is_run_stale,
    scan_stale_runs,
)
from backend.domain.models import InvestigationRun, Production, RunStatus
from backend.main import app
from backend.middleware.chaos import chaos_controller
from backend.orchestration.adk_pipeline import EXTERNAL_QUERY_SEMAPHORE
from backend.storage.repository import (
    InMemoryTenantRepository,
    _repository_cache,
    get_tenant_repository,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_chaos_and_storage():
    chaos_controller.disable()
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()
    yield
    chaos_controller.disable()
    _repository_cache.clear()
    InMemoryTenantRepository.reset_global_storage()


def test_circuit_breaker_closed_to_open_transition():
    """Validates that failures exceeding threshold trip circuit to OPEN."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_timeout=0.2)
    assert cb.state == CircuitState.CLOSED

    for _ in range(2):
        cb.record_failure(ValueError("Transient error"))
        assert cb.state == CircuitState.CLOSED

    cb.record_failure(ValueError("Third error"))
    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        cb.call_sync(lambda: "blocked")
    assert exc_info.value.stance == DEGRADED_CIRCUIT_STANCE


def test_circuit_breaker_half_open_probe_success():
    """Validates that a successful probe in HALF_OPEN resets circuit to CLOSED."""
    cb = CircuitBreaker(name="probe_cb", failure_threshold=1, recovery_timeout=0.05)
    cb.record_failure(RuntimeError("Trip"))
    assert cb.state == CircuitState.OPEN

    import time
    time.sleep(0.06)
    assert cb.state == CircuitState.HALF_OPEN

    result = cb.call_sync(lambda: "probe_ok")
    assert result == "probe_ok"
    assert cb.state == CircuitState.CLOSED


def test_decorrelated_jitter_bounds():
    """Validates decorrelated jitter stays within configured timeout limits."""
    delay = compute_decorrelated_jitter(base_timeout=5.0, max_timeout=60.0, attempt=3, prev_timeout=10.0)
    assert 5.0 <= delay <= 60.0


def test_chaos_middleware_fault_injection_and_headers():
    """Validates that enabled chaos middleware injects faults with X-Chaos headers."""
    chaos_controller.enable(failure_rate=1.0, jitter=False)
    res = client.get("/api/demo/state")
    assert res.status_code in (502, 504, 429)
    assert res.headers.get("X-Chaos-Injected") == "true"
    assert "http_" in res.headers.get("X-Chaos-Type", "")

    # Exempt health route must not be affected
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert "X-Chaos-Injected" not in res_health.headers


def test_stale_run_detection_and_cold_start_rehydration():
    """Validates heartbeat scanning, lease acquisition, and ledger emission."""
    org_id = "org_recovery_01"
    pid = "prod_rec_01"
    repo = get_tenant_repository(org_id)
    repo.save_production(Production(production_id=pid, organization_id=org_id, title="Test Prod"))

    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    run = InvestigationRun(
        run_id="run_stale_01",
        production_id=pid,
        organization_id=org_id,
        base_version_id="v7",
        target_version_id="v8",
        status=RunStatus.INVESTIGATING,
        created_at=stale_time,
        updated_at=stale_time,
        metadata={"heartbeat_timestamp": stale_time},
    )
    repo.save_run(run)

    stale, dur = is_run_stale(run, stale_threshold_sec=60.0)
    assert stale is True
    assert dur >= 60.0

    mock_ledger = MagicMock()
    results = execute_cold_start_recovery(
        repo=repo,
        production_ids=[pid],
        ledger=mock_ledger,
        stale_threshold_sec=60.0,
    )
    assert len(results) == 1
    assert results[0].status == "REHYDRATED"
    assert results[0].fencing_token >= 1
    mock_ledger.append_event.assert_called_once()
    assert mock_ledger.append_event.call_args[1]["action_type"] == "COLD_START_RUN_REHYDRATED"


def test_recovery_endpoint_http():
    """Validates /api/recovery/cold-start REST endpoint."""
    res = client.post("/api/recovery/cold-start?stale_threshold_sec=60.0")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "rehydrated_count" in data


def test_semaphore_concurrency_capacity():
    """Validates that EXTERNAL_QUERY_SEMAPHORE is configured with bounded capacity 10."""
    assert EXTERNAL_QUERY_SEMAPHORE._value <= 10
