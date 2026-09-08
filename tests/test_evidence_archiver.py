"""Unit and integration tests for EvidenceArchiver and SnapshotStore.
Verifies asynchronous HTTP probes, pre-mortem mitigations, redirect-aware SSRF defense,
registration number extraction enforcement, and historical snapshot provenance.
"""
from __future__ import annotations

from pathlib import Path
import httpx
import pytest

from backend.services.evidence_archiver import EvidenceArchiver, SnapshotStore
from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    CitationRequest,
    EvidenceSnapshot,
    RegistrationExtractionError,
    SSRFSecurityError,
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

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await EvidenceArchiver(store=temp_store, client=client).verify_url_liveness("https://example.com/record")
    assert res.status == CitationLivenessStatus.LIVE and res.http_status == 200 and res.method_used == "HEAD"
    assert res.headers.etag == "w/123" and res.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_pre_mortem_mitigation_403_cloudflare_scraper_block(temp_store: SnapshotStore) -> None:
    """Verifies 403 Forbidden is categorized as LIVE_RESTRICTED to avoid false negative dead alerts."""
    call_methods = []

    def handler(request: httpx.Request) -> httpx.Response:
        call_methods.append(request.method)
        return httpx.Response(403, headers={"Server": "cloudflare", "cf-ray": "9999"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await EvidenceArchiver(store=temp_store, client=client).verify_url_liveness("https://protected-site.com/doc")
    assert res.status == CitationLivenessStatus.LIVE_RESTRICTED and res.method_used == "GET"
    assert call_methods == ["HEAD", "GET"] and res.status.is_live and res.status.is_restricted


@pytest.mark.asyncio
async def test_head_405_fallback_get_success_200(temp_store: SnapshotStore) -> None:
    """Verifies servers rejecting HEAD with 405 fall back to GET."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(405) if request.method == "HEAD" else httpx.Response(200, headers={"Content-Type": "application/pdf"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await EvidenceArchiver(store=temp_store, client=client).verify_url_liveness("https://cdn.example.org/spec.pdf")
    assert res.status == CitationLivenessStatus.LIVE and res.http_status == 200 and res.method_used == "GET"


@pytest.mark.asyncio
async def test_verify_liveness_dead_404_and_timeout(temp_store: SnapshotStore) -> None:
    """Verifies 404 dead endpoints and network timeouts."""
    def h_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as c1:
        res1 = await EvidenceArchiver(store=temp_store, client=c1).verify_url_liveness("https://example.com/missing")
    assert res1.status == CitationLivenessStatus.DEAD

    async with httpx.AsyncClient(transport=httpx.MockTransport(h_timeout)) as c2:
        res2 = await EvidenceArchiver(store=temp_store, client=c2).verify_url_liveness("https://slow.com/data")
    assert res2.status == CitationLivenessStatus.TIMEOUT


@pytest.mark.asyncio
async def test_archive_citation_and_local_roundtrip(temp_store: SnapshotStore) -> None:
    """Verifies archiving computes separate response/content digests, locators, and persists snapshot."""
    html_doc = "<html><body>Registered under US Copyright Office record #PA000456 officially.</body></html>"
    snippet = "#PA000456"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html_doc, headers={"Content-Type": "text/html", "ETag": "alpha-1"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        snapshot = await archiver.archive_citation(
            url="https://publicrecords.copyright.gov/record/456", snippet=snippet,
            fetched_content=html_doc, tenant_id="warner",
        )

    assert snapshot.status == CitationLivenessStatus.LIVE and snapshot.raw_snippet == snippet
    assert snapshot.fetched_content == html_doc and snapshot.content_digest_sha256 != snapshot.response_digest_sha256
    assert snapshot.excerpt_locators["char_start"] == html_doc.find(snippet)
    assert Path(snapshot.storage_path).exists()
    retrieved = await temp_store.get_snapshot(snapshot.snapshot_id, tenant_id="warner")
    assert retrieved is not None and retrieved.content_digest_sha256 == snapshot.content_digest_sha256


@pytest.mark.asyncio
async def test_head_checks_cannot_extract_registration_numbers(temp_store: SnapshotStore) -> None:
    """REQUIREMENT: Note that HEAD checks cannot extract registration numbers."""
    archiver = EvidenceArchiver(store=temp_store)
    head_snapshot = EvidenceSnapshot(
        snapshot_id="snp_head_only", url="https://cocatalog.loc.gov/record/100",
        status=CitationLivenessStatus.LIVE, method_used="HEAD",
        raw_snippet="HTTP HEAD response headers only without body content",
        attributable_provider="catalog_lookup", retrieval_time_utc="2026-09-08T10:00:00Z",
    )
    with pytest.raises(RegistrationExtractionError, match="HEAD checks cannot extract registration numbers"):
        archiver.extract_registration_number_from_snapshot(head_snapshot)

    get_snapshot = EvidenceSnapshot(
        snapshot_id="snp_with_content", url="https://cocatalog.loc.gov/record/100",
        status=CitationLivenessStatus.LIVE, method_used="GET",
        fetched_content="US Copyright catalog renewal certificate TX00045892 registered in 1982.",
        retrieval_time_utc="2026-09-08T10:00:00Z",
    )
    assert archiver.extract_registration_number_from_snapshot(get_snapshot) == "TX00045892"


@pytest.mark.asyncio
async def test_historical_snapshots_retain_timestamps_and_label(temp_store: SnapshotStore) -> None:
    """REQUIREMENT: Historical snapshots must exist, retain their original timestamps, and be labeled historical."""
    original_ts = "1978-04-12T14:20:00Z"
    archiver = EvidenceArchiver(store=temp_store)
    snap = await archiver.archive_historical_snapshot(
        url="https://loc.gov/historical/entry/1978",
        snippet="LOC copyright registration #B-1946-8821 lapsed without renewal in 1974.",
        original_retrieval_time_utc=original_ts, tenant_id="paramount",
        fetched_content="Full public domain historical gazette entry for B-1946-8821.",
    )
    assert snap.is_historical is True and snap.historical_label == "historical"
    assert snap.retrieval_time_utc == original_ts and snap.original_retrieval_time_utc == original_ts
    assert Path(snap.storage_path).exists()
    loaded = await temp_store.get_snapshot(snap.snapshot_id, tenant_id="paramount")
    assert loaded is not None and loaded.is_historical is True and loaded.retrieval_time_utc == original_ts


@pytest.mark.asyncio
async def test_ssrf_redirect_hop_protection(temp_store: SnapshotStore) -> None:
    """REQUIREMENT: Follow redirects with destination IP validation on each hop; block cloud metadata."""
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://legit-site.org/start":
            return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"})
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        res = await archiver.verify_url_liveness("https://legit-site.org/start")
        assert res.status == CitationLivenessStatus.ERROR and "169.254.169.254" in (res.error_detail or "")
        with pytest.raises(SSRFSecurityError, match="169.254.169.254"):
            await archiver.archive_citation(url="https://legit-site.org/start", snippet="Exploit attempt")


@pytest.mark.asyncio
async def test_ssrf_direct_and_redirect_to_rfc1918(temp_store: SnapshotStore) -> None:
    """REQUIREMENT: Block RFC 1918 addresses on direct requests and redirect hops."""
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://external.org/bounce":
            return httpx.Response(301, headers={"Location": "http://10.0.0.1/admin"})
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        with pytest.raises(SSRFSecurityError, match="10.0.0.1"):
            await archiver.archive_citation(url="http://10.0.0.1/admin", snippet="Local admin access")
        with pytest.raises(SSRFSecurityError, match="10.0.0.1"):
            await archiver.archive_citation(url="https://external.org/bounce", snippet="Bounced to private")


@pytest.mark.asyncio
async def test_snapshot_store_gcs_and_fallback(tmp_path: Path) -> None:
    """Verifies SnapshotStore canonical GCS path schema and fallback to local disk."""
    store = SnapshotStore(base_dir=str(tmp_path / "fallback"), enable_gcs=True, gcs_client=None)
    assert store.get_gcs_bucket_path("disney") == "gs://lienmark-disney-evidence-snapshots/"
    snapshot = EvidenceSnapshot(
        snapshot_id="snp_mock1", url="https://example.com/record", status=CitationLivenessStatus.LIVE,
        raw_snippet="Snippet text", attributable_provider="fixture_provider",
        retrieved_at_utc="2026-09-07T11:00:00Z", payload_digest_sha256="abc123hash", tenant_id="disney",
    )
    path = await store.save_snapshot(snapshot)
    assert "fallback" in path and Path(path).exists()


@pytest.mark.asyncio
async def test_archive_batch(temp_store: SnapshotStore) -> None:
    """Verifies concurrent non-blocking archiving of multiple citations."""
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="Batch item body"))) as client:
        archiver = EvidenceArchiver(store=temp_store, client=client)
        requests = [
            CitationRequest(url="https://site1.org/item", snippet="Snippet 1", tenant_id="tenantA"),
            CitationRequest(url="https://site2.org/item", snippet="Snippet 2", tenant_id="tenantB"),
        ]
        results = await archiver.archive_batch(requests, concurrency_limit=2)
    assert len(results) == 2 and results[0].content_digest_sha256 != results[1].content_digest_sha256
