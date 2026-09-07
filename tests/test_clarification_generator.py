"""
tests/test_clarification_generator.py

Tests for Lienmark Targeted Clarification Generator Subsystem.
Validates benchmark scenarios, deterministic heuristics, and schema validation.
Sprint 4.1: Human-in-the-Loop Clarification State Machine & Checkpoints.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.agents.clarification import (
    ClarificationGenerator,
    ClarificationInput,
    DocumentTypeRequirement,
    ProductionRole,
    TargetedClarification,
)
from backend.domain.models import ClarificationRequest


def test_benchmark_scenario_uncredited_jazz_solo():
    """Benchmark Scenario: Screenplay cue flags uncertainty for Music Supervisor."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        claim_id="clm_scene14_jazz",
        category="music",
        scene_anchor="Scene 14, 00:18:22",
        asset_name_or_cue="uncredited jazz solo",
        context_snippet="an uncredited jazz solo plays in the background of the diner scene",
        flagged_reason="Master recording ownership and synchronization rights are unresolved",
        revision_id="v8",
        stable_lineage_key="lineage_diner_jazz_solo",
    )

    result = generator.generate_clarification_sync(input_data)

    assert isinstance(result, TargetedClarification)
    assert result.claim_id == "clm_scene14_jazz"
    assert result.scene_anchor == "Scene 14, 00:18:22"
    assert "Uncredited jazz solo cue" in result.asset_identity
    assert "Master recording ownership and synchronization rights are unresolved" in result.missing_legal_scope
    assert len(result.suggested_options) >= 3
    assert "Commissioned original score" in result.suggested_options[0]
    assert "Commercial track needing sync clearance" in result.suggested_options[1]
    assert "Library/production music" in result.suggested_options[2]
    assert result.required_document_type == DocumentTypeRequirement.SYNC_LICENSE.value
    assert result.designated_role == ProductionRole.MUSIC_SUPERVISOR.value
    assert "Scene 14, 00:18:22" in result.question_text
    assert "Music Supervisor" in result.question_text


def test_benchmark_scenario_auto_extracted_anchor():
    """Verifies anchor resolution when scene_anchor is not explicitly provided."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        asset_name_or_cue="jazz solo",
        context_snippet="an uncredited jazz solo plays in the background of the diner scene",
    )

    result = generator.generate_clarification_sync(input_data)
    assert result.scene_anchor == "Scene 14, 00:18:22"
    assert result.designated_role == ProductionRole.MUSIC_SUPERVISOR.value


def test_heuristic_brand_trademark():
    """Verifies rule profile matching for brand and trademark claims."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        claim_id="clm_brand_01",
        category="brand",
        scene_anchor="Scene 4, 00:05:10",
        asset_name_or_cue="Coca-Cola vintage neon sign",
        context_snippet="A glowing Coca-Cola sign hangs over the counter",
    )

    result = generator.generate_clarification_sync(input_data)
    assert result.designated_role == ProductionRole.CLEARANCE_COORDINATOR.value
    assert result.required_document_type == DocumentTypeRequirement.TRADEMARK_RELEASE.value
    assert any("product placement" in opt.lower() for opt in result.suggested_options)


def test_heuristic_artwork_vara():
    """Verifies rule profile matching for fine artwork and VARA scope."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        claim_id="clm_art_01",
        category="artwork",
        scene_anchor="Scene 9",
        asset_name_or_cue="Original abstract mural painting",
        context_snippet="A large abstract mural adorns the restaurant wall",
    )

    result = generator.generate_clarification_sync(input_data)
    assert result.designated_role == ProductionRole.CLEARANCE_COORDINATOR.value
    assert result.required_document_type == DocumentTypeRequirement.ARTIST_WORK_FOR_HIRE.value
    assert "VARA" in result.missing_legal_scope


def test_heuristic_archival_footage():
    """Verifies rule profile matching for archival footage."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        claim_id="clm_footage_01",
        category="footage",
        scene_anchor="Scene 2, 00:01:45",
        asset_name_or_cue="Apollo 11 broadcast newsreel clip",
        context_snippet="A TV monitor shows Apollo 11 moonwalk newsreel",
    )

    result = generator.generate_clarification_sync(input_data)
    assert result.designated_role == ProductionRole.ARCHIVAL_PRODUCER.value
    assert result.required_document_type == DocumentTypeRequirement.ARCHIVAL_FOOTAGE_LICENSE.value


def test_heuristic_unspecified_fallback():
    """Verifies fallback profile when asset does not match known categories."""
    generator = ClarificationGenerator(use_fallback=True)

    input_data = ClarificationInput(
        claim_id="clm_misc_01",
        category="other",
        scene_anchor="Scene 30",
        asset_name_or_cue="Custom prototype anti-gravity propulsion device",
    )

    result = generator.generate_clarification_sync(input_data)
    assert result.designated_role == ProductionRole.CLEARANCE_COUNSEL.value
    assert result.required_document_type == DocumentTypeRequirement.CUSTOM_CLEARANCE_DOC.value


@pytest.mark.asyncio
async def test_async_generate_clarification_offline():
    """Verifies asynchronous generation in offline mode."""
    generator = ClarificationGenerator(use_fallback=True)

    result = await generator.generate_clarification({
        "claim_id": "clm_async_01",
        "asset_name_or_cue": "Radio rock ballad cue",
        "scene_anchor": "Scene 1",
    })

    assert isinstance(result, TargetedClarification)
    assert result.claim_id == "clm_async_01"
    assert result.designated_role == ProductionRole.MUSIC_SUPERVISOR.value


def test_targeted_clarification_validation_and_conversion():
    """Verifies Pydantic v2 validation rules and conversion to domain ClarificationRequest."""
    with pytest.raises(ValidationError):
        TargetedClarification(
            claim_id="clm_invalid",
            scene_anchor="Scene 1",
            asset_identity="Asset",
            ambiguous_attribute="Attr",
            missing_legal_scope="Scope",
            suggested_options=["Only one option"],
            required_document_type="Doc",
            designated_role="Role",
            question_text="Question",
            stable_lineage_key="lineage_key",
        )

    valid_clarification = TargetedClarification(
        request_id="clrf_test_123",
        claim_id="clm_valid_01",
        scene_anchor="Scene 14, 00:18:22",
        asset_identity="Uncredited jazz solo cue",
        ambiguous_attribute="Master recording ownership unresolved",
        missing_legal_scope="Master rights unresolved",
        suggested_options=["Option A", "Option B"],
        required_document_type="Executed Synchronization License",
        designated_role="Music Supervisor",
        question_text="Targeted legal question text",
        stable_lineage_key="lineage_jazz_01",
    )

    domain_req = valid_clarification.to_domain_request(run_id="run_test_99")
    assert isinstance(domain_req, ClarificationRequest)
    assert domain_req.request_id == "clrf_test_123"
    assert domain_req.run_id == "run_test_99"
    assert domain_req.claim_id == "clm_valid_01"
    assert domain_req.assigned_role == "Music Supervisor"
    assert domain_req.suggested_options == ["Option A", "Option B"]
