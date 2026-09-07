"""
Unit and integration tests for EvidenceArchiver and SnapshotStore.
Verifies asynchronous HTTP HEAD/GET state machine, anti-scraper pre-mortem mitigations,
dual GCS/local fallback storage, and millisecond latency telemetry.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock
import httpx
import pytest

from backend.services.evidence_archiver import EvidenceArchiver, SnapshotStore
from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    CitationRequest,
    EvidenceArchiverConfig,
    EvidenceSnapshot,
)


@pytest.fixture
def temp_store(tmp_path: Path) -> SnapshotStore:
    """Provides an isolated local SnapshotStore in a temporary directory."""
    return SnapshotStore(base_dir=str(tmp_path / "evidence_snapshots"))


@pytest.mark.asyncio
async def test_verify_liveness_head_success_200(temp_store: SnapshotStore) -> None:
    """Verifies direct 200 response via HEAD classifies as LIVE."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "HEAD"
        return httpx.Response(200, headers={"Content-Type": "text/html", "ETag": "w/123"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        result = await archiver.verify_url_liveness("https://example.com/record")

    assert result.status == CitationLivenessStatus.LIVE
    assert result.http_status == 200
    assert result.method_used == "HEAD"
    assert result.headers.etag == "w/123"
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_pre_mortem_mitigation_403_cloudflare_scraper_block(temp_store: SnapshotStore) -> None:
    """
    PRE-MORTEM MITIGATION:
    Sites returning 403 Forbidden or 401 Unauthorized (e.g. Cloudflare, paywalls)
    MUST be categorized as LIVE_RESTRICTED rather than DEAD to prevent false negative alerts.
    """
    call_methods = []

    def handler(request: httpx.Request) -> httpx.Response:
        call_methods.append(request.method)
        return httpx.Response(403, headers={"Server": "cloudflare", "cf-ray": "9999"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        result = await archiver.verify_url_liveness("https://protected-site.com/doc")

    assert result.status == CitationLivenessStatus.LIVE_RESTRICTED
    assert result.http_status == 403
    assert result.method_used == "GET"
    assert call_methods == ["HEAD", "GET"]
    assert result.status.is_live is True
    assert result.status.is_restricted is True
    assert result.status.is_dead is False


@pytest.mark.asyncio
async def test_head_405_fallback_get_success_200(temp_store: SnapshotStore) -> None:
    """Verifies servers that reject HEAD with 405 gracefully fall back to GET."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(405)
        return httpx.Response(200, headers={"Content-Type": "application/pdf"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        result = await archiver.verify_url_liveness("https://cdn.example.org/spec.pdf")

    assert result.status == CitationLivenessStatus.LIVE
    assert result.http_status == 200
    assert result.method_used == "GET"


@pytest.mark.asyncio
async def test_verify_liveness_dead_404(temp_store: SnapshotStore) -> None:
    """Verifies 404 Not Found returns DEAD status."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        result = await archiver.verify_url_liveness("https://example.com/missing")

    assert result.status == CitationLivenessStatus.DEAD
    assert result.http_status == 404
    assert result.status.is_dead is True


@pytest.mark.asyncio
async def test_verify_liveness_timeout(temp_store: SnapshotStore) -> None:
    """Verifies network timeouts are categorized as TIMEOUT."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out after 4.0s")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        result = await archiver.verify_url_liveness("https://slow.com/data", timeout_seconds=4.0)

    assert result.status == CitationLivenessStatus.TIMEOUT
    assert result.http_status is None


@pytest.mark.asyncio
async def test_archive_citation_and_local_roundtrip(temp_store: SnapshotStore) -> None:
    """Verifies archiving a citation computes SHA-256 and persists snapshot to disk."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"ETag": "alpha-1"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        snippet = "Original script registered with US Copyright Office #PA000456"
        snapshot = await archiver.archive_citation(
            url="https://publicrecords.copyright.gov/record/456",
            snippet=snippet,
            tenant_id="warner",
        )

    assert snapshot.status == CitationLivenessStatus.LIVE
    assert snapshot.raw_snippet == snippet
    assert len(snapshot.payload_digest_sha256) == 64
    assert snapshot.storage_path is not None
    assert Path(snapshot.storage_path).exists()

    retrieved = await temp_store.get_snapshot(snapshot.snapshot_id, tenant_id="warner")
    assert retrieved is not None
    assert retrieved.snapshot_id == snapshot.snapshot_id
    assert retrieved.payload_digest_sha256 == snapshot.payload_digest_sha256


@pytest.mark.asyncio
async def test_snapshot_store_gcs_and_fallback(tmp_path: Path) -> None:
    """Verifies SnapshotStore canonical GCS path schema and fallback to local disk."""
    store = SnapshotStore(base_dir=str(tmp_path / "fallback"), enable_gcs=True, gcs_client=None)
    assert store.get_gcs_bucket_path("disney") == "gs://lienmark-disney-evidence-snapshots/"

    # When GCS client is None or fails, falls back safely to local filesystem
    snapshot = EvidenceSnapshot(
        snapshot_id="snp_mock1",
        url="https://example.com/record",
        status=CitationLivenessStatus.LIVE,
        raw_snippet="Snippet text",
        retrieved_at_utc="2026-09-07T11:00:00Z",
        payload_digest_sha256="abc123hash",
        tenant_id="disney",
    )
    path = await store.save_snapshot(snapshot)
    assert "fallback" in path
    assert Path(path).exists()


@pytest.mark.asyncio
async def test_archive_batch(temp_store: SnapshotStore) -> None:
    """Verifies concurrent non-blocking archiving of multiple citations."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        requests = [
            CitationRequest(url="https://site1.org/item", snippet="Snippet 1", tenant_id="tenantA"),
            CitationRequest(url="https://site2.org/item", snippet="Snippet 2", tenant_id="tenantB"),
        ]
        results = await archiver.archive_batch(requests, concurrency_limit=2)

    assert len(results) == 2
    assert results[0].url == "https://site1.org/item"
    assert results[1].url == "https://site2.org/item"
    assert results[0].payload_digest_sha256 != results[1].payload_digest_sha256
