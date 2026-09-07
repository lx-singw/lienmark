"""
backend/core/policy_engine.py

Core Studio Policy Inheritance Engine.
Sprint 5.1 / 5.2 - Studio Policy Inheritance, PolicyStore & Ledger Governance.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional, Tuple

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
from backend.storage.policy_store import PolicyStore, get_policy_store
from backend.storage.policy_store_types import (
    PolicyStoreError,
    PolicyStoreMode,
    compute_canonical_digest,
)

_GLOBAL_POLICY_ENGINE: Optional[StudioPolicyEngine] = None
_GLOBAL_ENGINE_LOCK = threading.RLock()
_DEFAULT_LEDGER = object()


def get_policy_engine() -> StudioPolicyEngine:
    """Returns or creates the process-wide StudioPolicyEngine singleton."""
    global _GLOBAL_POLICY_ENGINE
    with _GLOBAL_ENGINE_LOCK:
        if _GLOBAL_POLICY_ENGINE is None:
            active_ledger = CryptographicLedger()
            active_store = get_policy_store(ledger=active_ledger)
            _GLOBAL_POLICY_ENGINE = StudioPolicyEngine(ledger=active_ledger, policy_store=active_store)
        return _GLOBAL_POLICY_ENGINE


class StudioPolicyEngine:
    """
    Core engine managing studio policy inheritance, overrides, RBAC,
    immutable ledger audit dispatch, and statutory claim evaluations.
    """

    def __init__(
        self,
        firestore_adapter: Optional[Any] = None,
        ledger: Any = _DEFAULT_LEDGER,
        policy_store: Optional[Any] = None,
        store_mode: PolicyStoreMode = PolicyStoreMode.LOCAL_DISK,
        policies_dir: str = "output/policies",
        store: Optional[Any] = None,
    ) -> None:
        self._firestore = firestore_adapter
        if ledger is _DEFAULT_LEDGER:
            self._ledger = getattr(store or policy_store, "_ledger", None) or CryptographicLedger()
        else:
            self._ledger = ledger
        self._lock = threading.RLock()
        self._studio_policies: Dict[str, StudioPolicyConfig] = {}
        self._production_overrides: Dict[str, ProductionPolicyOverride] = {}
        eff_store = store or policy_store
        if eff_store is not None:
            self._policy_store = eff_store
        elif firestore_adapter and isinstance(firestore_adapter, PolicyStore):
            self._policy_store = firestore_adapter
        elif store_mode == PolicyStoreMode.FIRESTORE or (firestore_adapter and hasattr(firestore_adapter, "collection")):
            self._policy_store = PolicyStore(mode=PolicyStoreMode.FIRESTORE, firestore_client=firestore_adapter, base_dir=policies_dir, ledger=self._ledger)
        else:
            self._policy_store = PolicyStore(mode=PolicyStoreMode.LOCAL_DISK, base_dir=policies_dir, ledger=self._ledger)

    def get_studio_policy(self, org_id: str) -> StudioPolicyConfig:
        """Retrieves studio baseline policy, defaulting to MAJOR_THEATRICAL if unset."""
        with self._lock:
            if org_id in self._studio_policies:
                return self._studio_policies[org_id]
            persisted = self._policy_store.get_active_policy(org_id)
            if persisted is not None:
                pol = StudioPolicyConfig.model_validate(persisted.policy_config)
                self._studio_policies[org_id] = pol
                return pol
            default_pol = get_preset_profile_policy(org_id, StudioProfileType.MAJOR_THEATRICAL)
            self._studio_policies[org_id] = default_pol
            return default_pol

    def get_active_version(self, org_id: str) -> Optional[str]:
        """Returns the active policy version identifier."""
        active = self._policy_store.get_active_policy(org_id)
        return active.version_id if active else None

    def get_policy_digest(self, org_id: str) -> Optional[str]:
        """Returns the canonical digest for active studio policy."""
        active = self._policy_store.get_active_policy(org_id)
        return active.policy_digest if active else None

    def get_audit_lineage(self, org_id: str) -> List[Any]:
        """Returns audit events for policy mutations."""
        active = self._ledger or getattr(self._policy_store, "_ledger", None) or getattr(getattr(self._policy_store, "_adapter", None), "_ledger", None)
        return (active.get_events(f"policy_{org_id}") or active.get_events(org_id)) if active else []

    def get_effective_policy(self, org_id: str, production_id: str) -> StudioPolicyConfig:
        """Computes effective policy by merging studio baseline with production overrides."""
        with self._lock:
            base_policy = self.get_studio_policy(org_id)
            key = f"{org_id}:{production_id}"
            override = self._production_overrides.get(key)
            if override is None:
                persisted = self._policy_store.get_production_override(org_id, production_id)
                if persisted is not None:
                    override = ProductionPolicyOverride.model_validate(persisted)
                    self._production_overrides[key] = override
            return resolve_effective_policy(base_policy, override)

    def _verify_admin_role(self, actor_role: Any) -> None:
        """Validates that principal possesses authorized Admin privileges."""
        norm_role = LienmarkRole.normalize(actor_role) if hasattr(LienmarkRole, "normalize") else None
        is_admin = (
            actor_role == LienmarkRole.ADMIN or norm_role == LienmarkRole.ADMIN
            or str(actor_role).lower().strip() in ("admin", "admins", "studio_executive", "lead_admin", "studio_admin", "production_admin", "superadmin", "administrator")
        )
        if not is_admin:
            raise PermissionError("Production policy override requires Admin role sign-off.")

    def _verify_admin_authority(
        self, actor_role: Any, org_id: str, prod_id: str, override: ProductionPolicyOverride
    ) -> None:
        """Validates admin role and target production scope authority."""
        self._verify_admin_role(actor_role)
        if override.org_id != org_id or override.production_id != prod_id:
            raise PermissionError("Production policy override requires Admin role sign-off for target production scope.")

    def set_studio_policy(
        self, policy: StudioPolicyConfig, actor_id: Optional[str] = None, ledger: Any = _DEFAULT_LEDGER,
    ) -> StudioPolicyConfig:
        """Sets studio policy committing revision, pointer, and intent with mandatory ledger."""
        active_ledger = self._ledger if ledger is _DEFAULT_LEDGER else ledger
        if active_ledger is None:
            raise PolicyStoreError(
                "Policy mutation requires an active CryptographicLedger. Mandatory audit ledger infrastructure is missing (fail-closed)."
            )
        actor = actor_id or "system_admin"
        with self._lock:
            if hasattr(self._policy_store, "_adapter"):
                self._policy_store._adapter._ledger = active_ledger
            setattr(self._policy_store, "_ledger", active_ledger)
            try:
                rec, intent = self._policy_store.save_policy_revision(
                    policy.org_id, policy.model_dump(), actor, action="POLICY_UPDATED"
                )
            except Exception as exc:
                if hasattr(self._policy_store, "rollback_revision"):
                    self._policy_store.rollback_revision(policy.org_id, f"pol_{policy.org_id}", None)
                self._studio_policies.pop(policy.org_id, None)
                raise PolicyStoreError(
                    f"Policy mutation requires an active CryptographicLedger. Ledger audit append failed (fail-closed): {exc}"
                ) from exc
            self._studio_policies[policy.org_id] = policy
            return policy

    @staticmethod
    def _build_override_payload(
        org_id: str, prod_id: str, ovr: ProductionPolicyOverride, role: str, base: StudioPolicyConfig, eff: StudioPolicyConfig,
    ) -> Dict[str, Any]:
        """Constructs audit payload and diff for policy override event."""
        return {
            "action": "POLICY_OVERRIDE", "override_id": ovr.override_id, "production_id": prod_id, "org_id": org_id,
            "actor_id": ovr.admin_actor_id, "actor_name": ovr.admin_actor_name, "actor_role": str(role),
            "rationale": ovr.rationale, "waiver_notes": ovr.waiver_notes,
            "diff": {
                "before_scopes": [s.value for s in base.required_media_scopes], "after_scopes": [s.value for s in eff.required_media_scopes],
                "before_territories": [t.value for t in base.distribution_territories], "after_territories": [t.value for t in eff.distribution_territories],
                "before_prohibit_tm": base.prohibit_unvetted_trademark_fair_use, "after_prohibit_tm": eff.prohibit_unvetted_trademark_fair_use,
            },
        }

    def _dispatch_override_ledger_event(
        self, org_id: str, prod_id: str, override: ProductionPolicyOverride, actor_role: str,
        base_policy: StudioPolicyConfig, new_effective: StudioPolicyConfig, ledger: CryptographicLedger,
    ) -> None:
        """Records tamper-evident POLICY_OVERRIDE event into cryptographic ledger."""
        chains = getattr(ledger, "_chains", {})
        if prod_id not in chains or len(chains.get(prod_id, [])) == 0:
            ledger.initialize_production_ledger(tenant_id=org_id, production_id=prod_id, actor_id=override.admin_actor_id)
        payload = self._build_override_payload(org_id, prod_id, override, actor_role, base_policy, new_effective)
        event = ledger.append_event(
            tenant_id=org_id, production_id=prod_id, actor_id=override.admin_actor_id,
            action_type="POLICY_OVERRIDE", payload=payload,
        )
        override.ledger_event_id = event.event_id

    def apply_production_override(
        self, org_id: str, prod_id: str = "", override: Optional[ProductionPolicyOverride] = None,
        actor_role: str = "admin", ledger: Any = _DEFAULT_LEDGER, production_id: Optional[str] = None,
    ) -> StudioPolicyConfig:
        """Applies production override after admin scope verification and ledger audit."""
        target_prod = prod_id or production_id or (override.production_id if override else "")
        if override is None:
            raise ValueError("Override payload is required.")
        self._verify_admin_authority(actor_role, org_id, target_prod, override)
        active_ledger = self._ledger if ledger is _DEFAULT_LEDGER else ledger
        if active_ledger is None:
            raise PolicyStoreError("Policy override requires an active CryptographicLedger. Mandatory audit ledger infrastructure is missing (fail-closed).")
        with self._lock:
            base_policy = self.get_studio_policy(org_id)
            new_effective = resolve_effective_policy(base_policy, override)
            if hasattr(self._policy_store, "_adapter"):
                self._policy_store._adapter._ledger = active_ledger
            try:
                self._dispatch_override_ledger_event(org_id, target_prod, override, actor_role, base_policy, new_effective, active_ledger)
                self._policy_store.save_override(override, actor_role=actor_role, ledger=active_ledger)
            except Exception as exc:
                self._policy_store.rollback_override(org_id, target_prod)
                self._production_overrides.pop(f"{org_id}:{target_prod}", None)
                raise PolicyStoreError(f"Policy override requires an active CryptographicLedger. Ledger audit append failed (fail-closed): {exc}") from exc
            self._production_overrides[f"{org_id}:{target_prod}"] = override
            return new_effective

    def evaluate_claim(
        self, claim: Any, org_id: str, prod_id: str = "", production_id: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """Evaluates claim against effective policy returning 4-state result with provenance."""
        target_prod = prod_id or production_id or ""
        effective_policy = self.get_effective_policy(org_id, target_prod)
        result = evaluate_claim_against_policy(claim, effective_policy)
        override = self._production_overrides.get(f"{org_id}:{target_prod}")
        result.provenance = {
            "org_id": org_id, "production_id": target_prod, "policy_id": effective_policy.policy_id,
            "version": getattr(effective_policy, "version", "1.0"), "policy_digest": getattr(result, "effective_policy_digest", ""),
            "evaluated_at_utc": datetime.now(timezone.utc).isoformat(), "has_override": override is not None,
            "override_id": override.override_id if override else None,
        }
        return result
