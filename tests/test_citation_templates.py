"""
tests/test_citation_templates.py

Exhaustive verification suite for Attorney Citation Suggestion Engine.
Sprint 4.3 - Validates templates, asset types, variable substitution, and ranking.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from pydantic import ValidationError

from backend.services.citation_templates import (
    CitationCategory,
    CitationSuggestionEngine,
    LegalCitationTemplate,
)


def test_citation_categories_enum():
    """Verify all 6 mandated CitationCategory enum members exist with correct values."""
    expected = {
        "FAIR_USE_107", "PUBLIC_DOMAIN_304", "RINGGOLD_DE_MINIMIS",
        "SYNC_WARRANTY", "MASTER_WARRANTY", "TRADEMARK_NOMINATIVE",
    }
    actual = {c.value for c in CitationCategory}
    assert actual == expected


def test_default_templates_integrity():
    """Verify exact legally vetted citation texts and statutes for all 6 templates."""
    engine = CitationSuggestionEngine()
    templates = {t.category: t for t in engine.get_templates()}
    assert len(templates) == 6
    assert all(isinstance(t, LegalCitationTemplate) for t in templates.values())

    # 17 U.S.C. § 107 Fair Use
    fu = templates[CitationCategory.FAIR_USE_107]
    assert "Use is transformative under 17 U.S.C. § 107" in fu.template_text
    assert "zero market substitution" in fu.template_text

    # 17 U.S.C. § 304 Public Domain
    pd = templates[CitationCategory.PUBLIC_DOMAIN_304]
    assert "Work published prior to 1931" in pd.template_text
    assert "17 U.S.C. § 304" in pd.template_text

    # Ringgold De Minimis
    rm = templates[CitationCategory.RINGGOLD_DE_MINIMIS]
    assert "Ringgold v. Black Entertainment Television (126 F.3d 70)" in rm.template_text
    assert "duration < 3 seconds, out of focus and fleeting" in rm.template_text

    # Synchronized Music Warranty
    sw = templates[CitationCategory.SYNC_WARRANTY]
    assert "Executed Synchronization License dated [DATE]" in sw.template_text
    assert "worldwide perpetual exploitation in all media" in sw.template_text

    # Master Use License Warranty
    mw = templates[CitationCategory.MASTER_WARRANTY]
    assert "Master Use Agreement dated [DATE] from [LABEL]" in mw.template_text

    # Trademark Nominative Fair Use
    tn = templates[CitationCategory.TRADEMARK_NOMINATIVE]
    assert "New Kids on the Block v. News America (971 F.2d 302)" in tn.template_text
    assert "solely to identify the product without implying endorsement" in tn.template_text


def test_template_variable_substitution():
    """Verify placeholder substitution for bracketed and curly-brace variables."""
    engine = CitationSuggestionEngine()
    sync_tmpl = engine.get_template(CitationCategory.SYNC_WARRANTY)
    assert sync_tmpl is not None

    populated = sync_tmpl.substitute({
        "DATE": "2026-06-15",
        "LICENSOR": "Universal Music Publishing",
        "LICENSEE": "Lienmark Productions Inc.",
    })
    assert "[DATE]" not in populated.template_text
    assert "dated 2026-06-15" in populated.template_text
    assert "between Universal Music Publishing and Lienmark Productions Inc." in populated.template_text

    # Format citation helper method
    master_tmpl = engine.get_template(CitationCategory.MASTER_WARRANTY)
    formatted = master_tmpl.format_citation(date="2026-08-01", label="Sony Masterworks")
    assert "dated 2026-08-01 from Sony Masterworks" in formatted


def test_template_immutability():
    """Verify LegalCitationTemplate is frozen to prevent accidental state mutation."""
    engine = CitationSuggestionEngine()
    tmpl = engine.get_template(CitationCategory.FAIR_USE_107)
    assert tmpl is not None
    with pytest.raises(ValidationError):
        tmpl.template_text = "Mutated text"


def test_suggest_citations_music_asset_type():
    """Verify music claims return sync and master warranties ranked top."""
    engine = CitationSuggestionEngine()
    suggestions = engine.suggest_citations(claim_type="music")
    assert len(suggestions) >= 2
    cats = [s.category for s in suggestions]
    assert CitationCategory.SYNC_WARRANTY in cats
    assert CitationCategory.MASTER_WARRANTY in cats
    # Verify descending confidence sorting
    confs = [s.confidence_weight for s in suggestions]
    assert confs == sorted(confs, reverse=True)


def test_suggest_citations_artwork_asset_type():
    """Verify artwork claims prioritize Ringgold de minimis, public domain, and fair use."""
    engine = CitationSuggestionEngine()
    suggestions = engine.suggest_citations(claim_type="artwork")
    cats = [s.category for s in suggestions]
    assert CitationCategory.RINGGOLD_DE_MINIMIS in cats
    assert CitationCategory.PUBLIC_DOMAIN_304 in cats
    assert CitationCategory.FAIR_USE_107 in cats
    assert CitationCategory.SYNC_WARRANTY not in cats


def test_suggest_citations_brand_and_trademark():
    """Verify brand/trademark claims return nominative fair use as top suggestion."""
    engine = CitationSuggestionEngine()
    for brand_type in ("brand", "trademark", "logo"):
        suggestions = engine.suggest_citations(claim_type=brand_type)
        assert suggestions[0].category == CitationCategory.TRADEMARK_NOMINATIVE


def test_suggest_citations_footage_and_historical():
    """Verify footage and historical figure claims map to appropriate citations."""
    engine = CitationSuggestionEngine()
    footage_suggs = engine.suggest_citations(claim_type="footage")
    f_cats = [s.category for s in footage_suggs]
    assert CitationCategory.FAIR_USE_107 in f_cats
    assert CitationCategory.PUBLIC_DOMAIN_304 in f_cats

    hist_suggs = engine.suggest_citations(claim_type="historical_figure")
    h_cats = [s.category for s in hist_suggs]
    assert CitationCategory.PUBLIC_DOMAIN_304 in h_cats
    assert CitationCategory.FAIR_USE_107 in h_cats


def test_evidence_keyword_ranking_boost():
    """Verify that specific evidence findings boost the matching citation to rank #1."""
    engine = CitationSuggestionEngine()

    # De minimis evidence on artwork
    art_evidence = ["Visible for 1.8 seconds in background", "blurred and out of focus"]
    art_suggs = engine.suggest_citations("artwork", evidence_findings=art_evidence)
    assert art_suggs[0].category == CitationCategory.RINGGOLD_DE_MINIMIS
    assert art_suggs[0].confidence_weight >= 0.90

    # Public domain evidence on artwork
    pd_evidence = ["Archival photograph published pre-1931 in 1912", "expired copyright"]
    pd_suggs = engine.suggest_citations("artwork", evidence_findings=pd_evidence)
    assert pd_suggs[0].category == CitationCategory.PUBLIC_DOMAIN_304

    # Transformative evidence on footage
    fu_evidence = ["Documentary commentary", "highly transformative purpose"]
    fu_suggs = engine.suggest_citations("footage", evidence_findings=fu_evidence)
    assert fu_suggs[0].category == CitationCategory.FAIR_USE_107


