"""
tests/test_subgoal_decomposer.py

Comprehensive test suite for rights subgoal decomposition and evidence readiness assessment.
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.subgoal_builders import has_sample_or_remix_cues
from backend.agents.research.subgoal_decomposer import (
    SubgoalDecomposer,
    assess_subgoal_readiness,
    decompose_claim_to_subgoals,
)
from backend.agents.research.subgoal_types import (
    ReadinessStatus,
    SubgoalPriority,
    SubgoalType,
)
from backend.services.parallel_types import DomainAuthorityTier, ParallelSearchFinding


def test_music_claim_standard_decomposition():
    """Verifies that standard music claims decompose into publishing, master, and sync subgoals."""
    claim = ExtractedClaim(
        claim_id="clm_mus_01",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 4 - Radio cue",
        extracted_description="Midnight City by M83 playing on car stereo",
    )
    subgoals = decompose_claim_to_subgoals(claim)

    assert len(subgoals) == 3
    types = [sg.subgoal_type for sg in subgoals]
    assert SubgoalType.MUSIC_COMPOSITION_PUBLISHING in types
    assert SubgoalType.MUSIC_MASTER_RECORDING in types
    assert SubgoalType.MUSIC_SYNC_SCOPE in types
    assert SubgoalType.MUSIC_SAMPLE_INTERPOLATION not in types

    comp_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.MUSIC_COMPOSITION_PUBLISHING)
    assert "ISWC" in comp_sg.required_identifiers
    assert "ASCAP_BMI_WORK_ID" in comp_sg.required_identifiers
    assert any("ascap.com" in r for r in comp_sg.target_registries)

    master_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.MUSIC_MASTER_RECORDING)
    assert "ISRC" in master_sg.required_identifiers


def test_music_claim_sample_conditional_activation():
    """Verifies that derivative cues or sample keywords trigger conditional sample subgoal."""
    claim = ExtractedClaim(
        claim_id="clm_mus_02",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 12 - Club montage",
        extracted_description="Hip-hop track containing a sample of James Brown drum break",
        context_snippet="DJs play an uptempo remix sampling classic soul percussion",
    )
    assert has_sample_or_remix_cues(claim) is True

    subgoals = decompose_claim_to_subgoals(claim)
    assert len(subgoals) == 4
    types = [sg.subgoal_type for sg in subgoals]
    assert SubgoalType.MUSIC_SAMPLE_INTERPOLATION in types

    sample_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.MUSIC_SAMPLE_INTERPOLATION)
    assert sample_sg.is_conditional is True
    assert sample_sg.condition_trigger is not None
    assert "UNDERLYING_SAMPLE_RIGHTS" in sample_sg.required_identifiers
    assert sample_sg.priority == SubgoalPriority.CRITICAL


def test_brand_trademark_claims_decomposition():
    """Verifies brand claims decompose into word mark, stylized logo, and classification subgoals."""
    claim = ExtractedClaim(
        claim_id="clm_brd_01",
        category=ClaimCategory.BRAND,
        scene_or_timecode="Scene 1 - Diner table",
        extracted_description="Can of Red Bull energy drink on table",
    )
    subgoals = decompose_claim_to_subgoals(claim)

    assert len(subgoals) == 3
    types = [sg.subgoal_type for sg in subgoals]
    assert SubgoalType.BRAND_WORD_MARK in types
    assert SubgoalType.BRAND_LOGO_STYLIZED in types
    assert SubgoalType.BRAND_GOODS_SERVICES in types

    word_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.BRAND_WORD_MARK)
    assert "USPTO_REG_NO" in word_sg.required_identifiers

    class_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.BRAND_GOODS_SERVICES)
    assert "NICE_CLASS" in class_sg.required_identifiers


def test_archival_footage_claims_decomposition():
    """Verifies archival footage decomposes into federal public domain vs broadcaster rights."""
    claim = ExtractedClaim(
        claim_id="clm_ftg_01",
        category=ClaimCategory.FOOTAGE,
        scene_or_timecode="Scene 20 - Mission Control screen",
        extracted_description="Apollo 11 lunar landing footage with CBS News Cronkite commentary",
    )
    subgoals = decompose_claim_to_subgoals(claim)

    assert len(subgoals) == 2
    types = [sg.subgoal_type for sg in subgoals]
    assert SubgoalType.FOOTAGE_PUBLIC_DOMAIN_FEDERAL in types
    assert SubgoalType.FOOTAGE_BROADCASTER_MASTER in types

    fed_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.FOOTAGE_PUBLIC_DOMAIN_FEDERAL)
    assert "NASA_NARA_ID" in fed_sg.required_identifiers
    assert any("archives.gov" in r for r in fed_sg.target_registries)


def test_artwork_claims_decomposition():
    """Verifies artwork decomposes into original illustration, publication, and 1909/1976 renewal."""
    claim = ExtractedClaim(
        claim_id="clm_art_01",
        category=ClaimCategory.ARTWORK,
        scene_or_timecode="Scene 8 - Detective office",
        extracted_description="1940s pulp detective magazine cover illustration on wall",
    )
    subgoals = decompose_claim_to_subgoals(claim)

    assert len(subgoals) == 3
    types = [sg.subgoal_type for sg in subgoals]
    assert SubgoalType.ARTWORK_ORIGINAL_COPYRIGHT in types
    assert SubgoalType.ARTWORK_PERIODICAL_PUBLICATION in types
    assert SubgoalType.ARTWORK_RENEWAL_STATUS in types

    renew_sg = next(sg for sg in subgoals if sg.subgoal_type == SubgoalType.ARTWORK_RENEWAL_STATUS)
    assert "RENEWAL_REG_NO" in renew_sg.required_identifiers
    assert "1909" in renew_sg.description


def test_assess_subgoal_readiness_insufficient_empty_evidence():
    """Verifies that empty evidence produces INSUFFICIENT readiness and search action."""
    claim = ExtractedClaim(
        claim_id="clm_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 1",
        extracted_description="Background jazz track",
    )
    subgoal = decompose_claim_to_subgoals(claim)[0]
    readiness = assess_subgoal_readiness(subgoal, [])

    assert readiness.is_ready is False
    assert readiness.status == ReadinessStatus.INSUFFICIENT
    assert readiness.readiness_score == 0.0
    assert readiness.recommended_action == "DISPATCH_PARALLEL_SEARCH"
    assert len(readiness.gap_analysis) > 0


def test_assess_subgoal_readiness_ready_tier_1_verified():
    """Verifies that high-authority evidence with required identifiers yields READY status."""
    claim = ExtractedClaim(
        claim_id="clm_002",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 1",
        extracted_description="Clair de Lune",
    )
    comp_sg = decompose_claim_to_subgoals(claim)[0]

    findings = [
        ParallelSearchFinding(
            url="https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1",
            title="U.S. Copyright Office - Clair de Lune Registration",
            domain="cocatalog.loc.gov",
            excerpts=["Registration includes ISWC T-034.524.680-1, ASCAP Work ID: 902834."],
            full_excerpt="Official catalog entry. ISWC T-034.524.680-1 registered with ASCAP Work ID 902834.",
            authority_tier=DomainAuthorityTier.TIER_1_GOVERNMENT,
            authority_score=1.0,
            confidence_score=0.95,
        )
    ]

    readiness = assess_subgoal_readiness(comp_sg, findings)
    assert readiness.is_ready is True
    assert readiness.status == ReadinessStatus.READY
    assert readiness.readiness_score >= 0.75
    assert "ISWC" in readiness.matched_identifiers
    assert "ASCAP_BMI_WORK_ID" in readiness.matched_identifiers
    assert len(readiness.unresolved_identifiers) == 0
    assert readiness.recommended_action == "PROCEED_TO_CLEARANCE"


def test_assess_subgoal_readiness_partial_missing_identifier():
    """Verifies that evidence missing required identifiers yields PARTIAL or INSUFFICIENT."""
    claim = ExtractedClaim(
        claim_id="clm_003",
        category=ClaimCategory.BRAND,
        scene_or_timecode="Scene 5",
        extracted_description="Acme Brand logo",
    )
    goods_sg = next(
        sg for sg in decompose_claim_to_subgoals(claim) if sg.subgoal_type == SubgoalType.BRAND_GOODS_SERVICES
    )

    findings = [
        ParallelSearchFinding(
            url="https://blog.trademark-watcher.com/acme",
            title="Trademark Watcher Blog",
            domain="blog.trademark-watcher.com",
            excerpts=["Acme is a well known trade name in cartoons."],
            full_excerpt="Discussion of cartoon brands without specific international class references.",
            authority_tier=DomainAuthorityTier.TIER_4_GENERAL_WEB,
            authority_score=0.25,
            confidence_score=0.40,
        )
    ]

    readiness = assess_subgoal_readiness(goods_sg, findings)
    assert readiness.is_ready is False
    assert readiness.status in (ReadinessStatus.PARTIAL, ReadinessStatus.INSUFFICIENT)
    assert "NICE_CLASS" in readiness.unresolved_identifiers
    assert readiness.recommended_action in ("EXPAND_REGISTRY_SEARCH", "ESCALATE_TO_COUNSEL")


def test_subgoal_decomposer_orchestrator_class():
    """Verifies that the SubgoalDecomposer class wrapper operates idempotently."""
    decomposer = SubgoalDecomposer(readiness_threshold=0.75)
    claim = ExtractedClaim(
        claim_id="clm_004",
        category=ClaimCategory.FOOTAGE,
        scene_or_timecode="Scene 9",
        extracted_description="Apollo 11 lunar module landing broadcast",
    )
    subgoals = decomposer.decompose(claim)
    assert len(subgoals) == 2

    finding = ParallelSearchFinding(
        url="https://images.nasa.gov/details-as11-40-5874",
        title="Apollo 11 Lunar Surface Journal",
        domain="images.nasa.gov",
        excerpts=["NASA ID AS11-40-5874 is in the public domain under 17 U.S.C. § 105."],
        full_excerpt="Federal government work. NASA ID AS11-40-5874 public domain notice applies.",
        authority_tier=DomainAuthorityTier.TIER_1_GOVERNMENT,
        authority_score=1.0,
        confidence_score=0.96,
    )
    readiness = decomposer.assess_readiness(subgoals[0], [finding])
    assert readiness.is_ready is True
    assert "NASA_NARA_ID" in readiness.matched_identifiers
