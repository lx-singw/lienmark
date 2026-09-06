"""
Test suite for Counsel Rejection, Correction Loop & Retention Policy Enforcement
Tests:
1. Counsel Rejection & Correction Loop:
   - ReviewAction.RE_ATTEST (or APPROVE): sets claim disposition to APPROVED / CONDITIONAL with conditions.
   - ReviewAction.REJECT (or REJECT_USE): archives previous recommendation, updates claim disposition to REJECTED.
   - ReviewAction.REQUEST_CORRECTION:
     * Archives the prior finding/recommendation with timestamp and counsel name.
     * Preserves counsel's directive (e.g., "Must obtain festival sync addendum" or "Investigate master recording rights in UK territory").
     * Spawns an isolated InvestigationTask with counsel's directive as an explicit search/investigation constraint.
     * Transitions claim status to CensusDisposition.NEEDS_REVIEW and workflow_reason to REINVESTIGATION_REQUESTED.
2. Retention Policy & Legal Hold Enforcement:
   - purge_expired_materials:
     * If an active legal hold covers the production or asset: BLOCKS purge, logs caution, sets status="BLOCKED_BY_LEGAL_HOLD".
     * If no legal hold covers the asset and retention period has elapsed: marks files as deleted, records SHA-256 digest, sets evidence_availability=EvidenceAvailability.SOURCE_PURGED_PER_POLICY while preserving cryptographic event hash and metadata.
"""

from datetime import datetime, timezone, timedelta
import pytest

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    ApprovalOrigin,
    WorkflowReason,
    ReviewAction,
    InvestigationTask,
    TaskStatus,
    RetentionPolicy,
    LegalHoldRecord,
    DeletionRecord,
    RetentionClass,
    EvidenceAvailability,
    CounselDecisionResult,
)
from backend.core.invalidation_engine import (
    InvalidationEngine,
    process_counsel_decision as core_process_counsel_decision,
    purge_expired_materials as core_purge_expired_materials,
)
from backend.orchestration.adk_pipeline import (
    ADKClearancePipeline,
    process_counsel_decision as orch_process_counsel_decision,
    purge_expired_materials as orch_purge_expired_materials,
)


# =============================================================================
# 1. COUNSEL DECISION: RE_ATTEST / APPROVE
# =============================================================================

class TestCounselReAttestAndApprove:
    """Tests ReviewAction.RE_ATTEST and APPROVE behavior."""

    def test_reattest_unconditional_sets_approved(self):
        claim = AtomicRightsClaim(
            claim_id="claim_music_001",
            occurrence_id="occ_001",
            occurrence_lineage_id="lin_001",
            right_category="composition",
            rights_subject="Music Publisher",
            disposition=CensusDisposition.NEEDS_REVIEW,
        )

        result = InvalidationEngine.process_counsel_decision(
            claim=claim,
            action=ReviewAction.RE_ATTEST,
            counsel_name="Sarah Jenkins, Esq.",
        )

        assert isinstance(result, CounselDecisionResult)
        assert claim.disposition == CensusDisposition.APPROVED
        assert result.disposition == CensusDisposition.APPROVED
        assert claim.decision_conditions == []
        assert claim.approval_origin == ApprovalOrigin.RENEWED_APPROVAL
        assert claim.workflow_reason == WorkflowReason.NORMAL_OPERATION
        assert result.task is None

    def test_reattest_conditional_sets_conditional_with_conditions(self):
        claim = AtomicRightsClaim(
            claim_id="claim_music_002",
            occurrence_id="occ_002",
            occurrence_lineage_id="lin_002",
            right_category="master_recording",
            rights_subject="Record Label",
            disposition=CensusDisposition.UNKNOWN,
        )
        conditions = ["Theatrical release only", "Must not exceed 45 seconds"]

        result = orch_process_counsel_decision(
            claim=claim,
            action=ReviewAction.RE_ATTEST,
            conditions=conditions,
            counsel_name="Sarah Jenkins, Esq.",
        )

        assert claim.disposition == CensusDisposition.CONDITIONAL
        assert result.disposition == CensusDisposition.CONDITIONAL
        assert claim.decision_conditions == conditions
        assert result.conditions == conditions
        assert claim.approval_origin == ApprovalOrigin.RENEWED_APPROVAL
        assert result.task is None

    def test_approve_string_alias(self):
        claim_dict = {
            "claim_id": "claim_photo_001",
            "occurrence_id": "occ_photo",
            "occurrence_lineage_id": "lin_photo",
            "right_category": "copyright",
            "rights_subject": "Photographer",
            "disposition": CensusDisposition.NEEDS_REVIEW,
        }

        result = ADKClearancePipeline.process_counsel_decision(
            claim=claim_dict,
            action="approve",
        )

        assert claim_dict["disposition"] == CensusDisposition.APPROVED
        assert result.disposition == CensusDisposition.APPROVED
        assert claim_dict["decision_conditions"] == []


