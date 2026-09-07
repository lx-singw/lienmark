"""
Unit tests for evidence_archiver_types.py domain models, status enums, and hashing.
"""

from __future__ import annotations

import hashlib
import pytest

from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    CitationRequest,
    EvidenceArchiverConfig,
    EvidenceSnapshot,
    LivenessVerificationResult,
    SnapshotHttpHeaders,
    compute_payload_digest,
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
    """
    Verifies properties: 401/403 live-restricted endpoints are considered live
    and distinct from dead 404 endpoints to avoid false negative link warnings.
    """
    live_status = CitationLivenessStatus.LIVE
    restricted_status = CitationLivenessStatus.LIVE_RESTRICTED
    dead_status = CitationLivenessStatus.DEAD

    assert live_status.is_live is True
    assert live_status.is_restricted is False
    assert live_status.is_dead is False

    assert restricted_status.is_live is True
    assert restricted_status.is_restricted is True
    assert restricted_status.is_dead is False

    assert dead_status.is_live is False
    assert dead_status.is_restricted is False
    assert dead_status.is_dead is True


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


def test_config_defaults() -> None:
    """Verifies default values for EvidenceArchiverConfig."""
    cfg = EvidenceArchiverConfig()
    assert cfg.timeout_seconds == 4.0
    assert "clearance-audit" in cfg.user_agent
    assert cfg.local_storage_dir == "output/evidence_snapshots"
    assert cfg.gcs_bucket_template == "lienmark-{tenant}-evidence-snapshots"
    assert cfg.enable_gcs is False
    assert cfg.max_concurrency == 10
