"""
backend/agents/research/query_builder.py

Research query formulation, entity disambiguation, and inverse domain steering.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from backend.agents.research.query_types import (
    AssetClass,
    EntityDisambiguationError,
    EvidenceEvaluation,
    GeneratedQuery,
    InvalidSteeringTransitionError,
    SearchQueryRequest,
    SteeringState,
)

REGISTRY_DOMAINS: Dict[AssetClass, List[str]] = {
    AssetClass.MUSIC: ["site:ascap.com", "site:bmi.com", "site:cocatalog.loc.gov"],
    AssetClass.BRAND: ["site:tmsearch.uspto.gov", "site:uspto.report", "site:wipo.int"],
    AssetClass.FOOTAGE: ["site:images.nasa.gov", "site:archives.gov", "site:loc.gov"],
    AssetClass.ARTWORK: ["site:cocatalog.loc.gov", "site:loc.gov", "site:si.edu"],
    AssetClass.LIKENESS: ["site:cmgworldwide.com", "site:sagaftra.org", "site:archives.gov"],
}

NEGATIVE_OPERATORS: Dict[AssetClass, List[str]] = {
    AssetClass.MUSIC: [
        "-lyrics", "-chords", "-tabs", "-youtube", "-spotify", "-apple",
        "-soundcloud", "-cover", "-remix", "-karaoke", "-mp3",
    ],
    AssetClass.BRAND: [
        "-store", "-buy", "-coupon", "-shop", "-sale",
        "-price", "-discount", "-cart", "-checkout", "-deal",
    ],
    AssetClass.FOOTAGE: [
        "-wallpaper", "-stockphoto", "-shutterstock", "-gettyimages",
        "-pinterest", "-youtube", "-vimeo",
    ],
    AssetClass.ARTWORK: [
        "-posterprint", "-etsy", "-ebay", "-aliexpress", "-wallpaper", "-merch", "-tshirt",
    ],
    AssetClass.LIKENESS: [
        "-gossip", "-tabloid", "-dating", "-instagram", "-tiktok", "-twitter", "-fanart", "-scandal",
    ],
}

OWNERSHIP_KEYWORDS: Dict[AssetClass, List[str]] = {
    AssetClass.MUSIC: [
        '"catalog"', '"publishing"', '"master rights"', '"sync license"',
        '"administered by"', '"courtesy of"',
    ],
    AssetClass.BRAND: [
        '"trademark status"', '"assignment"', '"registration"', '"owner"',
        '"applicant"', '"serial number"',
    ],
    AssetClass.FOOTAGE: [
        '"public domain"', '"National Archives"', '"copyright status"',
        '"rights and restrictions"', '"courtesy of"',
    ],
    AssetClass.ARTWORK: [
        '"copyright renewal"', '"public domain"', '"Library of Congress"',
        '"catalog of copyright entries"',
    ],
    AssetClass.LIKENESS: [
        '"right of publicity"', '"estate of"', '"SAG-AFTRA"',
        '"licensing representative"', '"registered agent"',
    ],
}


class StructuredQueryBuilder:
    """Constructs deterministic, entity-anchored search queries across clearance tiers."""

    @staticmethod
    def build_disambiguation_key(
        asset_id: str,
        stable_lineage_key: Optional[str],
        creator_or_owner: Optional[str],
        title: str,
        year: Optional[int] = None,
    ) -> str:
        """Enforces entity disambiguation invariant by hashing identity tuple."""
        clean_title = (title or "").strip()
        clean_creator = (creator_or_owner or "").strip()
        if not clean_title or not clean_creator:
            raise EntityDisambiguationError(
                f"Entity disambiguation invariant violated: bare title '{title}' without "
                "creator/owner cannot be searched or cached."
            )
        lineage = (stable_lineage_key or asset_id or "").strip()
        payload = f"{asset_id}:{lineage}:{clean_creator.lower()}:{clean_title.lower()}:{year or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _sanitize(text: Optional[str]) -> str:
        """Normalizes whitespace and strips quotation marks to prevent query injection."""
        if not text:
            return ""
        return " ".join(text.replace('"', "").replace("'", "").strip().split())

    def build_query(self, req: SearchQueryRequest) -> GeneratedQuery:
        """Routes query building based on current steering state."""
        key = self.build_disambiguation_key(
            asset_id=req.asset_id,
            stable_lineage_key=req.stable_lineage_key,
            creator_or_owner=req.creator_or_owner,
            title=req.title,
            year=req.year,
        )
        if req.current_state == SteeringState.STRICT_REGISTRY:
            return self._build_strict_registry_query(req, key)
        if req.current_state == SteeringState.INVERSE_STEERING:
            return self._build_inverse_steered_query(req, key)
        if req.current_state == SteeringState.ADVERSARIAL_PROBE:
            return self._build_adversarial_query(req, key)
        return self._build_escalation_query(req, key)

    def _build_strict_registry_query(self, req: SearchQueryRequest, key: str) -> GeneratedQuery:
        """Tier 1: Constructs domain-scoped query targeting official statutory registries."""
        title_q = f'"{self._sanitize(req.title)}"'
        creator_q = f'"{self._sanitize(req.creator_or_owner)}"'
        year_str = f"{req.year}" if req.year else ""
        catalog_str = f'"{self._sanitize(req.catalog_or_reg_no)}"' if req.catalog_or_reg_no else ""
        domains = REGISTRY_DOMAINS.get(req.asset_class, [])
        domain_str = f"({' OR '.join(domains)})" if domains else ""
        parts = [p for p in [title_q, creator_q, year_str, catalog_str, domain_str] if p]
        return GeneratedQuery(
            query_string=" ".join(parts),
            state=SteeringState.STRICT_REGISTRY,
            asset_class=req.asset_class,
            disambiguation_key=key,
            registry_domains=domains,
        )

    def _build_inverse_steered_query(self, req: SearchQueryRequest, key: str) -> GeneratedQuery:
        """Tier 2: Strips site: constraints, injects negative operators and ownership terms."""
        title_q = f'"{self._sanitize(req.title)}"'
        creator_q = f'"{self._sanitize(req.creator_or_owner)}"'
        year_str = f"{req.year}" if req.year else ""
        negatives = NEGATIVE_OPERATORS.get(req.asset_class, [])
        neg_str = " ".join(negatives)
        keywords = OWNERSHIP_KEYWORDS.get(req.asset_class, [])
        keyword_str = f"({' OR '.join(keywords)})" if keywords else ""
        parts = [p for p in [title_q, creator_q, year_str, neg_str, keyword_str] if p]
        return GeneratedQuery(
            query_string=" ".join(parts),
            state=SteeringState.INVERSE_STEERING,
            asset_class=req.asset_class,
            disambiguation_key=key,
            negative_operators=negatives,
            ownership_keywords=keywords,
        )

    def _build_adversarial_query(self, req: SearchQueryRequest, key: str) -> GeneratedQuery:
        """Tier 3: Probes for disputes, litigation, adverse assignments, or competing claims."""
        title_q = f'"{self._sanitize(req.title)}"'
        creator_q = f'"{self._sanitize(req.creator_or_owner)}"'
        year_str = f"{req.year}" if req.year else ""
        conflict_str = '(dispute OR infringement OR lawsuit OR assignment OR "competing claim")'
        parts = [p for p in [title_q, creator_q, year_str, conflict_str] if p]
        return GeneratedQuery(
            query_string=" ".join(parts),
            state=SteeringState.ADVERSARIAL_PROBE,
            asset_class=req.asset_class,
            disambiguation_key=key,
        )

    def _build_escalation_query(self, req: SearchQueryRequest, key: str) -> GeneratedQuery:
        """Tier 4/5: Fallback envelope for deep multi-hop task or counsel review."""
        title_q = f'"{self._sanitize(req.title)}"'
        creator_q = f'"{self._sanitize(req.creator_or_owner)}"'
        return GeneratedQuery(
            query_string=f"{title_q} {creator_q} legal clearance ownership verification",
            state=req.current_state,
            asset_class=req.asset_class,
            disambiguation_key=key,
        )


class InverseDomainSteeringEngine:
    """Deterministic state machine governing query fallback and escalation transitions."""

    def __init__(self, builder: Optional[StructuredQueryBuilder] = None):
        self.builder = builder or StructuredQueryBuilder()

    @staticmethod
    def should_trigger_inverse_steering(eval_result: EvidenceEvaluation) -> bool:
        """Determines if registry results are empty or below confidence threshold."""
        if eval_result.error_status and eval_result.error_status >= 400:
            return True
        if eval_result.result_count == 0 or eval_result.confidence_score < 0.70:
            return True
        if eval_result.stance in ("insufficient", None):
            return True
        return False

    def transition_state(self, current: SteeringState, evaluation: EvidenceEvaluation) -> SteeringState:
        """Evaluates evidence to compute next deterministic steering state."""
        if current == SteeringState.STRICT_REGISTRY:
            if not self.should_trigger_inverse_steering(evaluation):
                return SteeringState.STRICT_REGISTRY
            return SteeringState.INVERSE_STEERING
        if current == SteeringState.INVERSE_STEERING:
            if evaluation.result_count > 0 and evaluation.confidence_score >= 0.70:
                return SteeringState.INVERSE_STEERING
            return SteeringState.ADVERSARIAL_PROBE
        if current == SteeringState.ADVERSARIAL_PROBE:
            return SteeringState.DEEP_TASK
        if current == SteeringState.DEEP_TASK:
            return SteeringState.EXHAUSTED
        raise InvalidSteeringTransitionError(f"Cannot transition from terminal state '{current}'")

    def next_query(
        self, req: SearchQueryRequest, evaluation: EvidenceEvaluation
    ) -> Tuple[SearchQueryRequest, GeneratedQuery]:
        """Advances state machine and synthesizes subsequent query attempt."""
        next_state = self.transition_state(req.current_state, evaluation)
        updated_req = req.model_copy(
            update={
                "current_state": next_state,
                "retry_count": req.retry_count + 1,
            }
        )
        query = self.builder.build_query(updated_req)
        return updated_req, query
