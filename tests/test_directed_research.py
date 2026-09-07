"""
tests/test_directed_research.py

Comprehensive test suite for counsel directive sanitization and directed clearance research.
Sprint 4.3: Counsel Rejection & Directed Re-Investigation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock
import pytest

from backend.agents.research.directed_research import (
    DirectedQueryReformulator,
    DirectedResearchCoordinator,
)
from backend.agents.research.directed_research_sanitizer import (
    DirectiveSanitizer,
    strip_conversational_filler,
)
from backend.agents.research.directed_research_types import (
    DirectedSearchRequest,
    DirectiveConstraintType,
    DirectiveSanitizationError,
)
from backend.services.parallel_service import ParallelSearchService


def test_strip_conversational_lawyer_filler() -> None:
    """Verifies that lawyer filler phrases and leading prepositions are stripped."""
    t1 = "Counsel advises we need to re-search ASCAP specifically for 1972 live adaptation rights in US."
    s1 = strip_conversational_filler(t1)
    assert "Counsel advises" not in s1
    assert "re-search" not in s1
    assert "specifically" not in s1
    assert "ASCAP" in s1 and "1972" in s1 and "live adaptation" in s1

    t2 = "I think we need to check Sony and CBS for master recording rights"
    s2 = strip_conversational_filler(t2)
    assert "I think we need to" not in s2
    assert "check" not in s2
    assert "Sony" in s2 and "CBS" in s2

    t3 = "Please check BMI for sync license in UK"
    s3 = strip_conversational_filler(t3)
    assert "Please check" not in s3
    assert "BMI" in s3 and "sync license" in s3


def test_extract_explicit_entities() -> None:
    """Tests case-insensitive extraction of PROs, registries, and major corporate entities."""
    sanitizer = DirectiveSanitizer()
    directive = "Check ascap, bmi, sony, cbs, warner, and universal records"
    result = sanitizer.sanitize(directive)

    for expected in ["ASCAP", "BMI", "Sony", "CBS", "Warner", "Universal"]:
        assert expected in result.extracted_entities

    reg_values = [c.value for c in result.extracted_constraints if c.constraint_type == DirectiveConstraintType.REGISTRY]
    ent_values = [c.value for c in result.extracted_constraints if c.constraint_type == DirectiveConstraintType.ENTITY]
    assert "ASCAP" in reg_values and "BMI" in reg_values
    assert "Sony" in ent_values and "Universal" in ent_values


def test_extract_years() -> None:
    """Tests extraction of 4-digit calendar years."""
    sanitizer = DirectiveSanitizer()
    result = sanitizer.sanitize("Investigate 1972 original release, 1958 registration, and 2026 sync renewal")
    assert result.extracted_years == [1958, 1972, 2026]
    yr_constraints = [c for c in result.extracted_constraints if c.constraint_type == DirectiveConstraintType.YEAR]
    assert len(yr_constraints) == 3
    assert {c.value for c in yr_constraints} == {"1958", "1972", "2026"}


def test_extract_territories() -> None:
    """Tests extraction of jurisdiction and territory codes."""
    sanitizer = DirectiveSanitizer()
    result = sanitizer.sanitize("Confirm rights across US, UK, Worldwide, and North America territories")
    for terr in ["US", "UK", "Worldwide", "North America"]:
        assert terr in result.extracted_territories
    terr_constraints = [c.value for c in result.extracted_constraints if c.constraint_type == DirectiveConstraintType.TERRITORY]
    assert set(terr_constraints) == {"US", "UK", "Worldwide", "North America"}


def test_extract_rights_terms() -> None:
    """Tests extraction of rights scopes (master recording, sync license, live adaptation, public domain)."""
    sanitizer = DirectiveSanitizer()
    result = sanitizer.sanitize(
        "Verify master recording, sync license, live adaptation rights, and public domain status."
    )
    right_constraints = [c.value for c in result.extracted_constraints if c.constraint_type == DirectiveConstraintType.RIGHT_SCOPE]
    assert "master recording" in right_constraints
    assert "sync license" in right_constraints
    assert "live adaptation" in right_constraints
    assert "public domain" in right_constraints


def test_directive_sanitizer_validation_error() -> None:
    """Verifies that empty or whitespace directive raises DirectiveSanitizationError."""
    sanitizer = DirectiveSanitizer()
    with pytest.raises(DirectiveSanitizationError):
        sanitizer.sanitize("   ")


def test_query_reformulator_primary_and_probes() -> None:
    """Verifies synthesis of primary, registry-targeted, and adversarial probe queries."""
    reformulator = DirectedQueryReformulator()
    request = DirectedSearchRequest(
        title="Hold On",
        artist_or_author="Alabama Shakes",
        raw_directive="Counsel advises we need to re-search ASCAP specifically for 1972 live adaptation rights in US.",
    )
    queries = reformulator.reformulate_queries(request)
    assert len(queries) >= 2
    primary = queries[0]
    assert '"Hold On"' in primary
    assert '"Alabama Shakes"' in primary
    assert "ASCAP" in primary
    assert "1972" in primary
    assert '"live adaptation"' in primary
    assert any("dispute OR infringement OR assignment" in q for q in queries)


def test_query_reformulator_without_artist() -> None:
    """Tests query reformulation when creator/artist is omitted."""
    reformulator = DirectedQueryReformulator()
    request = DirectedSearchRequest(
        title="Midnight Serenade",
        raw_directive="Please check BMI for master recording rights in Worldwide",
    )
    queries = reformulator.reformulate_queries(request)
    assert len(queries) >= 1
    assert '"Midnight Serenade"' in queries[0]
    assert "BMI" in queries[0]
    assert '"master recording"' in queries[0]
    assert "Worldwide" in queries[0]


@pytest.mark.asyncio
async def test_directed_research_coordinator_execution() -> None:
    """Tests end-to-end directed search execution using offline fallback service."""
    service = ParallelSearchService(use_fallback=True)
    coordinator = DirectedResearchCoordinator(search_service=service)
    request = DirectedSearchRequest(
        title="Noir Detective",
        artist_or_author="Vintage Comics",
        raw_directive="Counsel directs us to check LOC for 1958 public domain renewal in US",
        timeout_seconds=10.0,
    )
    result = await coordinator.execute_directed_search(request)
    assert result.status == "success"
    assert result.title == "Noir Detective"
    assert len(result.reformulated_queries) >= 1
    assert len(result.snapshots) >= 1
    assert result.execution_time_seconds <= 15.0
    assert any(c.value == "1958" for c in result.constraints_applied)
    assert any(c.value == "public domain" for c in result.constraints_applied)


@pytest.mark.asyncio
async def test_directed_research_coordinator_timeout_handling() -> None:
    """Tests strict enforcement of hard execution timeout (15.0s max ceiling)."""
    slow_service = AsyncMock(spec=ParallelSearchService)
    async def slow_search(*args, **kwargs):
        await asyncio.sleep(0.3)
    slow_service.search.side_effect = slow_search

    coordinator = DirectedResearchCoordinator(search_service=slow_service, default_timeout=0.05)
    request = DirectedSearchRequest(
        title="Slow Track",
        raw_directive="Check BMI for master recording",
        timeout_seconds=0.05,
    )
    result = await coordinator.execute_directed_search(request)
    assert result.status == "timeout"
    assert "timed out" in (result.error_message or "").lower()
    assert result.snapshots == []


@pytest.mark.asyncio
async def test_directed_research_coordinator_error_handling() -> None:
    """Tests fail-closed error handling when underlying search service encounters unexpected failure."""
    failing_service = AsyncMock(spec=ParallelSearchService)
    failing_service.search.side_effect = RuntimeError("Network socket disconnect")

    coordinator = DirectedResearchCoordinator(search_service=failing_service)
    request = DirectedSearchRequest(
        title="Faulty Track",
        raw_directive="Check Sony for sync license",
    )
    result = await coordinator.execute_directed_search(request)
    assert result.status == "error"
    assert "Network socket disconnect" in (result.error_message or "")
    assert result.snapshots == []
