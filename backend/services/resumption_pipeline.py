"""
backend/services/resumption_pipeline.py

Service for triggering durable investigation resumption upon clarification resolution.
Sprint 4.2 / Milestone D - Human-in-the-Loop Clarification Resumption.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from backend.domain.models import CensusDisposition, ClarificationRequest
from backend.orchestration.resumption import ResumptionCoordinator
from backend.orchestration.resumption_types import (
    ResolutionPayload,
    ResumptionResult,
)
from backend.orchestration.suspension import SuspensionManager
from backend.storage.checkpoint_store import CheckpointStore

logger = logging.getLogger("lienmark.services.resumption_pipeline")


class ResumptionPipelineService:
    """
    Orchestrates durable pipeline resumption immediately upon clarification resolution.
    Enforces invariant: Answering a clarification NEVER sets clearance disposition to APPROVED.
    """

    def __init__(
        self,
        coordinator: Optional[ResumptionCoordinator] = None,
        suspension_manager: Optional[SuspensionManager] = None,
        checkpoint_store: Optional[CheckpointStore] = None,
    ) -> None:
        self._coordinator = coordinator
        self._suspension_manager = suspension_manager
        self._checkpoint_store = checkpoint_store

    def _build_resolution_payload(
        self,
        clarification: ClarificationRequest,
        actor_id: str,
    ) -> ResolutionPayload:
        """Constructs canonical ResolutionPayload preserving provided facts and documents."""
        facts: Dict[str, str] = {}
        if clarification.response_text:
            facts["response_text"] = clarification.response_text
        if clarification.selected_option:
            facts["selected_option"] = clarification.selected_option

        docs: List[str] = []
        if clarification.attached_document_ref:
            docs.append(clarification.attached_document_ref)

        return ResolutionPayload(
            resolution_id=f"res_{clarification.request_id}",
            claim_id=clarification.claim_id,
            clarification_id=clarification.request_id,
            resolved_by=clarification.resolved_by or actor_id,
            provided_facts=facts,
            attached_documents=docs,
            notes=f"Resolved via {clarification.resolution_channel or 'api_submission'}",
        )

    def _verify_non_approved_disposition(
        self,
        clarification: ClarificationRequest,
    ) -> None:
        """Enforces governance invariant: clarification response NEVER sets disposition to APPROVED."""
        disposition_val = getattr(clarification, "disposition", None)
        if disposition_val is not None:
            norm_disp = str(disposition_val).lower().strip()
            if norm_disp in (CensusDisposition.APPROVED.value, "approved"):
                raise ValueError(
                    "Security invariant violated: answering clarification cannot set clearance disposition to APPROVED."
                )

    def trigger_resumption(
        self,
        clarification: ClarificationRequest,
        tenant_id: str,
        actor_id: str,
    ) -> Optional[ResumptionResult]:
        """Triggers durable pipeline resumption immediately upon atomic resolution commit."""
        self._verify_non_approved_disposition(clarification)
        payload = self._build_resolution_payload(clarification, actor_id)

        target_prod = clarification.production_id or "prod_default"
        logger.info(
            f"Triggering durable resumption for request='{clarification.request_id}', "
            f"claim='{clarification.claim_id}', tenant='{tenant_id}', prod='{target_prod}'"
        )

        if self._suspension_manager:
            for cp in self._suspension_manager.checkpoints.values():
                is_pending = clarification.request_id in cp.pending_clarification_ids
                is_same_claim = cp.claim_id == clarification.claim_id
                if is_pending or is_same_claim:
                    coord = self._coordinator or ResumptionCoordinator(
                        suspension_manager=self._suspension_manager,
                        checkpoint_store=self._checkpoint_store,
                    )
                    return coord.resume_run(
                        checkpoint_id=cp.checkpoint_id,
                        resume_token=cp.resume_token,
                        resolution_payload=payload,
                        tenant_id=tenant_id,
                        production_id=target_prod,
                        run_id=clarification.run_id,
                    )
        return None

    def __call__(
        self,
        clarification: ClarificationRequest,
        tenant_id: str,
        actor_id: str,
    ) -> Optional[ResumptionResult]:
        """Allows direct callable invocation of service."""
        return self.trigger_resumption(clarification, tenant_id, actor_id)


_service_instance: Optional[ResumptionPipelineService] = None


def get_resumption_pipeline_service() -> ResumptionPipelineService:
    """FastAPI dependency provider returning singleton ResumptionPipelineService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ResumptionPipelineService()
    return _service_instance


def set_resumption_pipeline_service(
    service: Optional[ResumptionPipelineService],
) -> None:
    """Sets global test override for ResumptionPipelineService."""
    global _service_instance
    _service_instance = service
