"""
tests/test_document_store.py

Unit test suite for DocumentStore and document deduplication lifecycle.
Verifies PENDING registration, COMMITTED cache hits, resumption, and tenant boundaries.
Authored strictly under Google AntiGravity architectural guidelines.
"""

import os
from unittest.mock import MagicMock
import pytest

from backend.storage.document_store import DocumentStore
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DocumentNotFoundError,
    DocumentProcessingStatus,
    IngestedDocumentRecord,
)
from backend.storage.ledger import CryptographicLedger


def test_ingested_document_record_validation():
    """Validates IngestedDocumentRecord defaults, processing_status, and baseline id."""
    doc = IngestedDocumentRecord(
        document_id="doc_001",
        tenant_id="org_cyberdyne",
        production_id="prod_terminator",
        filename="script.fountain",
        content_hash="a" * 64,
        semantic_hash="b" * 64,
        format="fountain",
        page_count=120,
        scene_count=45,
    )
    assert doc.tenant_id == "org_cyberdyne"
    assert doc.processing_status == DocumentProcessingStatus.PENDING
    assert doc.linked_baseline_version_id is None
    assert doc.format == "fountain"

    with pytest.raises(ValueError, match="Invalid document format"):
        IngestedDocumentRecord(
            document_id="doc_bad",
            tenant_id="org_cyberdyne",
            production_id="prod_terminator",
            filename="script.bad",
            content_hash="a" * 64,
            format="unsupported_format",
        )


def test_lookup_by_hash_cache_hit_only_when_committed_and_linked():
    """Verifies lookup_by_hash returns records ONLY if COMMITTED and baseline is linked."""
    store = DocumentStore()
    doc_pending = IngestedDocumentRecord(
        document_id="doc_pend",
        tenant_id="org_lucasfilm",
        production_id="prod_starwars",
        filename="anh.fountain",
        content_hash="hash_pending_123456",
        format="fountain",
        processing_status=DocumentProcessingStatus.PENDING,
    )
    store.register_document(doc_pending)
    assert store.lookup_by_hash("org_lucasfilm", "hash_pending_123456") is None

    # Commit baseline: now lookup succeeds
    committed = store.commit_document_baseline("org_lucasfilm", "doc_pend", "base_v1")
    assert committed.processing_status == DocumentProcessingStatus.COMMITTED
    assert committed.linked_baseline_version_id == "base_v1"

    found = store.lookup_by_hash("org_lucasfilm", "hash_pending_123456")
    assert found is not None
    assert found.document_id == "doc_pend"


def test_register_document_strict_tenant_isolation():
    """Verifies cross-tenant boundaries: same content hash in different tenants remain isolated."""
    store = DocumentStore()
    doc_a = IngestedDocumentRecord(
        document_id="doc_tenant_a",
        tenant_id="org_paramount",
        production_id="prod_godfather",
        filename="script.fountain",
        content_hash="shared_content_hash_123456",
        format="fountain",
        processing_status=DocumentProcessingStatus.COMMITTED,
        linked_baseline_version_id="base_paramount",
    )
    store.register_document(doc_a)

    # Tenant B lookup with identical hash MUST return None
    assert store.lookup_by_hash("org_warner", "shared_content_hash_123456") is None

    doc_b = IngestedDocumentRecord(
        document_id="doc_tenant_b",
        tenant_id="org_warner",
        production_id="prod_matrix",
        filename="script.fountain",
        content_hash="shared_content_hash_123456",
        format="fountain",
        processing_status=DocumentProcessingStatus.COMMITTED,
        linked_baseline_version_id="base_warner",
    )
    store.register_document(doc_b)

    assert store.lookup_by_hash("org_paramount", "shared_content_hash_123456").document_id == "doc_tenant_a"
    assert store.lookup_by_hash("org_warner", "shared_content_hash_123456").document_id == "doc_tenant_b"


