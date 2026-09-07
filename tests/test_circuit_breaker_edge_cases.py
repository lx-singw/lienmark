"""
tests/test_circuit_breaker_edge_cases.py

Edge case tests for Circuit Breaker:
HTTP 5xx status discrimination, async coroutine fallbacks,
probe stampede prevention, Pydantic v2 serialization, and custom predicates.
"""

import asyncio
import httpx
import pytest

from backend.services.circuit_breaker import CircuitBreaker
from backend.services.circuit_breaker_types import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class MockClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.val = start

    def __call__(self) -> float:
        return self.val

    def advance(self, secs: float) -> None:
        self.val += secs


@pytest.mark.asyncio
async def test_http_502_trips_breaker_404_does_not() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="http_status_test", clock=clock)
    req = httpx.Request("GET", "https://api.test.internal")

    err_502 = httpx.HTTPStatusError("Bad Gateway", request=req, response=httpx.Response(502))
    err_404 = httpx.HTTPStatusError("Not Found", request=req, response=httpx.Response(404))

    async def call_404():
        raise err_404

    with pytest.raises(httpx.HTTPStatusError):
        await breaker.call_async(call_404)
    assert breaker.get_telemetry().consecutive_failures == 0
    assert breaker.state == CircuitState.CLOSED

    async def call_502():
        raise err_502

    for _ in range(3):
        with pytest.raises(httpx.HTTPStatusError):
            await breaker.call_async(call_502)

    assert breaker.state == CircuitState.OPEN
    assert breaker.get_telemetry().total_trips == 1


@pytest.mark.asyncio
async def test_async_coroutine_fallback_with_args() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="async_fallback", clock=clock)

    async def failing_action(query: str):
        raise httpx.ConnectError("Network dead")

    async def fallback_mirror(query: str):
        return f"cached_record_for_{query}"

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(failing_action, "lien_001")

    assert breaker.state == CircuitState.OPEN

    res = await breaker.call_async(failing_action, "lien_001", fallback=fallback_mirror)
    assert res == "cached_record_for_lien_001"
    assert breaker.get_telemetry().total_fallbacks == 1


@pytest.mark.asyncio
async def test_half_open_probe_stampede_prevention() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="stampede_test", clock=clock)

    async def fail():
        raise httpx.ConnectError("Down")

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(fail)

    assert breaker.state == CircuitState.OPEN
    clock.advance(60.0)
    assert breaker.state == CircuitState.HALF_OPEN

    probe_entered = asyncio.Event()
    probe_proceed = asyncio.Event()

    async def slow_probe():
        probe_entered.set()
        await probe_proceed.wait()
        return "slow_probe_ok"

    probe_task = asyncio.create_task(breaker.call_async(slow_probe))
    await probe_entered.wait()

    concurrent_res = await breaker.call_async(
        slow_probe, fallback=lambda: "fallback_during_probe"
    )
    assert concurrent_res == "fallback_during_probe"

    probe_proceed.set()
    probe_result = await probe_task
    assert probe_result == "slow_probe_ok"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_custom_failure_predicate() -> None:
    class CustomRemoteErr(Exception):
        pass

    def custom_predicate(exc: BaseException) -> bool:
        return isinstance(exc, CustomRemoteErr)

    breaker = CircuitBreaker(
        name="custom_pred",
        failure_predicate=custom_predicate,
    )

    async def normal_err():
        raise RuntimeError("Ignored runtime error")

    with pytest.raises(RuntimeError):
        await breaker.call_async(normal_err)
    assert breaker.get_telemetry().consecutive_failures == 0

    async def custom_err():
        raise CustomRemoteErr("Trigger error")

    for _ in range(3):
        with pytest.raises(CustomRemoteErr):
            await breaker.call_async(custom_err)

    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_telemetry_pydantic_v2_serialization() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="telemetry_serialization", clock=clock)

    async def succeed():
        return {"data": 42}

    await breaker.call_async(succeed)
    telemetry = breaker.get_telemetry()

    json_str = telemetry.model_dump_json()
    assert '"circuit_name":"telemetry_serialization"' in json_str
    assert '"state":"CLOSED"' in json_str
    assert '"total_successes":1' in json_str

    dumped = telemetry.model_dump()
    assert dumped["circuit_name"] == "telemetry_serialization"
    assert dumped["state"] == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_manual_reset() -> None:
    clock = MockClock()
    breaker = CircuitBreaker(name="manual_reset_test", clock=clock)

    async def fail():
        raise httpx.ConnectError("Down")

    for _ in range(3):
        with pytest.raises(httpx.ConnectError):
            await breaker.call_async(fail)

    assert breaker.state == CircuitState.OPEN
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_telemetry().consecutive_failures == 0
