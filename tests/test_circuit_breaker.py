"""
tests/test_circuit_breaker.py

Unit and integration tests for Circuit Breaker subsystem.
Verifies state transitions, trip thresholds, probe mechanisms,
fallback routing, telemetry snapshots, and async safety.
"""

import asyncio
import httpx
import pytest

from backend.services.circuit_breaker import (
    CircuitBreaker,
    circuit_breaker,
    reset_all_circuit_breakers,
)
from backend.services.circuit_breaker_types import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class MockClock:
    """Deterministic simulated clock for time-dependent testing."""

    def __init__(self, initial_time: float = 1000.0) -> None:
        self.current_time = initial_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


@pytest.fixture(autouse=True)
def clean_registry():
    reset_all_circuit_breakers()
    yield
    reset_all_circuit_breakers()


@pytest.mark.asyncio
async def test_initial_state_closed() -> None:
    breaker = CircuitBreaker(name="test_initial")
    assert breaker.state == CircuitState.CLOSED
    telemetry = breaker.get_telemetry()
    assert telemetry.consecutive_failures == 0
    assert telemetry.total_requests == 0
    assert telemetry.total_trips == 0


@pytest.mark.asyncio
async def test_trip_after_strictly_three_failures() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="test_trip", clock=clock)

    async def faulty_call():
        raise httpx.ConnectError("Connection dropped")

    for i in range(2):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(faulty_call)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.get_telemetry().consecutive_failures == i + 1

    with pytest.raises(httpx.ConnectError):
        await breaker.call_async(faulty_call)

    assert breaker.state == CircuitState.OPEN
    telemetry = breaker.get_telemetry()
    assert telemetry.consecutive_failures == 3
    assert telemetry.total_trips == 1


@pytest.mark.asyncio
async def test_success_resets_consecutive_failures() -> None:
    breaker = CircuitBreaker(name="test_reset_failures")

    async def fail():
        raise httpx.ReadTimeout("Timeout")

    async def succeed():
        return "ok"

    for _ in range(2):
        with pytest.raises(httpx.ReadTimeout):
            await breaker.call_async(fail)
    assert breaker.get_telemetry().consecutive_failures == 2

    res = await breaker.call_async(succeed)
    assert res == "ok"
    assert breaker.get_telemetry().consecutive_failures == 0
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_non_qualifying_exceptions_do_not_trip() -> None:
    breaker = CircuitBreaker(name="test_non_qualifying")

    async def bad_input():
        raise ValueError("Invalid user argument")

    for _ in range(5):
        with pytest.raises(ValueError):
            await breaker.call_async(bad_input)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_telemetry().consecutive_failures == 0


@pytest.mark.asyncio
async def test_open_circuit_fast_fail_with_open_error() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="test_fast_fail", clock=clock)

    async def drop():
        raise ConnectionResetError("Reset by peer")

    for _ in range(3):
        with pytest.raises(ConnectionResetError):
            await breaker.call_async(drop)

    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        await breaker.call_async(drop)

    err = exc_info.value
    assert err.circuit_name == "test_fast_fail"
    assert err.retry_after == 60.0
    assert err.is_stale is True


@pytest.mark.asyncio
async def test_fallback_routing_when_open() -> None:
    clock = MockClock()
    cached_data = {"source": "cached_mirror", "records": [1, 2, 3]}
    breaker = CircuitBreaker(name="test_fallback", clock=clock)
    breaker.set_cached_mirror(cached_data)

    async def fail_req():
        raise httpx.ConnectTimeout("Timeout")

    for _ in range(3):
        with pytest.raises(httpx.ConnectTimeout):
            await breaker.call_async(fail_req)

    assert breaker.state == CircuitState.OPEN

    result = await breaker.call_async(fail_req)
    assert result == cached_data
    assert breaker.get_telemetry().total_fallbacks == 1


@pytest.mark.asyncio
async def test_half_open_probe_success_resets_to_closed() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="test_probe_success", clock=clock)

    async def fail():
        raise httpx.ConnectError("Down")

    async def healthy():
        return "recovered"

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(fail)

    assert breaker.state == CircuitState.OPEN

    clock.advance(60.0)
    assert breaker.state == CircuitState.HALF_OPEN

    result = await breaker.call_async(healthy)
    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_telemetry().consecutive_failures == 0


@pytest.mark.asyncio
async def test_half_open_probe_failure_retrips_to_open() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="test_probe_fail", clock=clock)

    async def fail():
        raise httpx.ConnectError("Down")

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(fail)

    clock.advance(60.0)
    assert breaker.state == CircuitState.HALF_OPEN

    with pytest.raises(httpx.ConnectError):
        await breaker.call_async(fail)

    assert breaker.state == CircuitState.OPEN
    assert breaker.get_telemetry().total_trips == 2


@pytest.mark.asyncio
async def test_decorator_integration() -> None:
    @circuit_breaker(name="decorator_service")
    async def sample_endpoint(val: int):
        if val < 0:
            raise httpx.ConnectError("Network dropped")
        return val * 2

    assert await sample_endpoint(5) == 10
    breaker = sample_endpoint.circuit_breaker
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_telemetry().total_successes == 1


@pytest.mark.asyncio
async def test_concurrent_call_safety() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="test_concurrency", clock=clock)

    async def task_call(idx: int):
        if idx < 3:
            raise httpx.ConnectError(f"Fail {idx}")
        return idx

    results = await asyncio.gather(
        *(breaker.call_async(task_call, i, fallback=lambda i: -1) for i in range(10)),
        return_exceptions=True,
    )
    telemetry = breaker.get_telemetry()
    assert telemetry.total_requests == 10
    assert telemetry.total_trips >= 1
