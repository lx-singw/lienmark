"""
backend/storage/policy_store.py

Unified, versioned PolicyStore persistence facade for Lienmark.
Coordinates native Firestore adapter and local filesystem adapter.
Zero silent fallback: mode failure immediately raises PolicyStoreError.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from backend.storage.policy_store_firestore import FirestorePolicyStore
from backend.storage.policy_store_local import LocalPolicyStore
from backend.storage.policy_store_types import (
    PolicyChangeDispatchIntent,
    PolicyConcurrencyError,
    PolicyStoreError,
    PolicyStoreMode,
    PolicyVersionRecord,
)

logger = logging.getLogger("lienmark.storage.policy_store")

# Compatibility alias
LedgerAuditError = PolicyStoreError


class PolicyStore:
    """
    Unified PolicyStore facade coordinating LocalPolicyStore and FirestorePolicyStore.
    Enforces strict mode isolation: never falls back from Firestore to local storage.
    """

    def __init__(
        self,
        mode: PolicyStoreMode = PolicyStoreMode.LOCAL_DISK,
        base_dir: str = "output/policies",
        firestore_client: Optional[Any] = None,
        ledger: Optional[Any] = None,
    ) -> None:
        self._mode = mode
        self._base_dir = base_dir
        self._firestore_client = firestore_client
        self._ledger = ledger
        self._adapter = self._init_adapter()

    @property
    def mode(self) -> PolicyStoreMode:
        """Returns the configured store mode."""
        return self._mode

    def _init_adapter(self) -> Any:
        """Instantiates adapter according to configured mode with zero silent fallback."""
        if self._mode == PolicyStoreMode.LOCAL_DISK:
            return LocalPolicyStore(base_dir=self._base_dir, ledger=self._ledger)

        if self._mode == PolicyStoreMode.FIRESTORE:
            client = self._firestore_client
            if client is None:
                raise PolicyStoreError(
                    "Firestore mode requires a valid Firestore client (client is missing). "
                    "Silent fallback to local disk is strictly prohibited."
                )
            return FirestorePolicyStore(client=client, ledger=self._ledger)

        raise PolicyStoreError(f"Unsupported PolicyStoreMode: '{self._mode}'.")

    def save_policy_revision(
        self,
        org_id: str,
        config: Dict[str, Any],
        actor_id: str,
        idempotency_key: Optional[str] = None,
        expected_current_version: Optional[str] = None,
        action: str = "POLICY_UPDATED",
    ) -> Tuple[PolicyVersionRecord, PolicyChangeDispatchIntent]:
        """Atomically commits a new immutable policy revision and dispatch intent."""
        return self._adapter.save_policy_revision(
            org_id=org_id,
            config=config,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            expected_current_version=expected_current_version,
            action=action,
        )

    def get_active_policy(self, org_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves active policy revision record for given organization."""
        return self._adapter.get_active_policy(org_id)

    def get_policy_revision(self, org_id: str, version_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves specific historical policy revision by version ID."""
        return self._adapter.get_policy_revision(org_id, version_id)

    def save_production_override(self, org_id: str, prod_id: str, override: Dict[str, Any]) -> str:
        """Persists production-level policy override signed off by admin."""
        return self._adapter.save_production_override(org_id, prod_id, override)

    def get_production_override(self, org_id: str, prod_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves active policy override for production."""
        return self._adapter.get_production_override(org_id, prod_id)

    def list_dispatch_intents(
        self, org_id: str, status: Optional[str] = None
    ) -> List[PolicyChangeDispatchIntent]:
        """Queries pending or status-filtered policy change dispatch intents."""
        return self._adapter.list_dispatch_intents(org_id, status)

    def update_dispatch_intent_status(self, intent_id: str, status: str) -> None:
        """Updates lifecycle status for a dispatch intent."""
        self._adapter.update_dispatch_intent_status(intent_id, status)

    # Compatibility methods
    def save_policy(
        self,
        policy: Any,
        actor_id: str = "admin",
        ledger: Optional[Any] = None,
        require_ledger: bool = False,
    ) -> Tuple[Any, PolicyChangeDispatchIntent]:
        """Compatibility wrapper for StudioPolicyConfig models."""
        config = policy.model_dump() if hasattr(policy, "model_dump") else dict(policy)
        org_id = config.get("org_id", "")
        rec, intent = self.save_policy_revision(org_id=org_id, config=config, actor_id=actor_id)
        return policy, intent

    def save_override(
        self,
        override: Any,
        actor_role: str = "admin",
        ledger: Optional[Any] = None,
        require_ledger: bool = False,
    ) -> Any:
        """Compatibility wrapper for ProductionPolicyOverride models."""
        data = override.model_dump() if hasattr(override, "model_dump") else dict(override)
        org_id = data.get("org_id", "")
        prod_id = data.get("production_id", "")
        self.save_production_override(org_id=org_id, prod_id=prod_id, override=data)
        return override

    def get_override(self, org_id: str, prod_id: str) -> Optional[Dict[str, Any]]:
        """Compatibility wrapper for get_production_override."""
        return self.get_production_override(org_id, prod_id)

    def get_dispatch_intents(self, org_id: str) -> List[PolicyChangeDispatchIntent]:
        """Compatibility wrapper for list_dispatch_intents."""
        return self.list_dispatch_intents(org_id)

    def rollback_revision(
        self, org_id: str, version_id: str, previous_version: Optional[str] = None
    ) -> None:
        """Rolls back an uncommitted policy revision on the underlying adapter."""
        if hasattr(self._adapter, "rollback_revision"):
            self._adapter.rollback_revision(org_id, version_id, previous_version)

    def rollback_override(self, org_id: str, prod_id: str) -> None:
        """Rolls back an uncommitted production override on the underlying adapter."""
        if hasattr(self._adapter, "rollback_override"):
            self._adapter.rollback_override(org_id, prod_id)


_GLOBAL_POLICY_STORE: Optional[PolicyStore] = None
_GLOBAL_STORE_LOCK = threading.RLock()


def get_policy_store(
    mode: Optional[PolicyStoreMode] = None,
    base_dir: str = "output/policies",
    firestore_client: Optional[Any] = None,
    ledger: Optional[Any] = None,
    force_fresh: bool = False,
) -> PolicyStore:
    """Returns or creates the process-wide PolicyStore singleton."""
    global _GLOBAL_POLICY_STORE
    with _GLOBAL_STORE_LOCK:
        if _GLOBAL_POLICY_STORE is None or force_fresh:
            resolved_mode = mode or (
                PolicyStoreMode.FIRESTORE
                if os.getenv("POLICY_STORE_MODE", "").lower() == "firestore"
                else PolicyStoreMode.LOCAL_DISK
            )
            _GLOBAL_POLICY_STORE = PolicyStore(
                mode=resolved_mode,
                base_dir=base_dir,
                firestore_client=firestore_client,
                ledger=ledger,
            )
        return _GLOBAL_POLICY_STORE
