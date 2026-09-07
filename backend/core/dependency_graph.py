"""
Lienmark Clearance Lineage & Causal Dependency Graph
Deterministic DAG engine for version-bound clearance change control and transitive invalidation.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
import hashlib
import heapq
import json
import logging
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
import uuid

from pydantic import BaseModel, Field, model_validator

from backend.domain.models import (
    AtomicRightsClaim,
    ClarificationRequest,
    ContractAgreement,
    ContractGrant,
    CounselDecision,
    CreativeUse,
    PublicEvidenceSnapshot,
    SceneContext,
    ScriptBeat,
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


class CrossTenantBoundaryViolationError(ClearanceGraphError):
    """Raised when an operation attempts to wire or access nodes across tenant boundaries."""
    pass


class GraphFrozenError(ClearanceGraphError):
    """Raised when mutating a frozen ClearanceDependencyGraph instance."""
    pass


class NodeType(str, Enum):
    SCENE_CONTEXT = "scene_context"
    SCRIPT_BEAT = "script_beat"
    CREATIVE_USE = "creative_use"
    ATOMIC_RIGHTS_CLAIM = "atomic_rights_claim"
    EVIDENCE_SNAPSHOT = "evidence_snapshot"
    CONTRACT_AGREEMENT = "contract_agreement"
    CONTRACT_GRANT = "contract_grant"
    CLARIFICATION_REQUEST = "clarification_request"
    COUNSEL_DECISION = "counsel_decision"
    CUSTOM = "custom"


class DependencyKind(str, Enum):
    SCENE_CONTAINMENT = "scene_containment"
    BEAT_NARRATIVE = "beat_narrative"
    CLAIM_DERIVATION = "claim_derivation"
    CONTRACTUAL_SUBGRANT = "contractual_subgrant"
    CONTRACTUAL_GRANT = "contractual_grant"
    EVIDENCE_STANCE = "evidence_stance"
    CLARIFICATION_ATTESTATION = "clarification_attestation"
    CREATIVE_CONTEXT = "creative_context"
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
    organization_id: str = "org_studio_alpha"
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
    organization_id: str = "org_studio_alpha"

    def canonical_sort_key(self) -> Tuple[str, str, str]:
        return (self.dependent_id, self.dependency_id, self.kind.value)


class InvalidationNotice(BaseModel):
    """
    Cryptographically verifiable, tamper-evident notice documenting the invalidation
    of a clearance decision due to causal upstream drift.
    """
    notice_id: str = Field(default_factory=lambda: f"inv_not_{uuid.uuid4().hex[:12]}")
    organization_id: str = Field(default="org_studio_alpha")
    production_id: str = Field(default="prod_broadway_01")
    run_id: str = Field(default="run_default")
    sequence_number: int = Field(default=1, ge=1)
    previous_notice_hash: str = Field(default="0" * 64)

    affected_node_id: str
    affected_lineage_key: str
    affected_node_type: NodeType
    root_cause_node_id: str
    root_cause_lineage_key: str
    root_cause_type: NodeType

    is_direct: bool = Field(default=True)
    hop_count: int = Field(default=1, ge=1)
    reason_code: str
    explanation: str
    invalidation_path: List[str]
    changed_state_details: Dict[str, Any] = Field(default_factory=dict)

    canonical_payload_digest: str = Field(default="")
    notice_hash: str = Field(default="")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def compute_payload_digest(cls, data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 digest over canonical payload attributes."""
        canonical_fields = {
            "affected_lineage_key": data.get("affected_lineage_key"),
            "affected_node_id": data.get("affected_node_id"),
            "affected_node_type": str(getattr(data.get("affected_node_type"), "value", data.get("affected_node_type"))),
            "changed_state_details": data.get("changed_state_details") or {},
            "explanation": data.get("explanation"),
            "hop_count": data.get("hop_count", 1),
            "invalidation_path": data.get("invalidation_path") or [],
            "is_direct": data.get("is_direct", True),
            "organization_id": data.get("organization_id", "org_studio_alpha"),
            "production_id": data.get("production_id", "prod_broadway_01"),
            "reason_code": data.get("reason_code"),
            "root_cause_lineage_key": data.get("root_cause_lineage_key"),
            "root_cause_node_id": data.get("root_cause_node_id"),
            "root_cause_type": str(getattr(data.get("root_cause_type"), "value", data.get("root_cause_type"))),
            "run_id": data.get("run_id", "run_default"),
            "sequence_number": data.get("sequence_number", 1),
        }
        serialized = json.dumps(canonical_fields, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def compute_notice_hash(cls, previous_hash: str, sequence: int, payload_digest: str) -> str:
        """Computes linked chain hash: SHA256(previous_hash:sequence:payload_digest)."""
        raw_token = f"{previous_hash}:{sequence}:{payload_digest}"
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def populate_cryptographic_hashes(self) -> "InvalidationNotice":
        raw_dict = self.__dict__
        expected_digest = self.compute_payload_digest(raw_dict)
        if not self.canonical_payload_digest:
            object.__setattr__(self, "canonical_payload_digest", expected_digest)

        expected_notice_hash = self.compute_notice_hash(
            self.previous_notice_hash, self.sequence_number, self.canonical_payload_digest
        )
        if not self.notice_hash:
            object.__setattr__(self, "notice_hash", expected_notice_hash)
        return self

    def verify_integrity(self) -> bool:
        """Verifies notice integrity against canonical SHA-256 payload and chain hash."""
        calc_digest = self.compute_payload_digest(self.__dict__)
        if self.canonical_payload_digest != calc_digest:
            return False
        calc_notice_hash = self.compute_notice_hash(
            self.previous_notice_hash, self.sequence_number, calc_digest
        )
        return self.notice_hash == calc_notice_hash

    def to_firestore_dict(self) -> Dict[str, Any]:
        """Formats notice for discrete subcollection persistence under /runs/{run_id}/invalidation_notices."""
        raw = self.model_dump()
        raw["affected_node_type"] = self.affected_node_type.value
        raw["root_cause_type"] = self.root_cause_type.value
        return raw


class ClearanceDependencyGraph:
    """
    Directed Acyclic Graph (DAG) for clearance lineage and causal change propagation.
    Guarantees:
    1. DAG integrity: Cycle detection on edge creation and validation.
    2. Input-order invariance: Canonical sorting on stable lineage keys ensures deterministic traversal.
    3. Transitive invalidation: Upstream shifts invalidate all downstream decisions, naming the exact dependency.
    """

    def __init__(self, organization_id: str = "org_studio_alpha") -> None:
        self.organization_id = organization_id
        self._nodes: Dict[str, DependencyNode] = {}
        self._dependencies: Dict[str, Set[str]] = {}  # dependent_id -> {dependency_ids} (upstream)
        self._dependents: Dict[str, Set[str]] = {}    # dependency_id -> {dependent_ids} (downstream)
        self._edges: Dict[Tuple[str, str], DependencyEdge] = {}
        self._lineage_map: Dict[str, Set[str]] = {}
        self._canonical_key_cache: Dict[str, Tuple[str, str, str]] = {}
        self._is_frozen: bool = False
        self._lock = threading.RLock()

    def freeze(self) -> None:
        """Freezes the graph, preventing further mutations for thread-safe reads."""
        with self._lock:
            self._is_frozen = True

    def _assert_not_frozen(self) -> None:
        if self._is_frozen:
            raise GraphFrozenError("ClearanceDependencyGraph is frozen and immutable.")

    def add_node(
        self,
        node: Union[DependencyNode, str],
        node_type: NodeType = NodeType.CUSTOM,
        stable_lineage_key: Optional[str] = None,
        state_hash: str = "0000000000000000",
        version_id: Optional[str] = None,
        entity: Optional[Any] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DependencyNode:
        """
        Adds a node to the graph. If node already exists, updates its attributes defensively.
        Supports passing either a DependencyNode instance or a string node_id.
        """
        self._assert_not_frozen()
        with self._lock:
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
                    organization_id=organization_id or self.organization_id,
                    metadata=metadata or {},
                )

            if node.organization_id != self.organization_id:
                raise CrossTenantBoundaryViolationError(
                    f"Node organization '{node.organization_id}' does not match graph organization '{self.organization_id}'."
                )

            self._nodes[node.node_id] = node
            self._canonical_key_cache[node.node_id] = node.canonical_sort_key()

            if node.node_id not in self._dependencies:
                self._dependencies[node.node_id] = set()
            if node.node_id not in self._dependents:
                self._dependents[node.node_id] = set()

            if node.stable_lineage_key not in self._lineage_map:
                self._lineage_map[node.stable_lineage_key] = set()
            self._lineage_map[node.stable_lineage_key].add(node.node_id)
            return node

    def add_scene_context(self, scene: SceneContext) -> DependencyNode:
        """Convenience method to register a SceneContext node."""
        node = DependencyNode(
            node_id=scene.scene_id,
            node_type=NodeType.SCENE_CONTEXT,
            stable_lineage_key=scene.stable_lineage_key,
            state_hash=scene.scene_hash,
            version_id=scene.version_id,
            entity=scene,
            organization_id=self.organization_id,
            metadata={
                "scene_number": scene.scene_number,
                "slugline": scene.slugline,
                "setting_type": scene.setting_type,
                "location": scene.location,
                "time_of_day": scene.time_of_day,
            },
        )
        return self.add_node(node)

    def add_script_beat(self, beat: ScriptBeat) -> DependencyNode:
        """Convenience method to register a ScriptBeat node."""
        node = DependencyNode(
            node_id=beat.beat_id,
            node_type=NodeType.SCRIPT_BEAT,
            stable_lineage_key=beat.stable_lineage_key,
            state_hash=beat.beat_hash,
            version_id=beat.version_id,
            entity=beat,
            organization_id=self.organization_id,
            metadata={
                "scene_id": beat.scene_id,
                "beat_index": beat.beat_index,
                "title": beat.title,
                "action_text": beat.action_text,
            },
        )
        return self.add_node(node)

    def add_atomic_rights_claim(self, claim: AtomicRightsClaim) -> DependencyNode:
        """Convenience method to register an AtomicRightsClaim node."""
        payload = f"{claim.right_category}::{claim.rights_subject}::{claim.disposition.value}::{claim.notes}"
        state_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=claim.claim_id,
            node_type=NodeType.ATOMIC_RIGHTS_CLAIM,
            stable_lineage_key=claim.occurrence_lineage_id or claim.claim_id,
            state_hash=state_hash,
            version_id=None,
            entity=claim,
            organization_id=self.organization_id,
            metadata={
                "occurrence_id": claim.occurrence_id,
                "right_category": claim.right_category,
                "rights_subject": claim.rights_subject,
                "disposition": claim.disposition.value,
            },
        )
        return self.add_node(node)

    def add_contract_grant(self, grant: ContractGrant) -> DependencyNode:
        """Convenience method to register a ContractGrant node."""
        payload = f"{grant.agreement_id}::{grant.source_clause.strip()}::{grant.verification_status}"
        state_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=grant.grant_id,
            node_type=NodeType.CONTRACT_GRANT,
            stable_lineage_key=f"grant_{grant.asset_id}_{grant.grant_id}",
            state_hash=state_hash,
            version_id=grant.agreement_version,
            entity=grant,
            organization_id=self.organization_id,
            metadata={
                "agreement_id": grant.agreement_id,
                "asset_id": grant.asset_id,
                "grantor": grant.grantor,
                "grantee": grant.grantee,
                "permitted_media": grant.permitted_media,
                "permitted_territories": grant.permitted_territories,
            },
        )
        return self.add_node(node)

    def add_clarification_request(self, clrf: ClarificationRequest) -> DependencyNode:
        """Convenience method to register a ClarificationRequest node."""
        payload = f"{clrf.status}::{clrf.response_text or ''}::{clrf.attached_document_ref or ''}"
        state_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        node = DependencyNode(
            node_id=clrf.request_id,
            node_type=NodeType.CLARIFICATION_REQUEST,
            stable_lineage_key=clrf.stable_lineage_key,
            state_hash=state_hash,
            version_id=clrf.revision_id,
            entity=clrf,
            organization_id=self.organization_id,
            metadata={
                "claim_id": clrf.claim_id,
                "status": clrf.status,
                "scope_field_missing": clrf.scope_field_missing,
                "assigned_role": clrf.assigned_role,
            },
        )
        return self.add_node(node)

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
                **(getattr(use, "metadata", None) or {}),
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

    def __len__(self) -> int:
        return len(self._nodes)

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def add_dependency(
        self,
        dependent_id: str,
        dependency_id: str,
        kind: DependencyKind = DependencyKind.CUSTOM,
        description: Optional[str] = None,
        validate_cycle: bool = True,
    ) -> DependencyEdge:
        """
        Adds a causal dependency edge: dependent_id depends on dependency_id.
        Raises NodeNotFoundError if either node is missing.
        Raises CycleDetectedError if this dependency creates a directed cycle.
        """
        self._assert_not_frozen()
        with self._lock:
            if dependent_id not in self._nodes:
                raise NodeNotFoundError(f"Dependent node '{dependent_id}' does not exist in graph.")
            if dependency_id not in self._nodes:
                raise NodeNotFoundError(f"Dependency node '{dependency_id}' does not exist in graph.")

            if dependent_id == dependency_id:
                raise CycleDetectedError(
                    f"Self-referential causal dependency detected: node '{dependent_id}' cannot depend on itself."
                )

            node_u = self._nodes[dependent_id]
            node_v = self._nodes[dependency_id]
            if node_u.organization_id != node_v.organization_id:
                raise CrossTenantBoundaryViolationError(
                    f"Cross-tenant dependency edge prohibited: {node_u.organization_id} vs {node_v.organization_id}"
                )

            if validate_cycle:
                # Online Cycle Pruning:
                # If dependent_id has no dependents, or dependency_id has no dependencies,
                # no cycle can be closed by adding dependent_id -> dependency_id.
                has_downstream = bool(self._dependents.get(dependent_id))
                has_upstream = bool(self._dependencies.get(dependency_id))

                if has_downstream and has_upstream:
                    # Target-directed BFS checking if dependent_id is reachable upstream from dependency_id
                    visited: Set[str] = set()
                    queue: deque[str] = deque([dependency_id])
                    cycle_found = False

                    while queue:
                        curr = queue.popleft()
                        if curr == dependent_id:
                            cycle_found = True
                            break
                        if curr in visited:
                            continue
                        visited.add(curr)
                        for parent in self._dependencies.get(curr, set()):
                            if parent not in visited:
                                queue.append(parent)

                    if cycle_found:
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
                organization_id=self.organization_id,
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
        validate_cycle: bool = True,
    ) -> DependencyEdge:
        """Alias for add_dependency where from_id depends on to_id."""
        return self.add_dependency(
            dependent_id=from_id,
            dependency_id=to_id,
            kind=kind,
            description=description,
            validate_cycle=validate_cycle,
        )

    def batch_add_dependencies(
        self,
        edges_data: List[Tuple[str, str, DependencyKind, Optional[str]]],
        validate_acyclicity: bool = True,
    ) -> None:
        """
        Batch bulk edge insertion bypassing per-edge BFS, followed by a single linear O(V + E) acyclicity check.
        """
        self._assert_not_frozen()
        with self._lock:
            for dep_id, src_id, kind, desc in edges_data:
                self.add_dependency(
                    dependent_id=dep_id,
                    dependency_id=src_id,
                    kind=kind,
                    description=desc,
                    validate_cycle=False,
                )
            if validate_acyclicity:
                self.validate_dag_acyclicity()

    def validate_dag_acyclicity(self) -> None:
        """
        Linear-time O(V + E) 3-color DFS verification ensuring graph is strictly acyclic.
        Input-order invariant: traverses nodes and edges in canonical sort order.
        Recursion-safe: uses explicit call stack to eliminate Python RecursionError on deep lineages.
        Raises CycleDetectedError upon discovering any back-edge.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self._nodes}

        canonical_nodes = self.all_nodes()
        for root_node in canonical_nodes:
            root_id = root_node.node_id
            if color[root_id] != WHITE:
                continue

            root_deps = self._sort_node_ids(list(self._dependencies.get(root_id, set())))
            stack: List[Tuple[str, List[str], int]] = [(root_id, root_deps, 0)]
            color[root_id] = GRAY
            path: List[str] = [root_id]

            while stack:
                u, deps, idx = stack[-1]
                if idx < len(deps):
                    v = deps[idx]
                    stack[-1] = (u, deps, idx + 1)
                    if color[v] == GRAY:
                        cycle_idx = path.index(v)
                        cycle_path = path[cycle_idx:] + [v]
                        raise CycleDetectedError(f"Causal cycle detected: {' -> '.join(cycle_path)}")
                    elif color[v] == WHITE:
                        color[v] = GRAY
                        path.append(v)
                        v_deps = self._sort_node_ids(list(self._dependencies.get(v, set())))
                        stack.append((v, v_deps, 0))
                else:
                    stack.pop()
                    color[u] = BLACK
                    path.pop()

    def validate_connectivity(self) -> List[Dict[str, Any]]:
        """
        Defensive Connectivity Audit:
        Identifies orphan decisions with 0 upstream context, or unlinked legal grants/evidence.
        Prevents silent carry-forward of disconnected decisions.
        """
        diagnostics: List[Dict[str, Any]] = []
        for nid, node in self._nodes.items():
            if node.node_type == NodeType.COUNSEL_DECISION:
                deps = self._dependencies.get(nid, set())
                creative_deps = [d for d in deps if self._nodes[d].node_type in (NodeType.CREATIVE_USE, NodeType.ATOMIC_RIGHTS_CLAIM)]
                if not creative_deps:
                    diagnostics.append({
                        "node_id": nid,
                        "lineage_key": node.stable_lineage_key,
                        "diagnostic_type": "ORPHAN_DECISION_NO_CREATIVE_CONTEXT",
                        "severity": "CRITICAL",
                    })
            elif node.node_type in (NodeType.CONTRACT_AGREEMENT, NodeType.EVIDENCE_SNAPSHOT):
                downstream = self._dependents.get(nid, set())
                if not downstream:
                    diagnostics.append({
                        "node_id": nid,
                        "lineage_key": node.stable_lineage_key,
                        "diagnostic_type": "UNLINKED_PREREQUISITE",
                        "severity": "WARNING",
                    })
        return diagnostics

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

    def find_cycles(self, direction: str = "upstream") -> List[List[str]]:
        """
        Finds and returns all elementary directed cycles using 3-color DFS graph coloring.
        Deterministic: checks nodes in canonical sort order and rotates cycles to minimum canonical vertex.
        direction: 'upstream' (follows dependencies) or 'downstream' (follows dependents).
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {nid: WHITE for nid in self._nodes}
        seen_cycles: Set[Tuple[str, ...]] = set()
        canonical_cycles: List[List[str]] = []

        def dfs(u: str, path: List[str]):
            color[u] = GRAY
            path.append(u)

            if direction == "downstream":
                neighbors = self.get_direct_dependents(u)
            else:
                neighbors = self.get_direct_dependencies(u)

            for v in neighbors:
                if color[v] == GRAY:
                    cycle_start_idx = path.index(v)
                    raw_cycle = path[cycle_start_idx:]

                    # Canonical Rotational Deduplication: rotate cycle to minimal canonical sort key
                    min_idx = min(
                        range(len(raw_cycle)),
                        key=lambda i: self._nodes[raw_cycle[i]].canonical_sort_key(),
                    )
                    rotated_cycle = raw_cycle[min_idx:] + raw_cycle[:min_idx]
                    dedup_key = tuple(rotated_cycle)

                    if dedup_key not in seen_cycles:
                        seen_cycles.add(dedup_key)
                        canonical_cycles.append(rotated_cycle + [rotated_cycle[0]])
                elif color[v] == WHITE:
                    dfs(v, path)

            path.pop()
            color[u] = BLACK

        for node in self.all_nodes():
            if color[node.node_id] == WHITE:
                dfs(node.node_id, [])

        canonical_cycles.sort(
            key=lambda c: self._nodes[c[0]].canonical_sort_key() if c[0] in self._nodes else ("", "", c[0])
        )
        return canonical_cycles

    def topological_sort(self, reverse: bool = False) -> List[DependencyNode]:
        """
        Performs a deterministic topological sort in O((V + E) log V) using Kahn's algorithm
        accelerated by Python's C-heapq min-heap priority queue.
        Dependencies (upstream) precede dependents (downstream).
        Deterministic tie-breaking uses canonical_sort_key: (stable_lineage_key, node_type.value, node_id).
        Guarantees mathematical input-order invariance.
        """
        in_degree: Dict[str, int] = {nid: len(self._dependencies.get(nid, set())) for nid in self._nodes}

        # Min-heap elements: (canonical_sort_key, node_id, DependencyNode)
        heap: List[Tuple[Tuple[str, str, str], str, DependencyNode]] = []
        for nid, deg in in_degree.items():
            if deg == 0:
                node = self._nodes[nid]
                key = self._canonical_key_cache.get(nid) or node.canonical_sort_key()
                heap.append((key, nid, node))

        heapq.heapify(heap)
        sorted_nodes: List[DependencyNode] = []

        while heap:
            _, curr_id, curr_node = heapq.heappop(heap)
            sorted_nodes.append(curr_node)

            for child_id in self._dependents.get(curr_id, set()):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    child_node = self._nodes[child_id]
                    child_key = self._canonical_key_cache.get(child_id) or child_node.canonical_sort_key()
                    heapq.heappush(heap, (child_key, child_id, child_node))

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
        run_id: str = "run_default",
        production_id: str = "prod_broadway_01",
    ) -> List[InvalidationNotice]:
        """
        Performs fail-closed transitive invalidation in O(R * (V_R + E_R) + D * L).
        Given a set of upstream nodes that have shifted/changed, traverses all downstream
        dependents in deterministic topological order.
        Generates cryptographically linked, tamper-evident InvalidationNotices.
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

        # Deterministic root evaluation order
        sorted_changed_ids = sorted(
            [nid for nid in change_details_map if nid in self._nodes],
            key=lambda nid: self._canonical_key_cache.get(nid) or ("", "", nid),
        )

        seq_counter = 0
        current_chain_hash = "0" * 64

        for root_id in sorted_changed_ids:
            root_node = self._nodes[root_id]
            root_info = change_details_map[root_id]

            # Forward BFS along _dependents with predecessor tracking
            queue: deque[str] = deque([root_id])
            predecessor: Dict[str, str] = {}
            visited_in_root: Set[str] = {root_id}

            while queue:
                current = queue.popleft()

                children = sorted(
                    self._dependents.get(current, set()),
                    key=lambda nid: self._canonical_key_cache.get(nid) or ("", "", nid),
                )

                for child_id in children:
                    if child_id not in visited_in_root:
                        visited_in_root.add(child_id)
                        predecessor[child_id] = current
                        queue.append(child_id)

                    pair = (child_id, root_id)
                    if pair in visited_invalidation_pairs:
                        continue
                    visited_invalidation_pairs.add(pair)

                    child_node = self._nodes[child_id]
                    if child_node.node_type != NodeType.COUNSEL_DECISION:
                        continue

                    # Backtrack causal path in O(L)
                    curr_node = child_id
                    causal_path = [curr_node]
                    while curr_node != root_id and curr_node in predecessor:
                        curr_node = predecessor[curr_node]
                        causal_path.append(curr_node)
                    causal_path.reverse()

                    is_direct = len(causal_path) == 2
                    hop_count = len(causal_path) - 1

                    if not is_direct:
                        reason_code = "UPSTREAM_DEPENDENCY_STALE"
                    else:
                        reason_code = root_info.get("reason_code")
                        if not reason_code:
                            if root_node.node_type == NodeType.CREATIVE_USE:
                                reason_code = "CREATIVE_CONTEXT_ALTERED"
                            elif root_node.node_type in (NodeType.EVIDENCE_SNAPSHOT, NodeType.CONTRACT_AGREEMENT):
                                reason_code = "EXTERNAL_EVIDENCE_SHIFT"
                            elif root_node.node_type == NodeType.SCENE_CONTEXT:
                                reason_code = "SCENE_CONTEXT_MODIFIED"
                            elif root_node.node_type == NodeType.SCRIPT_BEAT:
                                reason_code = "SCRIPT_BEAT_ALTERED"
                            else:
                                reason_code = "UPSTREAM_DEPENDENCY_STALE"

                    custom_explanation = root_info.get("explanation")
                    if custom_explanation:
                        explanation = (
                            f"Downstream clearance decision '{child_node.node_id}' for '{child_node.stable_lineage_key}' "
                            f"invalidated: {custom_explanation}"
                        )
                    else:
                        path_str = " -> ".join(causal_path)
                        explanation = (
                            f"Downstream clearance decision '{child_node.node_id}' for '{child_node.stable_lineage_key}' "
                            f"invalidated due to causal drift in upstream {root_node.node_type.value} '{root_node.node_id}' "
                            f"(stable lineage key: '{root_node.stable_lineage_key}'). "
                            f"Causal lineage dependency path: [{path_str}]."
                        )

                    seq_counter += 1
                    notice = InvalidationNotice(
                        notice_id=f"inv_not_{root_id}_{child_node.node_id}_{seq_counter:04d}",
                        organization_id=self.organization_id,
                        production_id=production_id,
                        run_id=run_id,
                        sequence_number=seq_counter,
                        previous_notice_hash=current_chain_hash,
                        affected_node_id=child_node.node_id,
                        affected_lineage_key=child_node.stable_lineage_key,
                        affected_node_type=child_node.node_type,
                        root_cause_node_id=root_node.node_id,
                        root_cause_lineage_key=root_node.stable_lineage_key,
                        root_cause_type=root_node.node_type,
                        is_direct=is_direct,
                        hop_count=hop_count,
                        reason_code=reason_code,
                        explanation=explanation,
                        invalidation_path=causal_path,
                        changed_state_details=root_info,
                    )
                    current_chain_hash = notice.notice_hash
                    notices.append(notice)

        notices.sort(
            key=lambda n: (n.affected_lineage_key, n.affected_node_id, n.root_cause_node_id)
        )
        return notices

    def persist_invalidation_notices(
        self,
        repository: Any,
        notices: Union[Sequence[Union[InvalidationNotice, Dict[str, Any]]], str],
        production_id: Optional[Union[str, Sequence[Union[InvalidationNotice, Dict[str, Any]]]]] = None,
        run_id: Optional[Union[str, Sequence[Union[InvalidationNotice, Dict[str, Any]]]]] = None,
        extra_notices: Optional[Sequence[Union[InvalidationNotice, Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Persists generated InvalidationNotices to the tenant repository's discrete subcollection:
        /organizations/{org_id}/productions/{prod_id}/runs/{run_id}/invalidation_notices/{notice_id}

        Polymorphic signature supporting:
        - persist_invalidation_notices(repo, notices, production_id=..., run_id=...)
        - persist_invalidation_notices(repo, production_id, run_id, notices)
        """
        if isinstance(notices, str):
            target_prod_id = notices
            target_run_id = str(production_id) if production_id is not None else "run_default"
            target_notices: Sequence[Any] = (
                run_id if isinstance(run_id, (list, tuple)) else (extra_notices or [])
            )
        else:
            target_notices = notices
            target_prod_id = str(production_id) if isinstance(production_id, str) else (
                target_notices[0].production_id
                if target_notices and hasattr(target_notices[0], "production_id")
                else "prod_broadway_01"
            )
            target_run_id = str(run_id) if isinstance(run_id, str) else (
                target_notices[0].run_id
                if target_notices and hasattr(target_notices[0], "run_id")
                else "run_default"
            )

        if not target_notices:
            return []

        if hasattr(repository, "save_invalidation_notices_batch"):
            return repository.save_invalidation_notices_batch(
                production_id=target_prod_id,
                run_id=target_run_id,
                notices=target_notices,
            )
        elif hasattr(repository, "save_invalidation_notice"):
            return [
                repository.save_invalidation_notice(target_prod_id, target_run_id, n)
                for n in target_notices
            ]
        return [
            n.to_firestore_dict() if hasattr(n, "to_firestore_dict") else dict(n)
            for n in target_notices
        ]

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
            key=lambda nid: self._canonical_key_cache.get(nid) or ("", "", nid),
        )

    @classmethod
    def build_clearance_graph(
        cls,
        base_uses: List[CreativeUse],
        target_uses: Optional[List[CreativeUse]] = None,
        prior_decisions: Optional[List[CounselDecision]] = None,
        evidence_snapshots: Optional[Union[Dict[str, PublicEvidenceSnapshot], List[PublicEvidenceSnapshot]]] = None,
        contracts: Optional[List[ContractAgreement]] = None,
        atomic_claims: Optional[List[AtomicRightsClaim]] = None,
        scene_contexts: Optional[List[SceneContext]] = None,
        script_beats: Optional[List[ScriptBeat]] = None,
        clarification_requests: Optional[List[ClarificationRequest]] = None,
        organization_id: str = "org_studio_alpha",
        quarantine_cycles: bool = False,
    ) -> ClearanceDependencyGraph:
        """
        Constructs a complete canonical ClearanceDependencyGraph from domain entities.
        Ensures input-order invariance by canonical sorting before building DAG.
        Uses multi-map indexing to wire multiple uses, contracts, and evidence snapshots sharing keys.
        """
        graph = cls(organization_id=organization_id)

        # 1. Register Scene Contexts
        for scene in sorted(scene_contexts or [], key=lambda s: (s.stable_lineage_key, s.scene_id)):
            graph.add_scene_context(scene)

        # 2. Register Script Beats
        for beat in sorted(script_beats or [], key=lambda b: (b.stable_lineage_key, b.beat_id)):
            graph.add_script_beat(beat)
            if beat.scene_id and graph.has_node(beat.scene_id):
                graph.add_dependency(
                    dependent_id=beat.beat_id,
                    dependency_id=beat.scene_id,
                    kind=DependencyKind.SCENE_CONTAINMENT,
                    description=f"Script beat contained in scene '{beat.scene_id}'",
                    validate_cycle=False,
                )

        # Index Scene Contexts for fast lookup
        scene_by_id: Dict[str, str] = {}
        scene_by_number: Dict[str, str] = {}
        scene_by_key: Dict[str, str] = {}
        for s in (scene_contexts or []):
            scene_by_id[s.scene_id] = s.scene_id
            if s.scene_number:
                scene_by_number[s.scene_number.strip().lower()] = s.scene_id
            if s.stable_lineage_key:
                scene_by_key[s.stable_lineage_key] = s.scene_id

        # 3. Creative Uses (Multi-map architecture)
        sorted_base = sorted(base_uses or [], key=lambda u: (u.stable_lineage_key, u.use_id))
        sorted_target = sorted(target_uses or [], key=lambda u: (u.stable_lineage_key, u.use_id))

        def _wire_use_containment(u: CreativeUse) -> None:
            use_meta = getattr(u, "metadata", None) or {}
            beat_id = use_meta.get("beat_id") if isinstance(use_meta, dict) else None
            scene_id = use_meta.get("scene_id") if isinstance(use_meta, dict) else None

            wired_beat = False
            if beat_id and graph.has_node(beat_id):
                try:
                    graph.add_dependency(
                        dependent_id=u.use_id,
                        dependency_id=beat_id,
                        kind=DependencyKind.BEAT_NARRATIVE,
                        description=f"Creative use contained in script beat '{beat_id}'",
                        validate_cycle=not quarantine_cycles,
                    )
                    wired_beat = True
                except CycleDetectedError:
                    if not quarantine_cycles:
                        raise

            if scene_id and graph.has_node(scene_id) and not wired_beat:
                try:
                    graph.add_dependency(
                        dependent_id=u.use_id,
                        dependency_id=scene_id,
                        kind=DependencyKind.SCENE_CONTAINMENT,
                        description=f"Creative use contained in scene '{scene_id}'",
                        validate_cycle=not quarantine_cycles,
                    )
                except CycleDetectedError:
                    if not quarantine_cycles:
                        raise
            elif not wired_beat and u.scene_or_timecode:
                st = u.scene_or_timecode.strip()
                st_low = st.lower()
                matched_sid = None
                if st in scene_by_id:
                    matched_sid = scene_by_id[st]
                elif st_low.startswith("scene "):
                    toks = st[6:].strip().split()
                    if toks and toks[0].lower() in scene_by_number:
                        matched_sid = scene_by_number[toks[0].lower()]
                elif st_low in scene_by_number:
                    matched_sid = scene_by_number[st_low]
                elif st in scene_by_key:
                    matched_sid = scene_by_key[st]

                if matched_sid and graph.has_node(matched_sid):
                    try:
                        graph.add_dependency(
                            dependent_id=u.use_id,
                            dependency_id=matched_sid,
                            kind=DependencyKind.SCENE_CONTAINMENT,
                            description=f"Creative use in scene '{matched_sid}'",
                            validate_cycle=not quarantine_cycles,
                        )
                    except CycleDetectedError:
                        if not quarantine_cycles:
                            raise

        use_by_key: Dict[str, List[CreativeUse]] = defaultdict(list)
        for use in sorted_base:
            graph.add_creative_use(use)
            use_by_key[use.stable_lineage_key].append(use)
            _wire_use_containment(use)

        for use in sorted_target:
            if not graph.has_node(use.use_id):
                graph.add_creative_use(use)
                _wire_use_containment(use)
            if use not in use_by_key[use.stable_lineage_key]:
                use_by_key[use.stable_lineage_key].append(use)

        # 4. Evidence Snapshots (Multi-map architecture)
        ev_items = (
            list(evidence_snapshots.values())
            if isinstance(evidence_snapshots, dict)
            else list(evidence_snapshots or [])
        )
        sorted_evidence = sorted(ev_items, key=lambda e: (e.stable_lineage_key, e.snapshot_id))
        evidence_by_key: Dict[str, List[PublicEvidenceSnapshot]] = defaultdict(list)
        for ev in sorted_evidence:
            graph.add_evidence_snapshot(ev)
            evidence_by_key[ev.stable_lineage_key].append(ev)

        # 5. Register Contract Agreements (Multi-map architecture)
        sorted_contracts = sorted(contracts or [], key=lambda c: (c.stable_lineage_key, c.agreement_id))
        contract_by_key: Dict[str, List[ContractAgreement]] = defaultdict(list)
        for c in sorted_contracts:
            graph.add_contract_agreement(c)
            contract_by_key[c.stable_lineage_key].append(c)

        # 6. Register Clarification Requests
        clrfs_by_claim: Dict[str, List[ClarificationRequest]] = defaultdict(list)
        clrfs_by_lineage: Dict[str, List[ClarificationRequest]] = defaultdict(list)
        for clrf in sorted(clarification_requests or [], key=lambda k: (k.stable_lineage_key, k.request_id)):
            graph.add_clarification_request(clrf)
            if clrf.claim_id:
                clrfs_by_claim[clrf.claim_id].append(clrf)
                if graph.has_node(clrf.claim_id):
                    graph.add_dependency(
                        dependent_id=clrf.request_id,
                        dependency_id=clrf.claim_id,
                        kind=DependencyKind.UPSTREAM_CLAIM,
                        description=f"Clarification request bound to claim '{clrf.claim_id}'",
                        validate_cycle=False,
                    )
            if clrf.stable_lineage_key:
                clrfs_by_lineage[clrf.stable_lineage_key].append(clrf)

        # 7. Register Atomic Rights Claims
        claims_by_occurrence: Dict[str, List[AtomicRightsClaim]] = defaultdict(list)
        claims_by_lineage: Dict[str, List[AtomicRightsClaim]] = defaultdict(list)
        for claim in sorted(atomic_claims or [], key=lambda a: (a.occurrence_lineage_id or a.claim_id, a.claim_id)):
            graph.add_atomic_rights_claim(claim)
            if claim.occurrence_id:
                claims_by_occurrence[claim.occurrence_id].append(claim)
                if graph.has_node(claim.occurrence_id):
                    graph.add_dependency(
                        dependent_id=claim.claim_id,
                        dependency_id=claim.occurrence_id,
                        kind=DependencyKind.CLAIM_DERIVATION,
                        description=f"Atomic claim derived from creative occurrence '{claim.occurrence_id}'",
                        validate_cycle=False,
                    )
            if claim.occurrence_lineage_id:
                claims_by_lineage[claim.occurrence_lineage_id].append(claim)

        # 8. Register all Counsel Decisions
        sorted_decisions = sorted(prior_decisions or [], key=lambda d: (d.stable_lineage_key, d.decision_id))
        for dec in sorted_decisions:
            graph.add_counsel_decision(dec)

        # 9. Wire all causal dependency edges
        for dec in sorted_decisions:
            # Wire creative use dependencies
            if graph.has_node(dec.use_id):
                graph.add_dependency(
                    dependent_id=dec.decision_id,
                    dependency_id=dec.use_id,
                    kind=DependencyKind.CREATIVE_CONTEXT,
                    description=f"Counsel decision depends on creative use '{dec.use_id}' context hash",
                    validate_cycle=False,
                )
            elif dec.stable_lineage_key in use_by_key:
                for matched_use in use_by_key[dec.stable_lineage_key]:
                    if graph.has_node(matched_use.use_id):
                        graph.add_dependency(
                            dependent_id=dec.decision_id,
                            dependency_id=matched_use.use_id,
                            kind=DependencyKind.CREATIVE_CONTEXT,
                            description=f"Counsel decision depends on creative use '{matched_use.use_id}' context hash",
                            validate_cycle=False,
                        )

            # Wire evidence snapshot dependencies (all matching snapshots wired)
            if dec.stable_lineage_key in evidence_by_key:
                for matched_ev in evidence_by_key[dec.stable_lineage_key]:
                    if graph.has_node(matched_ev.snapshot_id):
                        graph.add_dependency(
                            dependent_id=dec.decision_id,
                            dependency_id=matched_ev.snapshot_id,
                            kind=DependencyKind.EVIDENCE_STANCE,
                            description=f"Counsel decision depends on evidence snapshot '{matched_ev.snapshot_id}'",
                            validate_cycle=False,
                        )

            # Wire contract agreement dependencies (all matching contracts wired)
            if dec.stable_lineage_key in contract_by_key:
                for matched_contract in contract_by_key[dec.stable_lineage_key]:
                    if graph.has_node(matched_contract.agreement_id):
                        graph.add_dependency(
                            dependent_id=dec.decision_id,
                            dependency_id=matched_contract.agreement_id,
                            kind=DependencyKind.CONTRACTUAL_GRANT,
                            description=f"Counsel decision depends on active license '{matched_contract.agreement_id}'",
                            validate_cycle=False,
                        )

            # Wire atomic claims derived from this decision's creative use or matching lineage
            matched_claims_dict: Dict[str, AtomicRightsClaim] = {}
            for cl in claims_by_occurrence.get(dec.use_id, []):
                matched_claims_dict[cl.claim_id] = cl
            for cl in claims_by_lineage.get(dec.stable_lineage_key, []):
                matched_claims_dict[cl.claim_id] = cl
            for claim_id in sorted(matched_claims_dict.keys()):
                if graph.has_node(claim_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=claim_id,
                        kind=DependencyKind.UPSTREAM_CLAIM,
                        description=f"Counsel decision depends on atomic claim '{claim_id}'",
                        validate_cycle=False,
                    )

            # Wire clarification requests bound to this decision's claim or lineage
            matched_clrfs_dict: Dict[str, ClarificationRequest] = {}
            for clrf in clrfs_by_claim.get(dec.use_id, []):
                matched_clrfs_dict[clrf.request_id] = clrf
            for clrf in clrfs_by_lineage.get(dec.stable_lineage_key, []):
                matched_clrfs_dict[clrf.request_id] = clrf
            for req_id in sorted(matched_clrfs_dict.keys()):
                if graph.has_node(req_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=req_id,
                        kind=DependencyKind.CLARIFICATION_ATTESTATION,
                        description=f"Counsel decision conditioned on clarification '{req_id}'",
                        validate_cycle=False,
                    )

            # Wire explicit dependency IDs
            for explicit_dep_id in sorted(dec.dependency_ids):
                if graph.has_node(explicit_dep_id):
                    graph.add_dependency(
                        dependent_id=dec.decision_id,
                        dependency_id=explicit_dep_id,
                        kind=DependencyKind.PRIOR_DECISION,
                        description=f"Explicit clearance dependency '{explicit_dep_id}'",
                        validate_cycle=False,
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
                                validate_cycle=False,
                            )

            # Wire superseding decisions
            if dec.supersedes_decision_id and graph.has_node(dec.supersedes_decision_id):
                graph.add_dependency(
                    dependent_id=dec.decision_id,
                    dependency_id=dec.supersedes_decision_id,
                    kind=DependencyKind.PRIOR_DECISION,
                    description=f"Supersedes prior counsel decision '{dec.supersedes_decision_id}'",
                    validate_cycle=False,
                )

        # Linear verification of DAG acyclicity at end of build (O(V + E))
        if quarantine_cycles:
            cycles = graph.find_cycles()
            if cycles:
                for cyc in cycles:
                    for i in range(len(cyc)):
                        u = cyc[i]
                        v = cyc[(i + 1) % len(cyc)]
                        with graph._lock:
                            if (u, v) in graph._edges:
                                del graph._edges[(u, v)]
                            if u in graph._dependencies and v in graph._dependencies[u]:
                                graph._dependencies[u].remove(v)
                            if v in graph._dependents and u in graph._dependents[v]:
                                graph._dependents[v].remove(u)
        else:
            graph.validate_dag_acyclicity()

        return graph


DependencyGraph = ClearanceDependencyGraph
build_clearance_graph = ClearanceDependencyGraph.build_clearance_graph

__all__ = [
    "ClearanceGraphError",
    "CycleDetectedError",
    "NodeNotFoundError",
    "CrossTenantBoundaryViolationError",
    "GraphFrozenError",
    "NodeType",
    "DependencyKind",
    "DependencyNode",
    "DependencyEdge",
    "InvalidationNotice",
    "ClearanceDependencyGraph",
    "DependencyGraph",
    "build_clearance_graph",
]