def test_evidence_auto_variable_substitution():
    """Verify structured dictionary findings automatically populate citation placeholders."""
    engine = CitationSuggestionEngine()
    evidence = [{
        "date": "2026-05-20",
        "licensor": "Warner Chappell Music",
        "licensee": "Lienmark Studios",
        "note": "Synchronization rights secured",
    }]
    results = engine.suggest_citations("music", evidence_findings=evidence)
    sync_result = next(r for r in results if r.category == CitationCategory.SYNC_WARRANTY)
    assert "dated 2026-05-20" in sync_result.template_text
    assert "between Warner Chappell Music and Lienmark Studios" in sync_result.template_text
    assert "[DATE]" not in sync_result.template_text


def test_jurisdiction_filtering():
    """Verify non-US jurisdiction penalizes US statutory citations while preserving contracts."""
    engine = CitationSuggestionEngine()
    us_results = engine.suggest_citations("music", jurisdiction="US")
    uk_results = engine.suggest_citations("music", jurisdiction="UK")

    us_fu = next(r for r in us_results if r.category == CitationCategory.FAIR_USE_107)
    uk_fu = next(r for r in uk_results if r.category == CitationCategory.FAIR_USE_107)
    # UK should have lower confidence for US Fair Use statute
    assert uk_fu.confidence_weight < us_fu.confidence_weight

    # Worldwide contractual sync warranty retains high confidence in UK
    uk_sync = next(r for r in uk_results if r.category == CitationCategory.SYNC_WARRANTY)
    assert uk_sync.confidence_weight >= 0.85
    assert uk_results[0].category in (CitationCategory.SYNC_WARRANTY, CitationCategory.MASTER_WARRANTY)


def test_engine_retrieval_and_fallback():
    """Verify get_template lookups by ID and category, plus fallback behavior."""
    engine = CitationSuggestionEngine()
    assert engine.get_template("cit_fair_use_107") is not None
    assert engine.get_template(CitationCategory.RINGGOLD_DE_MINIMIS) is not None
    assert engine.get_template("non_existent_id") is None

    # Unknown claim type falls back gracefully
    unknown_suggs = engine.suggest_citations("alien_broadcast_signal")
    assert len(unknown_suggs) > 0
