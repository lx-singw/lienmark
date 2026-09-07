"""
backend/core/policy_engine.py

Core Studio Policy Inheritance Engine.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from backend.core.policy_rules import (
    evaluate_claim_against_policy,
    get_preset_profile_policy,
    resolve_effective_policy,
)
from backend.core.policy_types import (
    PolicyEvaluationResult,
    ProductionPolicyOverride,
    StudioPolicyConfig,
    StudioProfileType,
)
from backend.core.rbac import LienmarkRole
from backend.storage.ledger import CryptographicLedger


_GLOBAL_POLICY_ENGINE: Optional[StudioPolicyEngine] = None
_GLOBAL_ENGINE_LOCK = threading.RLock()


def get_policy_engine() -> StudioPolicyEngine:
    """Returns or creates the process-wide StudioPolicyEngine singleton."""
    global _GLOBAL_POLICY_ENGINE
    with _GLOBAL_ENGINE_LOCK:
        if _GLOBAL_POLICY_ENGINE is None:
            _GLOBAL_POLICY_ENGINE = StudioPolicyEngine()
        return _GLOBAL_POLICY_ENGINE


class StudioPolicyEngine:
    """
    Core engine managing studio policy inheritance, overrides, RBAC,
    immutable ledger audit dispatch, and statutory claim evaluations.
    """

    def __init__(
        self,
        firestore_adapter: Optional[Any] = None,
        ledger: Optional[CryptographicLedger] = None,
    ) -> None:
        self._firestore = firestore_adapter
        self._ledger = ledger
        self._studio_policies: Dict[str, StudioPolicyConfig] = {}
        self._production_overrides: Dict[str, ProductionPolicyOverride] = {}
        self._lock = threading.RLock()

    def set_studio_policy(self, policy: StudioPolicyConfig) -> StudioPolicyConfig:
        """Sets or updates the baseline policy for a studio organization."""
        with self._lock:
            self._studio_policies[policy.org_id] = policy
            if self._firestore and hasattr(self._firestore, "save_policy"):
                self._firestore.save_policy(policy)
            return policy

    def get_studio_policy(self, org_id: str) -> StudioPolicyConfig:
        """Retrieves studio baseline policy, defaulting to MAJOR_THEATRICAL if unset."""
        with self._lock:
            if org_id in self._studio_policies:
                return self._studio_policies[org_id]
            if self._firestore and hasattr(self._firestore, "get_policy"):
                persisted = self._firestore.get_policy(org_id)
                if persisted is not None:
                    self._studio_policies[org_id] = persisted
                    return persisted
            default_pol = get_preset_profile_policy(org_id, StudioProfileType.MAJOR_THEATRICAL)
            self._studio_policies[org_id] = default_pol
            return default_pol

    def get_effective_policy(self, org_id: str, production_id: str) -> StudioPolicyConfig:
        """Computes effective policy by merging studio baseline with production overrides."""
        with self._lock:
            base_policy = self.get_studio_policy(org_id)
            key = f"{org_id}:{production_id}"
            override = self._production_overrides.get(key)
            if override is None and self._firestore and hasattr(self._firestore, "get_override"):
                override = self._firestore.get_override(org_id, production_id)
                if override is not None:
                    self._production_overrides[key] = override
            return resolve_effective_policy(base_policy, override)

    def _verify_admin_role(self, actor_role: Any) -> None:
        """Validates that principal possesses authorized Admin privileges."""
        norm_role = LienmarkRole.normalize(actor_role) if hasattr(LienmarkRole, "normalize") else None
        is_admin = (
            actor_role == LienmarkRole.ADMIN
            or norm_role == LienmarkRole.ADMIN
            or str(actor_role).lower().strip() in ("admin", "studio_executive", "lead_admin")
        )
        if not is_admin:
            raise PermissionError("Production policy override requires Admin role sign-off.")

    @staticmethod
    def _build_override_payload(
        org_id: str,
        production_id: str,
        override: ProductionPolicyOverride,
        actor_role: str,
        base_policy: StudioPolicyConfig,
        new_effective: StudioPolicyConfig,
    ) -> Dict[str, Any]:
        """Constructs audit payload and diff for policy override event."""
        return {
            "action": "POLICY_OVERRIDE",
            "override_id": override.override_id,
            "production_id": production_id,
            "org_id": org_id,
            "actor_id": override.admin_actor_id,
            "actor_name": override.admin_actor_name,
            "actor_role": str(actor_role),
            "rationale": override.rationale,
            "waiver_notes": override.waiver_notes,
            "diff": {
                "before_scopes": [s.value for s in base_policy.required_media_scopes],
                "after_scopes": [s.value for s in new_effective.required_media_scopes],
                "before_territories": [t.value for t in base_policy.distribution_territories],
                "after_territories": [t.value for t in new_effective.distribution_territories],
                "before_prohibit_tm": base_policy.prohibit_unvetted_trademark_fair_use,
                "after_prohibit_tm": new_effective.prohibit_unvetted_trademark_fair_use,
            },
        }

    def _dispatch_override_ledger_event(
        self,
        org_id: str,
        production_id: str,
        override: ProductionPolicyOverride,
        actor_role: str,
        base_policy: StudioPolicyConfig,
        new_effective: StudioPolicyConfig,
        ledger: Optional[CryptographicLedger],
    ) -> None:
        """Records tamper-evident POLICY_OVERRIDE event into the cryptographic ledger."""
        active_ledger = ledger or self._ledger
        if active_ledger is None:
            return

        chains = getattr(active_ledger, "_chains", {})
        if production_id not in chains or len(chains.get(production_id, [])) == 0:
            active_ledger.initialize_production_ledger(
                tenant_id=org_id, production_id=production_id, actor_id=override.admin_actor_id,
            )

        payload = self._build_override_payload(
            org_id, production_id, override, actor_role, base_policy, new_effective,
        )
        event = active_ledger.append_event(
            tenant_id=org_id, production_id=production_id, actor_id=override.admin_actor_id,
            action_type="POLICY_OVERRIDE", payload=payload,
        )
        override.ledger_event_id = event.event_id

    def apply_production_override(
        self,
        org_id: str,
        production_id: str,
        override: ProductionPolicyOverride,
        actor_role: str,
        ledger: Optional[Any] = None,
    ) -> StudioPolicyConfig:
        """Applies production override after strict RBAC check and ledger event logging."""
        with self._lock:
            self._verify_admin_role(actor_role)
            base_policy = self.get_studio_policy(org_id)
            new_effective = resolve_effective_policy(base_policy, override)

            self._dispatch_override_ledger_event(
                org_id=org_id, production_id=production_id, override=override,
                actor_role=actor_role, base_policy=base_policy,
                new_effective=new_effective, ledger=ledger,
            )

            key = f"{org_id}:{production_id}"
            self._production_overrides[key] = override
            if self._firestore and hasattr(self._firestore, "save_override"):
                self._firestore.save_override(override)
            return new_effective

    def evaluate_claim(
        self,
        claim: Any,
        org_id: str,
        production_id: str,
    ) -> PolicyEvaluationResult:
        """Evaluates a claim against the merged effective policy for an org and production."""
        effective_policy = self.get_effective_policy(org_id, production_id)
        return evaluate_claim_against_policy(claim, effective_policy)
