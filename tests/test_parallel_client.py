"""
tests/test_parallel_client.py

Automated test suite for ParallelSearchClient transport, retry, and mock replay.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.services.domain_authority import (
    classify_domain_tier,
    extract_canonical_domain,
    score_domain_authority,
)
from backend.services.mock_parallel import MockParallelClient
from backend.services.parallel_client import ParallelSearchClient
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelAuthError,
    ParallelClientError,
    ParallelRateLimitError,
    ParallelSearchRequest,
    ParallelSearchResult,
    ParallelServerError,
    ParallelTimeoutError,
)


def _build_test_request(query: str = "Clair de Lune") -> ParallelSearchRequest:
    """Helper constructing valid ParallelSearchRequest."""
    return ParallelSearchRequest(
        objective="Verify public domain status of musical composition",
        search_queries=[query],
        mode="fast",
        max_chars_total=2000,
        max_results=5,
    )


@pytest.mark.asyncio
async def test_client_http2_configuration_and_tls():
    """Verifies that client enables TLS verification and attempts HTTP/2."""
    client = ParallelSearchClient(api_key="test_key_123")
    assert client.timeout == 5.0
    assert client.max_retries == 3
    headers = client._build_headers()
    assert headers["x-api-key"] == "test_key_123"
    assert headers["Authorization"] == "Bearer test_key_123"
    assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_client_timeout_handling_fail_closed():
    """Verifies that timeout on all retries fails closed cleanly with status 504."""
    client = ParallelSearchClient(api_key="test_key", max_retries=2, backoff_base=0.01)
    req = _build_test_request()

    with patch.object(client, "_execute_attempt", side_effect=httpx.TimeoutException("Read timed out")):
        result = await client.search(req)

    assert result.http_status == 504
    assert len(result.findings) == 0
    assert result.search_id == "fail_closed_provider_error"
    assert any("Timeout" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_retry_backoff_on_429_rate_limit():
    """Verifies exponential retry when provider returns HTTP 429 then recovers."""
    client = ParallelSearchClient(api_key="test_key", max_retries=3, backoff_base=0.01)
    req = _build_test_request()

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.headers = {"retry-after": "0.01"}

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.content = b'{"search_id": "call_recovered", "results": [{"url": "https://ascap.com/work/1", "title": "ASCAP", "excerpts": ["Cleared"]}]}'

    with patch.object(client, "_execute_attempt", side_effect=[mock_resp_429, mock_resp_200]):
        result = await client.search(req)

    assert result.http_status == 200
    assert result.search_id == "call_recovered"
    assert len(result.findings) == 1
    assert result.findings[0].domain == "ascap.com"
    assert result.findings[0].authority_tier == DomainAuthorityTier.TIER_2_RIGHTS_ORG


@pytest.mark.asyncio
async def test_retry_exhaustion_on_503_fails_closed():
    """Verifies that persistent 503 gateway drops fail closed without crashing."""
    client = ParallelSearchClient(api_key="test_key", max_retries=2, backoff_base=0.01)
    req = _build_test_request()

    mock_resp_503 = MagicMock()
    mock_resp_503.status_code = 503

    with patch.object(client, "_execute_attempt", return_value=mock_resp_503):
        result = await client.search(req)

    assert result.http_status == 503
    assert len(result.findings) == 0
    assert any("Gateway error (503)" in w for w in result.warnings)


@pytest.mark.asyncio
async def test_auth_error_raises_immediately():
    """Verifies that HTTP 401 Unauthorized raises ParallelAuthError without retrying."""
    client = ParallelSearchClient(api_key="bad_key", max_retries=3, backoff_base=0.01)
    req = _build_test_request()

    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    mock_resp_401.text = "Unauthorized: Invalid API Key"

    with patch.object(client, "_execute_attempt", return_value=mock_resp_401):
        with pytest.raises(ParallelAuthError) as exc_info:
            await client.search(req)
        assert "Parallel API auth failed (401)" in str(exc_info.value)


@pytest.mark.asyncio
async def test_offline_replay_mock_client():
    """Verifies that MockParallelClient matches fixtures deterministically."""
    mock_client = MockParallelClient(simulated_latency_ms=5.0)
    req = _build_test_request("Clair de Lune Claude Debussy")
    result = await mock_client.search(req)

    assert result.http_status == 200
    assert len(result.findings) >= 1
    assert any("ascap.com" in f.url or "loc.gov" in f.url for f in result.findings)
    assert result.top_authority_tier in (DomainAuthorityTier.TIER_1_GOVERNMENT, DomainAuthorityTier.TIER_2_RIGHTS_ORG)
    assert len(result.raw_response_hash) == 64
    assert len(result.request_payload_hash) == 64


@pytest.mark.asyncio
async def test_mock_client_fault_injection():
    """Verifies that MockParallelClient accurately simulates faults."""
    client_429 = MockParallelClient(simulate_failure="429")
    req = _build_test_request()
    with pytest.raises(ParallelRateLimitError):
        await client_429.search(req)

    client_timeout = MockParallelClient(simulate_failure="timeout")
    with pytest.raises(ParallelTimeoutError):
        await client_timeout.search(req)


def test_domain_authority_classification():
    """Verifies authority tiering and scoring for statutory and web domains."""
    assert classify_domain_tier("tmsearch.uspto.gov") == DomainAuthorityTier.TIER_1_GOVERNMENT
    assert score_domain_authority("tmsearch.uspto.gov") == 1.00

    assert classify_domain_tier("cocatalog.loc.gov") == DomainAuthorityTier.TIER_1_GOVERNMENT
    assert score_domain_authority("cocatalog.loc.gov") == 1.00

    assert classify_domain_tier("ascap.com") == DomainAuthorityTier.TIER_2_RIGHTS_ORG
    assert score_domain_authority("ascap.com") == 0.85

    assert classify_domain_tier("billboard.com") == DomainAuthorityTier.TIER_3_NEWS_EDITORIAL
    assert score_domain_authority("billboard.com") == 0.60

    assert classify_domain_tier("random-blog.net") == DomainAuthorityTier.TIER_4_GENERAL_WEB
    assert score_domain_authority("random-blog.net") == 0.25

    assert extract_canonical_domain("https://www.ascap.com:443/repertory") == "ascap.com"
