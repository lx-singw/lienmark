"""
backend/orchestration/shared_limits.py

Shared investigation limits, cycle prevention, and deadline governance.
Enforces shared 5-query budget across parent and child subgoals, explicit retry
and batch query accounting, separate inspection bounds, and 30s hard deadline.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field


class InvestigationLimitError(Exception):
    """Base exception for investigation governance violations."""
    pass


class MaxQueryLimitReachedError(InvestigationLimitError):
    """Raised when total queries exceed the shared investigation cap."""
    pass


class MaxInspectionLimitReachedError(InvestigationLimitError):
    """Raised when inspection calls exceed their separate bound."""
    pass


class CycleDetectedError(InvestigationLimitError):
    """Raised when an entity or query repetition cycle is detected."""
    pass


class DeadlineExceededError(InvestigationLimitError):
    """Raised when investigation exceeds the 30-second execution deadline."""
    pass


def normalize_entity(name: str) -> str:
    """Normalizes an entity name for deduplication and cycle tracking."""
    return " ".join(name.strip().lower().split())


def compute_query_fingerprint(query: str) -> str:
    """Computes SHA-256 fingerprint from whitespace-normalized query."""
    normalized = " ".join(query.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class QueryRecord(BaseModel):
    """Immutable audit record for a single executed query string."""
    model_config = ConfigDict(frozen=True)

    query: str = Field(..., min_length=1)
    fingerprint: str = Field(..., min_length=1)
    is_retry: bool = False
    is_batched: bool = False
    subgoal_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SharedInvestigationGovernor:
    """
    Coordinates shared query and inspection limits across an entire claim investigation,
    spanning root and all child subgoals (including inverse and adversarial branches).
    """

    def __init__(
        self,
        investigation_id: str,
        max_queries: int = 5,
        max_inspections: int = 5,
        max_depth: int = 2,
        deadline_seconds: float = 30.0,
        clock: Optional[Any] = None,
    ) -> None:
        self.investigation_id = investigation_id
        self.max_queries = max(1, max_queries)
        self.max_inspections = max(1, max_inspections)
        self.max_depth = max(0, max_depth)
        self.deadline_seconds = max(1.0, float(deadline_seconds))
        self._clock = clock or time.time
        self.start_time = self._clock()

        self.total_queries_executed = 0
        self.total_inspections_executed = 0
        self.retry_count = 0
        self.batched_query_count = 0

        self.visited_entities: Set[str] = set()
        self.query_fingerprints: Set[str] = set()
        self.query_history: List[QueryRecord] = []
        self.partial_findings: List[Dict[str, Any]] = []

    def check_deadline(self) -> bool:
        """Returns True if the 30-second execution deadline has elapsed."""
        return (self._clock() - self.start_time) >= self.deadline_seconds

    @property
    def remaining_time_seconds(self) -> float:
        """Returns remaining execution window before 30-second deadline."""
        elapsed = self._clock() - self.start_time
        return max(0.0, self.deadline_seconds - elapsed)

    @property
    def is_query_budget_exhausted(self) -> bool:
        """Returns True if the 5-query shared budget is fully consumed."""
        return self.total_queries_executed >= self.max_queries

    def check_cycle(
        self,
        entity_name: str,
        query: Optional[str] = None,
        ancestor_entities: Optional[Set[str]] = None,
    ) -> None:
        """Stops cycles by checking ancestor entities and query fingerprints."""
        norm_entity = normalize_entity(entity_name)
        if ancestor_entities and norm_entity in {normalize_entity(e) for e in ancestor_entities}:
            raise CycleDetectedError(
                f"Cycle detected: entity '{entity_name}' was already investigated in ancestor path."
            )
        if query:
            fp = compute_query_fingerprint(query)
            if fp in self.query_fingerprints:
                raise CycleDetectedError(
                    f"Duplicate query cycle: fingerprint '{fp}' already executed."
                )

    def _validate_query_limits(
        self, query: str, entity_name: Optional[str],
        is_retry: bool, check_cycle_entities: Optional[Set[str]],
    ) -> str:
        """Validates query limits, deadline, and cycle checks."""
        if self.check_deadline():
            raise DeadlineExceededError(f"Execution deadline ({self.deadline_seconds}s) exceeded for {self.investigation_id}.")
        if self.is_query_budget_exhausted:
            raise MaxQueryLimitReachedError(f"Shared query budget exhausted ({self.max_queries}) for {self.investigation_id}.")
        fp = compute_query_fingerprint(query)
        if not is_retry:
            if fp in self.query_fingerprints:
                raise CycleDetectedError(f"Duplicate query cycle: '{query}' already executed.")
            if check_cycle_entities and entity_name:
                self.check_cycle(entity_name, ancestor_entities=check_cycle_entities)
        return fp

    def record_query(
        self, query: str, entity_name: Optional[str] = None, is_retry: bool = False,
        is_batched: bool = False, subgoal_id: Optional[str] = None,
        check_cycle_entities: Optional[Set[str]] = None,
    ) -> QueryRecord:
        """Records query explicitly counting retries and batches against shared limit."""
        fp = self._validate_query_limits(query, entity_name, is_retry, check_cycle_entities)
        self.total_queries_executed += 1
        if is_retry: self.retry_count += 1
        if is_batched: self.batched_query_count += 1
        self.query_fingerprints.add(fp)
        if entity_name: self.visited_entities.add(normalize_entity(entity_name))
        record = QueryRecord(
            query=query, fingerprint=fp, is_retry=is_retry,
            is_batched=is_batched, subgoal_id=subgoal_id, timestamp=self._clock(),
        )
        self.query_history.append(record)
        return record

    def record_query_batch(
        self,
        queries: List[str],
        entity_names: Optional[List[str]] = None,
        is_retry: bool = False,
        subgoal_id: Optional[str] = None,
    ) -> List[QueryRecord]:
        """
        Explicitly counts each batched query string against the shared limit.
        """
        records: List[QueryRecord] = []
        for i, q in enumerate(queries):
            e_name = entity_names[i] if entity_names and i < len(entity_names) else None
            rec = self.record_query(
                query=q, entity_name=e_name, is_retry=is_retry,
                is_batched=len(queries) > 1, subgoal_id=subgoal_id,
            )
            records.append(rec)
        return records

    def record_inspection(self, source_url_or_id: str) -> None:
        """
        Separately bounds inspection calls without decrementing search queries.
        """
        if self.check_deadline():
            raise DeadlineExceededError(f"Execution deadline exceeded before inspecting {source_url_or_id}.")
        if self.total_inspections_executed >= self.max_inspections:
            raise MaxInspectionLimitReachedError(
                f"Inspection limit reached ({self.max_inspections}) for {self.investigation_id}."
            )
        self.total_inspections_executed += 1

    def add_partial_finding(self, finding: Dict[str, Any]) -> None:
        """Persists partial evidence finding gathered during investigation."""
        self.partial_findings.append(finding)

    def get_partial_unresolved_results(self, reason: str = "budget_or_deadline_exhausted") -> Dict[str, Any]:
        """
        Returns partial unresolved results gracefully when budget or 30s deadline hits.
        Ensures execution never hangs.
        """
        return {
            "status": "PARTIAL_UNRESOLVED",
            "investigation_id": self.investigation_id,
            "reason": reason,
            "queries_executed": self.total_queries_executed,
            "inspections_executed": self.total_inspections_executed,
            "retries_counted": self.retry_count,
            "batched_queries_counted": self.batched_query_count,
            "deadline_exceeded": self.check_deadline(),
            "elapsed_seconds": round(self._clock() - self.start_time, 3),
            "partial_findings": list(self.partial_findings),
            "visited_entities": list(self.visited_entities),
            "query_fingerprints": list(self.query_fingerprints),
        }
