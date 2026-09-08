import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Any
from google.cloud import firestore
from backend.domain.revision_models import (
    RevisionRecord,
    RevisionAuditDispatch,
    ResultSnapshot,
)

class RevisionStoreError(Exception):
    pass

class RevisionConflictError(RevisionStoreError):
    pass

class RevisionNotFoundError(RevisionStoreError):
    pass

class RevisionStoreInterface(ABC):
    @abstractmethod
    def save_revision_and_dispatch(
        self, record: RevisionRecord, dispatch: RevisionAuditDispatch
    ) -> RevisionAuditDispatch:
        pass
    
    @abstractmethod
    def get_dispatch_by_idempotency_key(
        self, tenant_id: str, production_id: str, idempotency_key: str
    ) -> Optional[RevisionAuditDispatch]:
        pass

    @abstractmethod
    def save_result_snapshot(
        self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot
    ) -> None:
        pass

class FirestoreRevisionStore(RevisionStoreInterface):
    def __init__(self) -> None:
        self.db = firestore.Client()
    
    def _get_dispatch_ref(self, tenant_id: str, production_id: str, idempotency_key: str) -> firestore.DocumentReference:
        return self.db.collection("tenants").document(tenant_id)\
            .collection("productions").document(production_id)\
            .collection("idempotency_keys").document(idempotency_key)
    
    def get_dispatch_by_idempotency_key(
        self, tenant_id: str, production_id: str, idempotency_key: str
    ) -> Optional[RevisionAuditDispatch]:
        doc_ref = self._get_dispatch_ref(tenant_id, production_id, idempotency_key)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data is None:
            return None
        return RevisionAuditDispatch(**data)

    def save_revision_and_dispatch(
        self, record: RevisionRecord, dispatch: RevisionAuditDispatch
    ) -> RevisionAuditDispatch:
        transaction = self.db.transaction()
        record_ref = self.db.collection("tenants").document(record.tenant_id)\
            .collection("productions").document(record.production_id)\
            .collection("revisions").document(record.revision_id)
        dispatch_ref = self._get_dispatch_ref(record.tenant_id, record.production_id, dispatch.idempotency_key)
        return self._run_transaction(transaction, record_ref, dispatch_ref, record, dispatch)

    @firestore.transactional
    def _run_transaction(
        self,
        transaction: firestore.Transaction,
        record_ref: firestore.DocumentReference,
        dispatch_ref: firestore.DocumentReference,
        record: RevisionRecord,
        dispatch: RevisionAuditDispatch
    ) -> RevisionAuditDispatch:
        doc = dispatch_ref.get(transaction=transaction)
        if doc.exists:
            data = doc.to_dict()
            if data is not None and data.get("payload_hash") != dispatch.payload_hash:
                raise RevisionConflictError(f"Idempotency key {dispatch.idempotency_key} used with different payload")
            if data is not None:
                return RevisionAuditDispatch(**data)

        # Use model_dump if Pydantic V2, else dict
        record_dict = getattr(record, "model_dump", getattr(record, "dict", lambda: {}))()
        dispatch_dict = getattr(dispatch, "model_dump", getattr(dispatch, "dict", lambda: {}))()
        
        transaction.set(record_ref, record_dict)
        transaction.set(dispatch_ref, dispatch_dict)
        return dispatch

    def save_result_snapshot(
        self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot
    ) -> None:
        version_id = f"snapshot_{snapshot.version_number}"
        snapshot_ref = self.db.collection("tenants").document(tenant_id)\
            .collection("productions").document(production_id)\
            .collection("revisions").document(revision_id)\
            .collection("snapshots").document(version_id)
        
        transaction = self.db.transaction()
        self._commit_snapshot(transaction, snapshot_ref, snapshot)

    @firestore.transactional
    def _commit_snapshot(
        self, 
        transaction: firestore.Transaction, 
        snapshot_ref: firestore.DocumentReference, 
        snapshot: ResultSnapshot
    ) -> None:
        doc = snapshot_ref.get(transaction=transaction)
        if doc.exists:
            raise RevisionConflictError(f"Snapshot version {snapshot.version_number} already exists")
            
        snapshot_dict = getattr(snapshot, "model_dump", getattr(snapshot, "dict", lambda: {}))()
        transaction.set(snapshot_ref, snapshot_dict)


class LocalRevisionStore(RevisionStoreInterface):
    def __init__(self, base_path: str = ".local_storage") -> None:
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        
    def _get_path(self, tenant_id: str, production_id: str, path_type: str) -> str:
        p = os.path.join(self.base_path, tenant_id, production_id, path_type)
        os.makedirs(p, exist_ok=True)
        return p

    def get_dispatch_by_idempotency_key(
        self, tenant_id: str, production_id: str, idempotency_key: str
    ) -> Optional[RevisionAuditDispatch]:
        path = self._get_path(tenant_id, production_id, "idempotency_keys")
        file_path = os.path.join(path, f"{idempotency_key}.json")
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return RevisionAuditDispatch(**data)
        except Exception as e:
            raise RevisionStoreError(f"Failed to read dispatch: {str(e)}")

    def save_revision_and_dispatch(
        self, record: RevisionRecord, dispatch: RevisionAuditDispatch
    ) -> RevisionAuditDispatch:
        idem_path = self._get_path(record.tenant_id, record.production_id, "idempotency_keys")
        idem_file = os.path.join(idem_path, f"{dispatch.idempotency_key}.json")
        
        if os.path.exists(idem_file):
            try:
                with open(idem_file, "r") as f:
                    data = json.load(f)
                if data.get("payload_hash") != dispatch.payload_hash:
                    raise RevisionConflictError(f"Idempotency key {dispatch.idempotency_key} used with different payload")
                return RevisionAuditDispatch(**data)
            except RevisionConflictError:
                raise
            except Exception as e:
                raise RevisionStoreError(f"Failed to check existing dispatch: {str(e)}")

        rev_path = self._get_path(record.tenant_id, record.production_id, "revisions")
        rev_file = os.path.join(rev_path, f"{record.revision_id}.json")
        
        try:
            record_json = getattr(record, "model_dump_json", getattr(record, "json", lambda: "{}"))()
            dispatch_json = getattr(dispatch, "model_dump_json", getattr(dispatch, "json", lambda: "{}"))()
            
            with open(rev_file, "w") as f:
                f.write(record_json)
            with open(idem_file, "w") as f:
                f.write(dispatch_json)
            return dispatch
        except Exception as e:
            raise RevisionStoreError(f"Failed to save local records: {str(e)}")

    def save_result_snapshot(
        self, tenant_id: str, production_id: str, revision_id: str, snapshot: ResultSnapshot
    ) -> None:
        path = self._get_path(tenant_id, production_id, f"revisions/{revision_id}/snapshots")
        version_id = f"snapshot_{snapshot.version_number}.json"
        file_path = os.path.join(path, version_id)
        
        if os.path.exists(file_path):
            raise RevisionConflictError(f"Snapshot version {snapshot.version_number} already exists")
            
        try:
            snapshot_json = getattr(snapshot, "model_dump_json", getattr(snapshot, "json", lambda: "{}"))()
            with open(file_path, "w") as f:
                f.write(snapshot_json)
        except Exception as e:
            raise RevisionStoreError(f"Failed to save snapshot: {str(e)}")

def get_revision_store() -> RevisionStoreInterface:
    if os.environ.get("USE_LOCAL_STORAGE", "").lower() == "true":
        return LocalRevisionStore()
    return FirestoreRevisionStore()
