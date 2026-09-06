"""
tests/test_vertical_slice_unfamiliar.py

Lienmark Unfamiliar Input & Census Test Suite
Authored strictly under Google AntiGravity for Agentic Cinema compliance.

This test suite rigorously tests all 7 unfamiliar test scenarios without relying on golden fixtures:
1. Test 1: Music Rights Split & Census Verification:
   - Creates a composite music cue ("Neon Horizon") that gets split into Composition and Master Recording claims.
   - Asserts Universal Census Equation:
     N_active = N_approved + N_conditional + N_needs_review + N_rejected + N_unknown.
   - Validates ExceptionsSchedule.verify_census_integrity() == True.
2. Test 2: Entity Disambiguation:
   - Two works with the identical title "Hold On" (one by Folk Artist A, one by Rock Band B).
   - Verifies they receive distinct asset IDs, distinct queries, and DO NOT share evidence or approvals.
3. Test 3: Trailer Promotional Restriction Trigger:
   - Asset ("Vintage Gramophone Track") has an agreement covering feature film, but with an unfulfilled obligation: "No promotional or trailer use without separate license addendum".
   - Occurrence moves from feature to trailer -> ApplicabilityAssessment.promotional_match == ScopeMatchStatus.MISMATCH and overall_match == ScopeMatchStatus.MISMATCH.
4. Test 4: Durable Claim-Level Pause & Document Resumption:
   - Claim A ("Lost Highway") lacks synchronization license -> suspended to WAITING_FOR_INFORMATION with ClarificationRequest.
   - Sibling Claim B ("City Lights") completes concurrently.
   - Simulated restart / state preservation.
   - Document arrives (resume_claim) -> freshness check passes -> Claim A resumes and completes.
5. Test 5: Counsel Rejection & Correction Loop:
   - AI recommends approval for an asset.
   - Counsel rejects recommendation and issues a directive: "Requires UK territory sync clearance".
   - Verifies: Prior finding is archived; counsel directive is recorded; a new isolated InvestigationTask is dispatched with directive as constraint; claim resets to NEEDS_REVIEW.
6. Test 6: Operational Recovery & Honest Partial Incompleteness:
   - Provider returns HTTP 504 timeout on unfamiliar asset.
   - Verifies: Does NOT manufacture false clearance or false green badge. Claim status is UNKNOWN with workflow_reason="PROVIDER_OFFLINE".
7. Test 7: Retention Policy & Legal Hold Enforcement:
   - Attempt to purge materials for a production with an active LegalHoldRecord -> blocked.
   - When hold is released and retention expires -> purge succeeds, deleted files marked SOURCE_PURGED_PER_POLICY, cryptographic hashes preserved.
"""

import copy
import hashlib
import json
import pytest
from datetime import datetime, timezone

from backend.domain.models import (
    ApplicabilityAssessment,
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
    ContractAgreement,
    ContractGrant,
    ContractObligation,
    CreativeOccurrence,
    DeletionRecord,
    EvidenceAvailability,
    ExceptionsSchedule,
    InvestigationTask,
    LegalHoldActiveError,
    LegalHoldRecord,
    PublicEvidenceSnapshot,
    RetentionClass,
    RetentionPolicy,
    ReviewerIdentity,
    ScopeMatchStatus,
    TaskStatus,
    WorkflowReason,
)
from backend.core.unfamiliar_workflows import (
    DisambiguatedEntity,
    RetentionAndLegalHoldManager,
    assess_contract_applicability,
    counsel_reject_and_correct,
    disambiguate_works,
    handle_provider_failure,
    pause_claim_investigation,
    resume_claim_investigation,
    split_music_rights_claim,
    verify_universal_census_equation,
)


# =============================================================================
# SCENARIO 1: MUSIC RIGHTS SPLIT & CENSUS VERIFICATION
# =============================================================================

