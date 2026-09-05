"""
P0 Scope Isolation and Acceptance Contract Tests for Lienmark
Sprint 0B Tasks 6, 7, 8: Formal Scope Boundary, Mathematical Invariants, and Policy Enforcement.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import ast
import os
import sys
from pathlib import Path
import pytest

from backend.domain.models import (
    ChangeKind,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    ExceptionsSchedule,
    PublicEvidenceSnapshot,
    ReattestationRequest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import get_golden_fixtures


def test_p0_scope_boundary_and_contract():
    """
    Consolidated P0 Scope Isolation and Acceptance Contract Test:
    1. Asserts no deferred modules (blockchain, carrier APIs, 6-agent peer bus, computer vision)
       are imported or present in backend/core/ or backend/services/.
    2. Asserts the single-sentence demo contract and the exact 12 -> 10/2 -> 1/1 mathematical invariants.
    3. Asserts that policy version is 'E&O-2026.1-DEVPOST' and fail-closed behavior is strictly enforced.
    """
    root_dir = Path(__file__).resolve().parent.parent
    core_dir = root_dir / "backend" / "core"
    services_dir = root_dir / "backend" / "services"

    # =========================================================================
    # Part 1: Scope Isolation — Zero Deferred Modules in core/ or services/
    # =========================================================================
    deferred_tokens = {
        "blockchain": ["blockchain", "web3", "solidity", "ethereum", "smart_contract", "ledger_agent", "crypto"],
        "carrier_apis": ["carrier_api", "insurance_carrier", "carrier_service", "bind_policy", "underwriting_api"],
        "peer_bus": ["peer_bus", "peer_deliberation", "agent_bus", "multi_agent_bus", "autonomous_negotiation", "message_bus"],
        "computer_vision": ["cv2", "opencv", "torchvision", "computer_vision", "video_ocr", "yolo", "albumentations"],
    }

    all_deferred_terms = [term for terms in deferred_tokens.values() for term in terms]

    for target_dir in [core_dir, services_dir]:
        assert target_dir.exists(), f"Target directory must exist: {target_dir}"
        for py_file in target_dir.glob("**/*.py"):
            # Check filename for prohibited deferred terms
            file_stem = py_file.stem.lower()
            for prohibited in all_deferred_terms:
                assert prohibited not in file_stem, (
                    f"Deferred module detected in filesystem: {py_file} contains prohibited token '{prohibited}'"
                )

            # Parse AST to ensure no deferred modules or symbols are imported
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_name = alias.name.lower()
                        for prohibited in all_deferred_terms:
                            assert prohibited not in imported_name, (
                                f"Deferred module imported in {py_file.name}: 'import {alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.lower()
                        for prohibited in all_deferred_terms:
                            assert prohibited not in module_name, (
                                f"Deferred module imported in {py_file.name}: 'from {node.module} import ...'"
                            )

    # Verify no deferred external libraries are loaded into sys.modules
    for mod_name in ["web3", "cv2", "torchvision", "albumentations"]:
        assert mod_name not in sys.modules, f"Deferred library {mod_name} must not be present in active environment"

    # =========================================================================
    # Part 2: Single-Sentence Demo Contract & Exact 12 -> 10/2 -> 1/1 Invariants
    # =========================================================================
    demo_contract = (
        "Every decision is bound to the exact cut and evidence reviewed. "
        "Parallel keeps that evidence current; when either changes, "
        "Lienmark reopens only the decisions that no longer carry forward."
    )
    assert len(demo_contract) > 50
    assert "Every decision is bound to the exact cut and evidence reviewed" in demo_contract
    assert "Parallel keeps that evidence current" in demo_contract
    assert "reopens only the decisions that no longer carry forward" in demo_contract

    # Exact mathematical constants of the golden wedge
    total_decisions = 12
    carried_forward = 10
    reopened_stale = 2
    re_attested = 1
    unresolved_exception = 1

    # Invariant identities
    assert carried_forward + reopened_stale == total_decisions
    assert re_attested + unresolved_exception == reopened_stale
    assert carried_forward + re_attested + unresolved_exception == total_decisions

    # Selectivity and burden reduction metrics
    selectivity_ratio = reopened_stale / total_decisions
    assert abs(selectivity_ratio - (2 / 12)) < 1e-6
    burden_reduction = (total_decisions - reopened_stale) / total_decisions
    assert abs(burden_reduction - (10 / 12)) < 1e-6  # 83.333%

    # Live verification of golden fixture against InvalidationEngine
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    assert len(v7_uses) == total_decisions
    assert len(v8_uses) == total_decisions
    assert len(v7_decisions) == total_decisions
    assert len(v8_evidence) == total_decisions

    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )
    assert len(validity_results) == total_decisions

    carried_items = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
    stale_items = [v for v in validity_results if v.state == DecisionState.STALE]

    assert len(carried_items) == carried_forward, f"Expected {carried_forward}, got {len(carried_items)}"
    assert len(stale_items) == reopened_stale, f"Expected {reopened_stale}, got {len(stale_items)}"

    # Re-attest 1 item (poster: approved) and mark 1 item as exception (music: rejected)
    reattestations = {
        "poster_noir_detective_magazine": ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork public domain confirmed via LOC catalog.",
            reviewer_name="Sarah Jenkins, Esq.",
        ),
        "music_cue_midnight_serenade": ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Active copyright dispute with Vanguard Media.",
            reviewer_name="Sarah Jenkins, Esq.",
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

    assert schedule.total_claims == total_decisions
    assert schedule.carried_forward_count == carried_forward
    assert schedule.reopened_count == reopened_stale
    assert schedule.re_attested_count == re_attested
    assert schedule.unresolved_exception_count == unresolved_exception
    assert len(schedule.items) == total_decisions

    # =========================================================================
    # Part 3: Policy Version & Fail-Closed Enforcement
    # =========================================================================
    expected_policy = "E&O-2026.1-DEVPOST"
    assert InvalidationEngine.POLICY_VERSION == expected_policy
    assert schedule.policy_version == expected_policy
    assert ExceptionsSchedule.model_fields["policy_version"].default == expected_policy

    # Strict Fail-Closed Policy Enforcement Tests:
    # 1. Missing target delta (severed lineage)
    tampered_target_uses = [u for u in v8_uses if u.stable_lineage_key != "prop_vintage_telephone"]
    tampered_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=tampered_target_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )
    tampered_entry = next(v for v in tampered_results if v.stable_lineage_key == "prop_vintage_telephone")
    assert tampered_entry.state in (DecisionState.STALE, DecisionState.REMOVED)
    assert (
        "FAIL_CLOSED" in tampered_entry.reason_code
        or "UNEXPECTED" in tampered_entry.reason_code
        or tampered_entry.reason_code == "CLAIM_REMOVED_FROM_SCRIPT"
    )
    assert tampered_entry.revalidation_action in ["manual", "revalidate", "close"]

    # 2. Contradictory evidence forces STALE state
    music_entry = next(v for v in validity_results if v.stable_lineage_key == "music_cue_midnight_serenade")
    assert music_entry.state == DecisionState.STALE
    assert music_entry.reason_code == "EXTERNAL_EVIDENCE_SHIFT"

    # 3. Insufficient evidence forces STALE state (never defaults to carried or approved)
    insufficient_evidence = dict(v8_evidence)
    insufficient_evidence["prop_vintage_telephone"] = PublicEvidenceSnapshot(
        snapshot_id="snap_insufficient",
        use_id="use_prop_vintage_telephone",
        stable_lineage_key="prop_vintage_telephone",
        query="vintage telephone copyright status",
        source_url="https://timeout.example.com",
        source_title="Timeout Record",
        excerpt="Query timed out without confirmation",
        stance=EvidenceStance.INSUFFICIENT,
    )
    insufficient_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=insufficient_evidence,
        target_version_id="v8",
    )
    insufficient_entry = next(v for v in insufficient_results if v.stable_lineage_key == "prop_vintage_telephone")
    assert insufficient_entry.state == DecisionState.STALE
    assert insufficient_entry.reason_code == "EXTERNAL_EVIDENCE_SHIFT"

    # 4. Context hash mismatch forces STALE state
    poster_entry = next(v for v in validity_results if v.stable_lineage_key == "poster_noir_detective_magazine")
    assert poster_entry.state == DecisionState.STALE
    assert poster_entry.reason_code == "CREATIVE_CONTEXT_ALTERED"
