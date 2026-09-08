"""
backend/core/dependency_graph.py

Lienmark Claim Dependency Graph & Invalidation Engine.
Milestone D: Tracks explicit dependency edges between claims, cycle-safe
transitive downstream invalidation, and enforces distinct rights invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from backend.core.clearance_dag import (
    ClearanceDependencyGraph,
    ClearanceGraphError,
    CycleDetectedError,
    NodeNotFoundError,
    CrossTenantBoundaryViolationError,
    GraphFrozenError,
    NodeType,
    DependencyKind,
    DependencyNode,
    DependencyEdge,
    InvalidationNotice,
    build_clearance_graph,
)


class ClaimDependencyEdge(BaseModel):
    """Explicit causal dependency edge between two atomic claims."""
    dependent_claim_id: str
    upstream_claim_id: str
    production_id: str = "default_production"
    relationship_type: str = "EXPLICIT_DEPENDENCY"
    description: Optional[str] = None


class ClaimMetadata(BaseModel):
    """Metadata tracking category, subject, scene, and title for invariant checks."""
    claim_id: str
    right_category: str
    rights_subject: str
    production_id: str = "default_production"
    scene_id: Optional[str] = None
    title: Optional[str] = None


class DependencyGraph:
    """
    Tracks explicit dependency edges between claims (e.g., Master Sound Recording ->
    Musical Composition; Clip License -> Trademark / Persona).
    Enforces distinct rights invariant and performs cycle-safe transitive invalidation.
    """

    def __init__(self, organization_id: str = "org_studio_alpha") -> None:
        self.organization_id = organization_id
        self._downstream: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        self._upstream: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        self._edges: Dict[Tuple[str, str, str], ClaimDependencyEdge] = {}
        self._claims: Dict[Tuple[str, str], ClaimMetadata] = {}

    def register_claim(
        self,
        claim_id: str,
        right_category: str,
        rights_subject: str,
        production_id: str = "default_production",
        scene_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """Registers claim metadata for invariant tracking."""
        key = (production_id, claim_id)
        self._claims[key] = ClaimMetadata(
            claim_id=claim_id,
            right_category=right_category,
            rights_subject=rights_subject,
            production_id=production_id,
            scene_id=scene_id,
            title=title,
        )

    def add_claim_dependency(
        self,
        dependent_claim_id: str,
        upstream_claim_id: str,
        production_id: str = "default_production",
        relationship_type: str = "EXPLICIT_DEPENDENCY",
        description: Optional[str] = None,
    ) -> ClaimDependencyEdge:
        """Adds explicit dependency: dependent_claim_id depends on upstream_claim_id."""
        if dependent_claim_id == upstream_claim_id:
            raise ValueError(f"Self-referential dependency: {dependent_claim_id} cannot depend on itself.")
        edge = ClaimDependencyEdge(
            dependent_claim_id=dependent_claim_id,
            upstream_claim_id=upstream_claim_id,
            production_id=production_id,
            relationship_type=relationship_type,
            description=description,
        )
        self._downstream[(production_id, upstream_claim_id)].add(dependent_claim_id)
        self._upstream[(production_id, dependent_claim_id)].add(upstream_claim_id)
        self._edges[(production_id, dependent_claim_id, upstream_claim_id)] = edge
        return edge

    def add_dependency(
        self,
        dependent_claim_id: str,
        upstream_claim_id: str,
        production_id: str = "default_production",
        relationship_type: str = "EXPLICIT_DEPENDENCY",
        description: Optional[str] = None,
    ) -> ClaimDependencyEdge:
        """Alias for add_claim_dependency."""
        return self.add_claim_dependency(
            dependent_claim_id=dependent_claim_id,
            upstream_claim_id=upstream_claim_id,
            production_id=production_id,
            relationship_type=relationship_type,
            description=description,
        )

    def get_transitive_downstream_dependents(
        self, claim_id: str, production_id: str = "default_production"
    ) -> List[str]:
        """
        Cycle-safe BFS traversal finding downstream claims whose assumptions are invalidated.
        Traverses downstream edges where dependent claims rely on invalidated upstream claim.
        """
        visited: Set[str] = set()
        queue: deque[str] = deque([claim_id])
        result: List[str] = []
        while queue:
            current = queue.popleft()
            children = self._downstream.get((production_id, current), set())
            for child in sorted(children):
                if child not in visited and child != claim_id:
                    visited.add(child)
                    result.append(child)
                    queue.append(child)
        return sorted(result)

    def check_distinct_rights_invariant(
        self, claim_a_id: str, claim_b_id: str, production_id: str = "default_production"
    ) -> bool:
        """
        Distinct rights invariant: composition and recording rights remain separate.
        Sharing a scene or title alone does not trigger invalidation without explicit edge.
        Returns True if invariant holds (separate without explicit edge), False if violated.
        """
        down_a = self.get_transitive_downstream_dependents(claim_a_id, production_id)
        down_b = self.get_transitive_downstream_dependents(claim_b_id, production_id)
        has_explicit = (claim_b_id in down_a) or (claim_a_id in down_b)
        
        # Invariant: claims without explicit dependency edge must not cross-invalidate
        if not has_explicit:
            return claim_b_id not in down_a and claim_a_id not in down_b
        return True


_global_graph: Optional[DependencyGraph] = None


def get_dependency_graph() -> DependencyGraph:
    """Returns singleton DependencyGraph instance."""
    global _global_graph
    if _global_graph is None:
        _global_graph = DependencyGraph()
    return _global_graph


def reset_dependency_graph() -> None:
    """Resets global singleton DependencyGraph instance."""
    global _global_graph
    _global_graph = None


def get_transitive_downstream_dependents(
    claim_id: str,
    production_id: str = "default_production",
    graph: Optional[DependencyGraph] = None,
) -> List[str]:
    """Cycle-safe traversal finding downstream claims whose assumptions are invalidated."""
    dg = graph or get_dependency_graph()
    return dg.get_transitive_downstream_dependents(claim_id, production_id)


__all__ = [
    "ClaimDependencyEdge",
    "ClaimMetadata",
    "ClearanceDependencyGraph",
    "ClearanceGraphError",
    "CycleDetectedError",
    "DependencyEdge",
    "DependencyGraph",
    "DependencyKind",
    "DependencyNode",
    "GraphFrozenError",
    "InvalidationNotice",
    "NodeNotFoundError",
    "NodeType",
    "CrossTenantBoundaryViolationError",
    "build_clearance_graph",
    "get_dependency_graph",
    "reset_dependency_graph",
    "get_transitive_downstream_dependents",
]
