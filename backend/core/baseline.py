"""
backend/core/baseline.py

Production Baseline Engine for Lienmark Sprint 2.3.
Coordinates registration, cryptographic digest verification, lineage continuity,
and immutable retrieval for cinematic script revision baselines.
Authored strictly under Google AntiGravity architectural guidelines for Sprint 2.3.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from backend.core.baseline_types import (
    MAX_BASELINE_PAYLOAD_BYTES,
    BaselineAlreadyExistsError,
    BaselineIntegrityError,
    BaselineLineageBrokenError,
    BaselineNotFoundError,
    BaselinePayloadTooLargeError,
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
    compute_baseline_digest,
    validate_tenant_boundary,
)
from backend.storage.baseline_store import (
    BaselineStoreInterface,
    get_default_baseline_store,
)

logger = logging.getLogger("lienmark.core.baseline")


class ProductionBaselineEngine:
    """
    Authoritative coordinator for Production Baseline lifecycles.
    Guarantees strict tenant isolation, immutable append-only semantics,
    unbroken lineage pointers, and cryptographic tamper detection.
    """

    def __init__(self, store: Optional[BaselineStoreInterface] = None) -> None:
        self._store = store or get_default_baseline_store()

    @property
    def store(self) -> BaselineStoreInterface:
        return self._store

    def _assemble_baseline(
        self,
        tenant_id: str,
        production_id: str,
        version_id: str,
        content_hash: str,
        parser_metadata: ParserMetadata,
        claims: Sequence[CreativeUseNode],
        version_tag: str,
        creator: str,
        previous_version_id: Optional[str],
    ) -> ProductionVersion:
        """Assembles and digests an immutable ProductionVersion snapshot."""
        digest = compute_baseline_digest(
            version_id=version_id,
            production_id=production_id,
            tenant_id=tenant_id,
            version_tag=version_tag,
            content_hash=content_hash,
            parser_metadata=parser_metadata,
            claims=claims,
            previous_version_id=previous_version_id,
        )
        return ProductionVersion(
            version_id=version_id,
            production_id=production_id,
            tenant_id=tenant_id,
            version_tag=version_tag,
            content_hash=content_hash,
            parser_metadata=parser_metadata,
            claims=tuple(claims),
            creator=creator,
            previous_version_id=previous_version_id,
            baseline_digest=digest,
        )

    def _validate_registration(
        self, tenant_id: str, production_id: str, version_id: str, prev_id: Optional[str]
    ) -> None:
        validate_tenant_boundary(tenant_id, production_id)
        if self._store.has_baseline(tenant_id, production_id, version_id):
            raise BaselineAlreadyExistsError(
                f"Baseline '{version_id}' already registered for production '{production_id}'."
            )
        self._validate_predecessor(tenant_id, production_id, prev_id)

    def register_baseline(
        self,
        tenant_id: str,
        production_id: str,
        version_id: str,
        content_hash: str,
        parser_metadata: ParserMetadata,
        claims: Sequence[CreativeUseNode],
        version_tag: str = "",
        creator: str = "system:intake",
        previous_version_id: Optional[str] = None,
    ) -> ProductionVersion:
        """Registers a new immutable baseline snapshot for a production cut."""
        self._validate_registration(tenant_id, production_id, version_id, previous_version_id)
        baseline = self._assemble_baseline(
            tenant_id=tenant_id,
            production_id=production_id,
            version_id=version_id,
            content_hash=content_hash,
            parser_metadata=parser_metadata,
            claims=claims,
            version_tag=version_tag,
            creator=creator,
            previous_version_id=previous_version_id,
        )
        self._guard_payload_size(baseline)
        self._store.save_baseline(baseline)
        logger.info(
            "Registered baseline '%s' for production '%s' (claims: %d, digest: %.12s...)",
            version_id,
            production_id,
            len(claims),
            baseline.baseline_digest,
        )
        return baseline

    def _validate_predecessor(
        self, tenant_id: str, production_id: str, previous_version_id: Optional[str]
    ) -> None:
        if previous_version_id:
            if not self._store.has_baseline(tenant_id, production_id, previous_version_id):
                raise BaselineLineageBrokenError(
                    f"Lineage broken: predecessor baseline '{previous_version_id}' "
                    f"does not exist for production '{production_id}'."
                )

    def _guard_payload_size(self, baseline: ProductionVersion) -> None:
        serialized = json.dumps(baseline.model_dump(), default=str)
        if len(serialized.encode("utf-8")) > MAX_BASELINE_PAYLOAD_BYTES:
            raise BaselinePayloadTooLargeError(
                f"Baseline payload exceeds maximum size limit of {MAX_BASELINE_PAYLOAD_BYTES} bytes."
            )

    def get_baseline(
        self, tenant_id: str, production_id: str, version_id: str
    ) -> ProductionVersion:
        """Retrieves and cryptographically verifies an immutable baseline snapshot."""
        validate_tenant_boundary(tenant_id, production_id)
        baseline = self._store.get_baseline(tenant_id, production_id, version_id)
        if baseline is None:
            raise BaselineNotFoundError(
                f"Baseline '{version_id}' not found for production '{production_id}'."
            )

        expected_digest = compute_baseline_digest(
            version_id=baseline.version_id,
            production_id=baseline.production_id,
            tenant_id=baseline.tenant_id,
            version_tag=baseline.version_tag,
            content_hash=baseline.content_hash,
            parser_metadata=baseline.parser_metadata,
            claims=baseline.claims,
            previous_version_id=baseline.previous_version_id,
        )
        if baseline.baseline_digest != expected_digest:
            raise BaselineIntegrityError(
                f"Tampering detected! Stored digest '{baseline.baseline_digest}' "
                f"does not match computed digest '{expected_digest}'."
            )
        return baseline

    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        """Lists all registered baseline snapshots for a given production."""
        validate_tenant_boundary(tenant_id, production_id)
        return self._store.list_baselines(tenant_id, production_id)

    def get_lineage_history(
        self, tenant_id: str, production_id: str, head_version_id: str
    ) -> List[ProductionVersion]:
        """
        Traverses predecessor pointers to assemble complete ordered lineage chain.
        Returns ordered list from root ancestor to head version.
        """
        validate_tenant_boundary(tenant_id, production_id)
        history: List[ProductionVersion] = []
        curr_id: Optional[str] = head_version_id
        visited = set()

        while curr_id is not None:
            if curr_id in visited:
                raise BaselineLineageBrokenError(
                    f"Circular lineage detected: version '{curr_id}' already in path."
                )
            visited.add(curr_id)
            baseline = self.get_baseline(tenant_id, production_id, curr_id)
            history.append(baseline)
            curr_id = baseline.previous_version_id

        return list(reversed(history))

    def extract_baseline_claims(
        self, tenant_id: str, production_id: str, version_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extracts claims from a registered baseline adapted for downstream
        consumption by InvalidationEngine and DeltaEngine.
        """
        baseline = self.get_baseline(tenant_id, production_id, version_id)
        return [
            {
                "claim_id": c.claim_id,
                "use_id": c.claim_id,
                "stable_lineage_key": c.stable_lineage_key,
                "asset_type": c.asset_type,
                "scene_or_timecode": c.scene_or_timecode,
                "description": c.description,
                "duration_or_prominence": c.prominence,
                "prominence": c.prominence,
                "context": c.context,
                "context_hash": c.context_hash,
                "intended_scope": c.intended_scope,
                "licensed_scope": c.licensed_scope,
                "confidence_score": c.confidence_score,
                "source_span": c.source_span,
                "metadata": c.metadata,
            }
            for c in baseline.claims
        ]
