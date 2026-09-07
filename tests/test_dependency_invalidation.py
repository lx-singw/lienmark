"""
tests/test_dependency_invalidation.py
Deterministic Dependency Graph & Invalidation Engine Verification Suite.

Validates the Zero False Invalidation Law, Causal Graph Lineage,
Fail-Closed Invalidation Policy, and 6 Underwriting Gap Remediations:
1. Canonical V7 -> V8 evaluation (12 = 10 carried + 1 creative + 1 evidence).
2. Zero False Carries Law (fail-closed under any mutated attribute).
3. Scene/Timecode Shift detection (SCENE_TIMECODE_ALTERED).
4. Exploitation Scope Drift detection (territory, media, context).
5. Severed Evidence Lineage Fallback (LOC/ASCAP snapshot preservation).
6. Unapproved Decision Protection (NEEDS_REVIEW never carries forward).
7. Arbitrary Additions, Deletions, Modifications.
8. Idempotent Execution Check (V7 -> V7 yields 100% carried).
9. Input Permutation Invariance (shuffling inputs yields bit-for-bit identical results).
10. Dynamic Version Lineage ($V_8 \to V_9$ without hardcoded "v8").
11. Cross-Version Approval Bleed Guardrail in process_counsel_decision.
"""

from __future__ import annotations

import copy
import random
import pytest

from backend.domain.models import (
    ChangeKind,
    CreativeUse,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    ReviewAction,
    CensusDisposition,
    WorkflowReason,
)
from backend.core.invalidation_engine import (
    InvalidationEngine,
    evaluate_version_delta,
    process_counsel_decision,
)
from backend.fixtures.golden_dataset import (
    get_golden_fixtures,
    compute_context_hash,
)


# =============================================================================
# 1. Canonical V7 -> V8 Evaluation: 12 = 10 carried + 1 creative + 1 evidence
# =============================================================================
def test_canonical_v7_to_v8_mathematical_conservation():
    """
    Assert the core mathematical conservation invariant:
    12 total claims = 10 carried forward + 1 creative drift + 1 evidence drift.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    assert len(results) == 12, "Total evaluated claims must equal 12"

    carried = [r for r in results if r.state == DecisionState.CARRIED_FORWARD]
    stale = [r for r in results if r.state == DecisionState.STALE]

    assert len(carried) == 10, f"Expected exactly 10 carried forward, got {len(carried)}"
    assert len(stale) == 2, f"Expected exactly 2 stale claims, got {len(stale)}"

    stale_map = {r.stable_lineage_key: r for r in stale}

    # Verify Creative Drift on Item 11 (poster)
    poster_key = "poster_noir_detective_magazine"
    assert poster_key in stale_map
    poster_res = stale_map[poster_key]
    assert poster_res.reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert poster_res.creative_delta is not None
    assert poster_res.creative_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert "duration_or_prominence" in poster_res.creative_delta.changed_fields

    # Verify External Evidence Drift on Item 12 (music cue)
    music_key = "music_cue_midnight_serenade"
    assert music_key in stale_map
    music_res = stale_map[music_key]
    assert music_res.reason_code == "EXTERNAL_EVIDENCE_SHIFT"
    assert music_res.evidence_snapshot is not None
    assert music_res.evidence_snapshot.stance == EvidenceStance.CONTRADICTORY


# =============================================================================
# 2. Zero False Carries Law
# =============================================================================
def test_zero_false_carries_on_any_creative_or_evidence_tampering():
    """
    Zero False Carries: Mutating ANY rights-bearing parameter of a carried item
    must immediately prevent it from carrying forward.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Tamper with Item 1 (vintage telephone): change dialogue context
    mutated_v8_uses = [copy.deepcopy(u) for u in v8_uses]
    phone_use = next(u for u in mutated_v8_uses if u.stable_lineage_key == "prop_vintage_telephone")
    phone_use.context = "Character smashes the telephone against the desk in rage."
    phone_use.context_hash = compute_context_hash(phone_use.context, phone_use.duration_or_prominence)

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=mutated_v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    phone_res = next(r for r in results if r.stable_lineage_key == "prop_vintage_telephone")
    assert phone_res.state == DecisionState.STALE, "Tampered item must NOT carry forward"
    assert phone_res.reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert "context" in phone_res.creative_delta.changed_fields

    # Carried count should now be 9, stale count 3
    carried = [r for r in results if r.state == DecisionState.CARRIED_FORWARD]
    assert len(carried) == 9


