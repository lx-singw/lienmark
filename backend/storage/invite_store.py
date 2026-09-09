import os
import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from backend.config.settings import settings
from backend.storage.firestore_client import get_firestore_client
from google.cloud import firestore

logger = logging.getLogger("lienmark.storage.invite")

class InviteStoreInterface(ABC):
    @abstractmethod
    def create_invite(self, hashed_token: str, role: str, tenant_id: str, production_id: str, max_uses: int = 1, expires_in: int = 86400) -> bool:
        pass

    @abstractmethod
    def consume_invite(self, hashed_token: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def revoke_session(self, session_id: str, expires_in: int = 86400) -> bool:
        pass

    @abstractmethod
    def is_session_revoked(self, session_id: str) -> bool:
        pass

class FirestoreInviteStore(InviteStoreInterface):
    def __init__(self):
        client = get_firestore_client()
        self.db = getattr(client, "db", client)

    def create_invite(self, hashed_token: str, role: str, tenant_id: str, production_id: str, max_uses: int = 1, expires_in: int = 86400) -> bool:
        try:
            doc_ref = self.db.collection("invites").document(hashed_token)
            doc_ref.set({
                "role": role,
                "tenant_id": tenant_id,
                "production_id": production_id,
                "max_uses": max_uses,
                "uses": 0,
                "expires_at": time.time() + expires_in
            })
            return True
        except Exception as e:
            logger.error(f"Error creating invite: {e}", exc_info=True)
            return False

    def consume_invite(self, hashed_token: str) -> Optional[Dict[str, Any]]:
        try:
            doc_ref = self.db.collection("invites").document(hashed_token)
            
            @firestore.transactional
            def consume_tx(transaction, ref):
                snapshot = ref.get(transaction=transaction)
                if not snapshot.exists:
                    return None
                data = snapshot.to_dict()
                if time.time() > data.get("expires_at", 0):
                    return None
                if data.get("uses", 0) >= data.get("max_uses", 1):
                    return None
                transaction.update(ref, {"uses": data["uses"] + 1})
                return data

            transaction = self.db.transaction()
            return consume_tx(transaction, doc_ref)
        except Exception as e:
            logger.error(f"Error consuming invite: {e}", exc_info=True)
            return None

    def revoke_session(self, session_id: str, expires_in: int = 86400) -> bool:
        try:
            doc_ref = self.db.collection("revoked_sessions").document(session_id)
            doc_ref.set({
                "revoked_at": time.time(),
                "expires_at": time.time() + expires_in
            })
            return True
        except Exception as e:
            logger.error(f"Error revoking session: {e}", exc_info=True)
            return False

    def is_session_revoked(self, session_id: str) -> bool:
        try:
            doc_ref = self.db.collection("revoked_sessions").document(session_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False
            if time.time() > doc.to_dict().get("expires_at", 0):
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking session revocation: {e}", exc_info=True)
            return False

class LocalInviteStore(InviteStoreInterface):
    def __init__(self, path: str = ".data"):
        self.path = path
        os.makedirs(self.path, exist_ok=True)
        self.invites_file = os.path.join(self.path, "invites.json")
        self.revoked_file = os.path.join(self.path, "revoked.json")
        if not os.path.exists(self.invites_file):
            with open(self.invites_file, "w") as f:
                json.dump({}, f)
        if not os.path.exists(self.revoked_file):
            with open(self.revoked_file, "w") as f:
                json.dump({}, f)

    def _read_json(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r") as f:
            return json.load(f)

    def _write_json(self, file_path: str, data: Dict[str, Any]) -> None:
        with open(file_path, "w") as f:
            json.dump(data, f)

    def create_invite(self, hashed_token: str, role: str, tenant_id: str, production_id: str, max_uses: int = 1, expires_in: int = 86400) -> bool:
        data = self._read_json(self.invites_file)
        data[hashed_token] = {
            "role": role,
            "tenant_id": tenant_id,
            "production_id": production_id,
            "max_uses": max_uses,
            "uses": 0,
            "expires_at": time.time() + expires_in
        }
        self._write_json(self.invites_file, data)
        return True

    def consume_invite(self, hashed_token: str) -> Optional[Dict[str, Any]]:
        # This is a naive lock-free implementation for local mock
        data = self._read_json(self.invites_file)
        if hashed_token not in data:
            return None
        invite = data[hashed_token]
        if time.time() > invite.get("expires_at", 0):
            return None
        if invite.get("uses", 0) >= invite.get("max_uses", 1):
            return None
        invite["uses"] += 1
        self._write_json(self.invites_file, data)
        return invite

    def revoke_session(self, session_id: str, expires_in: int = 86400) -> bool:
        data = self._read_json(self.revoked_file)
        data[session_id] = {
            "revoked_at": time.time(),
            "expires_at": time.time() + expires_in
        }
        self._write_json(self.revoked_file, data)
        return True

    def is_session_revoked(self, session_id: str) -> bool:
        data = self._read_json(self.revoked_file)
        if session_id not in data:
            return False
        revoked = data[session_id]
        if time.time() > revoked.get("expires_at", 0):
            return False
        return True

def get_invite_store() -> InviteStoreInterface:
    if os.getenv("USE_LOCAL_STORAGE", "").lower() == "true":
        return LocalInviteStore()
    if (
        os.getenv("K_SERVICE")
        or os.getenv("K_REVISION")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or getattr(settings, "is_production", False)
    ):
        return FirestoreInviteStore()
    return LocalInviteStore()