class TestScenario1MusicRightsSplitAndCensusVerification:
    """
    Test 1: Music Rights Split & Census Verification:
    - Creates a composite music cue ("Neon Horizon") that gets split into Composition and Master Recording claims.
    - Asserts Universal Census Equation:
      N_active = N_approved + N_conditional + N_needs_review + N_rejected + N_unknown.
    - Validates ExceptionsSchedule.verify_census_integrity() == True.
    """

    def test_music_rights_split_into_composition_and_master(self):
        """Creates composite music cue 'Neon Horizon' and verifies two distinct claims are created."""
        cue = CreativeOccurrence(
            occurrence_id="occ_neon_horizon_001",
            occurrence_lineage_id="occ_lin_neon_horizon",
            asset_id="work_neon_horizon",
            version_id="v1",
            scene_or_timecode="Scene 12, 00:18:24-00:19:10",
            asset_type="music",
            description='Original cue "Neon Horizon" featured in downtown club scene',
            duration_or_prominence="46s prominent background music",
            context="Protagonist enters the neon nightclub",
            context_hash=hashlib.sha256(b"Neon Horizon Scene 12 context").hexdigest(),
        )

        comp_claim, master_claim = split_music_rights_claim(
            occurrence=cue,
            composition_subject="Songwriter / Apex Music Publishing Inc.",
            master_subject="Neon Records Ltd. / Master Rights",
            composition_disposition=CensusDisposition.APPROVED,
            master_disposition=CensusDisposition.NEEDS_REVIEW,
            intended_territory=["Worldwide"],
            intended_media=["theatrical", "streaming"],
            intended_context="feature",
        )

        # 1. Verify claims are distinct atomic units
        assert comp_claim.claim_id != master_claim.claim_id
        assert comp_claim.claim_id == "occ_neon_horizon_001_composition"
        assert master_claim.claim_id == "occ_neon_horizon_001_master"

        # 2. Verify rights categories and subjects
        assert comp_claim.right_category == "composition"
        assert comp_claim.rights_subject == "Songwriter / Apex Music Publishing Inc."
        assert master_claim.right_category == "master_recording"
        assert master_claim.rights_subject == "Neon Records Ltd. / Master Rights"

        # 3. Verify parent occurrence linkage
        assert comp_claim.occurrence_id == cue.occurrence_id
        assert master_claim.occurrence_id == cue.occurrence_id
        assert comp_claim.occurrence_lineage_id == cue.occurrence_lineage_id
        assert master_claim.occurrence_lineage_id == cue.occurrence_lineage_id
        assert comp_claim.asset_id == cue.asset_id
        assert master_claim.asset_id == cue.asset_id

        # 4. Verify initial dispositions
        assert comp_claim.disposition == CensusDisposition.APPROVED
        assert master_claim.disposition == CensusDisposition.NEEDS_REVIEW

    def test_universal_census_equation_integrity(self):
        """
        Asserts Universal Census Equation:
        N_active = N_approved + N_conditional + N_needs_review + N_rejected + N_unknown.
        Validates ExceptionsSchedule.verify_census_integrity() == True.
        """
        cue = CreativeOccurrence(
            occurrence_id="occ_neon_horizon_001",
            occurrence_lineage_id="occ_lin_neon_horizon",
            asset_id="work_neon_horizon",
            version_id="v1",
            scene_or_timecode="Scene 12",
            asset_type="music",
            description='Original cue "Neon Horizon"',
            duration_or_prominence="46s",
            context="Nightclub sequence",
            context_hash=hashlib.sha256(b"Neon Horizon Scene 12").hexdigest(),
        )

        comp_claim, master_claim = split_music_rights_claim(
            occurrence=cue,
            composition_disposition=CensusDisposition.APPROVED,
            master_disposition=CensusDisposition.NEEDS_REVIEW,
        )

        # Additional active claims to represent all 5 mutually exclusive census dispositions
        claim_conditional = AtomicRightsClaim(
            claim_id="clm_retro_soda_can",
            occurrence_id="occ_prop_001",
            occurrence_lineage_id="occ_lin_prop_001",
            asset_id="work_retro_soda",
            right_category="trademark",
            rights_subject="Beverage Corp",
            disposition=CensusDisposition.CONDITIONAL,
            decision_conditions=["Requires blur on secondary packaging logo"],
        )

        claim_rejected = AtomicRightsClaim(
            claim_id="clm_unlicensed_sample",
            occurrence_id="occ_sample_002",
            occurrence_lineage_id="occ_lin_sample_002",
            asset_id="work_unlicensed_sample",
            right_category="master_recording",
            rights_subject="Defunct Record Label",
            disposition=CensusDisposition.REJECTED,
            notes="Unlicensed master sample; replacement required",
        )

        claim_unknown = AtomicRightsClaim(
            claim_id="clm_graffiti_mural",
            occurrence_id="occ_artwork_003",
            occurrence_lineage_id="occ_lin_artwork_003",
            asset_id="work_graffiti_mural",
            right_category="copyright",
            rights_subject="Unknown Street Artist",
            disposition=CensusDisposition.UNKNOWN,
            workflow_reason=WorkflowReason.NEWLY_DISCOVERED,
        )

        active_claims = [
            comp_claim,          # APPROVED
            claim_conditional,   # CONDITIONAL
            master_claim,        # NEEDS_REVIEW
            claim_rejected,      # REJECTED
            claim_unknown,       # UNKNOWN
        ]

        # Construct ExceptionsSchedule
        schedule = ExceptionsSchedule(
            schedule_id="sched_unfamiliar_001",
            project_id="proj_cyber_thriller_2026",
            project_name="Neon Horizon Cyber Thriller",
            target_version_id="v1",
            base_version_id="v0",
            total_claims=len(active_claims),
            carried_forward_count=1,
            reopened_count=1,
            re_attested_count=0,
            unresolved_exception_count=3,
            atomic_claims=active_claims,
        )

        # 1. Verify individual census partitions
        assert schedule.census_approved_count == 1
        assert schedule.census_conditional_count == 1
        assert schedule.census_needs_review_count == 1
        assert schedule.census_rejected_count == 1
        assert schedule.census_unknown_count == 1

        # 2. Universal Census Equation:
        # N_active = N_approved + N_conditional + N_needs_review + N_rejected + N_unknown
        n_active = len(active_claims)
        sum_census = (
            schedule.census_approved_count
            + schedule.census_conditional_count
            + schedule.census_needs_review_count
            + schedule.census_rejected_count
            + schedule.census_unknown_count
        )
        assert n_active == sum_census == 5

        # 3. Validates ExceptionsSchedule.verify_census_integrity() == True
        assert schedule.verify_census_integrity() is True
        assert verify_universal_census_equation(schedule) is True

    def test_census_integrity_detects_partition_violation(self):
        """Verifies that an unaligned or corrupted census partition causes verify_census_integrity() to fail."""
        dummy_claim = AtomicRightsClaim(
            claim_id="clm_approved_01",
            occurrence_id="occ_01",
            occurrence_lineage_id="occ_lin_01",
            right_category="copyright",
            rights_subject="Licensor A",
            disposition=CensusDisposition.APPROVED,
        )
        schedule = ExceptionsSchedule(
            schedule_id="sched_test_mismatch",
            project_id="proj_test",
            target_version_id="v1",
            base_version_id="v0",
            total_claims=1,
            carried_forward_count=1,
            reopened_count=0,
            re_attested_count=0,
            unresolved_exception_count=0,
            atomic_claims=[dummy_claim],
        )
        # Corrupt partition counter manually
        schedule.census_approved_count = 99
        assert schedule.verify_census_integrity() is False


