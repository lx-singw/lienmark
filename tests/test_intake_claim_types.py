"""
Tests for Lienmark Multimodal Intake Domain Types.
Validates Pydantic v2 schemas, word count constraints, enums, and bounds.
"""

import pytest
from pydantic import ValidationError

from backend.agents.intake.claim_types import (
    ClaimCategory,
    ExtractedClaim,
    ClaimExtractionOutput,
    MultimodalIntakeInput,
    IntakeExtractionError,
    SchemaValidationRetryExhaustedError,
    RateLimitExceededError,
)


def test_claim_category_enum_values():
    """Verifies all 8 required clearance categories are present."""
    expected = {
        "music",
        "brand",
        "artwork",
        "footage",
        "historical_figure",
        "real_person",
        "synthetic_ai",
        "other",
    }
    actual = {cat.value for cat in ClaimCategory}
    assert actual == expected


def test_extracted_claim_valid_creation():
    """Verifies successful creation of a compliant ExtractedClaim."""
    claim = ExtractedClaim(
        claim_id="clm_001",
        category=ClaimCategory.MUSIC,
        scene_or_timecode="SCENE 4",
        extracted_description="Jukebox playing vintage rock ballad",
        context_snippet="A neon jukebox hums softly in the corner",
        confidence=0.95,
        needs_clarification=False,
    )
    assert claim.claim_id == "clm_001"
    assert claim.category == ClaimCategory.MUSIC
    assert claim.confidence == 0.95
    assert not claim.needs_clarification


def test_extracted_claim_word_count_normalization():
    """Verifies that descriptions exceeding 20 words are truncated to 20 words."""
    long_desc = " ".join([f"word{i}" for i in range(30)])
    claim = ExtractedClaim(
        claim_id="clm_002",
        category=ClaimCategory.BRAND,
        scene_or_timecode="00:12:30",
        extracted_description=long_desc,
        confidence=0.8,
    )
    words = claim.extracted_description.split()
    assert len(words) == 20
    assert words[0] == "word0"
    assert words[19] == "word19"


def test_extracted_claim_confidence_bounds():
    """Verifies that confidence must be between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        ExtractedClaim(
            claim_id="clm_err",
            category=ClaimCategory.ARTWORK,
            scene_or_timecode="SCENE 1",
            extracted_description="Painting",
            confidence=1.5,
        )

    with pytest.raises(ValidationError):
        ExtractedClaim(
            claim_id="clm_err2",
            category=ClaimCategory.ARTWORK,
            scene_or_timecode="SCENE 1",
            extracted_description="Painting",
            confidence=-0.1,
        )


def test_claim_extraction_output_envelope():
    """Verifies envelope serialization and defaults."""
    output = ClaimExtractionOutput(
        document_id="script_v8",
        extraction_model="gemini-2.5-flash",
    )
    assert output.claims == []
    assert output.total_claims_count == 0

    claim = ExtractedClaim(
        claim_id="clm_f01",
        category=ClaimCategory.FOOTAGE,
        scene_or_timecode="SCENE 10",
        extracted_description="Apollo 11 archival television transmission",
    )
    output.claims.append(claim)
    output.total_claims_count = 1

    dumped = output.model_dump()
    assert len(dumped["claims"]) == 1
    assert dumped["claims"][0]["category"] == "footage"


def test_multimodal_intake_input_defaults():
    """Verifies MultimodalIntakeInput default values."""
    inp = MultimodalIntakeInput(content="INT. DINER - NIGHT")
    assert inp.content == "INT. DINER - NIGHT"
    assert inp.media_type == "text/plain"
    assert inp.media_bytes is None
    assert inp.media_uri is None


def test_domain_exception_hierarchy():
    """Verifies custom domain exceptions inherit from IntakeExtractionError."""
    assert issubclass(SchemaValidationRetryExhaustedError, IntakeExtractionError)
    assert issubclass(RateLimitExceededError, IntakeExtractionError)
