"""
evidence_item_mapper.py

Evidence Item Mapping and Domain Normalization Helpers.
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any, List, Optional

from backend.api.routes.evidence_schemas import EvidenceItem, EvidenceSourceType
from backend.domain.models import DocumentRecord


class EvidenceItemMapper:
    """Transforms domain claims and document records into standardized EvidenceItem models."""

    @staticmethod
    def extract_domain(url: Optional[str]) -> Optional[str]:
        """Extracts host domain from url defensively."""
        if not url:
            return None
        match = re.search(r"https?://([^/]+)", url)
        return match.group(1).lower() if match else None

    @classmethod
    def extract_claim_evidence(cls, claim: Any) -> List[EvidenceItem]:
        """Converts claim snapshot citations into EvidenceItems."""
        ev_list: List[EvidenceItem] = []
        c_dict = claim if isinstance(claim, dict) else claim.model_dump()
        snap = c_dict.get("evidence_snapshot")
        if not snap:
            return ev_list

        snap_dict = snap if isinstance(snap, dict) else snap.model_dump()
        excerpt = snap_dict.get("excerpt") or snap_dict.get("snippet") or ""
        digest = snap_dict.get("raw_payload_hash") or snap_dict.get("payload_hash") or hashlib.sha256(excerpt.encode()).hexdigest()
        src_url = snap_dict.get("source_url")
        claim_id = c_dict.get("claim_id") or c_dict.get("use_id", "claim_unknown")
        title = c_dict.get("title") or c_dict.get("name") or "Clearance Item"

        ev_list.append(EvidenceItem(
            evidence_id=f"ev_snap_{snap_dict.get('snapshot_id', 'unknown')}",
            source_type=EvidenceSourceType.PUBLIC_SEARCH,
            title=snap_dict.get("source_title") or f"Search Citation: {title}",
            source_url=src_url,
            domain=snap_dict.get("domain") or cls.extract_domain(src_url),
            snippet=excerpt,
            retrieved_at=snap_dict.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
            confidence_tier="primary_statutory" if "loc.gov" in (src_url or "") else "secondary_registry",
            stance=str(snap_dict.get("stance", "SUPPORTING")),
            asset_category=str(c_dict.get("category") or c_dict.get("asset_type") or "general"),
            payload_digest=digest,
            linked_claims=[claim_id],
            metadata=snap_dict.get("metadata", {}),
        ))
        return ev_list

    @classmethod
    def convert_document_to_evidence(cls, doc: DocumentRecord) -> EvidenceItem:
        """Converts a DocumentRecord contract into an EvidenceItem."""
        doc_id = getattr(doc, "doc_id", None) or getattr(doc, "document_id", "doc_unknown")
        filename = getattr(doc, "filename", None) or getattr(doc, "title", "Contract Document")
        doc_type = getattr(doc, "doc_type", "contract")
        ts = getattr(doc, "uploaded_at", None) or getattr(doc, "created_at", None) or datetime.now(timezone.utc).isoformat()
        content_hash = getattr(doc, "content_hash", "0" * 64)
        snippet = f"Contract agreement: {filename} ({doc_type})"
        return EvidenceItem(
            evidence_id=f"ev_doc_{doc_id}",
            source_type=EvidenceSourceType.PRIVATE_CONTRACT,
            title=filename,
            source_url=f"gs://contracts/{filename}",
            domain="contracts.internal",
            snippet=snippet,
            retrieved_at=ts,
            confidence_tier="private_legal",
            stance="SUPPORTING",
            asset_category=str(doc_type),
            payload_digest=content_hash,
            linked_claims=[],
            metadata={"filename": filename, "doc_type": doc_type},
        )
