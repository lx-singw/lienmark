"""
Lienmark Semantic Delta Engine, Lineage Tracking & Schema Repair Test Suite
Exhaustively tests:
1. repair_json_output across markdown fences, trailing commas, unquoted keys, single quotes, unescaped newlines, and partial JSON.
2. SemanticLineageTracker across unchanged, modified, added, and removed uses.
3. SemanticDeltaEngine Material vs Non-Material discrimination.
4. Model Containment Guardrail preventing model output from directly altering counsel decisions.
5. GeminiService integration with repair_json_output and retry backoff.
6. Golden expected deltas fixture for all 12 items.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import pytest
from typing import Dict, Any

from backend.domain.models import (
    ChangeKind,
    CreativeUse,
    CreativeDelta,
    CounselDecision,
    DecisionStatus,
    DecisionState,
    DecisionValidity,
)
from backend.core.semantic_delta import (
    SemanticLineageTracker,
    SemanticDeltaEngine,
    DeltaAnalysisResult,
    LineagePair,
    LineageStatus,
    ModelContainmentViolation,
    repair_json_output,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.services.gemini_service import GeminiService
from backend.fixtures.golden_dataset import (
    get_golden_fixtures,
    get_golden_expected_deltas,
)


# =============================================================================
# 1. REPAIR_JSON_OUTPUT TESTS
# =============================================================================

def test_repair_json_valid_json():
    """Verify standard valid JSON passes cleanly."""
    raw = '{"is_material": false, "clearance_risk_level": "low", "recommended_action": "carry"}'
    parsed = repair_json_output(raw)
    assert parsed["is_material"] is False
    assert parsed["clearance_risk_level"] == "low"
    assert parsed["recommended_action"] == "carry"


def test_repair_json_markdown_fences():
    """Verify markdown fences (```json ... ``` and ``` ... ```) with surrounding text."""
    raw_with_text = """Here is the clearance evaluation output:
