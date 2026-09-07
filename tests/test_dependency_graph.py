"""
Unit and Property-Based Tests for Lienmark ClearanceDependencyGraph & InvalidationEngine
Phase 2 Differentiating Engine — Sprint 2B Dependency Graph & Policy Gate.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import random
import pytest
from typing import List, Dict

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    ChangeKind,
    ClarificationRequest,
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceStance,
    PublicEvidenceSnapshot,
    ReattestationRequest,
    SceneContext,
    ScriptBeat,
)
from backend.core.dependency_graph import (
    ClearanceDependencyGraph,
    DependencyEdge,
    DependencyKind,
    DependencyNode,
    InvalidationNotice,
    NodeType,
    ClearanceGraphError,
    CycleDetectedError,
    NodeNotFoundError,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import get_golden_fixtures


# =============================================================================
# 1. DAG MATHEMATICAL FORMULATION & CONSTRUCTION TESTS
# =============================================================================

def test_dag_mathematical_formulation_nodes_and_edges():
    """
    Test formal DAG mathematical formulation:
    V = {U, D, E, A}
    E_dep subseteq V x V
    """
    graph = ClearanceDependencyGraph()

    # 1. CreativeUse node (U in V_U)
    use_node = graph.add_creative_use(
        CreativeUse(
            use_id="use_poster_01",
            version_id="v7",
            scene_or_timecode="Scene 42",
            asset_type="artwork",
            description="Noir detective magazine cover",
            duration_or_prominence="2s background",
            context="Out of focus on office wall",
            stable_lineage_key="poster_noir_detective_magazine",
            context_hash="a1b2c3d4e5f67890",
        )
    )
    assert use_node.node_type == NodeType.CREATIVE_USE
    assert graph.has_node("use_poster_01")

    # 2. EvidenceSnapshot node (E in V_E)
    evidence_node = graph.add_evidence_snapshot(
        PublicEvidenceSnapshot(
            snapshot_id="ev_poster_01",
            use_id="use_poster_01",
            stable_lineage_key="poster_noir_detective_magazine",
            query="noir detective magazine copyright 1939",
            source_url="https://loc.gov/copyright/1939",
            source_title="LOC Catalog of Copyright Entries 1939",
            excerpt="No renewal registration on file; work in public domain",
            stance=EvidenceStance.SUPPORTING,
        )
    )
    assert evidence_node.node_type == NodeType.EVIDENCE_SNAPSHOT
    assert graph.has_node("ev_poster_01")

    # 3. ContractAgreement node (A in V_A)
    contract_node = graph.add_contract_agreement(
        ContractAgreement(
            agreement_id="agr_noir_01",
            stable_lineage_key="poster_noir_detective_magazine",
            licensor="Retro Publishing Archives LLC",
            licensee="Production Co LLC",
            scope="Theatrical and worldwide streaming distribution",
            term="Perpetual worldwide",
            agreement_hash="c3d4e5f6a1b27890",
            is_active=True,
        )
    )
    assert contract_node.node_type == NodeType.CONTRACT_AGREEMENT
    assert graph.has_node("agr_noir_01")

    # 4. CounselDecision node (D in V_D)
    decision_node = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_poster_01",
            use_id="use_poster_01",
            stable_lineage_key="poster_noir_detective_magazine",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Cleared: artwork confirmed public domain via LOC records; background use.",
            dependency_ids=["ev_poster_01", "agr_noir_01"],
        )
    )
    assert decision_node.node_type == NodeType.COUNSEL_DECISION
    assert graph.has_node("dec_poster_01")

    # 5. Directed edges E_dep subseteq V x V:
    # (use_node, decision_node), (evidence_node, decision_node), (contract_node, decision_node)
    edge_use = graph.add_dependency(
        dependent_id="dec_poster_01",
        dependency_id="use_poster_01",
        kind=DependencyKind.CREATIVE_CONTEXT,
    )
    edge_ev = graph.add_dependency(
        dependent_id="dec_poster_01",
        dependency_id="ev_poster_01",
        kind=DependencyKind.EVIDENCE_STANCE,
    )
    edge_agr = graph.add_dependency(
        dependent_id="dec_poster_01",
        dependency_id="agr_noir_01",
        kind=DependencyKind.CONTRACTUAL_GRANT,
    )

    assert edge_use.kind == DependencyKind.CREATIVE_CONTEXT
    assert edge_ev.kind == DependencyKind.EVIDENCE_STANCE
    assert edge_agr.kind == DependencyKind.CONTRACTUAL_GRANT

    # Verify upstream dependencies and downstream dependents
    upstream = graph.get_dependencies("dec_poster_01")
    assert len(upstream) == 3
    assert set(upstream) == {"use_poster_01", "ev_poster_01", "agr_noir_01"}

    assert graph.get_dependents("use_poster_01") == ["dec_poster_01"]
    assert graph.get_dependents("ev_poster_01") == ["dec_poster_01"]
    assert graph.get_dependents("agr_noir_01") == ["dec_poster_01"]


def test_dag_cycle_detection_enforcement():
    """
    Test that the graph strictly prevents and detects cycles (Acyclicity guarantee).
    Self-referential edges and transitive cycles must raise CycleDetectedError.
    """
    graph = ClearanceDependencyGraph()
    use_a = graph.add_creative_use(
        CreativeUse(
            use_id="use_A",
            version_id="v7",
            scene_or_timecode="Scene 1",
            asset_type="prop",
            description="Prop A",
            duration_or_prominence="1s",
            context="desk",
            stable_lineage_key="prop_a",
            context_hash="hash_a",
        )
    )
    dec_a = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_A",
            use_id="use_A",
            stable_lineage_key="prop_a",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Approved",
        )
    )
    dec_b = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_B",
            use_id="use_A",
            stable_lineage_key="prop_a",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Approved B",
        )
    )

    # 1. Self-referential edge must fail (assert ValueError or CycleDetectedError)
    with pytest.raises(ValueError):
        graph.add_dependency(dependent_id="dec_A", dependency_id="dec_A")
    with pytest.raises(CycleDetectedError):
        graph.add_dependency(dependent_id="dec_A", dependency_id="dec_A")

    # 2. Add dec_A depends on use_A, and dec_B depends on dec_A
    graph.add_dependency(dependent_id="dec_A", dependency_id="use_A")
    graph.add_dependency(dependent_id="dec_B", dependency_id="dec_A")

    # 3. Closing the cycle (use_A depends on dec_B) must raise ValueError / CycleDetectedError
    with pytest.raises(ValueError):
        graph.add_dependency(dependent_id="use_A", dependency_id="dec_B")
    with pytest.raises(CycleDetectedError):
        graph.add_dependency(dependent_id="use_A", dependency_id="dec_B")

    assert not graph.has_cycles()


# =============================================================================
# 2. TOPOLOGICAL RESOLUTION & PERMUTATION INVARIANCE TESTS
# =============================================================================

def test_deterministic_topological_sort_order():
    """
    Asserts topological sort orders dependencies before dependents,
    with deterministic tie-breaking by canonical sort key.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    graph = ClearanceDependencyGraph.build_clearance_graph(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
    )

    sorted_nodes = graph.topological_sort()
    assert len(sorted_nodes) == len(graph.all_nodes())

    node_pos = {n.node_id: idx for idx, n in enumerate(sorted_nodes)}

    # Every dependency must appear BEFORE its dependent in the topological ordering
    for dec in v7_decisions:
        deps = graph.get_dependencies(dec.decision_id)
        for dep_id in deps:
            assert node_pos[dep_id] < node_pos[dec.decision_id], (
                f"Topological violation: dependency {dep_id} (idx {node_pos[dep_id]}) "
                f"must precede dependent {dec.decision_id} (idx {node_pos[dec.decision_id]})"
            )


