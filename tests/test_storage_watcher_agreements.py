"""
tests/test_storage_watcher_agreements.py

Unit and integration tests for canonical agreement path ingestion:
1. Canonical agreement path allowlist admission alongside locked scripts.
2. Bucket-to-tenant binding enforcement and target production authorization.
3. Streaming SHA-256 computation and Cloud Storage generation ID capture.
4. Routing agreement arrivals to DocumentMatcherService without InvestigationRun creation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
from typing import Dict, List, Optional, Union

from backend.services.document_matcher_types import MatchingDecision, MatchResult
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import (
    IngestionStatus,
    StorageEvent,
    WatcherConfig,
    compute_streaming_sha256,
    parse_and_validate_gcs_path,
    validate_bucket_tenant_binding,
    validate_production_authorization,
)
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository


class MockDocumentMatcher:
    """Mock DocumentMatcherService recording arrivals and returning simulated MatchResult."""
    def __init__(self, decision: MatchingDecision = MatchingDecision.AUTO_RESOLVE) -> None:
        self.decision = decision
        self.recorded_arrivals: List[object] = []
        self.recorded_contents: List[Optional[Union[bytes, str]]] = []

    def on_document_arrival(self, event: object, file_content: Optional[Union[bytes, str]] = None) -> MatchResult:
        self.recorded_arrivals.append(event)
        self.recorded_contents.append(file_content)
        return MatchResult(
            event_id=getattr(event, "event_id", "evt_mock"),
            document_id="doc_mock_123",
            decision=self.decision,
            confidence_score=0.92,
            dual_key_valid=True,
            pipeline_resumed=True,
        )


def test_parse_and_validate_canonical_agreement_path() -> None:
    """Canonical path: organizations/{org}/productions/{prod}/agreements/{filename} is admitted."""
    path = "organizations/paramount/productions/prod_noir/agreements/sync_license_final.pdf"
    res = parse_and_validate_gcs_path(path)
    assert res.is_valid_scope is True
    assert res.organization_id == "paramount"
    assert res.production_id == "prod_noir"
    assert res.filename == "sync_license_final.pdf"
    assert res.folder_type == "agreements"
    assert res.is_agreement is True


def test_bucket_to_tenant_binding_validation() -> None:
    """Bucket-to-tenant binding succeeds on authorized match and rejects tenant spoofing."""
    bindings = {"lienmark-paramount-bucket": "org_paramount"}
    ok, err = validate_bucket_tenant_binding("lienmark-paramount-bucket", "org_paramount", bindings)
    assert ok is True and err is None

    bad, b_err = validate_bucket_tenant_binding("lienmark-paramount-bucket", "org_rogue", bindings)
    assert bad is False
    assert "bound to tenant" in (b_err or "")


def test_production_authorization_validation() -> None:
    """Production authorization validates container syntax and non-empty IDs."""
    ok, err = validate_production_authorization("prod_diner_noir_v8")
    assert ok is True and err is None

    bad_empty, err_empty = validate_production_authorization("")
    assert bad_empty is False
    assert "empty or null" in (err_empty or "")

    bad_chars, err_chars = validate_production_authorization("prod/invalid/slashes")
    assert bad_chars is False
    assert "invalid characters" in (err_chars or "")


def test_streaming_sha256_computation() -> None:
    """Computes accurate streaming raw SHA-256 hash for binary content."""
    payload = b"Sample legal contract binary content for testing SHA256 integrity"
    digest = compute_streaming_sha256(payload, chunk_size=16)
    assert len(digest) == 64
    import hashlib
    assert digest == hashlib.sha256(payload).hexdigest()


def test_process_agreement_routes_to_matcher_zero_investigation_runs() -> None:
    """Agreement upload routes to DocumentMatcher without creating InvestigationRun."""
    InMemoryTenantRepository.reset_global_storage()
    repo = InMemoryTenantRepository("org_paramount")
    lock_mgr = DistributedLockManager()
    matcher = MockDocumentMatcher()
    config = WatcherConfig(bucket_tenant_bindings={"paramount_bucket": "org_paramount"})

    service = StorageWatcherService(
        lock_manager=lock_mgr, config=config, repository_factory=lambda o: repo, document_matcher=matcher,  # type: ignore[arg-type]
    )

    content = b"%PDF-1.4 Mock Agreement Payload"
    event = StorageEvent(
        event_id="evt_agr_001",
        bucket="paramount_bucket",
        object_name="organizations/org_paramount/productions/prod_noir/agreements/sync.pdf",
        etag="etag_old_dont_rely",
        generation="1708899220011",
        size_bytes=len(content),
        time_created_utc="2026-09-08T10:00:00Z",
    )
    result = service.process_storage_event(event, file_content=content)

    assert result["status"] == "agreement_processed"
    assert result["decision"] == "auto_resolve"
    assert result["generation"] == "1708899220011"
    assert result["file_hash"] == compute_streaming_sha256(content)
    assert result["pipeline_resumed"] is True

    # Invariant: Zero InvestigationRuns created for agreement uploads
    assert len(repo._get_org_store()["runs"]) == 0
    assert len(matcher.recorded_arrivals) == 1


def test_process_agreement_rejects_unbound_bucket() -> None:
    """Rejects agreement upload if bucket is not bound to the tenant."""
    config = WatcherConfig(bucket_tenant_bindings={"safe_bucket": "org_legit"})
    service = StorageWatcherService(config=config)
    event = StorageEvent(
        event_id="evt_spoof",
        bucket="unbound_bucket",
        object_name="organizations/org_legit/productions/prod_noir/agreements/sync.pdf",
        etag="etag_123",
        size_bytes=100,
        time_created_utc="2026-09-08T10:00:00Z",
    )
    result = service.process_storage_event(event)
    assert result["status"] == IngestionStatus.REJECTED_OUT_OF_SCOPE.value
    assert "is bound to tenant" in str(result.get("rejection_reason"))
