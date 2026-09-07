"""
Unit and Integration Tests for Screenplay AST Delta & Semantic Diff Engine (delta_engine.py)
Sprint 1.2 Testing Suite for Lienmark.
Exhaustively tests:
1. Screenplay AST parsing across sluglines, action, character cues, dialogue, parentheticals, transitions.
2. Semantic diffing between Revision N and N+1 with ChangeKind classification.
3. Localized bounding box matching: guarantees that non-rights dialogue edits do NOT cause false invalidations
   of unrelated background assets in the same scene.
4. Material creative drift isolation: proves that when an asset is targeted in dialogue, it is invalidated
   while unrelated background assets in the same scene carry forward.
5. Model Containment Guardrail: strictly prevents advisory AST deltas from mutating counsel decisions.
6. Integration contracts with InvalidationEngine and Golden Dataset fixtures.
Authored strictly under Google AntiGravity for Lienmark compliance.
"""

import pytest
from typing import Dict, List

from backend.domain.models import (
    ChangeKind,
    CreativeUse,
    CreativeDelta,
    CounselDecision,
    DecisionState,
    DecisionStatus,
    PublicEvidenceSnapshot,
)
from backend.core.delta_engine import (
    ScreenplayParser,
    ScreenplayDeltaEngine,
    ScreenplayAST,
    SceneNode,
    ASTElementNode,
    ScreenplayElementType,
    SpatialScope,
    InteractionLevel,
    SourceSpan,
    LocalizedBoundingBox,
    ASTDiffKind,
    ASTElementDelta,
    SceneDelta,
    AssetInterferenceResult,
    normalize_scene_number,
)
from backend.core.semantic_delta import ModelContainmentViolation
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import get_golden_fixtures


# =============================================================================
# 1. SCREENPLAY AST PARSER TESTS
# =============================================================================

SAMPLE_SCREENPLAY_V7 = """
SCENE 42 - INT. DETECTIVE OFFICE - NIGHT

Office establishing shot, protagonist enters holding trench coat.
1950s Western Electric Rotary Phone prop on mahogany desk.
Poster hangs on far wall behind detective desk, soft focus.

MILLER
(wearily)
Where was he?

SARAH
Nobody knows. He vanished into the rain.

CUT TO:
"""

SAMPLE_SCREENPLAY_V8_TYPO_ONLY = """
SCENE 42 - INT. DETECTIVE OFFICE - NIGHT

Office establishing shot, protagonist enters holding trench coat.
1950s Western Electric Rotary Phone prop on mahogany desk.
Poster hangs on far wall behind detective desk, soft focus.

MILLER
(wearily)
Where was he that stormy night?

SARAH
Nobody knows. He vanished into the rain.

CUT TO:
"""

SAMPLE_SCREENPLAY_V8_CREATIVE_DRIFT = """
SCENE 42 - INT. DETECTIVE OFFICE - NIGHT

Office establishing shot, protagonist enters holding trench coat.
1950s Western Electric Rotary Phone prop on mahogany desk.

Detective grabs poster off wall, examines the cover art closely and reads:
'Look at this headline: Shadows Over Broadway! They knew everything back in 1946.'

MILLER
(alarmed)
They knew from the beginning.

CUT TO:
"""


def test_screenplay_parser_elements_and_structure():
    """Verify parser extracts scene heading, action, character cue, parenthetical, dialogue, and transition."""
    ast = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V7, version_id="v7", title="Shadows Over Broadway")

    assert ast.version_id == "v7"
    assert len(ast.scenes) == 1

    scene = ast.scenes[0]
    assert normalize_scene_number(scene.scene_number) == "Scene 42"
    assert "INT." in scene.slugline
    assert "DETECTIVE OFFICE" in scene.location
    assert "NIGHT" in scene.time_of_day

    # Verify elements
    elem_types = [e.element_type for e in scene.elements]
    assert ScreenplayElementType.SCENE_HEADING in elem_types
    assert ScreenplayElementType.ACTION in elem_types
    assert ScreenplayElementType.CHARACTER_CUE in elem_types
    assert ScreenplayElementType.DIALOGUE in elem_types
    assert ScreenplayElementType.TRANSITION in elem_types

    # Find dialogue element
    dialogue_elems = [e for e in scene.elements if e.element_type == ScreenplayElementType.DIALOGUE]
    assert len(dialogue_elems) >= 2
    miller_dialogue = dialogue_elems[0]
    assert miller_dialogue.character_name == "MILLER"
    assert "wearily" in miller_dialogue.parentheticals
    assert "Where was he?" in miller_dialogue.content


