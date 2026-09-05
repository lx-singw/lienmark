"""
Lienmark Sprint 2B Verification Suite: Dependency Graph & Policy Engine
Tests:
- ClearanceDependencyGraph (DAG construction, topological sort, cycle detection, traversal, input-order invariance, transitive invalidation)
- InvalidationEngine (versioned change taxonomy, idempotent (v7, v7) execution, permutation invariance, defensible explanations)
- Complete backend/core exports
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import copy
import random
import pytest

from backend.domain.models import (
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    PublicEvidenceSnapshot,
)
from backend.core import (
    ClearanceDependencyGraph,
    ClearanceGraphError,
    CycleDetectedError,
    DependencyEdge,
    DependencyKind,
    DependencyNode,
    InvalidationEngine,
    InvalidationNotice,
    NodeNotFoundError,
    NodeType,
)
from backend.fixtures.golden_dataset import get_golden_fixtures


def test_core_exports_completeness():
    """Verify all Sprint 2B graph classes and error types are properly exported from backend.core."""
    assert ClearanceDependencyGraph is not None
    assert NodeType is not None
    assert DependencyKind is not None
    assert DependencyNode is not None
    assert DependencyEdge is not None
    assert InvalidationNotice is not None
    assert ClearanceGraphError is not None
    assert CycleDetectedError is not None
    assert NodeNotFoundError is not None


def test_dag_construction_and_topological_sort():
    """Verify DAG construction with all four entity types and deterministic topological sort."""
    graph = ClearanceDependencyGraph()

    # 1. Creative Use (upstream)
    use = CreativeUse(
        use_id="use_scene10_car",
        version_id="v7",
        scene_or_timecode="Scene 10",
        asset_type="prop",
        description="1955 Vintage Chevrolet",
        duration_or_prominence="5s background",
        context="Car parked in alley",
        stable_lineage_key="car_chevy_1955",
        context_hash="a1b2c3d4e5f60718",
    )
    node_use = graph.add_creative_use(use)
    assert node_use.node_type == NodeType.CREATIVE_USE
    assert node_use.node_id == "use_scene10_car"

    # 2. Public Evidence Snapshot (upstream)
    evidence = PublicEvidenceSnapshot(
        snapshot_id="ev_chevy_search",
        use_id="use_scene10_car",
        stable_lineage_key="car_chevy_1955",
        query="1955 Chevrolet trademark movie clearance",
        source_url="https://uspto.gov/trademarks/chevy",
        source_title="USPTO Trademark Database",
        excerpt="Historical vehicle trademark guidance permits de minimis set dressing.",
        stance=EvidenceStance.SUPPORTING,
    )
    node_ev = graph.add_evidence_snapshot(evidence)
    assert node_ev.node_type == NodeType.EVIDENCE_SNAPSHOT

    # 3. Contract Agreement (upstream)
    contract = ContractAgreement(
        agreement_id="contract_chevy_license",
        stable_lineage_key="car_chevy_1955",
        licensor="General Motors Archive",
        licensee="Shadows Production Co.",
        scope="Worldwide motion picture sync and background exhibition",
        term="Perpetuity",
        agreement_hash="9f8e7d6c5b4a3210",
        is_active=True,
    )
    node_contract = graph.add_contract_agreement(contract)
    assert node_contract.node_type == NodeType.CONTRACT_AGREEMENT

    # 4. Counsel Decision (downstream)
    decision = CounselDecision(
        decision_id="dec_chevy_clearance",
        use_id="use_scene10_car",
        stable_lineage_key="car_chevy_1955",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved based on incidental placement and GM archive license.",
    )
    node_dec = graph.add_counsel_decision(decision)
    assert node_dec.node_type == NodeType.COUNSEL_DECISION

    # Wire causal edges
    graph.add_dependency(decision.decision_id, use.use_id, kind=DependencyKind.CREATIVE_CONTEXT)
    graph.add_dependency(decision.decision_id, evidence.snapshot_id, kind=DependencyKind.EVIDENCE_STANCE)
    graph.add_dependency(decision.decision_id, contract.agreement_id, kind=DependencyKind.CONTRACTUAL_GRANT)

    assert not graph.has_cycles()

    # Topological sort: dependencies MUST precede dependents
    topo_order = graph.topological_sort()
    topo_ids = [n.node_id for n in topo_order]
    assert topo_ids.index(use.use_id) < topo_ids.index(decision.decision_id)
    assert topo_ids.index(evidence.snapshot_id) < topo_ids.index(decision.decision_id)
    assert topo_ids.index(contract.agreement_id) < topo_ids.index(decision.decision_id)


def test_cycle_detection_self_and_multi_hop():
    """Verify that cycle detection catches self-cycles, direct 2-hop cycles, and transitive multi-hop cycles."""
    graph = ClearanceDependencyGraph()

    use = CreativeUse(
        use_id="use_01",
        version_id="v7",
        scene_or_timecode="Scene 01",
        asset_type="prop",
        description="Prop",
        duration_or_prominence="2s",
        context="Context",
        stable_lineage_key="item_01",
        context_hash="hash01",
    )
    dec1 = CounselDecision(
        decision_id="dec_01",
        use_id="use_01",
        stable_lineage_key="item_01",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )
    dec2 = CounselDecision(
        decision_id="dec_02",
        use_id="use_01",
        stable_lineage_key="item_01",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )
    dec3 = CounselDecision(
        decision_id="dec_03",
        use_id="use_01",
        stable_lineage_key="item_01",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )

    graph.add_creative_use(use)
    graph.add_counsel_decision(dec1)
    graph.add_counsel_decision(dec2)
    graph.add_counsel_decision(dec3)

    # 1. Self-cycle
    with pytest.raises(CycleDetectedError):
        graph.add_dependency("dec_01", "dec_01")

    # 2. 2-hop cycle: dec_01 depends on use_01, making use_01 depend on dec_01 must raise
    graph.add_dependency("dec_01", "use_01")
    with pytest.raises(CycleDetectedError):
        graph.add_dependency("use_01", "dec_01")

    # 3. 3-hop cycle: dec_02 depends on dec_01, dec_03 depends on dec_02
    graph.add_dependency("dec_02", "dec_01")
    graph.add_dependency("dec_03", "dec_02")
    # Closing cycle: making dec_01 depend on dec_03 must raise
    with pytest.raises(CycleDetectedError):
        graph.add_dependency("dec_01", "dec_03")


def test_ancestor_and_descendant_traversal():
    """Verify transitive ancestor and descendant traversal across multi-tier lineage chains."""
    graph = ClearanceDependencyGraph()

    # Chain: Use A -> Dec 1 -> Dec 2 (derivative) -> Dec 3 (marketing trailer)
    use = CreativeUse(
        use_id="use_hero_sword",
        version_id="v7",
        scene_or_timecode="Scene 05",
        asset_type="prop",
        description="Hero Sword",
        duration_or_prominence="10s",
        context="Hero duel",
        stable_lineage_key="hero_sword",
        context_hash="swordhash",
    )
    d1 = CounselDecision(
        decision_id="dec_1_production",
        use_id="use_hero_sword",
        stable_lineage_key="hero_sword",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Production clearance",
    )
    d2 = CounselDecision(
        decision_id="dec_2_extended_cut",
        use_id="use_hero_sword",
        stable_lineage_key="hero_sword",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Extended cut clearance",
    )
    d3 = CounselDecision(
        decision_id="dec_3_trailer",
        use_id="use_hero_sword",
        stable_lineage_key="hero_sword",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Trailer promotional clearance",
    )

    graph.add_creative_use(use)
    graph.add_counsel_decision(d1)
    graph.add_counsel_decision(d2)
    graph.add_counsel_decision(d3)

    graph.add_dependency("dec_1_production", "use_hero_sword")
    graph.add_dependency("dec_2_extended_cut", "dec_1_production")
    graph.add_dependency("dec_3_trailer", "dec_2_extended_cut")

    # Transitive ancestors of dec_3_trailer
    ancestors = graph.get_ancestors("dec_3_trailer")
    assert "dec_2_extended_cut" in ancestors
    assert "dec_1_production" in ancestors
    assert "use_hero_sword" in ancestors
    assert len(ancestors) == 3

    # Direct dependencies of dec_3_trailer
    direct_deps = graph.get_direct_dependencies("dec_3_trailer")
    assert direct_deps == ["dec_2_extended_cut"]

    # Transitive descendants of use_hero_sword
    descendants = graph.get_descendants("use_hero_sword")
    assert "dec_1_production" in descendants
    assert "dec_2_extended_cut" in descendants
    assert "dec_3_trailer" in descendants
    assert len(descendants) == 3


def test_transitive_invalidation_multi_tier_causal_chain():
    """Verify transitive invalidation propagates downstream and tags decisions with UPSTREAM_DEPENDENCY_STALE."""
    graph = ClearanceDependencyGraph()

    use = CreativeUse(
        use_id="use_hero_sword",
        version_id="v7",
        scene_or_timecode="Scene 05",
        asset_type="prop",
        description="Hero Sword",
        duration_or_prominence="10s",
        context="Hero duel",
        stable_lineage_key="hero_sword",
        context_hash="hash_v7",
    )
    d1 = CounselDecision(
        decision_id="dec_1_production",
        use_id="use_hero_sword",
        stable_lineage_key="hero_sword",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Production clearance",
    )
    d2 = CounselDecision(
        decision_id="dec_2_derivative",
        use_id="use_hero_sword",
        stable_lineage_key="hero_sword",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Derivative clearance",
    )

    graph.add_creative_use(use)
    graph.add_counsel_decision(d1)
    graph.add_counsel_decision(d2)

    graph.add_dependency("dec_1_production", "use_hero_sword")
    graph.add_dependency("dec_2_derivative", "dec_1_production")

    # Shift upstream creative use
    notices = graph.propagate_invalidation(["use_hero_sword"])
    assert len(notices) == 2

    notice_map = {n.affected_node_id: n for n in notices}

    # d1 was directly dependent on use_hero_sword
    assert "dec_1_production" in notice_map
    assert notice_map["dec_1_production"].root_cause_node_id == "use_hero_sword"
    assert notice_map["dec_1_production"].reason_code == "CREATIVE_CONTEXT_ALTERED"

    # d2 was transitively dependent on use_hero_sword via d1
    assert "dec_2_derivative" in notice_map
    assert notice_map["dec_2_derivative"].root_cause_node_id == "use_hero_sword"
    assert notice_map["dec_2_derivative"].reason_code == "UPSTREAM_DEPENDENCY_STALE"
    assert notice_map["dec_2_derivative"].invalidation_path == ["use_hero_sword", "dec_1_production", "dec_2_derivative"]


def test_idempotent_execution_v7_v7():
    """Ensure evaluating (v7, v7) returns 100% carried-forward with zero stale claims."""
    v7_uses, _, v7_decisions, v8_evidence = get_golden_fixtures()

    # Pass v7 as both base and target
    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v7_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v7",
    )

    assert len(results) == 12
    carried = [r for r in results if r.state == DecisionState.CARRIED_FORWARD]
    stale = [r for r in results if r.state == DecisionState.STALE]

    assert len(carried) == 12, "Idempotent evaluation must have 100% carried forward"
    assert len(stale) == 0, "Idempotent evaluation must have exactly zero stale claims"
    for r in results:
        assert r.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"
        assert "idempotently" in r.explanation or "identical" in r.explanation


def test_input_permutation_invariance():
    """Ensure shuffling the input list of uses/decisions yields bit-for-bit identical results."""
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    baseline_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    baseline_dump = [r.model_dump() for r in baseline_results]

    # Test across 20 distinct random permutations of input orders
    rnd = random.Random(42)
    for _ in range(20):
        shuffled_v7 = copy.deepcopy(v7_uses)
        shuffled_v8 = copy.deepcopy(v8_uses)
        shuffled_dec = copy.deepcopy(v7_decisions)

        rnd.shuffle(shuffled_v7)
        rnd.shuffle(shuffled_v8)
        rnd.shuffle(shuffled_dec)

        # Shuffle dictionary insertion order
        shuffled_keys = list(v8_evidence.keys())
        rnd.shuffle(shuffled_keys)
        shuffled_evidence = {k: v8_evidence[k] for k in shuffled_keys}

        permuted_results = InvalidationEngine.evaluate_invalidation(
            base_uses=shuffled_v7,
            target_uses=shuffled_v8,
            prior_decisions=shuffled_dec,
            evidence_snapshots=shuffled_evidence,
            target_version_id="v8",
        )

        permuted_dump = [r.model_dump() for r in permuted_results]
        assert permuted_dump == baseline_dump, "Evaluation failed input permutation invariance!"


def test_versioned_change_taxonomy_all_states_and_reasons():
    """
    Verify complete versioned change taxonomy coverage:
    - States: CARRIED_FORWARD, STALE, REMOVED, NEW, EXCEPTION
    - Reason codes:
      * DEPENDENCIES_SATISFIED_UNCHANGED
      * CREATIVE_CONTEXT_ALTERED
      * EXTERNAL_EVIDENCE_SHIFT
      * UPSTREAM_DEPENDENCY_STALE
      * CLAIM_REMOVED_FROM_SCRIPT
      * NEW_UNCLEARED_CLAIM
    """
    # 1. Unchanged Claim -> CARRIED_FORWARD
    u_unchanged_v7 = CreativeUse(
        use_id="u_phone_v7",
        version_id="v7",
        scene_or_timecode="Scene 01",
        asset_type="prop",
        description="Desk Phone",
        duration_or_prominence="2s blur",
        context="Desk shot",
        stable_lineage_key="claim_phone",
        context_hash="hash_phone",
    )
    u_unchanged_v8 = CreativeUse(
        use_id="u_phone_v8",
        version_id="v8",
        scene_or_timecode="Scene 01",
        asset_type="prop",
        description="Desk Phone",
        duration_or_prominence="2s blur",
        context="Desk shot",
        stable_lineage_key="claim_phone",
        context_hash="hash_phone",
    )
    d_unchanged = CounselDecision(
        decision_id="dec_phone",
        use_id="u_phone_v7",
        stable_lineage_key="claim_phone",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )

    # 2. Creative Drift Claim -> STALE / CREATIVE_CONTEXT_ALTERED
    u_poster_v7 = CreativeUse(
        use_id="u_poster_v7",
        version_id="v7",
        scene_or_timecode="Scene 02",
        asset_type="artwork",
        description="Poster",
        duration_or_prominence="2s blur",
        context="Background wall",
        stable_lineage_key="claim_poster",
        context_hash="hash_poster_v7",
    )
    u_poster_v8 = CreativeUse(
        use_id="u_poster_v8",
        version_id="v8",
        scene_or_timecode="Scene 02",
        asset_type="artwork",
        description="Poster",
        duration_or_prominence="15s focal dialogue",
        context="Character quotes text",
        stable_lineage_key="claim_poster",
        context_hash="hash_poster_v8",
    )
    d_poster = CounselDecision(
        decision_id="dec_poster",
        use_id="u_poster_v7",
        stable_lineage_key="claim_poster",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )

    # 3. Evidence Shift Claim -> STALE / EXTERNAL_EVIDENCE_SHIFT
    u_music_v7 = CreativeUse(
        use_id="u_music_v7",
        version_id="v7",
        scene_or_timecode="Scene 03",
        asset_type="music",
        description="Jazz Song",
        duration_or_prominence="10s background",
        context="Diner music",
        stable_lineage_key="claim_music",
        context_hash="hash_music",
    )
    u_music_v8 = CreativeUse(
        use_id="u_music_v8",
        version_id="v8",
        scene_or_timecode="Scene 03",
        asset_type="music",
        description="Jazz Song",
        duration_or_prominence="10s background",
        context="Diner music",
        stable_lineage_key="claim_music",
        context_hash="hash_music",
    )
    d_music = CounselDecision(
        decision_id="dec_music",
        use_id="u_music_v7",
        stable_lineage_key="claim_music",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved",
    )
    ev_music_shift = PublicEvidenceSnapshot(
        snapshot_id="ev_music_contradictory",
        use_id="u_music_v8",
        stable_lineage_key="claim_music",
        query="Jazz Song copyright registry",
        source_url="https://musicregistry.org/jazz",
        source_title="Registry Disputed Notice",
        excerpt="Disputed ownership and active master infringement notice.",
        stance=EvidenceStance.CONTRADICTORY,
    )

    # 4. Transitive Upstream Stale Claim -> STALE / UPSTREAM_DEPENDENCY_STALE
    u_derivative_v7 = CreativeUse(
        use_id="u_derivative_v7",
        version_id="v7",
        scene_or_timecode="Scene 04",
        asset_type="artwork",
        description="Poster Derivative Montage",
        duration_or_prominence="5s",
        context="Montage",
        stable_lineage_key="claim_derivative",
        context_hash="hash_derivative",
    )
    u_derivative_v8 = CreativeUse(
        use_id="u_derivative_v8",
        version_id="v8",
        scene_or_timecode="Scene 04",
        asset_type="artwork",
        description="Poster Derivative Montage",
        duration_or_prominence="5s",
        context="Montage",
        stable_lineage_key="claim_derivative",
        context_hash="hash_derivative",
    )
    d_derivative = CounselDecision(
        decision_id="dec_derivative",
        use_id="u_derivative_v7",
        stable_lineage_key="claim_derivative",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Cleared based on prior poster approval",
        dependency_ids=["dec_poster"],
    )

    # 5. Removed Claim -> REMOVED / CLAIM_REMOVED_FROM_SCRIPT
    u_removed_v7 = CreativeUse(
        use_id="u_removed_v7",
        version_id="v7",
        scene_or_timecode="Scene 05",
        asset_type="prop",
        description="Deleted Car Scene",
        duration_or_prominence="3s",
        context="Cut from timeline",
        stable_lineage_key="claim_removed",
        context_hash="hash_removed",
    )
    d_removed = CounselDecision(
        decision_id="dec_removed",
        use_id="u_removed_v7",
        stable_lineage_key="claim_removed",
        applicable_version_id="v7",
        status=DecisionStatus.APPROVED,
        rationale="Approved in v7",
    )

    # 6. New Uncleared Claim -> NEW / NEW_UNCLEARED_CLAIM
    u_new_v8 = CreativeUse(
        use_id="u_new_v8",
        version_id="v8",
        scene_or_timecode="Scene 06",
        asset_type="trademark",
        description="Newly Added Billboard",
        duration_or_prominence="8s focal",
        context="Times Square sequence added in revision",
        stable_lineage_key="claim_new",
        context_hash="hash_new",
    )

    # 7. Unresolved Exception -> EXCEPTION
    u_exception_v7 = CreativeUse(
        use_id="u_exception_v7",
        version_id="v7",
        scene_or_timecode="Scene 07",
        asset_type="trademark",
        description="Unlicensed Brand",
        duration_or_prominence="4s",
        context="Storefront",
        stable_lineage_key="claim_exception",
        context_hash="hash_exception",
    )
    u_exception_v8 = CreativeUse(
        use_id="u_exception_v8",
        version_id="v8",
        scene_or_timecode="Scene 07",
        asset_type="trademark",
        description="Unlicensed Brand",
        duration_or_prominence="4s",
        context="Storefront",
        stable_lineage_key="claim_exception",
        context_hash="hash_exception",
    )
    d_exception = CounselDecision(
        decision_id="dec_exception",
        use_id="u_exception_v7",
        stable_lineage_key="claim_exception",
        applicable_version_id="v7",
        status=DecisionStatus.REJECTED,
        rationale="Counsel rejected due to trademark litigation risk",
    )

    base_uses = [u_unchanged_v7, u_poster_v7, u_music_v7, u_derivative_v7, u_removed_v7, u_exception_v7]
    target_uses = [u_unchanged_v8, u_poster_v8, u_music_v8, u_derivative_v8, u_new_v8, u_exception_v8]
    prior_decisions = [d_unchanged, d_poster, d_music, d_derivative, d_removed, d_exception]
    evidence_snapshots = {
        "claim_music": ev_music_shift,
    }

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=base_uses,
        target_uses=target_uses,
        prior_decisions=prior_decisions,
        evidence_snapshots=evidence_snapshots,
        target_version_id="v8",
    )

    result_map = {r.stable_lineage_key: r for r in results}

    # Verify 1: CARRIED_FORWARD & DEPENDENCIES_SATISFIED_UNCHANGED
    assert result_map["claim_phone"].state == DecisionState.CARRIED_FORWARD
    assert result_map["claim_phone"].reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"

    # Verify 2: STALE & CREATIVE_CONTEXT_ALTERED
    assert result_map["claim_poster"].state == DecisionState.STALE
    assert result_map["claim_poster"].reason_code == "CREATIVE_CONTEXT_ALTERED"

    # Verify 3: STALE & EXTERNAL_EVIDENCE_SHIFT
    assert result_map["claim_music"].state == DecisionState.STALE
    assert result_map["claim_music"].reason_code == "EXTERNAL_EVIDENCE_SHIFT"

    # Verify 4: STALE & UPSTREAM_DEPENDENCY_STALE
    assert result_map["claim_derivative"].state == DecisionState.STALE
    assert result_map["claim_derivative"].reason_code == "UPSTREAM_DEPENDENCY_STALE"

    # Verify 5: REMOVED & CLAIM_REMOVED_FROM_SCRIPT
    assert result_map["claim_removed"].state == DecisionState.REMOVED
    assert result_map["claim_removed"].reason_code == "CLAIM_REMOVED_FROM_SCRIPT"
    assert result_map["claim_removed"].revalidation_action == "close"

    # Verify 6: NEW & NEW_UNCLEARED_CLAIM
    assert result_map["claim_new"].state == DecisionState.NEW
    assert result_map["claim_new"].reason_code == "NEW_UNCLEARED_CLAIM"

    # Verify 7: EXCEPTION
    assert result_map["claim_exception"].state == DecisionState.EXCEPTION

    # Verify all 5 taxonomy states are covered
    distinct_states = {r.state for r in results}
    assert DecisionState.CARRIED_FORWARD in distinct_states
    assert DecisionState.STALE in distinct_states
    assert DecisionState.REMOVED in distinct_states
    assert DecisionState.NEW in distinct_states
    assert DecisionState.EXCEPTION in distinct_states

    # Verify all detailed reason codes are covered
    distinct_codes = {r.reason_code for r in results}
    assert "DEPENDENCIES_SATISFIED_UNCHANGED" in distinct_codes
    assert "CREATIVE_CONTEXT_ALTERED" in distinct_codes
    assert "EXTERNAL_EVIDENCE_SHIFT" in distinct_codes
    assert "UPSTREAM_DEPENDENCY_STALE" in distinct_codes
    assert "CLAIM_REMOVED_FROM_SCRIPT" in distinct_codes
    assert "NEW_UNCLEARED_CLAIM" in distinct_codes


def test_legally_defensible_explanations():
    """Verify that every DecisionValidity output includes a defensible human-readable explanation naming dependencies."""
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    for r in results:
        assert r.explanation is not None and len(r.explanation) > 20
        # Explanation must reference the lineage key or decision
        assert r.stable_lineage_key in r.explanation or r.decision_id in r.explanation

    # Stale creative drift must name modified prominence or fields
    poster_res = next(r for r in results if r.stable_lineage_key == "poster_noir_detective_magazine")
    assert "altered" in poster_res.explanation.lower() or "prominence" in poster_res.explanation.lower()

    # Stale evidence drift must name snapshot ID or source
    music_res = next(r for r in results if r.stable_lineage_key == "music_cue_midnight_serenade")
    assert "evidence" in music_res.explanation.lower() or "vanguard" in music_res.explanation.lower()
