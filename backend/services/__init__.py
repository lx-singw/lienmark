from backend.services.parallel_service import ParallelSearchService
from backend.services.gemini_service import GeminiService, DeltaAnalysisResult, ClearanceBriefing, repair_json_output
from backend.services.revalidation_planner import (
    RevalidationPlanner,
    RevalidationPlan,
    PlannedRevalidationRequest,
    MinimalBudgetViolationError,
)

from backend.services.storage_watcher_types import (
    FolderScopeResult,
    IngestionStatus,
    StorageEvent,
    WatcherConfig,
    parse_and_validate_gcs_path,
)
from backend.services.storage_watcher import StorageWatcherService
from backend.services.ingestion_recovery import IngestionRecoveryService

from backend.services.hasher_types import (
    HashAlgorithm,
    HashDigestResult,
    StreamingHasherError,
    StreamReadError,
    FileAccessError,
    NormalizationError,
)
from backend.services.hasher import (
    StreamingHasher,
    normalize_screenplay_text,
    normalize_and_hash_text,
    compute_semantic_digest,
)

from backend.services.evidence_archiver_types import (
    CitationLivenessStatus,
    CitationRequest,
    EvidenceArchiverConfig,
    EvidenceArchiverError,
    EvidenceSnapshot,
    InvalidCitationUrlError,
    LivenessCheckError,
    LivenessVerificationResult,
    SnapshotHttpHeaders,
    SnapshotStorageError,
    compute_payload_digest,
    validate_url_ssrf,
    SSRFSecurityError,
    RegistrationExtractionError,
    CITATION_LIVE,
    CITATION_LIVE_RESTRICTED,
    CITATION_DEAD_404,
    CITATION_ERROR,
    CITATION_TIMEOUT,
)
from backend.services.snapshot_store import SnapshotStore
from backend.services.evidence_archiver import EvidenceArchiver
from backend.services.notifier_types import (
    NotificationEventType,
    DeliveryStatus,
    NotificationDeliveryRecord,
    NotificationDispatchResult,
)
from backend.services.notifier import (
    ClarificationNotifier,
    get_notifier,
    set_notifier,
)

__all__ = [
    "ClarificationNotifier",
    "get_notifier",
    "set_notifier",
    "NotificationEventType",
    "DeliveryStatus",
    "NotificationDeliveryRecord",
    "NotificationDispatchResult",
    "ParallelSearchService",
    "GeminiService",
    "DeltaAnalysisResult",
    "ClearanceBriefing",
    "repair_json_output",
    "RevalidationPlanner",
    "RevalidationPlan",
    "PlannedRevalidationRequest",
    "MinimalBudgetViolationError",
    "CounselCheckpointManager",
    "CounselCheckpointEngine",
    "CounselCheckpointService",
    "counsel_checkpoint_manager",
    "FolderScopeResult",
    "IngestionStatus",
    "StorageEvent",
    "WatcherConfig",
    "parse_and_validate_gcs_path",
    "StorageWatcherService",
    "IngestionRecoveryService",
    "HashAlgorithm",
    "HashDigestResult",
    "StreamingHasherError",
    "StreamReadError",
    "FileAccessError",
    "NormalizationError",
    "StreamingHasher",
    "normalize_screenplay_text",
    "normalize_and_hash_text",
    "compute_semantic_digest",
    "EvidenceArchiver",
    "SnapshotStore",
    "CitationLivenessStatus",
    "CitationRequest",
    "EvidenceArchiverConfig",
    "EvidenceArchiverError",
    "EvidenceSnapshot",
    "InvalidCitationUrlError",
    "LivenessCheckError",
    "LivenessVerificationResult",
    "SnapshotHttpHeaders",
    "SnapshotStorageError",
    "compute_payload_digest",
    "validate_url_ssrf",
    "SSRFSecurityError",
    "RegistrationExtractionError",
    "CITATION_LIVE",
    "CITATION_LIVE_RESTRICTED",
    "CITATION_DEAD_404",
    "CITATION_ERROR",
    "CITATION_TIMEOUT",
    "CircuitBreaker",
    "circuit_breaker",
    "get_circuit_breaker",
    "reset_all_circuit_breakers",
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerTelemetry",
    "CircuitBreakerError",
    "CircuitBreakerOpenError",
    "CircuitBreakerProbeError",
    "StateTransitionRecord",
    "is_qualifying_failure",
]

from backend.services.circuit_breaker_types import (
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerOpenError,
    CircuitBreakerProbeError,
    CircuitBreakerTelemetry,
    CircuitState,
    StateTransitionRecord,
    is_qualifying_failure,
)
from backend.services.circuit_breaker import (
    CircuitBreaker,
    circuit_breaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)

from backend.core.counsel_checkpoint import (
    CounselCheckpointManager,
    CounselCheckpointEngine,
    CounselCheckpointService,
    counsel_checkpoint_manager,
)

from backend.services.agreement_verifier_types import (
    TerritoryScope,
    MediaScope,
    TermScope,
    RightType,
    VerificationStatus,
    SignatureParty,
    ExecutionValidity,
    GrantScopeAnalysis,
    VerificationCitation,
    ProductionRequirements,
    AgreementDocumentInput,
    AgreementVerificationResult,
)
from backend.services.agreement_verifier import AgreementVerifier

from backend.services.document_matcher_types import (
    AgreementParties,
    AgreementType,
    DocumentArrivalEvent,
    ExtractedAgreementMetadata,
    MatchingDecision,
    MatchResult,
    MatchScoreBreakdown,
    parse_agreement_path,
)
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.document_matcher_scoring import (
    compute_parties_similarity,
    compute_text_similarity,
    compute_type_similarity,
    evaluate_dual_key_match,
)
from backend.services.document_matcher import DocumentMatcherService
from backend.services.citation_templates import (
    CitationCategory,
    LegalCitationTemplate,
    CitationSuggestionEngine,
)
from backend.services.evidence_pack_types import (
    EvidenceCategory,
    EvidencePackFileEntry,
    EvidencePackManifest,
    VerificationCheckStatus,
    VerificationCheckResult,
    VerificationReport,
    compute_manifest_root_hash,
)
from backend.services.evidence_pack_builder import build_evidence_pack

__all__.extend([
    "CitationCategory",
    "LegalCitationTemplate",
    "CitationSuggestionEngine",
    "EvidenceCategory",
    "EvidencePackFileEntry",
    "EvidencePackManifest",
    "VerificationCheckStatus",
    "VerificationCheckResult",
    "VerificationReport",
    "compute_manifest_root_hash",
    "build_evidence_pack",
])

