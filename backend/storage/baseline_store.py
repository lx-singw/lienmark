"""
backend/storage/baseline_store.py

Production-ready persistence layer for Production Baseline Snapshots.
Supports:
1. Physical Firestore collection hierarchy:
   /organizations/{org_id}/productions/{prod_id}/baselines/{version_id}
2. Transparent thread-safe InMemory fallback (InMemoryBaselineStore) for offline/pytest.
3. Immutability enforcement: Rejects overwrites of already-registered baseline versions.
Authored strictly under Google AntiGravity architectural guidelines for Sprint 2.3.
"""

from __future__ import annotations

import abc
import copy
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.core.baseline_types import (
    BaselineAlreadyExistsError,
    ProductionVersion,
    validate_tenant_boundary,
)

logger = logging.getLogger("lienmark.storage.baseline")


class BaselineStoreInterface(abc.ABC):
    """Abstract persistence interface for Production Baseline Snapshots."""

    @abc.abstractmethod
    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        """Atomically saves a baseline snapshot. Rejects mutation if version exists."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_baseline(
        self, tenant_id: str, production_id: str, version_id: str
    ) -> Optional[ProductionVersion]:
        """Retrieves a baseline snapshot by tenant, production, and version ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        """Lists all registered baseline snapshots for a production."""
        raise NotImplementedError

    @abc.abstractmethod
    def has_baseline(self, tenant_id: str, production_id: str, version_id: str) -> bool:
        """Checks existence of a baseline snapshot."""
        raise NotImplementedError


class InMemoryBaselineStore(BaselineStoreInterface):
    """
    Thread-safe in-memory baseline store for local development, pytest,
    and offline execution without live GCP Firestore credentials.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._baselines: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        validate_tenant_boundary(baseline.tenant_id, baseline.production_id)
        key = (baseline.tenant_id, baseline.production_id, baseline.version_id)
        with self._lock:
            if key in self._baselines:
                raise BaselineAlreadyExistsError(
                    f"Baseline '{baseline.version_id}' already exists for production '{baseline.production_id}'."
                )
            self._baselines[key] = copy.deepcopy(baseline.model_dump())
            return baseline

    def get_baseline(
        self, tenant_id: str, production_id: str, version_id: str
    ) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        key = (tenant_id, production_id, version_id)
        with self._lock:
            raw = self._baselines.get(key)
            if raw is None:
                return None
            return ProductionVersion.model_validate(copy.deepcopy(raw))

    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            results: List[ProductionVersion] = []
            for (t_id, p_id, _), raw in self._baselines.items():
                if t_id == tenant_id and p_id == production_id:
                    results.append(ProductionVersion.model_validate(copy.deepcopy(raw)))
            return sorted(results, key=lambda b: b.created_at)

    def has_baseline(self, tenant_id: str, production_id: str, version_id: str) -> bool:
        validate_tenant_boundary(tenant_id, production_id)
        key = (tenant_id, production_id, version_id)
        with self._lock:
            return key in self._baselines

    def clear(self) -> None:
        """Test fixture helper to reset in-memory state."""
        with self._lock:
            self._baselines.clear()


class FirestoreBaselineStore(BaselineStoreInterface):
    """
    Native Google Cloud Firestore baseline persistence layer.
    Maps to /organizations/{org_id}/productions/{prod_id}/baselines/{version_id}.
    Falls back gracefully to InMemoryBaselineStore when Firestore client is unavailable.
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self._client = client
        self._fallback = InMemoryBaselineStore()
        if self._client is None:
            self._client = self._init_gcp_client()

    def _init_gcp_client(self) -> Optional[Any]:
        try:
            from google.cloud import firestore
            project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
            return firestore.Client(project=project)
        except Exception as exc:
            logger.info("Native Firestore unavailable; operating in in-memory mode: %s", exc)
            return None

    def _doc_ref(self, tenant_id: str, production_id: str, version_id: str) -> Any:
        return (
            self._client.collection("organizations")
            .document(tenant_id)
            .collection("productions")
            .document(production_id)
            .collection("baselines")
            .document(version_id)
        )

    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        validate_tenant_boundary(baseline.tenant_id, baseline.production_id)
        if self._client is None:
            return self._fallback.save_baseline(baseline)

        from google.cloud import firestore

        doc_ref = self._doc_ref(baseline.tenant_id, baseline.production_id, baseline.version_id)

        @firestore.transactional
        def _txn(transaction: Any) -> None:
            snap = doc_ref.get(transaction=transaction)
            if snap.exists:
                raise BaselineAlreadyExistsError(
                    f"Baseline '{baseline.version_id}' already exists for production '{baseline.production_id}'."
                )
            transaction.set(doc_ref, baseline.model_dump())

        transaction = self._client.transaction()
        _txn(transaction)
        return baseline

    def get_baseline(
        self, tenant_id: str, production_id: str, version_id: str
    ) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        if self._client is None:
            return self._fallback.get_baseline(tenant_id, production_id, version_id)

        doc_ref = self._doc_ref(tenant_id, production_id, version_id)
        snap = doc_ref.get()
        if not snap.exists:
            return None
        return ProductionVersion.model_validate(snap.to_dict() or {})

    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        if self._client is None:
            return self._fallback.list_baselines(tenant_id, production_id)

        coll_ref = (
            self._client.collection("organizations")
            .document(tenant_id)
            .collection("productions")
            .document(production_id)
            .collection("baselines")
        )
        snaps = coll_ref.stream()
        results = [
            ProductionVersion.model_validate(s.to_dict()) for s in snaps if s.exists
        ]
        return sorted(results, key=lambda b: b.created_at)

    def has_baseline(self, tenant_id: str, production_id: str, version_id: str) -> bool:
        validate_tenant_boundary(tenant_id, production_id)
        if self._client is None:
            return self._fallback.has_baseline(tenant_id, production_id, version_id)
        doc_ref = self._doc_ref(tenant_id, production_id, version_id)
        return bool(doc_ref.get().exists)


_GLOBAL_STORE: Optional[BaselineStoreInterface] = None
_GLOBAL_STORE_LOCK = threading.Lock()


def get_default_baseline_store(force_in_memory: bool = False) -> BaselineStoreInterface:
    """Factory retrieving the configured singleton BaselineStoreInterface."""
    global _GLOBAL_STORE
    with _GLOBAL_STORE_LOCK:
        if force_in_memory:
            return InMemoryBaselineStore()
        if _GLOBAL_STORE is None:
            _GLOBAL_STORE = FirestoreBaselineStore()
        return _GLOBAL_STORE