# =============================================================================
# SCENARIO 2: ENTITY DISAMBIGUATION
# =============================================================================

class TestScenario2EntityDisambiguation:
    """
    Test 2: Entity Disambiguation:
    - Two works with the identical title "Hold On" (one by Folk Artist A, one by Rock Band B).
    - Verifies they receive distinct asset IDs, distinct queries, and DO NOT share evidence or approvals.
    """

    def test_identical_title_disambiguation_creates_distinct_asset_ids_and_queries(self):
        """Works with identical title 'Hold On' receive distinct asset IDs and targeted queries."""
        metadata = [
            {
                "artist": "Folk Artist A",
                "genre": "Acoustic Folk",
                "scene": "Scene 04 (Campfire)",
                "prominence": "25s acoustic guitar",
            },
            {
                "artist": "Rock Band B",
                "genre": "Hard Rock",
                "scene": "Scene 28 (Car Chase)",
                "prominence": "40s high-energy track",
            },
        ]

        disambiguated = disambiguate_works(title="Hold On", entities_metadata=metadata)
        assert len(disambiguated) == 2

        folk_work = disambiguated[0]
        rock_work = disambiguated[1]

        # 1. Distinct Asset IDs
        assert folk_work.asset_id != rock_work.asset_id
        assert "folk_artist_a" in folk_work.asset_id
        assert "rock_band_b" in rock_work.asset_id

        # 2. Distinct Occurrence and Claim IDs
        assert folk_work.occurrence.occurrence_id != rock_work.occurrence.occurrence_id
        assert folk_work.claim.claim_id != rock_work.claim.claim_id

        # 3. Distinct Targeted Queries
        assert folk_work.catalog_query != rock_work.catalog_query
        assert "Folk Artist A" in folk_work.catalog_query
        assert "Rock Band B" not in folk_work.catalog_query
        assert "Rock Band B" in rock_work.catalog_query
        assert "Folk Artist A" not in rock_work.catalog_query

    def test_zero_evidence_and_approval_leakage_between_disambiguated_entities(self):
        """Verifies evidence and counsel approvals never leak between identically titled works."""
        metadata = [
            {"artist": "Folk Artist A", "genre": "Folk", "scene": "Scene 04"},
            {"artist": "Rock Band B", "genre": "Rock", "scene": "Scene 28"},
        ]
        folk_work, rock_work = disambiguate_works(title="Hold On", entities_metadata=metadata)

        # Create distinct evidence snapshots
        evidence_folk = PublicEvidenceSnapshot(
            snapshot_id="ev_snap_folk_001",
            use_id=folk_work.claim.claim_id,
            stable_lineage_key=folk_work.claim.occurrence_lineage_id,
            query=folk_work.catalog_query,
            source_url="https://ascap.com/repertory/work/hold-on-folk-artist-a",
            source_title="ASCAP Repertory: Hold On (Folk Artist A)",
            excerpt="ISWC T-070.123.456-1: Folk Artist A sole composer. Controlled 100% by Folk Heritage Music.",
        )

        evidence_rock = PublicEvidenceSnapshot(
            snapshot_id="ev_snap_rock_002",
            use_id=rock_work.claim.claim_id,
            stable_lineage_key=rock_work.claim.occurrence_lineage_id,
            query=rock_work.catalog_query,
            source_url="https://bmi.com/repertoire/work/hold-on-rock-band-b",
            source_title="BMI Repertoire: Hold On (Rock Band B)",
            excerpt="ISWC T-070.987.654-9: Rock Band B. Co-publishing dispute pending in UK High Court.",
        )

        # Attach evidence to claims
        folk_work.claim.evidence_ids.append(evidence_folk.snapshot_id)
        rock_work.claim.evidence_ids.append(evidence_rock.snapshot_id)

        # Counsel approves Folk Artist A claim
        folk_work.claim.disposition = CensusDisposition.APPROVED
        folk_work.claim.decision_id = "dec_counsel_folk_approved"

        # Rock Band B claim remains NEEDS_REVIEW / REJECTED due to dispute
        rock_work.claim.disposition = CensusDisposition.NEEDS_REVIEW

        # Strict Assertions: Zero cross-contamination
        assert folk_work.claim.evidence_ids == ["ev_snap_folk_001"]
        assert rock_work.claim.evidence_ids == ["ev_snap_rock_002"]
        assert "ev_snap_folk_001" not in rock_work.claim.evidence_ids
        assert "ev_snap_rock_002" not in folk_work.claim.evidence_ids

        assert folk_work.claim.disposition == CensusDisposition.APPROVED
        assert rock_work.claim.disposition == CensusDisposition.NEEDS_REVIEW
        assert rock_work.claim.decision_id is None


