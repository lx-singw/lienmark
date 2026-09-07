"""
reflection_reconciler.py

Deterministic reconciliation and de-duplication engine for the Intake Agent.
Matches secondary reflection candidates against primary claims, de-duplicates
overlapping entities by scene and token similarity, and promotes newly unflagged elements.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional, Set, Tuple

from backend.agents.intake.reflection_schemas import (
    RawReflectionFinding,
    ReconciliationMetrics,
)
from backend.storage.schema import Claim

BOILERPLATE_WORDS: Set[str] = {
    "trademark", "clearance", "sync", "licensing", "status", "piece", "song",
    "by", "shown", "on-screen", "product", "packaging", "broadcast", "archival",
    "footage", "pack", "of", "item", "prop", "brand", "music", "video", "rights",
    "risk", "placement", "appears", "in", "the", "a", "an", "and", "or"
}


def normalize_scene_ref(scene_ref: str) -> str:
    """Normalizes screenplay scene references across formatting variations."""
    if not scene_ref:
        return "UNKNOWN_SCENE"
    cleaned = re.sub(r'^(?:p\.\s*\d+,\s*|page\s*\d+\s*[-:]\s*)', '', scene_ref, flags=re.IGNORECASE)
    return " ".join(cleaned.strip().upper().split())


def extract_entity_fingerprint(description: str, target_entity: Optional[str] = None) -> Set[str]:
    """Extracts distinctive entity tokens, stripping noise and clearance boilerplate."""
    combined = f"{target_entity or ''} {description}".lower()
    raw_tokens = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)?', combined)
    return {tok for tok in raw_tokens if tok not in BOILERPLATE_WORDS and len(tok) > 1}


def calculate_entity_similarity(tokens_a: Set[str], tokens_b: Set[str]) -> float:
    """Computes Jaccard similarity coefficient between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return float(intersection / union) if union > 0 else 0.0


def are_claims_equivalent(
    primary: Claim, finding: RawReflectionFinding, similarity_threshold: float = 0.40
) -> bool:
    """Determines whether a reflection candidate duplicates an existing primary claim."""
    norm_p_scene = normalize_scene_ref(primary.scene_ref)
    norm_r_scene = normalize_scene_ref(finding.scene_ref)

    if norm_p_scene != norm_r_scene and norm_p_scene not in norm_r_scene and norm_r_scene not in norm_p_scene:
        return False

    types_compatible = (
        primary.type == finding.type
        or primary.type == "other"
        or finding.type == "other"
    )
    if not types_compatible:
        return False

    p_tokens = extract_entity_fingerprint(primary.extracted_description)
    r_tokens = extract_entity_fingerprint(finding.extracted_description, finding.target_entity)

    # Fast-path for exact target entity substring match
    if finding.target_entity and finding.target_entity.lower() in primary.extracted_description.lower():
        return True

    return calculate_entity_similarity(p_tokens, r_tokens) >= similarity_threshold


def sanitize_confidential_description(description: str, max_words: int = 20) -> str:
    """Enforces confidential description trimming (max words, stripped narrative)."""
    words = description.strip().split()
    if len(words) <= max_words:
        return description.strip()
    return " ".join(words[:max_words])


def create_promoted_claim(production_id: str, finding: RawReflectionFinding) -> Claim:
    """Promotes an unflagged reflection candidate into a canonical Claim model."""
    norm_scene = normalize_scene_ref(finding.scene_ref)
    raw_key = f"{production_id}:{norm_scene}:{finding.target_entity.lower()}:{finding.type}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:8]
    claim_id = f"clm_refl_{digest}"

    desc = sanitize_confidential_description(finding.extracted_description, max_words=20)
    prominence = "background_prop" if finding.category_focus == "background_prop" else None

    return Claim(
        claim_id=claim_id,
        production_id=production_id,
        type=finding.type,
        scene_ref=finding.scene_ref,
        extracted_description=desc,
        needs_clarification=finding.needs_clarification,
        proposed_by_agent="intake_self_reflection",
        flagged_reason=finding.flagged_reason,
        performer_prominence="crowd_background" if prominence else None,
    )


def reconcile_claims(
    production_id: str,
    primary_claims: List[Claim],
    candidate_findings: List[RawReflectionFinding],
    similarity_threshold: float = 0.40,
) -> Tuple[List[Claim], ReconciliationMetrics]:
    """Reconciles primary claims with secondary reflection findings."""
    consolidated: List[Claim] = [c.model_copy(deep=True) for c in primary_claims]
    metrics = ReconciliationMetrics(
        primary_claim_count=len(primary_claims),
        reflection_claim_count=len(candidate_findings),
    )

    for finding in candidate_findings:
        if finding.flagged_reason == "suspicious_embedded_instruction":
            metrics.adversarial_trapped_count += 1

        matched_primary = next(
            (p for p in consolidated if are_claims_equivalent(p, finding, similarity_threshold)),
            None,
        )

        if matched_primary is not None:
            metrics.deduplicated_claim_count += 1
            if finding.category_focus == "background_prop" and not matched_primary.performer_prominence:
                matched_primary.performer_prominence = "crowd_background"
        else:
            new_claim = create_promoted_claim(production_id, finding)
            consolidated.append(new_claim)
            metrics.new_claims_discovered_count += 1

    return consolidated, metrics
