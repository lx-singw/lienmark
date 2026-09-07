"""
backend/storage/policy_store_local.py

Thread-safe, filesystem-backed LocalPolicyStore for development and offline testing.
Stores immutable policy revisions, active-version pointer, overrides, and dispatch intents.
Path: output/policies/{org_id}/
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import copy
import glob
import os
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.storage.policy_store_types import (
    PolicyChangeDispatchIntent,
    PolicyConcurrencyError,
    PolicyStoreError,
    PolicyVersionRecord,
    atomic_write_json,
    compute_canonical_digest,
    detect_affected_rules,
    next_policy_version_id,
    read_json_file,
)


class LocalPolicyStore:
    """Filesystem-backed versioned policy store under output/policies/{org_id}/."""

    def __init__(self, base_dir: str = "output/policies", ledger: Optional[Any] = None) -> None:
        self._base_dir = os.path.normpath(base_dir)
        self._lock = threading.RLock()
        self._ledger = ledger

    def _org_dir(self, org_id: str) -> str:
        """Resolves root storage directory for a studio organization."""
        return os.path.join(self._base_dir, org_id.strip())

    def _record_ledger(
        self, org_id: str, prod_id: str, actor_id: str, action: str, payload: Dict[str, Any]
    ) -> str:
        """Appends audit event to cryptographic ledger, raising fail-closed if absent."""
        if self._ledger is None:
            raise PolicyStoreError("Mandatory audit ledger infrastructure is missing (fail-closed).")
        try:
            chains = getattr(self._ledger, "_chains", {})
            if prod_id not in chains or len(chains.get(prod_id, [])) == 0:
                self._ledger.initialize_production_ledger(
                    tenant_id=org_id, production_id=prod_id, actor_id=actor_id
                )
            event = self._ledger.append_event(
                tenant_id=org_id,
                production_id=prod_id,
                actor_id=actor_id,
                action_type=action,
                payload=payload,
            )
            if not event or not getattr(event, "event_id", None):
                raise PolicyStoreError("Ledger returned an invalid event without event_id.")
            return str(event.event_id)
        except Exception as exc:
            raise PolicyStoreError(f"Ledger audit append failed (fail-closed). Policy mutation requires an active CryptographicLedger: {exc}") from exc

    def _handle_idempotency(
        self, org_id: str, key: str
    ) -> Optional[Tuple[PolicyVersionRecord, PolicyChangeDispatchIntent]]:
        """Returns existing revision and intent if idempotency key has already committed."""
        idemp_path = os.path.join(self._org_dir(org_id), "idempotency", f"{key}.json")
        data = read_json_file(idemp_path)
        if not data:
            return None
        rec = self.get_policy_revision(org_id, data["version_id"])
        intent_path = os.path.join(self._org_dir(org_id), "intents", f"{data['intent_id']}.json")
        intent_data = read_json_file(intent_path)
        if rec and intent_data:
            return rec, PolicyChangeDispatchIntent.model_validate(intent_data)
        return None

    def _validate_precondition(
        self, org_id: str, expected_v: Optional[str]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Verifies version concurrency precondition and returns current version metadata."""
        org_dir = self._org_dir(org_id)
        active_data = read_json_file(os.path.join(org_dir, "active_version.json"))
        current_v = active_data.get("active_version") if active_data else None
        if expected_v is not None and current_v != expected_v:
            raise PolicyConcurrencyError(
                f"Concurrency mismatch: expected '{expected_v}', found '{current_v}'"
            )
        prior_rec = self.get_policy_revision(org_id, current_v) if current_v else None
        old_cfg = prior_rec.policy_config if prior_rec else None
        return current_v, old_cfg

    def save_policy_revision(
        self,
        org_id: str,
        config: Dict[str, Any],
        actor_id: str,
        idempotency_key: Optional[str] = None,
        expected_current_version: Optional[str] = None,
        action: str = "POLICY_UPDATED",
    ) -> Tuple[PolicyVersionRecord, PolicyChangeDispatchIntent]:
        """Atomically commits a new policy revision, active pointer, intent, and audit event."""
        with self._lock:
            if idempotency_key:
                existing = self._handle_idempotency(org_id, idempotency_key)
                if existing:
                    return existing

            current_v, old_cfg = self._validate_precondition(org_id, expected_current_version)
            version_id = str(config.get("version_id") or next_policy_version_id(current_v))
            policy_id = str(config.get("policy_id") or f"pol_{org_id}_{version_id}")
            digest = compute_canonical_digest(config)

            event_id = self._record_ledger(
                org_id=org_id, prod_id=f"policy_{org_id}", actor_id=actor_id,
                action=action, payload={"action": action, "org_id": org_id, "policy_id": policy_id, "version_id": version_id, "policy_digest": digest, "config": config},
            )
            record = PolicyVersionRecord(
                version_id=version_id, policy_id=policy_id, org_id=org_id,
                policy_config=copy.deepcopy(config), policy_digest=digest,
                created_by_actor_id=actor_id, ledger_event_id=event_id, idempotency_key=idempotency_key,
            )
            intent = PolicyChangeDispatchIntent(
                intent_id=f"intent_{uuid.uuid4().hex[:12]}", org_id=org_id,
                from_version=current_v, to_version=version_id, status="PENDING",
                affected_rules=detect_affected_rules(old_cfg, config),
            )
            self._commit_revision_files(self._org_dir(org_id), record, intent, idempotency_key)
            return record, intent

    def _commit_revision_files(
        self, org_dir: str, rec: PolicyVersionRecord, intent: PolicyChangeDispatchIntent, idemp_key: Optional[str]
    ) -> None:
        """Commits all atomic transaction files to disk."""
        atomic_write_json(os.path.join(org_dir, "revisions", f"{rec.version_id}.json"), rec.model_dump())
        atomic_write_json(os.path.join(org_dir, "intents", f"{intent.intent_id}.json"), intent.model_dump())
        atomic_write_json(os.path.join(org_dir, "active_version.json"), {
            "active_version": rec.version_id, "policy_id": rec.policy_id,
            "policy_digest": rec.policy_digest, "updated_at_utc": rec.created_at_utc,
            "ledger_event_id": rec.ledger_event_id,
        })
        if idemp_key:
            atomic_write_json(os.path.join(org_dir, "idempotency", f"{idemp_key}.json"), {"version_id": rec.version_id, "intent_id": intent.intent_id})

    def get_active_policy(self, org_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves current active policy revision for organization."""
        with self._lock:
            data = read_json_file(os.path.join(self._org_dir(org_id), "active_version.json"))
            if not data or "active_version" not in data:
                return None
            return self.get_policy_revision(org_id, data["active_version"])

    def get_policy_revision(self, org_id: str, version_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves specific immutable policy revision by version ID."""
        with self._lock:
            data = read_json_file(os.path.join(self._org_dir(org_id), "revisions", f"{version_id}.json"))
            if not data:
                return None
            return PolicyVersionRecord.model_validate(data)

    def save_production_override(self, org_id: str, prod_id: str, override: Dict[str, Any]) -> str:
        """Persists production-specific policy override with ledger entry."""
        with self._lock:
            to_save = copy.deepcopy(override)
            override_id = str(to_save.get("override_id") or f"ovr_{uuid.uuid4().hex[:12]}")
            actor_id = str(to_save.get("admin_actor_id") or to_save.get("actor_id") or "system_admin")
            to_save["override_id"] = override_id
            digest = compute_canonical_digest(to_save)
            to_save["override_digest"] = digest

            if not to_save.get("ledger_event_id") and self._ledger is not None:
                to_save["ledger_event_id"] = self._record_ledger(
                    org_id=org_id, prod_id=prod_id, actor_id=actor_id,
                    action="POLICY_OVERRIDE_SAVED", payload={"override_id": override_id, "digest": digest, "override": to_save},
                )
            atomic_write_json(os.path.join(self._org_dir(org_id), "overrides", f"{prod_id}.json"), to_save)
            return override_id

    def get_production_override(self, org_id: str, prod_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves active production override for specific production."""
        with self._lock:
            return read_json_file(os.path.join(self._org_dir(org_id), "overrides", f"{prod_id}.json"))

    def list_dispatch_intents(
        self, org_id: str, status: Optional[str] = None
    ) -> List[PolicyChangeDispatchIntent]:
        """Lists pending or filtered dispatch intents for an organization."""
        with self._lock:
            intents_dir = os.path.join(self._org_dir(org_id), "intents")
            if not os.path.isdir(intents_dir):
                return []
            results: List[PolicyChangeDispatchIntent] = []
            for fname in os.listdir(intents_dir):
                if fname.endswith(".json"):
                    data = read_json_file(os.path.join(intents_dir, fname))
                    if data:
                        intent = PolicyChangeDispatchIntent.model_validate(data)
                        if status is None or intent.status == status:
                            results.append(intent)
            results.sort(key=lambda x: x.created_at_utc)
            return results

    def update_dispatch_intent_status(self, intent_id: str, status: str) -> None:
        """Finds intent across organizations and updates its lifecycle status."""
        with self._lock:
            pattern = os.path.join(self._base_dir, "*", "intents", f"{intent_id}.json")
            matches = glob.glob(pattern)
            if not matches:
                raise PolicyStoreError(f"Dispatch intent '{intent_id}' not found.")
            data = read_json_file(matches[0])
            if not data:
                raise PolicyStoreError(f"Unreadable intent file '{matches[0]}'.")
            data["status"] = status
            atomic_write_json(matches[0], data)

    def rollback_revision(
        self, org_id: str, version_id: str, previous_version: Optional[str] = None
    ) -> None:
        """Rolls back an aborted revision to avoid phantom IDs on audit failure."""
        with self._lock:
            org_dir = self._org_dir(org_id)
            rev_p = os.path.join(org_dir, "revisions", f"{version_id}.json")
            if os.path.exists(rev_p):
                os.remove(rev_p)
            act_p = os.path.join(org_dir, "active_version.json")
            if previous_version:
                prev_rec = self.get_policy_revision(org_id, previous_version)
                if prev_rec:
                    atomic_write_json(act_p, {
                        "active_version": prev_rec.version_id, "policy_id": prev_rec.policy_id,
                        "policy_digest": prev_rec.policy_digest, "updated_at_utc": prev_rec.created_at_utc,
                    })
            elif os.path.exists(act_p):
                os.remove(act_p)

    def rollback_override(self, org_id: str, prod_id: str) -> None:
        """Removes uncommitted override to avoid phantom IDs."""
        with self._lock:
            ovr_p = os.path.join(self._org_dir(org_id), "overrides", f"{prod_id}.json")
            if os.path.exists(ovr_p):
                os.remove(ovr_p)
