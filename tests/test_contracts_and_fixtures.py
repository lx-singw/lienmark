"""
Lienmark Table-Driven Contract and Golden Fixture Test Suite
Validates canonical Pydantic v2 schemas, context hash determinism, JSON round-trip serialization,
table-driven pre-model drift assertions for all 12 items, fixture purity, and fail-closed validation.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional
import pytest
from pydantic import ValidationError

from backend.domain.models import (
    ChangeKind,
    DecisionState,
    DecisionStatus,
    EvidenceStance,
    ProductionVersion,
    CreativeUse,
    CreativeDelta,
    PublicEvidenceSnapshot,
    CounselDecision,
    DecisionValidity,
    ReattestationRequest,
    ExceptionsScheduleItem,
    ExceptionsSchedule,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
    get_golden_expected_deltas,
)


# =============================================================================
# 1. CANONICAL PYDANTIC V2 SCHEMA CONFORMANCE TESTS
# =============================================================================

def test_all_12_items_canonical_pydantic_v2_schemas():
    """
    Test that all 12 golden items in both V7 and V8 versions, together with
    decisions, evidence snapshots, deltas, validities, and schedule items,
    conform strictly to canonical Pydantic v2 schemas without type coercion failure.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    v7_ver = get_v7_version()
    v8_ver = get_v8_version()

    # Assert version models validate against ProductionVersion
    assert isinstance(v7_ver, ProductionVersion)
    assert isinstance(v8_ver, ProductionVersion)
    revalidated_v7 = ProductionVersion.model_validate(v7_ver.model_dump())
    revalidated_v8 = ProductionVersion.model_validate(v8_ver.model_dump())
    assert revalidated_v7 == v7_ver
    assert revalidated_v8 == v8_ver
    assert v7_ver.source_type == "screenplay"
    assert v8_ver.parent_version_id == "v7"

    # Assert exact cardinality
    assert len(v7_uses) == 12, "Base version must have exactly 12 creative uses"
    assert len(v8_uses) == 12, "Target version must have exactly 12 creative uses"
    assert len(v7_decisions) == 12, "Base version must have exactly 12 counsel decisions"
    assert len(v8_evidence) == 12, "Target version must have exactly 12 evidence snapshots"

    # Validate CreativeUse models
    for idx, (u7, u8) in enumerate(zip(v7_uses, v8_uses), start=1):
        assert isinstance(u7, CreativeUse), f"Item {idx} V7 must be instance of CreativeUse"
        assert isinstance(u8, CreativeUse), f"Item {idx} V8 must be instance of CreativeUse"

        # Pydantic v2 model_validate check
        u7_dump = u7.model_dump()
        u8_dump = u8.model_dump()
        assert CreativeUse.model_validate(u7_dump) == u7
        assert CreativeUse.model_validate(u8_dump) == u8

        # Mandatory fields non-empty check
        for field in ["use_id", "version_id", "scene_or_timecode", "asset_type", "description",
                      "duration_or_prominence", "context", "stable_lineage_key", "context_hash"]:
            assert getattr(u7, field), f"Item {idx} V7 missing mandatory field {field}"
            assert getattr(u8, field), f"Item {idx} V8 missing mandatory field {field}"

    # Validate CounselDecision models
    for idx, dec in enumerate(v7_decisions, start=1):
        assert isinstance(dec, CounselDecision), f"Decision {idx} must be instance of CounselDecision"
        assert CounselDecision.model_validate(dec.model_dump()) == dec
        assert isinstance(dec.status, DecisionStatus)
        assert dec.applicable_version_id == "v7"
        assert dec.human_confirmed is True
        assert dec.reviewer_display_name == "Sarah Jenkins, Esq. (Clearance Counsel)"

    # Validate PublicEvidenceSnapshot models
    for key, snap in v8_evidence.items():
        assert isinstance(snap, PublicEvidenceSnapshot), f"Snapshot for {key} must be PublicEvidenceSnapshot"
        assert PublicEvidenceSnapshot.model_validate(snap.model_dump()) == snap
        assert isinstance(snap.stance, EvidenceStance)
        assert snap.source_url.startswith("https://")
        assert len(snap.query) > 0
        assert len(snap.excerpt) > 0

    # Validate CreativeDelta and DecisionValidity models generated through InvalidationEngine
    deltas = InvalidationEngine.detect_creative_deltas(v7_uses, v8_uses)
    assert len(deltas) == 12
    for key, delta in deltas.items():
        assert isinstance(delta, CreativeDelta)
        assert CreativeDelta.model_validate(delta.model_dump()) == delta
        assert isinstance(delta.change_kind, ChangeKind)

    validities = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )
    assert len(validities) == 12
    for val in validities:
        assert isinstance(val, DecisionValidity)
        assert DecisionValidity.model_validate(val.model_dump()) == val
        assert isinstance(val.state, DecisionState)
        assert val.evaluated_for_version_id == "v8"

    # Validate ExceptionsSchedule and Items
    schedule = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validities,
    )
    assert isinstance(schedule, ExceptionsSchedule)
    assert ExceptionsSchedule.model_validate(schedule.model_dump()) == schedule
    assert len(schedule.items) == 12
    for item in schedule.items:
        assert isinstance(item, ExceptionsScheduleItem)
        assert ExceptionsScheduleItem.model_validate(item.model_dump()) == item
        assert item.v7_decision_status == "APPROVED"


