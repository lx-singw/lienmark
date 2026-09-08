"""
backend/storage/baseline_store.py
Production-ready persistence layer for Production Baseline Snapshots.
Supports physical Firestore hierarchy, thread-safe InMemory fallback,
monotonic version progression verification, and transactional writes.
"""

from __future__ import annotations

import abc
import copy
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.core.baseline_types import (
    BaselineAlreadyExistsError,
    BaselineLineageBrokenError,
    ProductionVersion,
    validate_tenant_boundary,
)

logger = logging.getLogger("lienmark.storage.baseline")


def parse_version_tuple(v: str) -> Optional[Tuple[int, ...]]:
    """Parse versions like 'v1', 'v2', 'v1.2.3', '1' into integer tuples."""
    if not v or not isinstance(v, str):
        return None
    try:
        return tuple(int(p) for p in v.strip().lstrip("vV").split("."))
    except (ValueError, AttributeError):
        return None


def _verify_baseline_progression(
    baseline: ProductionVersion, latest: Optional[ProductionVersion], has_fn: Callable[[str, str, str], bool],
) -> None:
    """Verifies that baseline advances monotonically or validates parent baseline linkage."""
    if baseline.previous_version_id is not None:
        if not has_fn(baseline.tenant_id, baseline.production_id, baseline.previous_version_id):
            raise BaselineLineageBrokenError(f"Lineage broken: parent baseline '{baseline.previous_version_id}' does not exist.")
    if latest is None:
        return
    new_vt, lat_vt = parse_version_tuple(baseline.version_id), parse_version_tuple(latest.version_id)
    is_monotonic = bool(new_vt and lat_vt and new_vt > lat_vt)
    has_parent = bool(baseline.previous_version_id and has_fn(baseline.tenant_id, baseline.production_id, baseline.previous_version_id))
    if not is_monotonic and not has_parent:
        raise BaselineLineageBrokenError(f"Baseline '{baseline.version_id}' does not advance monotonically from '{latest.version_id}'.")


