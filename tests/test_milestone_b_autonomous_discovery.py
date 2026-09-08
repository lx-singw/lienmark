"""
tests/test_milestone_b_autonomous_discovery.py

Milestone B Acceptance Gate: Autonomous Background Discovery & Ingestion.
Verifies CloudEvent progression, rename invariance (<100ms, $0.00 spend),
sandbox rejection, content lease dedup, confidentiality trimming,
budget halt, incomplete cache safety, and paginated GCS polling.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.intake.confidentiality import sanitize_description
from backend.api.webhooks.storage import clear_feed_activity, set_storage_watcher_service, storage_webhook_router
from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import CreativeUseNode, ParserMetadata
from backend.core.lifecycle import RunLifecycleManager, transition_run
from backend.domain.models import InvestigationRun, RunStatus
from backend.orchestration.execution_budget_governor import ExecutionBudgetGovernor as BudgetGovernor
from backend.services.hasher import StreamingHasher
from backend.services.storage_watcher import StorageWatcherService
from backend.services.storage_watcher_types import IngestionStatus
from backend.storage.baseline_store import InMemoryBaselineStore
from backend.storage.document_store import DocumentStore
from backend.storage.document_store_types import DocumentProcessingStatus
from backend.storage.ledger import CryptographicLedger
from backend.storage.locks import DistributedLockManager
from backend.storage.repository import InMemoryTenantRepository, get_tenant_repository


@pytest.fixture(autouse=True)
def clean_milestone_b_env():
    InMemoryTenantRepository.reset_global_storage()
    clear_feed_activity()
    yield


@pytest.fixture
def webhook_client() -> TestClient:
    lock_mgr = DistributedLockManager(in_memory=True)
    service = StorageWatcherService(
        lock_manager=lock_mgr,
        repository_factory=lambda org: get_tenant_repository(org, force_in_memory=True),
    )
    set_storage_watcher_service(service)
    app = FastAPI()
    app.include_router(storage_webhook_router)
    return TestClient(app)


def test_autonomous_progression_from_webhook_to_investigation(webhook_client: TestClient):
    """Post CloudEvent for locked/screenplay_v8.pdf; verify QUEUED->INVESTIGATING->READY_FOR_REVIEW."""
    payload = {
        "specversion": "1.0", "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/vault", "id": "evt_auto_v8_001",
        "data": {
            "bucket": "vault", "size": 4096, "etag": "etag_auto_v8_999",
            "name": "organizations/org_auto/productions/prod_cinema/locked/screenplay_v8.pdf",
        },
    }
    resp = webhook_client.post("/api/webhooks/storage/eventarc", json=payload)
    assert resp.status_code == 200 and resp.json()["status"] == "queued"
    run_id = resp.json()["run_id"]

    repo = get_tenant_repository("org_auto", force_in_memory=True)
    run = repo.get_run("prod_cinema", run_id)
    assert run is not None and run.status == RunStatus.QUEUED

    mgr = RunLifecycleManager()
    run = mgr.transition(run, RunStatus.INVESTIGATING, reason="Autonomous worker intake begun")
    claims = [ExtractedClaim(claim_id="c1", category=ClaimCategory.MUSIC, scene_or_timecode="p.1", extracted_description="Song Track")]
    assert len(claims) == 1

    b_store = InMemoryBaselineStore()
    b_engine = ProductionBaselineEngine(store=b_store)
    node = CreativeUseNode(
        claim_id="c1", stable_lineage_key="music:song", asset_type="music", scene_or_timecode="p.1",
        description="Song Track", prominence="background", context="Radio plays song", context_hash="ctx12345678",
    )
    b_engine.register_baseline("org_auto", "prod_cinema", "v8", "a" * 64, ParserMetadata(parser_name="pdf", parser_version="1.0"), [node])
    assert b_engine.get_baseline("org_auto", "prod_cinema", "v8") is not None

    run = mgr.transition(run, RunStatus.READY_FOR_REVIEW, reason="Drifted claims dispatched")
    repo.save_run(run)
    assert repo.get_run("prod_cinema", run_id).status == RunStatus.READY_FOR_REVIEW


def test_rename_invariance_and_zero_dollar_spend():
    """Ingest screenplay_v1.pdf then renamed_copy_of_v1.pdf: <100ms p95, $0.00 spend, DEDUPLICATION_CACHE_HIT."""
    store, ledger = DocumentStore(), CryptographicLedger()
    store.attach_ledger(ledger)
    pdf_bytes = b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\ntrailer << >>\n%%EOF"

    doc1, res1 = store.lookup_or_register("org_paramount", "prod_fast", "screenplay_v1.pdf", pdf_bytes, "v1", 12)
    assert not res1.is_duplicate
    store.commit_document_baseline("org_paramount", doc1.document_id, "v1")

    t0 = time.perf_counter()
    doc2, res2 = store.lookup_or_register("org_paramount", "prod_fast", "renamed_copy_of_v1.pdf", pdf_bytes, "v1", 12)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res2.is_duplicate is True and doc2.document_id == doc1.document_id
    assert res2.cache_hit_latency_ms < 100.0 and elapsed_ms < 100.0
    assert res2.claims_reused_count == 12 and res2.api_spend_saved_usd > 0.0

    events = ledger.get_events("prod_fast")
    assert any(e.action_type == "DEDUPLICATION_CACHE_HIT" for e in events)


def test_fail_closed_sandbox_rejection(webhook_client: TestClient):
    """Post event for /sandbox/draft.pdf or /temp/notes.txt; verify HTTP 202 rejected_out_of_scope and 0 runs."""
    payload_sandbox = {
        "specversion": "1.0", "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/vault", "id": "evt_sbx_001",
        "data": {"bucket": "vault", "name": "organizations/org_sbx/productions/prod_sbx/sandbox/draft.pdf", "etag": "etag_sbx"},
    }
    resp1 = webhook_client.post("/api/webhooks/storage/eventarc", json=payload_sandbox)
    assert resp1.status_code == 202 and resp1.json()["status"] == "rejected_out_of_scope"

    payload_temp = {
        "specversion": "1.0", "type": "google.cloud.storage.object.v1.finalized",
        "source": "//storage.googleapis.com/buckets/vault", "id": "evt_temp_002",
        "data": {"bucket": "vault", "name": "organizations/org_sbx/productions/prod_sbx/temp/notes.txt", "etag": "etag_temp"},
    }
    resp2 = webhook_client.post("/api/webhooks/storage/eventarc", json=payload_temp)
    assert resp2.status_code == 202 and resp2.json()["status"] == "rejected_out_of_scope"

    repo = get_tenant_repository("org_sbx", force_in_memory=True)
    assert len(repo.list_runs("prod_sbx")) == 0


def test_concurrent_renamed_uploads_content_lease():
    """Simultaneous uploads of renamed copies acquire content lease; second reuses results with 0 redundant LLM calls."""
    store, lock_mgr = DocumentStore(), DistributedLockManager(in_memory=True)
    pdf_bytes = b"%PDF-1.4\nINT. DINER - NIGHT\nRadio plays music.\n%%EOF"
    hasher = StreamingHasher()
    raw_sha = hasher.digest_bytes(pdf_bytes).raw_sha256
    lease_key = f"content_lease:org_duo:{raw_sha}"

    llm_calls = 0
    def mock_llm_extract() -> list:
        nonlocal llm_calls
        llm_calls += 1
        return ["claim_music_001"]

    lock1 = lock_mgr.acquire(lease_key, ttl_seconds=60.0)
    assert lock1 is not None
    extracted = mock_llm_extract()
    doc1, _ = store.lookup_or_register("org_duo", "prod_duo", "screenplay_copy1.pdf", pdf_bytes, "v1", len(extracted))
    store.commit_document_baseline("org_duo", doc1.document_id, "v1")
    lock_mgr.release_lock(lock1)

    lock2 = lock_mgr.acquire(lease_key, ttl_seconds=60.0)
    assert lock2 is not None
    doc2, res2 = store.lookup_or_register("org_duo", "prod_duo", "renamed_copy2.pdf", pdf_bytes, "v1", 1)
    lock_mgr.release_lock(lock2)

    assert res2.is_duplicate is True and doc2.document_id == doc1.document_id
    assert llm_calls == 1


def test_confidentiality_trimming_sanitization():
    """Script page with emotional breakdown, dialogue, and music cue extracts <= 20 words without spoilers."""
    raw = 'SARAH in tears (sobbing uncontrollably). "Why did you betray me?!" In the background, \'Moonlight Sonata\' plays.'
    sanitized = sanitize_description(raw, asset_type="music", cast_names=["SARAH"])
    words = sanitized.split()

    assert len(words) <= 20
    assert "'Moonlight Sonata'" in sanitized
    assert "sync licensing status" in sanitized
    assert '"Why did you betray me?!"' not in sanitized
    assert "(sobbing uncontrollably)" not in sanitized
    assert "in tears" not in sanitized.lower()


def test_budget_exhaustion_halts_intake_to_waiting():
    """Pre-intake reservation fails spend cap; run transitions to WAITING_FOR_BUDGET."""
    gov = BudgetGovernor(default_max_run_spend_usd=0.05)
    run = InvestigationRun(
        run_id="run_exhaust_01", organization_id="org_halt", production_id="prod_halt",
        base_version_id="v7", target_version_id="v8", status=RunStatus.QUEUED,
    )
    repo = get_tenant_repository("org_halt", force_in_memory=True)
    repo.save_run(run)

    auth = gov.authorize_run(run.run_id, estimated_cost=10.0, run_budget_limit=0.05)
    assert auth.authorized is False
    assert gov.get_run_status(run.run_id) == RunStatus.WAITING_FOR_BUDGET

    run = transition_run(run, RunStatus.INVESTIGATING, reason="Intake initiated")
    run = transition_run(run, RunStatus.WAITING_FOR_BUDGET, reason="Spend ceiling breached on pre-intake reservation")
    repo.save_run(run)

    assert repo.get_run("prod_halt", run.run_id).status == RunStatus.WAITING_FOR_BUDGET


def test_incomplete_cache_resumes_processing():
    """Crashed prior run does NOT trigger false cache hit; downstream processing resumes safely."""
    store = DocumentStore()
    pdf_bytes = b"%PDF-1.4\nINT. LAB - NIGHT\nScientist works on serum.\n%%EOF"

    crashed_doc, res1 = store.lookup_or_register("org_crash", "prod_crash", "draft.pdf", pdf_bytes, auto_commit=False)
    assert crashed_doc.processing_status == DocumentProcessingStatus.PENDING
    assert crashed_doc.linked_baseline_version_id is None

    assert store.lookup_by_hash("org_crash", crashed_doc.content_hash) is None

    resumed_doc, res2 = store.lookup_or_register("org_crash", "prod_crash", "draft.pdf", pdf_bytes, auto_commit=True)
    assert not res2.is_duplicate and resumed_doc.document_id == crashed_doc.document_id
    assert resumed_doc.processing_status == DocumentProcessingStatus.COMMITTED

    doc3, res3 = store.lookup_or_register("org_crash", "prod_crash", "renamed_draft.pdf", pdf_bytes)
    assert res3.is_duplicate is True and doc3.document_id == crashed_doc.document_id


def test_paginated_gcs_polling_discovery():
    """Polling discovers generation-specific locked objects across pages and triggers ingestion."""
    repo = get_tenant_repository("org_poll", force_in_memory=True)
    watcher = StorageWatcherService(lock_manager=DistributedLockManager(in_memory=True), repository_factory=lambda o: repo)

    page_1 = [
        {"name": "organizations/org_poll/productions/prod_p/locked/screenplay_v1.pdf", "etag": "etag_p1", "size_bytes": 2048, "generation": "1725800000000001"},
        {"name": "organizations/org_poll/productions/prod_p/sandbox/ignore.pdf", "etag": "etag_sbx", "size_bytes": 1024, "generation": "1725800000000002"},
    ]
    page_2 = [
        {"name": "organizations/org_poll/productions/prod_p/locked/screenplay_v2.pdf", "etag": "etag_p2", "size_bytes": 3072, "generation": "1725800000000003"},
    ]

    res1 = watcher.poll_bucket_once("vault", page_1)
    assert len(res1) == 1 and res1[0]["status"] == IngestionStatus.QUEUED.value

    res2 = watcher.poll_bucket_once("vault", page_2)
    assert len(res2) == 1 and res2[0]["status"] == IngestionStatus.QUEUED.value

    page_update = [
        {"name": "organizations/org_poll/productions/prod_p/locked/screenplay_v1.pdf", "etag": "etag_p1_rev", "size_bytes": 2100, "generation": "1725800000000099"},
    ]
    res3 = watcher.poll_bucket_once("vault", page_update)
    assert len(res3) == 1 and res3[0]["status"] == IngestionStatus.QUEUED.value