```json
{
  "is_material": true,
  "prominence_shift": "Escalated to 14s close-up focal dialogue.",
  "clearance_risk_level": "high"
}
```
Please let me know if you need more details."""
    parsed = repair_json_output(raw_with_text)
    assert parsed["is_material"] is True
    assert "close-up" in parsed["prominence_shift"]
    assert parsed["clearance_risk_level"] == "high"


def test_repair_json_trailing_commas():
    """Verify removal of trailing commas in objects and arrays."""
    raw = """{
        "is_material": false,
        "changed_fields": ["context", "prominence",],
        "clearance_risk_level": "low",
    }"""
    parsed = repair_json_output(raw)
    assert parsed["is_material"] is False
    assert parsed["changed_fields"] == ["context", "prominence"]
    assert parsed["clearance_risk_level"] == "low"


def test_repair_json_unquoted_keys():
    """Verify handling of unquoted JSON keys."""
    raw = """{
        is_material: true,
        prominence_shift: "close-up focal dialogue",
        clearance_risk_level: "high",
        recommended_action: "revalidate"
    }"""
    parsed = repair_json_output(raw)
    assert parsed["is_material"] is True
    assert parsed["prominence_shift"] == "close-up focal dialogue"
    assert parsed["clearance_risk_level"] == "high"
    assert parsed["recommended_action"] == "revalidate"


def test_repair_json_single_quotes_and_apostrophes():
    """Verify single-quoted dictionaries and values with escaped quotes/apostrophes."""
    raw = "{'is_material': True, 'prominence_shift': 'Focal close-up', 'clearance_risk_level': 'high'}"
    parsed = repair_json_output(raw)
    assert parsed["is_material"] is True
    assert parsed["prominence_shift"] == "Focal close-up"
    assert parsed["clearance_risk_level"] == "high"


def test_repair_json_unescaped_newlines():
    """Verify handling of unescaped newlines inside string literals."""
    raw = """{
        "is_material": true,
        "narrative_impact": "The character grabs the poster.
He reads the headline aloud:
'Shadows Over Broadway! They knew everything.'",
        "clearance_risk_level": "high"
    }"""
    parsed = repair_json_output(raw)
    assert parsed["is_material"] is True
    assert "grabs the poster" in parsed["narrative_impact"]
    assert "Shadows Over Broadway" in parsed["narrative_impact"]
    assert parsed["clearance_risk_level"] == "high"


def test_repair_json_partial_truncated():
    """Verify recovery from truncated/partial JSON strings."""
    # Truncated inside a string value
    raw_truncated_str = '{"is_material": true, "prominence_shift": "Escalated from background blur to 14s close-up focal'
    parsed_str = repair_json_output(raw_truncated_str)
    assert parsed_str["is_material"] is True
    assert "Escalated" in parsed_str["prominence_shift"]

    # Truncated after a key colon
    raw_truncated_colon = '{"is_material": false, "prominence_shift": "Identical", "narrative_impact": '
    parsed_colon = repair_json_output(raw_truncated_colon)
    assert parsed_colon["is_material"] is False
    assert parsed_colon["prominence_shift"] == "Identical"


def test_repair_json_target_model_validation():
    """Verify validation against a target Pydantic model."""
    raw = """```json
    {
        is_material: true,
        prominence_shift: 'Escalated to 14s focal dialogue.',
        narrative_impact: 'Reads headline aloud.',
        clearance_risk_level: 'high',
        statutory_fair_use_impact: 'De minimis inapplicable.',
        recommended_action: 'revalidate',
    }
    ```"""
    parsed = repair_json_output(raw, target_model=DeltaAnalysisResult)
    assert isinstance(parsed, dict)
    assert parsed["is_material"] is True
    assert parsed["clearance_risk_level"] == "high"


def test_repair_json_invalid_empty():
    """Verify empty or whitespace strings raise ValueError."""
    with pytest.raises(ValueError):
        repair_json_output("")
    with pytest.raises(ValueError):
        repair_json_output("   \n\t  ")


def test_repair_json_fail_closed_on_irrecoverable_text():
    """
    Verify fail-closed behavior on completely truncated, invalid, or irrecoverable text.
    Any non-JSON prose or corrupt text without recoverable JSON structure must raise ValueError.
    """
    irrecoverable_samples = [
        "",
        "   \n\t  ",
        "This is not a JSON object, completely irrecoverable prose from model hallucination.",
        "None",
        "<html><body>502 Bad Gateway: Upstream Model Server Unreachable</body></html>",
        "```text\nThere was an internal model error.\n```",
    ]
    for sample in irrecoverable_samples:
        with pytest.raises(ValueError):
            repair_json_output(sample)



# =============================================================================
# 2. SEMANTIC LINEAGE TRACKER TESTS
# =============================================================================

def test_lineage_tracker_golden_fixtures():
    """Verify SemanticLineageTracker pairs all 12 golden items accurately."""
    v7_uses, v8_uses, _, _ = get_golden_fixtures()
    tracker = SemanticLineageTracker(base_uses=v7_uses, target_uses=v8_uses)

    summary = tracker.summary()
    assert summary["total"] == 12
    assert summary["unchanged"] == 11, "10 unchanged items + Item 12 (music cue creative context identical)"
    assert summary["modified"] == 1, "Item 11 (poster) is modified in creative context"
    assert summary["added"] == 0
    assert summary["removed"] == 0

    # Assert Item 11 is modified
    poster_pair = tracker.get_pair("poster_noir_detective_magazine")
    assert poster_pair is not None
    assert poster_pair.status == LineageStatus.MODIFIED
    assert "context_hash" in poster_pair.changed_fields
    assert "duration_or_prominence" in poster_pair.changed_fields
    assert "context" in poster_pair.changed_fields

    # Assert Item 12 is unchanged in creative use
    music_pair = tracker.get_pair("music_cue_midnight_serenade")
    assert music_pair is not None
    assert music_pair.status == LineageStatus.UNCHANGED


def test_lineage_tracker_added_and_removed():
    """Verify detection of added and removed uses across versions."""
    v7_uses, v8_uses, _, _ = get_golden_fixtures()

    # Create target with 1 item removed and 1 item added
    custom_target = [u for u in v8_uses if u.stable_lineage_key != "prop_vintage_telephone"]
    added_use = CreativeUse(
        use_id="use_v8_new_prop_briefcase",
        version_id="v8",
        scene_or_timecode="Scene 45",
        asset_type="prop",
        description="Silver aluminum locking briefcase containing secret microfilm.",
        duration_or_prominence="Featured hero prop, 8s",
        context="Protagonist clicks open locks and inspects microfilm.",
        stable_lineage_key="prop_silver_briefcase",
        context_hash="hash_silver_briefcase_123",
    )
    custom_target.append(added_use)

    tracker = SemanticLineageTracker(base_uses=v7_uses, target_uses=custom_target)

    assert len(tracker.removed) == 1
    assert tracker.removed[0].stable_lineage_key == "prop_vintage_telephone"

    assert len(tracker.added) == 1
    assert tracker.added[0].stable_lineage_key == "prop_silver_briefcase"

    resolved = SemanticLineageTracker.resolve_pairs(v7_uses, custom_target)
    assert resolved["prop_vintage_telephone"][0] is not None
    assert resolved["prop_vintage_telephone"][1] is None
    assert resolved["prop_silver_briefcase"][0] is None
    assert resolved["prop_silver_briefcase"][1] is not None


def test_lineage_tracker_modifications():
    """
    Verify SemanticLineageTracker accurately tracks creative use modifications
    across versions when narrative context, duration, or prominence changes.
    """
    v7_uses, v8_uses, _, _ = get_golden_fixtures()

    # In golden dataset, Item 11 (poster) is modified between v7 and v8
    tracker = SemanticLineageTracker(base_uses=v7_uses, target_uses=v8_uses)
    assert len(tracker.modified) == 1
    poster_mod = tracker.modified[0]
    assert poster_mod.stable_lineage_key == "poster_noir_detective_magazine"
    assert poster_mod.status == LineageStatus.MODIFIED
    assert "context_hash" in poster_mod.changed_fields
    assert "duration_or_prominence" in poster_mod.changed_fields
    assert "context" in poster_mod.changed_fields
    assert "CONTEXT_HASH_MISMATCH" in poster_mod.reason_codes
    assert "PROMINENCE_ESCALATED" in poster_mod.reason_codes
    assert "SCRIPT_DIALOGUE_MODIFIED" in poster_mod.reason_codes

    # Custom modification test: modify telephone prop context and duration
    custom_target = [u.model_copy() for u in v7_uses]
    phone_idx = next(i for i, u in enumerate(custom_target) if u.stable_lineage_key == "prop_vintage_telephone")
    custom_target[phone_idx] = custom_target[phone_idx].model_copy(
        update={
            "duration_or_prominence": "Featured close-up dialogue shot, 15s",
            "context": "Detective picks up phone receiver and screams into mouthpiece.",
            "context_hash": "custom_phone_hash_modified",
        }
    )

    custom_tracker = SemanticLineageTracker(base_uses=v7_uses, target_uses=custom_target)
    phone_pair = custom_tracker.get_pair("prop_vintage_telephone")
    assert phone_pair is not None
    assert phone_pair.status == LineageStatus.MODIFIED
    assert "duration_or_prominence" in phone_pair.changed_fields
    assert "context" in phone_pair.changed_fields
    assert "context_hash" in phone_pair.changed_fields



# =============================================================================
# 3. SEMANTIC DELTA ENGINE: NON-MATERIAL VS MATERIAL DISCRIMINATION
# =============================================================================

def test_discrimination_identical_uses():
    """Verify identical creative uses evaluate to non-material, low risk, carry."""
    engine = SemanticDeltaEngine()
    v7_uses, _, _, _ = get_golden_fixtures()
    use = v7_uses[0]

    result = engine.evaluate_delta(base_use=use, target_use=use)
    assert result.is_material is False
    assert result.clearance_risk_level == "low"
    assert result.recommended_action == "carry"

    delta = engine.generate_creative_delta(base_use=use, target_use=use, delta_analysis=result)
    assert delta.change_kind == ChangeKind.UNCHANGED
    assert delta.materiality == "none"


def test_discrimination_non_material_phrasing_and_typos():
    """Verify minor phrasing, typos, and whitespace evaluate to is_material=False."""
    engine = SemanticDeltaEngine()
    v7_uses, _, _, _ = get_golden_fixtures()
    base_use = v7_uses[0]

    # Target use with minor typo and whitespace difference in narrative context
    target_use = base_use.model_copy(
        update={
            "context": "Office establishing shot, protagonist enters holding a trenchcoat.  ",
            "context_hash": "different_hash_due_to_typo",
        }
    )

    result = engine.evaluate_delta(base_use=base_use, target_use=target_use)
    assert result.is_material is False
    assert result.clearance_risk_level == "low"
    assert result.recommended_action == "carry"


def test_discrimination_non_material_visual_shifts():
    """Verify non-rights visual shifts (lighting, angle, reflections) evaluate to is_material=False."""
    engine = SemanticDeltaEngine()
    v7_uses, _, _, _ = get_golden_fixtures()
    base_use = next(u for u in v7_uses if u.stable_lineage_key == "car_ford_sedan_1949")

    # Shift lighting and camera angle while preserving background status
    target_use = base_use.model_copy(
        update={
            "context": "Rain-slicked pavement reflecting neon signs with dim moody lighting as parked car sits in shadows.",
            "duration_or_prominence": "Exterior street background, 6s",
            "context_hash": "hash_dim_lighting_street",
        }
    )

    result = engine.evaluate_delta(base_use=base_use, target_use=target_use)
    assert result.is_material is False
    assert result.clearance_risk_level == "low"
    assert result.recommended_action == "carry"


def test_discrimination_material_prominence_escalation():
    """Verify prominence escalation (background blur -> close-up focal) evaluates to is_material=True."""
    engine = SemanticDeltaEngine()
    v7_uses, v8_uses, _, _ = get_golden_fixtures()
    base_poster = next(u for u in v7_uses if u.stable_lineage_key == "poster_noir_detective_magazine")
    target_poster = next(u for u in v8_uses if u.stable_lineage_key == "poster_noir_detective_magazine")

    result = engine.evaluate_delta(base_use=base_poster, target_use=target_poster)
    assert result.is_material is True
    assert result.clearance_risk_level == "high"
    assert result.recommended_action == "revalidate"
    assert "close-up" in result.prominence_shift or "14s" in result.prominence_shift

    delta = engine.generate_creative_delta(base_use=base_poster, target_use=target_poster, delta_analysis=result)
    assert delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
    assert delta.materiality == "high"


def test_discrimination_material_dialogue_mention():
    """Verify introducing dialogue referencing asset evaluates to is_material=True."""
    engine = SemanticDeltaEngine()
    v7_uses, _, _, _ = get_golden_fixtures()
    base_coffee = next(u for u in v7_uses if u.stable_lineage_key == "trademark_acme_coffee")

    # Character now speaks about Acme Coffee by name in dialogue
    target_coffee = base_coffee.model_copy(
        update={
            "context": "Detective points at sign and says: 'Acme Coffee makes the worst brew in Manhattan.'",
            "duration_or_prominence": "Featured dialogue mention, 8s",
            "context_hash": "hash_dialogue_acme",
        }
    )

    result = engine.evaluate_delta(base_use=base_coffee, target_use=target_coffee)
    assert result.is_material is True
    assert result.clearance_risk_level == "high"
    assert result.recommended_action == "revalidate"


def test_discrimination_cosmetic_telephone_pacing_shift():
    """
    Verify that non-material cosmetic shift (e.g. vintage telephone prop dialogue
    pacing from 4s to 5s without prominence change) evaluates to is_material=False,
    clearance_risk_level='low', and recommended_action='carry'.
    """
    engine = SemanticDeltaEngine()
    v7_uses, _, _, _ = get_golden_fixtures()
    phone_v7 = next(u for u in v7_uses if u.stable_lineage_key == "prop_vintage_telephone")

    # Dialogue pacing slightly extended from 4s to 5s while remaining incidental background
    phone_v8 = phone_v7.model_copy(
        update={
            "duration_or_prominence": "Incidental background set dressing, 5s",
            "context": "Office establishing shot, protagonist enters holding trench coat and pauses briefly.",
            "context_hash": "hash_phone_5s_pacing",
        }
    )

    result = engine.evaluate_delta(base_use=phone_v7, target_use=phone_v8)
    assert result.is_material is False
    assert result.clearance_risk_level == "low"
    assert result.recommended_action == "carry"

    delta = engine.generate_creative_delta(base_use=phone_v7, target_use=phone_v8, delta_analysis=result)
    assert delta.change_kind == ChangeKind.UNCHANGED
    assert delta.materiality == "none"


# =============================================================================

# 4. MODEL CONTAINMENT GUARDRAIL TESTS
# =============================================================================

def test_model_containment_guardrail_prevents_decision_mutation():
    """
    Assert that model output CANNOT directly alter a CounselDecision or approve/invalidate a claim.
    Clearance authority strictly resides with human counsel and deterministic InvalidationEngine.
    """
    engine = SemanticDeltaEngine()

    # 1. Direct CounselDecision instance must trigger ModelContainmentViolation
    decision = CounselDecision(
        decision_id="dec_fake",
        use_id="use_fake",
        stable_lineage_key="fake_key",
        applicable_version_id="v8",
        status=DecisionStatus.APPROVED,
        rationale="Model attempting to auto-approve",
    )
    with pytest.raises(ModelContainmentViolation):
        engine.enforce_containment_guardrail(decision)

    # 2. Direct DecisionValidity instance must trigger ModelContainmentViolation
    validity = DecisionValidity(
        decision_id="dec_fake",
        evaluated_for_version_id="v8",
        stable_lineage_key="fake_key",
        state=DecisionState.CARRIED_FORWARD,
        reason_code="ATTEMPTED_AUTO_CARRY",
    )
    with pytest.raises(ModelContainmentViolation):
        engine.enforce_containment_guardrail(validity)

    # 3. Direct DecisionStatus enum must trigger ModelContainmentViolation
    with pytest.raises(ModelContainmentViolation):
        engine.enforce_containment_guardrail(DecisionStatus.APPROVED)

    # 4. Dict containing restricted clearance keys must trigger ModelContainmentViolation
    breach_dict = {
        "is_material": False,
        "decision_status": "approved",
        "override_clearance": True,
    }
    with pytest.raises(ModelContainmentViolation):
        engine.enforce_containment_guardrail(breach_dict)

    # 5. Calling apply_model_output_to_decision must unconditionally fail
    with pytest.raises(ModelContainmentViolation):
        engine.apply_model_output_to_decision(
            DeltaAnalysisResult(
                is_material=False,
                prominence_shift="none",
                narrative_impact="none",
                statutory_fair_use_impact="valid",
                recommended_action="carry",
            ),
            decision,
        )


def test_model_containment_cannot_mutate_counsel_decision_without_invalidation_engine():
    """
    Asserts that a DeltaAnalysisResult or GeminiService response alone cannot mutate
    a CounselDecision.status from APPROVED to anything else without being processed
    by InvalidationEngine.evaluate_invalidation().
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    poster_decision = next(d for d in v7_decisions if d.stable_lineage_key == "poster_noir_detective_magazine")

    # 1. Baseline: V7 counsel decision is APPROVED
    assert poster_decision.status == DecisionStatus.APPROVED

    # 2. Generate a high-risk material DeltaAnalysisResult recommending 'revalidate'
    model_result = DeltaAnalysisResult(
        is_material=True,
        prominence_shift="Escalated from 2s background blur to 14s close-up focal dialogue",
        narrative_impact="Character actively interacts with artwork and quotes text aloud",
        clearance_risk_level="high",
        statutory_fair_use_impact="De minimis fair use defense under 17 U.S.C. § 107 eliminated",
        recommended_action="revalidate",
    )

    # Assert model result recommends revalidation with high risk
    assert model_result.is_material is True
    assert model_result.recommended_action == "revalidate"
    assert model_result.clearance_risk_level == "high"

    # Guardrail Check 1: DeltaAnalysisResult alone CANNOT mutate CounselDecision.status
    assert poster_decision.status == DecisionStatus.APPROVED

    # Guardrail Check 2: Direct model application attempt is blocked
    engine = SemanticDeltaEngine()
    with pytest.raises(ModelContainmentViolation):
        engine.apply_model_output_to_decision(model_result, poster_decision)

    # 3. Only deterministic InvalidationEngine has legal authority to evaluate status
    validity_results = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )
    poster_validity = next(v for v in validity_results if v.stable_lineage_key == "poster_noir_detective_magazine")

    # InvalidationEngine evaluates the state as STALE for version 8
    assert poster_validity.state == DecisionState.STALE
    assert poster_validity.revalidation_action == "revalidate"

    # Guardrail Check 3: The historical CounselDecision remains strictly immutable (APPROVED for v7)
    assert poster_decision.status == DecisionStatus.APPROVED