# =============================================================================
# 2. CONTEXT HASH DETERMINISM TESTS
# =============================================================================

def test_context_hash_determinism_and_sha256_algorithm():
    """
    Test context hash determinism:
    1. SHA-256 calculation payload is f"{text.strip()}::{prominence.strip()}".
    2. Hex digest is sliced to 16 characters.
    3. Deterministic across repeat executions.
    4. Trimming resilience: leading/trailing whitespace changes do not alter hash.
    5. Avalanche effect: minute changes in text or prominence produce completely distinct hashes.
    6. All 12 items in V7 and V8 match InvalidationEngine.compute_context_hash exactly.
    """
    v7_uses, v8_uses, _, _ = get_golden_fixtures()

    # 1. Exact algorithmic equivalence assertion
    test_text = "Detective paces the room while jazz plays."
    test_prominence = "Background audio, 15s"
    expected_payload = f"{test_text.strip()}::{test_prominence.strip()}"
    expected_hash = hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()[:16]

    engine_hash = InvalidationEngine.compute_context_hash(test_text, test_prominence)
    assert engine_hash == expected_hash
    assert len(engine_hash) == 16
    assert re.match(r"^[0-9a-f]{16}$", engine_hash), "Context hash must be 16-char lowercase hex string"

    # 2. Determinism across 100 runs
    for _ in range(100):
        assert InvalidationEngine.compute_context_hash(test_text, test_prominence) == expected_hash

    # 3. Leading/trailing whitespace trimming resilience
    whitespace_variations = [
        ("  " + test_text + "  ", "\t" + test_prominence + "\n"),
        ("\n\n" + test_text, test_prominence + "   "),
        (test_text, "   " + test_prominence),
    ]
    for alt_text, alt_prom in whitespace_variations:
        assert InvalidationEngine.compute_context_hash(alt_text, alt_prom) == expected_hash

    # 4. Avalanche / sensitivity check
    variant_text = test_text + "."
    variant_prom = test_prominence.replace("15s", "16s")
    assert InvalidationEngine.compute_context_hash(variant_text, test_prominence) != expected_hash
    assert InvalidationEngine.compute_context_hash(test_text, variant_prom) != expected_hash
    # Swapped positions must yield different hashes
    assert InvalidationEngine.compute_context_hash(test_prominence, test_text) != expected_hash

    # 5. Verify all 12 items in golden fixtures have correct deterministic context hashes
    for idx, u in enumerate(v7_uses, start=1):
        computed = InvalidationEngine.compute_context_hash(u.context, u.duration_or_prominence)
        assert u.context_hash == computed, f"V7 Item {idx} context hash mismatch: {u.context_hash} vs {computed}"

    for idx, u in enumerate(v8_uses, start=1):
        computed = InvalidationEngine.compute_context_hash(u.context, u.duration_or_prominence)
        assert u.context_hash == computed, f"V8 Item {idx} context hash mismatch: {u.context_hash} vs {computed}"

    # 6. Verify hash equality for items 1-10 and item 12, but hash mismatch for item 11
    v7_map = {u.stable_lineage_key: u for u in v7_uses}
    v8_map = {u.stable_lineage_key: u for u in v8_uses}

    for key in v7_map:
        if key == "poster_noir_detective_magazine":
            assert v7_map[key].context_hash != v8_map[key].context_hash, (
                "Item 11 (poster) must have divergent context_hash due to creative drift"
            )
        else:
            assert v7_map[key].context_hash == v8_map[key].context_hash, (
                f"Item {key} context_hash should be identical between V7 and V8"
            )


