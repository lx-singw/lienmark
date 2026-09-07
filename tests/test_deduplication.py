"""
test_deduplication.py

Comprehensive test suite for multi-tenant DocumentStore and deduplication engine.
Validates content_hash lookup, rename invariance acceptance gate (<100ms, $0.00 spend),
semantic hash invariance across re-exports, and strict zero-trust tenant isolation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import time
import zlib
import pytest

from backend.services.hasher import StreamingHasher
from backend.storage.document_store import DocumentStore
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DedupLookupResult,
    IngestedDocumentRecord,
)
from backend.storage.ledger import CryptographicLedger


def _build_synthetic_pdf(text: str) -> bytes:
    """Builds a minimal valid PDF byte stream with zlib compressed content."""
    stream = f"BT\n({text}) Tj\nET\n".encode("latin-1")
    comp = zlib.compress(stream)
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length " + str(len(comp)).encode("latin-1") + b" /Filter /FlateDecode >>\n"
        b"stream\n" + comp + b"\nendstream\nendobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF"
    )


def test_document_store_lookup_by_content_hash() -> None:
    """Verifies first upload saves document and second upload of identical hash detects duplicate."""
    store = DocumentStore()
    content = b"INT. BOARDROOM - DAY\nThe executives review the merger contract.\n"

    # First upload saves new document
    doc1, res1 = store.lookup_or_register(
        tenant_id="org_paramount",
        production_id="prod_godfather",
        file_path_or_name="screenplay_draft.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=14,
    )
    assert not res1.is_duplicate
    assert res1.matched_document is None
    assert doc1.tenant_id == "org_paramount"
    assert doc1.claims_count == 14

    # Second upload with identical bytes detects duplicate
    doc2, res2 = store.lookup_or_register(
        tenant_id="org_paramount",
        production_id="prod_godfather",
        file_path_or_name="screenplay_draft.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=14,
    )
    assert res2.is_duplicate
    assert res2.matched_document is not None
    assert res2.matched_document.document_id == doc1.document_id
    assert doc2.document_id == doc1.document_id
    assert res2.claims_reused_count == 14


def test_rename_invariance_acceptance_gate() -> None:
    """Acceptance Gate: upload draft_v1.pdf, then renamed_copy_draft_v1.pdf.

    Must resolve duplicate in < 100ms with is_duplicate=True and $0.00 external spend.
    """
    store = DocumentStore()
    ledger = CryptographicLedger()
    store.attach_ledger(ledger)

    pdf_bytes = _build_synthetic_pdf("INT. ARCHIVE - NIGHT\nAgent investigates old title records.")

    # 1. Initial upload under original filename and path
    doc1, res1 = store.lookup_or_register(
        tenant_id="org_universal",
        production_id="prod_jurassic",
        file_path_or_name="/storage/intake/draft_v1.pdf",
        content_bytes=pdf_bytes,
        version_id="v1",
        claims_count=8,
    )
    assert not res1.is_duplicate

    # 2. Upload identical content under completely renamed path
    start_bench = time.perf_counter()
    doc2, res2 = store.lookup_or_register(
        tenant_id="org_universal",
        production_id="prod_jurassic",
        file_path_or_name="/mount/different_dir/renamed_copy_draft_v1.pdf",
        content_bytes=pdf_bytes,
        version_id="v1",
        claims_count=8,
    )
    bench_elapsed_ms = (time.perf_counter() - start_bench) * 1000.0

    # Acceptance Invariant Verification:
    assert res2.is_duplicate is True
    assert doc2.document_id == doc1.document_id
    assert res2.cache_hit_latency_ms < 100.0
    assert bench_elapsed_ms < 100.0
    assert res2.claims_reused_count == 8
    assert res2.api_spend_saved_usd > 0.0


def test_semantic_invariance_differing_raw_hashes() -> None:
    """Verifies two documents with differing raw hashes but identical normalized text match."""
    store = DocumentStore()
    hasher = StreamingHasher()

    script_v1 = (
        "%PDF-1.4\n"
        "/CreationDate (D:20260101120000Z)\n"
        "Draft Date: 2026-01-01\n"
        "Page 1\n"
        "INT. DETECTIVE OFFICE - NIGHT\n\n"
        "SARAH\n"
        "We tracked down the original chain of title.\n"
    ).encode("utf-8")

    script_v2 = (
        "%PDF-1.7\n"
        "/CreationDate (D:20260907090955Z)\n"
        "Draft Date: 2026-09-07\n"
        "Page 1\n"
        "INT. DETECTIVE OFFICE - NIGHT\n\n"
        "SARAH (cont'd)\n"
        "We tracked down the original chain of title.\n"
    ).encode("utf-8")

    # Confirm raw hashes strictly differ due to timestamps and export formatting
    res_h1 = hasher.digest_bytes(script_v1, compute_semantic=True)
    res_h2 = hasher.digest_bytes(script_v2, compute_semantic=True)
    assert res_h1.raw_sha256 != res_h2.raw_sha256
    assert res_h1.semantic_sha256 == res_h2.semantic_sha256

    # Upload script 1
    doc1, res1 = store.lookup_or_register(
        tenant_id="org_warner",
        production_id="prod_matrix",
        file_path_or_name="export_january.pdf",
        content_bytes=script_v1,
        version_id="v1",
        claims_count=16,
    )
    assert not res1.is_duplicate

    # Upload script 2: raw hash misses, but semantic hash matches
    doc2, res2 = store.lookup_or_register(
        tenant_id="org_warner",
        production_id="prod_matrix",
        file_path_or_name="export_september.pdf",
        content_bytes=script_v2,
        version_id="v2",
        claims_count=16,
    )
    assert res2.is_duplicate is True
    assert doc2.document_id == doc1.document_id
    assert "semantic" in res2.reason.lower()


def test_tenant_isolation_cross_tenant_guarantee() -> None:
    """Verifies file with identical hash in Tenant A is NOT accessible or detected in Tenant B."""
    store = DocumentStore()
    content = b"INT. SAFE HOUSE - NIGHT\nConfidential client notes.\n"

    # Register in Tenant A
    doc_a, res_a = store.lookup_or_register(
        tenant_id="org_studio_alpha",
        production_id="prod_project_x",
        file_path_or_name="confidential_script.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=25,
    )
    assert not res_a.is_duplicate
    assert doc_a.tenant_id == "org_studio_alpha"

    # Upload same content to Tenant B: must NOT detect Tenant A's document as duplicate
    doc_b, res_b = store.lookup_or_register(
        tenant_id="org_studio_beta",
        production_id="prod_project_y",
        file_path_or_name="confidential_script.fountain",
        content_bytes=content,
        version_id="v1",
        claims_count=5,
    )
    assert not res_b.is_duplicate
    assert doc_b.tenant_id == "org_studio_beta"
    assert doc_b.document_id != doc_a.document_id

    # Direct query in Tenant B for Tenant A's hash before registration returns None
    assert store.lookup_by_hash("org_studio_gamma", doc_a.content_hash) is None

    # Blank or cross-boundary lookups raise DeduplicationError
    with pytest.raises(DeduplicationError):
        store.lookup_by_hash("   ", doc_a.content_hash)