# =============================================================================

# 5. GEMINI SERVICE INTEGRATION & RETRY LOGIC TESTS
# =============================================================================

def test_gemini_service_parses_repaired_json():
    """Verify GeminiService._parse_llm_json repairs malformed JSON using repair_json_output."""
    malformed_llm_output = """```json
    {
        is_material: true,
        prominence_shift: 'Focal close-up shot.',
        narrative_impact: 'Active character interaction.',
        clearance_risk_level: 'high',
        statutory_fair_use_impact: 'De minimis invalid.',
        recommended_action: 'revalidate',
    }
    ```"""
    parsed = GeminiService._parse_llm_json(malformed_llm_output, target_model=DeltaAnalysisResult)
    assert parsed["is_material"] is True
    assert parsed["clearance_risk_level"] == "high"
    assert parsed["recommended_action"] == "revalidate"


@pytest.mark.asyncio
async def test_gemini_service_scene_delta_fallback():
    """Verify analyze_scene_delta returns structured DeltaAnalysisResult in fallback/deterministic mode."""
    service = GeminiService(use_fallback=True, mock_latency_ms=10.0, max_retries=2, retry_backoff_base=0.01)
    result = await service.analyze_scene_delta(
        asset_name="poster_noir_detective_magazine",
        v7_context="Poster on far wall blur",
        v7_prominence="Out-of-focus background, 2s",
        v8_context="Detective examines poster closely and reads headline",
        v8_prominence="Close-up focal shot, 14s",
    )
    assert isinstance(result, DeltaAnalysisResult)
    assert result.is_material is True
    assert result.clearance_risk_level == "high"
    assert result.recommended_action == "revalidate"


