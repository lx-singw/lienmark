"""
test_entity_disambiguation_and_modern_uspto.py

Unit and integration tests for:
1. Modern USPTO Trademark Search System (tmsearch.uspto.gov / uspto.report replacing retired TESS).
2. Two-Phase Grounded Research (Phase 1 Identity Anchoring, Phase 2 Adversarial Disconfirmation).
3. Entity Disambiguation Invariant (Alabama Shakes 'Hold On' vs. Wilson Phillips 'Hold On').
4. Dynamic fallback resolution for unfamiliar queries without hardcoded green badges.
"""

import pytest
import asyncio
from backend.domain.models import EvidenceStance, PublicEvidenceSnapshot
from backend.services.parallel_service import ParallelSearchService


class TestModernUSPTOSearchSystem:
    """Verifies replacement of retired USPTO TESS with Modern USPTO Trademark Search System."""

    def test_uspto_modern_domains_and_templates(self):
        """Asserts constants point to modern USPTO search endpoints rather than retired TESS."""
        assert ParallelSearchService.USPTO_MODERN_SEARCH_DOMAIN == "site:tmsearch.uspto.gov"
        assert ParallelSearchService.USPTO_REPORT_DOMAIN == "site:uspto.report"
        assert "tmsearch.uspto.gov" in ParallelSearchService.USPTO_TRADEMARK_REGISTRY_DOMAINS
        assert "uspto.report" in ParallelSearchService.USPTO_TRADEMARK_REGISTRY_DOMAINS
        assert "tess" not in ParallelSearchService.USPTO_TRADEMARK_REGISTRY_DOMAINS.lower()

    def test_build_trademark_search_query_targets_modern_uspto(self):
        """Asserts trademark query construction targets modern USPTO search system."""
        query = ParallelSearchService.build_trademark_search_query(
            mark_or_title="Lienmark Cinema Shield",
            owner_or_applicant="Lienmark Technologies Inc.",
            registration_or_serial_no="98765432",
        )
        assert '"Lienmark Cinema Shield"' in query
        assert '"Lienmark Technologies Inc."' in query
        assert "98765432" in query
        assert "site:tmsearch.uspto.gov" in query
        assert "site:uspto.report" in query
        assert "trademark status assignment" in query

    @pytest.mark.asyncio
    async def test_fallback_mode_modern_uspto_returns_informational(self):
        """Asserts fallback mode retrieves modern USPTO trademark informational status."""
        service = ParallelSearchService(use_fallback=True)
        query = ParallelSearchService.build_trademark_search_query(
            mark_or_title="Starlight Studios",
        )
        snapshot = await service.search(
            query=query,
            use_id="use_tm_starlight",
            stable_lineage_key="trademark_starlight_studios",
        )
        assert snapshot.stance == EvidenceStance.INFORMATIONAL
        assert "tmsearch.uspto.gov" in snapshot.source_url
        assert "Modern USPTO Trademark Search System" in snapshot.source_title
        assert "Patent and Trademark Office" in snapshot.publisher


