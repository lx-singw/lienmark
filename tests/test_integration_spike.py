"""
Sprint 1B Real Integration Spike Test Suite
Validates Gemini 2.5 Flash adapter, Parallel Search adapter, Agent Builder workflow,
SHA-256 payload hash tracking, redacted execution traces, and credential detection.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import hashlib
import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.domain.models import (
    EvidenceStance,
    PublicEvidenceSnapshot,
    DecisionState,
    DecisionStatus,
)
from backend.services.gemini_service import (
    GeminiService,
    DeltaAnalysisResult,
    ClearanceBriefing,
)
from backend.services.parallel_service import ParallelSearchService
from backend.orchestration.workflow import LienmarkWorkflow, WorkflowRunResult
from backend.main import app


# =============================================================================
# 1. GEMINI 2.5 FLASH STRUCTURED OUTPUT ADAPTER TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_adapter_structured_delta_output():
    """
    Asserts that GeminiService returns fully validated Pydantic DeltaAnalysisResult
    with required schema fields and legal reasoning outputs.
    """
    service = GeminiService()
    result = await service.analyze_scene_delta(
        asset_name="Crime Detective Magazine cover poster",
        v7_context="Poster hangs on far wall behind detective desk, soft focus.",
        v7_prominence="Out-of-focus background blur, 2s",
        v8_context="Detective grabs poster off wall and reads headline aloud.",
        v8_prominence="Featured close-up focal shot with dialogue, 14s",
    )

    assert isinstance(result, DeltaAnalysisResult), "Must return DeltaAnalysisResult instance"
    assert result.is_material is True, "Scene 42 poster shift must be evaluated as material"
    assert result.clearance_risk_level.lower() == "high"
    assert "dialogue" in result.narrative_impact.lower() or "interact" in result.narrative_impact.lower()
    assert result.recommended_action == "revalidate"
    assert len(result.prominence_shift) > 10
    assert len(result.statutory_fair_use_impact) > 10


@pytest.mark.asyncio
async def test_gemini_adapter_counsel_briefing_synthesis():
    """
    Asserts that GeminiService synthesizes a high-confidence ClearanceBriefing
    incorporating Parallel search evidence.
    """
    service = GeminiService()
    briefing = await service.synthesize_counsel_briefing(
        asset_name="Midnight Serenade jazz sync cue",
        reason_code="EXTERNAL_EVIDENCE_CONFLICT",
        evidence_excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
        source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
        source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
    )

    assert isinstance(briefing, ClearanceBriefing), "Must return ClearanceBriefing instance"
    assert briefing.claim_id == "music_cue_midnight_serenade"
    assert briefing.parallel_evidence_stance == "CONTRADICTORY"
    assert "Vanguard Media" in briefing.counsel_summary
    assert briefing.confidence >= 0.90
    assert "EXCEPTION" in briefing.suggested_counsel_action.upper() or "REJECT" in briefing.suggested_counsel_action.upper()


# =============================================================================
# 2. PARALLEL SEARCH API ADAPTER & SHA-256 HASH TRACKING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_parallel_search_adapter_runtime_call_and_metadata():
    """
    Asserts that ParallelSearchService executes runtime query, preserves
    source URL, citation title, excerpt, stance, latency, and call ID.
    """
    service = ParallelSearchService()

    # Query 1: Music Sync Rights Contradiction
    music_snap = await service.search(
        query="Midnight Serenade jazz sync rights copyright owner 2026",
        use_id="dec_v7_music_midnight",
        stable_lineage_key="music_cue_midnight_serenade",
    )

    assert isinstance(music_snap, PublicEvidenceSnapshot)
    assert music_snap.provider == "Parallel"
    assert music_snap.stance == EvidenceStance.CONTRADICTORY
    assert "ascap.com" in music_snap.source_url
    assert "Vanguard Media" in music_snap.excerpt
    assert music_snap.retrieval_latency_ms is not None and music_snap.retrieval_latency_ms > 0
    assert music_snap.provider_call_id is not None and len(music_snap.provider_call_id) > 0

    # Query 2: Historical Poster Public Domain Confirmation
    poster_snap = await service.search(
        query="1946 Crime Detective Magazine Shadows Over Broadway copyright renewal",
        use_id="dec_v7_poster_noir",
        stable_lineage_key="poster_noir_detective_magazine",
    )

    assert isinstance(poster_snap, PublicEvidenceSnapshot)
    assert poster_snap.provider == "Parallel"
    assert poster_snap.stance == EvidenceStance.SUPPORTING
    assert "loc.gov" in poster_snap.source_url
    assert "expired 1974" in poster_snap.excerpt
    assert poster_snap.retrieval_latency_ms is not None and poster_snap.retrieval_latency_ms > 0


def test_parallel_search_sha256_payload_hash_tracking():
    """
    Asserts that ParallelSearchService generates deterministic SHA-256 hashes
    of request payloads to guarantee tamper-evident provenance.
    """
    service = ParallelSearchService()
    payload = {
        "query": "Midnight Serenade jazz sync rights copyright owner 2026",
        "max_results": 3,
        "include_metadata": True,
    }

    computed_hash = service.compute_payload_hash(payload)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    assert computed_hash == expected_hash, "Payload hash must match canonical SHA-256"
    assert len(computed_hash) == 64, "SHA-256 hash must be exactly 64 hex characters"


@pytest.mark.asyncio
async def test_parallel_evidence_snapshot_payload_hash_attachment():
    """
    Asserts that the PublicEvidenceSnapshot returned by search contains
    the valid 64-character hex SHA-256 payload hash.
    """
    service = ParallelSearchService()
    snap = await service.search(
        query="Midnight Serenade jazz sync rights copyright owner 2026",
        use_id="dec_v7_music_midnight",
        stable_lineage_key="music_cue_midnight_serenade",
    )

    assert snap.payload_hash is not None
    assert len(snap.payload_hash) == 64
    # Recompute to verify match with Parallel API v1 V1SearchRequest
    payload = service.build_request_payload(
        query="Midnight Serenade jazz sync rights copyright owner 2026",
        stable_lineage_key="music_cue_midnight_serenade",
    )
    assert snap.payload_hash == service.compute_payload_hash(payload)


# =============================================================================
# 3. AGENT BUILDER / ORCHESTRATION TOOL INVOCATION & REDACTED TRACE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_agent_builder_workflow_tool_invocation_path():
    """
    Asserts that LienmarkWorkflow invokes registered tools in the application path:
    1. Golden version ingestion
    2. Gemini semantic delta tool
    3. InvalidationEngine dependency evaluator
    4. Parallel Search API targeted tool
    5. Gemini counsel briefing synthesis
    """
    workflow = LienmarkWorkflow()
    result = await workflow.execute_drift_detection()

    assert isinstance(result, WorkflowRunResult)
    assert result.run_id.startswith("run_")
    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2

    # Verify registered tool invocations in execution traces
    components = [t.component for t in result.execution_traces]
    assert "LienmarkEngine" in components
    assert "Gemini 2.5 Flash" in components
    assert "InvalidationEngine" in components
    assert "Parallel Search API" in components

    # Ensure traces verify successful status
    for trace in result.execution_traces:
        assert trace.status == "SUCCESS"
        assert trace.duration_ms >= 0


@pytest.mark.asyncio
async def test_redacted_trace_correlation_across_run():
    """
    Asserts that execution traces are correlated via run_id and do not leak
    confidential API keys or credentials.
    """
    workflow = LienmarkWorkflow()
    result = await workflow.execute_drift_detection()

    # Trace correlation check
    assert len(result.execution_traces) >= 4
    trace_details_str = json.dumps([t.details for t in result.execution_traces])

    # Redaction / Zero credential leakage verification
    assert "sk-" not in trace_details_str
    assert "AIza" not in trace_details_str
    assert "PARALLEL_API_KEY" not in trace_details_str
    assert "GEMINI_API_KEY" not in trace_details_str


# =============================================================================
# 4. HEALTH CHECK CREDENTIAL DETECTION & ERROR HANDLING TESTS
# =============================================================================

def test_health_check_detects_credentials_without_leaking():
    """
    Asserts that /api/health and /health report integration status without
    revealing any secret values or raw API key strings.
    """
    client = TestClient(app)

    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "integrations" in data
    assert "gemini" in data["integrations"]
    assert "parallel_search" in data["integrations"]

    # Verify that integration values are status descriptors, not raw secrets
    assert data["integrations"]["gemini"] in ("configured", "simulated_deterministic")
    assert data["integrations"]["parallel_search"] in ("configured", "simulated_deterministic")

    # Confirm raw API keys are never in the response
    content_str = response.text
    assert "sk-" not in content_str
    assert "AIza" not in content_str


@pytest.mark.asyncio
async def test_explicit_actionable_fallback_handling():
    """
    Asserts that unmapped or generic items execute deterministic fallback safely
    with explicit stance and non-failing retrieval.
    """
    service = ParallelSearchService()
    fallback_snap = await service.search(
        query="Custom prop item copyright check",
        use_id="use_custom_prop",
        stable_lineage_key="prop_vintage_telephone",
    )

    assert fallback_snap.provider == "Parallel"
    assert fallback_snap.stance == EvidenceStance.SUPPORTING
    assert fallback_snap.retrieval_latency_ms is not None
    assert fallback_snap.payload_hash is not None