def test_screenplay_parser_entity_extraction():
    """Verify extraction of known rights entities into EntityMention nodes."""
    ast = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V7, version_id="v7")
    scene = ast.scenes[0]

    mentions = scene.entity_mentions
    keys = [m.normalized_key for m in mentions]

    assert "prop_vintage_telephone" in keys
    assert "poster_noir_detective_magazine" in keys

    # In v7, both are incidental/set dressing
    for m in mentions:
        assert m.interaction_level in (
            InteractionLevel.INCIDENTAL_BACKGROUND,
            InteractionLevel.SET_DRESSING,
        )


# =============================================================================
# 2. LOCALIZED BOUNDING BOX MATCHING (ZERO FALSE INVALIDATION TEST)
# =============================================================================

def test_dialogue_typo_does_not_invalidate_background_assets():
    """
    CRITICAL ACCEPTANCE GATE:
    A minor dialogue edit in non-rights dialogue ('Where was he?' -> 'Where was he that stormy night?')
    MUST NOT invalidate unrelated background assets (telephone, poster) in the same scene.
    """
    ast_v7 = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V7, version_id="v7")
    ast_v8_typo = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V8_TYPO_ONLY, version_id="v8")

    report = ScreenplayDeltaEngine.diff(ast_v7, ast_v8_typo)
    assert len(report.scene_deltas) == 1
    scene_delta = report.scene_deltas[0]

    # Create CreativeUse instances for telephone and poster
    telephone_use = CreativeUse(
        use_id="use_v7_telephone",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="prop",
        description="1950s Western Electric Rotary Phone prop on mahogany desk.",
        duration_or_prominence="Incidental background set dressing, 4s",
        context="Office establishing shot, protagonist enters holding trench coat.",
        stable_lineage_key="prop_vintage_telephone",
        context_hash="a1b2c3d4e5f67890",
    )

    poster_use = CreativeUse(
        use_id="use_v7_poster_noir",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="artwork",
        description="1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
        duration_or_prominence="Out-of-focus background blur, 2s",
        context="Poster hangs on far wall behind detective desk, soft focus.",
        stable_lineage_key="poster_noir_detective_magazine",
        context_hash="b2c3d4e5f6789012",
    )

    # Evaluate interference for telephone
    interf_phone = ScreenplayDeltaEngine.evaluate_asset_interference(telephone_use, scene_delta)
    assert interf_phone.interferes is False
    assert interf_phone.reason_code == "LOCALIZED_BOUNDING_ISOLATED"
    assert "confined to unrelated dialogue" in interf_phone.explanation

    # Evaluate interference for poster
    interf_poster = ScreenplayDeltaEngine.evaluate_asset_interference(poster_use, scene_delta)
    assert interf_poster.interferes is False
    assert interf_poster.reason_code == "LOCALIZED_BOUNDING_ISOLATED"

    # Verify generated creative deltas
    deltas = ScreenplayDeltaEngine.generate_bounded_deltas(
        ast_v7,
        ast_v8_typo,
        base_uses=[telephone_use, poster_use],
        target_uses=[
            telephone_use.model_copy(update={"version_id": "v8", "use_id": "use_v8_telephone"}),
            poster_use.model_copy(update={"version_id": "v8", "use_id": "use_v8_poster"}),
        ],
    )

    assert deltas["prop_vintage_telephone"].change_kind == ChangeKind.UNCHANGED
    assert deltas["prop_vintage_telephone"].reason_codes == ["LOCALIZED_BOUNDING_ISOLATED"]
    assert deltas["poster_noir_detective_magazine"].change_kind == ChangeKind.UNCHANGED
    assert deltas["poster_noir_detective_magazine"].reason_codes == ["LOCALIZED_BOUNDING_ISOLATED"]


# =============================================================================
# 3. SELECTIVE CREATIVE DRIFT ISOLATION (ITEM 11 ISOLATION TEST)
# =============================================================================

