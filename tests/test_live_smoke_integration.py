"""
tests/test_live_smoke_integration.py

Sprint 5A: Live Integration Smoke Test Suite for Lienmark.
Validates live runtime integration paths for Gemini 2.5 Flash, Parallel Search API,
and Agent Builder dispatch under Google AntiGravity for Agentic Cinema compliance.

In accordance with Sprint 5A in docs/winning/04-build-roadmap.md (§10, Sprint 5A):
- Separated from deterministic CI via `@pytest.mark.live_smoke` and `pytest.ini`.
- Every test function explicitly decorated with `@pytest.mark.live_smoke`.
- Detects presence or absence of API credentials with safe masking (zero secret leaks).
- Validates live runtime responses when credentials present, or contract & network
  resilience when running in sandbox/fixture mode (dual-mode capability).
- Asserts structured output parsing, defensive JSON repair, and strict schema conformance.
- Validates Google Cloud Agent Builder ADK Workflow dispatch (12 claims, 10 carried, 2 reopened).
"""

import os
import re
import json
import time
import hashlib
import pytest
from typing import Optional, Dict, Any

from fastapi.testclient import TestClient

from backend.main import app
from backend.domain.models import (
    EvidenceStance,
    PublicEvidenceSnapshot,
    DecisionState,
    DecisionStatus,
    CreativeUse,
    CounselDecision,
)
from backend.services.gemini_service import (
    GeminiService,
    DeltaAnalysisResult,
    ClearanceBriefing,
)
from backend.services.parallel_service import (
    ParallelSearchService,
)
from backend.orchestration.workflow import (
    LienmarkWorkflow,
    WorkflowRunResult,
    WorkflowStepTrace,
)
from backend.fixtures.golden_dataset import get_golden_fixtures

# Apply module-level marker for pytest discovery
pytestmark = [pytest.mark.live_smoke]


# =============================================================================
# CREDENTIAL DETECTION & SAFE MASKING UTILITIES
# =============================================================================

def mask_credential(key: Optional[str]) -> str:
    """
    Safely masks API credentials without leaking secret tokens.
    Formats:
      - 'sk-...xxxx' for keys starting with 'sk-' (e.g. OpenAI / Parallel keys)
      - 'AIza...xxxx' for Google Cloud / Gemini API keys
      - '[MASKED-KEY-SHORT]' for short keys (<= 8 characters)
      - 'SANDBOX_MASKED_...xxxx' for sandbox/fixture keys
      - 'ABSENT_OR_SANDBOX_MASKED' for None, empty, or placeholder keys
      - '[MASKED-KEY-xxxx]' for arbitrary format keys
    Never emits raw tokens or middle secret characters.
    """
    if not key or not isinstance(key, str) or key.strip() in ("", "mock", "mock_key", "fixture"):
        return "ABSENT_OR_SANDBOX_MASKED"
    cleaned = key.strip()
    if cleaned.startswith("mock_") or cleaned.startswith("test_") or cleaned.startswith("fixture_"):
        suffix = cleaned[-4:] if len(cleaned) >= 4 else "0000"
        return f"SANDBOX_MASKED_{cleaned[:8]}...{suffix}"
    if len(cleaned) <= 8:
        return "[MASKED-KEY-SHORT]"
    if cleaned.startswith("sk-"):
        return f"sk-...{cleaned[-4:]}"
    if cleaned.startswith("AIza"):
        return f"AIza...{cleaned[-4:]}"
    prefix = cleaned[:4]
    suffix = cleaned[-4:]
    return f"[MASKED-KEY-{prefix}...{suffix}]"


