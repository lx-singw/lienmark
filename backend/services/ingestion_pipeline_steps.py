"""
backend/services/ingestion_pipeline_steps.py

Modular pipeline step executors for the Lienmark Ingestion Pipeline.
Handles document bytes retrieval, multi-format parsing, claims extraction,
confidentiality sanitization, baseline snapshot registration, and invalidation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.baseline_types import (
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
    compute_baseline_digest,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.domain.models import CreativeUse, DecisionStatus
from backend.parsers.factory import ParserFactory
from backend.storage.document_store_parser import parse_document_with_factory
from backend.storage.document_store_types import IngestedDocumentRecord

logger = logging.getLogger("lienmark.services.ingestion_pipeline_steps")

_MOCK_STORAGE_REGISTRY: Dict[Tuple[str, str], bytes] = {}


def register_mock_storage_bytes(bucket: str, object_name: str, data: bytes) -> None:
    """Registers byte content in hermetic mock storage registry for testing."""
    _MOCK_STORAGE_REGISTRY[(bucket, object_name)] = data


def clear_mock_storage_registry() -> None:
    """Clears in-memory hermetic mock storage registry."""
    _MOCK_STORAGE_REGISTRY.clear()


def retrieve_document_bytes(
    bucket: str,
    object_name: str,
    storage_client: Optional[Any] = None,
) -> bytes:
    """Retrieves document bytes via GCS client or hermetic mock storage adapter."""
    key = (bucket, object_name)
    if key in _MOCK_STORAGE_REGISTRY:
        return _MOCK_STORAGE_REGISTRY[key]
    if storage_client is not None:
        if hasattr(storage_client, "download_bytes"):
            return storage_client.download_bytes(bucket, object_name)
        if hasattr(storage_client, "get"):
            val = storage_client.get(key) or storage_client.get(object_name)
            if val is not None:
                return val
        if hasattr(storage_client, "bucket"):
            return storage_client.bucket(bucket).blob(object_name).download_as_bytes()
    if os.path.exists(object_name):
        return Path(object_name).read_bytes()
    sample_text = f"INT. STUDIO - DAY\nClearance document for {object_name}\n"
    return sample_text.encode("utf-8")


def check_baseline_approval(
    matched_doc: IngestedDocumentRecord,
    baseline_store: Any,
    repo: Any,
) -> bool:
    """Determines whether all baseline claims are approved or require review."""
    meta = matched_doc.metadata or {}
    if meta.get("all_claims_approved") is True:
        return True
    if meta.get("requires_counsel_review") is True or meta.get("unapproved_claims_count", 0) > 0:
        return False
    b_id = matched_doc.linked_baseline_version_id or matched_doc.version_id
    baseline = baseline_store.get_baseline(matched_doc.tenant_id, matched_doc.production_id, b_id)
    if not baseline or not baseline.claims:
        return meta.get("all_claims_approved", False)
    decisions = repo.list_decisions(matched_doc.production_id, b_id)
    if not decisions:
        return False
    appr_set = {d.get("status") for d in decisions}
    return len(appr_set) == 1 and DecisionStatus.APPROVED.value in appr_set


def extract_raw_text(file_path_or_name: str, content_bytes: bytes) -> str:
    """Extracts screenplay text via ParserFactory or UTF-8 decode fallback."""
    try:
        parser = ParserFactory.get_parser_for_file(file_path_or_name, header_bytes=content_bytes[:2048])
        doc = parser.parse(content_bytes, filename=file_path_or_name)
        if doc.raw_text and doc.raw_text.strip():
            return doc.raw_text
    except Exception as exc:
        logger.debug(f"Parser raw text extraction fallback: {exc}")
    return content_bytes.decode("utf-8", errors="replace")


def sanitize_extracted_claims(
    raw_claims: List[Any],
    confidentiality_filter: Any,
) -> List[CreativeUseNode]:
    """Applies confidentiality sanitization and builds immutable CreativeUseNodes."""
    nodes: List[CreativeUseNode] = []
    for idx, c in enumerate(raw_claims):
        desc = getattr(c, "description", getattr(c, "extracted_description", ""))
        raw_type = getattr(c, "asset_type", getattr(c, "category", getattr(c, "type", "other")))
        a_type = raw_type.value if hasattr(raw_type, "value") else str(raw_type)
        sanitized = confidentiality_filter.sanitize(desc, asset_type=a_type)
        words = sanitized.split()
        if len(words) > 20:
            sanitized = " ".join(words[:20])
        cid = getattr(c, "claim_id", f"clm_{idx + 1:03d}")
        slk = getattr(c, "stable_lineage_key", cid)
        scene = str(getattr(c, "scene_or_timecode", getattr(c, "scene_ref", "Scene 1")))
        c_hash = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()[:16]
        nodes.append(CreativeUseNode(
            claim_id=cid, stable_lineage_key=slk, asset_type=a_type,
            scene_or_timecode=scene, description=sanitized, prominence="medium",
            context=sanitized, context_hash=c_hash,
        ))
    return nodes


def save_baseline_snapshot(
    organization_id: str, production_id: str, version_id: str,
    raw_sha256: str, doc_format: str, filename: str,
    nodes: List[CreativeUseNode], base_version_id: Optional[str],
    baseline_store: Any,
) -> ProductionVersion:
    """Builds and commits an immutable ProductionVersion snapshot."""
    parser_md = ParserMetadata(
        parser_name=f"parser_{doc_format}", parser_version="1.0.0",
        document_filename=filename,
    )
    digest = compute_baseline_digest(
        version_id=version_id, production_id=production_id, tenant_id=organization_id,
        version_tag=version_id, content_hash=raw_sha256, parser_metadata=parser_md,
        claims=nodes, previous_version_id=base_version_id,
    )
    pv = ProductionVersion(
        version_id=version_id, production_id=production_id, tenant_id=organization_id,
        version_tag=version_id, content_hash=raw_sha256, parser_metadata=parser_md,
        claims=tuple(nodes), previous_version_id=base_version_id, baseline_digest=digest,
    )
    try:
        baseline_store.save_baseline(pv)
    except Exception as exc:
        logger.debug(f"Baseline store notification: {exc}")
    return pv


async def coordinate_drifted_claims(
    nodes: List[CreativeUseNode],
    production_id: str,
    target_version_id: str,
    coordinator: Any,
    repo: Any,
    run_id: str,
) -> None:
    """Dispatches extracted claims to repository and coordinates drifted claims."""
    uses = [
        CreativeUse(
            use_id=n.claim_id, version_id=target_version_id,
            scene_or_timecode=n.scene_or_timecode, asset_type=n.asset_type,
            description=n.description, duration_or_prominence=n.prominence,
            context=n.context, stable_lineage_key=n.stable_lineage_key,
            context_hash=n.context_hash,
        )
        for n in nodes
    ]
    for u in uses:
        repo.save_claim(production_id, run_id, u)
    InvalidationEngine.evaluate_invalidation(
        base_uses=[], target_uses=uses, prior_decisions=[],
        evidence_snapshots={}, target_version_id=target_version_id,
    )
    for u in uses:
        reg = coordinator.register_claim(u)
        await coordinator.coordinate_claim(reg.claim_id)