class TestTwoPhaseGroundedResearch:
    """Verifies Two-Phase Grounded Research query construction and execution."""

    def test_build_identity_anchoring_query(self):
        """Phase 1: Anchors identity by title, artist/author, year, catalog ID, or registry."""
        q_music = ParallelSearchService.build_identity_anchoring_query(
            title="Hold On",
            artist_or_author="Alabama Shakes",
            year=2012,
            catalog_id="ATO0134",
            asset_type="music",
        )
        assert '"Hold On"' in q_music
        assert '"Alabama Shakes"' in q_music
        assert "2012" in q_music
        assert "ATO0134" in q_music
        assert "ASCAP BMI rights" in q_music

        q_poster = ParallelSearchService.build_identity_anchoring_query(
            title="Shadows of Manhattan",
            artist_or_author="Detective Magazine",
            year=1944,
            asset_type="artwork",
        )
        assert '"Shadows of Manhattan"' in q_poster
        assert '"Detective Magazine"' in q_poster
        assert "1944" in q_poster
        assert "LOC copyright renewal" in q_poster

        q_tm = ParallelSearchService.build_identity_anchoring_query(
            title="CinemaGuard",
            registry="uspto",
        )
        assert '"CinemaGuard"' in q_tm
        assert "site:tmsearch.uspto.gov" in q_tm

    def test_build_adversarial_disconfirmation_query(self):
        """Phase 2: Probes against preliminary findings for disputes, adverse assignments, or conflicting claims."""
        q_probe = ParallelSearchService.build_adversarial_disconfirmation_query(
            title="Midnight Serenade",
            artist_or_author="Duke Ellington Band",
            preliminary_findings="Vanguard Media Holdings synchronization license",
        )
        assert '"Midnight Serenade"' in q_probe
        assert '"Duke Ellington Band"' in q_probe
        assert 'dispute OR assignment OR infringement OR "competing claim"' in q_probe
        assert '"Vanguard Media Holdings synchronization license"' in q_probe

    @pytest.mark.asyncio
    async def test_execute_two_phase_research_detects_dispute(self):
        """Executes full Two-Phase research where Phase 2 reveals an adverse assignment dispute."""
        service = ParallelSearchService(use_fallback=True)
        result = await service.execute_two_phase_research(
            title="Midnight Serenade",
            asset_id="asset_midnight_cue_01",
            stable_lineage_key="music_cue_midnight_serenade",
            artist_or_author="Duke Ellington Band",
            year=1938,
            asset_type="music",
        )
        assert result["is_disambiguated"] is True
        assert result["has_adversarial_dispute"] is True
        assert result["reconciled_stance"] == EvidenceStance.CONTRADICTORY
        assert result["phase2_snapshot"].stance == EvidenceStance.CONTRADICTORY
        assert len(result["snapshots"]) == 2

    @pytest.mark.asyncio
    async def test_execute_two_phase_research_confirms_public_domain(self):
        """Executes full Two-Phase research confirming public domain renewal lapse."""
        service = ParallelSearchService(use_fallback=True)
        result = await service.execute_two_phase_research(
            title="Shadows of Manhattan Detective Magazine",
            asset_id="asset_poster_noir_01",
            stable_lineage_key="poster_noir_detective_magazine",
            artist_or_author="Detective Magazine Publishers",
            year=1944,
            asset_type="poster",
        )
        assert result["is_disambiguated"] is True
        assert result["reconciled_stance"] == EvidenceStance.SUPPORTING
        assert result["phase1_snapshot"].stance == EvidenceStance.SUPPORTING