# =============================================================================
# SCENARIO 3: TRAILER PROMOTIONAL RESTRICTION TRIGGER
# =============================================================================

class TestScenario3TrailerPromotionalRestrictionTrigger:
    """
    Test 3: Trailer Promotional Restriction Trigger:
    - Asset ("Vintage Gramophone Track") has an agreement covering feature film, but with an unfulfilled obligation:
      "No promotional or trailer use without separate license addendum".
    - Occurrence moves from feature to trailer -> ApplicabilityAssessment.promotional_match == ScopeMatchStatus.MISMATCH
      and overall_match == ScopeMatchStatus.MISMATCH.
    """

    def test_feature_film_context_satisfies_agreement(self):
        """When used strictly in feature film context, promotional restriction is not triggered."""
        agreement = ContractAgreement(
            agreement_id="agr_vintage_gramophone_sync",
            stable_lineage_key="occ_lin_vintage_gramophone",
            licensor="Historic Sound Archives Ltd.",
            licensee="Production Studio LLC",
            scope="Theatrical feature film and streaming distribution",
            term="10 Years",
            agreement_hash=hashlib.sha256(b"Vintage Gramophone Sync Agreement").hexdigest(),
        )

        grant = ContractGrant(
            grant_id="grant_gramophone_001",
            agreement_id=agreement.agreement_id,
            asset_id="work_vintage_gramophone",
            grantor="Historic Sound Archives Ltd.",
            grantee="Production Studio LLC",
            permitted_media=["theatrical", "streaming"],
            permitted_territories=["worldwide"],
            allows_promotional_trailers=False,
            source_clause="Section 1.1: Licensor grants synchronization rights in the feature film.",
        )

        obligation = ContractObligation(
            obligation_id="obl_promo_restriction_001",
            agreement_id=agreement.agreement_id,
            obligation_type="promotional_restriction",
            restriction_text="No promotional or trailer use without separate license addendum",
            source_clause="Section 4.2: No promotional or trailer use without separate license addendum.",
            is_fulfilled=False,
        )

        # Claim placed in feature film
        claim_feature = AtomicRightsClaim(
            claim_id="clm_vintage_gramophone_feature",
            occurrence_id="occ_vintage_gramophone_001",
            occurrence_lineage_id="occ_lin_vintage_gramophone",
            asset_id="work_vintage_gramophone",
            right_category="synchronization",
            rights_subject="Historic Sound Archives Ltd.",
            intended_territory=["worldwide"],
            intended_media=["theatrical", "streaming"],
            intended_context="feature",
            disposition=CensusDisposition.APPROVED,
        )

        assessment = assess_contract_applicability(
            claim=claim_feature,
            agreement=agreement,
            grants=[grant],
            obligations=[obligation],
        )

        assert assessment.media_match == ScopeMatchStatus.MATCH
        assert assessment.territory_match == ScopeMatchStatus.MATCH
        assert assessment.term_match == ScopeMatchStatus.MATCH
        assert assessment.promotional_match == ScopeMatchStatus.MATCH
        assert assessment.overall_match == ScopeMatchStatus.MATCH
        assert len(assessment.conflicting_clauses) == 0

    def test_occurrence_moves_to_trailer_triggers_mismatch(self):
        """
        When occurrence moves from feature to trailer:
        ApplicabilityAssessment.promotional_match == ScopeMatchStatus.MISMATCH and overall_match == ScopeMatchStatus.MISMATCH.
        """
        agreement = ContractAgreement(
            agreement_id="agr_vintage_gramophone_sync",
            stable_lineage_key="occ_lin_vintage_gramophone",
            licensor="Historic Sound Archives Ltd.",
            licensee="Production Studio LLC",
            scope="Theatrical feature film and streaming distribution",
            term="10 Years",
            agreement_hash=hashlib.sha256(b"Vintage Gramophone Sync Agreement").hexdigest(),
        )

        grant = ContractGrant(
            grant_id="grant_gramophone_001",
            agreement_id=agreement.agreement_id,
            asset_id="work_vintage_gramophone",
            grantor="Historic Sound Archives Ltd.",
            grantee="Production Studio LLC",
            permitted_media=["theatrical", "streaming"],
            permitted_territories=["worldwide"],
            allows_promotional_trailers=False,
            source_clause="Section 1.1: Licensor grants synchronization rights in the feature film.",
        )

        obligation = ContractObligation(
            obligation_id="obl_promo_restriction_001",
            agreement_id=agreement.agreement_id,
            obligation_type="promotional_restriction",
            restriction_text="No promotional or trailer use without separate license addendum",
            source_clause="Section 4.2: No promotional or trailer use without separate license addendum.",
            is_fulfilled=False,
        )

        # Occurrence moves to marketing trailer
        claim_trailer = AtomicRightsClaim(
            claim_id="clm_vintage_gramophone_trailer",
            occurrence_id="occ_vintage_gramophone_trailer_001",
            occurrence_lineage_id="occ_lin_vintage_gramophone",
            asset_id="work_vintage_gramophone",
            right_category="synchronization",
            rights_subject="Historic Sound Archives Ltd.",
            intended_territory=["worldwide"],
            intended_media=["theatrical", "trailer"],
            intended_context="trailer",
            disposition=CensusDisposition.UNKNOWN,
        )

        assessment = assess_contract_applicability(
            claim=claim_trailer,
            agreement=agreement,
            grants=[grant],
            obligations=[obligation],
        )

        # Exact required assertions
        assert assessment.promotional_match == ScopeMatchStatus.MISMATCH
        assert assessment.overall_match == ScopeMatchStatus.MISMATCH
        assert len(assessment.conflicting_clauses) > 0
        assert any(
            "No promotional or trailer use without separate license addendum" in clause
            for clause in assessment.conflicting_clauses
        )


