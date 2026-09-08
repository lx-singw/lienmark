"""
tests/test_conflict_arbitration.py

Canonical test suite for Sprint 3.3 / Milestone C:
Corroboration Engine, Dual-Layer Apollo 11 Conflict Arbiter,
and Form E&O-2026 Exceptions Schedule Routing.
"""

import pytest

from backend.core.conflict_arbiter import (
    ConflictArbiter,
    CorroborationEngine,
    arbitrate_claim_conflicts,
)
from backend.core.conflict_types import (
    ArbitrationResult,
    ClaimStatusAssertion,
    ConflictStance,
    EvidenceFinding,
    RightsLayer,
    SourceAuthorityTier,
)
from backend.domain.models import ExceptionsScheduleItem
from backend.services.circuit_breaker import CircuitBreaker
from backend.services.circuit_breaker_types import CircuitState


@pytest.fixture
def nasa_apollo_finding() -> EvidenceFinding:
    return EvidenceFinding(
        finding_id="find_nasa_001",
        source_title="NASA Image and Video Library - Apollo 11 Lunar Transmission",
        source_url="https://images.nasa.gov/details/as11-40-5874",
        domain="images.nasa.gov",
        excerpt="NASA astronaut broadcasts from lunar surface. Work of U.S. Federal Government under 17 U.S.C. 105.",
        asserted_status=ClaimStatusAssertion.PUBLIC_DOMAIN,
        asserted_owner="United States Federal Government",
        rights_layer=RightsLayer.UNDERLYING_WORK,
        authority_tier=SourceAuthorityTier.TIER_1_GOVERNMENT_REGISTRY,
        is_federal_work=True,
        statutory_citation="17 U.S.C. § 105",
    )


@pytest.fixture
def cbs_apollo_finding() -> EvidenceFinding:
    return EvidenceFinding(
        finding_id="find_cbs_002",
        source_title="CBS News Archival Broadcast - Walter Cronkite Apollo 11 Special",
        source_url="https://cbsnews.com/archives/apollo-11-coverage",
        domain="cbsnews.com",
        excerpt="CBS News original television broadcast commentary and edited master recording. All rights reserved.",
        asserted_status=ClaimStatusAssertion.LICENSING_REQUIRED,
        asserted_owner="CBS Broadcasting Inc.",
        rights_layer=RightsLayer.RECORDING_OR_BROADCAST_MASTER,
        authority_tier=SourceAuthorityTier.TIER_2_ORGANIZATION_PRO_NEWS,
        is_federal_work=False,
    )


def _assert_apollo_conflict_invariants(result: ArbitrationResult) -> None:
    """Verifies invariant assertions for Apollo 11 dual-layer arbitration result."""
    assert result.conflict_detected is False
    assert result.overall_stance == ConflictStance.NEUTRAL
    assert result.risk_score == 0.30
    assert result.dual_layer is not None
    assert result.route_to_exceptions_schedule is False
    assert result.exceptions_schedule_state == "carried_forward"


@pytest.mark.asyncio
async def test_canonical_apollo_11_dual_layer_conflict(nasa_apollo_finding, cbs_apollo_finding):
    """
    Acceptance Gate for Milestone C:
    Apollo 11 audio clip scenario feeding NASA official archive vs CBS broadcast archive.
    Asserts circuit breaker stability, statutory federal rule, dual layer distinction.
    """
    breaker = CircuitBreaker("parallel_search_apollo")
    res_nasa = await breaker.call_async(lambda: nasa_apollo_finding)
    res_cbs = await breaker.call_async(lambda: cbs_apollo_finding)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_telemetry().consecutive_failures == 0

    assert res_nasa.is_federal_work is True
    assert "17 U.S.C. § 105" in res_nasa.statutory_citation
    assert res_nasa.asserted_status == ClaimStatusAssertion.PUBLIC_DOMAIN

    pair_eval = CorroborationEngine.classify_pair(res_nasa, res_cbs)
    assert pair_eval.stance == ConflictStance.NEUTRAL
    assert pair_eval.is_dual_layer_conflict is True

    result = ConflictArbiter.arbitrate(
        claim_id="clm_apollo_11",
        findings=[res_nasa, res_cbs],
        asset_type="archival_footage",
    )
    _assert_apollo_conflict_invariants(result)


def test_apollo_exceptions_schedule_item_formatting(nasa_apollo_finding, cbs_apollo_finding):
    """Verifies arbitration result conversion to Form E&O-2026 ExceptionsScheduleItem."""
    result = ConflictArbiter.arbitrate("clm_apollo_11", [nasa_apollo_finding, cbs_apollo_finding])
    item = ConflictArbiter.to_exceptions_schedule_item(
        result=result,
        asset_type="archival_footage",
        description="Apollo 11 moon landing broadcast footage",
        scene_or_timecode="00:14:22",
    )

    assert isinstance(item, ExceptionsScheduleItem)
    assert item.stable_lineage_key == "clm_apollo_11"
    assert item.v8_evaluation_state == "carried_forward"
    assert item.invalidation_reason is None
    assert item.counsel_action == "Leave recording clearance outstanding."
    assert len(item.evidence_citations) == 2
    assert any(c["domain"] == "images.nasa.gov" for c in item.evidence_citations)


