# backend/storage package
from backend.storage.repository import (
    TenantRepository,
    InMemoryTenantRepository,
    NativeFirestoreTenantRepository,
    get_tenant_repository,
    enforce_tenant_scope,
    RepositoryError,
    EntityNotFoundError,
    DuplicateEntityError,
    StaleRunCommitError,
    TenantSecurityViolation,
    TenantContextMissingError,
    TenantMismatchViolation,
    FailClosedSecurityViolation,
)
from backend.storage.firestore_client import (
    FirestoreClientInterface,
    InMemoryFirestoreClient,
    get_firestore_client,
)
from backend.storage.ledger import (
    AuditEvent,
    CryptographicLedger,
    LedgerTamperError,
    LedgerIntegrityError,
)
from backend.storage.locks import (
    DistributedLock,
    DistributedLockRecord,
    DistributedLockManager,
    get_distributed_lock_manager,
    LockAcquisitionError,
    LockExpiredError,
    LockReleaseError,
)
from backend.storage.document_store_types import (
    CrossTenantAccessViolation,
    DeduplicationError,
    DedupLookupResult,
    DocumentNotFoundError,
    IngestedDocumentRecord,
)
from backend.storage.document_store import DocumentStore

__all__ = [
    "TenantRepository",
    "InMemoryTenantRepository",
    "NativeFirestoreTenantRepository",
    "get_tenant_repository",
    "enforce_tenant_scope",
    "RepositoryError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "StaleRunCommitError",
    "TenantSecurityViolation",
    "TenantContextMissingError",
    "TenantMismatchViolation",
    "FailClosedSecurityViolation",
    "FirestoreClientInterface",
    "InMemoryFirestoreClient",
    "get_firestore_client",
    "AuditEvent",
    "CryptographicLedger",
    "LedgerTamperError",
    "LedgerIntegrityError",
    "DistributedLock",
    "DistributedLockRecord",
    "DistributedLockManager",
    "get_distributed_lock_manager",
    "LockAcquisitionError",
    "LockExpiredError",
    "LockReleaseError",
    "CrossTenantAccessViolation",
    "DeduplicationError",
    "DedupLookupResult",
    "DocumentNotFoundError",
    "IngestedDocumentRecord",
    "DocumentStore",
]