# =============================================================================
# 3. Scene / Timecode Shift Detection (Underwriting Gap 1)
# =============================================================================
def test_scene_timecode_shift_triggers_material_modification():
    """
    Underwriting Gap 1: Moving an asset from Scene 04 to Scene 42 without changing
    text context still alters shot geometry and surrounding rights context.
    Must flag SCENE_TIMECODE_ALTERED and MATERIALLY_MODIFIED.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    mutated_v8_uses = [copy.deepcopy(u) for u in v8_uses]
    phone_use = next(u for u in mutated_v8_uses if u.stable_lineage_key == "prop_vintage_telephone")
    phone_use.scene_or_timecode = "Scene 42 - Interrogation Room (Shifted from Scene 04)"

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=mutated_v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    phone_res = next(r for r in results if r.stable_lineage_key == "prop_vintage_telephone")
    assert phone_res.state == DecisionState.STALE
    assert phone_res.creative_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert "scene_or_timecode" in phone_res.creative_delta.changed_fields
    assert "SCENE_TIMECODE_ALTERED" in phone_res.creative_delta.reason_codes


# =============================================================================
# 4. Exploitation Scope Drift Detection (Underwriting Gap 6)
# =============================================================================
def test_exploitation_scope_drift_detection():
    """
    Underwriting Gap 6: Scope expansions (intended_territory, intended_media,
    intended_context) invalidate prior clearance determinations.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Base use has US territory, target expands to Worldwide ['US', 'UK', 'EU', 'JP']
    mutated_v7_uses = [copy.deepcopy(u) for u in v7_uses]
    mutated_v8_uses = [copy.deepcopy(u) for u in v8_uses]

    base_car = next(u for u in mutated_v7_uses if u.stable_lineage_key == "car_ford_sedan_1949")
    target_car = next(u for u in mutated_v8_uses if u.stable_lineage_key == "car_ford_sedan_1949")

    base_car.intended_territory = ["US"]
    target_car.intended_territory = ["US", "UK", "EU", "JP"]

    deltas = InvalidationEngine.detect_creative_deltas(mutated_v7_uses, mutated_v8_uses)
    car_delta = deltas["car_ford_sedan_1949"]

    assert car_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert "intended_territory" in car_delta.changed_fields
    assert "TERRITORY_SCOPE_ALTERED" in car_delta.reason_codes

    # Test media scope alteration
    base_car.intended_media = ["theatrical"]
    target_car.intended_media = ["theatrical", "svod", "broadcast"]
    target_car.intended_territory = ["US"]  # reset territory

    deltas_media = InvalidationEngine.detect_creative_deltas(mutated_v7_uses, mutated_v8_uses)
    car_delta_media = deltas_media["car_ford_sedan_1949"]
    assert "intended_media" in car_delta_media.changed_fields
    assert "MEDIA_SCOPE_ALTERED" in car_delta_media.reason_codes

    # Test exploitation context alteration (feature -> trailer)
    base_car.intended_context = "feature"
    target_car.intended_context = "promotional_clip"
    target_car.intended_media = ["theatrical"]  # reset media

    deltas_ctx = InvalidationEngine.detect_creative_deltas(mutated_v7_uses, mutated_v8_uses)
    car_delta_ctx = deltas_ctx["car_ford_sedan_1949"]
    assert "intended_context" in car_delta_ctx.changed_fields
    assert "EXPLOITATION_CONTEXT_ALTERED" in car_delta_ctx.reason_codes


