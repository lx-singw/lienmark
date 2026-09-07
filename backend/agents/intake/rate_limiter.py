"""
Lienmark Leaky Bucket Token & Request Rate Limiter.
Proactively guards Google Cloud GenAI quotas against throttling.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional

from backend.agents.intake.claim_types import RateLimitExceededError

logger = logging.getLogger("lienmark.intake.rate_limiter")


class LeakyBucketTokenLimiter:
    """
    Asynchronous dual leaky bucket rate limiter.
    Smooths traffic across Tokens Per Minute (TPM) and Requests Per Minute (RPM).
    """

    def __init__(
        self,
        tokens_per_minute: int = 1_000_000,
        requests_per_minute: int = 60,
        burst_token_capacity: Optional[int] = None,
        burst_request_capacity: Optional[int] = None,
    ):
        self.tpm = max(1000, tokens_per_minute)
        self.rpm = max(1, requests_per_minute)
        self.token_leak_rate = float(self.tpm) / 60.0
        self.request_leak_rate = float(self.rpm) / 60.0
        self.token_capacity = float(burst_token_capacity or (self.tpm // 3))
        self.request_capacity = float(burst_request_capacity or max(5, self.rpm // 3))

        self._available_tokens = self.token_capacity
        self._available_requests = self.request_capacity
        self._last_leak_time = time.monotonic()
        self._lock = asyncio.Lock()
        self._total_requests_processed = 0
        self._total_tokens_consumed = 0

    def _leak_locked(self, now: float) -> None:
        """Internal helper: calculates leaked token and request allowances."""
        elapsed = max(0.0, now - self._last_leak_time)
        self._last_leak_time = now

        self._available_tokens = min(
            self.token_capacity,
            self._available_tokens + (elapsed * self.token_leak_rate)
        )
        self._available_requests = min(
            self.request_capacity,
            self._available_requests + (elapsed * self.request_leak_rate)
        )

    def _calculate_wait_time(self, needed_tokens: float, needed_requests: float) -> float:
        """Calculates seconds required to leak enough tokens and requests."""
        token_wait = needed_tokens / self.token_leak_rate if needed_tokens > 0 else 0.0
        request_wait = needed_requests / self.request_leak_rate if needed_requests > 0 else 0.0
        return max(token_wait, request_wait)

    async def acquire(self, estimated_tokens: int = 1000, timeout: float = 30.0) -> float:
        """
        Acquires token capacity, asynchronously sleeping if necessary.
        Raises RateLimitExceededError if wait time exceeds specified timeout.
        """
        req_tokens = float(max(1, estimated_tokens))
        start_time = time.monotonic()

        while True:
            async with self._lock:
                now = time.monotonic()
                self._leak_locked(now)

                has_tokens = self._available_tokens >= req_tokens
                has_requests = self._available_requests >= 1.0

                if has_tokens and has_requests:
                    self._available_tokens -= req_tokens
                    self._available_requests -= 1.0
                    self._total_requests_processed += 1
                    self._total_tokens_consumed += int(req_tokens)
                    return time.monotonic() - start_time

                needed_tokens = req_tokens - self._available_tokens
                needed_requests = 1.0 - self._available_requests
                wait_seconds = self._calculate_wait_time(needed_tokens, needed_requests)

            total_elapsed = time.monotonic() - start_time
            if total_elapsed + wait_seconds > timeout:
                raise RateLimitExceededError(
                    f"Rate limit exceeded: acquisition wait {wait_seconds:.2f}s "
                    f"exceeds timeout {timeout:.2f}s."
                )

            sleep_step = min(wait_seconds, 0.25)
            await asyncio.sleep(sleep_step)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Fast heuristic token estimator (~3.5 characters per token).
        """
        if not text or not text.strip():
            return 50
        return max(50, int(len(text) / 3.5))

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of rate limiter telemetry."""
        return {
            "tpm": self.tpm,
            "rpm": self.rpm,
            "available_tokens": round(self._available_tokens, 2),
            "available_requests": round(self._available_requests, 2),
            "total_requests": self._total_requests_processed,
            "total_tokens": self._total_tokens_consumed,
        }

    def reset(self) -> None:
        """Resets bucket levels to maximum capacity."""
        self._available_tokens = self.token_capacity
        self._available_requests = self.request_capacity
        self._last_leak_time = time.monotonic()
