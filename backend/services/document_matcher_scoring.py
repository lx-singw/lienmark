"""
backend/services/document_matcher_scoring.py

Fuzzy text and metadata similarity scoring algorithms for legal document matching.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import difflib
import re
from typing import Optional, Tuple

from backend.domain.models import ClarificationRequest
from backend.services.document_matcher_types import (
    AgreementParties,
    DocumentArrivalEvent,
    ExtractedAgreementMetadata,
    MatchScoreBreakdown,
)

_STOPWORDS = {"the", "a", "an", "and", "or", "of", "in", "for", "to", "by", "scene"}


def compute_text_similarity(a: str, b: str) -> float:
    """Computes hybrid token-overlap and sequence ratio similarity between strings."""
    if not a or not b:
        return 0.0
    norm_a = re.sub(r"[^\w\s]", "", a.lower()).strip()
    norm_b = re.sub(r"[^\w\s]", "", b.lower()).strip()
    if not norm_a or not norm_b:
        return 0.0
    if norm_a == norm_b or norm_a in norm_b or norm_b in norm_a:
        return 0.96 if norm_a != norm_b else 1.0

    toks_a = set(norm_a.split())
    toks_b = set(norm_b.split())
    fa = toks_a - _STOPWORDS or toks_a
    fb = toks_b - _STOPWORDS or toks_b
    jaccard = len(fa & fb) / len(fa | fb) if (fa | fb) else 0.0
    seq = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    return round(0.6 * jaccard + 0.4 * seq, 4)


def compute_type_similarity(extracted_type: str, required_type: Optional[str]) -> float:
    """Computes legal compatibility between extracted and required agreement types."""
    if not required_type:
        return 0.85
    e_norm = extracted_type.lower()
    r_norm = required_type.lower()
    type_keywords = ("sync", "master", "trademark", "vara", "location", "talent")
    if any(k in e_norm and k in r_norm for k in type_keywords):
        return 1.0
    if "artist" in r_norm and "vara" in e_norm:
        return 0.95
    return 0.15


def compute_parties_similarity(parties: AgreementParties, clrf: ClarificationRequest) -> float:
    """Evaluates party alignment against question text and suggested options."""
    q_text = (clrf.question_text or "").lower()
    options_text = " ".join(clrf.suggested_options or []).lower()
    context = f"{q_text} {options_text}"

    lic_match = bool(parties.licensor and parties.licensor.lower() in context)
    lic_default = parties.licensor in ("Licensor Party", "Unknown Licensor", "")
    if lic_match:
        return 1.0
    if lic_default:
        return 0.85
    return 0.50


def evaluate_dual_key_match(
    metadata: ExtractedAgreementMetadata,
    clrf: ClarificationRequest,
    event: DocumentArrivalEvent,
) -> Tuple[bool, MatchScoreBreakdown]:
    """Validates Key 1 (tenant/prod isolation) and computes Key 2 fuzzy similarity."""
    zero_score = MatchScoreBreakdown(
        asset_score=0.0, parties_score=0.0, agreement_type_score=0.0, composite_score=0.0
    )
    if clrf.tenant_id != event.tenant_id:
        return False, zero_score

    if event.production_id and clrf.production_id and event.production_id != clrf.production_id:
        return False, zero_score

    targets = [clrf.question_text, clrf.claim_id, clrf.stable_lineage_key, clrf.scope_field_missing or ""]
    asset_score = max(compute_text_similarity(metadata.asset_title, tgt) for tgt in targets)
    type_score = compute_type_similarity(metadata.agreement_type, clrf.required_document_type)
    parties_score = compute_parties_similarity(metadata.parties, clrf)

    composite = round(0.50 * asset_score + 0.30 * type_score + 0.20 * parties_score, 4)
    breakdown = MatchScoreBreakdown(
        asset_score=asset_score,
        parties_score=parties_score,
        agreement_type_score=type_score,
        composite_score=composite,
    )
    return True, breakdown


def is_agreement_ambiguous(
    metadata: ExtractedAgreementMetadata,
    clrf: ClarificationRequest,
) -> Tuple[bool, Optional[str]]:
    """Detects whether agreement terms or extracted metadata contain legal ambiguities."""
    if metadata.extraction_confidence < 0.75:
        return True, f"Low extraction confidence ({metadata.extraction_confidence:.2f}) requires counsel review"

    ambiguous_terms = ("ambiguous", "tbd", "pending", "disputed", "unconfirmed", "negotiable", "subject to")
    combined = f"{metadata.asset_title} {metadata.agreement_type} {metadata.parties.licensor} {metadata.grant_term or ''}".lower()
    for kw in ambiguous_terms:
        if kw in combined:
            return True, f"Ambiguous term '{kw}' detected in agreement metadata"

    if metadata.grant_territory:
        t_low = [t.lower() for t in metadata.grant_territory]
        if any("worldwide" in t for t in t_low) and any("excluding" in t or "except" in t for t in t_low):
            return True, "Territory scope has conflicting worldwide grant with exclusions"

    lic = metadata.parties.licensor.strip().lower()
    if lic in ("unknown", "unknown licensor", "tbd", ""):
        return True, "Unidentified or placeholder licensor requires counsel clarification"

    return False, None


def verify_agreement_sufficiency(
    metadata: ExtractedAgreementMetadata,
    clrf: ClarificationRequest,
    event: DocumentArrivalEvent,
    breakdown: MatchScoreBreakdown,
) -> Tuple[bool, Optional[str]]:
    """
    Verifies agreement sufficiency across tenant, production, asset identity,
    requested document type, and relevant license scope.
    """
    if clrf.tenant_id != event.tenant_id:
        return False, f"Tenant mismatch: {clrf.tenant_id} != {event.tenant_id}"

    if event.production_id and clrf.production_id and event.production_id != clrf.production_id:
        return False, f"Production container mismatch: {clrf.production_id} != {event.production_id}"

    if breakdown.asset_score < 0.70:
        return False, f"Asset identity confidence ({breakdown.asset_score:.2f}) insufficient for auto-resolution"

    if breakdown.agreement_type_score < 0.70:
        return False, f"Document type '{metadata.agreement_type}' incompatible with required '{clrf.required_document_type}'"

    missing = (clrf.scope_field_missing or "").lower()
    if "territory" in missing and not metadata.grant_territory:
        return False, "Missing required territorial grant in agreement"
    if "media" in missing and not metadata.grant_media:
        return False, "Missing required media grant scope in agreement"
    if "term" in missing and not metadata.grant_term:
        return False, "Missing required license term duration in agreement"

    return True, None