# =============================================================================
# 5. Severed Evidence Lineage Fallback (Underwriting Gap 3)
# =============================================================================
def test_severed_evidence_lineage_fallback_preserves_citations():
    """
    Underwriting Gap 3: When selective ingestion yields no new evidence snapshot
    for unimpacted claims, the engine must fall back to prior decision evidence_snapshot
    so public domain citations (LOC, ASCAP, etc.) are never severed.
    """
    v7_uses, v8_uses, v7_decisions, _ = get_golden_fixtures()

    # Create prior decisions that explicitly store evidence_snapshot
    decisions_with_snapshots = [copy.deepcopy(d) for d in v7_decisions]
    sample_snapshot = PublicEvidenceSnapshot(
        snapshot_id="snap_loc_telephone_001",
        use_id="use_v7_telephone",
        stable_lineage_key="prop_vintage_telephone",
        query="Western Electric 1950 rotary phone patent public domain",
        source_title="US Patent and Trademark Office Historical Archive",
        source_url="https://patents.google.com/patent/US2500000A",
        stance=EvidenceStance.SUPPORTING,
        excerpt="Western Electric Model 500 patent expired 1971; utility design in public domain.",
        provider="Parallel",
    )
    phone_dec = next(d for d in decisions_with_snapshots if d.stable_lineage_key == "prop_vintage_telephone")
    phone_dec.evidence_snapshot = sample_snapshot

    # In selective ingestion, target evidence snapshots map is empty for unchanged claims
    empty_target_evidence = {}

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=decisions_with_snapshots,
        evidence_snapshots=empty_target_evidence,
        target_version_id="v8",
    )

    phone_res = next(r for r in results if r.stable_lineage_key == "prop_vintage_telephone")
    assert phone_res.state == DecisionState.CARRIED_FORWARD
    assert phone_res.evidence_snapshot is not None
    assert phone_res.evidence_snapshot.snapshot_id == "snap_loc_telephone_001"
    assert phone_res.evidence_snapshot.source_url == "https://patents.google.com/patent/US2500000A"

    # Verify Schedule generation also preserves the fallback citation
    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=results,
        prior_decisions=decisions_with_snapshots,
    )

    phone_item = next(i for i in schedule.items if i.stable_lineage_key == "prop_vintage_telephone")
    assert len(phone_item.evidence_citations) > 0
    assert phone_item.evidence_citations[0]["source_url"] == "https://patents.google.com/patent/US2500000A"