def test_input_permutation_invariance():
    """
    Acceptance Criterion: Reordering inputs does not change the result.
    Evaluates 10 distinct randomized permutations of base uses, target uses,
    decisions, and evidence snapshots.
    All permutations MUST produce identical DecisionValidity results.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Baseline canonical evaluation
    canonical_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    rng = random.Random(42)

    for trial in range(10):
        shuffled_v7_uses = list(v7_uses)
        shuffled_v8_uses = list(v8_uses)
        shuffled_v7_decisions = list(v7_decisions)
        shuffled_evidence_items = list(v8_evidence.items())

        rng.shuffle(shuffled_v7_uses)
        rng.shuffle(shuffled_v8_uses)
        rng.shuffle(shuffled_v7_decisions)
        rng.shuffle(shuffled_evidence_items)
        shuffled_evidence = dict(shuffled_evidence_items)

        permuted_results = InvalidationEngine.evaluate_invalidation(
            base_uses=shuffled_v7_uses,
            target_uses=shuffled_v8_uses,
            prior_decisions=shuffled_v7_decisions,
            evidence_snapshots=shuffled_evidence,
            target_version_id="v8",
        )

        assert len(permuted_results) == len(canonical_results)

        for c_res, p_res in zip(canonical_results, permuted_results):
            assert c_res.stable_lineage_key == p_res.stable_lineage_key
            assert c_res.state == p_res.state
            assert c_res.reason_code == p_res.reason_code
            assert c_res.revalidation_action == p_res.revalidation_action
            assert c_res.changed_dependency_ids == p_res.changed_dependency_ids


# =============================================================================
# 3. MATHEMATICAL IDEMPOTENCY TESTS: f(v, v) = f(v, v)
# =============================================================================

def test_mathematical_idempotency_same_version():
    """
    Acceptance Criterion: Rerunning the same version is idempotent.
    f(v, v) = f(v, v)
    When target_uses == base_uses and evidence is supporting, 100% of decisions
    carry forward unchanged (0 stale decisions).
    """
    v7_uses, _, v7_decisions, _ = get_golden_fixtures()

    # Construct supporting evidence for V7 base uses
    v7_evidence = {
        u.stable_lineage_key: PublicEvidenceSnapshot(
            snapshot_id=f"ev_v7_{u.stable_lineage_key}",
            use_id=u.use_id,
            stable_lineage_key=u.stable_lineage_key,
            query=f"clearance verification {u.stable_lineage_key}",
            source_url="https://registry.example.com/check",
            source_title="Public Registry Verification",
            excerpt="Confirmed in public domain / validly licensed",
            stance=EvidenceStance.SUPPORTING,
        )
        for u in v7_uses
    }

    # First execution: f(v7, v7)
    run_1 = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v7_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v7_evidence,
        target_version_id="v7",
    )

    # Second execution: f(v7, v7)
    run_2 = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v7_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v7_evidence,
        target_version_id="v7",
    )

    assert len(run_1) == 12
    assert len(run_2) == 12

    # All 12 decisions must carry forward: 12/12 CARRIED_FORWARD, 0 STALE, reason DEPENDENCIES_SATISFIED_UNCHANGED
    assert sum(1 for r in run_1 if r.state == DecisionState.CARRIED_FORWARD) == 12
    assert sum(1 for r in run_1 if r.state == DecisionState.STALE) == 0
    assert sum(1 for r in run_2 if r.state == DecisionState.CARRIED_FORWARD) == 12
    assert sum(1 for r in run_2 if r.state == DecisionState.STALE) == 0

    for res1, res2 in zip(run_1, run_2):
        assert res1.state == DecisionState.CARRIED_FORWARD
        assert res2.state == DecisionState.CARRIED_FORWARD
        assert res1.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"
        assert res2.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"
        assert res1.revalidation_action == "carry"
        assert res2.revalidation_action == "carry"
        assert res1.stable_lineage_key == res2.stable_lineage_key


# =============================================================================
# 4. GOLDEN FIXTURE INVARIANT: 12 -> 10 CARRIED / 2 STALE
# =============================================================================

def test_golden_fixture_10_carried_2_stale_with_dependency_attribution():
    """
    Acceptance Criteria:
    - Ten decisions carry forward and exactly two become stale.
    - Each stale result names the changed dependency.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    validities = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    carried = [v for v in validities if v.state == DecisionState.CARRIED_FORWARD]
    stale = [v for v in validities if v.state == DecisionState.STALE]

    assert len(carried) == 10, f"Expected exactly 10 carried forward, got {len(carried)}"
    assert len(stale) == 2, f"Expected exactly 2 stale, got {len(stale)}"

    stale_map = {v.stable_lineage_key: v for v in stale}

    # Item 11: Creative Drift
    item11_key = "poster_noir_detective_magazine"
    assert item11_key in stale_map
    item11 = stale_map[item11_key]
    assert item11.reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert item11.revalidation_action == "revalidate"
    assert len(item11.changed_dependency_ids) > 0
    assert "delta_poster_noir_detective_magazine" in item11.changed_dependency_ids[0]
    assert "materially altered" in (item11.explanation or "").lower()

    # Item 12: Evidence Drift
    item12_key = "music_cue_midnight_serenade"
    assert item12_key in stale_map
    item12 = stale_map[item12_key]
    assert item12.reason_code == "EXTERNAL_EVIDENCE_SHIFT"
    assert item12.revalidation_action == "revalidate"
    assert len(item12.changed_dependency_ids) > 0
    assert "ev_music_midnight" in item12.changed_dependency_ids[0] or "midnight" in item12.changed_dependency_ids[0]
    assert "evidence" in (item12.explanation or "").lower() or "vanguard" in (item12.explanation or "").lower()


