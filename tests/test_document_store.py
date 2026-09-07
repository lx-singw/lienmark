"""
tests/test_document_store.py

Comprehensive unit test suite for DocumentStore and document deduplication.
Verifies rename invariance, sub-100ms latency, spend calculation, and tenant isolation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

import os
from unittest.mock import MagicMock
import pytest

from backend.storage.document_store import DocumentStore
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DedupLookupResult,
    DocumentNotFoundError,
    IngestedDocumentRecord,
)
from backend.storage.ledger import CryptographicLedger


def test_ingested_document_record_validation():
    """Validates IngestedDocumentRecord constructor constraints and format checking."""
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
        version_id="v1",
        claims_count=10,
    )
    assert doc.tenant_id == "org_cyberdyne"
    assert doc.org_id == "org_cyberdyne"
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


def test_lookup_by_hash_raw_and_semantic():
    """Verifies lookups against raw SHA-256 and fallback semantic hashes."""
    store = DocumentStore()
    doc = IngestedDocumentRecord(
        document_id="doc_lookup",
        tenant_id="org_lucasfilm",
        production_id="prod_starwars",
        filename="anh.fountain",
        content_hash="rawhash1234567890abcdef",
        semantic_hash="semhash1234567890abcdef",
        format="fountain",
        page_count=110,
        scene_count=50,
    )
    store.register_document(doc)

    # 1. Hit on raw hash
    found_raw = store.lookup_by_hash("org_lucasfilm", "rawhash1234567890abcdef")
    assert found_raw is not None
    assert found_raw.document_id == "doc_lookup"

    # 2. Hit on semantic hash when raw hash differs
    found_sem = store.lookup_by_hash(
        "org_lucasfilm", "different_raw_hash_00000", "semhash1234567890abcdef"
    )
    assert found_sem is not None
    assert found_sem.document_id == "doc_lookup"

    # 3. Miss on non-existent hash
    found_none = store.lookup_by_hash(
        "org_lucasfilm", "non_existent_hash_00000", "non_existent_sem_hash"
    )
    assert found_none is None


def test_register_document_strict_tenant_isolation():
    """Verifies cross-tenant boundaries: same content hash in different tenants remain isolated."""
    store = DocumentStore()
    doc_tenant_a = IngestedDocumentRecord(
        document_id="doc_tenant_a",
        tenant_id="org_paramount",
        production_id="prod_godfather",
        filename="script.fountain",
        content_hash="shared_content_hash_123456",
        format="fountain",
    )
    store.register_document(doc_tenant_a)

    # Tenant B lookup with identical hash MUST return None
    cross_lookup = store.lookup_by_hash("org_warner", "shared_content_hash_123456")
    assert cross_lookup is None, "Cross-tenant lookup must return None"

    # Register in Tenant B
    doc_tenant_b = IngestedDocumentRecord(
        document_id="doc_tenant_b",
        tenant_id="org_warner",
        production_id="prod_matrix",
        filename="script.fountain",
        content_hash="shared_content_hash_123456",
        format="fountain",
    )
    store.register_document(doc_tenant_b)

    # Both retrieve only their respective tenant document
    assert store.lookup_by_hash("org_paramount", "shared_content_hash_123456").document_id == "doc_tenant_a"
    assert store.lookup_by_hash("org_warner", "shared_content_hash_123456").document_id == "doc_tenant_b"


def test_lookup_or_register_rename_invariance_and_savings():
    """Verifies that renamed files with identical bytes trigger cache hits under 100ms with savings."""
    store = DocumentStore()
    content = b"INT. CONTROL ROOM - NIGHT\nAgent Smith observes the monitors.\n"

    # First upload: new document
    doc1, res1 = store.lookup_or_register(
        tenant_id="org_matrix",
        production_id="prod_matrix_reloaded",
        file_path_or_name="original_scene.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=12,
    )
    assert not res1.is_duplicate
    assert res1.claims_reused_count == 0
    assert res1.api_spend_saved_usd == 0.0

    # Second upload: renamed file with identical content bytes
    doc2, res2 = store.lookup_or_register(
        tenant_id="org_matrix",
        production_id="prod_matrix_reloaded",
        file_path_or_name="renamed_copy_scene_v2.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=12,
    )
    assert res2.is_duplicate
    assert doc2.document_id == doc1.document_id
    assert res2.cache_hit_latency_ms < 100.0
    assert res2.claims_reused_count == 12

    expected_usd = round((doc1.page_count * 0.015) + (12 * 0.04), 4)
    assert abs(res2.api_spend_saved_usd - expected_usd) < 1e-6


def test_lookup_or_register_with_cryptographic_ledger():
    """Verifies that duplicate hits record tamper-evident audit events on attached ledger."""
    store = DocumentStore()
    ledger = CryptographicLedger()
    store.attach_ledger(ledger)

    content = b"EXT. DESERT HIGHWAY - DUSK\nA black sedan speeds across the tarmac.\n"
    # Initial registration
    doc, _ = store.lookup_or_register(
        tenant_id="org_universal",
        production_id="prod_fast",
        file_path_or_name="fast.fountain",
        content_bytes=content,
    )

    # Duplicate lookup
    _, res = store.lookup_or_register(
        tenant_id="org_universal",
        production_id="prod_fast",
        file_path_or_name="fast_backup.fountain",
        content_bytes=content,
    )
    assert res.is_duplicate

    # Verify ledger recorded the audit event
    events = ledger.get_events("prod_fast")
    assert len(events) >= 1
    dedup_events = [e for e in events if e.action_type == "DOCUMENT_DEDUP_CACHE_HIT"]
    assert len(dedup_events) == 1
    payload = dedup_events[0].payload
    assert payload["document_id"] == doc.document_id
    assert payload["content_hash"] == doc.content_hash


def test_input_validation_and_tenant_security():
    """Verifies that invalid or empty tenant parameters raise appropriate errors."""
    store = DocumentStore()
    valid_bytes = b"Sample script text"

    with pytest.raises(DeduplicationError):
        store.lookup_or_register("", "prod_1", "script.txt", valid_bytes)

    with pytest.raises(DeduplicationError):
        store.lookup_or_register("org_valid", "", "script.txt", valid_bytes)

    with pytest.raises(TypeError):
        store.lookup_or_register("org_valid", "prod_1", "script.txt", "not_bytes")  # type: ignore

    with pytest.raises(DeduplicationError):
        store.lookup_by_hash("", "some_hash")


def test_firestore_adapter_mock_interaction():
    """Verifies interaction with Firestore client mock adhering to /organizations/{org_id}/documents."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
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
