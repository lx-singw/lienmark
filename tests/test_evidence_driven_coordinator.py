"""
tests/test_evidence_driven_coordinator.py

Exhaustive verification of the dynamic 8-action EvidenceDrivenCoordinator:
1. 8-Action Decision Matrix Enum (CoordinatorAction)
2. Dynamic Decision Loop (decide_next_action) with all 8 branches
3. Dual-model support: AtomicRightsClaim and CreativeUse backward compatibility
4. Granular Claim-Level Suspension (suspend_claim) & Sibling Concurrency
5. Claim-Level Resumption (resume_claim) with Cut Revision Freshness Check (CANCELLED_SUPERSEDED)
6. Durable Checkpoint Store & Simulated Container Restart
7. Golden test invariant preservation (12 items)
"""

import pytest
import uuid
from datetime import datetime, timezone

from backend.domain.models import (
    CreativeUse,
    AtomicRightsClaim,
    ClarificationRequest,
    WorkflowReason,
    CensusDisposition,
    ApprovalOrigin,
    ContractAgreement,
    PublicEvidenceSnapshot,
    EvidenceStance,
)
from backend.orchestration.adk_pipeline import (
    CoordinatorAction,
    CoordinatorBudget,
    CoordinatorDecision,
    CoordinatorCheckpoint,
    EvidenceDrivenCoordinator,
    normalize_to_atomic_claim,
    ADKClearancePipeline,
)
from backend.fixtures.golden_dataset import get_golden_fixtures


# =============================================================================
# 1. 8-ACTION DECISION MATRIX ENUM TESTS
# =============================================================================

def test_coordinator_action_enum_members():
    """Verify all 8 canonical actions are explicitly defined with codes and names."""
    expected_actions = [
        "ACT_01_RETRIEVE_PRIVATE_AGREEMENTS",
        "ACT_02_SEARCH_PUBLIC_SOURCES",
        "ACT_03_INSPECT_SPECIFIC_SOURCE",
        "ACT_04_SPLIT_INVESTIGATION",
        "ACT_05_ADVERSARIAL_DISCONFIRMATION",
        "ACT_06_REQUEST_INFORMATION",
        "ACT_07_PREPARE_REVIEW_BRIEF",
        "ACT_08_STOP_UNRESOLVED",
    ]

    for act_name in expected_actions:
        assert hasattr(CoordinatorAction, act_name), f"Missing {act_name} on CoordinatorAction"
        member = getattr(CoordinatorAction, act_name)
        assert member.value == act_name
        assert member.code.startswith("ACT_0")

    assert CoordinatorAction.ACT_01_RETRIEVE_PRIVATE_AGREEMENTS.code == "ACT_01"
    assert CoordinatorAction.ACT_01_RETRIEVE_PRIVATE_AGREEMENTS.action_name == "Retrieve Private Agreements"
    assert CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION.code == "ACT_05"
    assert CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION.action_name == "Adversarial Disconfirmation"


# =============================================================================
# 2. CLAIM NORMALIZATION & BACKWARD COMPATIBILITY
# =============================================================================

def test_normalize_atomic_rights_claim():
    """Verify AtomicRightsClaim passes through normalization unchanged."""
    claim = AtomicRightsClaim(
        claim_id="clm_01",
        occurrence_id="occ_01",
        occurrence_lineage_id="lin_01",
        right_category="trademark",
        rights_subject="Acme Neon Sign",
    )
    norm = normalize_to_atomic_claim(claim)
    assert norm is claim
    assert norm.claim_id == "clm_01"
    assert norm.right_category == "trademark"


