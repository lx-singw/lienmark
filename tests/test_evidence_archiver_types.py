"""Unit tests for evidence_archiver_types.py domain models, status enums, hashing, and SSRF validation."""
from __future__ import annotations

import hashlib
import pytest
from pydantic import ValidationError

from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    EvidenceArchiverConfig,
    EvidenceSnapshot,
    SnapshotHttpHeaders,
    SSRFSecurityError,
    compute_payload_digest,
    validate_url_ssrf,
    CITATION_LIVE,
    CITATION_LIVE_RESTRICTED,
    CITATION_DEAD_404,
    CITATION_ERROR,
    CITATION_TIMEOUT,
)


def test_citation_liveness_status_values_and_aliases() -> None:
    """Verifies canonical status values and pre-mortem compliance aliases."""
    assert CitationLivenessStatus.LIVE == "LIVE"
    assert CitationLivenessStatus.LIVE_RESTRICTED == "LIVE_RESTRICTED"
    assert CitationLivenessStatus.DEAD == "DEAD"
    assert CitationLivenessStatus.ERROR == "ERROR"
    assert CitationLivenessStatus.TIMEOUT == "TIMEOUT"
    assert CITATION_LIVE == CitationLivenessStatus.LIVE
    assert CITATION_LIVE_RESTRICTED == CitationLivenessStatus.LIVE_RESTRICTED
    assert CITATION_DEAD_404 == CitationLivenessStatus.DEAD
    assert CITATION_ERROR == CitationLivenessStatus.ERROR
    assert CITATION_TIMEOUT == CitationLivenessStatus.TIMEOUT


def test_citation_liveness_properties_and_mitigation() -> None:
    """Verifies 401/403 live-restricted endpoints are classified as live and distinct from dead."""
    live = CitationLivenessStatus.LIVE
    restricted = CitationLivenessStatus.LIVE_RESTRICTED
    dead = CitationLivenessStatus.DEAD
    assert live.is_live and not live.is_restricted and not live.is_dead
    assert restricted.is_live and restricted.is_restricted and not restricted.is_dead
    assert not dead.is_live and not dead.is_restricted and dead.is_dead


def test_compute_payload_digest() -> None:
    """Verifies SHA-256 hex digest computation for raw text payloads."""
    raw_text = "Copyright 1984 Paramount Pictures. Registered under TX00012345."
    expected_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    digest = compute_payload_digest(raw_text)
    assert digest == expected_hash
    assert len(digest) == 64
    assert compute_payload_digest("") == hashlib.sha256(b"").hexdigest()


def test_evidence_snapshot_instantiation_and_validation() -> None:
    """Verifies EvidenceSnapshot model contracts, serialization, and header parsing."""
    headers = SnapshotHttpHeaders(
        content_type="text/html; charset=utf-8",
        last_modified="Wed, 21 Oct 2025 07:28:00 GMT",
        etag='"33a64df551425fcc"',
        raw_headers={"server": "cloudflare", "cf-ray": "8234abc12345"},
    )
    raw_snippet = "Official copyright catalog entry for Casablanca (1942)."
    digest = compute_payload_digest(raw_snippet)
    snapshot = EvidenceSnapshot(
        snapshot_id="snp_abc123",
        url="https://cocatalog.loc.gov/record/123",
        status=CitationLivenessStatus.LIVE,
        http_status=200,
        raw_snippet=raw_snippet,
        attributable_provider="USCO",
        headers=headers,
        retrieved_at_utc="2026-09-07T11:00:00Z",
        payload_digest_sha256=digest,
        latency_ms=45.2,
        method_used="HEAD",
        tenant_id="paramount",
    )
    dumped_json = snapshot.model_dump_json()
    restored = EvidenceSnapshot.model_validate_json(dumped_json)
    assert restored.snapshot_id == "snp_abc123"
    assert restored.status == CitationLivenessStatus.LIVE
    assert restored.headers.etag == '"33a64df551425fcc"'
    assert restored.payload_digest_sha256 == digest
    assert restored.attributable_provider == "USCO"
    assert restored.final_url == "https://cocatalog.loc.gov/record/123"
    assert "char_start" in restored.excerpt_locators


def test_evidence_snapshot_requires_content_or_provider() -> None:
    """Verifies EvidenceSnapshot rejects instances missing both fetched content and attributable provider."""
    with pytest.raises(ValidationError, match="Requires fetched_content or attributable provider"):
        EvidenceSnapshot(
            snapshot_id="snp_invalid",
            url="https://example.com/data",
            status=CitationLivenessStatus.LIVE,
            raw_snippet="Bare snippet without provider or fetched content",
            retrieved_at_utc="2026-09-08T10:00:00Z",
        )


def test_validate_url_ssrf_blocks_private_loopback_metadata_and_ipv6() -> None:
    """Verifies redirect-aware SSRF protection blocks RFC 1918, loopback, link-local, metadata, and IPv6."""
    blocked_urls = [
        "http://10.0.0.1/admin",
        "http://172.16.5.4:8080/data",
        "http://192.168.1.1/setup",
        "http://127.0.0.1:8000/info",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://service.corp.internal/api",
        "http://[::1]/secret",
        "http://[fe80::1]/linklocal",
        "http://[::ffff:169.254.169.254]/metadata",
        "http://[::ffff:127.0.0.1]/status",
        "http://localhost:3000/",
    ]
    for url in blocked_urls:
        with pytest.raises(SSRFSecurityError):
            validate_url_ssrf(url)
    validate_url_ssrf("https://example.com/record")


def test_historical_snapshot_label_and_timestamp_preservation() -> None:
    """Verifies historical snapshots retain their original timestamps and are labeled historical."""
    original_ts = "2024-01-15T08:30:00Z"
    snapshot = EvidenceSnapshot(
        snapshot_id="snp_hist_01",
        url="https://archive.org/item/1924_script",
        status=CitationLivenessStatus.LIVE,
        fetched_content="Full historical script text of 1924 silent film.",
        raw_snippet="Historical script excerpt.",
        is_historical=True,
        original_retrieval_time_utc=original_ts,
        retrieval_time_utc=original_ts,
    )
    assert snapshot.is_historical is True
    assert snapshot.historical_label == "historical"
    assert snapshot.retrieval_time_utc == original_ts
    assert snapshot.original_retrieval_time_utc == original_ts
    assert snapshot.response_digest_sha256 is not None
    assert snapshot.content_digest_sha256 != snapshot.response_digest_sha256


def test_config_defaults() -> None:
    """Verifies default values for EvidenceArchiverConfig."""
    cfg = EvidenceArchiverConfig()
    assert cfg.timeout_seconds == 4.0
    assert "clearance-audit" in cfg.user_agent
    assert cfg.local_storage_dir == "output/evidence_snapshots"
    assert cfg.gcs_bucket_template == "lienmark-{tenant}-evidence-snapshots"
    assert cfg.enable_gcs is False
    assert cfg.max_concurrency == 10
    assert cfg.max_redirects == 10
