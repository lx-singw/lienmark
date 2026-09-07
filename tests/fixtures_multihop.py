"""
tests/fixtures_multihop.py

Test fixtures and mock search responses for multi-hop research verification.
Separated strictly under Google AntiGravity architectural guidelines (SRP).
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelSearchFinding,
    ParallelSearchResult,
)


@pytest.fixture
def ambiguous_music_claim() -> ExtractedClaim:
    """Fixture providing an ambiguous music track administered by a corporate publisher."""
    return ExtractedClaim(
        claim_id="clm_mus_ambiguous_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 14 - Club Sequence",
        extracted_description="Midnight Echoes at Twilight",
        context_snippet="Original atmospheric jazz recording playing in club background.",
        confidence=0.85,
    )


@pytest.fixture
def hop0_search_result() -> ParallelSearchResult:
    """Simulates primary search findings containing an attributable corporate administrator lead."""
    finding = ParallelSearchFinding(
        url="https://www.ascap.com/ace/work/9823145",
        title="Midnight Echoes at Twilight - ACE Work #9823145",
        excerpts=[
            "Writers: Elena Vance, Marcus Holloway.",
            "Published by Twilight Melodies Ltd. Administered by Sony Music Publishing.",
        ],
        full_excerpt=(
            "Work ID: 9823145. Published by Twilight Melodies Ltd. "
            "Administered by Sony Music Publishing worldwide catalog."
        ),
        domain="ascap.com",
        authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
        confidence_score=0.74,
    )
    return ParallelSearchResult(
        query="Midnight Echoes at Twilight catalog publishing master rights",
        findings=[finding],
        total_results=1,
        latency_ms=120,
        http_status=200,
    )


@pytest.fixture
def hop1_search_result() -> ParallelSearchResult:
    """Simulates multi-hop follow-up findings from the target parent catalog."""
    finding = ParallelSearchFinding(
        url="https://www.sonymusicpub.com/catalog/work/9823145",
        title="Sony Music Publishing Catalog - Midnight Echoes at Twilight",
        excerpts=[
            "Confirmed worldwide administration rights for Midnight Echoes at Twilight.",
            "100% sync and mechanical administration controlled by Sony Music Publishing.",
        ],
        full_excerpt=(
            "Sony Music Publishing Sync Catalog: Confirmed 100% worldwide "
            "administration rights for Midnight Echoes at Twilight."
        ),
        domain="sonymusicpub.com",
        authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
        authority_score=1.0,
        confidence_score=0.92,
    )
    return ParallelSearchResult(
        query='"Sony Music Publishing" music publishing sync licensing catalog contact',
        findings=[finding],
        total_results=1,
        latency_ms=110,
        http_status=200,
    )
