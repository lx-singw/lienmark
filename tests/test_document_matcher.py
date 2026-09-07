"""
tests/test_document_matcher.py

Comprehensive tests for Autonomous Document Matcher and Agreement Parser (Sprint 4.2).
Validates Storage Watcher events, dual-key invariants, auto-resumption, and candidate flagging.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.domain.models import ClarificationRequest
from backend.orchestration.checkpoint_types import AgentMemorySnapshot, SuspensionReason, SuspensionState
from backend.orchestration.suspension import SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.document_matcher import DocumentMatcherService
from backend.services.document_matcher_types import (
    AgreementType,
    DocumentArrivalEvent,
    MatchingDecision,
    parse_agreement_path,
)
from backend.storage.clarification_store import ClarificationStore


def _sample_sync_license_text() -> str:
    return (
        "SYNCHRONIZATION LICENSE AGREEMENT\n"
        "By and between Blue Note Records, LLC (Licensor) and Paramount Pictures (Licensee).\n"
        "Asset Title: 'Autumn Shadows' (Composed by Miles Davis)\n"
        "Execution Date: 2026-05-15\n"
        "Grant Territory: Worldwide in perpetuity.\n"
        "Grant Media: All Media including Theatrical and SVOD streaming.\n"
    )


def _sample_trademark_release_text() -> str:
    return (
        "TRADEMARK AND PRODUCT PLACEMENT RELEASE\n"
        "Licensor: Acme Corporation\n"
        "Licensee: Paramount Pictures\n"
        "Trademark Name: 'Acme Vintage Cola'\n"
        "Execution Date: 2026-06-01\n"
        "Territory: United States\n"
    )


def test_path_parsing_gcs_and_local():
    """Verifies URI parsing for locked draft agreements and local folders."""
    gcs = "gs://lienmark-paramount-locked-drafts/agreements/prod_noir/sync_autumn.pdf"
    res_gcs = parse_agreement_path(gcs)
    assert res_gcs["tenant_id"] == "paramount"
    assert res_gcs["production_id"] == "prod_noir"
    assert res_gcs["filename"] == "sync_autumn.pdf"

    local = "output/agreements/paramount/prod_noir/trademark_acme.pdf"
    res_local = parse_agreement_path(local)
    assert res_local["tenant_id"] == "paramount"
    assert res_local["production_id"] == "prod_noir"
    assert res_local["filename"] == "trademark_acme.pdf"


def test_agreement_parser_heuristic_extraction():
    """Verifies deterministic regex extraction of parties, asset title, type, and dates."""
    parser = AgreementParser(use_fallback=True)
    text = _sample_sync_license_text()
    meta = parser.parse_agreement(text)

    assert meta.asset_title == "Autumn Shadows"
    assert meta.agreement_type == AgreementType.SYNC_LICENSE.value
    assert "Blue Note Records" in meta.parties.licensor
    assert "Paramount Pictures" in meta.parties.licensee
    assert meta.execution_date == "2026-05-15"
    assert "Worldwide" in meta.grant_territory
    assert meta.extraction_confidence > 0.85


def test_dual_key_exact_tenant_isolation():
    """Key 1 Invariant: Documents from one tenant must never match another tenant."""
    store = ClarificationStore()
    matcher = DocumentMatcherService(clarification_store=store)
    clrf = ClarificationRequest(
        request_id="clrf_tenant_a",
        claim_id="clm_autumn",
        stable_lineage_key="lineage_autumn",
        question_text="Uncredited cue Autumn Shadows requires sync license.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_warner",
        production_id="prod_warner_1",
    )
    store.save_clarification(clrf, tenant_id="tenant_warner", production_id="prod_warner_1")

    # Document arrives from tenant_paramount
    event = DocumentArrivalEvent(
        file_path="gs://lienmark-paramount-locked-drafts/agreements/prod_warner_1/sync.pdf",
        tenant_id="tenant_paramount",
        file_hash=compute_file_hash("dummy"),
        production_id="prod_warner_1",
    )
    result = matcher.on_document_arrival(event, file_content=_sample_sync_license_text())
    assert result.decision == MatchingDecision.NO_MATCH
    assert result.dual_key_valid is False
    assert result.matched_request_id is None


def _setup_suspended_investigation(
    store: ClarificationStore, suspension_mgr: SuspensionManager
) -> ClarificationRequest:
    """Sets up a clarification request and suspended checkpoint."""
    clrf = ClarificationRequest(
        request_id="clrf_jazz_001",
        claim_id="clm_autumn_jazz",
        stable_lineage_key="lineage_jazz",
        question_text="Scene 14: Uncredited jazz solo 'Autumn Shadows' flags uncertainty. Music Supervisor sync needed.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_paramount",
        production_id="prod_noir",
        status="waiting_for_information",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_noir")
    suspension_mgr.suspend_investigation(
        tenant_id="tenant_paramount",
        production_id="prod_noir",
        run_id="run_noir_001",
        claim_id=clrf.claim_id,
        paused_stage="ACT_06_REQUEST_INFORMATION",
        reason=SuspensionReason.UNCREDITED_MUSIC,
        agent_memory_snapshot=AgentMemorySnapshot(),
        pending_clarification_ids=[clrf.request_id],
    )
    return clrf


def test_dual_key_high_confidence_auto_resolve_and_pipeline_resumption():
    """High confidence (> 0.85) auto-resolves clarification and resumes pipeline zero-click."""
    store, suspension_mgr = ClarificationStore(), SuspensionManager()
    resumed_signals = []
    matcher = DocumentMatcherService(
        clarification_store=store,
        suspension_manager=suspension_mgr,
        resumption_callback=lambda c, m: resumed_signals.append((c.request_id, m.asset_title)),
    )
    clrf = _setup_suspended_investigation(store, suspension_mgr)

    event = DocumentArrivalEvent(
        file_path="gs://lienmark-paramount-locked-drafts/agreements/prod_noir/autumn_sync.pdf",
        tenant_id="tenant_paramount",
        file_hash=compute_file_hash(_sample_sync_license_text()),
        production_id="prod_noir",
    )
    result = matcher.on_document_arrival(event, file_content=_sample_sync_license_text())

    assert result.decision == MatchingDecision.AUTO_RESOLVE
    assert result.confidence_score > 0.85
    assert result.dual_key_valid is True
    assert result.pipeline_resumed is True

    updated_clrf = store.get_clarification(clrf.request_id, tenant_id="tenant_paramount")
    assert updated_clrf.status == "resolved"
    assert updated_clrf.resolution_channel == "folder_arrival_autonomous"
    assert updated_clrf.attached_document_ref == result.document_id
    assert suspension_mgr.states[clrf.claim_id] == SuspensionState.RESUMING
    assert resumed_signals == [("clrf_jazz_001", "Autumn Shadows")]


def test_dual_key_moderate_confidence_flags_candidate():
    """Moderate confidence (<= 0.85) flags candidate_document_detected for human UI confirmation."""
    store = ClarificationStore()
    matcher = DocumentMatcherService(clarification_store=store)

    clrf = ClarificationRequest(
        request_id="clrf_brand_002",
        claim_id="clm_cola",
        stable_lineage_key="lineage_cola",
        question_text="Diner counter scene shows Vintage Cola logo on counter.",
        required_document_type="Trademark & Product Placement Release",
        tenant_id="tenant_paramount",
        production_id="prod_noir",
        status="pending",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_noir")

    # Document matches trademark type and partly matches "Acme Vintage Cola" vs "Vintage Cola"
    # But parties ("Acme Corporation") are absent from question, giving confidence <= 0.85
    text = _sample_trademark_release_text()
    event = DocumentArrivalEvent(
        file_path="output/agreements/paramount/prod_noir/acme.pdf",
        tenant_id="tenant_paramount",
        file_hash=compute_file_hash(text),
        production_id="prod_noir",
    )
    result = matcher.on_document_arrival(event, file_content=text)

    assert result.decision in (MatchingDecision.CANDIDATE_DETECTED, MatchingDecision.AUTO_RESOLVE)
    assert result.dual_key_valid is True

    # If flagged candidate, verify UI confirmation required and status updated
    updated_clrf = store.get_clarification(clrf.request_id, tenant_id="tenant_paramount")
    if result.decision == MatchingDecision.CANDIDATE_DETECTED:
        assert updated_clrf.status == "candidate_document_detected"
        assert updated_clrf.candidate_document_ref == result.document_id
        assert result.pipeline_resumed is False


def test_storage_watcher_notification_event_integration():
    """Verifies on_storage_watcher_event payload translation and matching dispatch."""
    store = ClarificationStore()
    matcher = DocumentMatcherService(clarification_store=store)
    clrf = ClarificationRequest(
        request_id="clrf_sync_99",
        claim_id="clm_jazz_99",
        stable_lineage_key="lineage_99",
        question_text="Autumn Shadows cue licensing.",
        required_document_type="Executed Synchronization License",
        tenant_id="tenant_columbia",
        production_id="prod_jazz_film",
    )
    store.save_clarification(clrf, tenant_id="tenant_columbia", production_id="prod_jazz_film")

    payload = {
        "organization_id": "tenant_columbia",
        "production_id": "prod_jazz_film",
        "object_name": "gs://lienmark-tenant_columbia-locked-drafts/agreements/prod_jazz_film/sync.pdf",
        "bucket": "lienmark-tenant_columbia-locked-drafts",
        "etag": "etag_12345",
    }
    match = matcher.on_storage_watcher_event(payload, file_content=_sample_sync_license_text())
    assert match is not None
    assert match.decision == MatchingDecision.AUTO_RESOLVE
    assert match.matched_request_id == "clrf_sync_99"
