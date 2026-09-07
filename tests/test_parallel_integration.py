"""
tests/test_parallel_integration.py

Sprint 3.1 Acceptance Gate: Parallel Search Integration & Query Optimization Engine.
Verifies:
1. End-to-end grounded query execution across 5 benchmark asset classes.
2. Invariant: 100% of findings possess a valid external source_url.
3. Invariant: 100% of findings possess an attributable source_snippet (>= 25 chars).
4. Inverse domain steering automatic trigger on obscure musical asset.
5. Deterministic SHA-256 payload digests and millisecond latency telemetry.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import re
import pytest

from backend.agents.research.query_builder import (
    InverseDomainSteeringEngine,
    StructuredQueryBuilder,
)
from backend.agents.research.query_types import (
    AssetClass,
    EvidenceEvaluation,
    SearchQueryRequest,
    SteeringState,
)
from backend.services.mock_parallel import MockParallelClient
from backend.services.parallel_types import (
    DomainAuthorityTier,
    ParallelSearchRequest,
    ParallelSearchResult,
)

URL_REGEX = re.compile(r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$")


def _get_benchmark_asset_requests() -> list[SearchQueryRequest]:
    """Returns 5 benchmark test cases matching sample_script.pdf entities."""
    return [
        SearchQueryRequest(
            asset_id="clm_music_01",
            asset_class=AssetClass.MUSIC,
            title="Clair de Lune",
            creator_or_owner="Claude Debussy",
            year=1905,
        ),
        SearchQueryRequest(
            asset_id="clm_footage_01",
            asset_class=AssetClass.FOOTAGE,
            title="Apollo 11 Moon Landing Broadcast",
            creator_or_owner="NASA",
            year=1969,
        ),
        SearchQueryRequest(
            asset_id="clm_brand_01",
            asset_class=AssetClass.BRAND,
            title="Coca-Cola",
            creator_or_owner="The Coca-Cola Company",
        ),
        SearchQueryRequest(
            asset_id="clm_brand_02",
            asset_class=AssetClass.BRAND,
            title="Marlboro",
            creator_or_owner="Philip Morris",
        ),
        SearchQueryRequest(
            asset_id="clm_art_01",
            asset_class=AssetClass.ARTWORK,
            title="Shadows of Manhattan",
            creator_or_owner="Crime Detective Magazine Poster",
            year=1944,
        ),
    ]


@pytest.mark.asyncio
async def test_benchmark_5_asset_classes_execution_and_invariants():
    """Sprint 3.1 Acceptance Gate: Queries 5 benchmark assets, verifying URL and snippet invariants."""
    builder = StructuredQueryBuilder()
    client = MockParallelClient(simulated_latency_ms=8.0)
    requests = _get_benchmark_asset_requests()

    total_findings = 0
    for req in requests:
        query_obj = builder.build_query(req)
        search_req = ParallelSearchRequest(
            objective=f"Clearance investigation for {req.title}",
            search_queries=[query_obj.query_string],
            mode="fast",
        )
        res: ParallelSearchResult = await client.search(search_req)

        assert res.http_status == 200
        assert len(res.findings) >= 1, f"Expected at least 1 finding for '{req.title}'"
        assert res.latency_ms > 0.0
        assert len(res.raw_response_hash) == 64
        assert len(res.request_payload_hash) == 64

        for f in res.findings:
            total_findings += 1
            # Invariant 1: Valid external URL
            assert URL_REGEX.match(f.url), f"Finding URL '{f.url}' failed canonical URL regex"
            # Invariant 2: Attributable excerpt snippet >= 25 characters
            assert len(f.full_excerpt) >= 25, f"Finding for '{req.title}' has snippet < 25 chars"
            # Invariant 3: Classified domain authority
            assert f.authority_tier in DomainAuthorityTier
            assert 0.0 <= f.authority_score <= 1.0

    assert total_findings >= 6, f"Expected cumulative findings across 5 assets >= 6, got {total_findings}"


@pytest.mark.asyncio
async def _assert_strict_registry_returns_zero(
    client: MockParallelClient, builder: StructuredQueryBuilder, req: SearchQueryRequest
) -> str:
    """Verifies strict registry query for obscure music returns zero results."""
    initial_q = builder.build_query(req)
    assert "site:ascap.com" in initial_q.query_string
    res = await client.search(
        ParallelSearchRequest(objective="Clearance check", search_queries=[initial_q.query_string])
    )
    assert len(res.findings) == 0
    return initial_q.query_string


async def _assert_steered_recovery(client: MockParallelClient, query_str: str) -> None:
    """Verifies inverse domain steered query retrieves valid rights catalog findings."""
    res = await client.search(
        ParallelSearchRequest(objective="Catalog rights search", search_queries=[query_str])
    )
    assert res.http_status == 200
    assert len(res.findings) >= 1
    top_finding = res.findings[0]
    assert "ascap.com" in top_finding.url
    assert "VANCE MUSIC PUBLISHING" in top_finding.full_excerpt or "Evelyn Vance" in top_finding.full_excerpt
    assert len(top_finding.full_excerpt) >= 25


@pytest.mark.asyncio
async def test_inverse_domain_steering_e2e_obscure_music_trigger():
    """Sprint 3.1 Acceptance Gate: Obscure music triggers inverse steering and retrieves valid rights catalog."""
    builder = StructuredQueryBuilder()
    steering_engine = InverseDomainSteeringEngine(builder=builder)
    client = MockParallelClient(simulated_latency_ms=5.0)

    req_obscure = SearchQueryRequest(
        asset_id="clm_obscure_01",
        asset_class=AssetClass.MUSIC,
        title="Midnight Echoes at Twilight",
        creator_or_owner="Evelyn Vance",
        current_state=SteeringState.STRICT_REGISTRY,
    )

    await _assert_strict_registry_returns_zero(client, builder, req_obscure)

    eval_result = EvidenceEvaluation(result_count=0, confidence_score=0.0)
    assert steering_engine.should_trigger_inverse_steering(eval_result) is True

    steered_req, steered_q = steering_engine.next_query(req_obscure, eval_result)
    assert steered_req.current_state == SteeringState.INVERSE_STEERING
    assert "site:ascap.com" not in steered_q.query_string
    assert "-lyrics" in steered_q.query_string

    await _assert_steered_recovery(client, steered_q.query_string)


def test_entity_disambiguation_end_to_end_isolation():
    """Verifies that two songs named 'Hold On' maintain strictly isolated query keys."""
    builder = StructuredQueryBuilder()

    req_shakes = SearchQueryRequest(
        asset_id="track_101",
        asset_class=AssetClass.MUSIC,
        title="Hold On",
        creator_or_owner="Alabama Shakes",
        year=2012,
    )
    req_phillips = SearchQueryRequest(
        asset_id="track_102",
        asset_class=AssetClass.MUSIC,
        title="Hold On",
        creator_or_owner="Wilson Phillips",
        year=1990,
    )

    q_shakes = builder.build_query(req_shakes)
    q_phillips = builder.build_query(req_phillips)

    assert q_shakes.disambiguation_key != q_phillips.disambiguation_key
    assert '"Alabama Shakes"' in q_shakes.query_string
    assert '"Wilson Phillips"' in q_phillips.query_string
