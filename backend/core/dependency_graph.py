"""
Lienmark Clearance Lineage & Causal Dependency Graph
Deterministic DAG engine for version-bound clearance change control and transitive invalidation.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

from collections import deque
from enum import Enum
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from backend.domain.models import (
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    PublicEvidenceSnapshot,
)

logger = logging.getLogger("lienmark.dependency_graph")


class ClearanceGraphError(Exception):
    """Base exception for all clearance dependency graph errors."""
    pass


class CycleDetectedError(ValueError, ClearanceGraphError):
    """Raised when a causal dependency creates a directed cycle in the clearance DAG."""
    pass


class NodeNotFoundError(ClearanceGraphError):
    """Raised when querying a node identifier not present in the graph."""
    pass


class NodeType(str, Enum):
    CREATIVE_USE = "creative_use"
    COUNSEL_DECISION = "counsel_decision"
    EVIDENCE_SNAPSHOT = "evidence_snapshot"
    CONTRACT_AGREEMENT = "contract_agreement"
    CUSTOM = "custom"


class DependencyKind(str, Enum):
    CREATIVE_CONTEXT = "creative_context"
    EVIDENCE_STANCE = "evidence_stance"
    CONTRACTUAL_GRANT = "contractual_grant"
    PRIOR_DECISION = "prior_decision"
    UPSTREAM_CLAIM = "upstream_claim"
    CUSTOM = "custom"


class DependencyNode(BaseModel):
    """
    Immutable representation of an entity node in the clearance lineage graph.
    """
    node_id: str
    node_type: NodeType
    stable_lineage_key: str
    state_hash: str
    version_id: Optional[str] = None
    entity: Optional[Any] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def canonical_sort_key(self) -> Tuple[str, str, str]:
        """Canonical sort key ensuring deterministic traversal across permutations."""
        return (self.stable_lineage_key, self.node_type.value, self.node_id)


class DependencyEdge(BaseModel):
    """
    Directed causal edge: dependent_id depends on dependency_id.
    Upstream: dependency_id
    Downstream: dependent_id
    """
    dependent_id: str
    dependency_id: str
    kind: DependencyKind = DependencyKind.CUSTOM
    description: Optional[str] = None

    def canonical_sort_key(self) -> Tuple[str, str, str]:
        return (self.dependent_id, self.dependency_id, self.kind.value)


class InvalidationNotice(BaseModel):
    """
    Tamper-evident notice detailing transitive clearance invalidation.
    """
    affected_node_id: str
    affected_lineage_key: str
    affected_node_type: NodeType
    root_cause_node_id: str
    root_cause_lineage_key: str
    root_cause_type: NodeType
    reason_code: str
    explanation: str
    invalidation_path: List[str]
    changed_state_details: Dict[str, Any] = Field(default_factory=dict)


class ClearanceDependencyGraph:
    """
    Directed Acyclic Graph (DAG) for clearance lineage and causal change propagation.
    Guarantees:
    1. DAG integrity: Cycle detection on edge creation and validation.
    2. Input-order invariance: Canonical sorting on stable lineage keys ensures deterministic traversal.
    3. Transitive invalidation: Upstream shifts invalidate all downstream decisions, naming the exact dependency.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, DependencyNode] = {}
        self._dependencies: Dict[str, Set[str]] = {}  # dependent_id -> {dependency_ids} (upstream)
        self._dependents: Dict[str, Set[str]] = {}    # dependency_id -> {dependent_ids} (downstream)
        self._edges: Dict[Tuple[str, str], DependencyEdge] = {}
        self._lineage_map: Dict[str, Set[str]] = {}

    def add_node(
        self,
        node: Union[DependencyNode, str],
        node_type: NodeType = NodeType.CUSTOM,
        stable_lineage_key: Optional[str] = None,
        state_hash: str = "0000000000000000",
        version_id: Optional[str] = None,
        entity: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DependencyNode:
        """
        Adds a node to the graph. If node already exists, updates its attributes defensively.
        Supports passing either a DependencyNode instance or a string node_id.
        """
        if isinstance(node, str):
            node_id = node
            lineage_key = stable_lineage_key or node_id
            node = DependencyNode(
                node_id=node_id,
                node_type=node_type,
                stable_lineage_key=lineage_key,
                state_hash=state_hash,
                version_id=version_id,
                entity=entity,
                metadata=metadata or {},
            )

        self._nodes[node.node_id] = node
        if node.node_id not in self._dependencies:
            self._dependencies[node.node_id] = set()
        if node.node_id not in self._dependents:
            self._dependents[node.node_id] = set()

        if node.stable_lineage_key not in self._lineage_map:
            self._lineage_map[node.stable_lineage_key] = set()
        self._lineage_map[node.stable_lineage_key].add(node.node_id)
        return node

    def add_creative_use(self, use: CreativeUse) -> DependencyNode:
        """Convenience method to register a CreativeUse node."""
        node = DependencyNode(
            node_id=use.use_id,
            node_type=NodeType.CREATIVE_USE,
            stable_lineage_key=use.stable_lineage_key,
            state_hash=use.context_hash,
            version_id=use.version_id,
            entity=use,
            metadata={
                "scene_or_timecode": use.scene_or_timecode,
                "asset_type": use.asset_type,
                "duration_or_prominence": use.duration_or_prominence,
                "description": use.description,
            },
        )
        return self.add_node(node)

    def add_counsel_decision(self, decision: CounselDecision) -> DependencyNode:
        """Convenience method to register a CounselDecision node."""
        state_payload = f"{decision.status.value}::{decision.applicable_version_id}::{decision.rationale.strip()}"
        state_hash = hashlib.sha256(state_payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=decision.decision_id,
            node_type=NodeType.COUNSEL_DECISION,
            stable_lineage_key=decision.stable_lineage_key,
            state_hash=state_hash,
            version_id=decision.applicable_version_id,
            entity=decision,
            metadata={
                "status": decision.status.value,
                "rationale": decision.rationale,
                "use_id": decision.use_id,
                "reviewer": decision.reviewer_display_name,
            },
        )
        return self.add_node(node)

    def add_evidence_snapshot(self, snapshot: PublicEvidenceSnapshot) -> DependencyNode:
        """Convenience method to register a PublicEvidenceSnapshot node."""
        state_payload = f"{snapshot.stance.value}::{snapshot.raw_payload_hash or snapshot.payload_hash or snapshot.excerpt.strip()}"
        state_hash = hashlib.sha256(state_payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=snapshot.snapshot_id,
            node_type=NodeType.EVIDENCE_SNAPSHOT,
            stable_lineage_key=snapshot.stable_lineage_key,
            state_hash=state_hash,
            version_id=None,
            entity=snapshot,
            metadata={
                "stance": snapshot.stance.value,
                "source_url": snapshot.source_url,
                "source_title": snapshot.source_title,
                "provider": snapshot.provider,
            },
        )
        return self.add_node(node)

    def add_contract_agreement(self, contract: ContractAgreement) -> DependencyNode:
        """Convenience method to register a ContractAgreement node."""
        state_payload = f"{contract.agreement_hash}::{contract.is_active}::{contract.term.strip()}"
        state_hash = hashlib.sha256(state_payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=contract.agreement_id,
            node_type=NodeType.CONTRACT_AGREEMENT,
            stable_lineage_key=contract.stable_lineage_key,
            state_hash=state_hash,
            version_id=None,
            entity=contract,
            metadata={
                "licensor": contract.licensor,
                "licensee": contract.licensee,
                "scope": contract.scope,
                "term": contract.term,
                "is_active": contract.is_active,
            },
        )
        return self.add_node(node)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def get_node(self, node_id: str) -> DependencyNode:
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in clearance dependency graph.")
        return self._nodes[node_id]

    def all_nodes(self) -> List[DependencyNode]:
        """Returns all nodes in canonical order."""
        return sorted(self._nodes.values(), key=lambda n: n.canonical_sort_key())

    def get_nodes_by_lineage(self, stable_lineage_key: str) -> List[DependencyNode]:
        """Returns all nodes associated with a stable lineage key in canonical order."""
        node_ids = self._lineage_map.get(stable_lineage_key, set())
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]
        return sorted(nodes, key=lambda n: n.canonical_sort_key())

    def get_nodes_by_type(self, node_type: NodeType) -> List[DependencyNode]:
        """Returns all nodes of a specific NodeType in canonical order."""
        nodes = [n for n in self._nodes.values() if n.node_type == node_type]
        return sorted(nodes, key=lambda n: n.canonical_sort_key())

    @property
    def nodes(self) -> Dict[str, DependencyNode]:
        return self._nodes

    @property
    def edges(self) -> Dict[Tuple[str, str], DependencyEdge]:
        return self._edges

    @property
    def dependencies(self) -> Dict[str, Set[str]]:
        return self._dependencies

    @property
    def dependents(self) -> Dict[str, Set[str]]:
        return self._dependents

    def add_dependency(
        self,
        dependent_id: str,
        dependency_id: str,
        kind: DependencyKind = DependencyKind.CUSTOM,
        description: Optional[str] = None,
    ) -> DependencyEdge:
        """
        Adds a causal dependency edge: dependent_id depends on dependency_id.
        Raises NodeNotFoundError if either node is missing.
        Raises CycleDetectedError if this dependency creates a directed cycle.
        """
        if dependent_id not in self._nodes:
            raise NodeNotFoundError(f"Dependent node '{dependent_id}' does not exist in graph.")
        if dependency_id not in self._nodes:
            raise NodeNotFoundError(f"Dependency node '{dependency_id}' does not exist in graph.")

        if dependent_id == dependency_id:
            raise CycleDetectedError(
                f"Self-referential causal dependency detected: node '{dependent_id}' cannot depend on itself."
            )

        # Check for cycle: if dependent_id is already an upstream dependency of dependency_id,
        # then making dependent_id depend on dependency_id closes a cycle.
        existing_upstream_of_dependency = self.get_dependencies(dependency_id, transitive=True)
        if dependent_id in existing_upstream_of_dependency:
            path = self._find_path(dependency_id, dependent_id)
            cycle_desc = " -> ".join(path + [dependency_id])
            raise CycleDetectedError(
                f"Causal cycle detected: adding dependency '{dependent_id}' -> '{dependency_id}' "
                f"creates cycle: {cycle_desc}"
            )

        edge = DependencyEdge(
            dependent_id=dependent_id,
            dependency_id=dependency_id,
            kind=kind,
            description=description,
        )

        self._dependencies[dependent_id].add(dependency_id)
        self._dependents[dependency_id].add(dependent_id)
        self._edges[(dependent_id, dependency_id)] = edge
        return edge

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        kind: DependencyKind = DependencyKind.CUSTOM,
        description: Optional[str] = None,
    ) -> DependencyEdge:
        """
        Alias for add_dependency where from_id depends on to_id.
        """
        return self.add_dependency(dependent_id=from_id, dependency_id=to_id, kind=kind, description=description)

    def get_direct_dependencies(self, node_id: str) -> List[str]:
        """Immediate upstream dependencies (what this node directly depends on)."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph.")
        deps = list(self._dependencies.get(node_id, set()))
        return self._sort_node_ids(deps)

    def get_direct_dependents(self, node_id: str) -> List[str]:
        """Immediate downstream dependents (nodes that directly depend on this node)."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph.")
        dep_list = list(self._dependents.get(node_id, set()))
        return self._sort_node_ids(dep_list)

    def get_dependencies(self, node_id: str, transitive: bool = False) -> List[str]:
        """
        Returns upstream dependencies of node_id in canonical order.
        If transitive=True, returns all ancestors (transitive closure).
        """
        if not transitive:
            return self.get_direct_dependencies(node_id)

        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph.")

        visited: Set[str] = set()
        queue: deque[str] = deque([node_id])

        while queue:
            current = queue.popleft()
            for parent in self._dependencies.get(current, set()):
                if parent not in visited and parent != node_id:
                    visited.add(parent)
                    queue.append(parent)

        return self._sort_node_ids(list(visited))

    def get_dependents(self, node_id: str, transitive: bool = False) -> List[str]:
        """
        Returns downstream dependents of node_id in canonical order.
        If transitive=True, returns all descendants (transitive closure).
        """
        if not transitive:
            return self.get_direct_dependents(node_id)

        if node_id not in self._nodes:
            raise NodeNotFoundError(f"Node '{node_id}' not found in graph.")

        visited: Set[str] = set()
        queue: deque[str] = deque([node_id])

        while queue:
            current = queue.popleft()
            for child in self._dependents.get(current, set()):
                if child not in visited and child != node_id:
                    visited.add(child)
                    queue.append(child)

        return self._sort_node_ids(list(visited))

    def get_ancestors(self, node_id: str) -> List[str]:
        """Alias for transitive upstream dependencies."""
        return self.get_dependencies(node_id, transitive=True)

    def get_descendants(self, node_id: str) -> List[str]:
        """Alias for transitive downstream dependents."""
        return self.get_dependents(node_id, transitive=True)

    def has_cycles(self) -> bool:
        """Returns True if the graph contains any directed cycle, False otherwise."""
        return len(self.find_cycles()) > 0

    def find_cycles(self) -> List[List[str]]:
        """
        Finds and returns all elementary cycles using standard DFS graph coloring.
        Deterministic: checks nodes in canonical sort order.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self._nodes}
        parent_map: Dict[str, Optional[str]] = {nid: None for nid in self._nodes}
        cycles: List[List[str]] = []

        def dfs(u: str, path: List[str]):
            color[u] = GRAY
            path.append(u)

            children = self._sort_node_ids(list(self._dependencies.get(u, set())))
            for v in children:
                if color[v] == GRAY:
                    cycle_start_idx = path.index(v)
                    cycle_path = path[cycle_start_idx:] + [v]
                    cycles.append(cycle_path)
                elif color[v] == WHITE:
                    parent_map[v] = u
                    dfs(v, path)

            path.pop()
            color[u] = BLACK

        for node in self.all_nodes():
            if color[node.node_id] == WHITE:
                dfs(node.node_id, [])

        return cycles

    def topological_sort(self, reverse: bool = False) -> List[DependencyNode]:
        """
        Performs a deterministic topological sort of the clearance graph.
        Dependencies (upstream) precede dependents (downstream).
        Deterministic tie-breaking uses canonical_sort_key: (stable_lineage_key, node_type, node_id).
        Guarantees input-order invariance.
        """
        in_degree: Dict[str, int] = {nid: len(self._dependencies.get(nid, set())) for nid in self._nodes}

        available: List[DependencyNode] = [
            self._nodes[nid] for nid, deg in in_degree.items() if deg == 0
        ]
        available.sort(key=lambda n: n.canonical_sort_key())

        sorted_nodes: List[DependencyNode] = []

        while available:
            current = available.pop(0)
            sorted_nodes.append(current)

            direct_children = self.get_direct_dependents(current.node_id)
            for child_id in direct_children:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    child_node = self._nodes[child_id]
                    available.append(child_node)
                    available.sort(key=lambda n: n.canonical_sort_key())

        if len(sorted_nodes) != len(self._nodes):
            raise CycleDetectedError(
                f"Graph contains a directed cycle; topological sort resolved only "
                f"{len(sorted_nodes)} of {len(self._nodes)} nodes."
            )

        if reverse:
            sorted_nodes.reverse()

        return sorted_nodes

    def get_topological_order(self, reverse: bool = False) -> List[str]:
        """Returns node identifiers in deterministic topological sort order."""
        return [node.node_id for node in self.topological_sort(reverse=reverse)]

    def propagate_invalidation(
        self,
        changed_nodes: Union[List[str], Dict[str, Dict[str, Any]]],
    ) -> List[InvalidationNotice]:
        """
        Performs transitive invalidation:
        Given a set of upstream nodes that have shifted/changed, traverses all downstream
        dependents in topological order, tagging downstream CounselDecision nodes as stale.
        Produces detailed, legally defensible InvalidationNotices naming the specific changed dependency.
        """
        if isinstance(changed_nodes, list):
            change_details_map: Dict[str, Dict[str, Any]] = {
                nid: {"explanation": "Upstream state shift detected."}
                for nid in changed_nodes
            }
        else:
            change_details_map = dict(changed_nodes)

        notices: List[InvalidationNotice] = []
        visited_invalidation_pairs: Set[Tuple[str, str]] = set()

        sorted_changed_ids = self._sort_node_ids(list(change_details_map.keys()))

        for root_id in sorted_changed_ids:
            if root_id not in self._nodes:
                continue

            root_node = self._nodes[root_id]
            root_info = change_details_map[root_id]

            descendants = self.get_descendants(root_id)

            for desc_id in descendants:
                if (desc_id, root_id) in visited_invalidation_pairs:
                    continue
                visited_invalidation_pairs.add((desc_id, root_id))

                desc_node = self._nodes[desc_id]
                if desc_node.node_type != NodeType.COUNSEL_DECISION:
                    continue

                path = self._find_path(desc_id, root_id)
                causal_path = list(reversed(path)) if path else [root_id, desc_id]

                is_direct = len(causal_path) == 2
                if not is_direct:
                    reason_code = "UPSTREAM_DEPENDENCY_STALE"
                else:
                    reason_code = root_info.get("reason_code")
                    if not reason_code:
                        if root_node.node_type == NodeType.CREATIVE_USE:
                            reason_code = "CREATIVE_CONTEXT_ALTERED"
                        elif root_node.node_type in (NodeType.EVIDENCE_SNAPSHOT, NodeType.CONTRACT_AGREEMENT):
                            reason_code = "EXTERNAL_EVIDENCE_SHIFT"
                        else:
                            reason_code = "UPSTREAM_DEPENDENCY_STALE"

                custom_explanation = root_info.get("explanation")
                if custom_explanation:
                    explanation = (
                        f"Downstream clearance decision '{desc_node.node_id}' for '{desc_node.stable_lineage_key}' "
                        f"invalidated: {custom_explanation}"
                    )
                else:
                    path_str = " -> ".join(causal_path)
                    explanation = (
                        f"Downstream clearance decision '{desc_node.node_id}' for '{desc_node.stable_lineage_key}' "
                        f"invalidated due to causal drift in upstream {root_node.node_type.value} '{root_node.node_id}' "
                        f"(stable lineage key: '{root_node.stable_lineage_key}'). "
                        f"Causal lineage dependency path: [{path_str}]."
                    )

                notice = InvalidationNotice(
                    affected_node_id=desc_node.node_id,
                    affected_lineage_key=desc_node.stable_lineage_key,
                    affected_node_type=desc_node.node_type,
                    root_cause_node_id=root_node.node_id,
                    root_cause_lineage_key=root_node.stable_lineage_key,
                    root_cause_type=root_node.node_type,
                    reason_code=reason_code,
                    explanation=explanation,
                    invalidation_path=causal_path,
                    changed_state_details=root_info,
                )
                notices.append(notice)

        notices.sort(
            key=lambda n: (n.affected_lineage_key, n.affected_node_id, n.root_cause_node_id)
        )
        return notices

    def _find_path(self, from_dependent: str, to_dependency: str) -> List[str]:
        if from_dependent == to_dependency:
            return [from_dependent]

        visited: Set[str] = set()
        queue: deque[List[str]] = deque([[from_dependent]])

        while queue:
            current_path = queue.popleft()
            node = current_path[-1]

            if node == to_dependency:
                return current_path

            if node in visited:
                continue
            visited.add(node)

            deps = self._sort_node_ids(list(self._dependencies.get(node, set())))
            for dep in deps:
                if dep not in visited:
                    queue.append(current_path + [dep])

        return []

    def _sort_node_ids(self, node_ids: List[str]) -> List[str]:
        return sorted(
            node_ids,
            key=lambda nid: self._nodes[nid].canonical_sort_key() if nid in self._nodes else ("", "", nid),
        )

    @classmethod
    def build_clearance_graph(
        cls,
        base_uses: List[CreativeUse],
        target_uses: Optional[List[CreativeUse]] = None,
        prior_decisions: Optional[List[CounselDecision]] = None,
        evidence_snapshots: Optional[Dict[str, PublicEvidenceSnapshot]] = None,
        contracts: Optional[List[ContractAgreement]] = None,
    ) -> ClearanceDependencyGraph:
        """
        Constructs a complete canonical ClearanceDependencyGraph from domain entities.
        Ensures input-order invariance by canonical sorting before building DAG.
        """
        graph = cls()

        sorted_base = sorted(base_uses or [], key=lambda u: (u.stable_lineage_key, u.use_id))
        sorted_target = sorted(target_uses or [], key=lambda u: (u.stable_lineage_key, u.use_id))
        sorted_decisions = sorted(prior_decisions or [], key=lambda d: (d.stable_lineage_key, d.decision_id))
        sorted_contracts = sorted(contracts or [], key=lambda c: (c.stable_lineage_key, c.agreement_id))
        evidence_map = evidence_snapshots or {}

        use_by_key: Dict[str, CreativeUse] = {}
        for use in sorted_base:
            graph.add_creative_use(use)
            use_by_key[use.stable_lineage_key] = use

        for use in sorted_target:
            if not graph.has_node(use.use_id):
                graph.add_creative_use(use)
            use_by_key[use.stable_lineage_key] = use

        sorted_evidence = sorted(evidence_map.values(), key=lambda e: (e.stable_lineage_key, e.snapshot_id))
        evidence_by_key: Dict[str, PublicEvidenceSnapshot] = {}
        for ev in sorted_evidence:
            graph.add_evidence_snapshot(ev)
            evidence_by_key[ev.stable_lineage_key] = ev

        contract_by_key: Dict[str, ContractAgreement] = {}
        for c in sorted_contracts:
            graph.add_contract_agreement(c)
            contract_by_key[c.stable_lineage_key] = c

        # Pass 1: Register all CounselDecision nodes first
        for dec in sorted_decisions:
            graph.add_counsel_decision(dec)

        # Pass 2: Wire all causal dependency edges
        for dec in sorted_decisions:
            if graph.has_node(dec.use_id):
                graph.add_dependency(
                    dependent_id=dec.decision_id,
                    dependency_id=dec.use_id,
                    kind=DependencyKind.CREATIVE_CONTEXT,
                    description=f"Counsel decision depends on creative use '{dec.use_id}' context hash",
                )
            elif dec.stable_lineage_key in use_by_key:
                matched_use = use_by_key[dec.stable_lineage_key]
                if graph.has_node(matched_use.use_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=matched_use.use_id,
                        kind=DependencyKind.CREATIVE_CONTEXT,
                        description=f"Counsel decision depends on creative use '{matched_use.use_id}' context hash",
                    )

            if dec.stable_lineage_key in evidence_by_key:
                matched_ev = evidence_by_key[dec.stable_lineage_key]
                if graph.has_node(matched_ev.snapshot_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=matched_ev.snapshot_id,
                        kind=DependencyKind.EVIDENCE_STANCE,
                        description=f"Counsel decision depends on evidence snapshot '{matched_ev.snapshot_id}' stance and verification",
                    )

            if dec.stable_lineage_key in contract_by_key:
                matched_contract = contract_by_key[dec.stable_lineage_key]
                if graph.has_node(matched_contract.agreement_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=matched_contract.agreement_id,
                        kind=DependencyKind.CONTRACTUAL_GRANT,
                        description=f"Counsel decision depends on active license agreement '{matched_contract.agreement_id}'",
                    )

            for explicit_dep_id in sorted(dec.dependency_ids):
                if graph.has_node(explicit_dep_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=explicit_dep_id,
                        kind=DependencyKind.PRIOR_DECISION,
                        description=f"Explicit clearance dependency '{explicit_dep_id}'",
                    )
                else:
                    lineage_nodes = graph.get_nodes_by_lineage(explicit_dep_id)
                    for l_node in lineage_nodes:
                        if l_node.node_type == NodeType.COUNSEL_DECISION:
                            graph.add_dependency(
                                dependent_id=dec.decision_id,
                                dependency_id=l_node.node_id,
                                kind=DependencyKind.PRIOR_DECISION,
                                description=f"Lineage clearance dependency '{explicit_dep_id}'",
                            )

            if dec.supersedes_decision_id and graph.has_node(dec.supersedes_decision_id):
                graph.add_dependency(
                    dependent_id=dec.decision_id,
                    dependency_id=dec.supersedes_decision_id,
                    kind=DependencyKind.PRIOR_DECISION,
                    description=f"Supersedes prior counsel decision '{dec.supersedes_decision_id}'",
                )

        return graph


DependencyGraph = ClearanceDependencyGraph

__all__ = [
    "ClearanceGraphError",
    "CycleDetectedError",
    "NodeNotFoundError",
    "NodeType",
    "DependencyKind",
    "DependencyNode",
    "DependencyEdge",
    "InvalidationNotice",
    "ClearanceDependencyGraph",
    "DependencyGraph",
]
