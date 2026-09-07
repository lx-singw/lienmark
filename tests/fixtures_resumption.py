"""
tests/fixtures_resumption.py

Test fixtures and mock agreement payloads for Sprint 4.2 Autonomous Resumption.
Separated strictly under Google AntiGravity architectural guidelines (SRP, files <= 250 lines).
"""

from __future__ import annotations

from backend.domain.models import AtomicRightsClaim, CensusDisposition
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput,
    SignatureParty,
)


def mock_sync_license_content() -> str:
    """Returns sample executed synchronization license agreement text."""
    return (
        "SYNCHRONIZATION LICENSE AGREEMENT\n"
        "By and between Blue Note Publishing (Licensor) and Paramount Pictures (Licensee).\n"
        "Asset Title: 'Diner Jazz Solo Cue'\n"
        "Execution Date: 2026-06-15\n"
        "Grant Territory: Worldwide in perpetuity.\n"
        "Grant Media: All Media including Theatrical, Television, and SVOD streaming.\n"
        "Signed: Blue Note Publishing (Licensor Authorized Signature)\n"
        "Signed: Paramount Pictures (Licensee Authorized Signature)\n"
    )


def build_diner_jazz_claim() -> AtomicRightsClaim:
    """Builds atomic claim for ambiguous diner jazz cue."""
    return AtomicRightsClaim(
        claim_id="clm_scene14_diner_jazz",
        occurrence_id="occ_scene14_jazz",
        occurrence_lineage_id="lineage_diner_jazz_cue",
        right_category="music",
        rights_subject="Diner Jazz Solo Cue",
        intended_territory=["Worldwide"],
        intended_media=["theatrical", "streaming"],
        intended_context="diner scene background",
        disposition=CensusDisposition.NEEDS_REVIEW,
        notes="an uncredited jazz solo plays in the background of the diner scene",
    )


def create_verified_doc_input(text: str) -> AgreementDocumentInput:
    """Builds AgreementDocumentInput from parsed mock sync license."""
    signatures = [
        SignatureParty(party_name="Blue Note Publishing", party_role="licensor", is_signed=True),
        SignatureParty(party_name="Paramount Pictures", party_role="licensee", is_signed=True),
    ]
    return AgreementDocumentInput(
        agreement_id="agr_sync_blue_note_001",
        document_name="mock_sync_license.pdf",
        licensor="Blue Note Publishing",
        licensee="Paramount Pictures",
        execution_date="2026-06-15",
        territories=["Worldwide"],
        media=["All Media"],
        term="In perpetuity",
        granted_rights=["Synchronization rights"],
        signatures=signatures,
        raw_text=text,
    )
