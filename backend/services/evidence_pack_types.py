"""
backend/services/evidence_pack_types.py

Domain models, manifest contracts, and verification result types for
cryptographically verifiable evidence packs.
Sprint 5.4: Verifiable Evidence Pack & Standalone Offline Verifier.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceCategory(str, Enum):
    """Categorization of artifacts bundled within an evidence pack."""

    SUMMARY = "summary"
    LEDGER = "ledger"
    POLICY = "policy"
    PACKAGE = "package"
    EVIDENCE = "evidence"


class EvidencePackFileEntry(BaseModel):
    """Metadata and cryptographic hash for an individual bundled file."""

    model_config = ConfigDict(extra="ignore")

    path: str = Field(..., description="Relative path within evidence pack archive")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    sha256: str = Field(..., min_length=64, max_length=64, description="SHA-256 hex digest")
    category: EvidenceCategory = Field(
        default=EvidenceCategory.EVIDENCE,
        description="Category of the bundled artifact",
    )


def compute_manifest_root_hash(files: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 root hash over sorted file manifest entries."""
    lines: List[str] = []
    for rel_path in sorted(files.keys()):
        entry = files[rel_path]
        digest = entry.sha256 if hasattr(entry, "sha256") else entry.get("sha256", "")
        lines.append(f"{rel_path}:{digest}")
    payload = "\n".join(lines) + ("\n" if lines else "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EvidencePackManifest(BaseModel):
    """Cryptographic manifest anchoring all bundled artifacts in an evidence pack."""

    model_config = ConfigDict(extra="ignore")

    manifest_version: str = Field(default="1.0.0", description="Manifest schema version")
    production_id: str = Field(..., description="Target production identifier")
    org_id: str = Field(..., description="Studio organization identifier")
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Generation timestamp in UTC",
    )
    generator: str = Field(
        default="Lienmark-EvidencePackBuilder/1.0",
        description="Software generator identity",
    )
    root_hash: str = Field(..., min_length=64, max_length=64, description="Root SHA-256 hash")
    file_count: int = Field(..., ge=0, description="Total number of tracked files")
    files: Dict[str, EvidencePackFileEntry] = Field(
        default_factory=dict,
        description="Map of relative file paths to their file entries",
    )


class VerificationCheckStatus(str, Enum):
    """Execution status for an offline verification check."""

    PASSED = "PASSED"
    FAILED = "FAILED"


class VerificationCheckResult(BaseModel):
    """Detailed outcome of a single verification gate."""

    model_config = ConfigDict(extra="ignore")

    check_name: str = Field(..., description="Unique check identifier")
    status: VerificationCheckStatus = Field(..., description="PASSED or FAILED")
    message: str = Field(..., description="Human-readable outcome description")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured telemetry or failure diagnostics",
    )


class VerificationReport(BaseModel):
    """Aggregated verification report produced by the offline verifier."""

    model_config = ConfigDict(extra="ignore")

    production_id: str = Field(..., description="Target production identifier")
    verified_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Verification execution timestamp",
    )
    is_valid: bool = Field(..., description="True if all verification gates passed")
    total_checks: int = Field(..., ge=0, description="Total verification gates executed")
    passed_checks: int = Field(..., ge=0, description="Count of passed verification gates")
    failed_checks: int = Field(..., ge=0, description="Count of failed verification gates")
    root_hash: str = Field(default="", description="Recomputed or verified manifest root hash")
    checks: List[VerificationCheckResult] = Field(
        default_factory=list,
        description="Individual check results",
    )