# =============================================================================
# 2. COUNSEL DECISION: REJECT / REJECT_USE
# =============================================================================

class TestCounselReject:
    """Tests ReviewAction.REJECT and REJECT_USE behavior."""

    def test_reject_archives_recommendation_and_sets_rejected(self):
        claim = AtomicRightsClaim(
            claim_id="claim_artwork_001",
            occurrence_id="occ_art",
            occurrence_lineage_id="lin_art",
            right_category="trademark",
            rights_subject="Brand Owner",
            disposition=CensusDisposition.APPROVED,
            notes="Previously cleared under fair use doctrine.",
        )

        result = core_process_counsel_decision(
            claim=claim,
            action=ReviewAction.REJECT,
            counsel_name="Marcus Vance, Esq.",
            prior_finding="Initial clearance under fair use",
            notes="Fair use doctrine untenable following script rewrite into commercial context.",
        )

        assert claim.disposition == CensusDisposition.REJECTED
        assert result.disposition == CensusDisposition.REJECTED
        assert claim.decision_conditions == []
        assert claim.approval_origin == ApprovalOrigin.NONE
        assert claim.workflow_reason == WorkflowReason.NORMAL_OPERATION
        assert result.task is None

        # Verify archived recommendation
        assert len(claim.archived_recommendations) == 1
        archive = claim.archived_recommendations[0]
        assert archive["action"] == "reject"
        assert archive["counsel_name"] == "Marcus Vance, Esq."
        assert archive["prior_finding"] == "Initial clearance under fair use"
        assert "timestamp" in archive
        assert result.archived_record == archive

    def test_reject_use_string_alias_on_dict(self):
        claim_dict = {
            "claim_id": "claim_sample_001",
            "disposition": CensusDisposition.CONDITIONAL,
            "decision_conditions": ["Limited promo"],
            "notes": "Tentative promo approval",
        }

        result = orch_process_counsel_decision(
            claim=claim_dict,
            action="reject_use",
            counsel_name="Sarah Jenkins, Esq.",
        )

        assert claim_dict["disposition"] == CensusDisposition.REJECTED
        assert claim_dict["decision_conditions"] == []
        assert len(claim_dict["archived_recommendations"]) == 1
        assert claim_dict["archived_recommendations"][0]["action"] == "reject"


# =============================================================================
# 3. COUNSEL DECISION: REQUEST_CORRECTION
# =============================================================================

