"""
Unit Tests for Lienmark InvalidationEngine
Tests the 12 -> 10 carried / 2 reopened -> 1 re-attested + 1 exception workflow.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from backend.domain.models import (
    ChangeKind,
    DecisionState,
    DecisionStatus,
    ReattestationRequest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)


def test_golden_fixture_counts():
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    assert len(v7_uses) == 12, "Base version must have exactly 12 creative uses"
    assert len(v8_uses) == 12, "Target version must have exactly 12 creative uses"
    assert len(v7_decisions) == 12, "Base version must have 12 approved decisions"
    assert len(v8_evidence) == 12, "Every claim must have an attributable evidence snapshot"


def test_12_to_10_carried_2_reopened():
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    assert len(validity_results) == 12

    carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
    stale = [v for v in validity_results if v.state == DecisionState.STALE]

    # The Core Magic Moment Assertion: Exactly 10 carried forward, exactly 2 reopened
    assert len(carried) == 10, f"Expected 10 carried forward, got {len(carried)}"
    assert len(stale) == 2, f"Expected 2 reopened (stale), got {len(stale)}"

    stale_map = {v.stable_lineage_key: v for v in stale}

    # Verify Item 11: Creative Drift
    poster_key = "poster_noir_detective_magazine"
    assert poster_key in stale_map
    assert stale_map[poster_key].reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert stale_map[poster_key].revalidation_action == "revalidate"
    assert stale_map[poster_key].creative_delta is not None
    assert stale_map[poster_key].creative_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED

    # Verify Item 12: Evidence Drift
    music_key = "music_cue_midnight_serenade"
    assert music_key in stale_map
    assert stale_map[music_key].reason_code == "EXTERNAL_EVIDENCE_SHIFT"
    assert stale_map[music_key].revalidation_action == "revalidate"
    assert stale_map[music_key].evidence_snapshot is not None
    assert stale_map[music_key].evidence_snapshot.provider == "Parallel"


def test_fail_closed_policy():
    """Verify that missing dependencies or corrupt data strictly fails closed (marks as STALE)."""
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Artificially remove target use for an item
    tampered_target_uses = [u for u in v8_uses if u.stable_lineage_key != "prop_vintage_telephone"]

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=tampered_target_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    tampered_result = next(
        v for v in validity_results if v.stable_lineage_key == "prop_vintage_telephone"
    )
    assert tampered_result.state == DecisionState.STALE
    assert "FAIL_CLOSED" in tampered_result.reason_code or "UNEXPECTED" in tampered_result.reason_code


def test_exceptions_schedule_reconciliation():
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    # Counsel re-attests Item 11 (poster) with Fair Use rationale
    # Item 12 (music) is marked as an unresolved exception
    poster_key = "poster_noir_detective_magazine"
    music_key = "music_cue_midnight_serenade"

    reattestations = {
        poster_key: ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key=poster_key,
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork verified in public domain via LOC registration records retrieved by Parallel Search; non-infringing.",
            reviewer_name="Sarah Jenkins, Esq. (Clearance Counsel)",
        ),
        music_key: ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key=music_key,
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media active ownership conflict identified via Parallel Search; replace cue with alternate track.",
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

    # Verify counts for the final stage: 12 claims -> 10 carried + 1 re-attested + 1 exception
    assert schedule.total_claims == 12
    assert schedule.carried_forward_count == 10
    assert schedule.reopened_count == 2
    assert schedule.re_attested_count == 1
    assert schedule.unresolved_exception_count == 1
    assert len(schedule.items) == 12
