"""
tests/test_inverse_domain_steering.py

Automated test suite for InverseDomainSteeringEngine and query reformulation.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import pytest

from backend.agents.research.query_builder import (
    InverseDomainSteeringEngine,
    StructuredQueryBuilder,
)
from backend.agents.research.query_types import (
    AssetClass,
    EvidenceEvaluation,
    InvalidSteeringTransitionError,
    QueryBuilderError,
    SearchQueryRequest,
    SteeringState,
)


def test_trigger_condition_evaluation():
    """Verifies that 0 results or low confidence accurately trigger inverse steering, while provider error triggers recovery."""
    engine = InverseDomainSteeringEngine()

    zero_hits = EvidenceEvaluation(result_count=0, confidence_score=0.0)
    assert engine.should_trigger_inverse_steering(zero_hits) is True

    low_conf = EvidenceEvaluation(result_count=2, confidence_score=0.45)
    assert engine.should_trigger_inverse_steering(low_conf) is True

    http_error = EvidenceEvaluation(result_count=0, error_status=504)
    with pytest.raises(QueryBuilderError):
        engine.should_trigger_inverse_steering(http_error)

    high_conf = EvidenceEvaluation(result_count=4, confidence_score=0.88, stance="supporting")
    assert engine.should_trigger_inverse_steering(high_conf) is False


def test_inverse_steering_strips_site_and_injects_negatives():
    """Verifies that Tier 2 reformulation strips site: and adds negative operators."""
    engine = InverseDomainSteeringEngine()
    req = SearchQueryRequest(
        asset_id="clm_music_01",
        asset_class=AssetClass.MUSIC,
        title="Midnight Echoes at Twilight",
        creator_or_owner="Evelyn Vance",
    )

    zero_hits = EvidenceEvaluation(result_count=0, confidence_score=0.0)
    updated_req, query = engine.next_query(req, zero_hits)

    assert updated_req.current_state == SteeringState.INVERSE_STEERING
    assert updated_req.retry_count == 1
    assert "site:" not in query.query_string
    assert "-lyrics" in query.query_string
    assert "-chords" in query.query_string
    assert "-youtube" in query.query_string
    assert "-spotify" in query.query_string
    assert '"catalog"' in query.query_string or '"publishing"' in query.query_string


def test_inverse_steering_brand_negative_keywords():
    """Verifies that brand inverse steering injects shopping and ecommerce negative keywords."""
    engine = InverseDomainSteeringEngine()
    req = SearchQueryRequest(
        asset_id="clm_brand_01",
        asset_class=AssetClass.BRAND,
        title="Acme Corporation",
        creator_or_owner="Warner Bros",
        current_state=SteeringState.STRICT_REGISTRY,
    )

    zero_hits = EvidenceEvaluation(result_count=0, confidence_score=0.0)
    updated_req, query = engine.next_query(req, zero_hits)

    assert updated_req.current_state == SteeringState.INVERSE_STEERING
    assert "-store" in query.query_string
    assert "-buy" in query.query_string
    assert "-coupon" in query.query_string
    assert "-sale" in query.query_string


def test_state_progression_determinism_and_exhaustion():
    """Verifies monotonic state progression through all 4 clearance fallback tiers."""
    engine = InverseDomainSteeringEngine()
    req = SearchQueryRequest(
        asset_id="clm_rare_01",
        asset_class=AssetClass.ARTWORK,
        title="Lost Fresco",
        creator_or_owner="Anonymous",
        current_state=SteeringState.STRICT_REGISTRY,
    )

    bad_eval = EvidenceEvaluation(result_count=0, confidence_score=0.0)

    # STRICT_REGISTRY -> INVERSE_STEERING
    req, q1 = engine.next_query(req, bad_eval)
    assert req.current_state == SteeringState.INVERSE_STEERING

    # INVERSE_STEERING -> ADVERSARIAL_PROBE
    req, q2 = engine.next_query(req, bad_eval)
    assert req.current_state == SteeringState.ADVERSARIAL_PROBE
    assert "dispute" in q2.query_string or "infringement" in q2.query_string

    # ADVERSARIAL_PROBE -> DEEP_TASK
    req, q3 = engine.next_query(req, bad_eval)
    assert req.current_state == SteeringState.DEEP_TASK

    # DEEP_TASK -> EXHAUSTED
    req, q4 = engine.next_query(req, bad_eval)
    assert req.current_state == SteeringState.EXHAUSTED

    # EXHAUSTED raises InvalidSteeringTransitionError
    with pytest.raises(InvalidSteeringTransitionError):
        engine.next_query(req, bad_eval)
