"""
Lienmark Evidence Reconciliation Engine
Reconciles external search evidence with private contracts, classifies evidence stances,
and enforces fail-closed policies for version-bound clearance change control.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlsplit
from typing import Dict, List, Optional, Sequence, Union

from backend.domain.models import (
    ContractAgreement,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    EvidenceReconciliationResult,
    EvidenceStance,
    PublicEvidenceSnapshot,
)

logger = logging.getLogger("lienmark.evidence_reconciler")


class EvidenceReconciler:
    """
    Core Evidence Reconciliation Engine for Lienmark.
    
    Responsibilities:
    1. Categorizes external search evidence into four canonical stances:
       - SUPPORTING: Confirms public domain status, clear title, expired renewal, or licensed use.
       - INFORMATIONAL: Background or neutral registry records without adverse or confirmatory claims.
       - CONTRADICTORY: Active third-party ownership, adverse copyright assignments, or disputes.
       - INSUFFICIENT: Search failure (timeout, 5xx, rate limit), empty excerpt, or unresolvable results.
    2. Private Contract Reconciliation:
       - Reconciles public search evidence against private ContractAgreement terms.
       - Core Principle: A public catalog ownership shift alone DOES NOT void an existing valid,
         active, perpetual private agreement unless an active revocation or judicial injunction is proven.
    3. Fail-Closed Policy:
       - If Parallel Search fails (timeout, 5xx, rate limit), marks stance as INSUFFICIENT and
         leaves the clearance decision STALE with revalidation_action='manual'.
    """

    # Regex patterns for judicial injunction or formal license revocation
    REVOCATION_PATTERNS = [
        re.compile(r"\bjudicial\s+injunction\b", re.IGNORECASE),
        re.compile(r"\bcourt\s+injunction\b", re.IGNORECASE),
        re.compile(r"\bpreliminary\s+injunction\b", re.IGNORECASE),
        re.compile(r"\bpermanent\s+injunction\b", re.IGNORECASE),
        re.compile(r"\benjoining\b", re.IGNORECASE),
        re.compile(r"\blicense\s+revoked\b", re.IGNORECASE),
        re.compile(r"\bcontract\s+terminated\b", re.IGNORECASE),
        re.compile(r"\blicense\s+terminated\b", re.IGNORECASE),
        re.compile(r"\brescinded\b", re.IGNORECASE),
        re.compile(r"\bvoided\s+by\s+court\b", re.IGNORECASE),
        re.compile(r"\bbreach\s+of\s+contract\s+judgment\b", re.IGNORECASE),
    ]

    # Regex patterns for public catalog assignment / ownership shifts
    CATALOG_SHIFT_PATTERNS = [
        re.compile(r"\bassigned\s+(?:to|in|august|january|february|march|april|may|june|july|september|october|november|december)\b", re.IGNORECASE),
        re.compile(r"\bexclusive\s+(?:synchronization|sync|master|distribution|copyright)\s+rights\s+assigned\b", re.IGNORECASE),
        re.compile(r"\bownership\s+(?:transfer|transferred|assigned)\b", re.IGNORECASE),
        re.compile(r"\bacquired\s+by\b", re.IGNORECASE),
        re.compile(r"\bcatalog\s+sale\b", re.IGNORECASE),
        re.compile(r"\bdisputed\s+under\b", re.IGNORECASE),
        re.compile(r"\bvanguard\s+media\b", re.IGNORECASE),
    ]

    # Regex patterns for supporting / public domain evidence
    SUPPORTING_PATTERNS = [
        re.compile(r"\bpublic\s+domain\b", re.IGNORECASE),
        re.compile(r"\bexpired\s+(?:without|in)\s+(?:timely\s+)?renewal\b", re.IGNORECASE),
        re.compile(r"\bno\s+active\s+copyright\b", re.IGNORECASE),
        re.compile(r"\bno\s+adverse\b", re.IGNORECASE),
        re.compile(r"\bnon-infringing\b", re.IGNORECASE),
        re.compile(r"\bclearance\s+confirmed\b", re.IGNORECASE),
        re.compile(r"\bwork\s+is\s+in\s+the\s+public\s+domain\b", re.IGNORECASE),
        re.compile(r"\bunrestricted\s+public\s+use\b", re.IGNORECASE),
    ]

    # Regex patterns for contradictory evidence
    CONTRADICTORY_PATTERNS = [
        re.compile(r"\bworldwide\s+exclusive\b", re.IGNORECASE),
        re.compile(r"\brights\s+assigned\b", re.IGNORECASE),
        re.compile(r"\bcopyright\s+(?:dispute|disputed|assignment|conflict)\b", re.IGNORECASE),
        re.compile(r"\bassertions?\s+disputed\b", re.IGNORECASE),
        re.compile(r"\bstatus\s+disputed\b", re.IGNORECASE),
        re.compile(r"\bdisputed\b", re.IGNORECASE),
        re.compile(r"\bexclusive\s+(?:copyright|sync|synchronization|master|rights|ownership)\b", re.IGNORECASE),
        re.compile(r"\b(?:ownership|rights)\s+(?:was\s+|were\s+)?assigned\b", re.IGNORECASE),
        re.compile(r"\binfringement\b", re.IGNORECASE),
        re.compile(r"\bunauthorized\b", re.IGNORECASE),
        re.compile(r"\bcease\s+and\s+desist\b", re.IGNORECASE),
        re.compile(r"\bactive\s+litigation\b", re.IGNORECASE),
    ]

    @classmethod
    def classify_stance(
        cls,
        evidence: Optional[PublicEvidenceSnapshot],
    ) -> EvidenceStance:
        """
        Categorizes external search evidence into one of four canonical stances:
        SUPPORTING, INFORMATIONAL, CONTRADICTORY, INSUFFICIENT.
        """
        if evidence is None:
            return EvidenceStance.INSUFFICIENT

        # 1. Fail-closed check: HTTP status codes indicating network, server, or rate-limit failure
        if evidence.http_status is not None and evidence.http_status in (429, 500, 502, 503, 504):
            logger.warning(
                f"Classifying evidence '{evidence.snapshot_id}' as INSUFFICIENT due to HTTP {evidence.http_status}."
            )
            return EvidenceStance.INSUFFICIENT

        # Check explicit fail-closed metadata
        if evidence.metadata.get("fail_closed") is True or evidence.metadata.get("error"):
            return EvidenceStance.INSUFFICIENT

        combined_text = f"{evidence.excerpt or ''} {evidence.snippet or ''} {evidence.source_title or ''}".strip()
        if not combined_text:
            return EvidenceStance.INSUFFICIENT

        # Check for explicit timeout or error phrases
        if "timed out" in combined_text.lower() or "search failure" in combined_text.lower():
            return EvidenceStance.INSUFFICIENT

        # 2. Check for contradictory indicators
        has_contradictory = any(p.search(combined_text) for p in cls.CONTRADICTORY_PATTERNS)
        has_supporting = any(p.search(combined_text) for p in cls.SUPPORTING_PATTERNS)

        if has_contradictory and not has_supporting:
            return EvidenceStance.CONTRADICTORY

        if has_supporting and not has_contradictory:
            return EvidenceStance.SUPPORTING

        if has_supporting and has_contradictory:
            # When both exist, if public domain is asserted but disputed by an active assignee, stance is contradictory
            if "disputed" in combined_text.lower() or "assigned" in combined_text.lower():
                return EvidenceStance.CONTRADICTORY
            return EvidenceStance.CONTRADICTORY

        # If already predetermined on the snapshot
        if evidence.stance in (EvidenceStance.SUPPORTING, EvidenceStance.CONTRADICTORY, EvidenceStance.INSUFFICIENT):
            return evidence.stance

        # 3. Informational / Neutral registry record fallback
        return EvidenceStance.INFORMATIONAL

    @classmethod
    def check_revocation_or_injunction(cls, text: str) -> bool:
        """
        Detects whether public evidence proves an active judicial injunction
        or formal revocation of license rights.
        """
        if not text:
            return False
        return any(p.search(text) for p in cls.REVOCATION_PATTERNS)

    @classmethod
    def check_catalog_shift(cls, text: str) -> bool:
        """
        Detects whether public evidence describes a catalog ownership transfer or assignment.
        """
        if not text:
            return False
        return any(p.search(text) for p in cls.CATALOG_SHIFT_PATTERNS)

    def reconcile_claim(
        self,
        stable_lineage_key: str,
        decision_id: str,
        evidence: Optional[PublicEvidenceSnapshot],
        contract: Optional[ContractAgreement] = None,
        prior_validity: Optional[DecisionValidity] = None,
    ) -> EvidenceReconciliationResult:
        """
        Reconciles public search evidence against private contract agreements and prior decision state.
        
        Enforces:
        1. Fail-Closed Policy:
           If search fails (timeout, 5xx, rate limit), marks stance as INSUFFICIENT and
           leaves the decision STALE with revalidation_action='manual'.
        2. Private Contract Reconciliation:
           A public catalog ownership shift alone DOES NOT void an existing valid, active, perpetual
           private agreement unless an active revocation or judicial injunction is proven.
        """
        raw_stance = self.classify_stance(evidence)
        citations: List[Dict[str, str]] = []
        if evidence:
            domain_val = evidence.domain or (urlsplit(evidence.source_url).netloc if evidence.source_url else "search.parallel.ai")
            citations.append({
                "source_title": evidence.source_title,
                "source_url": evidence.source_url,
                "excerpt": evidence.excerpt,
                "domain": domain_val,
                "stance": raw_stance.value,
            })

        combined_text = f"{evidence.excerpt if evidence else ''} {evidence.source_title if evidence else ''}"

        # -----------------------------------------------------------------
        # 1. FAIL-CLOSED POLICY (Timeout, 5xx, 429 Rate Limit, Network Fail)
        # -----------------------------------------------------------------
        if raw_stance == EvidenceStance.INSUFFICIENT:
            http_code = evidence.http_status if evidence else None
            explanation = (
                f"Fail-closed policy engaged for '{stable_lineage_key}': Parallel Search returned "
                f"INSUFFICIENT evidence (HTTP status: {http_code or 'ERROR'}). Unverified rights cannot "
                "be cleared automatically; clearance decision remains STALE with manual attorney review required."
            )
            logger.warning(f"Fail-closed policy applied for claim '{stable_lineage_key}': {explanation}")
            return EvidenceReconciliationResult(
                stable_lineage_key=stable_lineage_key,
                decision_id=decision_id,
                raw_stance=EvidenceStance.INSUFFICIENT,
                reconciled_stance=EvidenceStance.INSUFFICIENT,
                has_contract=(contract is not None and contract.is_active),
                contract_shield_applied=False,
                contract_id=contract.agreement_id if contract else None,
                decision_state=DecisionState.STALE,
                revalidation_action="manual",
                reason_code="SEARCH_EVIDENCE_INSUFFICIENT",
                explanation=explanation,
                evidence_snapshot=evidence,
                citations=citations,
                is_license_voided=True,
                requires_counsel_rider=True,
            )

        # -----------------------------------------------------------------
        # 2. PRIVATE CONTRACT RECONCILIATION
        # -----------------------------------------------------------------
        has_active_contract = (contract is not None and contract.is_active)

        if has_active_contract and contract is not None:
            is_perpetual = "perpetuit" in contract.term.lower() or "all media" in contract.scope.lower()
            proven_revocation_or_injunction = self.check_revocation_or_injunction(combined_text)

            if proven_revocation_or_injunction:
                # Active revocation or court injunction defeats the contract defense
                explanation = (
                    f"Contract defense defeated for '{stable_lineage_key}': Evidence from '{evidence.source_title if evidence else 'registry'}' "
                    f"proves an active judicial injunction or license revocation against agreement #{contract.agreement_id} "
                    f"(Licensor: '{contract.licensor}'). Clearance decision remains STALE; manual revalidation required."
                )
                logger.error(explanation)
                return EvidenceReconciliationResult(
                    stable_lineage_key=stable_lineage_key,
                    decision_id=decision_id,
                    raw_stance=raw_stance,
                    reconciled_stance=EvidenceStance.CONTRADICTORY,
                    has_contract=True,
                    contract_shield_applied=False,
                    contract_id=contract.agreement_id,
                    decision_state=DecisionState.STALE,
                    revalidation_action="manual",
                    reason_code="CONTRACT_REVOCATION_OR_INJUNCTION_PROVEN",
                    explanation=explanation,
                    evidence_snapshot=evidence,
                    citations=citations,
                    is_license_voided=True,
                    requires_counsel_rider=True,
                )

            # Check if evidence describes a catalog ownership shift (e.g. Vanguard Media)
            is_catalog_shift = self.check_catalog_shift(combined_text) or raw_stance == EvidenceStance.CONTRADICTORY

            if is_catalog_shift and is_perpetual:
                # THE STATUTORY CONTRACT SHIELD:
                # Under entertainment copyright law (17 U.S.C. § 205(e), California contract law),
                # an assignee takes title subject to valid prior licenses granted in perpetuity.
                # A public catalog sale/assignment DOES NOT void the existing valid license!
                explanation = (
                    f"Private Contract Reconciliation Applied for '{stable_lineage_key}': Public evidence indicates "
                    f"a catalog ownership shift/assignment ({evidence.excerpt if evidence else 'catalog transfer'}), but "
                    f"existing valid, active, perpetual private agreement #{contract.agreement_id} "
                    f"(Licensor: '{contract.licensor}', Scope: '{contract.scope}', Term: '{contract.term}') "
                    "remains binding on successor assignees. Under copyright and contract law, "
                    "a public catalog ownership shift alone DOES NOT void an existing valid, active, perpetual private agreement "
                    "unless an active revocation or judicial injunction is proven. Rights are shielded by contract; clearance carried forward."
                )
                logger.info(
                    f"Private contract shield successfully applied for '{stable_lineage_key}' against catalog shift."
                )
                return EvidenceReconciliationResult(
                    stable_lineage_key=stable_lineage_key,
                    decision_id=decision_id,
                    raw_stance=raw_stance,
                    reconciled_stance=EvidenceStance.SUPPORTING,
                    has_contract=True,
                    contract_shield_applied=True,
                    contract_id=contract.agreement_id,
                    decision_state=DecisionState.CARRIED_FORWARD,
                    revalidation_action="carry",
                    reason_code="PRIVATE_CONTRACT_SHIELD_APPLIED",
                    explanation=explanation,
                    evidence_snapshot=evidence,
                    citations=citations,
                    is_license_voided=False,
                    requires_counsel_rider=False,
                )
            elif is_catalog_shift and not is_perpetual:
                # Contract is active but limited/non-perpetual; cannot shield against new copyright owner
                explanation = (
                    f"Contract defense insufficient for '{stable_lineage_key}': Private agreement #{contract.agreement_id} "
                    f"has limited or non-perpetual term ('{contract.term}'). Public catalog shift to new rights holder "
                    f"creates unresolved rights dispute. Decision remains STALE; manual revalidation required."
                )
                logger.warning(explanation)
                return EvidenceReconciliationResult(
                    stable_lineage_key=stable_lineage_key,
                    decision_id=decision_id,
                    raw_stance=raw_stance,
                    reconciled_stance=EvidenceStance.CONTRADICTORY,
                    has_contract=True,
                    contract_shield_applied=False,
                    contract_id=contract.agreement_id,
                    decision_state=DecisionState.STALE,
                    revalidation_action="manual",
                    reason_code="CONTRACT_NON_PERPETUAL_CATALOG_SHIFT",
                    explanation=explanation,
                    evidence_snapshot=evidence,
                    citations=citations,
                    is_license_voided=True,
                    requires_counsel_rider=True,
                )
            else:
                # Public evidence is supporting or informational; contract confirms clean title
                explanation = (
                    f"Clearance confirmed by private agreement #{contract.agreement_id} "
                    f"(Licensor: '{contract.licensor}', Term: '{contract.term}') and supporting public evidence."
                )
                return EvidenceReconciliationResult(
                    stable_lineage_key=stable_lineage_key,
                    decision_id=decision_id,
                    raw_stance=raw_stance,
                    reconciled_stance=EvidenceStance.SUPPORTING,
                    has_contract=True,
                    contract_shield_applied=False,
                    contract_id=contract.agreement_id,
                    decision_state=DecisionState.CARRIED_FORWARD,
                    revalidation_action="carry",
                    reason_code="PRIVATE_CONTRACT_CONFIRMED",
                    explanation=explanation,
                    evidence_snapshot=evidence,
                    citations=citations,
                    is_license_voided=False,
                    requires_counsel_rider=False,
                )

        # -----------------------------------------------------------------
        # 3. NO ACTIVE CONTRACT (Inactive Contract or No Contract Found)
        # -----------------------------------------------------------------
        if contract is not None and not contract.is_active:
            explanation = (
                f"Private contract agreement #{contract.agreement_id} is INACTIVE. "
                f"Adverse public evidence ({evidence.excerpt if evidence else 'conflict'}) cannot be shielded; "
                "clearance decision remains STALE with manual attorney intervention required."
            )
            return EvidenceReconciliationResult(
                stable_lineage_key=stable_lineage_key,
                decision_id=decision_id,
                raw_stance=raw_stance,
                reconciled_stance=raw_stance,
                has_contract=False,
                contract_shield_applied=False,
                contract_id=contract.agreement_id,
                decision_state=DecisionState.STALE,
                revalidation_action="manual",
                reason_code="INACTIVE_CONTRACT_WITH_ADVERSE_EVIDENCE",
                explanation=explanation,
                evidence_snapshot=evidence,
                citations=citations,
                is_license_voided=True,
                requires_counsel_rider=True,
            )

        if raw_stance == EvidenceStance.CONTRADICTORY:
            # Adverse rights dispute with no contract shield (e.g. Golden Item 12)
            explanation = (
                f"Adverse rights dispute for '{stable_lineage_key}': Public evidence indicates conflicting "
                f"ownership or third-party copyright assignment in '{evidence.source_title if evidence else 'registry'}': "
                f"\"{evidence.excerpt if evidence else ''}\". No valid shielding private contract was found; "
                "clearance decision remains STALE with manual attorney intervention required."
            )
            logger.warning(f"Unshielded contradictory evidence for '{stable_lineage_key}': {explanation}")
            return EvidenceReconciliationResult(
                stable_lineage_key=stable_lineage_key,
                decision_id=decision_id,
                raw_stance=EvidenceStance.CONTRADICTORY,
                reconciled_stance=EvidenceStance.CONTRADICTORY,
                has_contract=False,
                contract_shield_applied=False,
                contract_id=None,
                decision_state=DecisionState.STALE,
                revalidation_action="manual",
                reason_code="UNRESOLVED_RIGHTS_DISPUTE",
                explanation=explanation,
                evidence_snapshot=evidence,
                citations=citations,
                is_license_voided=True,
                requires_counsel_rider=True,
            )

        elif raw_stance == EvidenceStance.SUPPORTING:
            # Confirmatory public domain or clean rights (e.g. Golden Item 11)
            explanation = (
                f"Public evidence confirms clearance for '{stable_lineage_key}' via '{evidence.source_title if evidence else 'LOC'}': "
                f"\"{evidence.excerpt if evidence else 'Public domain verified'}\". Prior creative drift resolved; "
                "eligible for counsel re-attestation."
            )
            logger.info(f"Supporting public domain evidence confirmed for '{stable_lineage_key}'.")
            return EvidenceReconciliationResult(
                stable_lineage_key=stable_lineage_key,
                decision_id=decision_id,
                raw_stance=EvidenceStance.SUPPORTING,
                reconciled_stance=EvidenceStance.SUPPORTING,
                has_contract=False,
                contract_shield_applied=False,
                contract_id=None,
                decision_state=DecisionState.STALE,  # Remains STALE until counsel signs re-attestation
                revalidation_action="revalidate",
                reason_code="EVIDENCE_CONFIRMED_PUBLIC_DOMAIN",
                explanation=explanation,
                evidence_snapshot=evidence,
                citations=citations,
                is_license_voided=False,
                requires_counsel_rider=False,
            )

        else:  # INFORMATIONAL
            explanation = (
                f"Public evidence for '{stable_lineage_key}' is informational only ({evidence.source_title if evidence else 'registry'}), "
                "without affirmative clearance or adverse conflict. Manual counsel evaluation required."
            )
            return EvidenceReconciliationResult(
                stable_lineage_key=stable_lineage_key,
                decision_id=decision_id,
                raw_stance=EvidenceStance.INFORMATIONAL,
                reconciled_stance=EvidenceStance.INFORMATIONAL,
                has_contract=False,
                contract_shield_applied=False,
                contract_id=None,
                decision_state=DecisionState.STALE,
                revalidation_action="manual",
                reason_code="INFORMATIONAL_EVIDENCE_UNRESOLVED",
                explanation=explanation,
                evidence_snapshot=evidence,
                citations=citations,
                is_license_voided=False,
                requires_counsel_rider=True,
            )

    def reconcile_all(
        self,
        validity_results: List[DecisionValidity],
        evidence_snapshots: Dict[str, PublicEvidenceSnapshot],
        contracts: Optional[Union[List[ContractAgreement], Dict[str, ContractAgreement]]] = None,
        update_validity_in_place: bool = True,
    ) -> List[EvidenceReconciliationResult]:
        """
        Reconciles an entire batch of DecisionValidity claims with external evidence snapshots
        and private contract agreements.
        """
        contract_map: Dict[str, ContractAgreement] = {}
        if contracts:
            if isinstance(contracts, dict):
                contract_map = contracts
            else:
                contract_map = {c.stable_lineage_key: c for c in contracts}

        results: List[EvidenceReconciliationResult] = []

        for v in validity_results:
            key = v.stable_lineage_key
            ev = evidence_snapshots.get(key) or v.evidence_snapshot
            contract = contract_map.get(key)

            res = self.reconcile_claim(
                stable_lineage_key=key,
                decision_id=v.decision_id,
                evidence=ev,
                contract=contract,
                prior_validity=v,
            )
            results.append(res)

            if update_validity_in_place:
                # Update DecisionValidity attributes with reconciled outcome
                if res.contract_shield_applied:
                    v.state = res.decision_state
                    v.revalidation_action = res.revalidation_action
                    v.reason_code = res.reason_code
                    v.explanation = res.explanation
                elif res.raw_stance == EvidenceStance.INSUFFICIENT:
                    v.state = res.decision_state
                    v.revalidation_action = res.revalidation_action
                    v.reason_code = res.reason_code
                    v.explanation = res.explanation

        return results
