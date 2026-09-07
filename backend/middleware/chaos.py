"""
backend/middleware/chaos.py

Chaos Resilience Fault Injection Middleware.
Simulates transient network and external API disruptions (502 Bad Gateway,
504 Gateway Timeout, 429 Rate Limit) and latency jitter with runtime enable/disable controls.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from typing import Optional, Set
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("lienmark.middleware.chaos")


class ChaosController:
    """Runtime controller governing fault injection and latency jitter."""

    def __init__(self) -> None:
        self.is_enabled: bool = os.getenv("CHAOS_ENABLED", "").lower() in ("true", "1", "yes")
        self.failure_rate: float = float(os.getenv("CHAOS_FAILURE_RATE", "0.10"))
        self.latency_jitter_enabled: bool = os.getenv("CHAOS_JITTER_ENABLED", "").lower() in ("true", "1")
        self.min_latency_ms: float = float(os.getenv("CHAOS_MIN_LATENCY_MS", "50.0"))
        self.max_latency_ms: float = float(os.getenv("CHAOS_MAX_LATENCY_MS", "300.0"))
        self.exempt_paths: Set[str] = {
            "/health",
            "/healthz",
            "/readyz",
            "/api/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
        }

    def enable(self, failure_rate: float = 0.10, jitter: bool = False) -> None:
        """Enables chaos fault injection at runtime."""
        self.is_enabled = True
        self.failure_rate = max(0.0, min(1.0, failure_rate))
        self.latency_jitter_enabled = jitter
        logger.info(f"Chaos middleware ENABLED: failure_rate={self.failure_rate}, jitter={jitter}")

    def disable(self) -> None:
        """Disables chaos fault injection at runtime."""
        self.is_enabled = False
        logger.info("Chaos middleware DISABLED.")

    def should_inject_failure(self, path: str) -> Optional[int]:
        """Evaluates whether to inject a simulated 502, 504, or 429 status code."""
        if not self.is_enabled:
            return None
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return None
        if random.random() < self.failure_rate:
            return random.choice([502, 504, 429])
        return None

    def calculate_jitter_seconds(self, path: str) -> float:
        """Calculates random latency jitter in seconds if path is not exempt."""
        if not self.is_enabled or not self.latency_jitter_enabled:
            return 0.0
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return 0.0
        jitter_ms = random.uniform(self.min_latency_ms, self.max_latency_ms)
        return jitter_ms / 1000.0


chaos_controller = ChaosController()


class ChaosMiddleware(BaseHTTPMiddleware):
    """Starlette middleware injecting simulated chaos faults and latency jitter."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        simulated_status = chaos_controller.should_inject_failure(path)

        if simulated_status is not None:
            details = {
                502: "Bad Gateway (Simulated Chaos)",
                504: "Gateway Timeout (Simulated Chaos)",
                429: "Too Many Requests (Simulated Chaos)",
            }
            logger.warning(f"Chaos fault injected on {path}: HTTP {simulated_status}")
            return JSONResponse(
                status_code=simulated_status,
                content={
                    "error": "chaos_fault_injected",
                    "status_code": simulated_status,
                    "detail": details.get(simulated_status, "Chaos Fault"),
                    "path": path,
                },
                headers={
                    "X-Chaos-Injected": "true",
                    "X-Chaos-Type": f"http_{simulated_status}",
                    "Retry-After": "1",
                },
            )

        delay_sec = chaos_controller.calculate_jitter_seconds(path)
        if delay_sec > 0.0:
            await asyncio.sleep(delay_sec)

        response = await call_next(request)
        if delay_sec > 0.0:
            response.headers["X-Chaos-Injected"] = "true"
            response.headers["X-Chaos-Latency-Ms"] = f"{delay_sec * 1000.0:.1f}"
        return response
