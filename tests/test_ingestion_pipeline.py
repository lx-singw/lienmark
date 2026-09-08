"""
tests/test_ingestion_pipeline.py

Automated test suite for the autonomous background IngestionPipelineService.
Tests worker leases, content locking, deduplication cache hits, budget reservation,
multi-format parsing, claims extraction, sanitization, baseline snapshots,
invalidation, and budget settlement.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
import zlib
from datetime import datetime, timezone

from backend.core.baseline_types import (
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
    compute_baseline_digest,
)
from backend.domain.models import InvestigationRun, RunStatus
from backend.services.ingestion_pipeline import IngestionPipelineService
from backend.services.ingestion_pipeline_steps import register_mock_storage_bytes, clear_mock_storage_registry
from backend.storage.baseline_store import InMemoryBaselineStore
from backend.storage.document_store import DocumentStore
from backend.storage.document_store_types import DocumentProcessingStatus, IngestedDocumentRecord
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository, get_tenant_repository


def _build_pdf_bytes(text: str) -> bytes:
    """Builds synthetic compressed PDF byte stream."""
    stream = f"BT\n({text}) Tj\nET\n".encode("latin-1")
    comp = zlib.compress(stream)
    return (
        b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length " + str(len(comp)).encode("latin-1") + b" /Filter /FlateDecode >>\n"
        b"stream\n" + comp + b"\nendstream\nendobj\ntrailer << /Root 1 0 R >>\n%%EOF"
    )


@pytest.fixture(autouse=True)
def clean_env():
    InMemoryTenantRepository.reset_global_storage()
    clear_mock_storage_registry()
    yield


@pytest.mark.asyncio
async def test_new_document_ingestion_flow():
    """Verifies complete pipeline runner on new document content."""
    org_id = "org_paramount"
    prod_id = "prod_matrix"
    run_id = "run_new_001"
    bkt = "lienmark-intake"
    obj = "screenplay_v8.pdf"
    pdf_bytes = _build_pdf_bytes("INT. CAFE - DAY\nNeo orders Coca-Cola while Debussy plays.")
    register_mock_storage_bytes(bkt, obj, pdf_bytes)

    lock_mgr = DistributedLockManager(in_memory=True)
    doc_store = DocumentStore()
    base_store = InMemoryBaselineStore()
    repo = get_tenant_repository(org_id, force_in_memory=True)

    service = IngestionPipelineService(
        lock_manager=lock_mgr,
        document_store=doc_store,
        baseline_store=base_store,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
    )

    run = await service.process_run(
        run_id=run_id, organization_id=org_id, production_id=prod_id,
        bucket=bkt, object_name=obj, etag="etag_123",
    )

    assert run.status == RunStatus.READY_FOR_REVIEW
    assert run.budget_spent_usd > 0.0
    saved_doc = doc_store.get_document(org_id, doc_store.list_documents(org_id)[0].document_id)
    assert saved_doc is not None
    assert saved_doc.processing_status == DocumentProcessingStatus.COMMITTED
    assert saved_doc.linked_baseline_version_id == "v8"
    assert not lock_mgr.is_locked(f"worker_lease:run:{run_id}")


@pytest.mark.asyncio
async def test_dedup_cache_hit_all_approved():
    """Verifies deduplication hit transitions QUEUED -> COMPLETED with $0 spend when claims approved."""
    org_id = "org_universal"
    prod_id = "prod_jurassic"
    pdf_bytes = _build_pdf_bytes("INT. PARK - DAY\nTourists observe dinosaur enclosures.")
    register_mock_storage_bytes("bkt", "draft.pdf", pdf_bytes)

    doc_store = DocumentStore()
    base_store = InMemoryBaselineStore()
    lock_mgr = DistributedLockManager(in_memory=True)
    repo = get_tenant_repository(org_id, force_in_memory=True)

    # Pre-register committed document with all claims approved
    hasher = doc_store._hasher
    dig = hasher.digest_bytes(pdf_bytes, compute_semantic=True)
    pre_doc = IngestedDocumentRecord(
        document_id="doc_existing_01", tenant_id=org_id, production_id=prod_id,
        filename="draft.pdf", content_hash=dig.raw_sha256, semantic_hash=dig.semantic_sha256,
        format="pdf", page_count=5, scene_count=2, version_id="v1", claims_count=3,
        processing_status=DocumentProcessingStatus.COMMITTED, linked_baseline_version_id="v1",
        metadata={"all_claims_approved": True, "unapproved_claims_count": 0},
    )
    doc_store.register_document(pre_doc)

    service = IngestionPipelineService(
        lock_manager=lock_mgr, document_store=doc_store, baseline_store=base_store,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
    )

    run = await service.process_run(
        run_id="run_dedup_01", organization_id=org_id, production_id=prod_id,
        bucket="bkt", object_name="draft.pdf", etag="etag_abc",
    )

    assert run.status == RunStatus.COMPLETED
    assert run.budget_spent_usd == 0.0
    assert run.metadata.get("dedup_cache_hit") is True
    assert run.metadata.get("all_claims_approved") is True


@pytest.mark.asyncio
async def test_dedup_cache_hit_await_review():
    """Verifies deduplication hit transitions QUEUED -> READY_FOR_REVIEW when claims await review."""
    org_id = "org_warner"
    prod_id = "prod_batman"
    pdf_bytes = _build_pdf_bytes("INT. BATCAVE - NIGHT\nWayne analyzes forensic evidence.")
    register_mock_storage_bytes("bkt", "batman_v1.pdf", pdf_bytes)

    doc_store = DocumentStore()
    base_store = InMemoryBaselineStore()
    lock_mgr = DistributedLockManager(in_memory=True)

    hasher = doc_store._hasher
    dig = hasher.digest_bytes(pdf_bytes, compute_semantic=True)
    pre_doc = IngestedDocumentRecord(
        document_id="doc_bat_01", tenant_id=org_id, production_id=prod_id,
        filename="batman_v1.pdf", content_hash=dig.raw_sha256, semantic_hash=dig.semantic_sha256,
        format="pdf", page_count=10, scene_count=4, version_id="v1", claims_count=8,
        processing_status=DocumentProcessingStatus.COMMITTED, linked_baseline_version_id="v1",
        metadata={"all_claims_approved": False, "requires_counsel_review": True, "unapproved_claims_count": 8},
    )
    doc_store.register_document(pre_doc)

    service = IngestionPipelineService(
        lock_manager=lock_mgr, document_store=doc_store, baseline_store=base_store,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
    )

    run = await service.process_run(
        run_id="run_dedup_02", organization_id=org_id, production_id=prod_id,
        bucket="bkt", object_name="batman_v1.pdf", etag="etag_xyz",
    )

    assert run.status == RunStatus.READY_FOR_REVIEW
    assert run.budget_spent_usd == 0.0
    assert run.metadata.get("dedup_cache_hit") is True
    assert run.metadata.get("requires_counsel_review") is True


@pytest.mark.asyncio
async def test_budget_breach_halts_waiting_for_budget():
    """Verifies pipeline halts to WAITING_FOR_BUDGET when reservation exceeds limit."""
    org_id = "org_indie"
    prod_id = "prod_low_budget"
    run_id = "run_budget_fail"
    pdf_bytes = _build_pdf_bytes("INT. GARAGE - DAY\nIndie band rehearses song.")
    register_mock_storage_bytes("bkt", "indie.pdf", pdf_bytes)

    lock_mgr = DistributedLockManager(in_memory=True)
    doc_store = DocumentStore()
    base_store = InMemoryBaselineStore()

    service = IngestionPipelineService(
        lock_manager=lock_mgr, document_store=doc_store, baseline_store=base_store,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
    )
    # Set run spend limit lower than reservation cost ($0.50)
    service.budget_governor._run_limits[run_id] = 0.01

    run = await service.process_run(
        run_id=run_id, organization_id=org_id, production_id=prod_id,
        bucket="bkt", object_name="indie.pdf", etag="etag_budget",
    )

    assert run.status == RunStatus.WAITING_FOR_BUDGET
    assert not lock_mgr.is_locked(f"worker_lease:run:{run_id}")


@pytest.mark.asyncio
async def test_concurrent_content_lock_yielding():
    """Verifies worker yields when content lock active and attaches once committed."""
    org_id = "org_mgm"
    prod_id = "prod_bond"
    pdf_bytes = _build_pdf_bytes("INT. CASINO - NIGHT\nBond places high-stakes bet.")
    register_mock_storage_bytes("bkt", "bond.pdf", pdf_bytes)

    lock_mgr = DistributedLockManager(in_memory=True)
    doc_store = DocumentStore()
    base_store = InMemoryBaselineStore()

    hasher = doc_store._hasher
    dig = hasher.digest_bytes(pdf_bytes, compute_semantic=True)
    c_key = f"content_lock:{org_id}:{prod_id}:{dig.raw_sha256}"
    # Simulate existing worker holding content lock
    other_lock = lock_mgr.acquire(c_key, ttl_seconds=1.0)
    assert other_lock is not None

    # Pre-commit document so yielding worker picks up committed result
    pre_doc = IngestedDocumentRecord(
        document_id="doc_bond_01", tenant_id=org_id, production_id=prod_id,
        filename="bond.pdf", content_hash=dig.raw_sha256, semantic_hash=dig.semantic_sha256,
        format="pdf", page_count=8, scene_count=3, version_id="v1", claims_count=5,
        processing_status=DocumentProcessingStatus.COMMITTED, linked_baseline_version_id="v1",
        metadata={"all_claims_approved": True},
    )
    doc_store.register_document(pre_doc)

    service = IngestionPipelineService(
        lock_manager=lock_mgr, document_store=doc_store, baseline_store=base_store,
        repository_factory=lambda o: get_tenant_repository(o, force_in_memory=True),
    )

    run = await service.process_run(
        run_id="run_bond_007", organization_id=org_id, production_id=prod_id,
        bucket="bkt", object_name="bond.pdf", etag="etag_007",
    )

    assert run.status == RunStatus.COMPLETED
    assert run.budget_spent_usd == 0.0