class TestCounselRequestCorrection:
    """Tests ReviewAction.REQUEST_CORRECTION directive and reinvestigation loop."""

    def test_request_correction_sync_addendum(self):
        claim = AtomicRightsClaim(
            claim_id="claim_cues_003",
            occurrence_id="occ_cues",
            occurrence_lineage_id="lin_cues",
            right_category="composition",
            rights_subject="Publisher International",
            disposition=CensusDisposition.APPROVED,
            notes="Original worldwide theatrical clearance.",
        )
        directive = "Must obtain festival sync addendum"

        result = InvalidationEngine.process_counsel_decision(
            claim=claim,
            action=ReviewAction.REQUEST_CORRECTION,
            counsel_directive=directive,
            counsel_name="Sarah Jenkins, Esq.",
            prior_finding="Worldwide theatrical clearance on file",
        )

        # 1. Archives prior finding with timestamp and counsel name
        assert len(claim.archived_recommendations) == 1
        archive = claim.archived_recommendations[0]
        assert archive["action"] == "request_correction"
        assert archive["counsel_name"] == "Sarah Jenkins, Esq."
        assert archive["prior_finding"] == "Worldwide theatrical clearance on file"
        assert archive["counsel_directive"] == directive
        assert "timestamp" in archive

        # 2. Preserves counsel directive
        assert claim.counsel_directive == directive
        assert directive in claim.notes
        assert claim.metadata["counsel_directive"] == directive

        # 3. Spawns an isolated InvestigationTask with counsel directive as constraint
        assert result.task is not None
        task = result.task
        assert isinstance(task, InvestigationTask)
        assert task.claim_ids == [claim.claim_id]
        assert task.counsel_directive == directive
        assert task.investigation_constraints == [directive]
        assert task.status == TaskStatus.QUEUED
        assert claim.clarification_request_id == task.task_id

        # 4. Transitions claim status to CensusDisposition.NEEDS_REVIEW and workflow_reason to REINVESTIGATION_REQUESTED
        assert claim.disposition == CensusDisposition.NEEDS_REVIEW
        assert claim.workflow_reason == WorkflowReason.REINVESTIGATION_REQUESTED
        assert result.disposition == CensusDisposition.NEEDS_REVIEW
        assert result.workflow_reason == WorkflowReason.REINVESTIGATION_REQUESTED

    def test_request_correction_uk_territory_directive(self):
        claim = AtomicRightsClaim(
            claim_id="claim_master_uk",
            occurrence_id="occ_uk",
            occurrence_lineage_id="lin_uk",
            right_category="master_recording",
            rights_subject="Decca Records",
            disposition=CensusDisposition.UNKNOWN,
        )
        directive = "Investigate master recording rights in UK territory"

        result = ADKClearancePipeline.process_counsel_decision(
            claim=claim,
            action=ReviewAction.REQUEST_CORRECTION,
            counsel_directive=directive,
            counsel_name="Marcus Vance, Esq.",
        )

        assert claim.counsel_directive == directive
        assert claim.disposition == CensusDisposition.NEEDS_REVIEW
        assert claim.workflow_reason == WorkflowReason.REINVESTIGATION_REQUESTED
        assert result.task.investigation_constraints == [directive]
        assert result.task.query_or_ref == directive

    def test_tuple_unpacking_support(self):
        claim = AtomicRightsClaim(
            claim_id="claim_unpack_test",
            occurrence_id="occ_u",
            occurrence_lineage_id="lin_u",
            right_category="trademark",
            rights_subject="Studio Corp",
        )
        updated_claim, task = orch_process_counsel_decision(
            claim=claim,
            action=ReviewAction.REQUEST_CORRECTION,
            counsel_directive="Verify trademark registry",
        )
        assert updated_claim.disposition == CensusDisposition.NEEDS_REVIEW
        assert isinstance(task, InvestigationTask)


# =============================================================================
# 4. RETENTION POLICY & LEGAL HOLD ENFORCEMENT
# =============================================================================

