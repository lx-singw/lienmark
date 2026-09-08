"""
tests/test_document_matcher_sufficiency.py

Tests for DocumentMatcherService and scoring enhancements:
1. Disentangling candidate association from agreement sufficiency (missing license scopes).
2. Multiple qualifying candidates (> 1 match) flags ambiguity for counsel without guessing.
3. Ambiguous terms detection (TBD, conflicting territory grants, placeholder licensors).
4. Auto-resolve upon complete sufficiency and unambiguous terms.
5. Invariant: Document arrival resumes verification but NEVER sets disposition = APPROVED.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest
from typing import List

from backend.domain.models import CensusDisposition, ClarificationRequest
from backend.services.document_matcher import DocumentMatcherService
from backend.services.document_matcher_scoring import (
    is_agreement_ambiguous,
    verify_agreement_sufficiency,
)
from backend.services.document_matcher_types import (
    AgreementParties,
    DocumentArrivalEvent,
    ExtractedAgreementMetadata,
    MatchingDecision,
    MatchScoreBreakdown,
)
from backend.storage.clarification_store import ClarificationStore


def _build_metadata(
    asset_title: str = "Autumn Shadows",
    agreement_type: str = "Sync License",
    licensor: str = "Blue Note Records",
    territory: List[str] = None,
    media: List[str] = None,
    term: str = "in perpetuity",
    confidence: float = 0.95,
    file_hash: str = "hash_doc_001",
) -> ExtractedAgreementMetadata:
    return ExtractedAgreementMetadata(
        document_id="doc_sync_001",
        file_hash=file_hash,
        parties=AgreementParties(licensor=licensor, licensee="Paramount Pictures"),
        asset_title=asset_title,
        agreement_type=agreement_type,
        execution_date="2026-05-15",
        grant_territory=territory if territory is not None else ["Worldwide"],
        grant_media=media if media is not None else ["All Media"],
        grant_term=term,
        extraction_confidence=confidence,
    )


def test_sufficiency_check_missing_territory_scope_fails() -> None:
    """Disentangled check: Candidate score high, but missing requested territorial scope fails sufficiency."""
    meta = _build_metadata(territory=[])  # Missing territory grant
    clrf = ClarificationRequest(
        request_id="clrf_missing_terr", claim_id="clm_01",
        stable_lineage_key="lin_01",
        question_text="Autumn Shadows sync license needed with territorial grant.",
        required_document_type="Executed Synchronization License",
        scope_field_missing="territory",
        tenant_id="tenant_paramount", production_id="prod_noir",
    )
    event = DocumentArrivalEvent(file_path="dummy.pdf", tenant_id="tenant_paramount", file_hash="h1", production_id="prod_noir")
    bdown = MatchScoreBreakdown(asset_score=0.96, parties_score=0.85, agreement_type_score=1.0, composite_score=0.92)

    ok, reason = verify_agreement_sufficiency(meta, clrf, event, bdown)
    assert ok is False
    assert "Missing required territorial grant" in (reason or "")


def test_ambiguity_detection_flags_tbd_and_conflicting_territory() -> None:
    """Ambiguity check flags placeholder terms, low confidence, and conflicting scopes."""
    clrf = ClarificationRequest(request_id="clrf_tbd", claim_id="clm_02", stable_lineage_key="lin_02", question_text="Autumn Shadows cue.", tenant_id="tenant_p")
    meta_tbd = _build_metadata(term="pending TBD negotiations")
    ambig1, rsn1 = is_agreement_ambiguous(meta_tbd, clrf)
    assert ambig1 is True
    assert "tbd" in (rsn1 or "").lower()

    meta_conflict = _build_metadata(territory=["Worldwide", "excluding North America"])
    ambig2, rsn2 = is_agreement_ambiguous(meta_conflict, clrf)
    assert ambig2 is True
    assert "conflicting worldwide grant" in (rsn2 or "").lower()

    meta_unk = _build_metadata(licensor="Unknown Licensor")
    ambig3, rsn3 = is_agreement_ambiguous(meta_unk, clrf)
    assert ambig3 is True
    assert "Unidentified or placeholder licensor" in (rsn3 or "")


def test_multiple_qualifying_candidates_flags_ambiguity_for_counsel() -> None:
    """When multiple open clarifications match (> 0.85), flag ambiguity rather than guessing."""
    store = ClarificationStore()
    matcher = DocumentMatcherService(clarification_store=store)
    clrf1 = ClarificationRequest(
        request_id="clrf_multi_1", claim_id="clm_scene1",
        stable_lineage_key="lin_multi_1",
        question_text="Autumn Shadows cue composition in opening diner scene.",
        required_document_type="Sync License",
        tenant_id="tenant_paramount", production_id="prod_multi", status="pending",
    )
    clrf2 = ClarificationRequest(
        request_id="clrf_multi_2", claim_id="clm_scene2",
        stable_lineage_key="lin_multi_2",
        question_text="Autumn Shadows cue reprise in closing alley scene.",
        required_document_type="Sync License",
        tenant_id="tenant_paramount", production_id="prod_multi", status="pending",
    )
    store.save_clarification(clrf1, tenant_id="tenant_paramount", production_id="prod_multi")
    store.save_clarification(clrf2, tenant_id="tenant_paramount", production_id="prod_multi")

    event = DocumentArrivalEvent(
        file_path="gs://lienmark/agreements/autumn_shadows_sync.pdf",
        tenant_id="tenant_paramount", file_hash="hash_multi", production_id="prod_multi",
    )
    doc_text = "SYNCHRONIZATION LICENSE\nAsset Title: Autumn Shadows\nLicensor: Blue Note Records\nLicensee: Paramount\n"
    res = matcher.on_document_arrival(event, file_content=doc_text)

    # Invariant: Multiple candidates detected -> flags ambiguity for counsel
    assert res.decision == MatchingDecision.CANDIDATE_DETECTED
    assert res.pipeline_resumed is False
    c1 = store.get_clarification("clrf_multi_1", "tenant_paramount")
    c2 = store.get_clarification("clrf_multi_2", "tenant_paramount")
    assert c1.status == "candidate_document_detected"
    assert c2.status == "candidate_document_detected"


def test_critical_invariant_document_arrival_never_sets_approved_disposition() -> None:
    """CRITICAL INVARIANT: Document arrival must NEVER set disposition = APPROVED."""
    from backend.domain.models import AtomicRightsClaim
    from backend.services.agreement_verifier import AgreementVerifier
    from backend.services.agreement_verifier_types import (
        AgreementDocumentInput,
        ProductionRequirements,
        RightType,
        SignatureParty,
    )

    store = ClarificationStore()
    matcher = DocumentMatcherService(clarification_store=store)

    clrf = ClarificationRequest(
        request_id="clrf_inv_01", claim_id="clm_inv_01",
        stable_lineage_key="lin_inv_01",
        question_text="Autumn Shadows sync license.",
        required_document_type="Sync License",
        tenant_id="tenant_paramount", production_id="prod_inv", status="pending",
    )
    store.save_clarification(clrf, tenant_id="tenant_paramount", production_id="prod_inv")

    event = DocumentArrivalEvent(
        file_path="gs://lienmark/agreements/sync.pdf",
        tenant_id="tenant_paramount", file_hash="hash_inv", production_id="prod_inv",
    )
    doc_text = (
        "SYNCHRONIZATION LICENSE AGREEMENT\n"
        "Asset Title: Autumn Shadows\n"
        "Licensor: Blue Note Records\n"
        "Licensee: Paramount Pictures\n"
        "Grant Territory: Worldwide\n"
        "Grant Media: All Media\n"
        "Grant Term: Perpetual\n"
    )

    match_result = matcher.on_document_arrival(event, file_content=doc_text)
    assert match_result.decision == MatchingDecision.AUTO_RESOLVE

    verifier = AgreementVerifier()
    claim = AtomicRightsClaim(
        claim_id="clm_inv_01", occurrence_id="occ_01", occurrence_lineage_id="lin_inv_01",
        right_category="music", rights_subject="Autumn Shadows",
    )
    doc_in = AgreementDocumentInput(
        agreement_id="agr_inv_01", document_name="sync.pdf", licensor="Blue Note Records",
        licensee="Paramount Pictures", territories=["Worldwide"], media=["All Media"],
        term="Perpetual", granted_rights=["Synchronization"],
        signatures=[SignatureParty(party_name="Blue Note Records", party_role="licensor", is_signed=True),
                    SignatureParty(party_name="Paramount Pictures", party_role="licensee", is_signed=True)],
        raw_text=doc_text,
    )
    v_res = verifier.verify_agreement(
        doc=doc_in,
        requirements=ProductionRequirements(required_territory="worldwide", required_rights=[RightType.SYNCHRONIZATION]),
        claim=claim,
    )
    assert v_res.is_valid is True

    # Invariant: Document arrival unblocks verification but disposition remains NEEDS_REVIEW
    updated_claim = verifier.update_claim_state(claim, v_res, counsel_signoff=False)
    assert updated_claim.licensor_grant_confirmed is True
    assert updated_claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert updated_claim.disposition != CensusDisposition.APPROVED

    # Only explicit counsel sign-off transitions to APPROVED
    approved_claim = verifier.update_claim_state(claim, v_res, counsel_signoff=True)
    assert approved_claim.disposition == CensusDisposition.APPROVED
