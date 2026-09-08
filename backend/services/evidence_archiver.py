"""evidence_archiver.py
Asynchronous Evidence Archiver and citation verification with redirect-aware SSRF defense.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin
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
    RegistrationExtractionError,
    SnapshotHttpHeaders,
    SSRFSecurityError,
    compute_payload_digest,
    validate_url_ssrf,
)
from backend.services.snapshot_store import SnapshotStore

logger = logging.getLogger("lienmark.services.evidence_archiver")
REG_REGEX = re.compile(r"\b(?:(?:TX|PA|VA|SR|RE|B)[- ]?\d{4,8}|\d{7,8}|[A-Z]{1,3}-\d{4}-\d{4,8})\b", re.IGNORECASE)


class EvidenceArchiver:
    """Evidence verification and snapshot archiver with redirect-aware SSRF protection."""

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

    async def _send_hop(
        self, client: httpx.AsyncClient, method: str, url: str, timeout: float
    ) -> httpx.Response:
        """Executes a single hop validating SSRF boundaries."""
        validate_url_ssrf(url)
        return await client.request(
            method, url, headers={"User-Agent": self.config.user_agent},
            timeout=timeout, follow_redirects=False
        )

    async def _follow_redirects(
        self, client: httpx.AsyncClient, method: str, url: str, timeout: float, start: float
    ) -> Tuple[Optional[httpx.Response], str, int, Optional[Exception]]:
        """Follows redirects with destination IP validation on each hop."""
        curr_url, hops = url, 0
        while hops <= self.config.max_redirects:
            rem = max(0.5, timeout - (time.perf_counter() - start))
            try:
                resp = await self._send_hop(client, method, curr_url, rem)
                if resp.is_redirect and "location" in resp.headers:
                    curr_url = urljoin(curr_url, resp.headers["location"])
                    hops += 1
                    continue
                return resp, curr_url, hops, None
            except Exception as exc:
                return None, curr_url, hops, exc
        return None, curr_url, hops, EvidenceArchiverError(f"Exceeded max redirects ({self.config.max_redirects})")

    async def _probe(
        self, client: httpx.AsyncClient, url: str, timeout: float, start: float
    ) -> Tuple[Optional[httpx.Response], str, int, Optional[Exception], str]:
        """Probes URL with HEAD and fallback GET, validating redirects for SSRF."""
        resp, f_url, hops, exc = await self._follow_redirects(client, "HEAD", url, timeout, start)
        method = "HEAD"
        need_fallback = exc is not None or (resp is not None and resp.status_code in (400, 401, 403, 404, 405, 501))
        if need_fallback and not isinstance(exc, (httpx.TimeoutException, SSRFSecurityError)):
            rem = max(0.5, timeout - (time.perf_counter() - start))
            g_resp, g_url, g_hops, g_exc = await self._follow_redirects(client, "GET", url, rem, start)
            if g_resp is not None or g_exc is not None:
                resp, f_url, hops, exc = g_resp, g_url, hops + g_hops, g_exc
                method = "GET"
        return resp, f_url, hops, exc, method

    async def verify_url_liveness(
        self, url: str, timeout_seconds: Optional[float] = None
    ) -> LivenessVerificationResult:
        """Asynchronously verifies URL liveness with redirect-aware SSRF protection."""
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return LivenessVerificationResult(
                url=url or "", status=CitationLivenessStatus.DEAD,
                error_detail="Invalid URL scheme; must begin with http:// or https://",
            )
        start, timeout = time.perf_counter(), timeout_seconds or self.config.timeout_seconds
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            resp, f_url, hops, exc, method = await self._probe(client, url, timeout, start)
            lat = round((time.perf_counter() - start) * 1000.0, 2)
            if isinstance(exc, httpx.TimeoutException):
                return LivenessVerificationResult(url=url, final_url=f_url, status=CitationLivenessStatus.TIMEOUT, latency_ms=lat)
            if exc is not None or resp is None:
                return LivenessVerificationResult(
                    url=url, final_url=f_url, status=CitationLivenessStatus.ERROR,
                    latency_ms=lat, error_detail=str(exc), redirect_count=hops
                )
            body = resp.text if method == "GET" else None
            return LivenessVerificationResult(
                url=url, final_url=f_url, status=self._classify_status(resp.status_code),
                http_status=resp.status_code, latency_ms=lat, method_used=method,
                headers=self._extract_headers(resp), redirect_count=hops, fetched_body=body
            )
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def extract_registration_number_from_snapshot(snapshot: EvidenceSnapshot) -> str:
        """HEAD checks cannot extract registration numbers; body content or extraction is required."""
        if snapshot.method_used == "HEAD" and not snapshot.fetched_content and not snapshot.provider_extraction:
            raise RegistrationExtractionError("HEAD checks cannot extract registration numbers.")
        source = snapshot.fetched_content or snapshot.provider_extraction or snapshot.raw_snippet or ""
        match = REG_REGEX.search(source)
        if not match:
            raise RegistrationExtractionError("No registration number found in evidence content.")
        return match.group(0)

    @staticmethod
    def compute_locators(snippet: str, content: str) -> Dict[str, Any]:
        """Calculates character offset excerpt locators within source content."""
        if snippet and content and snippet in content:
            idx = content.find(snippet)
            return {"char_start": idx, "char_end": idx + len(snippet), "type": "exact"}
        return {"char_start": 0, "char_end": len(snippet), "type": "snippet"}

    async def archive_citation(
        self,
        url: str,
        snippet: str,
        tenant_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        fetched_content: Optional[str] = None,
        provider_extraction: Optional[str] = None,
        attributable_provider: Optional[str] = None,
        excerpt_locators: Optional[Dict[str, Any]] = None,
        is_historical: bool = False,
        historical_timestamp: Optional[str] = None,
    ) -> EvidenceSnapshot:
        """Archives citation requiring fetched content or attributable extraction, digests, and SSRF check."""
        validate_url_ssrf(url)
        v = await self.verify_url_liveness(url)
        if v.error_detail and "SSRF blocked" in v.error_detail:
            raise SSRFSecurityError(v.error_detail)
        body = fetched_content or v.fetched_body
        final_url = v.final_url or url
        prov_ext = provider_extraction or (snippet if not body else None)
        attr_prov = attributable_provider or ("search_provider" if prov_ext and not body else None)
        locators = excerpt_locators or self.compute_locators(snippet, body or prov_ext or "")
        ret_time = historical_timestamp if (is_historical and historical_timestamp) else v.checked_at_utc
        snapshot = EvidenceSnapshot(
            snapshot_id=f"snp_{uuid.uuid4().hex[:16]}", url=url, final_url=final_url,
            status=v.status, http_status=v.http_status, raw_snippet=snippet,
            fetched_content=body, provider_extraction=prov_ext, attributable_provider=attr_prov,
            excerpt_locators=locators, retrieval_time_utc=ret_time,
            response_digest_sha256=compute_payload_digest(body) if body else None,
            content_digest_sha256=compute_payload_digest(snippet),
            headers=v.headers, latency_ms=v.latency_ms, method_used=v.method_used,
            tenant_id=tenant_id, is_historical=is_historical,
            historical_label="historical" if is_historical else None,
            original_retrieval_time_utc=ret_time if is_historical else None,
            metadata=metadata or {},
        )
        await self.store.save_snapshot(snapshot)
        return snapshot

    async def archive_historical_snapshot(
        self,
        url: str,
        snippet: str,
        original_retrieval_time_utc: str,
        tenant_id: str = "default",
        fetched_content: Optional[str] = None,
        provider_extraction: Optional[str] = None,
        attributable_provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceSnapshot:
        """Creates and stores a historical snapshot retaining original timestamp and historical label."""
        return await self.archive_citation(
            url=url, snippet=snippet, tenant_id=tenant_id, metadata=metadata,
            fetched_content=fetched_content, provider_extraction=provider_extraction,
            attributable_provider=attributable_provider or "historical_archive",
            is_historical=True, historical_timestamp=original_retrieval_time_utc,
        )

    async def archive_batch(
        self, citations: Sequence[CitationRequest], concurrency_limit: Optional[int] = None
    ) -> List[EvidenceSnapshot]:
        """Archives a batch of citations concurrently with bounded concurrency."""
        sem = asyncio.Semaphore(concurrency_limit or self.config.max_concurrency)

        async def _w(r: CitationRequest) -> EvidenceSnapshot:
            async with sem:
                return await self.archive_citation(
                    r.url, r.snippet, r.tenant_id, r.metadata, r.fetched_content,
                    r.provider_extraction, r.attributable_provider, r.excerpt_locators,
                    r.is_historical, r.historical_timestamp,
                )

        return list(await asyncio.gather(*[_w(c) for c in citations]))


__all__ = ["EvidenceArchiver", "SnapshotStore"]
