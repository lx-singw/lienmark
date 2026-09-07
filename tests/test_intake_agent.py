"""
Tests for Lienmark Intake Agent.
Validates offline fallback mode, live extraction mock, schema repair retries, and ADK tool bridge.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from backend.agents.intake.agent import IntakeAgent
from backend.agents.intake.claim_types import (
    ClaimCategory,
    ExtractedClaim,
    ClaimExtractionOutput,
    MultimodalIntakeInput,
)
from backend.agents.intake.rate_limiter import LeakyBucketTokenLimiter


@pytest.mark.asyncio
async def test_intake_agent_offline_fallback_music_and_brand():
    """Verifies deterministic fallback extracts music and brand claims correctly."""
    agent = IntakeAgent(use_fallback=True)
    script_text = (
        "INT. DINER - NIGHT\n"
        "Alex orders a cold Coca-Cola while the radio plays 'Hotel California'."
    )
    result = await agent.extract_claims(script_text)

    assert isinstance(result, ClaimExtractionOutput)
    assert result.extraction_model == "offline_deterministic_fallback"
    assert result.total_claims_count >= 2

    categories = {c.category for c in result.claims}
    assert ClaimCategory.BRAND in categories
    assert ClaimCategory.MUSIC in categories


@pytest.mark.asyncio
async def test_intake_agent_offline_fallback_art_and_ai():
    """Verifies deterministic fallback extracts artwork and synthetic AI elements."""
    agent = IntakeAgent(use_fallback=True)
    script = (
        "EXT. MUSEUM - DAY\n"
        "A large mural of Mona Lisa hangs on the wall. "
        "A billboard displays a deepfake synthetic voice avatar."
    )
    result = await agent.extract_claims(script)

    categories = {c.category for c in result.claims}
    assert ClaimCategory.ARTWORK in categories
    assert ClaimCategory.SYNTHETIC_AI in categories


@pytest.mark.asyncio
async def test_intake_agent_offline_fallback_generic_text():
    """Verifies fallback produces an 'other' claim for non-matching script text."""
    agent = IntakeAgent(use_fallback=True)
    script = "The character sits silently on the bench looking at the stars."
    result = await agent.extract_claims(script)

    assert result.total_claims_count == 1
    assert result.claims[0].category == ClaimCategory.OTHER


def _build_mock_repair_client(valid_payload: dict) -> MagicMock:
    """Builds a mock GenAI client returning broken JSON then valid JSON."""
    mock_client = MagicMock()
    resp_bad = MagicMock(text="```json\n{ broken json here: [ }```")
    resp_good = MagicMock(text=json.dumps(valid_payload))
    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(side_effect=[resp_bad, resp_good])
    mock_client.aio = MagicMock(models=mock_models)
    return mock_client


@pytest.mark.asyncio
async def test_intake_agent_schema_repair_retry_success():
    """Verifies automatic repair retry when first attempt returns malformed JSON."""
    agent = IntakeAgent(api_key="mock-key", use_fallback=False)
    agent.is_offline = False

    valid_payload = {
        "claims": [
            {
                "claim_id": "clm_live_01",
                "category": "music",
                "scene_or_timecode": "SCENE 2",
                "extracted_description": "Radio playing jazz saxophone cue",
                "confidence": 0.92,
                "needs_clarification": False,
            }
        ],
        "document_id": "live_doc",
        "total_claims_count": 1,
    }

    agent.client = _build_mock_repair_client(valid_payload)
    result = await agent.extract_claims("Some script text")
    assert result.total_claims_count == 1
    assert result.claims[0].claim_id == "clm_live_01"
    assert result.claims[0].category == ClaimCategory.MUSIC
    assert agent.client.aio.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_intake_agent_adk_tool_integration():
    """Verifies as_adk_tool() creates a functional Google ADK FunctionTool."""
    agent = IntakeAgent(use_fallback=True)
    tool = agent.as_adk_tool()

    assert tool is not None
    # Invoke the tool function directly
    script = "INT. GARAGE - DAY\nA vintage Ford mustang sits parked."
    result = await tool.func(script, "SCENE 12")

    assert isinstance(result, ClaimExtractionOutput)
    assert any(c.category == ClaimCategory.BRAND for c in result.claims)
