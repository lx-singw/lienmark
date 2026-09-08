"""
tests/test_agreement_verifier.py

Sprint 4.2 Comprehensive Acceptance Gate:
Tests Post-Resumption Contract Verification, grant scope analysis, execution checks,
compliance scoring, claim state updates, and cryptographic ledger integration.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import pytest

from backend.domain.models import (
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
)
from backend.services.agreement_verifier import AgreementVerifier
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput,
    AgreementVerificationResult,
    MediaScope,
    ProductionRequirements,
    RightType,
    SignatureParty,
    TermScope,
    TerritoryScope,
    VerificationStatus,
)
from backend.storage.ledger import CryptographicLedger


@pytest.fixture
def ledger() -> CryptographicLedger:
    led = CryptographicLedger()
    led.initialize_production_ledger(
        tenant_id="org_cinema",
        production_id="prod_matrix",
        actor_id="usr_admin",
    )
    return led


@pytest.fixture
def verifier(ledger: CryptographicLedger) -> AgreementVerifier:
    return AgreementVerifier(ledger=ledger)


def _create_sample_doc(
    territories: list[str] | None = None,
    media: list[str] | None = None,
    term: str = "In perpetuity",
    granted_rights: list[str] | None = None,
    licensor_signed: bool = True,
    licensee_signed: bool = True,
    execution_date: str = "2026-02-15",
    raw_text: str | None = None,
) -> AgreementDocumentInput:
    signatures = []
    if licensor_signed:
        signatures.append(SignatureParty(
            party_name="Warner Chappell Music",
            party_role="licensor",
            is_signed=True,
            signed_date=execution_date,
        ))
    if licensee_signed:
        signatures.append(SignatureParty(
            party_name="Matrix Productions LLC",
            party_role="licensee",
            is_signed=True,
            signed_date=execution_date,
        ))

    default_raw = "Licensor grants Licensee the irrevocable, perpetual right throughout the universe in all media now known or hereafter devised to synchronize the musical composition."
    return AgreementDocumentInput(
        agreement_id="agr_sync_101",
        document_name="Synchronization License Agreement - Matrix",
        licensor="Warner Chappell Music",
        licensee="Matrix Productions LLC",
        execution_date=execution_date,
        territories=territories or ["Worldwide"],
        media=media or ["All media now known or hereafter devised"],
        term=term,
        granted_rights=granted_rights or ["Synchronization rights", "Master recording rights"],
        signatures=signatures,
        raw_text=raw_text or default_raw,
    )


def test_valid_perpetual_worldwide_sync_license(verifier: AgreementVerifier) -> None:
    doc = _create_sample_doc()
    req = ProductionRequirements(
        required_territory="worldwide",
        distribution_window_start="2026-11-01",
        required_rights=[RightType.SYNCHRONIZATION],
    )
    res = verifier.verify_agreement(doc=doc, requirements=req)

    assert res.is_valid is True
    assert res.status == VerificationStatus.VERIFIED_COMPLIANT
    assert res.compliance_score >= 0.95
    assert res.requires_counsel_rider is False
    assert res.grant_scope.is_worldwide is True
    assert res.grant_scope.has_all_media_devised is True
    assert res.grant_scope.is_perpetual is True
    assert len(res.verified_citations) >= 3


def test_unexecuted_missing_licensor_signature(verifier: AgreementVerifier) -> None:
    doc = _create_sample_doc(licensor_signed=False)
    req = ProductionRequirements(required_rights=[RightType.SYNCHRONIZATION])
    res = verifier.verify_agreement(doc=doc, requirements=req)

    assert res.is_valid is False
    assert res.status == VerificationStatus.REJECTED
    assert res.execution_validity.licensor_signed is False
    assert any("Missing licensor" in d for d in res.missing_clauses)


def test_restricted_territory_requires_counsel_rider(verifier: AgreementVerifier) -> None:
    doc = _create_sample_doc(
        territories=["North America", "United States", "Canada"],
        raw_text="Territory strictly restricted to North America only.",
    )
    req = ProductionRequirements(
        required_territory="worldwide",
        required_rights=[RightType.SYNCHRONIZATION],
    )
    res = verifier.verify_agreement(doc=doc, requirements=req)

    assert res.is_valid is True
    assert res.requires_counsel_rider is True
    assert res.status == VerificationStatus.CONDITIONALLY_COMPLIANT
    assert res.grant_scope.territory_scope == TerritoryScope.NORTH_AMERICA
    assert any("Territory restricted" in r for r in res.rider_reasons)


def test_fixed_in_license_term_requires_counsel_rider(verifier: AgreementVerifier) -> None:
    doc = _create_sample_doc(
        term="5 years from initial theatrical release",
        raw_text="The term shall be for a period of five (5) years only.",
    )
    req = ProductionRequirements(
        requires_perpetual=True,
        required_rights=[RightType.SYNCHRONIZATION],
    )
    res = verifier.verify_agreement(doc=doc, requirements=req)

    assert res.is_valid is True
    assert res.requires_counsel_rider is True
    assert res.grant_scope.term_scope == TermScope.IN_LICENSE_TERM
    assert any("term limitation" in r for r in res.rider_reasons)


def test_date_postdating_distribution_window(verifier: AgreementVerifier) -> None:
    doc = _create_sample_doc(execution_date="2027-01-10")
    req = ProductionRequirements(
        distribution_window_start="2026-08-01",
        required_rights=[RightType.SYNCHRONIZATION],
    )
    res = verifier.verify_agreement(doc=doc, requirements=req)

    assert res.execution_validity.is_date_within_window is False
    assert any("postdates distribution start" in d for d in res.missing_clauses)


def test_claim_update_and_ledger_recording(
    verifier: AgreementVerifier,
    ledger: CryptographicLedger,
) -> None:
    doc = _create_sample_doc()
    claim = AtomicRightsClaim(
        claim_id="clm_song_bullet_time",
        occurrence_id="occ_bullet_time",
        occurrence_lineage_id="lin_bullet_time",
        right_category="music",
        rights_subject="Brass Motif",
    )
    res = verifier.verify_agreement(doc=doc, claim=claim)
    updated_claim = verifier.update_claim_state(claim, res, counsel_signoff=True)

    assert updated_claim.licensor_grant_confirmed is True
    assert updated_claim.disposition == CensusDisposition.APPROVED
    assert "agr_sync_101" in updated_claim.notes

    event = verifier.record_verification_in_ledger(
        result=res,
        tenant_id="org_cinema",
        production_id="prod_matrix",
        actor_id="usr_clearance_counsel",
    )
    assert event is not None
    assert event.action_type == "LICENSE_VERIFIED_AGREEMENT"
    assert event.payload["claim_id"] == "clm_song_bullet_time"

    is_valid_chain, err, length = ledger.verify_chain("prod_matrix")
    assert is_valid_chain is True
    assert err is None
    assert length >= 2


def test_unblock_clarification_post_resumption(
    verifier: AgreementVerifier,
    ledger: CryptographicLedger,
) -> None:
    doc = _create_sample_doc()
    claim = AtomicRightsClaim(
        claim_id="clm_trademark_sunglasses",
        occurrence_id="occ_neo_sunglasses",
        occurrence_lineage_id="lin_neo_shades",
        right_category="trademark",
        rights_subject="Custom Designer Shades",
    )
    clarification = ClarificationRequest(
        request_id="clrf_shades_01",
        claim_id="clm_trademark_sunglasses",
        stable_lineage_key="lin_neo_shades",
        question_text="Provide executed product placement agreement.",
    )

    res, evt = verifier.verify_and_unblock(
        clarification=clarification,
        claim=claim,
        doc=doc,
        tenant_id="org_cinema",
        actor_id="usr_coordinator",
        production_id="prod_matrix",
    )

    assert res.is_valid is True
    assert clarification.status == "resolved"
    assert "agr_sync_101" in (clarification.attached_document_ref or "")
    assert claim.licensor_grant_confirmed is True
    assert claim.clarification_request_id is None
    assert evt is not None
    assert res.ledger_event_id == evt.event_id
