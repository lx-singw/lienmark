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
]
