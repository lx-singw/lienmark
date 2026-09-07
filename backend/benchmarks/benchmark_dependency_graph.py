"""
Clearance Dependency Graph Performance Benchmark
Lienmark Sprint 1.2 Performance & Traversal Benchmark Suite.

Simulates a 150-page screenplay clearance dependency graph:
- 125 SceneContexts
- 375 ScriptBeats (3 beats per scene)
- 320 CreativeUses
- 450 AtomicRightsClaims
- 350 PublicEvidenceSnapshots
- 160 ContractAgreements
- 40 ClarificationRequests
- 320 CounselDecisions
Total Nodes: >2,100 nodes | Total Edges: >3,800 edges

Verifies the Roadmap Obligation:
"Benchmark graph traversal algorithms to ensure dependency resolution
for a 150-page screenplay (>300 claims) executes in <150 ms."
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is on sys.path for direct execution
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.core.dependency_graph import (
    ClearanceDependencyGraph,
    DependencyKind,
    NodeType,
    build_clearance_graph,
)
from backend.domain.models import (
    ApprovalOrigin,
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    DecisionStatus,
    EvidenceStance,
    PublicEvidenceSnapshot,
    SceneContext,
    ScriptBeat,
)


def generate_150_page_screenplay_data(
    num_scenes: int = 125,
    beats_per_scene: int = 3,
    num_uses: int = 320,
    num_claims: int = 450,
    num_contracts: int = 160,
    num_evidence: int = 350,
    num_clarifications: int = 40,
    num_decisions: int = 320,
    org_id: str = "org_studio_alpha",
    prod_id: str = "prod_feature_150p",
    run_id: str = "run_benchmark_01",
) -> Dict[str, Any]:
    """
    Generates a deterministic synthetic dataset modeling a full 150-page screenplay.
    """
    # 1. Scenes
    scenes: List[SceneContext] = []
    for s_idx in range(1, num_scenes + 1):
        scene_hash = hashlib.sha256(f"SCENE_{s_idx}_{prod_id}".encode()).hexdigest()
        scenes.append(
            SceneContext(
                scene_id=f"scene_{s_idx:03d}",
                version_id="v7",
                scene_number=str(s_idx),
                slugline=f"EXT. LOCATION {s_idx} - DAY",
                setting_type="EXT." if s_idx % 2 == 0 else "INT.",
                scene_hash=scene_hash,
                stable_lineage_key=f"scene_lineage_{s_idx:03d}",
            )
        )

    # 2. Script Beats
    beats: List[ScriptBeat] = []
    beat_counter = 1
    for scene in scenes:
        for b_idx in range(1, beats_per_scene + 1):
            beat_hash = hashlib.sha256(f"BEAT_{beat_counter}_{scene.scene_id}".encode()).hexdigest()
            beats.append(
                ScriptBeat(
                    beat_id=f"beat_{beat_counter:04d}",
                    scene_id=scene.scene_id,
                    version_id="v7",
                    beat_index=b_idx,
                    title=f"Beat {b_idx}",
                    action_text=f"Beat {b_idx} in scene {scene.scene_number}: specific creative action unfolding.",
                    beat_hash=beat_hash,
                    stable_lineage_key=f"beat_lineage_{beat_counter:04d}",
                )
            )
            beat_counter += 1

    # 3. Creative Uses
    uses: List[CreativeUse] = []
    for u_idx in range(1, num_uses + 1):
        assigned_scene = scenes[(u_idx - 1) % len(scenes)]
        assigned_beat = beats[(u_idx - 1) % len(beats)]
        ctx_hash = hashlib.sha256(f"USE_{u_idx}_{assigned_scene.scene_id}".encode()).hexdigest()
        uses.append(
            CreativeUse(
                use_id=f"use_{u_idx:04d}",
                version_id="v8",
                scene_or_timecode=f"Scene {assigned_scene.scene_number}",
                asset_type="music" if u_idx % 2 == 0 else "artwork",
                description=f"Creative Entity #{u_idx}",
                duration_or_prominence="featured",
                context=f"Entity depicted prominently in scene {assigned_scene.scene_number}.",
                stable_lineage_key=f"use_lineage_{u_idx:04d}",
                context_hash=ctx_hash,
                metadata={"scene_id": assigned_scene.scene_id, "beat_id": assigned_beat.beat_id},
            )
        )

    # 4. Atomic Rights Claims
    claims: List[AtomicRightsClaim] = []
    for c_idx in range(1, num_claims + 1):
        parent_use = uses[(c_idx - 1) % len(uses)]
        claims.append(
            AtomicRightsClaim(
                claim_id=f"claim_{c_idx:04d}",
                occurrence_id=parent_use.use_id,
                occurrence_lineage_id=parent_use.stable_lineage_key,
                right_category="composition" if c_idx % 2 == 0 else "master_recording",
                rights_subject=f"Rights Subject {c_idx}",
                disposition=CensusDisposition.APPROVED,
                approval_origin=ApprovalOrigin.INITIAL_APPROVAL,
            )
        )

    # 5. Contract Agreements
    contracts: List[ContractAgreement] = []
    for k_idx in range(1, num_contracts + 1):
        target_use = uses[(k_idx - 1) % len(uses)]
        agr_hash = hashlib.sha256(f"AGR_{k_idx}_{target_use.use_id}".encode()).hexdigest()
        contracts.append(
            ContractAgreement(
                agreement_id=f"contract_{k_idx:04d}",
                stable_lineage_key=target_use.stable_lineage_key,
                licensor=f"Licensor Group {k_idx}",
                licensee="Production Co.",
                scope="Worldwide, all media in perpetuity",
                term="Perpetuity",
                agreement_hash=agr_hash,
                is_active=True,
            )
        )

    # 6. Public Evidence Snapshots
    evidence_list: List[PublicEvidenceSnapshot] = []
    for e_idx in range(1, num_evidence + 1):
        target_use = uses[(e_idx - 1) % len(uses)]
        evidence_list.append(
            PublicEvidenceSnapshot(
                snapshot_id=f"evidence_{e_idx:04d}",
                use_id=target_use.use_id,
                stable_lineage_key=target_use.stable_lineage_key,
                query=f"clearance evidence inquiry {e_idx}",
                source_url=f"https://records.example.com/record/{e_idx}",
                source_title=f"USPTO / Copyright Office Registry Record {e_idx}",
                excerpt=f"Official registration record verifying rights holder for entity #{target_use.use_id}.",
                stance=EvidenceStance.SUPPORTING if e_idx % 4 != 0 else EvidenceStance.CONTRADICTORY,
            )
        )

    # 7. Clarification Requests
    clarifications: List[ClarificationRequest] = []
    for cl_idx in range(1, num_clarifications + 1):
        target_use = uses[(cl_idx - 1) % len(uses)]
        target_claim = claims[(cl_idx - 1) % len(claims)]
        clarifications.append(
            ClarificationRequest(
                request_id=f"clarif_{cl_idx:04d}",
                run_id=run_id,
                claim_id=target_claim.claim_id,
                revision_id="v8",
                stable_lineage_key=target_use.stable_lineage_key,
                question_text=f"Clarification regarding sub-licensing terms on {target_use.use_id}.",
                status="resolved",
            )
        )

    # 8. Counsel Decisions
    decisions: List[CounselDecision] = []
    for d_idx in range(1, num_decisions + 1):
        target_use = uses[(d_idx - 1) % len(uses)]
        target_contract = contracts[(d_idx - 1) % len(contracts)]
        target_evidence = evidence_list[(d_idx - 1) % len(evidence_list)]
        decisions.append(
            CounselDecision(
                decision_id=f"decision_{d_idx:04d}",
                use_id=target_use.use_id,
                stable_lineage_key=target_use.stable_lineage_key,
                applicable_version_id="v8",
                status=DecisionStatus.APPROVED if d_idx % 5 != 0 else DecisionStatus.APPROVED_WITH_CONDITION,
                rationale=f"Clearance approved based on contract grant and registry evidence for use #{target_use.use_id}.",
                evidence_snapshot_ids=[target_evidence.snapshot_id, target_contract.agreement_id],
            )
        )

    return {
        "org_id": org_id,
        "prod_id": prod_id,
        "run_id": run_id,
        "scenes": scenes,
        "beats": beats,
        "uses": uses,
        "claims": claims,
        "contracts": contracts,
        "evidence_list": evidence_list,
        "clarifications": clarifications,
        "decisions": decisions,
    }


def run_benchmark_trial(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Executes a single benchmark run through the full clearance dependency graph pipeline:
    1. Graph Construction (nodes + multi-tier causal edges + acyclicity validation)
    2. Deterministic Topological Sorting (heapq min-heap Kahn's algorithm)
    3. Elementary Cycle Detection (3-color DFS coloring)
    4. Transitive Invalidation Propagation (forward BFS + causal backtracking + SHA-256 hash chaining)
    Returns timing metrics in milliseconds.
    """
    # 1. Construction
    t0 = time.perf_counter()
    graph = build_clearance_graph(
        base_uses=data["uses"],
        contracts=data["contracts"],
        evidence_snapshots=data["evidence_list"],
        prior_decisions=data["decisions"],
        scene_contexts=data["scenes"],
        script_beats=data["beats"],
        atomic_claims=data["claims"],
        clarification_requests=data["clarifications"],
        organization_id=data["org_id"],
    )
    t1 = time.perf_counter()
    construction_ms = (t1 - t0) * 1000.0

    # 2. Topological Sort
    t2 = time.perf_counter()
    sorted_nodes = graph.topological_sort()
    t3 = time.perf_counter()
    topological_ms = (t3 - t2) * 1000.0

    # 3. Cycle Detection
    t4 = time.perf_counter()
    cycles = graph.find_cycles()
    t5 = time.perf_counter()
    cycle_detection_ms = (t5 - t4) * 1000.0

    # 4. Transitive Invalidation Propagation
    # Simulate 5 upstream shifts (1 scene modified, 2 beats altered, 2 evidence snapshots changed)
    changed_nodes = {
        data["scenes"][0].scene_id: {"reason_code": "SCENE_CONTEXT_MODIFIED", "explanation": "Scene rewrite"},
        data["beats"][0].beat_id: {"reason_code": "SCRIPT_BEAT_ALTERED", "explanation": "Beat action modified"},
        data["beats"][1].beat_id: {"reason_code": "SCRIPT_BEAT_ALTERED", "explanation": "Beat dialogue trimmed"},
        data["evidence_list"][0].snapshot_id: {"reason_code": "EXTERNAL_EVIDENCE_SHIFT", "explanation": "Court finding reversed"},
        data["evidence_list"][1].snapshot_id: {"reason_code": "EXTERNAL_EVIDENCE_SHIFT", "explanation": "Trademark expired"},
    }
    t6 = time.perf_counter()
    notices = graph.propagate_invalidation(
        changed_nodes=changed_nodes,
        run_id=data["run_id"],
        production_id=data["prod_id"],
    )
    t7 = time.perf_counter()
    invalidation_ms = (t7 - t6) * 1000.0

    total_resolution_ms = construction_ms + topological_ms + invalidation_ms

    return {
        "node_count": float(graph.node_count()),
        "edge_count": float(graph.edge_count()),
        "sorted_node_count": float(len(sorted_nodes)),
        "cycle_count": float(len(cycles)),
        "notice_count": float(len(notices)),
        "construction_ms": construction_ms,
        "topological_ms": topological_ms,
        "cycle_detection_ms": cycle_detection_ms,
        "invalidation_ms": invalidation_ms,
        "total_resolution_ms": total_resolution_ms,
    }