# =============================================================================
# SCENARIO 4: DURABLE CLAIM-LEVEL PAUSE & DOCUMENT RESUMPTION
# =============================================================================

class TestScenario4DurableClaimLevelPauseAndDocumentResumption:
    """
    Test 4: Durable Claim-Level Pause & Document Resumption:
    - Claim A ("Lost Highway") lacks synchronization license -> suspended to WAITING_FOR_INFORMATION with ClarificationRequest.
    - Sibling Claim B ("City Lights") completes concurrently.
    - Simulated restart / state preservation.
    - Document arrives (resume_claim) -> freshness check passes -> Claim A resumes and completes.
    """

    def test_claim_level_pause_and_concurrent_sibling_completion(self):
        """Claim A pauses in WAITING_FOR_INFORMATION while sibling Claim B completes concurrently."""
        claim_a = AtomicRightsClaim(
            claim_id="clm_lost_highway",
            occurrence_id="occ_lost_highway_01",
            occurrence_lineage_id="occ_lin_lost_highway",
            asset_id="work_lost_highway",
            right_category="synchronization",
            rights_subject="Lost Highway Composer",
            disposition=CensusDisposition.UNKNOWN,
        )

        claim_b = AtomicRightsClaim(
            claim_id="clm_city_lights",
            occurrence_id="occ_city_lights_01",
            occurrence_lineage_id="occ_lin_city_lights",
            asset_id="work_city_lights",
            right_category="synchronization",
            rights_subject="City Lights Publisher",
            disposition=CensusDisposition.UNKNOWN,
        )

        # Claim A lacks synchronization license -> suspend with ClarificationRequest
        paused_a, clarification_a = pause_claim_investigation(
            claim=claim_a,
            revision_id="v8",
            question_text="Missing executed synchronization license for 'Lost Highway'.",
            required_document_type="Executed Synchronization License",
            assigned_role="Music Supervisor",
        )

        # Sibling Claim B continues concurrently and completes
        completed_b = claim_b.model_copy(
            update={
                "disposition": CensusDisposition.APPROVED,
                "workflow_reason": WorkflowReason.NORMAL_OPERATION,
                "licensor_grant_confirmed": True,
            }
        )

        # Assert Claim A is suspended with ClarificationRequest
        assert paused_a.disposition == CensusDisposition.NEEDS_REVIEW
        assert paused_a.workflow_reason == WorkflowReason.WAITING_FOR_INFORMATION
        assert paused_a.clarification_request_id == clarification_a.request_id
        assert clarification_a.status == "pending"
        assert clarification_a.required_document_type == "Executed Synchronization License"

        # Assert Sibling Claim B completed concurrently without being blocked
        assert completed_b.disposition == CensusDisposition.APPROVED
        assert completed_b.workflow_reason == WorkflowReason.NORMAL_OPERATION
        assert completed_b.clarification_request_id is None

    def test_durable_restart_and_freshness_verified_resumption(self):
        """Simulates server restart, verifies state persistence, and completes resumption on document arrival."""
        claim_a = AtomicRightsClaim(
            claim_id="clm_lost_highway",
            occurrence_id="occ_lost_highway_01",
            occurrence_lineage_id="occ_lin_lost_highway",
            asset_id="work_lost_highway",
            right_category="synchronization",
            rights_subject="Lost Highway Composer",
            disposition=CensusDisposition.UNKNOWN,
        )

        paused_a, clarification_a = pause_claim_investigation(
            claim=claim_a,
            revision_id="v8",
            question_text="Missing executed synchronization license for 'Lost Highway'.",
            required_document_type="Executed Synchronization License",
        )

        # 1. Simulated State Serialization & Container Restart
        serialized_state = json.dumps({
            "claim": paused_a.model_dump(),
            "clarification": clarification_a.model_dump(),
        })

        # Rehydrate state after simulated restart
        reloaded_payload = json.loads(serialized_state)
        restored_claim = AtomicRightsClaim.model_validate(reloaded_payload["claim"])
        restored_clarification = ClarificationRequest.model_validate(reloaded_payload["clarification"])

        assert restored_claim.workflow_reason == WorkflowReason.WAITING_FOR_INFORMATION
        assert restored_claim.clarification_request_id == restored_clarification.request_id
        assert restored_clarification.status == "pending"

        # 2. Document arrives
        doc_uri = "gs://studio-vault/executed_licenses/lost_highway_sync_2026.pdf"
        active_lineages = ["occ_lin_lost_highway", "occ_lin_city_lights"]

        resumed_claim, resolved_clarification, success = resume_claim_investigation(
            claim=restored_claim,
            clarification=restored_clarification,
            document_uri=doc_uri,
            active_lineage_keys=active_lineages,
        )

        # 3. Assertions on completed resumption
        assert success is True
        assert resolved_clarification.status == "RESOLVED"
        assert resolved_clarification.attached_document_ref == doc_uri
        assert resolved_clarification.resolved_at is not None

        assert resumed_claim.disposition == CensusDisposition.APPROVED
        assert resumed_claim.workflow_reason == WorkflowReason.NORMAL_OPERATION
        assert resumed_claim.licensor_grant_confirmed is True
        assert doc_uri in resumed_claim.notes

    def test_resumption_fails_if_asset_eliminated_in_new_revision(self):
        """Freshness check: If asset was cut from active revision, clarification is superseded and claim not cleared."""
        claim_a = AtomicRightsClaim(
            claim_id="clm_lost_highway",
            occurrence_id="occ_lost_highway_01",
            occurrence_lineage_id="occ_lin_lost_highway",
            right_category="synchronization",
            rights_subject="Lost Highway Composer",
        )
        paused_a, clarification_a = pause_claim_investigation(
            claim=claim_a,
            revision_id="v8",
            question_text="Need license",
            required_document_type="Sync License",
        )

        # Asset removed from latest cut (lineage key missing)
        active_lineages = ["occ_lin_other_track"]
        resumed_claim, resolved_clarification, success = resume_claim_investigation(
            claim=paused_a,
            clarification=clarification_a,
            document_uri="gs://vault/sync.pdf",
            active_lineage_keys=active_lineages,
        )

        assert success is False
        assert resolved_clarification.status == "SUPERSEDED"
        assert resumed_claim.disposition != CensusDisposition.APPROVED


