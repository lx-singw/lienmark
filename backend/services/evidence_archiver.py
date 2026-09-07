"""
evidence_archiver.py

Asynchronous Evidence Snapshot Archiver and citation URL liveness verification.
Enforces Cloudflare/paywall pre-mortem mitigations and dual GCS/local snapshot storage.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid

import httpx

from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    CitationRequest,
    EvidenceArchiverConfig,
    EvidenceArchiverError,
    EvidenceSnapshot,
    InvalidCitationUrlError,
    LivenessVerificationResult,
    SnapshotHttpHeaders,
    SnapshotStorageError,
    compute_payload_digest,
)
from backend.services.snapshot_store import SnapshotStore

logger = logging.getLogger("lienmark.services.evidence_archiver")


class EvidenceArchiver:
    """
    Evidence verification and snapshot archiver service.
    Verifies citation URLs using HEAD and fallback GET with scraper pre-mortem classification.
    """

    def __init__(
        self,
        config: Optional[EvidenceArchiverConfig] = None,
        store: Optional[SnapshotStore] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.config = config or EvidenceArchiverConfig()
        self.store = store or SnapshotStore(
            base_dir=self.config.local_storage_dir,
            bucket_template=self.config.gcs_bucket_template,
            enable_gcs=self.config.enable_gcs,
        )
        self._client = client

    @staticmethod
    def _classify_status(code: int) -> CitationLivenessStatus:
        """Maps HTTP status code to domain status with scraper anti-bot mitigation."""
        if 200 <= code < 400:
            return CitationLivenessStatus.LIVE
        if code in (401, 403):
            return CitationLivenessStatus.LIVE_RESTRICTED
        if code in (404, 410):
            return CitationLivenessStatus.DEAD
        if 500 <= code < 600:
            return CitationLivenessStatus.ERROR
        return CitationLivenessStatus.DEAD if (400 <= code < 500) else CitationLivenessStatus.ERROR

    @staticmethod
    def _extract_headers(resp: httpx.Response) -> SnapshotHttpHeaders:
        """Extracts and normalizes caching and provenance headers from response."""
        return SnapshotHttpHeaders(
            content_type=resp.headers.get("content-type"),
            last_modified=resp.headers.get("last-modified"),
            etag=resp.headers.get("etag"),
            raw_headers={
                k.lower(): v for k, v in resp.headers.items()
                if k.lower() in ("content-type", "last-modified", "etag", "server", "cf-ray", "date")
            },
        )

    async def _send_request(
        self, client: httpx.AsyncClient, method: str, url: str, timeout: float
    ) -> Tuple[Optional[httpx.Response], Optional[Exception]]:
        """Executes a single HTTP request defensively."""
        headers = {"User-Agent": self.config.user_agent}
        try:
            resp = await client.request(method, url, headers=headers, timeout=timeout, follow_redirects=True)
            return resp, None
        except Exception as exc:
            return None, exc

    async def _execute_liveness_probes(
        self, client: httpx.AsyncClient, url: str, timeout: float, start: float
    ) -> Tuple[Optional[httpx.Response], Optional[Exception], str]:
        """Executes HEAD probe with conditional fallback GET."""
        resp, exc = await self._send_request(client, "HEAD", url, timeout)
        method_used = "HEAD"
        need_fallback = exc is not None or (resp is not None and resp.status_code in (400, 401, 403, 404, 405, 501))

        if need_fallback and not isinstance(exc, httpx.TimeoutException):
            rem_timeout = max(0.5, timeout - (time.perf_counter() - start))
            get_resp, get_exc = await self._send_request(client, "GET", url, rem_timeout)
            if get_resp is not None or get_exc is not None:
                resp, exc = get_resp, get_exc
                method_used = "GET"
        return resp, exc, method_used

    async def verify_url_liveness(
        self, url: str, timeout_seconds: Optional[float] = None
    ) -> LivenessVerificationResult:
        """
        Asynchronously verifies citation URL liveness with HEAD and fallback GET.
        Categorizes 401/403 as LIVE_RESTRICTED to prevent false negative dead-link alerts.
        """
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return LivenessVerificationResult(
                url=url or "",
                status=CitationLivenessStatus.DEAD,
                error_detail="Invalid URL scheme; must begin with http:// or https://",
            )

        timeout = timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
        start = time.perf_counter()
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()

        try:
            resp, exc, method_used = await self._execute_liveness_probes(client, url, timeout, start)
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            if isinstance(exc, httpx.TimeoutException):
                return LivenessVerificationResult(url=url, status=CitationLivenessStatus.TIMEOUT, latency_ms=latency_ms)
            if exc is not None or resp is None:
                return LivenessVerificationResult(
                    url=url, status=CitationLivenessStatus.ERROR, latency_ms=latency_ms, error_detail=str(exc)
                )

            return LivenessVerificationResult(
                url=url,
                status=self._classify_status(resp.status_code),
                http_status=resp.status_code,
                latency_ms=latency_ms,
                method_used=method_used,
                headers=self._extract_headers(resp),
            )
        finally:
            if owns_client:
                await client.aclose()

    async def archive_citation(
        self,
        url: str,
        snippet: str,
        tenant_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceSnapshot:
        """Verifies citation liveness, hashes payload, and stores immutable snapshot."""
        verification = await self.verify_url_liveness(url)
        snapshot = EvidenceSnapshot(
            snapshot_id=f"snp_{uuid.uuid4().hex[:16]}",
            url=url,
            status=verification.status,
            http_status=verification.http_status,
            raw_snippet=snippet,
            headers=verification.headers,
            retrieved_at_utc=verification.checked_at_utc,
            payload_digest_sha256=compute_payload_digest(snippet),
            latency_ms=verification.latency_ms,
            method_used=verification.method_used,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )
        await self.store.save_snapshot(snapshot)
        return snapshot

    async def archive_batch(
        self,
        citations: Sequence[CitationRequest],
        concurrency_limit: Optional[int] = None,
    ) -> List[EvidenceSnapshot]:
        """Archives a batch of citations concurrently with bounded concurrency."""
        limit = concurrency_limit or self.config.max_concurrency
        semaphore = asyncio.Semaphore(limit)

        async def _worker(req: CitationRequest) -> EvidenceSnapshot:
            async with semaphore:
                return await self.archive_citation(req.url, req.snippet, req.tenant_id, req.metadata)

        return list(await asyncio.gather(*[_worker(c) for c in citations]))


__all__ = ["EvidenceArchiver", "SnapshotStore"]