def execute_full_benchmark_suite(trials: int = 5) -> Dict[str, Any]:
    """
    Executes multiple benchmark trials and computes aggregate performance statistics.
    """
    data = generate_150_page_screenplay_data()
    results: List[Dict[str, float]] = []

    # Warm-up run
    run_benchmark_trial(data)

    for _ in range(trials):
        results.append(run_benchmark_trial(data))

    avg_construction = sum(r["construction_ms"] for r in results) / len(results)
    avg_topological = sum(r["topological_ms"] for r in results) / len(results)
    avg_cycle = sum(r["cycle_detection_ms"] for r in results) / len(results)
    avg_invalidation = sum(r["invalidation_ms"] for r in results) / len(results)
    avg_total = sum(r["total_resolution_ms"] for r in results) / len(results)
    max_total = max(r["total_resolution_ms"] for r in results)

    return {
        "node_count": int(results[0]["node_count"]),
        "edge_count": int(results[0]["edge_count"]),
        "trials": trials,
        "avg_construction_ms": avg_construction,
        "avg_topological_ms": avg_topological,
        "avg_cycle_detection_ms": avg_cycle,
        "avg_invalidation_ms": avg_invalidation,
        "avg_total_resolution_ms": avg_total,
        "max_total_resolution_ms": max_total,
        "sla_target_ms": 150.0,
        "sla_met": avg_total < 150.0 and max_total < 150.0,
    }