def test_lookup_or_register_pending_lifecycle_and_resumption():
    """Verifies initial PENDING registration, downstream commit, and duplicate resolution."""
    store = DocumentStore()
    content = b"INT. CONTROL ROOM - NIGHT\nAgent Smith observes the monitors.\n"

    # 1. First upload: registered initially as PENDING
    doc1, res1 = store.lookup_or_register(
        "org_matrix", "prod_reloaded", "scene.fountain", content, claims_count=12
    )
    assert not res1.is_duplicate
    assert doc1.processing_status == DocumentProcessingStatus.PENDING
    assert doc1.linked_baseline_version_id is None

    # 2. Second upload before commit: resumes pending doc, NOT a cache hit
    doc2, res2 = store.lookup_or_register(
        "org_matrix", "prod_reloaded", "scene_copy.fountain", content, claims_count=12
    )
    assert not res2.is_duplicate
    assert doc2.document_id == doc1.document_id

    # 3. Downstream investigation succeeds: commit baseline
    store.commit_document_baseline("org_matrix", doc1.document_id, "base_matrix_v1")

    # 4. Third upload after commit: triggers duplicate cache hit under 100ms
    doc3, res3 = store.lookup_or_register(
        "org_matrix", "prod_reloaded", "scene_final.fountain", content, claims_count=12
    )
    assert res3.is_duplicate
    assert doc3.document_id == doc1.document_id
    assert res3.cache_hit_latency_ms < 100.0
    assert res3.claims_reused_count == 12
    assert res3.api_spend_saved_usd > 0.0


def test_mark_document_failed_and_resumption():
    """Verifies mark_document_failed records error reason and subsequent upload resumes."""
    store = DocumentStore()
    content = b"SCENE 1 - EXT. ROOFTOP - NIGHT\nCorrupted script syntax.\n"
    doc, _ = store.lookup_or_register("org_sony", "prod_spiderman", "script.fountain", content)

    store.mark_document_failed("org_sony", doc.document_id, "Invalid dialogue token at line 42")
    failed = store.get_document("org_sony", doc.document_id)
    assert failed is not None
    assert failed.processing_status == DocumentProcessingStatus.FAILED
    assert failed.metadata["error_reason"] == "Invalid dialogue token at line 42"

    # Lookup by hash returns None for failed record
    assert store.lookup_by_hash("org_sony", doc.content_hash) is None

    # Re-upload resumes the record back to PENDING
    resumed_doc, res = store.lookup_or_register("org_sony", "prod_spiderman", "script.fountain", content)
    assert not res.is_duplicate
    assert resumed_doc.document_id == doc.document_id
    assert resumed_doc.processing_status == DocumentProcessingStatus.PENDING


def test_lookup_or_register_with_cryptographic_ledger():
    """Verifies that duplicate hits record tamper-evident audit events on attached ledger."""
    store = DocumentStore()
    ledger = CryptographicLedger()
    store.attach_ledger(ledger)
    content = b"EXT. DESERT HIGHWAY - DUSK\nA black sedan speeds across tarmac.\n"

    doc, _ = store.lookup_or_register("org_universal", "prod_fast", "fast.fountain", content)
    store.commit_document_baseline("org_universal", doc.document_id, "base_fast_1")

    _, res = store.lookup_or_register("org_universal", "prod_fast", "fast_backup.fountain", content)
    assert res.is_duplicate

    events = ledger.get_events("prod_fast")
    dedup_events = [e for e in events if e.action_type == "DOCUMENT_DEDUP_CACHE_HIT"]
    assert len(dedup_events) == 1
    assert dedup_events[0].payload["document_id"] == doc.document_id


def test_commit_and_fail_errors_and_tenant_security():
    """Verifies error handling for non-existent documents and boundary violations."""
    store = DocumentStore()
    with pytest.raises(DocumentNotFoundError):
        store.commit_document_baseline("org_a", "non_existent_id", "base_1")

    with pytest.raises(DocumentNotFoundError):
        store.mark_document_failed("org_a", "non_existent_id", "some error")

    with pytest.raises(DeduplicationError):
        store.lookup_or_register("", "prod_1", "script.txt", b"content")

    with pytest.raises(DeduplicationError):
        store.lookup_by_hash("", "hash123")


def test_firestore_adapter_mock_interaction():
    """Verifies interaction with Firestore client mock adhering to /organizations/{org_id}/documents."""
    mock_client = MagicMock()
    mock_doc_ref = MagicMock()
    mock_client.db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref

    store = DocumentStore(firestore_client=mock_client)
    doc = IngestedDocumentRecord(
        document_id="doc_fs_test",
        tenant_id="org_disney",
        production_id="prod_lion_king",
        filename="lk.fountain",
        content_hash="fs_hash_1234567890",
        format="fountain",
    )
    store.register_document(doc)
    mock_doc_ref.set.assert_called_once()