# =============================================================================
# SCENARIO 5: COUNSEL REJECTION & CORRECTION LOOP
# =============================================================================

class TestScenario5CounselRejectionAndCorrectionLoop:
    """
    Test 5: Counsel Rejection & Correction Loop:
    - AI recommends approval for an asset.
    - Counsel rejects recommendation and issues a directive: "Requires UK territory sync clearance".
    - Verifies: Prior finding is archived; counsel directive is recorded; a new isolated InvestigationTask is dispatched with directive as constraint; claim resets to NEEDS_REVIEW.
    """

    def test_counsel_rejection_archives_prior_finding_and_dispatches_directive_task(self):
        """
        Verifies counsel rejection archives AI approval finding, records directive,
        dispatches new isolated InvestigationTask, and resets claim to NEEDS_REVIEW.
        """
        claim = AtomicRightsClaim(
            claim_id="clm_transatlantic_track",
            occurrence_id="occ_track_001",
            occurrence_lineage_id="occ_lin_transatlantic_track",
            asset_id="work_transatlantic_track",
            right_category="synchronization",
            rights_subject="Global Soundtracks LLP",
            intended_territory=["US", "UK", "EU"],
            disposition=CensusDisposition.APPROVED,  # Tentatively approved by AI
            workflow_reason=WorkflowReason.NORMAL_OPERATION,
        )

        prior_ai_task = InvestigationTask(
            task_id="task_ai_recommender_001",
            claim_ids=[claim.claim_id],
            task_type="search_public",
            status=TaskStatus.SUCCEEDED,
            target_provider="parallel",
            query_or_ref="Transatlantic Track worldwide rights",
            result_payload={
                "recommendation": "APPROVE",
                "confidence": 0.95,
                "territories_cleared": ["US"],
            },
        )

        counsel_reviewer = ReviewerIdentity(
            reviewer_id="counsel_lead_001",
            name="Sarah Jenkins, Esq.",
            title="Senior Clearance Counsel",
            organization="Lienmark Legal Partners LLP",
            is_fictional_demo=True,
        )

        directive = "Requires UK territory sync clearance"

        updated_claim, archived_task, new_task = counsel_reject_and_correct(
            claim=claim,
            prior_task=prior_ai_task,
            directive=directive,
            reviewer=counsel_reviewer,
        )

        # 1. Prior finding is archived
        assert archived_task.task_id == prior_ai_task.task_id
        assert archived_task.status == TaskStatus.CANCELLED
        assert directive in archived_task.error_details

        # 2. Counsel directive is recorded
        assert directive in updated_claim.notes
        assert updated_claim.workflow_reason == WorkflowReason.EVIDENCE_CHANGE

        # 3. New isolated InvestigationTask is dispatched with directive as constraint
        assert new_task.task_id != prior_ai_task.task_id
        assert new_task.status == TaskStatus.QUEUED
        assert new_task.query_or_ref == directive
        assert new_task.result_payload["constraint_directive"] == directive
        assert new_task.claim_ids == [claim.claim_id]

        # 4. Claim resets to NEEDS_REVIEW
        assert updated_claim.disposition == CensusDisposition.NEEDS_REVIEW