# =============================================================================
# 5. CLEARANCE STATE TAXONOMY & REASON CODE TESTS
# =============================================================================

def test_clearance_state_taxonomy_removed_asset():
    """
    Test versioned change taxonomy: REMOVED state.
    When an asset present in base version is removed in target version,
    the decision state is classified as REMOVED (or fail-closed STALE with close action).
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Remove vintage telephone from target cut
    target_uses_without_phone = [
        u for u in v8_uses if u.stable_lineage_key != "prop_vintage_telephone"
    ]

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=target_uses_without_phone,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    phone_entry = next(r for r in results if r.stable_lineage_key == "prop_vintage_telephone")
    assert phone_entry.state in (DecisionState.REMOVED, DecisionState.STALE)
    assert phone_entry.reason_code == "CLAIM_REMOVED_FROM_SCRIPT"
    assert phone_entry.revalidation_action in ("close", "manual", "revalidate")


def test_clearance_state_taxonomy_new_asset():
    """
    Test versioned change taxonomy: NEW state.
    When an unreviewed asset is introduced in target version without prior decisions.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    new_use = CreativeUse(
        use_id="use_v8_hero_watch",
        version_id="v8",
        scene_or_timecode="Scene 99",
        asset_type="trademark",
        description="Luxury chronograph wristwatch worn by antagonist",
        duration_or_prominence="8s extreme close-up",
        context="Dial prominently visible during bomb defusal countdown",
        stable_lineage_key="trademark_chronograph_luxury",
        context_hash="c0d1e2f3a4b56789",
    )

    extended_target_uses = list(v8_uses) + [new_use]

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=extended_target_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    # 12 prior decisions evaluated, plus new asset handled as NEW_UNCLEARED_CLAIM
    new_entries = [r for r in results if r.stable_lineage_key == "trademark_chronograph_luxury"]
    assert len(new_entries) == 1
    assert new_entries[0].state in (DecisionState.NEW, DecisionState.STALE)
    assert new_entries[0].reason_code == "NEW_UNCLEARED_CLAIM"
    assert new_entries[0].revalidation_action == "manual"


