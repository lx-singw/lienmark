"""
backend/storage/document_store.py

Multi-tenant document store and deduplication engine for Lienmark Milestone B.
Provides sub-100ms duplicate resolution, rename invariance, and strict tenant isolation.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any, List, Optional, Tuple, Union

from backend.services.hasher import StreamingHasher, normalize_and_hash_text
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
    extract_semantic_hash,
    validate_scope_parameters,
)
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DedupLookupResult,
    DocumentNotFoundError,
    DocumentProcessingStatus,
    IngestedDocumentRecord,
)

logger = logging.getLogger("lienmark.storage.document_store")


class DocumentStore:
    """Multi-tenant document repository with Firestore and memory tiers."""

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
        self, tenant_id: str, content_hash: str, semantic_hash: Optional[str] = None
    ) -> Optional[IngestedDocumentRecord]:
        """Looks up document by hash. Hit valid ONLY if COMMITTED and linked baseline is set."""
        t_id, c_hash, s_hash = clean_lookup_parameters(tenant_id, content_hash, semantic_hash)

        cached = self._memory.get_by_hash(t_id, c_hash, s_hash)
        if cached is not None:
            if cached.tenant_id != t_id:
                raise CrossTenantAccessViolation(f"Tenant boundary violation: {cached.tenant_id} != {t_id}")
            if cached.processing_status == DocumentProcessingStatus.COMMITTED and cached.linked_baseline_version_id:
                return cached
            return None

        rec_fs = lookup_document_by_hash_from_firestore(self._firestore_client, t_id, c_hash, s_hash)
        if rec_fs is not None:
            if rec_fs.tenant_id != t_id:
                raise CrossTenantAccessViolation(f"Tenant boundary violation: {rec_fs.tenant_id} != {t_id}")
            self._memory.put(rec_fs)
            if rec_fs.processing_status == DocumentProcessingStatus.COMMITTED and rec_fs.linked_baseline_version_id:
                return rec_fs
        return None

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

    def _find_resumable(
        self, tenant_id: str, raw_hash: str, sem_hash: Optional[str]
    ) -> Optional[IngestedDocumentRecord]:
        """Finds existing pending or failed record in tenant partition."""
        rec = self._memory.get_by_hash(tenant_id, raw_hash, sem_hash)
        if rec and rec.tenant_id == tenant_id:
            if rec.processing_status in (DocumentProcessingStatus.PENDING, DocumentProcessingStatus.FAILED):
                return rec
        return None

    def lookup_or_register(
        self,
        tenant_id: str,
        production_id: str,
        file_path_or_name: str,
        content_bytes: bytes,
        version_id: str = "v1",
        claims_count: int = 12,
        auto_commit: bool = False,
    ) -> Tuple[IngestedDocumentRecord, DedupLookupResult]:
        """Resolves duplicate committed documents or registers/resumes document."""
        start_time = time.perf_counter()
        t_id = validate_scope_parameters(tenant_id, production_id, content_bytes)
        filename = os.path.basename(file_path_or_name) or file_path_or_name

        digest_res = self._hasher.digest_bytes(content_bytes, compute_semantic=True)
        raw_hash = digest_res.raw_sha256
        sem_hash = digest_res.semantic_sha256 or extract_semantic_hash(content_bytes, filename)

        matched = self.lookup_by_hash(t_id, raw_hash, sem_hash)
        if matched is not None:
            return build_duplicate_hit_result(
                matched, t_id, production_id, filename, start_time,
                raw_hash, claims_count, self._ledger
            )

        resumable = self._find_resumable(t_id, raw_hash, sem_hash)
        if resumable is not None:
            st = DocumentProcessingStatus.COMMITTED if auto_commit else DocumentProcessingStatus.PENDING
            lb = version_id if auto_commit else None
            resumed = resumable.model_copy(update={"processing_status": st, "linked_baseline_version_id": lb})
            self.register_document(resumed)
            return resumed, build_new_document_result(start_time)

        return self._create_and_register_new(
            t_id, production_id, file_path_or_name, filename, content_bytes,
            raw_hash, sem_hash, version_id, claims_count, start_time, auto_commit
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
        auto_commit: bool = False,
    ) -> Tuple[IngestedDocumentRecord, DedupLookupResult]:
        """Parses document, persists record as PENDING initially, and returns telemetry."""
        doc_format, page_cnt, scene_cnt, meta = parse_document_with_factory(
            file_path_or_name, content_bytes
        )
        if sem_hash is None and "raw_text" in meta:
            sem_hash = normalize_and_hash_text(meta["raw_text"])

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
            processing_status=DocumentProcessingStatus.COMMITTED if auto_commit else DocumentProcessingStatus.PENDING,
            linked_baseline_version_id=version_id if auto_commit else None,
            metadata=meta,
        )
        return self.register_document(new_doc), build_new_document_result(start_time)

    def commit_document_baseline(
        self,
        tenant_id: Union[str, IngestedDocumentRecord],
        document_id: Optional[str] = None,
        baseline_version_id: Optional[str] = None,
    ) -> IngestedDocumentRecord:
        """Updates document status to COMMITTED and links baseline version ID."""
        if hasattr(tenant_id, "document_id"):
            doc = tenant_id
            committed = doc.model_copy(
                update={
                    "processing_status": DocumentProcessingStatus.COMMITTED,
                    "linked_baseline_version_id": doc.linked_baseline_version_id or doc.version_id or "v1",
                }
            )
            return self.register_document(committed)
        t_id = tenant_id.strip() if isinstance(tenant_id, str) else ""
        d_id = document_id.strip() if isinstance(document_id, str) else ""
        b_id = baseline_version_id.strip() if isinstance(baseline_version_id, str) else ""
        if not (t_id and d_id and b_id):
            raise DeduplicationError("tenant_id, document_id, and baseline_version_id must be non-empty")
        doc = self.get_document(t_id, d_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document '{d_id}' not found for tenant '{t_id}'")
        if doc.tenant_id != t_id:
            raise CrossTenantAccessViolation(f"Cross-tenant leak: {doc.tenant_id} != {t_id}")
        committed = doc.model_copy(
            update={
                "processing_status": DocumentProcessingStatus.COMMITTED,
                "linked_baseline_version_id": b_id,
            }
        )
        return self.register_document(committed)

    def mark_document_failed(self, tenant_id: str, document_id: str, error_reason: str) -> None:
        """Marks document status as FAILED and records error reason in metadata."""
        t_id, d_id = tenant_id.strip(), document_id.strip()
        if not (t_id and d_id): raise DeduplicationError("tenant_id and document_id must be non-empty")
        doc = self.get_document(t_id, d_id)
        if doc is None: raise DocumentNotFoundError(f"Document '{d_id}' not found for tenant '{t_id}'")
        if doc.tenant_id != t_id: raise CrossTenantAccessViolation(f"Cross-tenant leak: {doc.tenant_id} != {t_id}")
        self.register_document(doc.model_copy(update={
            "processing_status": DocumentProcessingStatus.FAILED,
            "metadata": {**doc.metadata, "error_reason": error_reason},
        }))

    def get_document(self, tenant_id: str, document_id: str) -> Optional[IngestedDocumentRecord]:
        """Retrieves a document record by ID strictly within tenant scope."""
        t_id = tenant_id.strip()
        doc = self._memory.get(t_id, document_id)
        if doc is not None: return doc
        rec_fs = get_document_from_firestore(self._firestore_client, t_id, document_id)
        if rec_fs is not None: self._memory.put(rec_fs)
        return rec_fs

    def list_documents(
        self, tenant_id: str, production_id: Optional[str] = None
    ) -> List[IngestedDocumentRecord]:
        """Lists all document records belonging exclusively to the tenant."""
        return self._memory.list(tenant_id.strip(), production_id)

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clears in-memory storage for a specific tenant or all tenants."""
        self._memory.clear(tenant_id.strip() if tenant_id else None)
