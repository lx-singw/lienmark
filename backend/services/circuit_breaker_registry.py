"""
backend/services/circuit_breaker_registry.py

Registry and decorator interface for the Circuit Breaker subsystem.
Separates global singleton lifecycle management and function decoration
from the core state machine in accordance with SRP and architectural limits.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Optional

from backend.services.circuit_breaker import CircuitBreaker
from backend.services.circuit_breaker_types import CircuitBreakerConfig

_CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Any] = None,
    failure_predicate: Optional[Callable[[BaseException], bool]] = None,
    clock: Optional[Callable[[], float]] = None,
) -> CircuitBreaker:
    """
    Retrieves or registers a named CircuitBreaker singleton instance.
    Ensures safe reuse of circuit breakers across multiple service calls.
    """
    if name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[name] = CircuitBreaker(
            name=name,
            config=config,
            fallback=fallback,
            failure_predicate=failure_predicate,
            clock=clock,
        )
    return _CIRCUIT_BREAKERS[name]


def reset_all_circuit_breakers() -> None:
    """Resets the global circuit breaker registry (for testing teardown)."""
    _CIRCUIT_BREAKERS.clear()


def circuit_breaker(
    name: Optional[str] = None,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Any] = None,
    failure_predicate: Optional[Callable[[BaseException], bool]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to protect async and sync functions with a CircuitBreaker.
    Attaches the active breaker instance to wrapper.circuit_breaker for inspection.
    """
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        cb_name = name or f"{fn.__module__}.{fn.__qualname__}"
        breaker = get_circuit_breaker(
            name=cb_name,
            config=config,
            fallback=fallback,
            failure_predicate=failure_predicate,
        )

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker.call_async(fn, *args, fallback=fallback, **kwargs)

        wrapper.circuit_breaker = breaker  # type: ignore[attr-defined]
        return wrapper

    return decorator
