"""
tests/test_firestore_invite_delegation.py

Unit tests verifying NativeFirestoreClient collection/batch/transaction delegation
and FirestoreInviteStore / FirestoreSessionStore resilience against client wrapping.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from unittest.mock import MagicMock
from backend.storage.firestore_client import NativeFirestoreClient
from backend.storage.invite_store import FirestoreInviteStore
from backend.storage.session_store import FirestoreSessionStore, SessionRecord


def _create_mock_native_client():
    mock_db = MagicMock()
    # Construct NativeFirestoreClient without connecting to live GCP
    client = object.__new__(NativeFirestoreClient)
    client.db = mock_db
    return client, mock_db


def test_native_firestore_client_delegations():
    client, mock_db = _create_mock_native_client()

    client.collection("invites")
    mock_db.collection.assert_called_with("invites")

    client.collection_group("snapshots")
    mock_db.collection_group.assert_called_with("snapshots")

    client.document("path/to/doc")
    mock_db.document.assert_called_with("path/to/doc")

    client.batch()
    mock_db.batch.assert_called_with()

    client.transaction()
    mock_db.transaction.assert_called_with()


def test_firestore_invite_store_with_delegated_client(monkeypatch):
    client, mock_db = _create_mock_native_client()
    monkeypatch.setattr("backend.storage.invite_store.get_firestore_client", lambda: client)

    store = FirestoreInviteStore()
    assert store.db is mock_db  # Unwrapped correctly

    # Test create_invite
    mock_doc = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc
    success = store.create_invite("test_hash", "reviewer", "tenant_1", "prod_1")
    assert success is True
    mock_doc.set.assert_called_once()

    # Test consume_invite failure on missing doc
    mock_tx = MagicMock()
    mock_db.transaction.return_value = mock_tx
    mock_snapshot = MagicMock()
    mock_snapshot.exists = False
    mock_doc.get.return_value = mock_snapshot

    res = store.consume_invite("test_hash")
    assert res is None


def test_firestore_session_store_with_delegated_client(monkeypatch):
    client, mock_db = _create_mock_native_client()
    monkeypatch.setattr("backend.storage.firestore_client.get_firestore_client", lambda: client)

    store = FirestoreSessionStore()
    assert store.db is mock_db  # Unwrapped correctly

    mock_doc = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "session_id": "sess_123",
        "user_id": "usr_123",
        "email": "user@example.com",
        "display_name": "Test User",
        "role": "reviewer",
        "tenant_id": "tenant_1",
        "production_id": "prod_1",
        "expires_at": 9999999999.0,
        "revoked": False,
    }
    mock_doc.get.return_value = mock_snapshot

    session = store.get_session("sess_123")
    assert session is not None
    assert session.role == "reviewer"
    assert session.display_name == "Test User"