# =============================================================================
# 6. Unapproved Decision Protection (Underwriting Gap 2)
# =============================================================================
def test_unapproved_decisions_never_carry_forward_as_cleared():
    """
    Underwriting Gap 2: Prior decisions with NEEDS_REVIEW or REJECTED status
    must NEVER silently carry forward as CARRIED_FORWARD even when creative delta
    is UNCHANGED.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    mutated_decisions = [copy.deepcopy(d) for d in v7_decisions]
    phone_dec = next(d for d in mutated_decisions if d.stable_lineage_key == "prop_vintage_telephone")
    phone_dec.status = DecisionStatus.NEEDS_REVIEW
    phone_dec.rationale = "Pending clearance counsel verification of prop manufacturer logo."

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=mutated_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    phone_res = next(r for r in results if r.stable_lineage_key == "prop_vintage_telephone")
    assert phone_res.state == DecisionState.STALE
    assert phone_res.reason_code == "PRIOR_DECISION_UNAPPROVED"
    assert phone_res.revalidation_action == "revalidate"
    assert "unapproved status" in phone_res.explanation


# =============================================================================
# 7. Arbitrary Additions, Deletions, Modifications
# =============================================================================
def test_arbitrary_script_additions_and_deletions():
    """
    Test arbitrary script changes:
    - Adding a new claim introduces state NEW with reason NEW_UNCLEARED_CLAIM.
    - Removing a claim produces state REMOVED with reason CLAIM_REMOVED_FROM_SCRIPT.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Add a brand new use in v8
    new_use = CreativeUse(
        use_id="use_v8_new_neon_sign",
        version_id="v8",
        scene_or_timecode="Scene 99 - Times Square",
        asset_type="trademark",
        description="Glowing neon billboard featuring Acme Corp logo.",
        duration_or_prominence="Focal establishing shot, 8s",
        context="Protagonist looks up at the towering neon sign.",
        stable_lineage_key="billboard_acme_neon",
        context_hash=compute_context_hash("Protagonist looks up at the towering neon sign.", "Focal establishing shot, 8s"),
    )
    expanded_v8_uses = v8_uses + [new_use]

    # Delete an existing use from v8 (e.g. car_ford_sedan_1949)
    filtered_v8_uses = [u for u in expanded_v8_uses if u.stable_lineage_key != "car_ford_sedan_1949"]

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=filtered_v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    result_map = {r.stable_lineage_key: r for r in results}

    # Verify new claim
    assert "billboard_acme_neon" in result_map
    new_res = result_map["billboard_acme_neon"]
    assert new_res.state == DecisionState.NEW
    assert new_res.reason_code == "NEW_UNCLEARED_CLAIM"

    # Verify removed claim
    assert "car_ford_sedan_1949" in result_map
    removed_res = result_map["car_ford_sedan_1949"]
    assert removed_res.state == DecisionState.REMOVED
    assert removed_res.reason_code == "CLAIM_REMOVED_FROM_SCRIPT"