# =============================================================================
# 3. JSON ROUND-TRIP SERIALIZATION AND DESERIALIZATION TESTS
# =============================================================================

def test_json_roundtrip_production_version():
    """Verify JSON and dict round-trip serialization for ProductionVersion."""
    v7 = get_v7_version()
    v8 = get_v8_version()

    for original in [v7, v8]:
        # JSON round-trip
        json_str = original.model_dump_json()
        deserialized = ProductionVersion.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.version_id == original.version_id
        assert deserialized.project_id == original.project_id
        assert deserialized.content_hash == original.content_hash

        # Dict round-trip
        data_dict = original.model_dump()
        reconstructed = ProductionVersion.model_validate(data_dict)
        assert reconstructed == original


def test_json_roundtrip_creative_use():
    """Verify JSON and dict round-trip serialization across all 12 CreativeUse instances."""
    v7_uses, v8_uses, _, _ = get_golden_fixtures()

    for original in v7_uses + v8_uses:
        # JSON round-trip
        json_str = original.model_dump_json()
        deserialized = CreativeUse.model_validate_json(json_str)
        assert deserialized == original
        assert deserialized.use_id == original.use_id
        assert deserialized.stable_lineage_key == original.stable_lineage_key
        assert deserialized.context_hash == original.context_hash

        # Dict round-trip
        data_dict = original.model_dump()
        reconstructed = CreativeUse.model_validate(data_dict)
        assert reconstructed == original


def test_json_roundtrip_counsel_decision():
    """Verify JSON and dict round-trip serialization across all 12 CounselDecision instances."""
    _, _, v7_decisions, _ = get_golden_fixtures()

    for original in v7_decisions:
        # JSON round-trip
        json_str = original.model_dump_json()
        deserialized = CounselDecision.model_validate_json(json_str)
        assert deserialized == original
        assert isinstance(deserialized.status, DecisionStatus)
        assert deserialized.status == original.status
        assert deserialized.reviewer_display_name == original.reviewer_display_name

        # Dict round-trip
        data_dict = original.model_dump()
        reconstructed = CounselDecision.model_validate(data_dict)
        assert reconstructed == original


