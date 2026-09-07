"""
tests/test_counsel_rejection_loop.py

Milestone D Acceptance Gate: Human-in-the-Loop Clarification & Reviewer Reinvestigation.
Tests:
- Full closed loop: automated finding rejected by counsel with directive ->
  pipeline re-executes search with directive constraint -> revised finding
  logged to immutable ledger -> claim resets -> counsel sign-off -> Milestone D verified.
- Cryptographic hash-chain preservation and non-destructive attempt archiving.
- Monotonic multi-attempt lineage tracking (Attempt 1 -> 2 -> 3).
- Custom search executor injection for directed search.
- Raw dictionary claim backward compatibility.
"""

from datetime import datetime, timezone
import pytest

from backend.core.directed_research import DirectedResearchCoordinator
from backend.core.reviewer_loop import CounselReviewLoopCoordinator
from backend.core.reviewer_types import (
    AttemptLineage,
    ClaimSignOffResult,
    CounselDirective,
    ReinvestigationDispatch,
    ResearchFinding,
    ReviewerAction,
)
from backend.domain.models import AtomicRightsClaim, CensusDisposition, WorkflowReason
from backend.storage.ledger import CryptographicLedger


@pytest.fixture
def fresh_ledger() -> CryptographicLedger:
    """Provides an isolated CryptographicLedger instance."""
    return CryptographicLedger()


@pytest.fixture
def coordinator(fresh_ledger: CryptographicLedger) -> CounselReviewLoopCoordinator:
    """Provides a fresh CounselReviewLoopCoordinator wired to fresh ledger."""
    return CounselReviewLoopCoordinator(ledger=fresh_ledger)


def test_milestone_d_acceptance_gate_full_loop(coordinator: CounselReviewLoopCoordinator):
    """
    Milestone D Acceptance Gate:
    Automated finding rejected by counsel with directive -> search re-executed
    with directive constraint -> revised finding logged -> claim resets -> sign-off.
    """
    claim = AtomicRightsClaim(
        claim_id="claim_music_d1", occurrence_id="occ_d1", occurrence_lineage_id="lin_d1",
        right_category="composition", rights_subject="The 1972 Live Adaptation",
        disposition=CensusDisposition.APPROVED, attempt_number=1,
    )
    prior_finding = "Public domain based on 1920 publication record"
    directive_text = "Re-search ASCAP specifically for 1972 live adaptation rights in UK territory"
    dispatch = coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding=prior_finding, directive_text=directive_text,
        counsel_id="counsel_007", counsel_name="Sarah Jenkins, Esq.",
        tenant_id="tenant_warner", production_id="prod_matrix",
        prior_finding_id="find_pd_001",
    )
    assert dispatch.attempt_number == 2
    assert claim.attempt_number == 2
    assert claim.disposition == CensusDisposition.NEEDS_REVIEW
    assert claim.workflow_reason == WorkflowReason.REINVESTIGATION_REQUESTED
    assert dispatch.ledger_event.action_type == "CLAIM_REJECTED_BY_COUNSEL"
    assert "ASCAP" in dispatch.directive.sanitized_keywords
    assert "1972" in dispatch.directive.sanitized_keywords
    assert dispatch.revised_finding_id is not None
    assert len(claim.archived_recommendations) == 1
    assert claim.archived_recommendations[0]["prior_finding"] == prior_finding

    signoff = coordinator.sign_off_claim(
        claim=claim, counsel_id="counsel_007", counsel_name="Sarah Jenkins, Esq.",
        citation_text="ASCAP Work #771029 / 17 U.S.C. § 107 Fair Use cleared",
        conditions=["Worldwide theatrical only"], tenant_id="tenant_warner", production_id="prod_matrix",
    )
    assert signoff.disposition == CensusDisposition.APPROVED
    assert claim.disposition == CensusDisposition.APPROVED
    assert signoff.ledger_event.action_type == "CLAIM_COUNSEL_SIGNED_OFF"
    assert "ASCAP Work #771029" in claim.notes


def test_ledger_immutability_and_hash_chain(coordinator: CounselReviewLoopCoordinator):
    """Verifies that rejection and sign-off form an unbroken, tamper-evident hash chain."""
    claim = AtomicRightsClaim(
        claim_id="claim_tm_002", occurrence_id="occ_02", occurrence_lineage_id="lin_02",
        right_category="trademark", rights_subject="Acme Brand Billboard",
        attempt_number=1, disposition=CensusDisposition.UNKNOWN,
    )
    coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding="Unregistered trademark in background",
        directive_text="Verify USPTO principal register for Acme marks in class 009",
        counsel_id="counsel_tm", counsel_name="David Ross, Esq.",
        tenant_id="tenant_sony", production_id="prod_spiderman",
    )
    coordinator.sign_off_claim(
        claim=claim, counsel_id="counsel_tm", counsel_name="David Ross, Esq.",
        citation_text="De minimis background trademark use per 15 U.S.C. § 1125",
        tenant_id="tenant_sony", production_id="prod_spiderman",
    )
    chain = coordinator.ledger._chains["prod_spiderman"]
    assert len(chain) == 4
    assert [e.action_type for e in chain] == [
        "GENESIS", "CLAIM_REJECTED_BY_COUNSEL", "REVISED_FINDING_LOGGED", "CLAIM_COUNSEL_SIGNED_OFF"
    ]
    for i in range(1, len(chain)):
        assert chain[i].previous_event_hash == chain[i - 1].entry_hash