def test_normalize_creative_use_backward_compatibility():
    """Verify CreativeUse maps seamlessly into AtomicRightsClaim."""
    use = CreativeUse(
        use_id="use_midnight_serenade",
        version_id="v8",
        scene_or_timecode="Scene 42",
        asset_type="music",
        description="Midnight Serenade Foreground Playback",
        duration_or_prominence="20s feature",
        context="Detective enters diner while jukebox plays",
        stable_lineage_key="music_cue_midnight_serenade",
        context_hash="hash_abc123",
        intended_territory=["US", "CA"],
        intended_media=["theatrical", "svod"],
    )
    norm = normalize_to_atomic_claim(use)
    assert isinstance(norm, AtomicRightsClaim)
    assert norm.claim_id == "clm_use_midnight_serenade"
    assert norm.occurrence_lineage_id == "music_cue_midnight_serenade"
    assert norm.right_category == "composite"  # music cue detected as composite
    assert norm.intended_territory == ["US", "CA"]
    assert norm.intended_media == ["theatrical", "svod"]
    assert norm.disposition == CensusDisposition.UNKNOWN


# =============================================================================
# 3. DYNAMIC DECISION LOOP (decide_next_action) BRANCH VERIFICATION
# =============================================================================

def test_decision_budget_exhaustion():
    """Verify budget exhaustion immediately yields ACT_08_STOP_UNRESOLVED with WAITING_FOR_BUDGET."""
    budget = CoordinatorBudget(max_calls=2, used_calls=2)
    coordinator = EvidenceDrivenCoordinator(budget=budget)

    claim = AtomicRightsClaim(
        claim_id="clm_budget_test",
        occurrence_id="occ_budget",
        occurrence_lineage_id="lin_budget",
        right_category="copyright",
        rights_subject="Vintage Painting",
    )
    decision = coordinator.decide_next_action(claim)

    assert decision.action == CoordinatorAction.ACT_08_STOP_UNRESOLVED
    assert decision.reason == WorkflowReason.WAITING_FOR_BUDGET
    assert claim.workflow_reason == WorkflowReason.WAITING_FOR_BUDGET
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW


def test_decision_provider_offline():
    """Verify public search failure (HTTP 504 / timeout) yields ACT_08_STOP_UNRESOLVED with PROVIDER_OFFLINE."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_offline_test",
        occurrence_id="occ_offline",
        occurrence_lineage_id="lin_offline",
        right_category="copyright",
        rights_subject="1950 Film Poster",
    )
    coordinator.register_claim(claim)
    # Simulate HTTP 504 gateway timeout from Parallel Search
    coordinator.claim_contexts[claim.claim_id]["last_search_status"] = 504

    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_08_STOP_UNRESOLVED
    assert decision.reason == WorkflowReason.PROVIDER_OFFLINE
    assert claim.workflow_reason == WorkflowReason.PROVIDER_OFFLINE
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW


def test_decision_composite_music_cue_split():
    """Verify composite music cue triggers ACT_04_SPLIT_INVESTIGATION."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_music_cue",
        occurrence_id="occ_music",
        occurrence_lineage_id="music_cue_midnight_serenade",
        right_category="composite",
        rights_subject="Midnight Serenade",
    )
    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_04_SPLIT_INVESTIGATION


def test_decision_private_agreements_retrieval():
    """Verify un-evaluated private agreements trigger ACT_01_RETRIEVE_PRIVATE_AGREEMENTS."""
    contract = ContractAgreement(
        agreement_id="agree_acme_diner_prop",
        stable_lineage_key="prop_neon_sign_acme_diner",
        licensor="Acme Prop House",
        licensee="Lienmark Studios",
        scope="theatrical, streaming",
        term="perpetual",
        agreement_hash="hash_acme_prop_01",
        is_active=True,
    )
    coordinator = EvidenceDrivenCoordinator(contracts=[contract])
    claim = AtomicRightsClaim(
        claim_id="clm_neon_sign",
        occurrence_id="occ_neon",
        occurrence_lineage_id="prop_neon_sign_acme_diner",
        right_category="trademark",
        rights_subject="Acme Prop House Neon Sign",
    )
    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_01_RETRIEVE_PRIVATE_AGREEMENTS