if __name__ == "__main__":
    suite = execute_full_benchmark_suite(trials=5)
    print("=" * 70)
    print("LIENMARK CLEARANCE DEPENDENCY GRAPH PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"Screenplay Scope:       150-page screenplay (>300 claims)")
    print(f"Graph Topology:         {suite['node_count']} nodes, {suite['edge_count']} causal edges")
    print(f"Benchmark Trials:       {suite['trials']} trials")
    print("-" * 70)
    print(f"Construction & Wiring:  {suite['avg_construction_ms']:.2f} ms")
    print(f"Kahn Min-Heap TopoSort: {suite['avg_topological_ms']:.2f} ms")
    print(f"3-Color DFS Cycles:     {suite['avg_cycle_detection_ms']:.2f} ms")
    print(f"Transitive Invalidation:{suite['avg_invalidation_ms']:.2f} ms")
    print("-" * 70)
    print(f"Total Resolution Time:  {suite['avg_total_resolution_ms']:.2f} ms (max: {suite['max_total_resolution_ms']:.2f} ms)")
    print(f"Roadmap SLA Obligation: < 150.0 ms")
    print(f"SLA Compliance Status:  {'PASS (COMPLIANT)' if suite['sla_met'] else 'FAIL'}")
    headroom = ((150.0 - suite['avg_total_resolution_ms']) / 150.0) * 100.0
    print(f"Performance Headroom:   {headroom:.1f}%")
    print("=" * 70)