# =============================================================================
# 8. Idempotent Execution Check
# =============================================================================
def test_idempotent_self_evaluation():
    """
    Idempotent execution: evaluating (v7, v7) yields 100% carried forward
    with 0 stale claims, preserving all existing approved clearances.
    """
    v7_uses, _, v7_decisions, _ = get_golden_fixtures()

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v7_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots={},
        target_version_id="v7",
    )

    assert len(results) == 12
    assert all(r.state == DecisionState.CARRIED_FORWARD for r in results)
    assert all(r.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED" for r in results)


# =============================================================================
# 9. Input Permutation Invariance
# =============================================================================
def test_permutation_invariance():
    """
    Input order invariance: shuffling input lists in any arbitrary order
    yields bit-for-bit identical results.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    baseline_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    # Shuffle inputs multiple times
    for seed in [42, 1337, 9999]:
        rng = random.Random(seed)

        shuffled_v7 = list(v7_uses)
        shuffled_v8 = list(v8_uses)
        shuffled_dec = list(v7_decisions)

        rng.shuffle(shuffled_v7)
        rng.shuffle(shuffled_v8)
        rng.shuffle(shuffled_dec)

        shuffled_results = InvalidationEngine.evaluate_invalidation(
            base_uses=shuffled_v7,
            target_uses=shuffled_v8,
            prior_decisions=shuffled_dec,
            evidence_snapshots=v8_evidence,
            target_version_id="v8",
        )

        assert len(shuffled_results) == len(baseline_results)
        for base_r, shuf_r in zip(baseline_results, shuffled_results):
            assert base_r.stable_lineage_key == shuf_r.stable_lineage_key
            assert base_r.state == shuf_r.state
            assert base_r.reason_code == shuf_r.reason_code
            assert base_r.revalidation_action == shuf_r.revalidation_action


# =============================================================================
# 10. Dynamic Version Lineage (Underwriting Gap 5)
# =============================================================================
def test_dynamic_version_lineage_beyond_v8():
    """
    Underwriting Gap 5: The engine must dynamically evaluate arbitrary version pairs
    such as V8 -> V9 or V10 -> V11 with full reconciliation, without any hardcoded
    'v8' fallback strings.
    """
    _, v8_uses, _, v8_evidence = get_golden_fixtures()

    # Synthesize V8 as base and V9 as target
    v8_base_uses = [copy.deepcopy(u) for u in v8_uses]
    v9_target_uses = [copy.deepcopy(u) for u in v8_uses]
    for u in v9_target_uses:
        u.version_id = "v9"

    # In V8, counsel had cleared midnight serenade (e.g. via replacement cue or license)
    v9_evidence = copy.deepcopy(v8_evidence)
    v9_evidence["music_cue_midnight_serenade"].stance = EvidenceStance.SUPPORTING

    # Create V8 decisions
    v8_decisions = [
        CounselDecision(
            decision_id=f"dec_v8_{u.stable_lineage_key}",
            use_id=u.use_id,
            stable_lineage_key=u.stable_lineage_key,
            applicable_version_id="v8",
            status=DecisionStatus.APPROVED,
            rationale="Approved for V8 cut.",
        )
        for u in v8_base_uses
    ]

    # Mutate one item in V9 (vintage telephone moved to Scene 88)
    phone_v9 = next(u for u in v9_target_uses if u.stable_lineage_key == "prop_vintage_telephone")
    phone_v9.scene_or_timecode = "Scene 88 - Climax"

    results_v9 = InvalidationEngine.evaluate_invalidation(
        base_uses=v8_base_uses,
        target_uses=v9_target_uses,
        prior_decisions=v8_decisions,
        evidence_snapshots=v9_evidence,
        target_version_id="v9",
    )

    assert len(results_v9) == 12
    carried_v9 = [r for r in results_v9 if r.state == DecisionState.CARRIED_FORWARD]
    stale_v9 = [r for r in results_v9 if r.state == DecisionState.STALE]

    assert len(carried_v9) == 11
    assert len(stale_v9) == 1
    assert stale_v9[0].stable_lineage_key == "prop_vintage_telephone"

    # Test Exceptions Schedule generation for V8 -> V9
    reattestation_v9 = {
        "prop_vintage_telephone": ReattestationRequest(
            decision_id="dec_v9_telephone",
            stable_lineage_key="prop_vintage_telephone",
            version_id="v9",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Prop in Scene 88 confirmed unchanged Western Electric rotary phone; approved.",
        )
    }

    schedule_v9 = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v8",
        target_version_id="v9",
        target_uses=v9_target_uses,
        validity_results=results_v9,
        reattestations=reattestation_v9,
        prior_decisions=v8_decisions,
    )

    assert schedule_v9.target_version_id == "v9"
    assert schedule_v9.carried_forward_count == 11
    assert schedule_v9.re_attested_count == 1
    assert schedule_v9.unresolved_exception_count == 0


# =============================================================================
# 11. Cross-Version Approval Bleed Guardrail (Underwriting Gap 4)
# =============================================================================
def test_cross_version_approval_bleed_prevention_in_counsel_decision():
    """
    Underwriting Gap 4: In process_counsel_decision, validating target_version_id
    against claim.version_id must strictly reject cross-version attempts.
    """
    claim = {
        "claim_id": "claim_scene_04_phone",
        "version_id": "v7",
        "stable_lineage_key": "prop_vintage_telephone",
        "disposition": "needs_review",
    }

    # Attempting to record a v8 approval on a v7 claim must raise ValueError
    with pytest.raises(ValueError, match="Version mismatch"):
        process_counsel_decision(
            claim=claim,
            action=ReviewAction.RE_ATTEST,
            target_version_id="v8",
            counsel_directive="Re-attest for V8",
        )

    # Correct version matches succeeds
    result = process_counsel_decision(
        claim=claim,
        action=ReviewAction.RE_ATTEST,
        target_version_id="v7",
        counsel_name="Sarah Jenkins, Esq.",
    )
    assert result.disposition == CensusDisposition.APPROVED
    assert result.claim["disposition"] == CensusDisposition.APPROVED