class BaselineStoreInterface(abc.ABC):
    """Abstract persistence interface for Production Baseline Snapshots."""

    @abc.abstractmethod
    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        """Atomically saves a baseline snapshot. Rejects mutation or regression."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_baseline(self, tenant_id: str, production_id: str, version_id: str) -> Optional[ProductionVersion]:
        """Retrieves a baseline snapshot by tenant, production, and version ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_latest_baseline(self, tenant_id: str, production_id: str) -> Optional[ProductionVersion]:
        """Retrieves the latest registered baseline snapshot for the production."""
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
    """Thread-safe in-memory baseline store for local development and pytest."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._baselines: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        validate_tenant_boundary(baseline.tenant_id, baseline.production_id)
        key = (baseline.tenant_id, baseline.production_id, baseline.version_id)
        with self._lock:
            if key in self._baselines:
                raise BaselineAlreadyExistsError(f"Baseline '{baseline.version_id}' already exists for '{baseline.production_id}'.")
            latest = self.get_latest_baseline(baseline.tenant_id, baseline.production_id)
            _verify_baseline_progression(baseline, latest, lambda t, p, v: (t, p, v) in self._baselines)
            self._baselines[key] = copy.deepcopy(baseline.model_dump())
            return baseline

    def get_baseline(self, tenant_id: str, production_id: str, version_id: str) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            raw = self._baselines.get((tenant_id, production_id, version_id))
            return ProductionVersion.model_validate(copy.deepcopy(raw)) if raw is not None else None

    def get_latest_baseline(self, tenant_id: str, production_id: str) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            baselines = self.list_baselines(tenant_id, production_id)
            if not baselines:
                return None
            return sorted(baselines, key=lambda b: (b.created_at, parse_version_tuple(b.version_id) or ()))[-1]

    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            results = [
                ProductionVersion.model_validate(copy.deepcopy(raw))
                for (t, p, _), raw in self._baselines.items() if t == tenant_id and p == production_id
            ]
            return sorted(results, key=lambda b: b.created_at)

    def has_baseline(self, tenant_id: str, production_id: str, version_id: str) -> bool:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            return (tenant_id, production_id, version_id) in self._baselines

    def clear(self) -> None:
        with self._lock:
            self._baselines.clear()


class FirestoreBaselineStore(BaselineStoreInterface):
    """Native Google Cloud Firestore baseline persistence layer."""

    def __init__(self, client: Optional[Any] = None) -> None:
        self._lock = threading.RLock()
        self._fallback = InMemoryBaselineStore()
        self._client = client if client is not None else self._init_gcp_client()

    def _init_gcp_client(self) -> Optional[Any]:
        try:
            from google.cloud import firestore
            project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
            return firestore.Client(project=project)
        except Exception as exc:
            logger.info("Native Firestore unavailable; operating in fallback mode: %s", exc)
            return None

    def _doc_ref(self, t_id: str, p_id: str, v_id: str) -> Any:
        return self._client.collection("organizations").document(t_id).collection("productions").document(p_id).collection("baselines").document(v_id)

    def save_baseline(self, baseline: ProductionVersion) -> ProductionVersion:
        validate_tenant_boundary(baseline.tenant_id, baseline.production_id)
        with self._lock:
            if self._client is None:
                return self._fallback.save_baseline(baseline)
            if self.has_baseline(baseline.tenant_id, baseline.production_id, baseline.version_id):
                raise BaselineAlreadyExistsError(f"Baseline '{baseline.version_id}' already exists for '{baseline.production_id}'.")
            latest = self.get_latest_baseline(baseline.tenant_id, baseline.production_id)
            _verify_baseline_progression(baseline, latest, lambda t, p, v: self.has_baseline(t, p, v))
            from google.cloud import firestore
            doc_ref = self._doc_ref(baseline.tenant_id, baseline.production_id, baseline.version_id)
            p_ref = self._doc_ref(baseline.tenant_id, baseline.production_id, baseline.previous_version_id) if baseline.previous_version_id else None

            @firestore.transactional
            def _txn(transaction: Any) -> None:
                if doc_ref.get(transaction=transaction).exists:
                    raise BaselineAlreadyExistsError(f"Baseline '{baseline.version_id}' already exists for '{baseline.production_id}'.")
                if p_ref is not None and not p_ref.get(transaction=transaction).exists:
                    raise BaselineLineageBrokenError(f"Parent baseline '{baseline.previous_version_id}' does not exist.")
                transaction.set(doc_ref, baseline.model_dump())

            transaction = self._client.transaction()
            _txn(transaction)
            return baseline

    def get_baseline(self, tenant_id: str, production_id: str, version_id: str) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            if self._client is None:
                return self._fallback.get_baseline(tenant_id, production_id, version_id)
            snap = self._doc_ref(tenant_id, production_id, version_id).get()
            return ProductionVersion.model_validate(snap.to_dict()) if snap.exists else None

    def get_latest_baseline(self, tenant_id: str, production_id: str) -> Optional[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            if self._client is None:
                return self._fallback.get_latest_baseline(tenant_id, production_id)
            baselines = self.list_baselines(tenant_id, production_id)
            if not baselines:
                return None
            return sorted(baselines, key=lambda b: (b.created_at, parse_version_tuple(b.version_id) or ()))[-1]

    def list_baselines(self, tenant_id: str, production_id: str) -> List[ProductionVersion]:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            if self._client is None:
                return self._fallback.list_baselines(tenant_id, production_id)
            coll_ref = self._client.collection("organizations").document(tenant_id).collection("productions").document(production_id).collection("baselines")
            return sorted([ProductionVersion.model_validate(s.to_dict()) for s in coll_ref.stream() if s.exists], key=lambda b: b.created_at)

    def has_baseline(self, tenant_id: str, production_id: str, version_id: str) -> bool:
        validate_tenant_boundary(tenant_id, production_id)
        with self._lock:
            if self._client is None:
                return self._fallback.has_baseline(tenant_id, production_id, version_id)
            return bool(self._doc_ref(tenant_id, production_id, version_id).get().exists)


_GLOBAL_STORE: Optional[BaselineStoreInterface] = None
_GLOBAL_STORE_LOCK = threading.Lock()


def get_default_baseline_store(force_in_memory: bool = False) -> BaselineStoreInterface:
    """Factory retrieving configured singleton BaselineStoreInterface."""
    global _GLOBAL_STORE
    with _GLOBAL_STORE_LOCK:
        if force_in_memory:
            return InMemoryBaselineStore()
        if _GLOBAL_STORE is None:
            _GLOBAL_STORE = FirestoreBaselineStore()
        return _GLOBAL_STORE
