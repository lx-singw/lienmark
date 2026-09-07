"""
tests/test_clarification_genai_live.py

Tests for live GenAI integration, repair retries, batch generation, and modularity.
Sprint 4.1: Human-in-the-Loop Clarification State Machine & Checkpoints.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.agents.clarification import (
    ClarificationGenerator,
    ClarificationInput,
    ClarificationOutput,
    TargetedClarification,
)


def _get_sample_genai_payload() -> dict:
    """Helper returning a canonical valid GenAI response payload."""
    return {
        "request_id": "clrf_genai_01",
        "claim_id": "clm_genai_01",
        "scene_anchor": "Scene 14, 00:18:22",
        "asset_identity": "Uncredited jazz solo cue playing in the background diner",
        "ambiguous_attribute": "Master recording ownership and synchronization rights are unresolved",
        "missing_legal_scope": "Master recording ownership and synchronization rights are unresolved",
        "suggested_options": [
            "Commissioned original score",
            "Commercial track needing sync clearance",
            "Library/production music (e.g. APM/Extreme)",
        ],
        "required_document_type": "Executed Synchronization License",
        "designated_role": "Music Supervisor",
        "question_text": "Regarding the uncredited jazz solo in Scene 14: Please confirm rights.",
        "urgency": "high",
        "status": "pending",
        "revision_id": "v8",
        "stable_lineage_key": "lineage_diner_jazz",
    }


@pytest.mark.asyncio
async def test_live_genai_mock_and_repair_retry():
    """Verifies live Google GenAI path, schema parsing, and repair retry logic."""
    payload = _get_sample_genai_payload()
    bad_resp = MagicMock(text="```json\n{ broken json: [ }```")
    good_resp = MagicMock(text=json.dumps(payload))
    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(side_effect=[bad_resp, good_resp])

    mock_client = MagicMock()
    mock_client.aio = MagicMock(models=mock_models)

    generator = ClarificationGenerator(api_key="valid-key-for-test", use_fallback=False)
    generator.is_offline = False
    generator.client = mock_client

    inp = ClarificationInput(
        claim_id="clm_genai_01",
        asset_name_or_cue="uncredited jazz solo",
        scene_anchor="Scene 14, 00:18:22",
    )
    result = await generator.generate_clarification(inp)

    assert isinstance(result, TargetedClarification)
    assert result.claim_id == "clm_genai_01"
    assert result.designated_role == "Music Supervisor"
    assert mock_models.generate_content.await_count == 2


@pytest.mark.asyncio
async def test_batch_generation_sync_and_async():
    """Verifies batch generation envelopes for both sync and async calls."""
    generator = ClarificationGenerator(use_fallback=True)
    items = [
        ClarificationInput(asset_name_or_cue="jazz solo in diner", scene_anchor="Scene 14"),
        ClarificationInput(asset_name_or_cue="Coca-Cola bottle", scene_anchor="Scene 5"),
    ]

    batch_sync = generator.generate_batch_sync(items)
    assert isinstance(batch_sync, ClarificationOutput)
    assert batch_sync.total_count == 2
    assert batch_sync.generation_mode == "rule_based_fallback"

    batch_async = await generator.generate_batch(items)
    assert isinstance(batch_async, ClarificationOutput)
    assert batch_async.total_count == 2


def test_file_size_and_modularity_constraints():
    """Enforces architecture constraint: all clarification files must be <= 250 lines."""
    clarification_dir = Path("backend/agents/clarification")
    assert clarification_dir.exists()

    py_files = list(clarification_dir.glob("*.py"))
    assert len(py_files) >= 4

    for py_file in py_files:
        lines = py_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 250, f"{py_file.name} exceeds 250 lines ({len(lines)} lines)"
