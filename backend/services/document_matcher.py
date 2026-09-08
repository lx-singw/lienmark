"""
backend/services/document_matcher.py

Autonomous document matcher integrating Storage Watcher events with ClarificationStore.
Enforces dual-key invariant matching, auto-resolution, and zero-click pipeline resumption.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple, Union

from backend.domain.models import ClarificationRequest
from backend.orchestration.suspension import SuspensionManager
from backend.services.agreement_parser import AgreementParser, compute_file_hash
from backend.services.document_matcher_scoring import (
    compute_parties_similarity,
    compute_text_similarity,
    compute_type_similarity,
    evaluate_dual_key_match,
    is_agreement_ambiguous,
    verify_agreement_sufficiency,
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
    "is_agreement_ambiguous",
    "verify_agreement_sufficiency",
]


class DocumentMatcherService:
    """Autonomous Document Matcher orchestrating dual-key matching and pipeline resumption."""

    def __init__(
        self,
        parser: Optional[AgreementParser] = None,
        clarification_store: Optional[ClarificationStore] = None,
        suspension_manager: Optional[SuspensionManager] = None,
        resumption_coordinator: Optional[object] = None,
        resumption_callback: Optional[Callable[[ClarificationRequest, ExtractedAgreementMetadata], object]] = None,
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
        disp = getattr(clrf, "disposition", None)
        if disp and str(disp).upper() == "APPROVED":
            raise ValueError("Critical invariant violation: document arrival cannot set or approve claim disposition.")
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

    def _dispatch_result(self, result: MatchResult) -> MatchResult:
        """Notifies registered listeners and returns the MatchResult."""
        for listener in self._listeners:
            try:
                listener(result)
            except Exception as exc:
                logger.error(f"Matcher listener error: {exc}")
        return result

    def _evaluate_qualifying(
        self,
        qualifying: List[Tuple[ClarificationRequest, MatchScoreBreakdown]],
        evaluated: List[Tuple[ClarificationRequest, MatchScoreBreakdown]],
        metadata: ExtractedAgreementMetadata,
        event: DocumentArrivalEvent,
    ) -> MatchResult:
        """Determines matching outcome from evaluated candidates."""
        if len(qualifying) > 1:
            for c, b in qualifying:
                self.store.flag_candidate_document(
                    request_id=c.request_id, tenant_id=event.tenant_id,
                    candidate_document_ref=metadata.document_id, match_confidence=b.composite_score,
                )
            top_clrf, top_bdown = max(qualifying, key=lambda pair: pair[1].composite_score)
            return self._flag_candidate(top_clrf, metadata, event, top_bdown)
        if len(qualifying) == 1:
            target_clrf, bdown = qualifying[0]
            suff_ok, _ = verify_agreement_sufficiency(metadata, target_clrf, event, bdown)
            ambig_found, _ = is_agreement_ambiguous(metadata, target_clrf)
            if suff_ok and not ambig_found:
                return self._resolve_match(target_clrf, metadata, event, bdown)
            return self._flag_candidate(target_clrf, metadata, event, bdown)
        best_clrf, best_bdown = max(evaluated, key=lambda pair: pair[1].composite_score)
        return self._flag_candidate(best_clrf, metadata, event, best_bdown)

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

        evaluated: List[Tuple[ClarificationRequest, MatchScoreBreakdown]] = []
        for clrf in open_clrfs:
            valid, bdown = evaluate_dual_key_match(metadata, clrf, event)
            if valid and bdown.composite_score >= 0.40:
                evaluated.append((clrf, bdown))

        if not evaluated:
            return MatchResult(
                event_id=event.event_id, document_id=metadata.document_id,
                decision=MatchingDecision.NO_MATCH, confidence_score=0.0, dual_key_valid=False,
            )

        qualifying = [(c, b) for c, b in evaluated if b.composite_score > 0.85]
        res = self._evaluate_qualifying(qualifying, evaluated, metadata, event)
        return self._dispatch_result(res)

    def on_storage_watcher_event(
        self,
        payload: Dict[str, Union[str, int, float, bool, None, Dict[str, object]]],
        file_content: Optional[Union[str, bytes]] = None,
    ) -> Optional[MatchResult]:
        """Translates generic storage watcher notification into DocumentArrivalEvent and matches."""
        obj_name = str(payload.get("object_name") or payload.get("filename") or "")
        parsed = parse_agreement_path(obj_name)
        tenant_id = str(payload.get("organization_id") or parsed.get("tenant_id") or "")
        if not tenant_id:
            return None

        event = DocumentArrivalEvent(
            file_path=obj_name,
            tenant_id=tenant_id,
            gcs_uri=f"gs://{payload.get('bucket', 'default')}/{obj_name}",
            file_hash=str(payload.get("etag") or compute_file_hash(file_content or obj_name)),
            production_id=str(payload.get("production_id") or parsed.get("production_id") or ""),
        )
        return self.on_document_arrival(event, file_content=file_content)