def test_multi_attempt_lineage_preservation(coordinator: CounselReviewLoopCoordinator):
    """Verifies monotonic attempt incrementing across 2 successive rejections."""
    claim = AtomicRightsClaim(
        claim_id="claim_multi_01", occurrence_id="occ_m", occurrence_lineage_id="lin_m",
        right_category="footage", rights_subject="Archival Apollo 11 Clip",
        attempt_number=1,
    )
    d1 = coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding="NASA public domain assumption",
        directive_text="Verify whether astronaut likeness release is required",
        counsel_id="counsel_space", counsel_name="Elena Rostova, Esq.",
        tenant_id="tenant_paramount", production_id="prod_apollo",
    )
    assert d1.attempt_number == 2
    d2 = coordinator.reject_and_reopen_investigation(
        claim=claim, prior_finding="NASA footage confirmed, but audio contains music",
        directive_text="Re-search audio track for separate sync license rights",
        counsel_id="counsel_space", counsel_name="Elena Rostova, Esq.",
        tenant_id="tenant_paramount", production_id="prod_apollo",
    )
    assert d2.attempt_number == 3
    assert claim.attempt_number == 3
    lineage = coordinator.get_lineage("claim_multi_01")
    assert lineage is not None
    assert len(lineage.attempts) == 2
    assert lineage.attempts[0].attempt_number == 1
    assert lineage.attempts[1].attempt_number == 2


def test_custom_search_executor_injection(fresh_ledger: CryptographicLedger):
    """Verifies injection of custom search executor in directed research."""
    called_queries = []

    def mock_search(query: str, directive: CounselDirective, claim_id: str):
        called_queries.append(query)
        return {
            "evidence_summary": f"Custom mock search matched {directive.directive_text}",
            "source_uri": "https://ascap.com/mock_entry",
            "confidence_score": 0.99,
        }

    dir_coord = DirectedResearchCoordinator(ledger=fresh_ledger, search_executor=mock_search)
    loop_coord = CounselReviewLoopCoordinator(ledger=fresh_ledger, directed_coordinator=dir_coord)
    claim = AtomicRightsClaim(
        claim_id="claim_custom_01", occurrence_id="occ_c", occurrence_lineage_id="lin_c",
        right_category="music", rights_subject="Yesterday Live 1966",
    )
    dispatch = loop_coord.reject_and_reopen_investigation(
        claim=claim, prior_finding="Fair use parity assumption",
        directive_text="Confirm Sony/ATV publishing share in France",
        counsel_id="counsel_eu", counsel_name="Jean Dupont, Avocat",
        tenant_id="tenant_pathe", production_id="prod_paris",
    )
    assert len(called_queries) == 1
    assert "Yesterday Live 1966" in called_queries[0]
    assert "Custom mock search" in dispatch.reinvestigation_result.evidence_summary


def test_dictionary_compatibility_mode(coordinator: CounselReviewLoopCoordinator):
    """Verifies end-to-end operation with raw dictionary claims."""
    claim_dict = {
        "claim_id": "claim_dict_99",
        "right_category": "publicity",
        "rights_subject": "Famous Athlete Likeness",
        "attempt_number": 1,
        "disposition": CensusDisposition.UNKNOWN,
    }
    dispatch = coordinator.reject_and_reopen_investigation(
        claim=claim_dict, prior_finding="Incidental news documentary use",
        directive_text="Verify commercial endorsement disclaimer",
        counsel_id="counsel_dict", counsel_name="Pat Stone, Esq.",
        tenant_id="tenant_disney", production_id="prod_sports",
    )
    assert claim_dict["attempt_number"] == 2
    assert claim_dict["disposition"] == CensusDisposition.NEEDS_REVIEW
    assert dispatch.revised_finding_id is not None
    signoff = coordinator.sign_off_claim(
        claim=claim_dict, counsel_id="counsel_dict", counsel_name="Pat Stone, Esq.",
        citation_text="First Amendment artistic relevance cleared",
        tenant_id="tenant_disney", production_id="prod_sports",
    )
    assert claim_dict["disposition"] == CensusDisposition.APPROVED
    assert signoff.disposition == CensusDisposition.APPROVED
