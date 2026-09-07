"""
backend/services/document_matcher.py

Autonomous document matcher integrating Storage Watcher events with ClarificationStore.
Enforces dual-key invariant matching, auto-resolution, and zero-click pipeline resumption.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from backend.domain.models import ClarificationRequest
from backend.orchestration.suspension import SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.document_matcher_scoring import (
    compute_parties_similarity,
    compute_text_similarity,
    compute_type_similarity,
    evaluate_dual_key_match,
)
from backend.services.document_matcher_types import (
    DocumentArrivalEvent,
    ExtractedAgreementMetadata,
    MatchingDecision,
    MatchResult,
    MatchScoreBreakdown,
    parse_agreement_path,
)
from backend.storage.clarification_store import ClarificationStore, get_clarification_store

logger = logging.getLogger("lienmark.services.document_matcher")

__all__ = [
    "DocumentMatcherService",
    "compute_text_similarity",
    "compute_type_similarity",
    "compute_parties_similarity",
    "evaluate_dual_key_match",
]


class DocumentMatcherService:
    """Autonomous Document Matcher orchestrating dual-key matching and pipeline resumption."""

    def __init__(
        self,
        parser: Optional[AgreementParser] = None,
        clarification_store: Optional[ClarificationStore] = None,
        suspension_manager: Optional[SuspensionManager] = None,
        resumption_coordinator: Optional[Any] = None,
        resumption_callback: Optional[Callable[[ClarificationRequest, ExtractedAgreementMetadata], Any]] = None,
    ) -> None:
        self.parser = parser or AgreementParser(use_fallback=True)
        self.store = clarification_store or get_clarification_store()
        self.suspension_manager = suspension_manager
        self.resumption_coordinator = resumption_coordinator
        self.resumption_callback = resumption_callback
        self._listeners: List[Callable[[MatchResult], None]] = []

    def register_listener(self, callback: Callable[[MatchResult], None]) -> None:
        """Subscribes a listener to document matching outcomes."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _resume_pipeline(self, clrf: ClarificationRequest, metadata: ExtractedAgreementMetadata) -> bool:
        """Triggers autonomous pipeline resumption with zero human button clicks."""
        resumed = False
        if self.resumption_callback:
            try:
                self.resumption_callback(clrf, metadata)
                resumed = True
            except Exception as exc:
                logger.error(f"Custom resumption callback failed: {exc}")

        if self.resumption_coordinator and not resumed:
            try:
                fn = getattr(self.resumption_coordinator, "resume_from_clarification", None)
                if callable(fn) and fn(clrf, metadata):
                    resumed = True
            except Exception as exc:
                logger.debug(f"ResumptionCoordinator attempt: {exc}")

        if self.suspension_manager:
            for cp in self.suspension_manager.checkpoints.values():
                if clrf.request_id in cp.pending_clarification_ids or cp.claim_id == clrf.claim_id:
                    try:
                        self.suspension_manager.resume_investigation(
                            checkpoint_id=cp.checkpoint_id,
                            resume_token=cp.resume_token,
                            current_revision_uses=[{"claim_id": clrf.claim_id}],
                        )
                        resumed = True
                    except Exception as exc:
                        logger.error(f"SuspensionManager resumption failed for {cp.checkpoint_id}: {exc}")
        return resumed

    def _resolve_match(
        self,
        clrf: ClarificationRequest,
        metadata: ExtractedAgreementMetadata,
        event: DocumentArrivalEvent,
        breakdown: MatchScoreBreakdown,
    ) -> MatchResult:
        """Auto-attaches agreement, transitions clarification to resolved, and resumes pipeline."""
        resp_text = f"Autonomous match verified: {metadata.agreement_type} for '{metadata.asset_title}'"
        self.store.resolve_clarification(
            request_id=clrf.request_id,
            tenant_id=event.tenant_id,
            actor_id="autonomous_document_matcher",
            responder_role="autonomous_matcher_service",
            response_text=resp_text,
            attached_document_id=metadata.document_id,
            resolution_channel="folder_arrival_autonomous",
        )
        resumed = self._resume_pipeline(clrf, metadata)
        return MatchResult(
            event_id=event.event_id,
            document_id=metadata.document_id,
            matched_request_id=clrf.request_id,
            matched_claim_id=clrf.claim_id,
            decision=MatchingDecision.AUTO_RESOLVE,
            confidence_score=breakdown.composite_score,
            score_breakdown=breakdown,
            dual_key_valid=True,
            pipeline_resumed=resumed,
            resolution_channel="folder_arrival_autonomous",
        )

    def _flag_candidate(
        self,
        clrf: ClarificationRequest,
        metadata: ExtractedAgreementMetadata,
        event: DocumentArrivalEvent,
        breakdown: MatchScoreBreakdown,
    ) -> MatchResult:
        """Flags clarification with candidate document requiring human confirmation in UI."""
        self.store.flag_candidate_document(
            request_id=clrf.request_id,
            tenant_id=event.tenant_id,
            candidate_document_ref=metadata.document_id,
            match_confidence=breakdown.composite_score,
        )
        return MatchResult(
            event_id=event.event_id,
            document_id=metadata.document_id,
            matched_request_id=clrf.request_id,
            matched_claim_id=clrf.claim_id,
            decision=MatchingDecision.CANDIDATE_DETECTED,
            confidence_score=breakdown.composite_score,
            score_breakdown=breakdown,
            dual_key_valid=True,
            pipeline_resumed=False,
        )

    def on_document_arrival(
        self,
        event: DocumentArrivalEvent,
        file_content: Optional[Union[str, bytes]] = None,
    ) -> MatchResult:
        """Matches newly arrived agreement against open ClarificationRequests in tenant boundary."""
        content = file_content or event.file_path
        metadata = self.parser.parse_agreement(content, file_path=event.file_path, file_hash=event.file_hash)
        open_clrfs = self.store.list_open_clarifications(event.tenant_id, event.production_id)
        if not open_clrfs:
            return MatchResult(
                event_id=event.event_id, document_id=metadata.document_id,
                decision=MatchingDecision.NO_MATCH, confidence_score=0.0, dual_key_valid=False,
            )

        best_score, best_clrf, best_bdown = -1.0, None, None
        for clrf in open_clrfs:
            valid, bdown = evaluate_dual_key_match(metadata, clrf, event)
            if valid and bdown.composite_score > best_score:
                best_score, best_clrf, best_bdown = bdown.composite_score, clrf, bdown

        if not best_clrf or best_score < 0.40 or not best_bdown:
            return MatchResult(
                event_id=event.event_id, document_id=metadata.document_id,
                decision=MatchingDecision.NO_MATCH, confidence_score=max(0.0, best_score), dual_key_valid=False,
            )

        if best_score > 0.85:
            result = self._resolve_match(best_clrf, metadata, event, best_bdown)
        else:
            result = self._flag_candidate(best_clrf, metadata, event, best_bdown)

        for listener in self._listeners:
            try:
                listener(result)
            except Exception as exc:
                logger.error(f"Matcher listener error: {exc}")
        return result

    def on_storage_watcher_event(
        self,
        payload: Dict[str, Any],
        file_content: Optional[Union[str, bytes]] = None,
    ) -> Optional[MatchResult]:
        """Translates generic storage watcher notification into DocumentArrivalEvent and matches."""
        obj_name = payload.get("object_name") or payload.get("filename") or ""
        parsed = parse_agreement_path(obj_name)
        tenant_id = payload.get("organization_id") or parsed.get("tenant_id")
        if not tenant_id:
            return None

        event = DocumentArrivalEvent(
            file_path=obj_name,
            tenant_id=tenant_id,
            gcs_uri=f"gs://{payload.get('bucket', 'default')}/{obj_name}",
            file_hash=payload.get("etag") or compute_file_hash(file_content or obj_name),
            production_id=payload.get("production_id") or parsed.get("production_id"),
        )
        return self.on_document_arrival(event, file_content=file_content)