def test_corroborating_public_domain_sources(nasa_apollo_finding):
    """Verifies corroboration when independent sources agree on public domain status."""
    nara_finding = EvidenceFinding(
        finding_id="find_nara_003",
        source_title="National Archives (NARA) - Apollo 11 Mission Audio Clearance",
        source_url="https://archives.gov/apollo-11",
        domain="archives.gov",
        excerpt="Original audio broadcasts created by NASA personnel are unrestricted public domain records.",
        asserted_status=ClaimStatusAssertion.PUBLIC_DOMAIN,
        asserted_owner="United States Federal Government",
        authority_tier=SourceAuthorityTier.TIER_1_GOVERNMENT_REGISTRY,
        is_federal_work=True,
    )

    pair_eval = CorroborationEngine.classify_pair(nasa_apollo_finding, nara_finding)
    assert pair_eval.stance == ConflictStance.CORROBORATING

    result = arbitrate_claim_conflicts("clm_corrob", [nasa_apollo_finding, nara_finding])
    assert result.conflict_detected is False
    assert result.overall_stance == ConflictStance.CORROBORATING
    assert result.risk_score == 0.10
    assert result.route_to_exceptions_schedule is False
    assert result.exceptions_schedule_state == "carried_forward"


def test_direct_contradiction_between_ownership_claims():
    """Verifies direct contradiction between public domain assertion and private copyright claim."""
    source_a = EvidenceFinding(
        finding_id="src_a", source_title="LOC Catalog of Copyright Entries",
        excerpt="Copyright expired without renewal. In the public domain.",
        asserted_status=ClaimStatusAssertion.PUBLIC_DOMAIN,
    )
    source_b = EvidenceFinding(
        finding_id="src_b", source_title="Commercial Publisher Database",
        excerpt="Active copyright registered. All rights reserved. Licensing required.",
        asserted_status=ClaimStatusAssertion.COPYRIGHTED,
        asserted_owner="Global Music Corp",
    )

    result = ConflictArbiter.arbitrate("clm_direct_conflict", [source_a, source_b])
    assert result.conflict_detected is True
    assert result.overall_stance == ConflictStance.CONTRADICTORY
    assert result.risk_score == 0.85
    assert result.route_to_exceptions_schedule is True
    assert result.exceptions_schedule_state == "unresolved_exception"


def test_insufficient_and_timeout_fail_closed():
    """Verifies fail-closed behavior for HTTP timeout and rate-limit responses."""
    err_finding = EvidenceFinding(
        finding_id="src_err", source_title="Parallel Search Gateway",
        excerpt="Gateway timeout: search failure",
        http_status=504,
    )
    empty_finding = EvidenceFinding(
        finding_id="src_empty", source_title="Empty Registry Query",
        excerpt="",
        http_status=200,
    )

    assert CorroborationEngine.is_insufficient(err_finding) is True
    assert CorroborationEngine.is_insufficient(empty_finding) is True

    result = ConflictArbiter.arbitrate("clm_timeout", [err_finding, empty_finding])
    assert result.conflict_detected is False
    assert result.overall_stance == ConflictStance.INSUFFICIENT
    assert result.risk_score == 0.65
    assert result.route_to_exceptions_schedule is True
    assert result.exceptions_schedule_state == "unresolved_exception"


def test_neutral_background_mentions():
    """Verifies neutral handling for informational background mentions."""
    finding_1 = EvidenceFinding(
        finding_id="src_info_1", source_title="Film History Blog",
        excerpt="The scene depicts a poster from 1950 hanging on the wall.",
        asserted_status=ClaimStatusAssertion.NEUTRAL_MENTION,
    )
    finding_2 = EvidenceFinding(
        finding_id="src_info_2", source_title="Set Decorator Interview",
        excerpt="We used various era-appropriate set dressing props.",
        asserted_status=ClaimStatusAssertion.NEUTRAL_MENTION,
    )

    result = ConflictArbiter.arbitrate("clm_neutral", [finding_1, finding_2])
    assert result.conflict_detected is False
    assert result.overall_stance == ConflictStance.NEUTRAL
    assert result.risk_score == 0.40
    assert result.route_to_exceptions_schedule is False
    assert result.exceptions_schedule_state == "carried_forward"


def test_mixed_set_insufficient_and_corroborating(nasa_apollo_finding):
    """Verifies robust arbitration when one source fails but others corroborate."""
    nara_finding = EvidenceFinding(
        finding_id="find_nara_004", source_title="National Archives Clearance",
        excerpt="Unrestricted public domain records under 17 U.S.C. 105.",
        asserted_status=ClaimStatusAssertion.PUBLIC_DOMAIN,
    )
    timed_out_finding = EvidenceFinding(
        finding_id="find_timeout", source_title="Timeout Source",
        excerpt="Search timed out", http_status=504,
    )

    result = ConflictArbiter.arbitrate(
        "clm_mixed", [nasa_apollo_finding, nara_finding, timed_out_finding],
    )
    assert result.conflict_detected is False
    assert result.overall_stance == ConflictStance.CORROBORATING
    assert result.risk_score == 0.10


def test_pydantic_v2_model_serialization(nasa_apollo_finding, cbs_apollo_finding):
    """Verifies full roundtrip Pydantic v2 JSON serialization/deserialization."""
    result = ConflictArbiter.arbitrate("clm_ser", [nasa_apollo_finding, cbs_apollo_finding])
    json_data = result.model_dump_json()
    deserialized = ArbitrationResult.model_validate_json(json_data)
    assert deserialized.claim_id == result.claim_id
    assert deserialized.risk_score == result.risk_score
    assert deserialized.dual_layer.is_dual_layer is True