# =============================================================================
# SCENARIO 6: OPERATIONAL RECOVERY & HONEST PARTIAL INCOMPLETENESS
# =============================================================================

class TestScenario6OperationalRecoveryAndHonestPartialIncompleteness:
    """
    Test 6: Operational Recovery & Honest Partial Incompleteness:
    - Provider returns HTTP 504 timeout on unfamiliar asset.
    - Verifies: Does NOT manufacture false clearance or false green badge. Claim status is UNKNOWN with workflow_reason="PROVIDER_OFFLINE".
    """

    def test_http_504_timeout_sets_unknown_with_provider_offline_reason(self):
        """
        When external search times out (HTTP 504), system fails closed:
        Does NOT manufacture false clearance or false green badge.
        Claim status is UNKNOWN with workflow_reason="PROVIDER_OFFLINE".
        """
        claim = AtomicRightsClaim(
            claim_id="clm_obscure_folk_recording",
            occurrence_id="occ_obscure_folk_001",
            occurrence_lineage_id="occ_lin_obscure_folk",
            asset_id="work_obscure_folk",
            right_category="synchronization",
            rights_subject="Unregistered Artist",
            disposition=CensusDisposition.UNKNOWN,
            workflow_reason=WorkflowReason.NEWLY_DISCOVERED,
        )

        # External provider encounters HTTP 504 Gateway Timeout
        failed_claim = handle_provider_failure(
            claim=claim,
            http_status=504,
            error_message="Parallel Search HTTP 504 Gateway Timeout",
        )

        # 1. Does NOT manufacture false clearance or green badge
        assert failed_claim.disposition != CensusDisposition.APPROVED
        assert failed_claim.disposition != CensusDisposition.CONDITIONAL
        assert failed_claim.licensor_grant_confirmed is False

        # 2. Claim status is UNKNOWN
        assert failed_claim.disposition == CensusDisposition.UNKNOWN

        # 3. workflow_reason is "PROVIDER_OFFLINE" (or WorkflowReason.PROVIDER_OFFLINE)
        assert failed_claim.workflow_reason == WorkflowReason.PROVIDER_OFFLINE
        assert failed_claim.workflow_reason == "provider_offline"

        # 4. Notes preserve honest audit rationale
        assert "504" in failed_claim.notes
        assert "Gateway Timeout" in failed_claim.notes