class TestRetentionPolicyAndLegalHolds:
    """Tests purge_expired_materials and legal hold blocking."""

    @pytest.fixture
    def policy(self):
        return RetentionPolicy(
            policy_id="policy_studio_2026",
            org_id="studio_universal",
            retention_days_by_class={
                RetentionClass.INTAKE_COPIES.value: 30,
                RetentionClass.RETAINED_EVIDENCE.value: 90,
                RetentionClass.EXTRACTED_PASSAGES.value: 365,
                RetentionClass.EMBEDDINGS.value: 15,
                RetentionClass.AUDIT_METADATA.value: 3650,
            },
        )

    def test_active_legal_hold_blocks_purge_and_sets_status(self, policy):
        """Active legal hold covers production -> BLOCKS purge, logs caution, sets status='BLOCKED_BY_LEGAL_HOLD'."""
        hold = LegalHoldRecord(
            hold_id="hold_litigation_001",
            production_id="prod_project_titan",
            claim_ids=["claim_001", "claim_002"],
            reason="Pending copyright litigation in SDNY",
            placed_by="Arthur Miller, Lead Litigation Counsel",
            is_active=True,
        )

        expired_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
        files = [
            {
                "uri": "s3://clearance-vault/titan/evidence_001.pdf",
                "production_id": "prod_project_titan",
                "claim_id": "claim_001",
                "created_at": expired_date,
                "retention_class": RetentionClass.RETAINED_EVIDENCE,
                "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "event_hash": "event_hash_111",
                "metadata": {"title": "Evidence document"},
            }
        ]

        record = InvalidationEngine.purge_expired_materials(
            retention_policy=policy,
            legal_holds=[hold],
            files=files,
        )

        assert isinstance(record, DeletionRecord)
        assert record.status == "BLOCKED_BY_LEGAL_HOLD"
        assert record.purged_at is None
        assert record.blocked_by_hold_id == hold.hold_id
        # Files MUST NOT be marked as deleted
        assert files[0].get("deleted") is False

    def test_active_legal_hold_on_asset_blocks_purge(self, policy):
        """Active legal hold covering specific asset_id blocks purge even if production_id differs."""
        hold = LegalHoldRecord(
            hold_id="hold_asset_999",
            production_id="prod_other",
            claim_ids=["asset_target_cue"],
            reason="Subpoena received for audio masters",
            placed_by="Rachel Green, Compliance Officer",
            is_active=True,
        )

        expired_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        files = [
            {
                "uri": "s3://clearance-vault/titan/audio_cue.wav",
                "production_id": "prod_project_titan",
                "asset_id": "asset_target_cue",
                "created_at": expired_date,
                "retention_class": RetentionClass.RETAINED_EVIDENCE,
                "sha256": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            }
        ]

        record = orch_purge_expired_materials(
            retention_policy=policy,
            legal_holds=[hold],
            files=files,
        )

        assert record.status == "BLOCKED_BY_LEGAL_HOLD"
        assert files[0].get("deleted") is False

    def test_released_legal_hold_does_not_block_purge(self, policy):
        """Released legal hold (released_at is set or is_active=False) allows expired materials purge."""
        hold = LegalHoldRecord(
            hold_id="hold_old_001",
            production_id="prod_project_titan",
            reason="Settled litigation",
            placed_by="Arthur Miller",
            is_active=False,
            released_at=datetime.now(timezone.utc).isoformat(),
        )

        expired_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
        files = [
            {
                "uri": "s3://clearance-vault/titan/intake_script.pdf",
                "production_id": "prod_project_titan",
                "created_at": expired_date,
                "retention_class": RetentionClass.INTAKE_COPIES,  # retention is 30 days
                "sha256": "5555555555555555555555555555555555555555555555555555555555555555",
                "event_hash": "cryptographic_hash_original",
                "metadata": {"source": "screenplay_intake"},
            }
        ]

        record = core_purge_expired_materials(
            retention_policy=policy,
            legal_holds=[hold],
            files=files,
        )

        assert record.status == "PURGED"
        assert record.evidence_availability == EvidenceAvailability.SOURCE_PURGED_PER_POLICY
        assert record.purged_at is not None
        assert files[0]["deleted"] is True
        assert files[0]["evidence_availability"] == EvidenceAvailability.SOURCE_PURGED_PER_POLICY
        # Cryptographic event hash and metadata preserved
        assert files[0]["event_hash"] == "cryptographic_hash_original"
        assert files[0]["metadata"]["source"] == "screenplay_intake"
        assert files[0]["metadata"]["preserved_original_sha256"] == "5555555555555555555555555555555555555555555555555555555555555555"

    def test_no_legal_hold_unexpired_files_remain_active(self, policy):
        """When retention period has NOT elapsed, files remain active and are not deleted."""
        recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        files = [
            {
                "uri": "s3://clearance-vault/titan/recent_evidence.pdf",
                "created_at": recent_date,
                "retention_class": RetentionClass.RETAINED_EVIDENCE,  # 90 days retention
                "sha256": "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
            }
        ]

        record = ADKClearancePipeline.purge_expired_materials(
            retention_policy=policy,
            legal_holds=[],
            files=files,
        )

        assert record.status == "ACTIVE_RETENTION"
        assert record.purged_at is None
        assert files[0].get("deleted") is not True