def test_decision_scope_mismatch_clarification():
    """Verify scope mismatch or missing crucial license triggers ACT_06_REQUEST_INFORMATION."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_scope_mismatch",
        occurrence_id="occ_scope",
        occurrence_lineage_id="song_master_vanguard",
        right_category="master_recording",
        rights_subject="Vanguard Master Recording",
        intended_media=["theatrical", "svod"],
        intended_territory=["Worldwide"],
        licensor_grant_confirmed=False,
    )
    coordinator.register_claim(claim)
    # Private agreements were evaluated, but 0 matching contracts were found
    coordinator.claim_contexts[claim.claim_id]["private_agreements_evaluated"] = True

    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_06_REQUEST_INFORMATION
    assert decision.reason == WorkflowReason.WAITING_FOR_INFORMATION


def test_decision_public_search_phase_1():
    """Verify unperformed public search triggers ACT_02_SEARCH_PUBLIC_SOURCES."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_poster_noir",
        occurrence_id="occ_poster",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine 1948 Cover",
    )
    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES


def test_decision_adversarial_disconfirmation_phase_2():
    """Verify preliminary search findings trigger ACT_05_ADVERSARIAL_DISCONFIRMATION."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_poster_noir",
        occurrence_id="occ_poster",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine 1948 Cover",
    )
    coordinator.register_claim(claim)
    # Simulate Phase 1 completed with preliminary hit
    coordinator.claim_contexts[claim.claim_id]["public_search_performed"] = True
    coordinator.claim_contexts[claim.claim_id]["preliminary_evidence"] = {
        "source_title": "Catalog of Copyright Entries 1948",
        "excerpt": "Registered Class B, No. 49102",
    }

    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION


def test_decision_prepare_review_brief_when_ready():
    """Verify collected evidence and verified scope trigger ACT_07_PREPARE_REVIEW_BRIEF."""
    coordinator = EvidenceDrivenCoordinator()
    claim = AtomicRightsClaim(
        claim_id="clm_poster_noir",
        occurrence_id="occ_poster",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine 1948 Cover",
    )
    coordinator.register_claim(claim)
    ctx = coordinator.claim_contexts[claim.claim_id]
    ctx["public_search_performed"] = True
    ctx["public_evidence"] = {"source_title": "LOC Renewal Catalog", "excerpt": "No renewal record found"}
    ctx["adversarial_disconfirmation_performed"] = True

    decision = coordinator.decide_next_action(claim)
    assert decision.action == CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF


# =============================================================================
# 4. GRANULAR CLAIM-LEVEL SUSPENSION & SIBLING CONCURRENCY
# =============================================================================

def test_claim_level_suspension_isolation():
    """Verify suspend_claim suspends only target claim while sibling claims continue."""
    coordinator = EvidenceDrivenCoordinator(revision_id="v8")

    claim_a = AtomicRightsClaim(
        claim_id="clm_prop_gun",
        occurrence_id="occ_gun",
        occurrence_lineage_id="prop_vintage_revolver",
        right_category="prop",
        rights_subject="Vintage 1938 Revolver",
    )
    claim_b = AtomicRightsClaim(
        claim_id="clm_poster_art",
        occurrence_id="occ_poster",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine Cover",
    )

    coordinator.register_claim(claim_a)
    coordinator.register_claim(claim_b)

    # Suspend only Claim A
    clrf = coordinator.suspend_claim(
        claim=claim_a,
        question_text="Please provide armory rental invoice for 1938 Revolver",
        scope_field_missing="rental_invoice",
        required_document_type="Armory Rental Agreement",
        assigned_role="props_master",
    )

    assert isinstance(clrf, ClarificationRequest)
    assert clrf.claim_id == claim_a.claim_id
    assert clrf.revision_id == "v8"
    assert clrf.scope_field_missing == "rental_invoice"
    assert clrf.status == "pending"

    # Claim A is suspended in WAITING_FOR_INFORMATION / NEEDS_REVIEW
    assert coordinator.claim_states[claim_a.claim_id] == "waiting_for_information"
    assert claim_a.workflow_reason == WorkflowReason.WAITING_FOR_INFORMATION
    assert claim_a.disposition == CensusDisposition.NEEDS_REVIEW
    assert claim_a.clarification_request_id == clrf.request_id

    # SIBLING CONCURRENCY: Claim B remains evaluating and unaffected!
    assert coordinator.claim_states[claim_b.claim_id] == "evaluating"
    assert claim_b.workflow_reason == WorkflowReason.NEWLY_DISCOVERED
    assert claim_b.disposition == CensusDisposition.UNKNOWN


# =============================================================================
# 5. CLAIM-LEVEL RESUMPTION & CUT REVISION FRESHNESS CHECK
# =============================================================================

def test_resume_claim_superseded_cut_detection():
    """Verify resume_claim cancels and marks CANCELLED_SUPERSEDED if scene was removed in current cut revision."""
    coordinator = EvidenceDrivenCoordinator(revision_id="v8")
    claim = AtomicRightsClaim(
        claim_id="clm_scene42_song",
        occurrence_id="occ_scene42",
        occurrence_lineage_id="music_cue_scene_42_cut",
        right_category="master_recording",
        rights_subject="Scene 42 Diner Jukebox Song",
    )
    coordinator.register_claim(claim)
    clrf = coordinator.suspend_claim(claim, "Provide Master License")

    # Target revision is v9, where Scene 42 has been CUT ENTIRELY
    v9_active_uses = [
        {"claim_id": "clm_scene10_intro", "occurrence_lineage_id": "intro_car"},
        {"claim_id": "clm_scene50_climax", "occurrence_lineage_id": "climax_rooftop"},
    ]

    res = coordinator.resume_claim(
        claim_id=claim.claim_id,
        response_text="Attached Master License from Vanguard",
        current_revision_uses=v9_active_uses,
        current_revision_id="v9",
    )

    assert res["status"] == "CANCELLED_SUPERSEDED"
    assert res["is_active"] is False
    assert "CANCELLED_SUPERSEDED" in claim.notes
    assert coordinator.claim_states[claim.claim_id] == "cancelled_superseded"
    assert clrf.status == "cancelled_superseded"


def test_resume_claim_fresh_active_occurrence():
    """Verify resume_claim succeeds when asset remains active in current revision, resuming 8-action loop."""
    coordinator = EvidenceDrivenCoordinator(revision_id="v8")
    claim = AtomicRightsClaim(
        claim_id="clm_poster_noir",
        occurrence_id="occ_poster",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine Cover",
    )
    coordinator.register_claim(claim)
    clrf = coordinator.suspend_claim(claim, "Need publisher clearance info")

    # Asset is present in active v8 revision
    v8_active_uses = [claim]

    res = coordinator.resume_claim(
        claim_id=claim.claim_id,
        response_text="Publisher confirmed public domain release",
        attached_document_ref="gs://lienmark-vault/docs/loc_cert.pdf",
        current_revision_uses=v8_active_uses,
        current_revision_id="v8",
    )

    assert res["status"] == "RESUMED"
    assert res["is_active"] is True
    assert clrf.status == "resolved"
    assert claim.licensor_grant_confirmed is True
    assert claim.workflow_reason == WorkflowReason.NORMAL_OPERATION
    assert "next_action" in res


# =============================================================================
# 6. DURABLE CHECKPOINT STORE & SIMULATED CONTAINER RESTART
# =============================================================================

def test_durable_checkpoint_store_and_container_restart():
    """Verify coordinator state serializes to JSON and faithfully rehydrates simulating container restart."""
    coordinator = EvidenceDrivenCoordinator(run_id="run_checkpoint_test", revision_id="v8")
    coordinator.budget.consume(calls=3, tokens=1200, dollars=0.15)

    claim_1 = AtomicRightsClaim(
        claim_id="clm_1",
        occurrence_id="occ_1",
        occurrence_lineage_id="asset_1",
        right_category="copyright",
        rights_subject="Artwork 1",
    )
    claim_2 = AtomicRightsClaim(
        claim_id="clm_2",
        occurrence_id="occ_2",
        occurrence_lineage_id="asset_2",
        right_category="trademark",
        rights_subject="Brand 2",
    )
    coordinator.register_claim(claim_1)
    coordinator.register_claim(claim_2)
    coordinator.suspend_claim(claim_2, "Missing trademark clearance")

    # 1. Export checkpoint to JSON
    cp_json = coordinator.export_checkpoint_json()
    assert isinstance(cp_json, str)
    assert "run_checkpoint_test" in cp_json
    assert "clm_1" in cp_json
    assert "clm_2" in cp_json

    # 2. Simulate container restart: hydrate brand new instance
    restarted_coord = EvidenceDrivenCoordinator.from_checkpoint(cp_json)

    assert restarted_coord.run_id == coordinator.run_id
    assert restarted_coord.revision_id == coordinator.revision_id
    assert restarted_coord.budget.used_calls == 3
    assert restarted_coord.budget.used_tokens == 1200
    assert restarted_coord.budget.used_dollars == 0.15
    assert len(restarted_coord.claims) == 2
    assert restarted_coord.claim_states["clm_2"] == "waiting_for_information"
    assert len(restarted_coord.clarification_requests) == 1

    # Verify coordinator can continue execution after restart
    resume_res = restarted_coord.resume_claim(
        claim_id="clm_2",
        response_text="Trademark consent letter attached",
        attached_document_ref="gs://vault/consent.pdf",
    )
    assert resume_res["status"] == "RESUMED"


# =============================================================================
# 7. GOLDEN TEST INVARIANT PRESERVATION (12 Items: 10 Carried / 2 Reopened)
# =============================================================================

@pytest.mark.asyncio
async def test_golden_dataset_compatibility_preserved():
    """Verify ADKClearancePipeline maintains exact 12 -> 10/2 invariant preservation."""
    pipeline = ADKClearancePipeline()
    result = await pipeline.execute(force_offline=True)

    assert result.total_claims == 12
    assert result.carried_forward_count == 10
    assert result.reopened_count == 2
    assert len(result.claims) == 12
    assert len(result.counsel_briefings) == 2
    assert "poster_noir_detective_magazine" in result.counsel_briefings
    assert "music_cue_midnight_serenade" in result.counsel_briefings
    assert len(result.reconciliation_results) == 12


# =============================================================================
# 8. SPLIT INVESTIGATION & MULTI-ACTION ORCHESTRATION TESTS
# =============================================================================

def test_split_claim_investigation():
    """Verify split_claim creates independent Composition and Master Sound Recording child claims."""
    coordinator = EvidenceDrivenCoordinator()
    parent = AtomicRightsClaim(
        claim_id="clm_parent_music",
        occurrence_id="occ_music_01",
        occurrence_lineage_id="music_midnight_serenade",
        right_category="composite",
        rights_subject="Midnight Serenade Foreground Playback",
        intended_territory=["Worldwide"],
        intended_media=["theatrical", "streaming"],
    )
    children = coordinator.split_claim(parent)
    assert len(children) == 2
    comp, master = children

    assert comp.claim_id == "clm_parent_music_comp"
    assert comp.right_category == "composition"
    assert "Composer / Music Publisher" in comp.rights_subject

    assert master.claim_id == "clm_parent_music_master"
    assert master.right_category == "master_recording"
    assert "Record Label / Master Rights Holder" in master.rights_subject

    assert coordinator.claim_states["clm_parent_music"] == "split"
    assert "clm_parent_music_comp" in coordinator.claims
    assert "clm_parent_music_master" in coordinator.claims


@pytest.mark.asyncio
async def test_execute_action_lifecycle():
    """Verify execute_action executes actions and records audit trace correctly."""
    contract = ContractAgreement(
        agreement_id="agree_kobalt_sync",
        stable_lineage_key="music_midnight_serenade",
        licensor="Kobalt Music Publishing",
        licensee="Lienmark Studios",
        scope="theatrical, streaming",
        term="perpetual",
        agreement_hash="hash_kobalt_01",
        is_active=True,
    )
    coordinator = EvidenceDrivenCoordinator(contracts=[contract], use_fallback=True)

    claim = AtomicRightsClaim(
        claim_id="clm_kobalt_comp",
        occurrence_id="occ_kobalt",
        occurrence_lineage_id="music_midnight_serenade",
        right_category="composition",
        rights_subject="Midnight Serenade Composition",
        intended_territory=["worldwide"],
        intended_media=["theatrical", "streaming"],
    )
    coordinator.register_claim(claim)

    # 1. Execute ACT_01
    res1 = await coordinator.execute_action(CoordinatorAction.ACT_01_RETRIEVE_PRIVATE_AGREEMENTS, claim)
    assert res1["status"] == "SUCCESS"
    assert claim.licensor_grant_confirmed is True

    # 2. Execute ACT_02
    res2 = await coordinator.execute_action(CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES, claim)
    assert res2["status"] == "SUCCESS"

    # 3. Execute ACT_05
    res3 = await coordinator.execute_action(CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION, claim)
    assert res3["status"] == "SUCCESS"

    # 4. Execute ACT_07
    res4 = await coordinator.execute_action(CoordinatorAction.ACT_07_PREPARE_REVIEW_BRIEF, claim)
    assert res4["status"] == "SUCCESS"
    assert claim.disposition == CensusDisposition.APPROVED
    assert coordinator.claim_states[claim.claim_id] == "ready_for_review"

    # Verify audit history captured
    history = coordinator.action_history[claim.claim_id]
    actions_logged = [h["code"] for h in history]
    assert "ACT_01" in actions_logged
    assert "ACT_02" in actions_logged
    assert "ACT_05" in actions_logged
    assert "ACT_07" in actions_logged


@pytest.mark.asyncio
async def test_coordinate_all_dynamic_investigation():
    """Verify coordinate_all runs concurrent dynamic investigations across claims."""
    coordinator = EvidenceDrivenCoordinator(use_fallback=True)

    # Claim 1: Normal copyright poster
    claim_1 = AtomicRightsClaim(
        claim_id="clm_c1_poster",
        occurrence_id="occ_c1",
        occurrence_lineage_id="poster_noir_detective_magazine",
        right_category="copyright",
        rights_subject="Detective Magazine 1948",
    )

    # Claim 2: Missing agreement / scope mismatch prop
    claim_2 = AtomicRightsClaim(
        claim_id="clm_c2_missing_prop",
        occurrence_id="occ_c2",
        occurrence_lineage_id="prop_unlicensed_device",
        right_category="trademark",
        rights_subject="Unlicensed Acme Device",
    )
    coordinator.claim_contexts[claim_2.claim_id] = {
        "scope_mismatch": True,
        "scope_field_missing": "trademark_license",
    }

    result = await coordinator.coordinate_all(claims=[claim_1, claim_2], max_steps_per_claim=6)

    assert result["total_claims"] >= 2
    assert "clm_c1_poster" in result["results"]
    assert "clm_c2_missing_prop" in result["results"]

    # Claim 1 reached ready_for_review
    assert coordinator.claim_states["clm_c1_poster"] == "ready_for_review"

    # Claim 2 was suspended into waiting_for_information without blocking Claim 1
    assert coordinator.claim_states["clm_c2_missing_prop"] == "waiting_for_information"
    assert len(coordinator.clarification_requests) >= 1

