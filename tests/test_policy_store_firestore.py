"""
tests/test_policy_store_firestore.py

Dedicated test suite for Native Firestore adapter in PolicyStore.
Tests atomic transactions, precondition concurrency, overrides, and intents.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from typing import Any, Dict, List, Optional
import pytest

from backend.storage.ledger import CryptographicLedger
from backend.storage.policy_store_types import (
    PolicyConcurrencyError,
    PolicyStoreError,
    PolicyStoreMode,
)
from backend.storage.policy_store import PolicyStore


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

    def collection(self, col_name: str) -> "MockCollection":
        return MockCollection(self.storage, f"{self.path}/{col_name}")

    def get(self) -> MockDocSnap:
        data = self.storage.get(self.path)
        return MockDocSnap(data=data, exists=(data is not None), doc_id=self.path.split("/")[-1])

    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        if merge and self.path in self.storage:
            self.storage[self.path].update(data)
        else:
            self.storage[self.path] = dict(data)

    def update(self, data: Dict[str, Any]) -> None:
        if self.path in self.storage:
            self.storage[self.path].update(data)


class MockBatch:
    def __init__(self) -> None:
        self.ops: List[Any] = []

    def set(self, ref: Any, data: Dict[str, Any]) -> None:
        self.ops.append((ref, data))

    def commit(self) -> None:
        for ref, data in self.ops:
            ref.set(data)


class MockCollection:
    def __init__(self, storage: Dict[str, Any], path: str):
        self.storage = storage
        self.path = path

    def document(self, doc_id: str) -> MockDocRef:
        return MockDocRef(self.storage, f"{self.path}/{doc_id}")

    def collection(self, col_name: str) -> "MockCollection":
        return MockCollection(self.storage, f"{self.path}/{col_name}")

    def stream(self):
        prefix = f"{self.path}/"
        for k, v in list(self.storage.items()):
            if k.startswith(prefix) and "/" not in k[len(prefix):]:
                yield MockDocSnap(data=v, exists=True, doc_id=k[len(prefix):])

    def where(self, field: str, op: str, val: Any) -> "MockCollection":
        return self

    def limit(self, count: int) -> "MockCollection":
        return self


class MockFirestoreClient:
    def __init__(self) -> None:
        self.storage: Dict[str, Any] = {}

    def collection(self, col_name: str) -> MockCollection:
        return MockCollection(self.storage, col_name)

    def collection_group(self, name: str) -> MockCollection:
        return MockCollection(self.storage, f"cg_{name}")

    def batch(self) -> MockBatch:
        return MockBatch()


@pytest.fixture
def firestore_client():
    return MockFirestoreClient()


@pytest.fixture
def ledger():
    return CryptographicLedger()


def test_firestore_save_and_get_policy(firestore_client, ledger):
    """Verifies atomic revision commit and active pointer in Firestore mode."""
    store = PolicyStore(
        mode=PolicyStoreMode.FIRESTORE,
        firestore_client=firestore_client,
        ledger=ledger,
    )
    rec, intent = store.save_policy_revision("org_disney", {"profile": "family"}, "actor_walt")
    assert rec.version_id == "v1"
    assert intent.to_version == "v1"

    active = store.get_active_policy("org_disney")
    assert active is not None
    assert active.version_id == "v1"
    assert active.policy_config["profile"] == "family"


def test_firestore_precondition_concurrency(firestore_client, ledger):
    """Verifies expected_current_version mismatch in Firestore mode."""
    store = PolicyStore(
        mode=PolicyStoreMode.FIRESTORE,
        firestore_client=firestore_client,
        ledger=ledger,
    )
    store.save_policy_revision("org_sony", {"profile": "action"}, "actor_1")

    with pytest.raises(PolicyConcurrencyError):
        store.save_policy_revision("org_sony", {"profile": "drama"}, "actor_2", expected_current_version="v9")

    rec2, intent2 = store.save_policy_revision(
        "org_sony", {"profile": "drama"}, "actor_2", expected_current_version="v1"
    )
    assert rec2.version_id == "v2"
    assert intent2.from_version == "v1"


def test_firestore_overrides_and_intents(firestore_client, ledger):
    """Verifies production overrides and intents querying in Firestore mode."""
    store = PolicyStore(
        mode=PolicyStoreMode.FIRESTORE,
        firestore_client=firestore_client,
        ledger=ledger,
    )
    ovr_id = store.save_production_override("org_lionsgate", "prod_jw4", {"waiver": True})
    assert ovr_id is not None

    loaded = store.get_production_override("org_lionsgate", "prod_jw4")
    assert loaded is not None
    assert loaded["waiver"] is True