def test_transitive_invalidation_causal_path_propagation():
    """
    Test transitive invalidation traversal through a multi-tier dependency chain:
    Use U -> Decision D1 -> Derivative Decision D2.
    Shifting U must transitively invalidate both D1 and D2, documenting the causal path.
    """
    graph = ClearanceDependencyGraph()

    use = graph.add_creative_use(
        CreativeUse(
            use_id="use_master_script",
            version_id="v7",
            scene_or_timecode="Scene 1",
            asset_type="text",
            description="Historical monologue",
            duration_or_prominence="30s",
            context="Lead actor speaks text",
            stable_lineage_key="text_historical_monologue",
            context_hash="hash_monologue_v7",
        )
    )

    dec1 = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_primary_monologue",
            use_id="use_master_script",
            stable_lineage_key="text_historical_monologue",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Fair use verified under 17 U.S.C. 107",
        )
    )

    dec2 = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_derivative_trailer",
            use_id="use_master_script",
            stable_lineage_key="text_historical_monologue",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Trailer cut promotional clearance tied to primary monologue",
            dependency_ids=["dec_primary_monologue"],
        )
    )

    # Wire DAG: dec1 depends on use, dec2 depends on dec1
    graph.add_dependency(dependent_id="dec_primary_monologue", dependency_id="use_master_script")
    graph.add_dependency(dependent_id="dec_derivative_trailer", dependency_id="dec_primary_monologue")

    # Propagate invalidation from use_master_script
    notices = graph.propagate_invalidation(
        changed_nodes={
            "use_master_script": {
                "reason_code": "CREATIVE_CONTEXT_ALTERED",
                "explanation": "Monologue text rewritten in target revision.",
            }
        }
    )

    assert len(notices) == 2

    notice_map = {n.affected_node_id: n for n in notices}
    assert "dec_primary_monologue" in notice_map
    assert "dec_derivative_trailer" in notice_map

    # Primary decision is directly invalidated
    assert notice_map["dec_primary_monologue"].invalidation_path == ["use_master_script", "dec_primary_monologue"]

    # Derivative decision is transitively invalidated through dec_primary_monologue
    assert notice_map["dec_derivative_trailer"].invalidation_path == [
        "use_master_script",
        "dec_primary_monologue",
        "dec_derivative_trailer",
    ]


def test_contract_agreement_invalidation_handling():
    """
    Test ContractAgreement lifecycle and causal invalidation when agreement expires or terminates.
    """
    graph = ClearanceDependencyGraph()

    contract = graph.add_contract_agreement(
        ContractAgreement(
            agreement_id="agr_music_lic_01",
            stable_lineage_key="music_track_theme",
            licensor="AudioVault Records Ltd",
            licensee="Film Production Co",
            scope="Theatrical synch license",
            term="Expired September 1, 2026",
            agreement_hash="hash_lic_expired",
            is_active=False,
        )
    )

    decision = graph.add_counsel_decision(
        CounselDecision(
            decision_id="dec_music_track",
            use_id="use_music_01",
            stable_lineage_key="music_track_theme",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            rationale="Sync license active at production start",
        )
    )

    graph.add_dependency(
        dependent_id="dec_music_track",
        dependency_id="agr_music_lic_01",
        kind=DependencyKind.CONTRACTUAL_GRANT,
    )

    notices = graph.propagate_invalidation(
        changed_nodes={
            "agr_music_lic_01": {
                "reason_code": "CONTRACT_EXPIRED_OR_TERMINATED",
                "explanation": "Theatrical synch license expired on September 1, 2026.",
            }
        }
    )

    assert len(notices) == 1
    notice = notices[0]
    assert notice.affected_node_id == "dec_music_track"
    assert notice.root_cause_node_id == "agr_music_lic_01"
    assert notice.reason_code == "CONTRACT_EXPIRED_OR_TERMINATED"


