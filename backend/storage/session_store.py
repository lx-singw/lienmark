"""
backend/storage/session_store.py

Dedicated server-side session persistence.
Tracks session identity, expiry, and revocation in Firestore or Local memory.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import logging

from backend.config.settings import settings

logger = logging.getLogger("lienmark.storage.session")


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    email: str
    display_name: str
    role: str
    tenant_id: str
    production_id: str
    expires_at: float
    revoked: bool = False


class SessionStoreInterface(ABC):
    @abstractmethod
    def create_session(self, record: SessionRecord) -> bool:
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        pass

    @abstractmethod
    def revoke_session(self, session_id: str) -> bool:
        pass

    @abstractmethod
    def is_revoked(self, session_id: str) -> bool:
        pass


class LocalSessionStore(SessionStoreInterface):
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, record: SessionRecord) -> bool:
        self._sessions[record.session_id] = asdict(record)
        return True

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        data = self._sessions.get(session_id)
        if not data:
            return None
        if data.get("revoked", False) or time.time() > data.get("expires_at", 0):
            return None
        return SessionRecord(**data)

    def revoke_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id]["revoked"] = True
            return True
        return False

    def is_revoked(self, session_id: str) -> bool:
        data = self._sessions.get(session_id)
        if not data:
            return True
        return bool(data.get("revoked", False))


class FirestoreSessionStore(SessionStoreInterface):
    def __init__(self) -> None:
        from backend.storage.firestore_client import get_firestore_client
        client = get_firestore_client()
        self.db = getattr(client, "db", client)

    def create_session(self, record: SessionRecord) -> bool:
        try:
            doc_ref = self.db.collection("sessions").document(record.session_id)
            doc_ref.set(asdict(record))
            return True
        except Exception as exc:
            logger.error(f"Error creating session in Firestore: {exc}", exc_info=True)
            return False

    def get_session(self, session_id: str) -> Optional[SessionRecord]:
        try:
            doc_ref = self.db.collection("sessions").document(session_id)
            snapshot = doc_ref.get()
            if not snapshot.exists:
                return None
            data = snapshot.to_dict() or {}
            if data.get("revoked", False) or time.time() > data.get("expires_at", 0):
                return None
            return SessionRecord(**data)
        except Exception as exc:
            logger.error(f"Error getting session from Firestore: {exc}", exc_info=True)
            return None

    def revoke_session(self, session_id: str) -> bool:
        try:
            doc_ref = self.db.collection("sessions").document(session_id)
            doc_ref.update({"revoked": True})
            return True
        except Exception as exc:
            logger.error(f"Error revoking session in Firestore: {exc}", exc_info=True)
            return False

    def is_revoked(self, session_id: str) -> bool:
        try:
            doc_ref = self.db.collection("sessions").document(session_id)
            snapshot = doc_ref.get()
            if not snapshot.exists:
                return True
            data = snapshot.to_dict() or {}
            return bool(data.get("revoked", False))
        except Exception as exc:
            logger.error(f"Error checking session revocation in Firestore: {exc}", exc_info=True)
            return True


_GLOBAL_SESSION_STORE: Optional[SessionStoreInterface] = None


def get_session_store() -> SessionStoreInterface:
    global _GLOBAL_SESSION_STORE
    if _GLOBAL_SESSION_STORE is not None:
        return _GLOBAL_SESSION_STORE

    is_cloud_run = bool(
        os.getenv("K_SERVICE")
        or os.getenv("K_REVISION")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    use_local = os.getenv("USE_LOCAL_STORAGE", "").lower() in ("true", "1")

    if use_local and os.getenv('SESSION_SQLITE_PATH'):
        from .sqlite_session_store import SQLiteSessionStore
        _GLOBAL_SESSION_STORE = SQLiteSessionStore(os.environ['SESSION_SQLITE_PATH'])
        return _GLOBAL_SESSION_STORE

    if is_cloud_run and not use_local:
        try:
            _GLOBAL_SESSION_STORE = FirestoreSessionStore()
            return _GLOBAL_SESSION_STORE
        except Exception as exc:
            logger.warning("Firestore session init failed; falling back to local: %s", exc)

    _GLOBAL_SESSION_STORE = LocalSessionStore()
    return _GLOBAL_SESSION_STORE
