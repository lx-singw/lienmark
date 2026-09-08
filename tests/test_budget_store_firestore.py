"""
tests/test_budget_store_firestore.py

Tests for FirestoreBudgetStore:
Namespaced paths, atomic transactions, budget caps, recovery, and zero silent fallback.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from typing import Any, Dict, Optional
import pytest

from backend.orchestration.budget_store_firestore import FirestoreBudgetStore
from backend.orchestration.budget_store_types import (
    BudgetExceededError,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
)
from backend.orchestration.budget_store import (
    BudgetStoreMode,
    get_budget_store,
    resolve_budget_store_mode,
)


class MockDocSnap:
    def __init__(self, data: Optional[Dict[str, Any]] = None, exists: bool = True, doc_id: str = ""):
        self._data = data or {}
        self.exists = exists
        self.id = doc_id

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class MockDocRef:
    def __init__(self, storage: Dict[str, Any], path: str):
        self.storage = storage
        self.path = path

    def collection(self, name: str) -> "MockCollection":
        return MockCollection(self.storage, f"{self.path}/{name}")

    def get(self, transaction: Any = None) -> MockDocSnap:
        d = self.storage.get(self.path)
        return MockDocSnap(data=d, exists=(d is not None), doc_id=self.path.split("/")[-1])

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        if merge and self.path in self.storage:
            self.storage[self.path].update(data)
        else:
            self.storage[self.path] = dict(data)

    def update(self, data: Dict[str, Any]) -> None:
        if self.path in self.storage:
            self.storage[self.path].update(data)
        else:
            self.storage[self.path] = dict(data)


class MockCollection:
    def __init__(self, storage: Dict[str, Any], path: str):
        self.storage = storage
        self.path = path

    def document(self, doc_id: str) -> MockDocRef:
        return MockDocRef(self.storage, f"{self.path}/{doc_id}")

    def stream(self):
        prefix = f"{self.path}/"
        for k, v in list(self.storage.items()):
            if k.startswith(prefix) and "/" not in k[len(prefix):]:
                yield MockDocSnap(data=v, exists=True, doc_id=k[len(prefix):])


class MockTransaction:
    def __init__(self, client: Any):
        self.client = client
        self.writes = []

    def get(self, ref: Any) -> Any:
        return ref.get(transaction=self)

    def set(self, ref: Any, data: Dict[str, Any], merge: bool = False) -> None:
        self.writes.append((ref, "set", data, merge))

    def update(self, ref: Any, data: Dict[str, Any]) -> None:
        self.writes.append((ref, "update", data, False))

    def commit(self) -> None:
        for ref, op, data, merge in self.writes:
            if op == "set":
                ref.set(data, merge=merge)
            elif op == "update":
                ref.update(data)


class MockFirestoreClient:
    def __init__(self):
        self.storage: Dict[str, Any] = {}

    def collection(self, name: str) -> MockCollection:
        return MockCollection(self.storage, name)

    def transaction(self) -> MockTransaction:
        return MockTransaction(self)


@pytest.fixture
def mock_client():
    return MockFirestoreClient()


@pytest.fixture
def firestore_store(mock_client):
    return FirestoreBudgetStore(client=mock_client)


def test_firestore_reserve_and_settle(firestore_store):
    """Verifies atomic reservation and settlement through Firestore adapter."""
    firestore_store.set_budget_limit("org_hbo", "prod_succession", "period_s4", 100_000)
    res = firestore_store.reserve_budget(
        "org_hbo", "prod_succession", "period_s4", "run_roy", "act_gemini",
        "gemini-1.5-pro", "pro", 25_000,
    )
    assert res.reservation_id.startswith("res_")
    assert res.max_cost_micros == 25_000

    summary1 = firestore_store.get_summary("org_hbo", "prod_succession", "period_s4")
    assert summary1.outstanding_reservations_micros == 25_000
    assert summary1.settled_spend_micros == 0

    record = firestore_store.settle_reservation(
        res.reservation_id, actual_cost_micros=18_000, usage_measurements={"prompt_tokens": 1200},
    )
    assert record.actual_cost_micros == 18_000

    summary2 = firestore_store.get_summary("org_hbo", "prod_succession", "period_s4")
    assert summary2.outstanding_reservations_micros == 0
    assert summary2.settled_spend_micros == 18_000


def test_firestore_budget_exceeded(firestore_store):
    """Verifies that exceeding budget cap in Firestore transaction raises BudgetExceededError."""
    firestore_store.set_budget_limit("org_apple", "prod_severance", "period_lumon", 30_000)
    firestore_store.reserve_budget(
        "org_apple", "prod_severance", "period_lumon", "run_mdr", "act_1",
        "gemini", "pro", 20_000,
    )

    with pytest.raises(BudgetExceededError) as exc_info:
        firestore_store.reserve_budget(
            "org_apple", "prod_severance", "period_lumon", "run_mdr", "act_2",
            "gemini", "pro", 15_000,
        )
    assert exc_info.value.limit_micros == 30_000


def test_firestore_recover_and_list(firestore_store):
    """Verifies recovery of orphaned reservation and listing by status."""
    res = firestore_store.reserve_budget(
        "org_sony", "prod_lastofus", "period_tlou", "run_joel", "act_search",
        "parallel", "fast", 10_000,
    )
    firestore_store.recover_reservation(res.reservation_id, status=ReservationStatus.UNCERTAIN)

    summary = firestore_store.get_summary("org_sony", "prod_lastofus", "period_tlou")
    assert summary.outstanding_reservations_micros == 0

    uncertain = firestore_store.list_reservations("org_sony", "prod_lastofus", "period_tlou", status=ReservationStatus.UNCERTAIN)
    assert len(uncertain) == 1
    assert uncertain[0].status == ReservationStatus.UNCERTAIN


def test_firestore_zero_silent_fallback():
    """Verifies strict fail-closed policy: missing client never silently falls back to local disk."""
    with pytest.raises(BudgetStoreError) as exc_info:
        FirestoreBudgetStore(client=None)
    assert "Firestore client is required" in str(exc_info.value)


def test_factory_modes(mock_client, monkeypatch):
    """Verifies get_budget_store factory mode routing and fallback prevention."""
    store_local = get_budget_store(mode="local_disk")
    assert store_local.__class__.__name__ == "LocalBudgetStore"

    store_firestore = get_budget_store(mode="firestore", firestore_client=mock_client)
    assert store_firestore.__class__.__name__ == "FirestoreBudgetStore"

    # In Firestore mode, client failure must raise BudgetStoreError, NOT fall back to local disk
    def _fail_init(*args, **kwargs):
        raise RuntimeError("GCP credentials missing or unreachable")

    monkeypatch.setattr("google.cloud.firestore.Client", _fail_init)
    with pytest.raises(BudgetStoreError) as exc_info:
        get_budget_store(mode="firestore", firestore_client=None)
    assert "Silent fallback to local disk is strictly prohibited" in str(exc_info.value)

    with pytest.raises(BudgetStoreError):
        get_budget_store(mode="unsupported_quantum_mode")

    assert resolve_budget_store_mode("local") == BudgetStoreMode.LOCAL_DISK
    assert resolve_budget_store_mode("firestore") == BudgetStoreMode.FIRESTORE