class TestEntityDisambiguationInvariant:
    """
    Verifies that two works with the same title:
    Song A: 'Hold On' by Alabama Shakes (2012)
    Song B: 'Hold On' by Wilson Phillips (1990)
    must NOT share evidence snapshots, cached results, or approvals.
    """

    def test_cache_key_requires_disambiguation_tuple(self):
        """Cache keys strictly require (asset_id, stable_lineage_key, artist_or_author)."""
        key_a = ParallelSearchService.build_disambiguation_key(
            asset_id="asset_song_alabama_shakes",
            stable_lineage_key="music_cue_hold_on_alabama",
            artist_or_author="Alabama Shakes",
            title="Hold On",
            query="Hold On Alabama Shakes dispute",
        )
        key_b = ParallelSearchService.build_disambiguation_key(
            asset_id="asset_song_wilson_phillips",
            stable_lineage_key="music_cue_hold_on_wilson",
            artist_or_author="Wilson Phillips",
            title="Hold On",
            query="Hold On Wilson Phillips 1990",
        )
        assert key_a != key_b
        assert "alabama shakes" in key_a
        assert "wilson phillips" in key_b
        assert "asset_song_alabama_shakes" in key_a
        assert "asset_song_wilson_phillips" in key_b

    def test_bare_title_cache_key_rejected(self):
        """Bare title strings cannot be used as cache keys without entity identifiers."""
        with pytest.raises(ValueError) as exc_info:
            ParallelSearchService.build_disambiguation_key(
                asset_id="",
                stable_lineage_key="",
                artist_or_author="",
                title="Hold On",
            )
        assert "Entity disambiguation invariant violated" in str(exc_info.value)
        assert "Bare title 'Hold On' cannot be used as a cache key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_same_title_two_artists_isolated_in_cache(self):
        """Song A and Song B sharing title 'Hold On' must NOT share cached snapshots."""
        service = ParallelSearchService(use_fallback=True)

        # Work A: Alabama Shakes (active dispute probe)
        snap_a = await service.search(
            query="Hold On Alabama Shakes copyright assignment dispute",
            use_id="use_song_alabama",
            stable_lineage_key="cue_hold_on_alabama",
            asset_id="asset_alabama_01",
            artist_or_author="Alabama Shakes",
            title="Hold On",
            use_cache=True,
        )
        assert snap_a.stance == EvidenceStance.CONTRADICTORY

        # Work B: Wilson Phillips (ASCAP registry lookup)
        snap_b = await service.search(
            query="Hold On Wilson Phillips 1990 ASCAP registry",
            use_id="use_song_wilson",
            stable_lineage_key="cue_hold_on_wilson",
            asset_id="asset_wilson_01",
            artist_or_author="Wilson Phillips",
            title="Hold On",
            use_cache=True,
        )
        assert snap_b.stance == EvidenceStance.INFORMATIONAL

        # Assert snapshots and cache records are strictly distinct
        assert snap_a.snapshot_id != snap_b.snapshot_id
        assert snap_a.metadata["artist_or_author"] == "Alabama Shakes"
        assert snap_b.metadata["artist_or_author"] == "Wilson Phillips"
        assert snap_a.metadata["disambiguation_key"] != snap_b.metadata["disambiguation_key"]

        # Assert cache lookups retrieve the correct respective snapshot
        cached_a = service.get_cached_snapshot(
            asset_id="asset_alabama_01",
            stable_lineage_key="cue_hold_on_alabama",
            artist_or_author="Alabama Shakes",
            query="Hold On Alabama Shakes copyright assignment dispute",
            title="Hold On",
        )
        cached_b = service.get_cached_snapshot(
            asset_id="asset_wilson_01",
            stable_lineage_key="cue_hold_on_wilson",
            artist_or_author="Wilson Phillips",
            query="Hold On Wilson Phillips 1990 ASCAP registry",
            title="Hold On",
        )
        assert cached_a is not None
        assert cached_b is not None
        assert cached_a.stance == EvidenceStance.CONTRADICTORY
        assert cached_b.stance == EvidenceStance.INFORMATIONAL
        assert cached_a.metadata["artist_or_author"] == "Alabama Shakes"
        assert cached_b.metadata["artist_or_author"] == "Wilson Phillips"

    @pytest.mark.asyncio
    async def test_dynamic_fallback_unfamiliar_queries(self):
        """
        In fallback/simulation mode:
        - query with 'dispute' or 'infringement' -> CONTRADICTORY
        - query with 'public domain' and valid expiry -> SUPPORTING
        - query with empty / unfound -> INSUFFICIENT
        - does NOT return hardcoded 'No adverse copyright' green badges.
        """
        service = ParallelSearchService(use_fallback=True)

        # 1. Dispute / Infringement
        snap_dispute = await service.search(
            query="Novel title infringement lawsuit competing claim",
            use_id="use_test_dispute",
            stable_lineage_key="novel_unknown_dispute",
        )
        assert snap_dispute.stance == EvidenceStance.CONTRADICTORY
        assert "dispute" in snap_dispute.source_title.lower() or "dispute" in snap_dispute.excerpt.lower()

        # 2. Public domain with valid expiry (pre-1929)
        snap_pd_valid = await service.search(
            query="Folk Melody 1920 public domain valid expiry LOC",
            use_id="use_test_pd_valid",
            stable_lineage_key="melody_1920_pd",
        )
        assert snap_pd_valid.stance == EvidenceStance.SUPPORTING
        assert "public domain" in snap_pd_valid.excerpt.lower()

        # 3. Public domain WITHOUT valid expiry (e.g. 1995 modern work)
        snap_pd_invalid = await service.search(
            query="Modern Electronic Album 1995 public domain without expiry proof",
            use_id="use_test_pd_invalid",
            stable_lineage_key="album_1995_not_pd",
        )
        # Should NOT return SUPPORTING because 1995 has not statutorily expired
        assert snap_pd_invalid.stance != EvidenceStance.SUPPORTING
        assert snap_pd_invalid.stance in (EvidenceStance.INSUFFICIENT, EvidenceStance.INFORMATIONAL)

        # 4. Empty query
        snap_empty = await service.search(
            query="   ",
            use_id="use_empty",
            stable_lineage_key="asset_empty",
        )
        assert snap_empty.stance == EvidenceStance.INSUFFICIENT
        assert "No Attributable Evidence Found" in snap_empty.source_title

        # 5. Unfamiliar / unindexed query
        snap_unfamiliar = await service.search(
            query="Random obscure modern screenplay unpublished manuscript 2023",
            use_id="use_unfamiliar",
            stable_lineage_key="script_unfamiliar_asset",
        )
        assert snap_unfamiliar.stance == EvidenceStance.INSUFFICIENT
        assert "zero matching catalog records" in snap_unfamiliar.excerpt.lower()
        # Verify NO hardcoded 'No adverse copyright' green badge
        assert "no adverse copyright" not in snap_unfamiliar.excerpt.lower()
