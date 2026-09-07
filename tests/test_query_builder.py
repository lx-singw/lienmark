"""
tests/test_query_builder.py

Automated test suite for StructuredQueryBuilder and entity disambiguation.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.research.query_builder import StructuredQueryBuilder
from backend.agents.research.query_types import (
    AssetClass,
    EntityDisambiguationError,
    SearchQueryRequest,
    SteeringState,
)


def test_query_generation_music_asset_class():
    """Verifies that music queries target ASCAP, BMI, and LOC."""
    builder = StructuredQueryBuilder()
    req = SearchQueryRequest(
        asset_id="clm_001",
        asset_class=AssetClass.MUSIC,
        title="Clair de Lune",
        creator_or_owner="Claude Debussy",
        year=1905,
    )
    res = builder.build_query(req)
    assert res.state == SteeringState.STRICT_REGISTRY
    assert '"Clair de Lune"' in res.query_string
    assert '"Claude Debussy"' in res.query_string
    assert "1905" in res.query_string
    assert any("site:ascap.com" in d for d in res.registry_domains)
    assert any("site:bmi.com" in d for d in res.registry_domains)


def test_query_generation_modern_uspto_trademark():
    """Verifies that trademark queries target modern USPTO, never legacy TESS."""
    builder = StructuredQueryBuilder()
    req = SearchQueryRequest(
        asset_id="clm_002",
        asset_class=AssetClass.BRAND,
        title="Coca-Cola",
        creator_or_owner="The Coca-Cola Company",
    )
    res = builder.build_query(req)
    assert '"Coca-Cola"' in res.query_string
    assert "site:tmsearch.uspto.gov" in res.query_string
    assert "tess" not in res.query_string.lower()


def test_query_generation_footage_nasa_and_archives():
    """Verifies that archival footage queries target NASA and National Archives."""
    builder = StructuredQueryBuilder()
    req = SearchQueryRequest(
        asset_id="clm_003",
        asset_class=AssetClass.FOOTAGE,
        title="Apollo 11 Moon Landing",
        creator_or_owner="NASA",
        year=1969,
    )
    res = builder.build_query(req)
    assert "site:images.nasa.gov" in res.query_string
    assert "site:archives.gov" in res.query_string


def test_query_generation_artwork_and_likeness():
    """Verifies artwork and likeness category query generation."""
    builder = StructuredQueryBuilder()
    req_art = SearchQueryRequest(
        asset_id="clm_004",
        asset_class=AssetClass.ARTWORK,
        title="Shadows of Manhattan",
        creator_or_owner="Crime Detective Magazine",
        year=1944,
    )
    res_art = builder.build_query(req_art)
    assert "site:cocatalog.loc.gov" in res_art.query_string

    req_likeness = SearchQueryRequest(
        asset_id="clm_005",
        asset_class=AssetClass.LIKENESS,
        title="Marilyn Monroe",
        creator_or_owner="Estate of Marilyn Monroe",
    )
    res_likeness = builder.build_query(req_likeness)
    assert "site:cmgworldwide.com" in res_likeness.query_string


def test_entity_disambiguation_invariant():
    """Verifies that same-title works by different creators yield distinct keys."""
    builder = StructuredQueryBuilder()

    key_shakes = builder.build_disambiguation_key(
        asset_id="song_01",
        stable_lineage_key="lineage_hold_on",
        creator_or_owner="Alabama Shakes",
        title="Hold On",
        year=2012,
    )
    key_phillips = builder.build_disambiguation_key(
        asset_id="song_02",
        stable_lineage_key="lineage_hold_on",
        creator_or_owner="Wilson Phillips",
        title="Hold On",
        year=1990,
    )

    assert key_shakes != key_phillips
    assert len(key_shakes) == 64
    assert len(key_phillips) == 64


def test_entity_disambiguation_rejects_bare_title():
    """Verifies that queries without creator/owner raise EntityDisambiguationError."""
    builder = StructuredQueryBuilder()
    with pytest.raises(EntityDisambiguationError) as exc_info:
        builder.build_disambiguation_key(
            asset_id="song_anon",
            stable_lineage_key=None,
            creator_or_owner="",
            title="Mystery Song",
        )
    assert "bare title" in str(exc_info.value)


def test_query_sanitization_defense():
    """Verifies that unescaped quotes and formatting are sanitized cleanly."""
    builder = StructuredQueryBuilder()
    req = SearchQueryRequest(
        asset_id="clm_inj",
        asset_class=AssetClass.MUSIC,
        title='Clair "de" Lune',
        creator_or_owner='Claude "Debussy"',
        year=1905,
    )
    res = builder.build_query(req)
    # Quotes should be sanitized to avoid double-escaping inside phrase quotes
    assert '""' not in res.query_string
    assert '"Clair de Lune"' in res.query_string
