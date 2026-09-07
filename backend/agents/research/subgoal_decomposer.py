"""
backend/agents/research/subgoal_decomposer.py

Investigation subgoal decomposition and evidence readiness assessment engine.
Sprint 3.2: Subgoal Decomposition & Evidence Readiness Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.subgoal_builders import (
    build_artwork_subgoals,
    build_brand_subgoals,
    build_footage_subgoals,
    build_generic_subgoals,
    build_music_subgoals,
)
from backend.agents.research.subgoal_rules import (
    AUTHORITY_WEIGHTS,
    IDENTIFIER_PATTERNS,
)
from backend.agents.research.subgoal_types import (
    InvestigationSubgoal,
    ReadinessStatus,
    SubgoalReadiness,
)
from backend.services.parallel_types import DomainAuthorityTier, ParallelSearchFinding

TIER_ORDER: List[DomainAuthorityTier] = [
    DomainAuthorityTier.TIER_1_GOVERNMENT,
    DomainAuthorityTier.TIER_2_RIGHTS_ORG,
    DomainAuthorityTier.TIER_3_NEWS_EDITORIAL,
    DomainAuthorityTier.TIER_4_GENERAL_WEB,
]


def _match_identifiers(
    subgoal: InvestigationSubgoal, evidence: List[ParallelSearchFinding]
) -> Tuple[Dict[str, str], List[str]]:
    """Scans evidence excerpts against target regex patterns for required identifiers."""
    matched: Dict[str, str] = {}
    unresolved: List[str] = []
    combined_corpus = " ".join(
        f"{f.title} {f.full_excerpt} {' '.join(f.excerpts)}" for f in evidence
    )

    for req_id in subgoal.required_identifiers:
        pattern = IDENTIFIER_PATTERNS.get(req_id)
        if pattern:
            match = pattern.search(combined_corpus)
            if match:
                matched[req_id] = match.group(0).strip()
            else:
                unresolved.append(req_id)
        elif any(req_id.lower() in f.full_excerpt.lower() for f in evidence):
            matched[req_id] = f"Corroborated in evidence for {req_id}"
        else:
            unresolved.append(req_id)

    return matched, unresolved


def _evaluate_domain_authority(
    evidence: List[ParallelSearchFinding],
) -> Tuple[DomainAuthorityTier, float, float]:
    """Extracts top domain authority tier, numeric weight, and max finding confidence."""
    if not evidence:
        return DomainAuthorityTier.TIER_4_GENERAL_WEB, 0.0, 0.0

    top_tier = DomainAuthorityTier.TIER_4_GENERAL_WEB
    for tier in TIER_ORDER:
        if any(f.authority_tier == tier for f in evidence):
            top_tier = tier
            break

    authority_weight = AUTHORITY_WEIGHTS.get(top_tier, 0.25)
    max_confidence = max(f.confidence_score for f in evidence)
    return top_tier, authority_weight, max_confidence


def _compute_readiness_score(
    subgoal: InvestigationSubgoal,
    matched_count: int,
    auth_weight: float,
    max_conf: float,
) -> float:
    """Calculates normalized readiness score based on authority, confidence, and matches."""
    total_req = len(subgoal.required_identifiers)
    if total_req == 0:
        raw = (0.60 * auth_weight) + (0.40 * max_conf)
    else:
        match_ratio = matched_count / total_req
        raw = (0.45 * auth_weight) + (0.25 * max_conf) + (0.30 * match_ratio)
    return round(min(max(raw, 0.0), 1.0), 3)


def _synthesize_gap_and_action(
    score: float,
    unresolved: List[str],
    top_tier: DomainAuthorityTier,
    evidence_count: int,
) -> Tuple[ReadinessStatus, List[str], str]:
    """Synthesizes readiness status, gap analysis, and clearance action recommendation."""
    gaps: List[str] = []
    if evidence_count == 0:
        gaps.append("Zero search findings retrieved for this investigation subgoal.")
        return ReadinessStatus.INSUFFICIENT, gaps, "DISPATCH_PARALLEL_SEARCH"

    if unresolved:
        gaps.append(f"Missing required identifier(s): {', '.join(unresolved)}")
    if top_tier in (DomainAuthorityTier.TIER_3_NEWS_EDITORIAL, DomainAuthorityTier.TIER_4_GENERAL_WEB):
        gaps.append("Evidence lacks Tier 1 government or Tier 2 rights organization registry backing.")

    if score >= 0.75 and not unresolved:
        return ReadinessStatus.READY, gaps, "PROCEED_TO_CLEARANCE"
    if score >= 0.50:
        return ReadinessStatus.PARTIAL, gaps, "EXPAND_REGISTRY_SEARCH"
    return ReadinessStatus.INSUFFICIENT, gaps, "ESCALATE_TO_COUNSEL"


def decompose_claim_to_subgoals(claim: ExtractedClaim) -> List[InvestigationSubgoal]:
    """Decomposes an extracted clearance claim into structured rights subgoals."""
    dispatch_map = {
        ClaimCategory.MUSIC: build_music_subgoals,
        ClaimCategory.BRAND: build_brand_subgoals,
        ClaimCategory.FOOTAGE: build_footage_subgoals,
        ClaimCategory.ARTWORK: build_artwork_subgoals,
    }
    builder = dispatch_map.get(claim.category, build_generic_subgoals)
    return builder(claim)


def assess_subgoal_readiness(
    subgoal: InvestigationSubgoal, evidence: List[ParallelSearchFinding]
) -> SubgoalReadiness:
    """Evaluates search evidence completeness and clearance readiness for an investigative subgoal."""
    matched, unresolved = _match_identifiers(subgoal, evidence)
    top_tier, auth_weight, max_conf = _evaluate_domain_authority(evidence)

    if not evidence:
        score = 0.0
    else:
        score = _compute_readiness_score(subgoal, len(matched), auth_weight, max_conf)

    status, gaps, action = _synthesize_gap_and_action(
        score, unresolved, top_tier, len(evidence)
    )
    urls = [f.url for f in evidence if f.url]

    return SubgoalReadiness(
        subgoal_id=subgoal.subgoal_id,
        claim_id=subgoal.claim_id,
        is_ready=(status == ReadinessStatus.READY),
        readiness_score=score,
        status=status,
        matched_identifiers=matched,
        unresolved_identifiers=unresolved,
        authority_level=top_tier,
        supporting_urls=urls,
        gap_analysis=gaps,
        recommended_action=action,
    )


class SubgoalDecomposer:
    """Orchestrator for claim subgoal decomposition and evidence readiness assessment."""

    def __init__(self, readiness_threshold: float = 0.75) -> None:
        self.readiness_threshold = readiness_threshold

    def decompose(self, claim: ExtractedClaim) -> List[InvestigationSubgoal]:
        """Instance method wrapper around decompose_claim_to_subgoals."""
        return decompose_claim_to_subgoals(claim)

    def assess_readiness(
        self, subgoal: InvestigationSubgoal, evidence: List[ParallelSearchFinding]
    ) -> SubgoalReadiness:
        """Instance method wrapper around assess_subgoal_readiness."""
        return assess_subgoal_readiness(subgoal, evidence)