def test_json_roundtrip_exceptions_schedule():
    """
    Verify JSON and dict round-trip serialization for ExceptionsSchedule,
    including nested ExceptionsScheduleItem instances and evidence citations.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    validities = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )

    reattestations = {
        "poster_noir_detective_magazine": ReattestationRequest(
            decision_id="dec_v7_poster_noir",
            stable_lineage_key="poster_noir_detective_magazine",
            version_id="v8",
            new_status=DecisionStatus.APPROVED,
            counsel_rationale="Artwork public domain confirmed via LOC renewal search.",
            reviewer_name="Sarah Jenkins, Esq.",
        ),
        "music_cue_midnight_serenade": ReattestationRequest(
            decision_id="dec_v7_music_midnight",
            stable_lineage_key="music_cue_midnight_serenade",
            version_id="v8",
            new_status=DecisionStatus.REJECTED,
            counsel_rationale="Vanguard Media conflict; cue must be replaced in final sound cut.",
            reviewer_name="Sarah Jenkins, Esq.",
        ),
    }

    original = InvalidationEngine.generate_exceptions_schedule(
        project_id="proj_blockbuster_cinema",
        base_version_id="v7",
        target_version_id="v8",
        target_uses=v8_uses,
        validity_results=validities,
        reattestations=reattestations,
    )

    # JSON round-trip
    json_str = original.model_dump_json()
    deserialized = ExceptionsSchedule.model_validate_json(json_str)
    assert deserialized == original
    assert deserialized.total_claims == 12
    assert deserialized.carried_forward_count == 10
    assert deserialized.reopened_count == 2
    assert deserialized.re_attested_count == 1
    assert deserialized.unresolved_exception_count == 1
    assert len(deserialized.items) == 12

    # Verify nested citations and state preserved
    poster_item = next(i for i in deserialized.items if i.stable_lineage_key == "poster_noir_detective_magazine")
    assert poster_item.v8_evaluation_state == "re_attested"
    assert len(poster_item.evidence_citations) > 0
    assert poster_item.evidence_citations[0]["provider"] == "Parallel"

    # Dict round-trip
    data_dict = original.model_dump()
    reconstructed = ExceptionsSchedule.model_validate(data_dict)
    assert reconstructed == original


def test_json_roundtrip_ancillary_models():
    """Verify JSON round-trip for CreativeDelta, PublicEvidenceSnapshot, DecisionValidity, ReattestationRequest."""
    _, v8_uses, _, v8_evidence = get_golden_fixtures()

    # PublicEvidenceSnapshot
    for snap in v8_evidence.values():
        dumped = snap.model_dump_json()
        parsed = PublicEvidenceSnapshot.model_validate_json(dumped)
        assert parsed == snap
        assert parsed.stance == snap.stance

    # CreativeDelta
    delta = CreativeDelta(
        delta_id="delta_test_123",
        before_use_id="use_v7_test",
        after_use_id="use_v8_test",
        stable_lineage_key="test_lineage_key",
        change_kind=ChangeKind.MATERIALLY_MODIFIED,
        materiality="high",
        match_confidence=1.0,
        changed_fields=["context_hash", "duration_or_prominence"],
        reason_codes=["CONTEXT_HASH_MISMATCH", "PROMINENCE_ESCALATED"],
    )
    assert CreativeDelta.model_validate_json(delta.model_dump_json()) == delta

    # DecisionValidity
    validity = DecisionValidity(
        decision_id="dec_test_456",
        evaluated_for_version_id="v8",
        stable_lineage_key="test_lineage_key",
        state=DecisionState.STALE,
        reason_code="CREATIVE_CONTEXT_ALTERED",
        changed_dependency_ids=["delta_test_123"],
        revalidation_action="revalidate",
        creative_delta=delta,
    )
    assert DecisionValidity.model_validate_json(validity.model_dump_json()) == validity

    # ReattestationRequest
    reattest = ReattestationRequest(
        decision_id="dec_test_456",
        stable_lineage_key="test_lineage_key",
        version_id="v8",
        new_status=DecisionStatus.APPROVED,
        counsel_rationale="De minimis fair use confirmed.",
        reviewer_name="Jane Doe, Esq.",
    )
    assert ReattestationRequest.model_validate_json(reattest.model_dump_json()) == reattest


# =============================================================================
# 4. TABLE-DRIVEN TEST OF EXACT 12 ITEMS BEFORE ANY MODEL CALL
# =============================================================================

# Comprehensive specification of all 12 items as expected BEFORE any external LLM/API calls:
# Items 1-10: unchanged, carried forward
# Item 11: Scene 42 poster: creative drift, materially modified
# Item 12: Scene 18 jazz cue: external evidence drift, contradictory stance
TWELVE_GOLDEN_ITEMS_SPEC = [
    # (index, lineage_key, asset_type, scene, v7_status, change_kind, decision_state, reason_code, action, evidence_stance, is_material)
    (
        1,
        "prop_vintage_telephone",
        "prop",
        "Scene 04 - Detective Office",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        2,
        "poster_paris_expo_1937",
        "artwork",
        "Scene 08 - Hotel Corridor",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        3,
        "car_ford_sedan_1949",
        "prop",
        "Scene 12 - Street Exterior",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        4,
        "trademark_acme_coffee",
        "trademark",
        "Scene 15 - Diner Booth",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        5,
        "artwork_abstract_expressionist",
        "artwork",
        "Scene 21 - Penthouse Loft",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        6,
        "likeness_mayor_cameo",
        "likeness",
        "Scene 26 - Courtroom Gallery",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        7,
        "architecture_tribunal_facade",
        "location",
        "Scene 30 - Civic Center",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        8,
        "text_headline_gazette",
        "text",
        "Scene 34 - Newsstand",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        9,
        "wardrobe_fedora_brand",
        "trademark",
        "Scene 38 - Subway Platform",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        10,
        "music_incidental_radio_static",
        "music",
        "Scene 40 - Safehouse",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.CARRIED_FORWARD,
        "DEPENDENCIES_SATISFIED_UNCHANGED",
        "carry",
        EvidenceStance.SUPPORTING,
        False,
    ),
    (
        11,
        "poster_noir_detective_magazine",
        "artwork",
        "Scene 42 - 00:44:12",
        DecisionStatus.APPROVED,
        ChangeKind.MATERIALLY_MODIFIED,
        DecisionState.STALE,
        "CREATIVE_CONTEXT_ALTERED",
        "revalidate",
        EvidenceStance.SUPPORTING,
        True,
    ),
    (
        12,
        "music_cue_midnight_serenade",
        "music",
        "Scene 18 - 00:19:40",
        DecisionStatus.APPROVED,
        ChangeKind.UNCHANGED,
        DecisionState.STALE,
        "EXTERNAL_EVIDENCE_SHIFT",
        "revalidate",
        EvidenceStance.CONTRADICTORY,
        False,
    ),
]


@pytest.mark.parametrize(
    "item_idx,lineage_key,expected_asset_type,expected_scene,expected_v7_status,"
    "expected_change_kind,expected_decision_state,expected_reason_code,"
    "expected_action,expected_evidence_stance,expected_materiality",
    TWELVE_GOLDEN_ITEMS_SPEC,
)
def test_table_driven_twelve_items_before_model_call(
    item_idx: int,
    lineage_key: str,
    expected_asset_type: str,
    expected_scene: str,
    expected_v7_status: DecisionStatus,
    expected_change_kind: ChangeKind,
    expected_decision_state: DecisionState,
    expected_reason_code: str,
    expected_action: str,
    expected_evidence_stance: EvidenceStance,
    expected_materiality: bool,
):
    """
    Table-driven verification of each item's state BEFORE any LLM or external model call:
    - Items 1-10: unchanged, carried forward, supporting evidence
    - Item 11: creative drift, materially modified, reason CREATIVE_CONTEXT_ALTERED
    - Item 12: external evidence drift, contradictory stance, reason EXTERNAL_EVIDENCE_SHIFT
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()

    # 1. Locate items across fixtures by stable_lineage_key
    u7 = next((u for u in v7_uses if u.stable_lineage_key == lineage_key), None)
    u8 = next((u for u in v8_uses if u.stable_lineage_key == lineage_key), None)
    d7 = next((d for d in v7_decisions if d.stable_lineage_key == lineage_key), None)
    ev8 = v8_evidence.get(lineage_key)

    assert u7 is not None, f"Item {item_idx} ({lineage_key}) not found in V7 uses"
    assert u8 is not None, f"Item {item_idx} ({lineage_key}) not found in V8 uses"
    assert d7 is not None, f"Item {item_idx} ({lineage_key}) not found in V7 decisions"
    assert ev8 is not None, f"Item {item_idx} ({lineage_key}) not found in V8 evidence snapshots"

    # 2. Assert structural attributes
    assert u7.asset_type == expected_asset_type
    assert u8.asset_type == expected_asset_type
    assert u7.scene_or_timecode == expected_scene
    assert d7.status == expected_v7_status
    assert ev8.stance == expected_evidence_stance

    # 3. Detect creative deltas without model invocation
    deltas = InvalidationEngine.detect_creative_deltas(v7_uses, v8_uses)
    delta = deltas.get(lineage_key)
    assert delta is not None, f"Delta must be computed for {lineage_key}"
    assert delta.change_kind == expected_change_kind
    if expected_materiality:
        assert delta.materiality == "high"
        assert len(delta.changed_fields) > 0
    else:
        assert delta.materiality == "none"
        assert len(delta.changed_fields) == 0

    # 4. Evaluate invalidation state without model invocation
    validities = InvalidationEngine.evaluate_invalidation(
        base_uses=v7_uses,
        target_uses=v8_uses,
        prior_decisions=v7_decisions,
        evidence_snapshots=v8_evidence,
        target_version_id="v8",
    )
    val = next((v for v in validities if v.stable_lineage_key == lineage_key), None)
    assert val is not None, f"Validity evaluation must exist for {lineage_key}"
    assert val.state == expected_decision_state
    assert val.reason_code == expected_reason_code
    assert val.revalidation_action == expected_action

    # 5. Item-specific detailed invariant assertions
    if 1 <= item_idx <= 10:
        # Items 1-10: fully unchanged and carried forward
        assert u7.context_hash == u8.context_hash
        assert u7.duration_or_prominence == u8.duration_or_prominence
        assert u7.context == u8.context
        assert val.state == DecisionState.CARRIED_FORWARD
        assert val.revalidation_action == "carry"
        assert val.reason_code == "DEPENDENCIES_SATISFIED_UNCHANGED"

    elif item_idx == 11:
        # Item 11: Scene 42 Poster - Creative Drift
        assert lineage_key == "poster_noir_detective_magazine"
        assert u7.context_hash != u8.context_hash, "Context hash must change for Scene 42 poster"
        assert "2s" in u7.duration_or_prominence
        assert "14s" in u8.duration_or_prominence
        assert "Detective grabs poster off wall" in u8.context
        assert val.state == DecisionState.STALE
        assert val.reason_code == "CREATIVE_CONTEXT_ALTERED"
        assert val.revalidation_action == "revalidate"
        assert val.creative_delta is not None
        assert val.creative_delta.change_kind == ChangeKind.MATERIALLY_MODIFIED
        assert "context_hash" in val.creative_delta.changed_fields
        assert "PROMINENCE_ESCALATED" in val.creative_delta.reason_codes

    elif item_idx == 12:
        # Item 12: Scene 18 Jazz Cue - External Evidence Drift
        assert lineage_key == "music_cue_midnight_serenade"
        assert u7.context_hash == u8.context_hash, "Context hash must remain identical for Scene 18 jazz cue"
        assert u7.duration_or_prominence == u8.duration_or_prominence
        assert val.state == DecisionState.STALE
        assert val.reason_code == "EXTERNAL_EVIDENCE_SHIFT"
        assert val.revalidation_action == "revalidate"
        assert ev8.stance == EvidenceStance.CONTRADICTORY
        assert "Vanguard Media Holdings LLC" in ev8.excerpt


