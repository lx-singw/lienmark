"""
End-to-End Pipeline Integration Tests for Lienmark
Tests the complete multi-step workflow:
Ingestion -> Semantic Delta (Gemini) -> Invalidation -> Targeted Search (Parallel) -> Exceptions Schedule.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from backend.domain.models import DecisionStatus, ReattestationRequest
from backend.orchestration.workflow import LienmarkWorkflow
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import get_golden_fixtures


@pytest.mark.asyncio
async def test_workflow_execution():
    workflow = LienmarkWorkflow()
    result = await workflow.execute_drift_detection()

    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2
    assert len(result.claims) == 12
    assert len(result.execution_traces) >= 4

    # Verify Parallel Search traces exist
    parallel_traces = [t for t in result.execution_traces if "Parallel Search" in t.component]
    assert len(parallel_traces) == 2, "Must execute targeted Parallel search for both reopened claims"
    for pt in parallel_traces:
        assert pt.status == "SUCCESS"
        assert pt.details.get("source_url")
        assert pt.details.get("stance")

    # Verify Gemini delta trace exists
    gemini_traces = [t for t in result.execution_traces if "Gemini" in t.component]
    assert len(gemini_traces) >= 1
    assert gemini_traces[0].details.get("is_material") is True

    # Verify Counsel briefings generated
    assert "poster_noir_detective_magazine" in result.counsel_briefings
    assert "music_cue_midnight_serenade" in result.counsel_briefings
    assert (
        result.counsel_briefings["music_cue_midnight_serenade"].parallel_evidence_stance
        == "CONTRADICTORY"
    )


@pytest.mark.asyncio
async def test_full_review_to_exceptions_schedule_flow():
    workflow = LienmarkWorkflow()
    result = await workflow.execute_drift_detection()

    v7_uses, v8_uses, v7_decisions, initial_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=initial_evidence,
        target_version_id="v8",
    )

    # Counsel reviews the 2 reopened claims
    poster_key = "poster_noir_detective_magazine"
    music_key = "music_cue_midnight_serenade"

    reattestations = {
        poster_key: ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key=poster_key,
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Public domain status of 1946 cover art verified via Library of Congress catalog records from Parallel search.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        ),
        music_key: ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key=music_key,
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel search; cue excluded from final sound mix.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        ),
    }

    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validity_results,
        reattestations=reattestations,
    )

    assert schedule.total_claims == 12
    assert schedule.carried_forward_count == 10
    assert schedule.reopened_count == 2
    assert schedule.re_attested_count == 1
    assert schedule.unresolved_exception_count == 1

    # Check item details in schedule
    poster_item = next(i for i in schedule.items if i.stable_lineage_key == poster_key)
    assert poster_item.v8_evaluation_state == "re_attested"
    assert "Sarah Jenkins" in poster_item.counsel_action

    music_item = next(i for i in schedule.items if i.stable_lineage_key == music_key)
    assert music_item.v8_evaluation_state == "exception"
    assert "Vanguard Media" in music_item.counsel_action
