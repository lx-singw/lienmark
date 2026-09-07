"""
backend/storage/document_store.py

Multi-tenant document store and deduplication engine for Lienmark Sprint 2.2.
Provides sub-100ms duplicate resolution, rename invariance, and strict tenant isolation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, List, Optional, Tuple

from backend.services.hasher import StreamingHasher
from backend.storage.document_store_firestore import (
    get_document_from_firestore,
    lookup_document_by_hash_from_firestore,
    save_document_to_firestore,
)
from backend.storage.document_store_memory import InMemoryDocumentIndex
from backend.storage.document_store_parser import parse_document_with_factory
from backend.storage.document_store_telemetry import (
    build_duplicate_hit_result,
    build_new_document_result,
    clean_lookup_parameters,
    validate_scope_parameters,
)
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DedupLookupResult,
    IngestedDocumentRecord,
)

logger = logging.getLogger("lienmark.storage.document_store")


class DocumentStore:
    """
    Multi-tenant document repository supporting in-memory storage and Firestore collection
    `/organizations/{org_id}/documents/{doc_id}` with index on `(tenant_id, content_hash)`.
    
    Strictly enforces tenant boundaries on all lookups and writes. Cross-tenant matches
    are strictly forbidden!
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        ledger: Optional[Any] = None,
        firestore_client: Optional[Any] = None,
    ) -> None:
        self._repository = repository
        self._ledger = ledger
        self._firestore_client = firestore_client
        self._memory = InMemoryDocumentIndex()
        self._hasher = StreamingHasher()

    def attach_ledger(self, ledger: Any) -> None:
        """Attaches an audit ledger for recording deduplication cache hit events."""
        self._ledger = ledger

    def lookup_by_hash(
        self,
        tenant_id: str,
        content_hash: str,
        semantic_hash: Optional[str] = None,
    ) -> Optional[IngestedDocumentRecord]:
        """Looks up document by raw SHA-256 hash first, falling back to semantic hash."""
        t_id, c_hash, s_hash = clean_lookup_parameters(tenant_id, content_hash, semantic_hash)

        # 1. In-memory tenant partition lookup
        cached = self._memory.get_by_hash(t_id, c_hash, s_hash)
        if cached is not None:
            return cached

        # 2. Firestore fallback query if client configured
        rec_fs = lookup_document_by_hash_from_firestore(self._firestore_client, t_id, c_hash, s_hash)
        if rec_fs is not None:
            self._memory.put(rec_fs)
        return rec_fs

    def register_document(self, doc: IngestedDocumentRecord) -> IngestedDocumentRecord:
        """Saves document in tenant document partition and secondary hash indexes."""
        if not isinstance(doc, IngestedDocumentRecord):
            raise TypeError(f"Expected IngestedDocumentRecord, got {type(doc).__name__}")

        t_id = doc.tenant_id.strip()
        if not t_id:
            raise CrossTenantAccessViolation("Cannot register document with empty tenant_id.")

        self._memory.put(doc)
        save_document_to_firestore(self._firestore_client, doc)
        return doc

    def lookup_or_register(
        self,
        tenant_id: str,
        production_id: str,
        file_path_or_name: str,
        content_bytes: bytes,
        version_id: str = "v1",
        claims_count: int = 12,
    ) -> Tuple[IngestedDocumentRecord, DedupLookupResult]:
        """Resolves duplicates under 100ms or parses and stores a new document."""
        start_time = time.perf_counter()
        t_id = validate_scope_parameters(tenant_id, production_id, content_bytes)
        filename = os.path.basename(file_path_or_name) or file_path_or_name

        digest_res = self._hasher.digest_bytes(content_bytes, compute_semantic=True)
        raw_hash = digest_res.raw_sha256
        sem_hash = digest_res.semantic_sha256

        matched = self.lookup_by_hash(t_id, raw_hash, sem_hash)
        if matched is not None:
            return build_duplicate_hit_result(
                matched, t_id, production_id, filename, start_time,
                raw_hash, claims_count, self._ledger
            )

        return self._create_and_register_new(
            t_id, production_id, file_path_or_name, filename, content_bytes,
            raw_hash, sem_hash, version_id, claims_count, start_time
        )

    def _create_and_register_new(
        self,
        tenant_id: str,
        production_id: str,
        file_path_or_name: str,
        filename: str,
        content_bytes: bytes,
        raw_hash: str,
        sem_hash: Optional[str],
        version_id: str,
        claims_count: int,
        start_time: float,
    ) -> Tuple[IngestedDocumentRecord, DedupLookupResult]:
        """Parses multi-format document, persists record, and returns telemetry."""
        doc_format, page_cnt, scene_cnt, meta = parse_document_with_factory(
            file_path_or_name, content_bytes
        )
        new_doc = IngestedDocumentRecord(
            document_id=f"doc_{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            production_id=production_id,
            filename=filename,
            content_hash=raw_hash,
            semantic_hash=sem_hash,
            format=doc_format,
            page_count=page_cnt,
            scene_count=scene_cnt,
            version_id=version_id,
            claims_count=claims_count,
            metadata=meta,
        )
        stored_doc = self.register_document(new_doc)
        telemetry = build_new_document_result(start_time)
        return stored_doc, telemetry

    def get_document(self, tenant_id: str, document_id: str) -> Optional[IngestedDocumentRecord]:
        """Retrieves a document record by ID strictly within tenant scope."""
        t_id = tenant_id.strip()
        doc = self._memory.get(t_id, document_id)
        if doc is not None:
            return doc

        rec_fs = get_document_from_firestore(self._firestore_client, t_id, document_id)
        if rec_fs is not None:
            self._memory.put(rec_fs)
        return rec_fs

    def list_documents(
        self, tenant_id: str, production_id: Optional[str] = None
    ) -> List[IngestedDocumentRecord]:
        """Lists all document records belonging exclusively to the tenant."""
        return self._memory.list(tenant_id.strip(), production_id)

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clears in-memory storage for a specific tenant or all tenants (test fixture helper)."""
        self._memory.clear(tenant_id.strip() if tenant_id else None)