# =============================================================================
# 5. FIXTURE PURITY & CONFIDENTIALITY / SECRET SCANNING TESTS
# =============================================================================

def test_fixture_purity_no_secrets_or_confidential_data():
    """
    Verify fixture purity:
    1. No actual API keys, private tokens, bearer secrets, or private keys.
    2. No private internal IPv4 addresses or intranet endpoints.
    3. No personal identifiable information (real phone numbers, SSNs, personal emails).
    4. All 12 items belong strictly to the fictional film production 'Shadows Over Broadway'.
    5. All external snapshot URLs point to approved public records / archives / test domains.
    """
    v7_uses, v8_uses, v7_decisions, v8_evidence = get_golden_fixtures()
    v7_ver = get_v7_version()
    v8_ver = get_v8_version()

    # Prohibited Secret & Key Regexes
    secret_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),                                    # OpenAI / general sk keys
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),                                   # Google API Key
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),                                    # GitHub personal token
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{25,}", re.IGNORECASE),          # Bearer auth tokens
        re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+)?PRIVATE\s+KEY-----"),        # PEM private keys
        re.compile(r"(?i)(password|secret|api_key|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]

    # Prohibited Internal IP / Network Regexes
    internal_ip_patterns = [
        re.compile(r"https?://(?:127\.0\.0\.1|localhost)(?::\d+)?"),
        re.compile(r"https?://10\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
        re.compile(r"https?://192\.168\.\d{1,3}\.\d{1,3}"),
        re.compile(r"https?://172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"),
    ]

    # PII Regexes
    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    phone_pattern = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

    # Approved external domain hosts for clearance evidence mock citations
    allowed_domains = {
        "records.publicdomain.org",
        "cocatalog.loc.gov",
        "ascap.com",
    }

    # Aggregate all string values across all models
    all_strings: List[str] = []

    for ver in [v7_ver, v8_ver]:
        all_strings.extend([ver.version_id, ver.project_id, ver.label, ver.content_hash, ver.source_type])

    for u in v7_uses + v8_uses:
        all_strings.extend([
            u.use_id, u.version_id, u.scene_or_timecode, u.asset_type,
            u.description, u.duration_or_prominence, u.context,
            u.stable_lineage_key, u.context_hash,
        ])
        if u.source_span:
            all_strings.append(u.source_span)

    for dec in v7_decisions:
        all_strings.extend([
            dec.decision_id, dec.use_id, dec.stable_lineage_key,
            dec.applicable_version_id, dec.rationale, dec.reviewer_display_name,
        ])

    for snap in v8_evidence.values():
        all_strings.extend([
            snap.snapshot_id, snap.use_id, snap.stable_lineage_key,
            snap.query, snap.source_url, snap.source_title,
            snap.excerpt, snap.provider,
        ])

    combined_text = "\n".join(all_strings)

    # 1. Assert no secret keys
    for pattern in secret_patterns:
        matches = pattern.findall(combined_text)
        assert len(matches) == 0, f"Found prohibited secret pattern match in fixture: {matches}"

    # 2. Assert no internal IP leaks
    for pattern in internal_ip_patterns:
        matches = pattern.findall(combined_text)
        assert len(matches) == 0, f"Found prohibited internal IP/host pattern match in fixture: {matches}"

    # 3. Assert no SSN or private personal telephone PII
    ssn_matches = ssn_pattern.findall(combined_text)
    assert len(ssn_matches) == 0, f"Found potential SSN pattern in fixtures: {ssn_matches}"

    phone_matches = phone_pattern.findall(combined_text)
    assert len(phone_matches) == 0, f"Found potential phone number pattern in fixtures: {phone_matches}"

    # 4. Assert URL purity
    for snap in v8_evidence.values():
        url = snap.source_url
        match = re.match(r"https://([^/]+)", url)
        assert match is not None, f"Snapshot URL must be valid HTTPS: {url}"
        domain = match.group(1)
        assert domain in allowed_domains, f"Snapshot domain '{domain}' not in approved whitelist: {allowed_domains}"

    # 5. Assert fictional film metadata consistency
    assert v7_ver.project_id == "proj_blockbuster_cinema"
    assert v8_ver.project_id == "proj_blockbuster_cinema"
    assert "Shadows Over Broadway" in v7_ver.label
    assert "Shadows Over Broadway" in v8_ver.label


# =============================================================================
# 6. FAIL-CLOSED VALIDATION TESTS (PYDANTIC VALIDATIONERROR ON MALFORMED SCHEMAS)
# =============================================================================

def test_fail_closed_pydantic_validation_error_on_missing_required_fields():
    """Verify that omitting mandatory fields raises Pydantic ValidationError (fail-closed)."""

    # CreativeUse missing context_hash
    with pytest.raises(ValidationError) as exc_info:
        CreativeUse(
            use_id="use_test_missing_hash",
            version_id="v7",
            scene_or_timecode="Scene 01",
            asset_type="prop",
            description="Test prop",
            duration_or_prominence="5s",
            context="Test context",
            stable_lineage_key="prop_test",
            # context_hash omitted
        )
    assert "context_hash" in str(exc_info.value)

    # CreativeUse missing stable_lineage_key
    with pytest.raises(ValidationError) as exc_info:
        CreativeUse(
            use_id="use_test_missing_key",
            version_id="v7",
            scene_or_timecode="Scene 01",
            asset_type="prop",
            description="Test prop",
            duration_or_prominence="5s",
            context="Test context",
            context_hash="a1b2c3d4e5f60718",
            # stable_lineage_key omitted
        )
    assert "stable_lineage_key" in str(exc_info.value)

    # ProductionVersion missing content_hash
    with pytest.raises(ValidationError) as exc_info:
        ProductionVersion(
            version_id="v99",
            project_id="proj_test",
            label="Malformed version",
            # content_hash omitted
        )
    assert "content_hash" in str(exc_info.value)

    # CounselDecision missing rationale
    with pytest.raises(ValidationError) as exc_info:
        CounselDecision(
            decision_id="dec_missing_rationale",
            use_id="use_1",
            stable_lineage_key="key_1",
            applicable_version_id="v7",
            status=DecisionStatus.APPROVED,
            # rationale omitted
        )
    assert "rationale" in str(exc_info.value)


def test_fail_closed_pydantic_validation_error_on_invalid_enum_values():
    """Verify that invalid enum strings fail closed with Pydantic ValidationError."""

    # CounselDecision with invalid status (e.g. 'MAYBE' or 'PENDING')
    with pytest.raises(ValidationError) as exc_info:
        CounselDecision(
            decision_id="dec_invalid_status",
            use_id="use_1",
            stable_lineage_key="key_1",
            applicable_version_id="v7",
            status="MAYBE",  # Not in DecisionStatus enum
            rationale="Uncertain approval",
        )
    assert "status" in str(exc_info.value)

    # PublicEvidenceSnapshot with invalid stance
    with pytest.raises(ValidationError) as exc_info:
        PublicEvidenceSnapshot(
            snapshot_id="snap_invalid_stance",
            use_id="use_1",
            stable_lineage_key="key_1",
            query="test query",
            source_url="https://records.publicdomain.org/test",
            source_title="Test Record",
            excerpt="Test excerpt",
            stance="HIGHLY_SUSPICIOUS",  # Not in EvidenceStance enum
        )
    assert "stance" in str(exc_info.value)

    # CreativeDelta with invalid change_kind
    with pytest.raises(ValidationError) as exc_info:
        CreativeDelta(
            delta_id="delta_invalid_kind",
            stable_lineage_key="key_1",
            change_kind="MUTATED",  # Not in ChangeKind enum
        )
    assert "change_kind" in str(exc_info.value)

    # DecisionValidity with invalid state
    with pytest.raises(ValidationError) as exc_info:
        DecisionValidity(
            decision_id="dec_1",
            evaluated_for_version_id="v8",
            stable_lineage_key="key_1",
            state="GUARANTEED_VALID",  # Not in DecisionState enum
            reason_code="MANUAL_OVERRIDE",
        )
    assert "state" in str(exc_info.value)


def test_fail_closed_pydantic_validation_error_on_corrupted_json_or_dict():
    """Verify that malformed JSON payloads and incorrect field types fail validation."""

    # Empty payload to model_validate
    for model_cls in [CreativeUse, ProductionVersion, CounselDecision, ExceptionsSchedule]:
        with pytest.raises(ValidationError):
            model_cls.model_validate({})

    # Malformed JSON string to model_validate_json
    with pytest.raises(ValidationError):
        CreativeUse.model_validate_json('{"invalid_key": 12345}')

    # Type mismatch: total_claims passed as non-numeric string to ExceptionsSchedule
    with pytest.raises(ValidationError) as exc_info:
        ExceptionsSchedule(
            schedule_id="sched_test",
            project_id="proj_test",
            target_version_id="v8",
            base_version_id="v7",
            total_claims="NOT_AN_INT",  # Invalid type
            carried_forward_count=10,
            reopened_count=2,
            re_attested_count=1,
            unresolved_exception_count=1,
        )
    assert "total_claims" in str(exc_info.value)


def test_golden_expected_deltas_contract():
    """Verify get_golden_expected_deltas conforms strictly to contracts across all 12 items."""
    deltas = get_golden_expected_deltas()
    assert len(deltas) == 12, "Must contain exactly 12 expected deltas"

    # Assert Item 11 (poster) is material
    poster = deltas["poster_noir_detective_magazine"]
    assert poster.is_material is True
    assert poster.clearance_risk_level == "high"
    assert poster.recommended_action == "revalidate"

    # Assert Item 12 and Items 1-10 are non-material for creative context
    music = deltas["music_cue_midnight_serenade"]
    assert music.is_material is False
    assert music.clearance_risk_level == "low"
    assert music.recommended_action == "carry"

    for key, d in deltas.items():
        if key != "poster_noir_detective_magazine":
            assert d.is_material is False
            assert d.clearance_risk_level == "low"
