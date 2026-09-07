"""
backend/services/parallel_client.py

Asynchronous HTTP client for the Parallel Search API v1.
Features: HTTP/2 with fallback, TLS verification, jittered exponential backoff,
latency tracking, SHA-256 payload hashing, and fail-closed safety.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import time
from typing import Any, Callable, Dict, List, Optional
import httpx

from backend.services.domain_authority import (
    classify_domain_tier,
    extract_canonical_domain,
    score_domain_authority,
)
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelAuthError,
    ParallelClientError,
    ParallelRateLimitError,
    ParallelSearchFinding,
    ParallelSearchRequest,
    ParallelSearchResult,
    ParallelServerError,
    ParallelTimeoutError,
    ParallelValidationError,
)

logger = logging.getLogger("lienmark.parallel.client")


def _is_http2_supported() -> bool:
    """Checks if h2 dependency is installed for HTTP/2 support."""
    try:
        import h2  # noqa: F401
        return True
    except ImportError:
        return False


class ParallelSearchClient:
    """Production asynchronous client for Parallel Search API v1."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
        backoff_base: float = 0.25,
        telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.base_url = base_url or os.getenv("PARALLEL_API_URL", "https://api.parallel.ai/v1/search")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.telemetry_callback = telemetry_callback
        self.http2_enabled = _is_http2_supported()

    def _build_headers(self) -> Dict[str, str]:
        """Constructs headers conforming to Parallel v1 authentication specifications."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Lienmark-Rights-Clearance/1.0",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _calculate_delay(self, attempt: int, retry_after: Optional[str]) -> float:
        """Calculates backoff delay in seconds with full jitter or parsed Retry-After."""
        if retry_after:
            try:
                val = float(retry_after)
                if 0.0 < val <= 30.0:
                    return val
            except ValueError:
                pass
        exponential = min(4.0, self.backoff_base * (2 ** attempt))
        jitter = random.uniform(0.01, 0.08)
        return exponential + jitter

    def _parse_findings(self, results: List[Dict[str, Any]]) -> List[ParallelSearchFinding]:
        """Maps raw API result records into validated ParallelSearchFinding instances."""
        findings: List[ParallelSearchFinding] = []
        for r in results:
            url = str(r.get("url") or "").strip()
            if not url:
                continue
            domain = extract_canonical_domain(url)
            tier = classify_domain_tier(domain)
            score = score_domain_authority(domain)
            excerpts = [str(x).strip() for x in r.get("excerpts", []) if str(x).strip()]
            findings.append(
                ParallelSearchFinding(
                    url=url,
                    title=str(r.get("title") or domain),
                    domain=domain,
                    publish_date=r.get("publish_date"),
                    excerpts=excerpts,
                    full_excerpt="\n".join(excerpts),
                    authority_tier=tier,
                    authority_score=score,
                    confidence_score=min(1.0, 0.40 + (score * 0.60)),
                )
            )
        return findings

    def _parse_response(
        self,
        raw_bytes: bytes,
        latency_ms: float,
        req_hash: str,
        http_status: int,
    ) -> ParallelSearchResult:
        """Parses response JSON, extracts findings, and computes cryptographic hashes."""
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            data = {}
        findings = self._parse_findings(data.get("results", []))
        top_tier = (
            min((f.authority_tier for f in findings), key=lambda t: t.value, default=DomainAuthorityTier.TIER_4_GENERAL_WEB)
            if findings else DomainAuthorityTier.TIER_4_GENERAL_WEB
        )
        return ParallelSearchResult(
            search_id=str(data.get("search_id") or ""),
            session_id=data.get("session_id"),
            findings=findings,
            raw_response_hash=raw_hash,
            request_payload_hash=req_hash,
            latency_ms=latency_ms,
            http_status=http_status,
            top_authority_tier=top_tier,
        )

    def _build_fail_closed_result(
        self, req_hash: str, latency_ms: float, status: int, warning: str
    ) -> ParallelSearchResult:
        """Emits a safe fail-closed result when upstream requests fail or exhaust retries."""
        return ParallelSearchResult(
            search_id="fail_closed_provider_error",
            findings=[],
            raw_response_hash="0" * 64,
            request_payload_hash=req_hash,
            latency_ms=latency_ms,
            http_status=status,
            warnings=[warning],
        )

    async def _execute_attempt(
        self, client: httpx.AsyncClient, payload: Dict[str, Any], headers: Dict[str, str]
    ) -> httpx.Response:
        """Executes a single HTTP POST request to Parallel API endpoint."""
        return await client.post(
            self.base_url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

    async def _handle_response_attempt(
        self, resp: httpx.Response, attempt: int
    ) -> tuple[Optional[bytes], int, str]:
        """Evaluates response status, returning (content, status, warning) or raising."""
        if resp.status_code == 200:
            return resp.content, 200, ""
        if resp.status_code == 429:
            delay = self._calculate_delay(attempt, resp.headers.get("retry-after"))
            await asyncio.sleep(delay)
            return None, 429, f"Rate limited (429) on attempt {attempt + 1}"
        if resp.status_code in (500, 502, 503, 504):
            delay = self._calculate_delay(attempt, None)
            await asyncio.sleep(delay)
            return None, resp.status_code, f"Gateway error ({resp.status_code}) on attempt {attempt + 1}"
        if resp.status_code in (401, 403):
            raise ParallelAuthError(f"Parallel API auth failed ({resp.status_code}): {resp.text}")
        raise ParallelClientError(f"Parallel API error ({resp.status_code}): {resp.text}")

    async def search(self, request: ParallelSearchRequest) -> ParallelSearchResult:
        """
        Executes an asynchronous search with exponential backoff and jitter.
        Applies fail-closed fallback on rate limits, timeouts, or server drops.
        """
        payload = request.to_api_payload()
        req_hash = request.compute_payload_hash()
        headers = self._build_headers()
        start = time.perf_counter()
        last_status = 500
        last_warning = "Retries exhausted"

        async with httpx.AsyncClient(verify=True, http2=self.http2_enabled) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await self._execute_attempt(client, payload, headers)
                    content, last_status, last_warning = await self._handle_response_attempt(resp, attempt)
                    if content is not None:
                        elapsed = (time.perf_counter() - start) * 1000.0
                        return self._parse_response(content, elapsed, req_hash, 200)
                except (httpx.TimeoutException, asyncio.TimeoutError):
                    last_status = 504
                    last_warning = f"Timeout ({self.timeout}s) on attempt {attempt + 1}"
                    await asyncio.sleep(self._calculate_delay(attempt, None))
                except (ParallelAuthError, ParallelClientError):
                    raise
                except Exception as e:
                    last_warning = f"Transport error on attempt {attempt + 1}: {e}"
                    await asyncio.sleep(self._calculate_delay(attempt, None))

        elapsed = (time.perf_counter() - start) * 1000.0
        return self._build_fail_closed_result(req_hash, elapsed, last_status, last_warning)
