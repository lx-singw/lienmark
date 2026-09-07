"""
backend/agents/research/discovery_handler.py

Mid-run claim discovery coordinator and baseline promotion service.
Sprint 3.2: Mid-Run Claim Discovery & Secondary IP Detection.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Dict, List, Optional, Sequence

from backend.agents.intake.claim_types import ClaimCategory, ExtractedClaim
from backend.agents.research.discovery_heuristics import (
    RawCandidate,
    scan_text_for_candidates,
)
from backend.agents.research.discovery_types import (
    DiscoveryHandlerError,
    DiscoveryValidationError,
    ProposedClaimEvent,
    ProposedClaimNotFoundError,
    ProposedClaimStatus,
    SecondaryIPType,
)
from backend.agents.research.query_types import AssetClass
from backend.agents.research.result_sanitizer import sanitize_excerpt
from backend.core.baseline import ProductionBaselineEngine
from backend.core.baseline_types import (
    CreativeUseNode,
    ParserMetadata,
    ProductionVersion,
)
from backend.services.parallel_types import ParallelSearchFinding

logger = logging.getLogger("lienmark.research.discovery_handler")

ASSET_TO_CLAIM_CATEGORY: Dict[AssetClass, ClaimCategory] = {
    AssetClass.MUSIC: ClaimCategory.MUSIC,
    AssetClass.BRAND: ClaimCategory.BRAND,
    AssetClass.FOOTAGE: ClaimCategory.FOOTAGE,
    AssetClass.ARTWORK: ClaimCategory.ARTWORK,
    AssetClass.LIKENESS: ClaimCategory.REAL_PERSON,
}


class DiscoveryHandler:
    """
    Coordinates detection of secondary IP during research, validates candidates
    against intake schema invariants, and stages proposed claims for baseline promotion.
    """

    def __init__(self, baseline_engine: Optional[ProductionBaselineEngine] = None) -> None:
        self._baseline_engine = baseline_engine or ProductionBaselineEngine()
        self._lock = threading.RLock()
        self._staging_ledger: Dict[str, ProposedClaimEvent] = {}

    @property
    def baseline_engine(self) -> ProductionBaselineEngine:
        return self._baseline_engine

    def detect_secondary_ip(
        self, parent_claim: ExtractedClaim, findings: List[ParallelSearchFinding]
    ) -> List[ProposedClaimEvent]:
        """Scans findings for secondary IP, validates against Intake schema, and stages."""
        discovered_events: List[ProposedClaimEvent] = []
        seen_ids = set()

        for finding in findings:
            events = self._process_single_finding(parent_claim, finding)
            for ev in events:
                if ev.proposed_claim_id not in seen_ids:
                    seen_ids.add(ev.proposed_claim_id)
                    self.record_proposed_claim(ev)
                    discovered_events.append(ev)

        logger.info(
            "DiscoveryHandler detected %d secondary IP claims for parent '%s'",
            len(discovered_events), parent_claim.claim_id,
        )
        return discovered_events

    def _process_single_finding(
        self, parent_claim: ExtractedClaim, finding: ParallelSearchFinding
    ) -> List[ProposedClaimEvent]:
        raw_text = finding.full_excerpt or " ".join(finding.excerpts)
        safe_text = sanitize_excerpt(f"{finding.title} {raw_text}")
        candidates = scan_text_for_candidates(safe_text)
        events: List[ProposedClaimEvent] = []

        for cand in candidates:
            event = self._build_event(parent_claim, finding, cand)
            self.validate_as_extracted_claim(event)
            events.append(event)
        return events

    def _build_event(
        self, parent_claim: ExtractedClaim, finding: ParallelSearchFinding, cand: RawCandidate
    ) -> ProposedClaimEvent:
        norm_entity = cand.detected_entity.strip().lower()
        hash_src = f"{parent_claim.claim_id}:{cand.category.value}:{norm_entity}"
        prop_id = f"prop_{hashlib.sha256(hash_src.encode('utf-8')).hexdigest()[:12]}"
        meta = {
            "source_domain": finding.domain,
            "authority_tier": finding.authority_tier.value,
            "finding_title": finding.title,
        }
        return ProposedClaimEvent(
            proposed_claim_id=prop_id,
            parent_claim_id=parent_claim.claim_id,
            source_finding_id=finding.url or finding.domain or "unknown_finding",
            detected_entity=cand.detected_entity,
            category=cand.category,
            rationale=cand.rationale,
            confidence=round(min(1.0, cand.confidence * max(0.5, finding.authority_score + 0.4)), 2),
            scene_locator=parent_claim.scene_or_timecode,
            status=ProposedClaimStatus.PROPOSED,
            discovery_type=cand.discovery_type,
            metadata=meta,
        )

    def validate_as_extracted_claim(self, event: ProposedClaimEvent) -> ExtractedClaim:
        """Validates proposed claim against the canonical Intake ExtractedClaim schema."""
        category = ASSET_TO_CLAIM_CATEGORY.get(event.category, ClaimCategory.OTHER)
        desc = f"Discovered {event.category.value}: {event.detected_entity}"
        try:
            return ExtractedClaim(
                claim_id=event.proposed_claim_id,
                category=category,
                scene_or_timecode=event.scene_locator,
                extracted_description=desc,
                context_snippet=event.rationale,
                confidence=event.confidence,
                needs_clarification=True,
                flagged_reason=f"Mid-run secondary IP discovery: {event.rationale}",
            )
        except Exception as exc:
            raise DiscoveryValidationError(
                f"Proposed claim '{event.proposed_claim_id}' violates ExtractedClaim schema: {exc}"
            ) from exc

    def record_proposed_claim(self, event: ProposedClaimEvent) -> None:
        """Thread-safe staging of proposed claim without corrupting immutable baselines."""
        with self._lock:
            self._staging_ledger[event.proposed_claim_id] = event

    def get_proposed_claim(self, proposed_claim_id: str) -> Optional[ProposedClaimEvent]:
        with self._lock:
            return self._staging_ledger.get(proposed_claim_id)

    def list_proposed_claims(
        self, parent_claim_id: Optional[str] = None, status: Optional[ProposedClaimStatus] = None
    ) -> List[ProposedClaimEvent]:
        """Lists staged proposed claims filtered by parent claim or clearance status."""
        with self._lock:
            claims = list(self._staging_ledger.values())
        if parent_claim_id:
            claims = [c for c in claims if c.parent_claim_id == parent_claim_id]
        if status:
            claims = [c for c in claims if c.status == status]
        return claims

    def update_claim_status(
        self, proposed_claim_id: str, new_status: ProposedClaimStatus
    ) -> ProposedClaimEvent:
        """Updates lifecycle status of a staged proposed claim (e.g. accepted/dismissed)."""
        with self._lock:
            existing = self._staging_ledger.get(proposed_claim_id)
            if not existing:
                raise ProposedClaimNotFoundError(
                    f"Proposed claim '{proposed_claim_id}' not found in staging ledger."
                )
            updated = existing.model_copy(update={"status": new_status})
            self._staging_ledger[proposed_claim_id] = updated
            return updated

    def promote_accepted_claims_to_new_baseline(
        self,
        tenant_id: str,
        production_id: str,
        current_version_id: str,
        new_version_id: str,
        accepted_claim_ids: Sequence[str],
        version_tag: str = "Discovered Secondary IP Cut",
        creator: str = "agent:research:discovery",
    ) -> ProductionVersion:
        """Promotes accepted proposed claims to a new immutable baseline revision."""
        current_baseline = self._baseline_engine.get_baseline(
            tenant_id, production_id, current_version_id
        )
        new_nodes: List[CreativeUseNode] = []
        for claim_id in accepted_claim_ids:
            event = self.update_claim_status(claim_id, ProposedClaimStatus.ACCEPTED)
            node = self._create_creative_use_node(event)
            new_nodes.append(node)

        all_claims = list(current_baseline.claims) + new_nodes
        parser_meta = ParserMetadata(
            parser_name="lienmark_midrun_discovery",
            parser_version="3.2.0",
            model_id="discovery_heuristics_v1",
            execution_duration_ms=10.0,
        )
        return self._baseline_engine.register_baseline(
            tenant_id=tenant_id,
            production_id=production_id,
            version_id=new_version_id,
            content_hash=current_baseline.content_hash,
            parser_metadata=parser_meta,
            claims=all_claims,
            version_tag=version_tag,
            creator=creator,
            previous_version_id=current_version_id,
        )

    def _create_creative_use_node(self, event: ProposedClaimEvent) -> CreativeUseNode:
        return CreativeUseNode(
            claim_id=event.proposed_claim_id,
            stable_lineage_key=f"sec_{event.proposed_claim_id}",
            asset_type=event.category.value,
            scene_or_timecode=event.scene_locator,
            description=f"Discovered secondary IP: {event.detected_entity}",
            prominence="secondary_discovered",
            context=event.rationale,
            context_hash=hashlib.sha256(event.rationale.encode("utf-8")).hexdigest()[:16],
            confidence_score=event.confidence,
            metadata={
                "parent_claim_id": event.parent_claim_id,
                "source_finding_id": event.source_finding_id,
                "discovered_mid_run": True,
                **event.metadata,
            },
        )
