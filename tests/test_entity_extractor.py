"""
tests/test_entity_extractor.py

Automated test suite for EntityExtractor, signal classifiers, and catalog matching.
Sprint 3.2: Snippet Entity & Lead Extractor Specialist.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from backend.agents.research.entity_extractor import EntityExtractor
from backend.agents.research.lead_types import (
    ExtractedLead,
    LeadEntityType,
    LeadRelationshipType,
)
from backend.services.parallel_types import DomainAuthorityTier, ParallelSearchFinding


def test_publisher_and_corporate_parent_extraction():
    """Verifies extraction of major music publishers and corporate parents."""
    extractor = EntityExtractor()
    text = (
        "The track is published by Universal Music Publishing Group and administered by Sony Music Publishing. "
        "Catalog owned by Concord Music, a division of Sony Music."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_pub_01")
    entity_names = {l.entity_name for l in leads}
    assert "Universal Music Publishing Group" in entity_names
    assert "Sony Music Publishing" in entity_names
    assert "Concord Music" in entity_names

    pub_lead = next(l for l in leads if l.entity_name == "Universal Music Publishing Group")
    assert pub_lead.relationship_type == LeadRelationshipType.PUBLISHED_BY
    assert pub_lead.entity_type == LeadEntityType.PUBLISHER
    assert "music publishing" in pub_lead.proposed_query_extension


def test_record_label_and_master_rights_extraction():
    """Verifies extraction of record labels under courtesy_of and licensed_to signals."""
    extractor = EntityExtractor()
    text = (
        "Master recording courtesy of Columbia Records. "
        "Sound recording released under exclusive license to Atlantic Records."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_lbl_01")
    labels = {l.entity_name: l for l in leads}
    assert "Columbia Records" in labels
    assert "Atlantic Records" in labels

    columbia = labels["Columbia Records"]
    assert columbia.relationship_type == LeadRelationshipType.COURTESY_OF
    assert columbia.entity_type == LeadEntityType.LABEL
    assert "master recording" in columbia.proposed_query_extension

    atlantic = labels["Atlantic Records"]
    assert atlantic.relationship_type == LeadRelationshipType.LICENSED_TO
    assert atlantic.entity_type == LeadEntityType.LABEL


def test_estate_and_trust_extraction():
    """Verifies extraction of estates and living trusts."""
    extractor = EntityExtractor()
    text = (
        "Clearance requested by the Estate of Jimi Hendrix. "
        "Publishing assets transferred to The Marvin Gaye Family Trust. "
        "Likeness controlled by Miles Davis Living Trust."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_est_01")
    entities = {l.entity_name: l for l in leads}
    assert "Estate of Jimi Hendrix" in entities
    assert any("Marvin Gaye" in k for k in entities)
    assert any("Miles Davis" in k for k in entities)

    hendrix = entities["Estate of Jimi Hendrix"]
    assert hendrix.entity_type == LeadEntityType.ESTATE
    assert hendrix.relationship_type == LeadRelationshipType.ESTATE_ADMINISTERED
    assert "estate representative" in hendrix.proposed_query_extension


def test_trademark_assignee_extraction():
    """Verifies modern trademark assignment and registrant signals."""
    extractor = EntityExtractor()
    text = (
        "Modern USPTO record: mark assigned to Lienmark Cinema Technologies. "
        "Trademark registrant: Starlight Global Media LLC."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_tm_01")
    entities = {l.entity_name: l for l in leads}
    assert any("Lienmark Cinema Technologies" in k for k in entities)

    assignee = next(l for l in leads if "Lienmark" in l.entity_name)
    assert assignee.entity_type == LeadEntityType.ASSIGNEE
    assert assignee.relationship_type == LeadRelationshipType.TRADEMARK_ASSIGNED
    assert "trademark assignment owner USPTO" in assignee.proposed_query_extension


def test_false_lead_rejection():
    """Ensures recording studios and generic platforms are filtered out."""
    extractor = EntityExtractor()
    text = (
        "Master recorded at Abbey Road Studios, sound recording courtesy of Decca Records. "
        "Sponsored by Red Bull and distributed on Spotify."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_filter_01")
    entity_names = {l.entity_name.lower() for l in leads}
    assert "abbey road studios" not in entity_names
    assert "red bull" not in entity_names
    assert "spotify" not in entity_names
    assert "decca records" in entity_names


def test_lead_deduplication_and_deterministic_id():
    """Verifies duplicate leads across sentences retain highest confidence and deterministic id."""
    extractor = EntityExtractor()
    text = (
        "Published by Warner Chappell Music in North America. "
        "The entire catalog is published by Warner Chappell Music internationally."
    )
    leads = extractor.extract_leads_from_text(text, parent_finding_id="find_dedup_01")
    warner_leads = [l for l in leads if l.entity_name == "Warner Chappell Music"]
    assert len(warner_leads) == 1
    lead = warner_leads[0]
    expected_id = EntityExtractor.compute_lead_id("find_dedup_01", "Warner Chappell Music", LeadRelationshipType.PUBLISHED_BY)
    assert lead.lead_id == expected_id
    assert lead.confidence_score >= 0.80


def test_extract_leads_from_findings():
    """Verifies processing of multiple ParallelSearchFinding objects."""
    extractor = EntityExtractor()
    finding1 = ParallelSearchFinding(
        url="https://repertoire.bmi.com/song/123",
        title="BMI Song Repertoire",
        domain="bmi.com",
        full_excerpt="Administered by Kobalt Music Group for worldwide territories.",
        authority_tier=DomainAuthorityTier.TIER_1_GOVERNMENT,
        authority_score=0.95,
        confidence_score=0.90,
    )
    finding2 = ParallelSearchFinding(
        url="https://discogs.com/release/456",
        title="Vinyl Release Details",
        domain="discogs.com",
        excerpts=["Master recording courtesy of Verve Records."],
        authority_tier=DomainAuthorityTier.TIER_2_RIGHTS_ORG,
        authority_score=0.70,
        confidence_score=0.75,
    )
    leads = extractor.extract_leads_from_findings([finding1, finding2])
    entities = {l.entity_name for l in leads}
    assert "Kobalt Music Group" in entities
    assert "Verve Records" in entities


@pytest.mark.asyncio
async def test_llm_fallback_invoked_when_regex_finds_zero():
    """Verifies LLM fallback is triggered if regex yields no leads and fallback is enabled."""
    mock_llm = AsyncMock()
    mock_llm.generate_json.return_value = [
        {
            "entity_name": "Bespoke Independent Music Rights",
            "entity_type": "publisher",
            "relationship_type": "published_by",
            "confidence_score": 0.81,
            "source_sentence": "Non-standard phrasing with bespoke ownership indication.",
        }
    ]
    extractor = EntityExtractor(use_llm_fallback=True, llm_service=mock_llm)
    leads = await extractor.aextract_leads_from_text(
        "Non-standard phrasing with bespoke ownership indication.",
        parent_finding_id="find_llm_01",
    )
    assert len(leads) == 1
    assert leads[0].entity_name == "Bespoke Independent Music Rights"
    assert leads[0].metadata.get("source") == "llm_fallback"
    mock_llm.generate_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_fallback_graceful_error_handling():
    """Verifies extractor gracefully handles LLM failure without crashing."""
    mock_llm = AsyncMock()
    mock_llm.generate_json.side_effect = RuntimeError("API connection timeout")
    extractor = EntityExtractor(use_llm_fallback=True, llm_service=mock_llm)
    leads = await extractor.aextract_leads_from_text(
        "Unparseable gibberish with no identifiable entities.",
        parent_finding_id="find_err_01",
    )
    assert leads == []
