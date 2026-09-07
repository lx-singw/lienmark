"""
Tests for Lienmark Leaky Bucket Token & Request Rate Limiter.
Validates burst capacity, token leak rates, concurrency, and timeout enforcement.
"""

import pytest
import asyncio
import time

from backend.agents.intake.rate_limiter import LeakyBucketTokenLimiter
from backend.agents.intake.claim_types import RateLimitExceededError


@pytest.mark.asyncio
async def test_rate_limiter_immediate_acquire():
    """Verifies that requests within burst capacity are acquired with near-zero latency."""
    limiter = LeakyBucketTokenLimiter(
        tokens_per_minute=60_000,
        requests_per_minute=60,
        burst_token_capacity=10_000,
        burst_request_capacity=10,
    )
    elapsed = await limiter.acquire(estimated_tokens=500, timeout=1.0)
    assert elapsed < 0.1
    metrics = limiter.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["total_tokens"] == 500
    assert metrics["available_tokens"] <= 9500.0


@pytest.mark.asyncio
async def test_rate_limiter_leaks_over_time():
    """Verifies that consumed tokens leak back over elapsed time."""
    limiter = LeakyBucketTokenLimiter(
        tokens_per_minute=60_000,  # 1000 tokens/sec
        requests_per_minute=600,   # 10 req/sec
        burst_token_capacity=2000,
        burst_request_capacity=10,
    )
    # Drain 1500 tokens
    await limiter.acquire(estimated_tokens=1500, timeout=1.0)
    metrics_initial = limiter.get_metrics()
    assert metrics_initial["available_tokens"] <= 500.0

    # Sleep for 0.2s (should leak ~200 tokens)
    await asyncio.sleep(0.2)
    # Acquire a small amount to trigger leak calculation
    await limiter.acquire(estimated_tokens=50, timeout=1.0)
    metrics_after = limiter.get_metrics()
    assert metrics_after["available_tokens"] > 500.0


@pytest.mark.asyncio
async def test_rate_limiter_timeout_exceeded():
    """Verifies that requesting more capacity than can leak within timeout raises error."""
    limiter = LeakyBucketTokenLimiter(
        tokens_per_minute=60,  # 1 token/sec
        requests_per_minute=60,
        burst_token_capacity=10,
        burst_request_capacity=5,
    )
    # Drain the bucket
    await limiter.acquire(estimated_tokens=10, timeout=1.0)

    # Attempt to acquire 100 tokens with 0.1s timeout (needs ~100s to leak)
    with pytest.raises(RateLimitExceededError):
        await limiter.acquire(estimated_tokens=100, timeout=0.1)


def test_token_estimation_heuristic():
    """Verifies heuristic token estimation logic."""
    assert LeakyBucketTokenLimiter.estimate_tokens("") == 50
    assert LeakyBucketTokenLimiter.estimate_tokens("   ") == 50
    sample_text = "This is a typical screenplay line containing about ten words total."
    estimated = LeakyBucketTokenLimiter.estimate_tokens(sample_text)
    assert estimated >= 15


def test_rate_limiter_reset():
    """Verifies resetting rate limiter restored maximum burst capacity."""
    limiter = LeakyBucketTokenLimiter(
        tokens_per_minute=10_000,
        requests_per_minute=60,
        burst_token_capacity=5000,
        burst_request_capacity=10,
    )
    limiter._available_tokens = 100.0
    limiter.reset()
    metrics = limiter.get_metrics()
    assert metrics["available_tokens"] == 5000.0
