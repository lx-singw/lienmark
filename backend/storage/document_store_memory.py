"""
backend/storage/document_store_memory.py

Thread-safe in-memory multi-tenant indexing and document partition storage.
Provides O(1) hash and semantic lookups strictly segregated by tenant boundary.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from backend.storage.document_store_types import IngestedDocumentRecord


class InMemoryDocumentIndex:
    """
    Thread-safe in-memory partition storing IngestedDocumentRecords and hash indexes.
    Segregates all entries strictly by tenant_id to guarantee zero cross-tenant leakage.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # tenant_id -> { document_id: IngestedDocumentRecord }
        self._documents: Dict[str, Dict[str, IngestedDocumentRecord]] = {}
        # tenant_id -> { raw_content_hash: document_id }
        self._hash_index: Dict[str, Dict[str, str]] = {}
        # tenant_id -> { semantic_hash: document_id }
        self._semantic_index: Dict[str, Dict[str, str]] = {}

    def get(self, tenant_id: str, document_id: str) -> Optional[IngestedDocumentRecord]:
        """Retrieves a document by ID strictly within tenant scope."""
        with self._lock:
            return self._documents.get(tenant_id, {}).get(document_id)

    def get_by_hash(
        self, tenant_id: str, content_hash: str, semantic_hash: Optional[str] = None
    ) -> Optional[IngestedDocumentRecord]:
        """Looks up a document in the tenant partition by raw or semantic hash."""
        with self._lock:
            tenant_docs = self._documents.get(tenant_id, {})
            # 1. Raw hash lookup
            doc_id = self._hash_index.get(tenant_id, {}).get(content_hash)
            if doc_id and doc_id in tenant_docs:
                rec = tenant_docs[doc_id]
                if rec.tenant_id == tenant_id:
                    return rec

            # 2. Semantic hash fallback lookup
            if semantic_hash:
                doc_id_sem = self._semantic_index.get(tenant_id, {}).get(semantic_hash)
                if doc_id_sem and doc_id_sem in tenant_docs:
                    rec_sem = tenant_docs[doc_id_sem]
                    if rec_sem.tenant_id == tenant_id:
                        return rec_sem
            return None

    def put(self, doc: IngestedDocumentRecord) -> None:
        """Stores a document record and indexes its raw and semantic hashes."""
        with self._lock:
            t_id = doc.tenant_id
            if t_id not in self._documents:
                self._documents[t_id] = {}
                self._hash_index[t_id] = {}
                self._semantic_index[t_id] = {}

            self._documents[t_id][doc.document_id] = doc
            self._hash_index[t_id][doc.content_hash] = doc.document_id
            if doc.semantic_hash:
                self._semantic_index[t_id][doc.semantic_hash] = doc.document_id

    def list(
        self, tenant_id: str, production_id: Optional[str] = None
    ) -> List[IngestedDocumentRecord]:
        """Returns all documents belonging to a tenant, optionally filtered by production."""
        with self._lock:
            docs = list(self._documents.get(tenant_id, {}).values())
            if production_id:
                docs = [d for d in docs if d.production_id == production_id]
            return docs

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clears records for a single tenant or all tenants."""
        with self._lock:
            if tenant_id:
                self._documents.pop(tenant_id, None)
                self._hash_index.pop(tenant_id, None)
                self._semantic_index.pop(tenant_id, None)
            else:
                self._documents.clear()
                self._hash_index.clear()
                self._semantic_index.clear()