def test_selective_creative_drift_isolates_affected_asset_only():
    """
    CRITICAL ACCEPTANCE GATE:
    In V8 Creative Drift, Detective Miller grabs the poster, examines it, and reads headline aloud.
    The engine MUST:
    1. Invalidate poster_noir_detective_magazine as MATERIALLY_MODIFIED (Interference = True).
    2. Carry forward prop_vintage_telephone as UNCHANGED (Interference = False) even though
       both exist in the exact same Scene 42!
    """
    ast_v7 = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V7, version_id="v7")
    ast_v8_drift = ScreenplayParser.parse(SAMPLE_SCREENPLAY_V8_CREATIVE_DRIFT, version_id="v8")

    report = ScreenplayDeltaEngine.diff(ast_v7, ast_v8_drift)
    assert len(report.scene_deltas) == 1
    scene_delta = report.scene_deltas[0]

    telephone_use = CreativeUse(
        use_id="use_v7_telephone",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="prop",
        description="1950s Western Electric Rotary Phone prop on mahogany desk.",
        duration_or_prominence="Incidental background set dressing, 4s",
        context="Office establishing shot, protagonist enters holding trench coat.",
        stable_lineage_key="prop_vintage_telephone",
        context_hash="a1b2c3d4e5f67890",
    )

    poster_use_v7 = CreativeUse(
        use_id="use_v7_poster_noir",
        version_id="v7",
        scene_or_timecode="Scene 42",
        asset_type="artwork",
        description="1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
        duration_or_prominence="Out-of-focus background blur, 2s",
        context="Poster hangs on far wall behind detective desk, soft focus.",
        stable_lineage_key="poster_noir_detective_magazine",
        context_hash="b2c3d4e5f6789012",
    )

    poster_use_v8 = CreativeUse(
        use_id="use_v8_poster_noir",
        version_id="v8",
        scene_or_timecode="Scene 42",
        asset_type="artwork",
        description="1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
        duration_or_prominence="Featured close-up focal shot with dialogue, 14s",
        context="Detective grabs poster off wall, examines the cover art closely and reads: 'Look at this headline: Shadows Over Broadway! They knew everything back in 1946.'",
        stable_lineage_key="poster_noir_detective_magazine",
        context_hash="c3d4e5f678901234",
    )

    # 1. Check telephone: MUST NOT interfere!
    interf_phone = ScreenplayDeltaEngine.evaluate_asset_interference(telephone_use, scene_delta)
    assert interf_phone.interferes is False
    assert interf_phone.reason_code == "LOCALIZED_BOUNDING_ISOLATED"

    # 2. Check poster: MUST interfere!
    interf_poster = ScreenplayDeltaEngine.evaluate_asset_interference(poster_use_v7, scene_delta)
    assert interf_poster.interferes is True
    assert interf_poster.reason_code == "CREATIVE_CONTEXT_ALTERED"
    assert "Direct narrative interaction" in interf_poster.explanation

    # 3. Generate bounded deltas
    deltas = ScreenplayDeltaEngine.generate_bounded_deltas(
        ast_v7,
        ast_v8_drift,
        base_uses=[telephone_use, poster_use_v7],
        target_uses=[
            telephone_use.model_copy(update={"version_id": "v8", "use_id": "use_v8_telephone"}),
            poster_use_v8,
        ],
    )

    # Assert mathematical separation:
    assert deltas["prop_vintage_telephone"].change_kind == ChangeKind.UNCHANGED
    assert deltas["prop_vintage_telephone"].reason_codes == ["LOCALIZED_BOUNDING_ISOLATED"]
    assert deltas["poster_noir_detective_magazine"].change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert deltas["poster_noir_detective_magazine"].is_material is True
    assert "PROMINENCE_ESCALATED" in deltas["poster_noir_detective_magazine"].reason_codes


# =============================================================================
# 4. MODEL CONTAINMENT GUARDRAIL TESTS
# =============================================================================

def test_model_containment_guardrail_prevents_counsel_mutation():
    """Verify that delta_engine adheres to the Model Containment Guardrail."""
    from backend.core.semantic_delta import SemanticDeltaEngine

    # Attempting to validate a CounselDecision through containment raises ModelContainmentViolation
    decision = CounselDecision(
        decision_id="dec_fake",
        use_id="use_fake",
        stable_lineage_key="fake_key",
        applicable_version_id="v8",
        status=DecisionStatus.APPROVED,
        rationale="Unauthorized override attempt",
        reviewer_display_name="Malicious AI",
    )

    with pytest.raises(ModelContainmentViolation):
        SemanticDeltaEngine.enforce_containment_guardrail(decision)

    # Attempting dictionary with forbidden clearance keys
    forbidden_dict = {"v8_evaluation_state": "APPROVED", "is_material": False}
    with pytest.raises(ModelContainmentViolation):
        SemanticDeltaEngine.enforce_containment_guardrail(forbidden_dict)


# =============================================================================
# 5. INTEGRATION WITH INVALIDATION ENGINE
# =============================================================================

def test_invalidation_engine_with_bounded_ast_deltas():
    """
    Verify that InvalidationEngine cleanly consumes bounded deltas and maintains
    the 10 carried forward / 2 stale law.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # Verify that InvalidationEngine evaluates golden fixtures with 10 carried / 2 stale
    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    carried = [v for v in validity_results if v.state == DecisionState.CARRIED_FORWARD]
    stale = [v for v in validity_results if v.state == DecisionState.STALE]

    assert len(carried) == 10
    assert len(stale) == 2

    # Telephone is carried forward
    tel_validity = next(v for v in validity_results if v.stable_lineage_key == "prop_vintage_telephone")
    assert tel_validity.state == DecisionState.CARRIED_FORWARD

    # Poster is stale
    poster_validity = next(v for v in validity_results if v.stable_lineage_key == "poster_noir_detective_magazine")
    assert poster_validity.state == DecisionState.STALE
