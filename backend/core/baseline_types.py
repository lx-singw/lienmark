"""
backend/core/baseline_types.py

Domain models, enums, canonical deterministic digest calculation,
and typed exceptions for the Production Baseline Engine.
Authored strictly under Google AntiGravity architectural guidelines for Sprint 2.3.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

TENANT_ID_REGEX = re.compile(r"^org_[a-zA-Z0-9_\-]{1,64}$")
PROD_ID_REGEX = re.compile(r"^prod_[a-zA-Z0-9_\-]{1,64}$")
MAX_BASELINE_PAYLOAD_BYTES = 900 * 1024  # 900 KB guard before 1MB Firestore limit


class BaselineError(Exception):
    """Base exception for all baseline engine operations."""
    pass


class BaselineAlreadyExistsError(BaselineError):
    """Raised when attempting to overwrite an existing immutable baseline version."""
    pass


class BaselineNotFoundError(BaselineError):
    """Raised when a requested baseline version does not exist."""
    pass


class BaselineLineageBrokenError(BaselineError):
    """Raised when predecessor version pointer is missing, cyclic, or invalid."""
    pass


class BaselineIntegrityError(BaselineError):
    """Raised when baseline digest validation detects tampering or corruption."""
    pass


class BaselineTenantMismatchError(BaselineError):
    """Raised on invalid tenant identifier or cross-tenant boundary breach."""
    pass


class BaselinePayloadTooLargeError(BaselineError):
    """Raised when baseline snapshot payload exceeds storage quota limits."""
    pass


def validate_tenant_boundary(tenant_id: str, production_id: str) -> None:
    """Validates tenant_id and production_id format, failing closed on violations."""
    if not tenant_id or not isinstance(tenant_id, str):
        raise BaselineTenantMismatchError("tenant_id must be a non-empty string.")
    if not TENANT_ID_REGEX.match(tenant_id.strip()):
        raise BaselineTenantMismatchError(
            f"tenant_id '{tenant_id}' violates required pattern '^org_[a-zA-Z0-9_\\-]{{1,64}}$'."
        )
    if not production_id or not isinstance(production_id, str):
        raise BaselineTenantMismatchError("production_id must be a non-empty string.")
    if not PROD_ID_REGEX.match(production_id.strip()):
        raise BaselineTenantMismatchError(
            f"production_id '{production_id}' violates required pattern '^prod_[a-zA-Z0-9_\\-]{{1,64}}$'."
        )


class CreativeUseNode(BaseModel):
    """
    Immutable atomic rights claim or creative use extracted from a script cut.
    Represents an immutable clearance boundary node within a baseline snapshot.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(..., min_length=1, description="Unique claim instance ID")
    stable_lineage_key: str = Field(..., min_length=1, description="Cross-version lineage key")
    asset_type: str = Field(..., description="music, trademark, artwork, likeness, prop, dialogue")
    scene_or_timecode: str = Field(..., description="Scene number or media timecode, e.g. Scene 42")
    description: str = Field(..., description="Factual description of the creative use")
    prominence: str = Field(..., description="Duration or visual prominence level")
    context: str = Field(default="", description="Verbatim dialogue or action context")
    context_hash: str = Field(..., min_length=8, description="Truncated SHA-256 context hash")
    intended_scope: Dict[str, Any] = Field(default_factory=dict, description="Intended exploitation scope")
    licensed_scope: Dict[str, Any] = Field(default_factory=dict, description="Documented legal grants")
    source_span: Optional[Dict[str, int]] = Field(default=None, description="Screenplay line span")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Parser and bounding box metadata")


class ParserMetadata(BaseModel):
    """
    Immutable parser and extraction telemetry associated with baseline generation.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    parser_name: str = Field(..., description="Name of parser, e.g. gemini_screenplay_ast")
    parser_version: str = Field(..., description="Parser semantic version, e.g. 2.5.0")
    model_id: Optional[str] = Field(default=None, description="Model identifier, e.g. gemini-2.5-flash")
    document_id: Optional[str] = Field(default=None, description="Source DocumentRecord doc_id")
    document_filename: Optional[str] = Field(default=None, description="Source document file name")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token consumption metrics")
    execution_duration_ms: float = Field(default=0.0, ge=0.0, description="Extraction duration in ms")
    extracted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductionVersion(BaseModel):
    """
    Immutable production baseline revision snapshot.
    Strictly bound to tenant_id (organization_id) and production_id.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    version_id: str = Field(..., min_length=1, description="Revision ID, e.g. v1, v2, v7")
    production_id: str = Field(..., min_length=1, description="Bound production ID")
    tenant_id: str = Field(..., min_length=1, description="Owning tenant organization boundary")
    version_tag: str = Field(default="", description="Human-readable release tag, e.g. 'Picture Lock v1'")
    content_hash: str = Field(..., min_length=32, description="SHA-256 digest of source cut document")
    parser_metadata: ParserMetadata = Field(..., description="Extraction parser telemetry")
    claims: Tuple[CreativeUseNode, ...] = Field(default_factory=tuple, description="Immutable tuple of claims")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    creator: str = Field(default="system:intake", description="User or agent actor identity")
    previous_version_id: Optional[str] = Field(default=None, description="Lineage predecessor version ID")
    baseline_digest: str = Field(..., min_length=64, description="Deterministic SHA-256 baseline digest")

    @property
    def organization_id(self) -> str:
        return self.tenant_id

    @property
    def org_id(self) -> str:
        return self.tenant_id

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id_format(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not TENANT_ID_REGEX.match(v.strip()):
            raise ValueError(f"tenant_id '{v}' violates pattern '^org_[a-zA-Z0-9_\\-]{{1,64}}$'")
        return v.strip()

    @field_validator("production_id")
    @classmethod
    def validate_production_id_format(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not PROD_ID_REGEX.match(v.strip()):
            raise ValueError(f"production_id '{v}' violates pattern '^prod_[a-zA-Z0-9_\\-]{{1,64}}$'")
        return v.strip()


# Class alias for explicit semantic naming
ProductionVersionSnapshot = ProductionVersion
ClaimBaselineRecord = CreativeUseNode


def compute_baseline_digest(
    version_id: str,
    production_id: str,
    tenant_id: str,
    version_tag: str,
    content_hash: str,
    parser_metadata: Dict[str, Any] | ParserMetadata,
    claims: Sequence[Dict[str, Any] | CreativeUseNode],
    previous_version_id: Optional[str],
) -> str:
    """
    Computes a bit-for-bit deterministic SHA-256 digest of a production baseline.
    Claims are deterministically sorted by stable_lineage_key and claim_id.
    """
    meta_dict = (
        parser_metadata.model_dump()
        if hasattr(parser_metadata, "model_dump")
        else dict(parser_metadata)
    )
    normalized_claims: List[Dict[str, Any]] = []
    for c in claims:
        raw = c.model_dump() if hasattr(c, "model_dump") else dict(c)
        normalized_claims.append(raw)

    normalized_claims.sort(
        key=lambda x: (str(x.get("stable_lineage_key", "")), str(x.get("claim_id", "")))
    )

    canonical_repr = {
        "claims": normalized_claims,
        "content_hash": str(content_hash).strip(),
        "parser_metadata": meta_dict,
        "previous_version_id": previous_version_id,
        "production_id": str(production_id).strip(),
        "tenant_id": str(tenant_id).strip(),
        "version_id": str(version_id).strip(),
        "version_tag": str(version_tag).strip(),
    }
    serialized = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