# =============================================================================
# 6. RULE BRANCH & REASON CODE COVERAGE TESTS (SPRINT 2B TASK 3)
# =============================================================================

def test_rule_branch_creative_context_altered_item_11():
    """
    Acceptance Criterion: Test CREATIVE_CONTEXT_ALTERED for Item 11 (Scene 42 poster)
    naming creative context drift.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    poster_key = "poster_noir_detective_magazine"
    poster_val = next(r for r in results if r.stable_lineage_key == poster_key)

    assert poster_val.state == DecisionState.STALE
    assert poster_val.reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert poster_val.revalidation_action == "revalidate"
    assert poster_val.creative_delta is not None
    assert poster_val.creative_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert len(poster_val.changed_dependency_ids) > 0
    assert "delta_poster_noir_detective_magazine" in poster_val.changed_dependency_ids[0]
    assert "materially altered" in (poster_val.explanation or "").lower()


def test_rule_branch_external_evidence_shift_item_12():
    """
    Acceptance Criterion: Test EXTERNAL_EVIDENCE_SHIFT for Item 12 (Scene 18 jazz cue)
    naming external evidence stance shift.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    music_key = "music_cue_midnight_serenade"
    music_val = next(r for r in results if r.stable_lineage_key == music_key)

    assert music_val.state == DecisionState.STALE
    assert music_val.reason_code == "EXTERNAL_EVIDENCE_SHIFT"
    assert music_val.revalidation_action == "revalidate"
    assert music_val.evidence_snapshot is not None
    assert music_val.evidence_snapshot.stance == EvidenceStance.CONTRADICTORY
    assert len(music_val.changed_dependency_ids) > 0
    assert "ev_music_midnight" in music_val.changed_dependency_ids[0]
    assert "evidence" in (music_val.explanation or "").lower() or "vanguard" in (music_val.explanation or "").lower()


