"""
backend/services/agreement_verifier.py

Post-resumption contract verification service and cryptographic ledger integration.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.domain.models import (
    ApprovalOrigin,
    AtomicRightsClaim,
    CensusDisposition,
    ClarificationRequest,
)
from backend.services.agreement_verifier_rules import (
    calculate_compliance,
    evaluate_execution_validity,
    evaluate_grant_scope,
)
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput,
    AgreementVerificationResult,
    ProductionRequirements,
    RightType,
)
from backend.storage.ledger import CryptographicLedger
from backend.storage.ledger_types import AuditEvent

logger = logging.getLogger("lienmark.services.agreement_verifier")


def _derive_requirements(
    claim: Optional[Union[AtomicRightsClaim, ClarificationRequest, Dict[str, Any]]],
    req_override: Optional[ProductionRequirements],
) -> ProductionRequirements:
    """Extracts target exploitation requirements from claim or production defaults."""
    if req_override is not None:
        return req_override

    req = ProductionRequirements()
    if isinstance(claim, AtomicRightsClaim):
        if claim.intended_territory:
            req.required_territory = claim.intended_territory[0]
        if claim.intended_media:
            req.required_media = claim.intended_media
        cat = (claim.right_category or "").lower()
        if "music" in cat or "comp" in cat:
            req.required_rights.append(RightType.SYNCHRONIZATION)
        elif "master" in cat:
            req.required_rights.append(RightType.MASTER_RECORDING)
        elif "trademark" in cat or "brand" in cat:
            req.required_rights.append(RightType.TRADEMARK_APPEARANCE)
    return req


def _build_audit_payload(result: AgreementVerificationResult) -> Dict[str, Any]:
    """Serializes verification outcome into canonical audit payload."""
    return {
        "action": "LICENSE_VERIFIED_AGREEMENT",
        "verification_id": result.verification_id,
        "agreement_id": result.agreement_id,
        "claim_id": result.claim_id,
        "is_valid": result.is_valid,
        "compliance_score": result.compliance_score,
        "verified_license_ref": result.verified_license_ref,
        "status": result.status.value,
        "requires_counsel_rider": result.requires_counsel_rider,
        "missing_clauses": result.missing_clauses,
        "rider_reasons": result.rider_reasons,
    }


def _append_to_ledger_safely(
    ledger: CryptographicLedger,
    tenant_id: str,
    production_id: str,
    actor_id: str,
    payload: Dict[str, Any],
) -> Optional[AuditEvent]:
    """Appends event to ledger, initializing genesis if chain is absent."""
    try:
        return ledger.append_event(
            tenant_id=tenant_id,
            production_id=production_id,
            actor_id=actor_id,
            action_type="LICENSE_VERIFIED_AGREEMENT",
            payload=payload,
        )
    except Exception as exc:
        logger.debug(f"Ledger append failed ({exc}); attempting genesis initialization.")
        try:
            ledger.initialize_production_ledger(
                tenant_id=tenant_id, production_id=production_id, actor_id=actor_id
            )
            return ledger.append_event(
                tenant_id=tenant_id,
                production_id=production_id,
                actor_id=actor_id,
                action_type="LICENSE_VERIFIED_AGREEMENT",
                payload=payload,
            )
        except Exception as final_exc:
            logger.error(f"Failed to record audit event in ledger: {final_exc}")
            return None


class AgreementVerifier:
    """
    Contract verification engine for unblocking claims post-clarification.
    Enforces execution validity, grant scope matching, and ledger recording.
    """

    def __init__(self, ledger: Optional[CryptographicLedger] = None) -> None:
        self._ledger = ledger or CryptographicLedger()

    def verify_agreement(
        self,
        doc: AgreementDocumentInput,
        claim: Optional[Union[AtomicRightsClaim, ClarificationRequest, Dict[str, Any]]] = None,
        requirements: Optional[ProductionRequirements] = None,
    ) -> AgreementVerificationResult:
        """Executes full verification checklist against production requirements."""
        claim_id = getattr(claim, "claim_id", "clm_unspecified") if claim else "clm_unspecified"
        req = _derive_requirements(claim, requirements)

        exec_val, cit_exec = evaluate_execution_validity(doc, req)
        scope, def_scope, cit_scope = evaluate_grant_scope(doc, req)

        missing_clauses = exec_val.execution_deficiencies + def_scope
        score, is_valid, req_rider, rider_reasons, status = calculate_compliance(
            exec_val, scope, missing_clauses
        )

        all_citations = cit_exec + cit_scope
        digest_slice = hashlib.sha256(f"{doc.agreement_id}:{score}".encode("utf-8")).hexdigest()[:8]
        lic_ref = f"lic_ref_{doc.agreement_id}_{digest_slice}" if is_valid else None

        return AgreementVerificationResult(
            agreement_id=doc.agreement_id,
            claim_id=claim_id,
            is_valid=is_valid,
            compliance_score=score,
            missing_clauses=missing_clauses,
            grant_scope=scope,
            execution_validity=exec_val,
            verified_citations=all_citations,
            requires_counsel_rider=req_rider,
            rider_reasons=rider_reasons,
            verified_license_ref=lic_ref,
            status=status,
            notes=f"Compliance score {score:.2f} under ruleset E&O-2026.1",
        )

    def record_verification_in_ledger(
        self,
        result: AgreementVerificationResult,
        tenant_id: str,
        production_id: str,
        actor_id: str,
    ) -> Optional[AuditEvent]:
        """Appends tamper-evident audit event linking verified license to claim."""
        payload = _build_audit_payload(result)
        return _append_to_ledger_safely(self._ledger, tenant_id, production_id, actor_id, payload)

    def update_claim_state(
        self,
        claim: AtomicRightsClaim,
        result: AgreementVerificationResult,
        counsel_signoff: bool = False,
    ) -> AtomicRightsClaim:
        """Synchronizes claim state, licensed scope, and disposition with verification results."""
        claim.licensor_grant_confirmed = result.is_valid
        claim.licensed_territory = result.grant_scope.permitted_territories or ["Worldwide"]
        claim.licensed_media = result.grant_scope.permitted_media or ["All Media"]
        claim.licensed_term = result.grant_scope.term_scope.value

        if result.requires_counsel_rider:
            claim.disposition = CensusDisposition.CONDITIONAL
            claim.decision_conditions = list(result.rider_reasons)
        elif result.is_valid and counsel_signoff:
            claim.disposition = CensusDisposition.APPROVED
            claim.approval_origin = ApprovalOrigin.INITIAL_APPROVAL
        else:
            claim.disposition = CensusDisposition.NEEDS_REVIEW

        claim.notes = f"Verified by license {result.agreement_id} (score {result.compliance_score:.2f})."
        return claim

    def verify_and_unblock(
        self,
        clarification: ClarificationRequest,
        claim: AtomicRightsClaim,
        doc: AgreementDocumentInput,
        tenant_id: str,
        actor_id: str,
        production_id: str = "prod_default",
        requirements: Optional[ProductionRequirements] = None,
    ) -> Tuple[AgreementVerificationResult, Optional[AuditEvent]]:
        """Coordinates post-resumption verification, unblocks clarification, and persists to ledger."""
        res = self.verify_agreement(doc=doc, claim=claim, requirements=requirements)
        self.update_claim_state(claim, res, counsel_signoff=False)

        if res.is_valid:
            clarification.status = "resolved"
            clarification.attached_document_ref = res.verified_license_ref or doc.agreement_id
            clarification.response_text = f"Unblocked by verified agreement {doc.agreement_id}."
            claim.clarification_request_id = None

        event = self.record_verification_in_ledger(
            result=res,
            tenant_id=tenant_id,
            production_id=production_id,
            actor_id=actor_id,
        )
        if event:
            res.ledger_event_id = event.event_id
        return res, event