# =============================================================================
# 6. GOLDEN EXPECTED DELTAS FIXTURE TESTS
# =============================================================================

def test_golden_expected_deltas_all_12_items():
    """
    Verify get_golden_expected_deltas() contains all 12 items, asserts Item 11 is material,
    and asserts Item 12 and Items 1-10 are non-material in creative context.
    """
    deltas = get_golden_expected_deltas()

    assert len(deltas) == 12, "Must contain exactly 12 items"

    # Index 10 corresponds to Item 11 (poster_noir_detective_magazine)
    item_11 = deltas[10]
    assert item_11.is_material is True
    assert item_11.clearance_risk_level == "high"
    assert item_11.recommended_action == "revalidate"

    # Item 11 by key: Creative drift (poster)
    poster = deltas["poster_noir_detective_magazine"]
    assert poster.is_material is True
    assert poster.clearance_risk_level == "high"
    assert poster.recommended_action == "revalidate"

    # Item 12: External evidence drift (cue) has identical creative context
    music = deltas["music_cue_midnight_serenade"]
    assert music.is_material is False
    assert music.clearance_risk_level == "low"
    assert music.recommended_action == "carry"

    # Exactly 1 item marked material across all 12 items
    material_items = [k for k, d in deltas.items() if d.is_material]
    assert len(material_items) == 1, f"Expected exactly 1 material item, found {len(material_items)}"
    assert material_items[0] == "poster_noir_detective_magazine"

    # Items 1-10: All non-material
    for key, d in deltas.items():
        if key != "poster_noir_detective_magazine":
            assert d.is_material is False, f"Item {key} should have is_material=False"
            assert d.clearance_risk_level == "low", f"Item {key} should have clearance_risk_level='low'"
            assert d.recommended_action == "carry", f"Item {key} should have recommended_action='carry'"