# =============================================================================
# SCENARIO 7: RETENTION POLICY & LEGAL HOLD ENFORCEMENT
# =============================================================================

class TestScenario7RetentionPolicyAndLegalHoldEnforcement:
    """
    Test 7: Retention Policy & Legal Hold Enforcement:
    - Attempt to purge materials for a production with an active LegalHoldRecord -> blocked.
    - When hold is released and retention expires -> purge succeeds, deleted files marked SOURCE_PURGED_PER_POLICY, cryptographic hashes preserved.
    """

    def test_active_legal_hold_blocks_purge_attempt(self):
        """Attempt to purge materials for a production with active LegalHoldRecord is strictly blocked."""
        manager = RetentionAndLegalHoldManager()
        production_id = "prod_unfamiliar_litigation_01"

        # Place statutory legal hold
        hold = manager.place_hold(
            production_id=production_id,
            reason="Subpoena duces tecum re copyright litigation SDNY 2026-CV-4421",
            placed_by="Sarah Jenkins, Esq. (Lead Litigation Counsel)",
            claim_ids=["clm_disputed_poster_001"],
        )
        assert hold.is_active is True
        assert manager.has_active_hold(production_id) is True

        # Attempt to purge materials while hold is active
        target_uri = "gs://lienmark-vault-prod/cuts/v1_unreleased_cut.mov"
        file_bytes = b"Unreleased raw cut content under legal hold"
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # Must raise LegalHoldActiveError
        with pytest.raises(LegalHoldActiveError) as exc_info:
            manager.attempt_purge_material(
                target_uri=target_uri,
                production_id=production_id,
                retention_class=RetentionClass.INTAKE_COPIES,
                file_content_or_hash=content_hash,
                file_age_days=180,  # Exceeds 90-day intake policy
            )

        assert "active legal hold" in str(exc_info.value).lower()
        assert production_id in str(exc_info.value)

    def test_purge_succeeds_when_hold_released_and_retention_expires(self):
        """
        When legal hold is released and retention expires:
        Purge succeeds, deleted files marked SOURCE_PURGED_PER_POLICY, cryptographic hashes preserved.
        """
        manager = RetentionAndLegalHoldManager()
        production_id = "prod_unfamiliar_litigation_01"

        hold = manager.place_hold(
            production_id=production_id,
            reason="Preliminary hold",
            placed_by="Clearance Counsel",
        )

        target_uri = "gs://lienmark-vault-prod/cuts/v1_unreleased_cut.mov"
        file_bytes = b"Unreleased raw cut content under legal hold"
        original_hash = hashlib.sha256(file_bytes).hexdigest()

        # Release the legal hold
        released_hold = manager.release_hold(hold.hold_id)
        assert released_hold.is_active is False
        assert manager.has_active_hold(production_id) is False
        assert released_hold.released_at is not None

        # Purge succeeds after hold release and retention expiration (age 100d >= 90d policy)
        deletion_record = manager.attempt_purge_material(
            target_uri=target_uri,
            production_id=production_id,
            retention_class=RetentionClass.INTAKE_COPIES,
            file_content_or_hash=original_hash,
            file_age_days=100,
        )

        # 1. Deletion record created
        assert isinstance(deletion_record, DeletionRecord)
        assert deletion_record.target_uri == target_uri
        assert deletion_record.retention_class == RetentionClass.INTAKE_COPIES

        # 2. Deleted files marked SOURCE_PURGED_PER_POLICY
        assert deletion_record.availability_status == EvidenceAvailability.SOURCE_PURGED_PER_POLICY
        assert deletion_record.availability_status.value == "source_purged_per_policy"

        # 3. Cryptographic hash preserved for audit defense
        assert deletion_record.original_sha256 == original_hash
        assert len(deletion_record.original_sha256) == 64
        assert deletion_record.purged_at is not None

    def test_unexpired_retention_prevents_premature_deletion(self):
        """Files younger than retention policy schedule cannot be purged even without legal hold."""
        manager = RetentionAndLegalHoldManager()
        production_id = "prod_clean_001"

        with pytest.raises(ValueError) as exc_info:
            manager.attempt_purge_material(
                target_uri="gs://vault/fresh_upload.mov",
                production_id=production_id,
                retention_class=RetentionClass.INTAKE_COPIES,
                file_content_or_hash="a" * 64,
                file_age_days=15,  # 15 days < 90 days required
            )
        assert "not expired" in str(exc_info.value).lower()