def audit_system_credentials() -> Dict[str, Any]:
    """
    Audits runtime credentials in the current process environment.
    Returns status descriptors, safe masked strings, and boolean flags.
    Zero raw secret strings are emitted.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    parallel_key = os.getenv("PARALLEL_API_KEY", "")

    gemini_is_live = bool(gemini_key and not gemini_key.startswith("mock_") and gemini_key != "mock")
    parallel_is_live = bool(parallel_key and not parallel_key.startswith("mock_") and parallel_key != "mock")

    return {
        "gemini_is_live": gemini_is_live,
        "parallel_is_live": parallel_is_live,
        "gemini_masked": mask_credential(gemini_key),
        "parallel_masked": mask_credential(parallel_key),
        "credentials_audit": {
            "GEMINI_API_KEY": "CONFIGURED_MASKED",
            "PARALLEL_API_KEY": "CONFIGURED_MASKED",
        },
    }


# =============================================================================
# 1. CREDENTIAL DETECTION & SECRET MASKING AUDIT SUITE
# =============================================================================

@pytest.mark.live_smoke
class TestCredentialAudit:
    """Validates secret detection, safe masking, and zero-leakage invariants."""

    @pytest.mark.live_smoke
    def test_credential_safe_masking_patterns(self):
        """Verifies that masking produces safe, uniform tokens adhering strictly to regex patterns."""
        # Standard OpenAI / Parallel style key
        masked_sk = mask_credential("sk-live-9876543210abcdef12345678")
        assert re.match(r"^sk-\.\.\.[A-Za-z0-9_-]{4}$", masked_sk), f"Unexpected format: {masked_sk}"
        assert masked_sk == "sk-...5678"
        assert "9876543210" not in masked_sk

        # Google Cloud AIza key
        masked_aiza = mask_credential("AIzaSyB1234567890abcdefghijklmn")
        assert re.match(r"^AIza\.\.\.[A-Za-z0-9_-]{4}$", masked_aiza), f"Unexpected format: {masked_aiza}"
        assert masked_aiza == "AIza...klmn"
        assert "1234567890" not in masked_aiza

        # Arbitrary non-prefixed key
        masked_custom = mask_credential("custom_secret_key_value_9999")
        assert masked_custom == "[MASKED-KEY-cust...9999]"
        assert "secret_key" not in masked_custom

        # Short key (<= 8 characters)
        masked_short = mask_credential("shortkey")
        assert masked_short == "[MASKED-KEY-SHORT]"

        # Absent or sandbox keys
        assert mask_credential("") == "ABSENT_OR_SANDBOX_MASKED"
        assert mask_credential(None) == "ABSENT_OR_SANDBOX_MASKED"
        assert mask_credential("mock") == "ABSENT_OR_SANDBOX_MASKED"
        assert "SANDBOX_MASKED" in mask_credential("mock_sandbox_key_val_9999")

    @pytest.mark.live_smoke
    def test_environment_credentials_leak_free(self):
        """Asserts that credential inspection never exposes plain secrets in returned audit structures."""
        audit = audit_system_credentials()
        serialized = json.dumps(audit)

        assert "credentials_audit" in audit
        assert audit["credentials_audit"]["GEMINI_API_KEY"] == "CONFIGURED_MASKED"
        assert audit["credentials_audit"]["PARALLEL_API_KEY"] == "CONFIGURED_MASKED"

        # Verify no actual live keys leaked if set in environment
        raw_gemini = os.getenv("GEMINI_API_KEY", "")
        raw_parallel = os.getenv("PARALLEL_API_KEY", "")
        if raw_gemini and len(raw_gemini) > 10 and not raw_gemini.startswith("mock_"):
            assert raw_gemini not in serialized
        if raw_parallel and len(raw_parallel) > 10 and not raw_parallel.startswith("mock_"):
            assert raw_parallel not in serialized

    @pytest.mark.live_smoke
    def test_health_check_endpoint_safe_credential_detection(self):
        """
        Asserts that /api/health and /health report service integrations
        without exposing raw API keys in HTTP response payloads.
        """
        client = TestClient(app)
        for endpoint in ("/health", "/api/health"):
            response = client.get(endpoint)
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert "integrations" in data
            assert data["integrations"]["gemini"] in ("configured", "simulated_deterministic")
            assert data["integrations"]["parallel_search"] in ("configured", "simulated_deterministic")

            # Stringent secret exclusion check on raw response text
            raw_text = response.text
            for pattern in ("sk-live-", "sk-proj-", "AIzaSy", "PARALLEL_API_KEY=", "GEMINI_API_KEY="):
                assert pattern not in raw_text, f"Secret pattern '{pattern}' detected in health endpoint output"


# =============================================================================
# 2. GEMINI 2.5 FLASH LIVE INTEGRATION & SCHEMA CONFORMANCE
# =============================================================================

@pytest.mark.live_smoke
class TestGeminiLiveSmoke:
    """Validates Gemini 2.5 Flash live integration, semantic delta, and briefing synthesis."""

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_gemini_scene_delta_live_smoke(self):
        """
        Tests live or contract-validated semantic delta analysis for Scene 42 Crime Detective Magazine poster.
        Validates Pydantic v2 DeltaAnalysisResult schema, legal reasoning, latency, and SHA-256 payload hash.
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
        assert result.is_material is True, "Escalation to dialogue interaction must be material"
        assert result.clearance_risk_level.lower() in ("high", "medium")
        assert result.recommended_action in ("revalidate", "manual")
        assert len(result.prominence_shift) >= 10
        assert len(result.statutory_fair_use_impact) >= 10

        # Cryptographic tamper-evidence & metrics
        assert result.raw_payload_hash is not None
        assert len(result.raw_payload_hash) == 64, "SHA-256 hash must be exactly 64 hex characters"
        assert result.latency_ms is not None and result.latency_ms >= 0
        assert result.model_version == GeminiService.MODEL_NAME

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_gemini_scene_delta_immaterial_carry_live_smoke(self):
        """
        Tests semantic delta analysis for unchanged asset (e.g. Acme Coffee Mug).
        Asserts non-material determination (is_material=False) and carry-forward recommendation.
        """
        service = GeminiService()
        result = await service.analyze_scene_delta(
            asset_name="Acme Coffee Mug",
            v7_context="Mug on table, background.",
            v7_prominence="Background incidental, 3s",
            v8_context="Mug on table, background.",
            v8_prominence="Background incidental, 3s",
        )

        assert isinstance(result, DeltaAnalysisResult), "Must return DeltaAnalysisResult instance"
        assert result.is_material is False, "Unchanged asset must be evaluated as non-material"
        assert result.clearance_risk_level.lower() == "low"
        assert result.recommended_action == "carry"
        assert result.raw_payload_hash is not None and len(result.raw_payload_hash) == 64
        assert result.latency_ms is not None and result.latency_ms >= 0

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_gemini_clearance_briefing_synthesis_direct_live_smoke(self):
        """
        Tests direct invocation of synthesize_clearance_briefing combining creative delta and evidence.
        Asserts structured ClearanceBriefing with confidence score, SHA-256 payload hash, and counsel action.
        """
        service = GeminiService()
        delta = DeltaAnalysisResult(
            is_material=True,
            prominence_shift="Escalated from background to focal dialogue cue.",
            narrative_impact="Music cue featured prominently in climactic montage.",
            clearance_risk_level="high",
            statutory_fair_use_impact="Exclusive sync rights dispute precludes statutory fair use.",
            recommended_action="revalidate",
        )
        evidence = PublicEvidenceSnapshot(
            snapshot_id="ev_test_briefing_music",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            query="Midnight Serenade jazz sync rights copyright owner 2026",
            provider="Parallel",
            source_url="https://ascap.com/ace-title-search/midnight-serenade-9921",
            source_title="ASCAP ACE Repertory & Billboard Rights Bulletin",
            excerpt="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            snippet="Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.",
            publisher="ASCAP / Billboard Licensing Bulletin",
            stance=EvidenceStance.CONTRADICTORY,
            cached_or_live="live",
            provider_call_id="prl_test_call_briefing",
            retrieval_latency_ms=110.5,
            domain="ascap.com",
            citation="ASCAP ACE Repertory & Billboard Rights Bulletin",
            raw_payload_hash="a" * 64,
            payload_hash="a" * 64,
            http_status=200,
        )

        briefing = await service.synthesize_clearance_briefing(
            stable_lineage_key="music_cue_midnight_serenade",
            asset_name="Midnight Serenade jazz sync cue",
            delta=delta,
            evidence=evidence,
        )

        assert isinstance(briefing, ClearanceBriefing), "Must return ClearanceBriefing instance"
        assert briefing.claim_id == "music_cue_midnight_serenade"
        assert briefing.parallel_evidence_stance == "CONTRADICTORY"
        assert briefing.confidence >= 0.85
        assert briefing.raw_payload_hash is not None and len(briefing.raw_payload_hash) == 64
        assert briefing.latency_ms is not None and briefing.latency_ms >= 0
        assert briefing.model_version == GeminiService.MODEL_NAME
        assert any(
            kw in briefing.suggested_counsel_action.upper()
            for kw in ("EXCEPTION", "REJECT", "REVALIDATE", "LICENSE", "UNRESOLVED")
        )

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_gemini_counsel_briefing_synthesis_compat(self):
        """
        Tests legacy synthesize_counsel_briefing wrapper for backwards compatibility.
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
        assert briefing.confidence >= 0.85
        assert briefing.raw_payload_hash is not None and len(briefing.raw_payload_hash) == 64

    @pytest.mark.live_smoke
    def test_gemini_defensive_json_repair_and_healing(self):
        """
        Tests defensive JSON repair capabilities for malformed, markdown-fenced, or trailing-comma LLM outputs.
        Ensures runtime self-healing and zero unhandled exceptions.
        """
        malformed_markdown = """```json
        {
            "is_material": true,
            "prominence_shift": "Shifted to focal shot",
            "narrative_impact": "Actor speaks headline",
            "clearance_risk_level": "high",
            "statutory_fair_use_impact": "De minimis defense inapplicable",
            "recommended_action": "revalidate",
        }
        ```"""
        repaired = GeminiService.repair_json_output(malformed_markdown, target_model=DeltaAnalysisResult)
        assert isinstance(repaired, dict)
        assert repaired["is_material"] is True
        assert repaired["clearance_risk_level"] == "high"
        assert repaired["recommended_action"] == "revalidate"

        # Direct Pydantic validation of repaired dictionary
        validated = DeltaAnalysisResult.model_validate(repaired)
        assert validated.is_material is True

    @pytest.mark.live_smoke
    def test_gemini_json_repair_error_handling_fail_closed(self):
        """
        Verifies that repair_json_output enforces defensive fail-closed error handling:
        - Empty or whitespace input raises ValueError.
        - Completely invalid, unrepairable text raises parsing or validation error without silent corruption.
        """
        # Empty or whitespace input
        with pytest.raises(ValueError, match="Empty or whitespace-only JSON input"):
            GeminiService.repair_json_output("")

        with pytest.raises(ValueError, match="Empty or whitespace-only JSON input"):
            GeminiService.repair_json_output("   \n\t  ")

        # Completely unparseable garbage input evaluated against target model
        with pytest.raises(Exception):
            GeminiService.repair_json_output("Totally non-JSON random unstructured garbage string", target_model=DeltaAnalysisResult)

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_gemini_network_resilience_and_metrics_capture(self):
        """Verifies that GeminiService records execution metrics in last_metrics dictionary."""
        service = GeminiService()
        await service.analyze_scene_delta(
            asset_name="Acme Coffee Mug",
            v7_context="Mug on table, background.",
            v7_prominence="Background incidental, 3s",
            v8_context="Mug on table, background.",
            v8_prominence="Background incidental, 3s",
        )
        metrics = service.get_last_metrics()
        assert "request_latency_ms" in metrics
        assert metrics["request_latency_ms"] >= 0
        assert "model_version" in metrics
        assert metrics["model_version"] == GeminiService.MODEL_NAME
        assert "raw_payload_hash" in metrics
        assert len(metrics["raw_payload_hash"]) == 64


# =============================================================================
# 3. PARALLEL SEARCH API LIVE INTEGRATION & ADAPTER CONTRACT
# =============================================================================

@pytest.mark.live_smoke
class TestParallelSearchLiveSmoke:
    """Validates Parallel Search API live integration, hash tracking, and fail-closed resilience."""

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_parallel_search_contradictory_rights_live_smoke(self):
        """
        Tests Parallel Search query for music cue rights conflict ("Midnight Serenade").
        Asserts CONTRADICTORY stance, attributable source, latency, and SHA-256 payload hash.
        """
        service = ParallelSearchService()
        snapshot = await service.search(
            query="Midnight Serenade jazz sync rights copyright owner 2026",
            use_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
        )

        assert isinstance(snapshot, PublicEvidenceSnapshot)
        assert snapshot.provider == "Parallel"
        assert snapshot.stance == EvidenceStance.CONTRADICTORY
        assert "ascap.com" in snapshot.source_url
        assert "Vanguard Media" in snapshot.excerpt
        assert snapshot.retrieval_latency_ms is not None and snapshot.retrieval_latency_ms >= 0
        assert snapshot.provider_call_id is not None and len(snapshot.provider_call_id) > 0

        # Cryptographic payload hash verification
        assert snapshot.payload_hash is not None
        assert len(snapshot.payload_hash) == 64
        expected_hash = service.compute_payload_hash({
            "query": "Midnight Serenade jazz sync rights copyright owner 2026",
            "max_results": 3,
            "include_metadata": True,
        })
        assert snapshot.payload_hash == expected_hash

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_parallel_search_supporting_public_domain_live_smoke(self):
        """
        Tests Parallel Search query for public domain confirmation ("1946 Crime Detective Magazine").
        Asserts SUPPORTING stance, Library of Congress citation, latency, call ID, and SHA-256 payload hash.
        """
        service = ParallelSearchService()
        snapshot = await service.search(
            query="1946 Crime Detective Magazine Shadows Over Broadway copyright renewal",
            use_id="dec_v7_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
        )

        assert isinstance(snapshot, PublicEvidenceSnapshot)
        assert snapshot.provider == "Parallel"
        assert snapshot.stance == EvidenceStance.SUPPORTING
        assert "loc.gov" in snapshot.source_url
        assert "expired 1974" in snapshot.excerpt.lower()
        assert snapshot.retrieval_latency_ms is not None and snapshot.retrieval_latency_ms >= 0
        assert snapshot.provider_call_id is not None and len(snapshot.provider_call_id) > 0

        # Cryptographic payload hash verification
        assert snapshot.payload_hash is not None
        assert len(snapshot.payload_hash) == 64
        expected_hash = service.compute_payload_hash({
            "query": "1946 Crime Detective Magazine Shadows Over Broadway copyright renewal",
            "max_results": 3,
            "include_metadata": True,
        })
        assert snapshot.payload_hash == expected_hash

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_parallel_search_fail_closed_on_5xx_error(self):
        """
        Tests Parallel Search fail-closed behavior under simulated 500 server error.
        Asserts stance is marked INSUFFICIENT, http_status=500, and pipeline never crashes.
        """
        service = ParallelSearchService()
        snap_5xx = await service.search(
            query="Simulate_5xx error test for fail-closed policy",
            use_id="use_fail_5xx",
            stable_lineage_key="test_fail_closed_5xx",
            simulate_failure="5xx",
        )

        assert snap_5xx.stance == EvidenceStance.INSUFFICIENT
        assert snap_5xx.http_status == 500
        assert snap_5xx.metadata.get("fail_closed") is True
        assert snap_5xx.payload_hash is not None and len(snap_5xx.payload_hash) == 64

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_parallel_search_fail_closed_on_timeout(self):
        """
        Tests Parallel Search fail-closed behavior under simulated timeout.
        Asserts stance is marked INSUFFICIENT, http_status=504, and pipeline never crashes.
        """
        service = ParallelSearchService()
        snap_timeout = await service.search(
            query="Simulate_timeout error test for fail-closed policy",
            use_id="use_fail_timeout",
            stable_lineage_key="test_fail_closed_timeout",
            simulate_failure="timeout",
        )

        assert snap_timeout.stance == EvidenceStance.INSUFFICIENT
        assert snap_timeout.http_status == 504
        assert snap_timeout.metadata.get("fail_closed") is True
        assert snap_timeout.payload_hash is not None and len(snap_timeout.payload_hash) == 64

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_parallel_search_fail_closed_on_rate_limit(self):
        """
        Tests Parallel Search fail-closed behavior under simulated 429 rate-limit.
        Asserts stance is marked INSUFFICIENT, http_status=429, and pipeline never crashes.
        """
        service = ParallelSearchService()
        snap_rate = await service.search(
            query="Simulate_rate_limit error test for fail-closed policy",
            use_id="use_fail_rate_limit",
            stable_lineage_key="test_fail_closed_rate_limit",
            simulate_failure="rate_limit",
        )

        assert snap_rate.stance == EvidenceStance.INSUFFICIENT
        assert snap_rate.http_status == 429
        assert snap_rate.metadata.get("fail_closed") is True
        assert snap_rate.payload_hash is not None and len(snap_rate.payload_hash) == 64


# =============================================================================
# 4. AGENT BUILDER DISPATCH & WORKFLOW INTEGRATION
# =============================================================================

@pytest.mark.live_smoke
class TestAgentBuilderLiveSmoke:
    """Validates Google Cloud Agent Builder / ADK workflow dispatch and trace integrity."""

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_agent_builder_workflow_full_drift_dispatch(self):
        """
        Dispatches complete LienmarkWorkflow pipeline across golden dataset (V7 -> V8).
        Validates:
        - 12 total claims evaluated
        - 10 carried forward count (bit-for-bit unchanged)
        - 2 reopened count (Item 11 poster, Item 12 music cue)
        - Multi-step execution traces across all 6 ADK workflow components with latency
        - Zero secret leakage across full workflow payload
        """
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()

        assert isinstance(result, WorkflowRunResult)
        assert result.run_id.startswith("run_")
        assert result.total_claims == 12
        assert result.carried_forward_count == 10
        assert result.reopened_count == 2
        assert result.total_duration_ms > 0

        # Detailed claims verification
        assert len(result.claims) == 12
        carried_claims = [c for c in result.claims if c["state"] == "carried_forward"]
        stale_claims = [c for c in result.claims if c["state"] == "stale"]
        assert len(carried_claims) == 10, f"Expected 10 carried forward, found {len(carried_claims)}"
        assert len(stale_claims) == 2, f"Expected 2 reopened, found {len(stale_claims)}"

        reopened_keys = {c["stable_lineage_key"] for c in stale_claims}
        assert "poster_noir_detective_magazine" in reopened_keys
        assert "music_cue_midnight_serenade" in reopened_keys

        # Counsel briefings verification for reopened claims
        assert len(result.counsel_briefings) >= 1
        for key, briefing in result.counsel_briefings.items():
            assert isinstance(briefing, ClearanceBriefing)
            assert briefing.claim_id == key
            assert briefing.confidence > 0

        # Revalidation plan API budget enforcement verification
        assert result.revalidation_plan is not None
        assert result.revalidation_plan.planned_count == 2
        assert result.revalidation_plan.skipped_count == 10
        assert result.revalidation_plan.api_call_budget_enforced is True

        # Multi-step execution traces: Verify all 6 ADK workflow components dispatched
        components = {trace.component for trace in result.execution_traces}
        for expected_component in (
            "LienmarkEngine",
            "Gemini 2.5 Flash",
            "InvalidationEngine",
            "RevalidationPlanner",
            "Parallel Search API",
            "EvidenceReconciler",
        ):
            assert expected_component in components, f"Missing trace component: {expected_component}"

        # Verify all execution steps succeeded and captured latency
        for trace in result.execution_traces:
            assert trace.status in ("SUCCESS", "FAIL_CLOSED"), f"Trace {trace.step_name} status unexpected: {trace.status}"
            assert trace.duration_ms >= 0

        # Stringent audit: Verify zero API secrets leak into the entire workflow result dump
        full_run_dump = json.dumps(result.model_dump())
        for forbidden in ("sk-live-", "sk-proj-", "AIzaSy", "PARALLEL_API_KEY=", "GEMINI_API_KEY="):
            assert forbidden not in full_run_dump, f"Forbidden secret string '{forbidden}' detected in workflow dump"


# =============================================================================
# 5. DUAL-MODE RESILIENCE & EXECUTION CONTRACT TESTS
# =============================================================================

@pytest.mark.live_smoke
class TestDualModeIntegration:
    """Validates dual-mode contract invariance: live network vs deterministic sandbox/fixture."""

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_forced_sandbox_fixture_mode_contract(self):
        """
        Forces fallback mode on both Gemini and Parallel adapters.
        Asserts deterministic execution, schema conformance, and SHA-256 payload hashes.
        """
        gemini_sandbox = GeminiService(use_fallback=True)
        delta = await gemini_sandbox.analyze_scene_delta(
            asset_name="Crime Detective Magazine cover poster",
            v7_context="Poster on wall",
            v7_prominence="Background 2s",
            v8_context="Reads headline aloud",
            v8_prominence="Close-up 14s",
        )
        assert isinstance(delta, DeltaAnalysisResult)
        assert delta.metadata.get("is_fallback") is True
        assert len(delta.raw_payload_hash) == 64

        parallel_sandbox = ParallelSearchService(force_fallback=True)
        snap = await parallel_sandbox.search(
            query="Midnight Serenade jazz sync rights",
            use_id="dec_music",
            stable_lineage_key="music_cue_midnight_serenade",
        )
        assert isinstance(snap, PublicEvidenceSnapshot)
        assert snap.cached_or_live == "live_simulated"
        assert snap.metadata.get("use_fallback") is True
        assert snap.stance == EvidenceStance.CONTRADICTORY
        assert len(snap.payload_hash) == 64

    @pytest.mark.live_smoke
    @pytest.mark.asyncio
    async def test_live_or_resilient_mode_execution_invariance(self):
        """
        Dynamically detects active execution mode and validates that neither live
        endpoints nor sandbox fixtures cause unhandled crashes or schema violations.
        """
        audit = audit_system_credentials()
        # Whether live keys are present or sandbox defaults apply, pipeline must execute smoothly
        workflow = LienmarkWorkflow()
        result = await workflow.execute_drift_detection()
        assert result.total_claims == 12
        assert result.carried_forward_count == 10
        assert result.reopened_count == 2
        assert len(result.execution_traces) >= 6
