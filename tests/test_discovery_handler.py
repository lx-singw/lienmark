"""
tests/test_discovery_handler.py

Automated test suite for DiscoveryHandler and mid-run claim discovery.
Sprint 3.2: Mid-Run Claim Discovery & Secondary IP Detection.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.discovery_handler import DiscoveryHandler
from backend.agents.research.discovery_types import (
    ProposedClaimEvent,
    ProposedClaimNotFoundError,
    ProposedClaimStatus,
    SecondaryIPType,
)
from backend.agents.research.query_types import AssetClass
from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import CreativeUseNode, ParserMetadata
from backend.services.parallel_types import DomainAuthorityTier, ParallelSearchFinding
from backend.storage.baseline_store import InMemoryBaselineStore


@pytest.fixture
def sample_parent_claim() -> ExtractedClaim:
    return ExtractedClaim(
        claim_id="clm_song_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="Scene 14 - Club Sequence",
        extracted_description="Main theme hip-hop track playing on radio.",
        confidence=0.95,
    )


@pytest.fixture
def baseline_setup():
    store = InMemoryBaselineStore()
    engine = ProductionBaselineEngine(store=store)
    tenant_id = "org_cinema_group"
    prod_id = "prod_blockbuster_2026"
    meta = ParserMetadata(parser_name="screenplay_ast", parser_version="1.0.0")
    c1 = CreativeUseNode(
        claim_id="clm_song_001",
        stable_lineage_key="lin_song_001",
        asset_type="music",
        scene_or_timecode="Scene 14",
        description="Main theme hip-hop track",
        prominence="background",
        context="Track plays on boombox",
        context_hash="a1b2c3d4e5f60718",
    )
    v1 = engine.register_baseline(
        tenant_id=tenant_id,
        production_id=prod_id,
        version_id="v1",
        content_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        parser_metadata=meta,
        claims=[c1],
        version_tag="Cut 1",
    )
    return engine, tenant_id, prod_id, v1


def test_detect_musical_sample(sample_parent_claim):
    handler = DiscoveryHandler()
    finding = ParallelSearchFinding(
        url="https://www.whosampled.com/track/123",
        title="WhoSampled: Track Breakdown",
        domain="whosampled.com",
        full_excerpt="This track contains samples from 'Funky Drummer' by James Brown.",
        authority_tier=DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
        authority_score=0.75,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    assert len(events) == 1
    ev = events[0]
    assert ev.category == AssetClass.MUSIC
    assert ev.discovery_type == SecondaryIPType.MUSICAL_SAMPLE
    assert "Funky Drummer" in ev.detected_entity
    assert "James Brown" in ev.detected_entity
    assert ev.status == ProposedClaimStatus.PROPOSED
    assert ev.parent_claim_id == sample_parent_claim.claim_id


def test_detect_interpolation(sample_parent_claim):
    handler = DiscoveryHandler()
    finding = ParallelSearchFinding(
        url="https://genius.com/track/analysis",
        title="Genius Track Annotations",
        domain="genius.com",
        full_excerpt="The chorus interpolates 'Pastime Paradise' by Stevie Wonder.",
        authority_tier=DomainAuthorityTier.TIER_4_GENERAL_WEB,
        authority_score=0.60,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    assert len(events) == 1
    ev = events[0]
    assert ev.category == AssetClass.MUSIC
    assert ev.discovery_type == SecondaryIPType.INTERPOLATION
    assert "Pastime Paradise" in ev.detected_entity
    assert ev.status == ProposedClaimStatus.PROPOSED


def test_detect_featured_artist_likeness(sample_parent_claim):
    handler = DiscoveryHandler()
    finding = ParallelSearchFinding(
        url="https://billboard.com/charts/top-100",
        title="Billboard Feature Story",
        domain="billboard.com",
        full_excerpt="Single release featuring Kendrick Lamar with distinct guest appearance.",
        authority_tier=DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
        authority_score=0.85,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    assert len(events) == 1
    ev = events[0]
    assert ev.category == AssetClass.LIKENESS
    assert ev.discovery_type == SecondaryIPType.FEATURED_ARTIST
    assert "Kendrick Lamar" in ev.detected_entity


def test_detect_secondary_trademark(sample_parent_claim):
    handler = DiscoveryHandler()
    finding = ParallelSearchFinding(
        url="https://variety.com/archival-footage-cleared",
        title="Variety Production Archive Notes",
        domain="variety.com",
        full_excerpt="Archival news broadcast prominently features the logo of Stark Industries.",
        authority_tier=DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
        authority_score=0.80,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    assert len(events) == 1
    ev = events[0]
    assert ev.category == AssetClass.BRAND
    assert ev.discovery_type == SecondaryIPType.SECONDARY_TRADEMARK
    assert "Stark Industries" in ev.detected_entity


def test_intake_claim_schema_validation(sample_parent_claim):
    handler = DiscoveryHandler()
    ev = ProposedClaimEvent(
        proposed_claim_id="prop_test_001",
        parent_claim_id=sample_parent_claim.claim_id,
        source_finding_id="https://example.com/finding",
        detected_entity="Pastime Paradise by Stevie Wonder",
        category=AssetClass.MUSIC,
        rationale="Sample clearance needed",
        confidence=0.9,
        scene_locator="Scene 14",
    )
    extracted = handler.validate_as_extracted_claim(ev)
    assert extracted.claim_id == "prop_test_001"
    assert extracted.category == ClaimCategory.MUSIC
    assert extracted.needs_clarification is True
    assert len(extracted.extracted_description.split()) <= 20


def _assert_v1_integrity(engine, tenant_id: str, prod_id: str, initial_digest: str) -> None:
    """Asserts that baseline v1 maintains unchanged digest and claim count."""
    v1 = engine.get_baseline(tenant_id, prod_id, "v1")
    assert v1.baseline_digest == initial_digest
    assert len(v1.claims) == 1


def test_baseline_immutability_and_promotion(sample_parent_claim, baseline_setup):
    engine, tenant_id, prod_id, v1 = baseline_setup
    initial_digest = v1.baseline_digest
    handler = DiscoveryHandler(baseline_engine=engine)

    finding = ParallelSearchFinding(
        url="https://whosampled.com/track/1",
        title="WhoSampled",
        domain="whosampled.com",
        full_excerpt="This track contains samples from 'Amen Brother' by The Winstons.",
        authority_tier=DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
        authority_score=0.75,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    assert len(events) == 1
    prop_id = events[0].proposed_claim_id

    _assert_v1_integrity(engine, tenant_id, prod_id, initial_digest)

    v2 = handler.promote_accepted_claims_to_new_baseline(
        tenant_id=tenant_id,
        production_id=prod_id,
        current_version_id="v1",
        new_version_id="v2",
        accepted_claim_ids=[prop_id],
    )
    assert v2.version_id == "v2"
    assert v2.previous_version_id == "v1"
    assert len(v2.claims) == 2
    assert any(c.claim_id == prop_id for c in v2.claims)

    _assert_v1_integrity(engine, tenant_id, prod_id, initial_digest)
    lineage = engine.get_lineage_history(tenant_id, prod_id, "v2")
    assert [v.version_id for v in lineage] == ["v1", "v2"]


def test_status_update_and_dismissal(sample_parent_claim):
    handler = DiscoveryHandler()
    finding = ParallelSearchFinding(
        url="https://example.com/source",
        title="Source",
        full_excerpt="Track contains samples from 'Soul Power' by Maceo Parker.",
        authority_tier=DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [finding])
    prop_id = events[0].proposed_claim_id

    updated = handler.update_claim_status(prop_id, ProposedClaimStatus.DISMISSED)
    assert updated.status == ProposedClaimStatus.DISMISSED
    assert handler.get_proposed_claim(prop_id).status == ProposedClaimStatus.DISMISSED

    with pytest.raises(ProposedClaimNotFoundError):
        handler.update_claim_status("nonexistent_id", ProposedClaimStatus.ACCEPTED)


def test_deduplication_across_findings(sample_parent_claim):
    handler = DiscoveryHandler()
    f1 = ParallelSearchFinding(
        url="https://source1.com",
        title="Source 1",
        full_excerpt="Contains samples from 'Funky Drummer' by James Brown.",
    )
    f2 = ParallelSearchFinding(
        url="https://source2.com",
        title="Source 2",
        full_excerpt="Sample of 'Funky Drummer' by James Brown was used in verse 1.",
    )
    events = handler.detect_secondary_ip(sample_parent_claim, [f1, f2])
    assert len(events) == 1
