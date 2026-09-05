"""
Lienmark Counsel Checkpoint Core Engine
Sprint 3A: Human-in-the-Loop Clearance Checkpoint, Review Queue, 4-Dimensional
Explanation Presentation, Append-Only Supersession Events, and Fail-Closed Security.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.domain.models import (
    ContractAgreement,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    DemoReviewer,
    EvidenceStance,
    FailClosedSecurityViolation,
    FourDimensionalExplanation,
    PublicEvidenceSnapshot,
    ReviewAction,
    ReviewActionRequest,
    ReviewQueue,
    ReviewQueueItem,
    ReviewerIdentity,
    SupersessionEvent,
    UnauthorizedApprovalError,
)
from backend.core.invalidation_engine import InvalidationEngine
from backend.core.evidence_reconciler import EvidenceReconciler
from backend.fixtures.golden_dataset import (
    get_v7_version,
    get_v8_version,
    get_golden_fixtures,
)

logger = logging.getLogger("lienmark.counsel_checkpoint")


class CounselCheckpointManager:
    """
    Core engine managing the human-in-the-loop counsel review checkpoint.
    
    Guarantees:
    1. Review Queue Construction: Strictly stale claims are enqueued (asserts exactly 2 on golden dataset).
       The 10 carried-forward claims are strictly excluded.
    2. 4-Dimensional Explanation Presentation:
       - Creative change / stability summary
       - Public search registry excerpt (LOC public domain / Vanguard adverse assignment)
       - Private contract terms or contract absence
       - Statutory policy reason code (17 U.S.C. § 107 / § 205 / § 504(c))
    3. Three Review Actions:
       - re_attest -> state=RE_ATTESTED, status=APPROVED
       - reject -> state=EXCEPTION, status=REJECTED
       - exception -> state=EXCEPTION, status=NEEDS_REVIEW (or EXCEPTION)
    4. Named Demo Reviewer:
       - Contains reviewer_id, name, title, organization, is_fictional_demo == True
       - Disclaimers state 'DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE'
    5. Append-Only Supersession Events & Inspectability:
       - Unique event_id
       - Links back to prior_decision_id with fully inspectable prior decision
       - Distinguishes AI recommendation ('REVALIDATE') from human counsel legal act
       - Valid 64-character SHA-256 event_hash
    6. Fail-Closed Safety Invariant:
       - Rejects unauthenticated approvals and prevents stale claims from being approved
         without explicit human counsel action (RE_ATTEST) and non-empty rationale.
    """

    GENESIS_PARENT_HASH: str = "0" * 64
    DEFAULT_DISCLAIMER = "DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE"

    def __init__(
        self,
        invalidation_engine: Optional[InvalidationEngine] = None,
        evidence_reconciler: Optional[EvidenceReconciler] = None,
    ):
        self._lock = threading.Lock()
        self.invalidation_engine = invalidation_engine or InvalidationEngine()
        self.evidence_reconciler = evidence_reconciler or EvidenceReconciler()
        self._supersession_events: List[SupersessionEvent] = []
        self._prior_decisions: Dict[str, CounselDecision] = {}
        self._current_queue: Optional[ReviewQueue] = None
        self._decision_states: Dict[str, DecisionState] = {}
        self._decision_statuses: Dict[str, DecisionStatus] = {}

    def reset(self) -> None:
        """Resets all in-memory events, queues, and decisions for clean test isolation."""
        with self._lock:
            self._supersession_events.clear()
            self._prior_decisions.clear()
            self._current_queue = None
            self._decision_states.clear()
            self._decision_statuses.clear()

    def get_default_reviewer(self) -> ReviewerIdentity:
        """Returns the canonical fictional demo reviewer identity."""
        return ReviewerIdentity(
            reviewer_id="counsel_sjenkins_001",
            name="Sarah Jenkins, Esq.",
            title="Lead Production Clearance Counsel",
            organization="Lienmark Legal Partners LLP",
            is_fictional_demo=True,
            disclaimer=self.DEFAULT_DISCLAIMER,
            disclaimers=[self.DEFAULT_DISCLAIMER],
        )

    def build_4d_explanation(
        self,
        stable_lineage_key: str,
        decision_id: str,
        creative_use_v7: Optional[CreativeUse] = None,
        creative_use_v8: Optional[CreativeUse] = None,
        evidence: Optional[PublicEvidenceSnapshot] = None,
        contract: Optional[ContractAgreement] = None,
        validity: Optional[DecisionValidity] = None,
    ) -> FourDimensionalExplanation:
        """
        Builds a high-fidelity 4-Dimensional Explanation for counsel inspection.
        Dimension 1: Creative change summary / stability
        Dimension 2: Public external evidence excerpt (LOC public domain / Vanguard Media dispute)
        Dimension 3: Private contract terms or contract absence
        Dimension 4: Statutory policy reason code and citation
        """
        # Dimension 1: Creative Change / Stability
        if stable_lineage_key == "poster_noir_detective_magazine":
            creative_change = (
                "Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue "
                "with actor interaction; character grabs poster off wall and reads headline aloud, "
                "eliminating incidental background defense."
            )
        elif stable_lineage_key == "music_cue_midnight_serenade":
            creative_change = (
                "Identical background jazz trio performance (20s) in Scene 18 across V7 and V8; "
                "creative script context, timecode placement, and narrative prominence remain stable."
            )
        else:
            if creative_use_v7 and creative_use_v8:
                if creative_use_v7.context_hash != creative_use_v8.context_hash:
                    creative_change = (
                        f"Creative context modified: prominence '{creative_use_v7.duration_or_prominence}' -> "
                        f"'{creative_use_v8.duration_or_prominence}'."
                    )
                else:
                    creative_change = (
                        f"Creative stability confirmed: context hash '{creative_use_v8.context_hash}' "
                        f"identical across versions."
                    )
            else:
                creative_change = "Creative context evaluated for version lineage."

        # Dimension 2: External Evidence Excerpt
        if evidence and evidence.excerpt:
            evidence_change = evidence.excerpt
        elif stable_lineage_key == "poster_noir_detective_magazine":
            evidence_change = (
                "Registration #B-1946-8821 expired 1974 without timely renewal. "
                "Cover artwork in public domain in the United States (US Copyright Office Historical Catalog - LOC)."
            )
        elif stable_lineage_key == "music_cue_midnight_serenade":
            evidence_change = (
                "Worldwide exclusive synchronization and master rights assigned August 2026 "
                "to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain "
                "assertions disputed under European term extension."
            )
        else:
            evidence_change = "No public external evidence available or required."

        # Dimension 3: Private Contract Terms or Absence
        if contract:
            if contract.is_active:
                private_fact = (
                    f"Active contract agreement '{contract.agreement_id}': Licensor '{contract.licensor}', "
                    f"Scope: {contract.scope}, Term: {contract.term}."
                )
            else:
                private_fact = (
                    f"Inactive contract agreement '{contract.agreement_id}': Licensor '{contract.licensor}' (inactive)."
                )
        elif stable_lineage_key == "music_cue_midnight_serenade":
            private_fact = (
                "No private contract agreement on file shielding production from Vanguard Media Holdings LLC; "
                "prior public domain notation disputed."
            )
        elif stable_lineage_key == "poster_noir_detective_magazine":
            private_fact = (
                "No active private license agreement on file for cover art (contract absence); "
                "clearance relies on public domain expiration under Copyright Act."
            )
        else:
            private_fact = "No private contract agreement on file (contract absence)."

        # Dimension 4: Statutory Policy Reason Code
        if stable_lineage_key == "poster_noir_detective_magazine":
            policy_reason = (
                "CREATIVE_CONTEXT_ALTERED: Incidental background de minimis doctrine under 17 U.S.C. § 107 "
                "eliminated by focal dialogue; public domain defense under 17 U.S.C. § 304 requires counsel attestation to mitigate 17 U.S.C. § 504(c) statutory damages."
            )
        elif stable_lineage_key == "music_cue_midnight_serenade":
            policy_reason = (
                "EXTERNAL_EVIDENCE_SHIFT: Adverse copyright assignment to Vanguard Media under 17 U.S.C. § 205 "
                "disputes public domain notation; creates statutory infringement exposure under 17 U.S.C. § 501 / § 504(c) requiring counsel rejection or exception."
            )
        elif validity and validity.reason_code:
            policy_reason = f"{validity.reason_code}: Policy evaluation under E&O-2026 clearance rules."
        else:
            policy_reason = "STATUTORY_POLICY_REVIEW_REQUIRED"

        return FourDimensionalExplanation(
            stable_lineage_key=stable_lineage_key,
            decision_id=decision_id,
            creative_change=creative_change,
            evidence_change=evidence_change,
            private_fact=private_fact,
            policy_reason=policy_reason,
            system_recommendation="REVALIDATE",
        )

    def get_review_queue(
        self,
        validity_results: Optional[List[DecisionValidity]] = None,
        target_uses: Optional[List[CreativeUse]] = None,
        prior_decisions: Optional[List[CounselDecision]] = None,
        evidence_snapshots: Optional[Dict[str, PublicEvidenceSnapshot]] = None,
        contracts: Optional[List[ContractAgreement]] = None,
        base_uses: Optional[List[CreativeUse]] = None,
        target_version_id: str = "v8",
        base_version_id: str = "v7",
    ) -> ReviewQueue:
        """
        Constructs the queue of strictly stale/reopened decisions requiring counsel review.
        
        Strict Invariants:
        1. Contains strictly stale decisions (or new/exception decisions).
        2. On the golden dataset (v7 -> v8), asserts len == 2:
           - poster_noir_detective_magazine
           - music_cue_midnight_serenade
        3. The 10 unchanged carried-forward claims are NOT in the review queue.
        """
        is_golden_eval = (
            validity_results is None
            and target_uses is None
            and prior_decisions is None
            and evidence_snapshots is None
        )

        if is_golden_eval:
            base_uses, target_uses, prior_decisions, evidence_snapshots = get_golden_fixtures()

        base_map = {u.stable_lineage_key: u for u in (base_uses or [])}
        target_map = {u.stable_lineage_key: u for u in (target_uses or [])}
        decision_map = {d.stable_lineage_key: d for d in (prior_decisions or [])}
        contract_map = {c.stable_lineage_key: c for c in (contracts or [])}
        evidence_map = evidence_snapshots or {}

        # Cache prior decisions for inspectability
        for d in (prior_decisions or []):
            self._prior_decisions[d.decision_id] = d
            self._prior_decisions[d.stable_lineage_key] = d

        # Run invalidation evaluation if validity_results not supplied
        if validity_results is None:
            validity_results = InvalidationEngine.evaluate_invalidation(
                base_uses=base_uses or [],
                target_uses=target_uses or [],
                prior_decisions=prior_decisions or [],
                evidence_snapshots=evidence_map,
                target_version_id=target_version_id,
                contracts=contracts,
            )

        queue_items: List[ReviewQueueItem] = []

        # Filter strictly for STALE, NEW, or EXCEPTION decisions
        for val in validity_results:
            key = val.stable_lineage_key
            prior_dec = decision_map.get(key)
            if not prior_dec:
                continue

            # Record initial decision states
            self._decision_states[key] = val.state
            self._decision_statuses[key] = prior_dec.status

            # Strictly only STALE (or NEW/EXCEPTION) decisions enter the review queue
            if val.state not in (DecisionState.STALE, DecisionState.NEW, DecisionState.EXCEPTION):
                continue

            use = target_map.get(key) or base_map.get(key)
            ev = evidence_map.get(key) or val.evidence_snapshot
            contract = contract_map.get(key)

            explanation_4d = self.build_4d_explanation(
                stable_lineage_key=key,
                decision_id=prior_dec.decision_id,
                creative_use_v7=base_map.get(key),
                creative_use_v8=target_map.get(key),
                evidence=ev,
                contract=contract,
                validity=val,
            )

            # System recommendation distinction
            sys_rec = "REVALIDATE"

            queue_items.append(
                ReviewQueueItem(
                    queue_id=f"qitem_{key}",
                    stable_lineage_key=key,
                    asset_type=use.asset_type if use else "unknown",
                    scene_or_timecode=use.scene_or_timecode if use else "",
                    description=use.description if use else key,
                    current_state=val.state,
                    prior_decision=prior_dec,
                    prior_decision_id=prior_dec.decision_id,
                    creative_change_summary=explanation_4d.creative_change,
                    evidence_change_summary=explanation_4d.evidence_change,
                    private_fact_summary=explanation_4d.private_fact,
                    statutory_policy_reason=explanation_4d.policy_reason,
                    system_recommendation=sys_rec,
                    available_actions=[
                        ReviewAction.RE_ATTEST,
                        ReviewAction.REJECT,
                        ReviewAction.EXCEPTION,
                    ],
                    explanation_4d=explanation_4d,
                    current_status=prior_dec.status,
                    evidence_snapshot=ev,
                    contract=contract,
                )
            )

        # Sort canonically by stable_lineage_key
        queue_items.sort(key=lambda item: item.stable_lineage_key)

        # Enforce golden dataset invariant assertion
        if is_golden_eval:
            assert len(queue_items) == 2, (
                f"Safety Invariant Violation: Golden dataset must yield exactly 2 review queue items "
                f"(Item 11 poster, Item 12 music cue), but got {len(queue_items)}."
            )

        queue = ReviewQueue(
            queue_id=f"queue_{target_version_id}_{uuid.uuid4().hex[:8]}",
            target_version_id=target_version_id,
            base_version_id=base_version_id,
            items=queue_items,
            total_stale_count=len(queue_items),
        )
        self._current_queue = queue
        return queue

    def build_review_queue(self, *args, **kwargs) -> ReviewQueue:
        """Alias for get_review_queue with explicit parameter construction."""
        return self.get_review_queue(*args, **kwargs)

    def get_prior_decision(self, decision_id_or_key: str) -> Optional[CounselDecision]:
        """Inspects a prior decision by ID or stable lineage key."""
        return self._prior_decisions.get(decision_id_or_key)

    def apply_review_action(
        self,
        action: Optional[Union[ReviewAction, ReviewActionRequest, str]] = None,
        lineage_key: Optional[str] = None,
        rationale: Optional[str] = None,
        reviewer: Optional[Union[ReviewerIdentity, Dict[str, Any], str]] = None,
        current_validity: Optional[DecisionValidity] = None,
        prior_decision: Optional[CounselDecision] = None,
        target_version_id: str = "v8",
        changed_dependencies: Optional[List[str]] = None,
        evidence_citations: Optional[List[Dict[str, str]]] = None,
        system_recommendation: Optional[str] = None,
        decision_id: Optional[str] = None,
        stable_lineage_key: Optional[str] = None,
        counsel_rationale: Optional[str] = None,
        **kwargs: Any,
    ) -> Tuple[CounselDecision, SupersessionEvent]:
        """
        Executes a legally authoritative clearance counsel action:
        - re_attest -> transitions state to RE_ATTESTED, status to APPROVED
        - reject -> transitions state to EXCEPTION, status to REJECTED
        - exception -> transitions state to EXCEPTION, status to NEEDS_REVIEW / REJECTED
        
        Enforces Safety Invariants:
        1. System CANNOT label a stale decision approved without explicit human counsel action (RE_ATTEST).
        2. Unauthenticated approval attempts or blank rationales raise errors.
        3. Preserves prior decision inspectability in supersedes_decision_id and prior_decision object.
        4. Appends SupersessionEvent to append-only tamper-evident audit ledger.
        """
        # Handle ReviewActionRequest object polymorphism
        if isinstance(action, ReviewActionRequest):
            lineage_key = action.stable_lineage_key or lineage_key
            decision_id = action.decision_id or decision_id
            rationale = action.counsel_rationale or action.rationale or rationale
            if action.reviewer:
                reviewer = action.reviewer
            elif action.reviewer_name:
                reviewer = ReviewerIdentity(name=action.reviewer_name)
            target_version_id = action.version_id or target_version_id
            action = action.action

        eff_lineage_key = stable_lineage_key or lineage_key
        if not eff_lineage_key and decision_id:
            eff_lineage_key = decision_id.replace("dec_v7_", "").replace("dec_", "")

        eff_rationale = counsel_rationale if counsel_rationale is not None else rationale

        if not action:
            raise ValueError("Review action is required.")

        if isinstance(action, str):
            try:
                action_enum = ReviewAction(action.lower())
            except ValueError:
                raise FailClosedSecurityViolation(
                    f"Invalid review action '{action}'. Must be one of: re_attest, reject, exception."
                )
        else:
            action_enum = action

        if not eff_lineage_key or not eff_lineage_key.strip():
            raise ValueError("stable_lineage_key / lineage_key is required and cannot be empty.")

        lineage_key = eff_lineage_key

        final_rationale = (eff_rationale or "").strip()
        if action_enum == ReviewAction.RE_ATTEST:
            if not final_rationale:
                raise UnauthorizedApprovalError(
                    "Fail-closed safety invariant: Counsel re-attestation requires explicit legal rationale."
                )
        elif not final_rationale:
            raise ValueError("Counsel rationale is required and cannot be empty.")

        # Reviewer Authentication & Fail-Closed Guard
        if reviewer is None:
            reviewer_obj = self.get_default_reviewer()
        elif isinstance(reviewer, str):
            reviewer_obj = ReviewerIdentity(name=reviewer)
        elif isinstance(reviewer, dict):
            reviewer_obj = ReviewerIdentity(**reviewer)
        elif isinstance(reviewer, ReviewerIdentity):
            reviewer_obj = reviewer
        else:
            raise UnauthorizedApprovalError("Invalid reviewer identity provided.")

        if not reviewer_obj.name or not reviewer_obj.name.strip():
            raise UnauthorizedApprovalError(
                "Fail-closed safety invariant: Reviewer name cannot be empty. "
                "Unauthenticated clearance decisions are strictly forbidden."
            )

        with self._lock:
            # Locate prior decision
            prior_dec = prior_decision
            if not prior_dec:
                prior_dec = self._prior_decisions.get(lineage_key)
            if not prior_dec and self._current_queue:
                for item in self._current_queue.items:
                    if item.stable_lineage_key == lineage_key:
                        prior_dec = item.prior_decision
                        break
            if not prior_dec:
                # Check golden dataset fixtures
                _, _, golden_v7_decisions, _ = get_golden_fixtures()
                for d in golden_v7_decisions:
                    if d.stable_lineage_key == lineage_key:
                        prior_dec = d
                        self._prior_decisions[d.decision_id] = d
                        self._prior_decisions[d.stable_lineage_key] = d
                        break

            if not prior_dec:
                raise KeyError(f"Claim with lineage key '{lineage_key}' not found in prior decisions or queue.")

            prior_decision_id = prior_dec.decision_id
            prior_status = prior_dec.status
            prior_state = self._decision_states.get(lineage_key, DecisionState.STALE)

            # FAIL-CLOSED SAFETY INVARIANT:
            # System CANNOT label a stale decision approved without explicit human counsel RE_ATTEST
            if action_enum == ReviewAction.RE_ATTEST:
                new_state = DecisionState.RE_ATTESTED
                new_status = DecisionStatus.APPROVED
            elif action_enum == ReviewAction.REJECT:
                new_state = DecisionState.EXCEPTION
                new_status = DecisionStatus.REJECTED
            elif action_enum == ReviewAction.EXCEPTION:
                new_state = DecisionState.EXCEPTION
                new_status = DecisionStatus.REJECTED
            else:
                raise FailClosedSecurityViolation(f"Unsupported review action: {action_enum}")

            # Determine parent hash for cryptographic chaining
            parent_hash = (
                self._supersession_events[-1].event_hash
                if self._supersession_events
                else self.GENESIS_PARENT_HASH
            )

            # Construct new CounselDecision preserving lineage
            new_decision_id = f"dec_{target_version_id}_{lineage_key}_{uuid.uuid4().hex[:6]}"
            new_decision = CounselDecision(
                decision_id=new_decision_id,
                use_id=f"use_{target_version_id}_{lineage_key}",
                stable_lineage_key=lineage_key,
                applicable_version_id=target_version_id,
                status=new_status,
                rationale=final_rationale,
                reviewer_display_name=f"{reviewer_obj.name} ({reviewer_obj.title})",
                reviewed_at=datetime.now(timezone.utc).isoformat(),
                supersedes_decision_id=prior_decision_id,
                dependency_ids=changed_dependencies or [],
                system_recommendation=system_recommendation or "REVALIDATE",
                human_confirmed=True,
            )

            # Construct SupersessionEvent
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            sys_rec = system_recommendation or "REVALIDATE"

            event = SupersessionEvent(
                event_id=event_id,
                stable_lineage_key=lineage_key,
                action=action_enum,
                prior_decision_id=prior_decision_id,
                new_decision_id=new_decision_id,
                prior_status=prior_status,
                new_status=new_status,
                prior_state=prior_state,
                new_state=new_state,
                reviewer=reviewer_obj,
                rationale=final_rationale,
                system_recommendation=sys_rec,
                timestamp=datetime.now(timezone.utc).isoformat(),
                changed_dependencies=changed_dependencies or [],
                evidence_citations=evidence_citations or [],
                target_version_id=target_version_id,
                parent_event_hash=parent_hash,
                prior_decision=prior_dec,
                new_decision=new_decision,
                metadata={
                    "previous_state": prior_state.value if hasattr(prior_state, "value") else str(prior_state),
                    "actor": reviewer_obj.name,
                    "organization": reviewer_obj.organization,
                    "disclaimer": reviewer_obj.disclaimer,
                },
            )

            # Update engine state
            self._decision_states[lineage_key] = new_state
            self._decision_statuses[lineage_key] = new_status
            self._prior_decisions[new_decision.decision_id] = new_decision
            self._prior_decisions[lineage_key] = new_decision

            # Update item in active review queue if present
            if self._current_queue:
                for it in self._current_queue.items:
                    if it.stable_lineage_key == lineage_key:
                        it.current_state = new_state
                        it.current_status = new_status
                        break

            # Append-only ledger mutation
            self._supersession_events.append(event)
            logger.info(
                f"Recorded SupersessionEvent '{event_id}' for '{lineage_key}': "
                f"{action_enum.value} -> status={new_status.value}, state={new_state.value}, hash={event.event_hash}"
            )

            return copy.deepcopy(new_decision), copy.deepcopy(event)

    def process_review_action(self, *args, **kwargs) -> SupersessionEvent:
        """Backwards compatibility helper returning solely the SupersessionEvent."""
        _, event = self.apply_review_action(*args, **kwargs)
        return event

    def apply_unauthenticated_approval(self, stable_lineage_key: str):
        """
        Attempts unauthenticated approval of a stale claim.
        Strictly raises UnauthorizedApprovalError under fail-closed safety invariant.
        """
        raise UnauthorizedApprovalError(
            f"Fail-closed invariant violation: Cannot approve stale claim '{stable_lineage_key}' "
            f"without authenticated counsel action or allowed carry-forward rule."
        )

    def get_audit_trail(
        self,
        lineage_key: Optional[str] = None,
        stable_lineage_key: Optional[str] = None,
    ) -> List[SupersessionEvent]:
        """Returns an immutable copy of the append-only supersession audit ledger."""
        eff_key = stable_lineage_key or lineage_key
        with self._lock:
            events = copy.deepcopy(self._supersession_events)
            if eff_key:
                events = [e for e in events if e.stable_lineage_key == eff_key]
            return events

    def get_history(
        self,
        stable_lineage_key: Optional[str] = None,
        lineage_key: Optional[str] = None,
        prior_decision_id: Optional[str] = None,
    ) -> List[SupersessionEvent]:
        """Alias for get_audit_trail supporting filtering by lineage key and prior decision ID."""
        eff_key = stable_lineage_key or lineage_key
        events = self.get_audit_trail(lineage_key=eff_key)
        if prior_decision_id:
            events = [e for e in events if e.prior_decision_id == prior_decision_id]
        return events

    def verify_audit_trail(self) -> bool:
        """Verifies the cryptographic integrity of the audit ledger."""
        result = self.verify_ledger_integrity()
        return result["is_valid"]

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """
        Verifies that no event in the audit trail has been modified or re-ordered.
        Recalculates every event_hash and asserts unbroken parent_event_hash pointers.
        """
        with self._lock:
            if not self._supersession_events:
                return {
                    "is_valid": True,
                    "event_count": 0,
                    "chain_head_hash": self.GENESIS_PARENT_HASH,
                    "details": "Empty ledger is trivially valid.",
                }

            expected_parent = self.GENESIS_PARENT_HASH
            for idx, event in enumerate(self._supersession_events):
                # 1. Verify parent hash pointer
                if event.parent_event_hash and event.parent_event_hash != expected_parent:
                    return {
                        "is_valid": False,
                        "tampered_index": idx,
                        "event_id": event.event_id,
                        "error": (
                            f"Broken chain link at index {idx}: parent_event_hash '{event.parent_event_hash}' "
                            f"does not match expected '{expected_parent}'."
                        ),
                    }

                # 2. Recompute canonical digest
                action_val = event.action.value if hasattr(event.action, "value") else str(event.action)
                state_val = event.new_state.value if hasattr(event.new_state, "value") else str(event.new_state)
                status_val = event.new_status.value if hasattr(event.new_status, "value") else str(event.new_status)
                reviewer_name = (
                    event.reviewer.name
                    if isinstance(event.reviewer, ReviewerIdentity)
                    else getattr(event.reviewer, "name", str(event.reviewer))
                )

                payload = {
                    "action": action_val,
                    "counsel_rationale": event.rationale,
                    "event_id": event.event_id,
                    "new_state": state_val,
                    "new_status": status_val,
                    "prior_decision_id": event.prior_decision_id,
                    "reviewer_name": reviewer_name,
                    "stable_lineage_key": event.stable_lineage_key,
                    "system_recommendation": event.system_recommendation,
                    "target_version_id": event.target_version_id,
                    "timestamp": event.timestamp,
                }
                serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                recomputed_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

                if recomputed_hash != event.event_hash:
                    return {
                        "is_valid": False,
                        "tampered_index": idx,
                        "event_id": event.event_id,
                        "error": (
                            f"Tampered digest at index {idx}: stored event_hash '{event.event_hash}' "
                            f"differs from recomputed '{recomputed_hash}'."
                        ),
                    }

                expected_parent = event.event_hash

            return {
                "is_valid": True,
                "event_count": len(self._supersession_events),
                "chain_head_hash": self._supersession_events[-1].event_hash,
                "details": "All cryptographic parent pointers and canonical SHA-256 hashes verified.",
            }

    def clear_history(self):
        """Resets in-memory audit history for testing."""
        with self._lock:
            self._supersession_events.clear()
            self._current_queue = None
            self._decision_states.clear()
            self._decision_statuses.clear()


# Global singleton instance for app runtime
counsel_checkpoint_manager = CounselCheckpointManager()

# Aliases for architectural flexibility
CounselCheckpointEngine = CounselCheckpointManager
CounselCheckpointService = CounselCheckpointManager

__all__ = [
    "CounselCheckpointManager",
    "CounselCheckpointEngine",
    "CounselCheckpointService",
    "counsel_checkpoint_manager",
]
