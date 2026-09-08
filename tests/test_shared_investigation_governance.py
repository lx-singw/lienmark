"""
tests/test_shared_investigation_governance.py

Test suite for shared investigation governance across entire claim investigation.
Verifies max 5 shared queries across parent and child subgoals, retry accounting,
batch query accounting, separate inspection bounds, cycle stopping, and 30s deadline.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import time
import pytest

from backend.domain.models import AtomicRightsClaim, CensusDisposition
from backend.orchestration.adk_pipeline import CoordinatorAction, EvidenceDrivenCoordinator
from backend.orchestration.shared_limits import (
    CycleDetectedError,
    DeadlineExceededError,
    MaxInspectionLimitReachedError,
    MaxQueryLimitReachedError,
    SharedInvestigationGovernor,
)


class MockClock:
    """Controllable clock for testing 30s deadlines."""
    def __init__(self, start: float = 1000.0):
        self.time = start
    def __call__(self) -> float:
        return self.time
    def advance(self, seconds: float) -> None:
        self.time += seconds


def test_shared_max_five_queries_across_parent_and_children():
    """Verifies max 5 queries shared across parent and all child subgoals."""
    gov = SharedInvestigationGovernor(investigation_id="inv_001", max_queries=5)

    # Root query
    gov.record_query("root query for composition", entity_name="Entity A")
    assert gov.total_queries_executed == 1

    # Child subgoal 1 query (e.g. master recording)
    gov.record_query("child query master recording", subgoal_id="sg_master")
    assert gov.total_queries_executed == 2

    # Child subgoal 2 query (e.g. publishing)
    gov.record_query("child query publishing", subgoal_id="sg_pub")
    assert gov.total_queries_executed == 3

    # Inverse steering query
    gov.record_query("inverse steering query", subgoal_id="sg_pub")
    assert gov.total_queries_executed == 4

    # Adversarial probe query
    gov.record_query("adversarial probe query", subgoal_id="sg_adv")
    assert gov.total_queries_executed == 5
    assert gov.is_query_budget_exhausted is True

    # 6th query must raise MaxQueryLimitReachedError
    with pytest.raises(MaxQueryLimitReachedError):
        gov.record_query("overflow 6th query")


def test_explicitly_counts_retries_and_batched_query_strings():
    """Verifies retries and each batched query string count against the 5-query budget."""
    gov = SharedInvestigationGovernor(investigation_id="inv_002", max_queries=5)

    # Batch of 3 query strings explicitly consumes 3 queries
    batch = ["query_batch_1", "query_batch_2", "query_batch_3"]
    records = gov.record_query_batch(batch)
    assert len(records) == 3
    assert gov.total_queries_executed == 3
    assert gov.batched_query_count == 3

    # Retry of query_batch_1 explicitly increments queries and retries
    rec_retry = gov.record_query("query_batch_1_retry", is_retry=True)
    assert rec_retry.is_retry is True
    assert gov.total_queries_executed == 4
    assert gov.retry_count == 1

    # 5th query
    gov.record_query("final_query_5")
    assert gov.total_queries_executed == 5
    assert gov.is_query_budget_exhausted is True


def test_separately_bounded_inspection_calls():
    """Verifies inspection calls are separately bounded without decrementing search queries."""
    gov = SharedInvestigationGovernor(investigation_id="inv_003", max_queries=5, max_inspections=3)

    gov.record_query("query 1")
    assert gov.total_queries_executed == 1

    # Inspections do not decrement search query count
    gov.record_inspection("https://cocatalog.loc.gov/1")
    gov.record_inspection("https://cocatalog.loc.gov/2")
    gov.record_inspection("https://cocatalog.loc.gov/3")
    assert gov.total_inspections_executed == 3
    assert gov.total_queries_executed == 1  # Still 1!

    # 4th inspection exceeds separate bound
    with pytest.raises(MaxInspectionLimitReachedError):
        gov.record_inspection("https://cocatalog.loc.gov/4")


def test_root_depth_and_cycle_stopping():
    """Verifies cycle stopping, visited entities, and query fingerprint persistence."""
    gov = SharedInvestigationGovernor(investigation_id="inv_004", max_depth=2)
    assert gov.max_depth == 2

    # Record first query
    gov.record_query("Creedence Clearwater Revival catalog", entity_name="Creedence Clearwater Revival")
    assert "creedence clearwater revival" in gov.visited_entities
    assert len(gov.query_fingerprints) == 1

    # Exact duplicate query triggers CycleDetectedError
    with pytest.raises(CycleDetectedError) as exc_dup:
        gov.record_query("Creedence Clearwater Revival catalog")
    assert "Duplicate query cycle" in str(exc_dup.value)

    # Proposed hop to an entity already in ancestor path triggers CycleDetectedError
    with pytest.raises(CycleDetectedError) as exc_cycle:
        gov.check_cycle("Creedence Clearwater Revival", ancestor_entities={"Creedence Clearwater Revival"})
    assert "Cycle detected" in str(exc_cycle.value)


def test_thirty_second_execution_deadline_graceful_unresolved():
    """Verifies 30s deadline stops execution gracefully without hanging."""
    clock = MockClock(start=100.0)
    gov = SharedInvestigationGovernor(investigation_id="inv_005", deadline_seconds=30.0, clock=clock)

    gov.record_query("first fast query")
    gov.add_partial_finding({"source": "LOC", "title": "Partial Result 1"})

    # Advance clock past 30 seconds
    clock.advance(30.1)
    assert gov.check_deadline() is True

    # Calling record_query after deadline raises DeadlineExceededError
    with pytest.raises(DeadlineExceededError):
        gov.record_query("late query after deadline")

    # Governor returns partial unresolved results gracefully without hanging
    partial = gov.get_partial_unresolved_results()
    assert partial["status"] == "PARTIAL_UNRESOLVED"
    assert partial["deadline_exceeded"] is True
    assert len(partial["partial_findings"]) == 1
    assert partial["queries_executed"] == 1


@pytest.mark.asyncio
async def test_coordinator_integrates_shared_limits_and_split():
    """Verifies EvidenceDrivenCoordinator uses shared limits across parent and split children."""
    coord = EvidenceDrivenCoordinator(use_fallback=True)
    parent_claim = AtomicRightsClaim(
        claim_id="clm_parent_music", occurrence_id="occ_pm",
        occurrence_lineage_id="music_cue_track_01",
        right_category="composite", rights_subject="Midnight Cue Track 01",
    )
    coord.register_claim(parent_claim)

    # Split composite claim into composition and master
    children = coord.split_claim(parent_claim)
    assert len(children) == 2
    comp_claim, master_claim = children[0], children[1]

    # Both parent and children share the SAME limits_governor on coordinator
    assert coord.limits_governor.total_queries_executed == 0

    # Execute search on comp claim
    res1 = await coord.execute_action(CoordinatorAction.ACT_02_SEARCH_PUBLIC_SOURCES, comp_claim)
    assert res1["status"] == "SUCCESS"
    assert coord.limits_governor.total_queries_executed == 1

    # Execute adversarial probe on master claim
    res2 = await coord.execute_action(CoordinatorAction.ACT_05_ADVERSARIAL_DISCONFIRMATION, master_claim)
    assert res2["status"] == "SUCCESS"
    assert coord.limits_governor.total_queries_executed == 2
