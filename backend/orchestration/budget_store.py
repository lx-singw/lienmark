"""
backend/orchestration/budget_store.py

Unified factory and mode dispatcher for durable budget persistence.
Enforces zero silent fallback: if firestore mode fails, raises BudgetStoreError.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

from backend.orchestration.budget_store_firestore import FirestoreBudgetStore
from backend.orchestration.budget_store_local import LocalBudgetStore
from backend.orchestration.budget_store_types import (
    BudgetPeriodSummary,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetStoreError,
    ReservationStatus,
)


class BudgetStoreMode(str, Enum):
    """Supported persistence storage modes for budget subsystem."""
    FIRESTORE = "firestore"
    LOCAL_DISK = "local_disk"


class BudgetStoreProtocol(Protocol):
    """Structural protocol defining public interface for all budget stores."""

    def reserve_budget(
        self, org_id: str, production_id: str, budget_period_id: str, run_id: str,
        action_id: str, provider: str, model_or_mode: str, max_cost_micros: int,
        expires_in_seconds: int = 300,
    ) -> BudgetReservation:
        ...

    def settle_reservation(
        self, reservation_id: str, actual_cost_micros: int, usage_measurements: Dict[str, Any],
        provider_confirmed_cost_micros: Optional[int] = None, cache_hit: bool = False,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> BudgetSettlementRecord:
        ...

    def recover_reservation(
        self, reservation_id: str, status: ReservationStatus = ReservationStatus.UNCERTAIN,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> None:
        ...

    def get_summary(self, org_id: str, production_id: str, budget_period_id: str) -> BudgetPeriodSummary:
        ...

    def set_budget_limit(self, org_id: str, production_id: str, budget_period_id: str, limit_micros: int) -> None:
        ...

    def list_reservations(
        self, org_id: str, production_id: str, budget_period_id: str,
        status: Optional[ReservationStatus] = None,
    ) -> List[BudgetReservation]:
        ...


def resolve_budget_store_mode(mode: Optional[str] = None) -> BudgetStoreMode:
    """Determines active budget store mode based on argument, env, and test context."""
    if mode:
        norm = mode.strip().lower()
        if norm in ("firestore", "gcp", "cloud"):
            return BudgetStoreMode.FIRESTORE
        if norm in ("local_disk", "local", "disk", "file"):
            return BudgetStoreMode.LOCAL_DISK
        raise BudgetStoreError(f"Unsupported budget store mode '{mode}'. Must be 'firestore' or 'local_disk'.")

    env_mode = os.getenv("BUDGET_STORE_MODE")
    if env_mode:
        return resolve_budget_store_mode(env_mode)

    if "PYTEST_CURRENT_TEST" in os.environ:
        return BudgetStoreMode.LOCAL_DISK

    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name in ("test", "testing", "local", "dev", "development"):
        return BudgetStoreMode.LOCAL_DISK

    return BudgetStoreMode.FIRESTORE


def get_budget_store(
    mode: Optional[str] = None,
    base_dir: str = "output/budgets",
    firestore_client: Optional[Any] = None,
) -> Any:
    """
    Factory creating configured BudgetStore instance.
    Guarantees zero silent fallback: firestore misconfiguration raises BudgetStoreError.
    """
    selected_mode = resolve_budget_store_mode(mode)

    if selected_mode == BudgetStoreMode.LOCAL_DISK:
        return LocalBudgetStore(base_dir=base_dir)

    if selected_mode == BudgetStoreMode.FIRESTORE:
        client = firestore_client
        if client is None:
            try:
                from google.cloud import firestore
                client = firestore.Client()
            except Exception as exc:
                raise BudgetStoreError(
                    f"Firestore client initialization failed: {exc}. "
                    "Silent fallback to local disk is strictly prohibited."
                ) from exc
        return FirestoreBudgetStore(client=client)

    raise BudgetStoreError(f"Unhandled budget store mode: '{selected_mode}'")


BudgetStore = LocalBudgetStore

__all__ = [
    "BudgetStore",
    "BudgetStoreMode",
    "BudgetStoreProtocol",
    "resolve_budget_store_mode",
    "get_budget_store",
]