def test_rule_branch_upstream_dependency_stale_cascading_invalidation():
    """
    Acceptance Criterion: Test UPSTREAM_DEPENDENCY_STALE cascading invalidation.
    1. Downstream decision dependent on Item 11 (poster) is invalidated with UPSTREAM_DEPENDENCY_STALE.
    2. Independent claims remain CARRIED_FORWARD.
    3. Multi-hop cascading: A -> B -> C cascades invalidation through the chain.
    4. When upstream is unchanged (v7 self-eval), downstream carries forward.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Step 1: Create downstream claim B that depends on Item 11 (dec_v7_poster_noir)
    use_b_v7 = CreativeUse(
        use_id="use_v7_poster_framed_closeup",
        version_id="v7",
        scene_or_timecode="Scene 42b",
        asset_type="artwork",
        description="Insert shot of framed magazine logo from Scene 42 poster",
        duration_or_prominence="Incidental background, 2s",
        context="Framed cutout on desk",
        stable_lineage_key="artwork_poster_framed_cutout",
        context_hash="hash_b_v7",
    )
    use_b_v8 = use_b_v7.model_copy(update={"version_id": "v8"})

    dec_b = CounselDecision(
        decision_id="dec_v7_poster_framed_cutout",
        use_id="use_v7_poster_framed_closeup",
        stable_lineage_key="artwork_poster_framed_cutout",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Promotional insert clearance contingent upon underlying Scene 42 poster.",
        dependency_ids=["dec_v7_poster_noir"],
    )

    # Step 2: Create derivative claim C that depends on claim B (multi-hop cascade: A -> B -> C)
    use_c_v7 = CreativeUse(
        use_id="use_v7_trailer_poster_montage",
        version_id="v7",
        scene_or_timecode="Trailer Cut",
        asset_type="artwork",
        description="Rapid montage including Scene 42 poster cutout",
        duration_or_prominence="Promotional montage, 1s",
        context="Montage sequence",
        stable_lineage_key="artwork_trailer_poster_montage",
        context_hash="hash_c_v7",
    )
    use_c_v8 = use_c_v7.model_copy(update={"version_id": "v8"})

    dec_c = CounselDecision(
        decision_id="dec_v7_trailer_poster_montage",
        use_id="use_v7_trailer_poster_montage",
        stable_lineage_key="artwork_trailer_poster_montage",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Trailer montage clearance dependent upon framed cutout clearance.",
        dependency_ids=["dec_v7_poster_framed_cutout"],
    )

    # Evidence for B and C
    extended_evidence = dict(v8_evidence)
    extended_evidence["artwork_poster_framed_cutout"] = PublicEvidenceSnapshot(
        snapshot_id="ev_poster_cutout",
        use_id="use_v7_poster_framed_closeup",
        stable_lineage_key="artwork_poster_framed_cutout",
        query="clearance cutout",
        source_url="https://records.publicdomain.org/cutout",
        source_title="Registry",
        excerpt="No direct conflicting claim",
        stance=EvidenceStance.SUPPORTING,
    )
    extended_evidence["artwork_trailer_poster_montage"] = PublicEvidenceSnapshot(
        snapshot_id="ev_poster_montage",
        use_id="use_v7_trailer_poster_montage",
        stable_lineage_key="artwork_trailer_poster_montage",
        query="clearance montage",
        source_url="https://records.publicdomain.org/montage",
        source_title="Registry",
        excerpt="No direct conflicting claim",
        stance=EvidenceStance.SUPPORTING,
    )

    # In V8, Item 11 is altered (CREATIVE_CONTEXT_ALTERED)
    # B and C script contexts are unchanged, but because B depends on Item 11, B cascades to STALE
    # and C depends on B, so C also cascades to STALE
    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses + [use_b_v7, use_c_v7],
        target_uses=v8_uses + [use_b_v8, use_c_v8],
        prior_decisions=v7_decisions + [dec_b, dec_c],
        evidence_snapshots=extended_evidence,
        target_version_id="v8",
    )

    res_map = {r.stable_lineage_key: r for r in results}

    # Verify Item 11 is directly STALE due to creative context
    assert res_map["poster_noir_detective_magazine"].state == DecisionState.STALE
    assert res_map["poster_noir_detective_magazine"].reason_code == "CREATIVE_CONTEXT_ALTERED"

    # Verify claim B is STALE via UPSTREAM_DEPENDENCY_STALE
    assert res_map["artwork_poster_framed_cutout"].state == DecisionState.STALE
    assert res_map["artwork_poster_framed_cutout"].reason_code == "UPSTREAM_DEPENDENCY_STALE"
    assert "dec_v7_poster_noir" in res_map["artwork_poster_framed_cutout"].changed_dependency_ids
    assert res_map["artwork_poster_framed_cutout"].revalidation_action == "revalidate"

    # Verify claim C is STALE via UPSTREAM_DEPENDENCY_STALE (cascading)
    assert res_map["artwork_trailer_poster_montage"].state == DecisionState.STALE
    assert res_map["artwork_trailer_poster_montage"].reason_code == "UPSTREAM_DEPENDENCY_STALE"
    assert "dec_v7_poster_framed_cutout" in res_map["artwork_trailer_poster_montage"].changed_dependency_ids

    # Verify unaffected claim (e.g. telephone prop) remains CARRIED_FORWARD
    assert res_map["prop_vintage_telephone"].state == DecisionState.CARRIED_FORWARD
    assert res_map["prop_vintage_telephone"].reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"

    # Step 3: When upstream is unchanged (v7 self-eval), B and C carry forward
    v7_supporting_evidence = {
        k: ev.model_copy(update={"stance": EvidenceStance.SUPPORTING})
        for k, ev in extended_evidence.items()
    }
    results_v7 = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses + [use_b_v7, use_c_v7],
        target_uses=v7_uses + [use_b_v7, use_c_v7],
        prior_decisions=v7_decisions + [dec_b, dec_c],
        evidence_snapshots=v7_supporting_evidence,
        target_version_id="v7",
    )
    res_v7_map = {r.stable_lineage_key: r for r in results_v7}
    assert res_v7_map["artwork_poster_framed_cutout"].state == DecisionState.CARRIED_FORWARD
    assert res_v7_map["artwork_poster_framed_cutout"].reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"
    assert res_v7_map["artwork_trailer_poster_montage"].state == DecisionState.CARRIED_FORWARD
    assert res_v7_map["artwork_trailer_poster_montage"].reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"


# =============================================================================
# 7. SPRINT 1.2 EXTENDED HARDENING & MULTI-TIER CAUSAL LINEAGE TESTS
# =============================================================================

def test_multi_tier_causal_mapping_scene_beat_use_claim_clarif_decision():
    """
    Sprint 1.2 Requirement 1:
    Map CreativeUse / AtomicRightsClaim nodes to parent scene contexts, script beats,
    contract agreements, external evidence snapshots, clarification requests, and counsel decisions.
    """
    scene = SceneContext(
        scene_id="scene_042",
        version_id="v7",
        scene_number="42",
        slugline="INT. DETECTIVE OFFICE - NIGHT",
        scene_hash="hash_scene_042",
        stable_lineage_key="scene_42",
    )
    beat = ScriptBeat(
        beat_id="beat_042_01",
        scene_id="scene_042",
        version_id="v7",
        beat_index=1,
        title="Detective Enters Office",
        action_text="Protagonist hangs coat on rack next to framed poster.",
        beat_hash="hash_beat_042_01",
        stable_lineage_key="beat_42_01",
    )
    use = CreativeUse(
        use_id="use_poster_42",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="artwork",
        description="Framed noir detective magazine poster",
        duration_or_prominence="2s background",
        context="Hangs on office wall",
        stable_lineage_key="poster_noir_detective_magazine",
        context_hash="hash_use_poster_42",
        metadata={"beat_id": "beat_042_01", "scene_id": "scene_042"},
    )
    claim = AtomicRightsClaim(
        claim_id="claim_poster_copyright_01",
        occurrence_id="use_poster_42",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Magazine Publisher",
        disposition=CensusDisposition.APPROVED,
    )
    contract = ContractAgreement(
        agreement_id="agr_poster_license_01",
        stable_lineage_key="poster_noir_detective_magazine",
        licensor="Retro Publishing Archives LLC",
        licensee="Production Co LLC",
        scope="Theatrical worldwide",
        term="Perpetual",
        agreement_hash="hash_agr_01",
        is_active=True,
    )
    evidence = PublicEvidenceSnapshot(
        snapshot_id="ev_loc_record_01",
        use_id="use_poster_42",
        stable_lineage_key="poster_noir_detective_magazine",
        query="copyright registration 1939",
        source_url="https://loc.gov/copyright/1939",
        source_title="LOC Catalog 1939",
        excerpt="No renewal on file; public domain",
        stance=EvidenceStance.SUPPORTING,
    )
    clarification = ClarificationRequest(
        request_id="clarif_poster_01",
        run_id="run_test",
        claim_id="use_poster_42",
        revision_id="v7",
        stable_lineage_key="poster_noir_detective_magazine",
        question_text="Confirm artwork is pre-1978 without renewal",
        status="resolved",
    )
    decision = CounselDecision(
        decision_id="dec_poster_42",
        use_id="use_poster_42",
        stable_lineage_key="poster_noir_detective_magazine",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Cleared background artwork via LOC registry and sync license",
    )

    graph = ClearanceDependencyGraph.build_clearance_graph(
        base_uses=[use],
        target_uses=[use],
        prior_decisions=[decision],
        evidence_snapshots=[evidence],
        contracts=[contract],
        atomic_claims=[claim],
        scene_contexts=[scene],
        script_beats=[beat],
        clarification_requests=[clarification],
    )

    # 1. Verify Node Registration
    assert graph.has_node("scene_042")
    assert graph.has_node("beat_042_01")
    assert graph.has_node("use_poster_42")
    assert graph.has_node("claim_poster_copyright_01")
    assert graph.has_node("agr_poster_license_01")
    assert graph.has_node("ev_loc_record_01")
    assert graph.has_node("clarif_poster_01")
    assert graph.has_node("dec_poster_42")

    # 2. Verify Causal Lineage Edges
    # beat -> scene
    assert "scene_042" in graph.get_dependencies("beat_042_01")
    # use -> beat
    assert "beat_042_01" in graph.get_dependencies("use_poster_42")
    # claim -> use
    assert "use_poster_42" in graph.get_dependencies("claim_poster_copyright_01")
    # clarification -> use (or claim)
    assert "use_poster_42" in graph.get_dependencies("clarif_poster_01")
    # decision -> use, evidence, contract, claim, clarification
    dec_deps = graph.get_dependencies("dec_poster_42")
    assert "use_poster_42" in dec_deps
    assert "ev_loc_record_01" in dec_deps
    assert "agr_poster_license_01" in dec_deps
    assert "claim_poster_copyright_01" in dec_deps
    assert "clarif_poster_01" in dec_deps

    # 3. Verify Transitive Closure
    ancestors = graph.get_ancestors("dec_poster_42")
    assert "scene_042" in ancestors
    assert "beat_042_01" in ancestors
    assert "use_poster_42" in ancestors
    assert "claim_poster_copyright_01" in ancestors


def test_transitive_invalidation_scene_shift_propagates_to_decision():
    """
    Sprint 1.2 Requirement 3:
    When an upstream scene context shifts, the DAG traverses downstream
    to invalidate affected decisions into stale status while generating
    tamper-evident InvalidationNotices.
    """
    scene = SceneContext(
        scene_id="scene_042",
        version_id="v7",
        scene_number="42",
        slugline="INT. DETECTIVE OFFICE - NIGHT",
        scene_hash="hash_scene_042",
        stable_lineage_key="scene_42",
    )
    beat = ScriptBeat(
        beat_id="beat_042_01",
        scene_id="scene_042",
        version_id="v7",
        beat_index=1,
        title="Detective Enters Office",
        action_text="Protagonist hangs coat on rack next to framed poster.",
        beat_hash="hash_beat_042_01",
        stable_lineage_key="beat_42_01",
    )
    use = CreativeUse(
        use_id="use_poster_42",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="artwork",
        description="Framed noir detective magazine poster",
        duration_or_prominence="2s background",
        context="Hangs on office wall",
        stable_lineage_key="poster_noir_detective_magazine",
        context_hash="hash_use_poster_42",
        metadata={"beat_id": "beat_042_01", "scene_id": "scene_042"},
    )
    decision = CounselDecision(
        decision_id="dec_poster_42",
        use_id="use_poster_42",
        stable_lineage_key="poster_noir_detective_magazine",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Cleared background artwork",
    )

    graph = ClearanceDependencyGraph.build_clearance_graph(
        base_uses=[use],
        target_uses=[use],
        prior_decisions=[decision],
        scene_contexts=[scene],
        script_beats=[beat],
        organization_id="org_studio_alpha",
    )

    # Trigger upstream scene rewrite
    notices = graph.propagate_invalidation(
        changed_nodes={
            "scene_042": {
                "reason_code": "SCENE_CONTEXT_MODIFIED",
                "explanation": "Scene location changed from 1940s office to modern lab.",
            }
        },
        production_id="prod_feature_test",
        run_id="run_inv_test_01",
    )

    assert len(notices) == 1
    notice = notices[0]
    assert notice.affected_node_id == "dec_poster_42"
    assert notice.root_cause_node_id == "scene_042"
    assert notice.root_cause_type == NodeType.SCENE_CONTEXT
    assert notice.is_direct is False
    assert notice.hop_count >= 3
    assert notice.reason_code == "UPSTREAM_DEPENDENCY_STALE"
    assert notice.invalidation_path[0] == "scene_042"
    assert notice.invalidation_path[-1] == "dec_poster_42"

    # Verify Cryptographic Tamper-Evidence
    assert notice.verify_integrity() is True
    assert len(notice.canonical_payload_digest) == 64
    assert len(notice.notice_hash) == 64


def test_iterative_dfs_deep_chain_acyclicity_no_recursion_error():
    """
    Sprint 1.2 Hardening:
    Verifies that validate_dag_acyclicity uses an iterative call stack,
    preventing RecursionError even on chains exceeding Python's default
    recursion limit (1,000 frames).
    """
    graph = ClearanceDependencyGraph()
    chain_length = 1200

    # Build linear chain: node_0 -> node_1 -> node_2 -> ... -> node_1199
    for i in range(chain_length):
        graph.add_node(
            node=f"node_{i:04d}",
            node_type=NodeType.CUSTOM,
            stable_lineage_key=f"lineage_{i:04d}",
        )

    for i in range(chain_length - 1):
        graph.add_dependency(
            dependent_id=f"node_{i+1:04d}",
            dependency_id=f"node_{i:04d}",
            validate_cycle=False,
        )

    # Must execute in linear time without RecursionError
    graph.validate_dag_acyclicity()
    assert graph.node_count() == chain_length
    assert graph.edge_count() == chain_length - 1


def test_persist_invalidation_notices_polymorphic_signatures_and_hash_chain():
    """
    Sprint 1.2 Requirement 3:
    Verifies discrete subcollection persistence under:
    /organizations/{org_id}/productions/{prod_id}/runs/{run_id}/invalidation_notices
    Supports both polymorphic calling conventions and unbroken hash chain continuity.
    """
    graph = ClearanceDependencyGraph(organization_id="org_studio_alpha")
    u = graph.add_node("use_alpha", NodeType.CREATIVE_USE, "lineage_alpha")
    d1 = graph.add_node("dec_01", NodeType.COUNSEL_DECISION, "lineage_d1")
    d2 = graph.add_node("dec_02", NodeType.COUNSEL_DECISION, "lineage_d2")
    graph.add_dependency("dec_01", "use_alpha")
    graph.add_dependency("dec_02", "use_alpha")

    notices = graph.propagate_invalidation(
        changed_nodes=["use_alpha"],
        production_id="prod_test_01",
        run_id="run_audit_01",
    )
    assert len(notices) == 2

    # Verify cryptographic hash chaining
    assert notices[0].sequence_number == 1
    assert notices[0].previous_notice_hash == "0" * 64
    assert notices[0].verify_integrity() is True

    assert notices[1].sequence_number == 2
    assert notices[1].previous_notice_hash == notices[0].notice_hash
    assert notices[1].verify_integrity() is True

    # Mock repository
    class MockTenantRepository:
        def __init__(self):
            self.saved_batches = []
            self.saved_singles = []

        def save_invalidation_notices_batch(self, production_id, run_id, notices):
            self.saved_batches.append((production_id, run_id, notices))
            return [n.to_firestore_dict() for n in notices]

    repo = MockTenantRepository()

    # Test Calling Pattern A: (repo, notices, production_id, run_id)
    persisted_a = graph.persist_invalidation_notices(
        repository=repo,
        notices=notices,
        production_id="prod_test_01",
        run_id="run_audit_01",
    )
    assert len(persisted_a) == 2
    assert repo.saved_batches[0][0] == "prod_test_01"
    assert repo.saved_batches[0][1] == "run_audit_01"

    # Test Calling Pattern B: (repo, production_id, run_id, notices)
    persisted_b = graph.persist_invalidation_notices(
        repo,
        "prod_test_01",
        "run_audit_01",
        notices,
    )
    assert len(persisted_b) == 2
    assert len(repo.saved_batches) == 2

