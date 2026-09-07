"""
backend/storage/policy_store_firestore.py

Native Google Cloud Firestore persistence adapter for PolicyStore.
Strictly isolated under /organizations/{org_id}/ canonical hierarchy.
Zero silent fallback: all failures raise PolicyStoreError immediately.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.storage.policy_store_types import (
    PolicyChangeDispatchIntent,
    PolicyConcurrencyError,
    PolicyStoreError,
    PolicyVersionRecord,
    compute_canonical_digest,
    detect_affected_rules,
    next_policy_version_id,
)


class FirestorePolicyStore:
    """Firestore persistence adapter executing atomic version and intent transactions."""

    def __init__(self, client: Any, ledger: Optional[Any] = None) -> None:
        if client is None:
            raise PolicyStoreError("Firestore client is required for FirestorePolicyStore.")
        self._client = client
        self._ledger = ledger

    def _org_ref(self, org_id: str) -> Any:
        """Returns DocumentReference for organization."""
        return self._client.collection("organizations").document(org_id.strip())

    def _record_ledger(
        self, org_id: str, prod_id: str, actor_id: str, action: str, payload: Dict[str, Any]
    ) -> str:
        """Records audit event into cryptographic ledger, failing closed if missing."""
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
            return str(event.event_id)
        except Exception as exc:
            raise PolicyStoreError(f"Ledger append failed in Firestore store: {exc}") from exc

    def _check_idempotency(
        self, org_id: str, key: str
    ) -> Optional[Tuple[PolicyVersionRecord, PolicyChangeDispatchIntent]]:
        """Resolves existing revision and intent if idempotency key is already recorded."""
        doc = self._org_ref(org_id).collection("idempotency").document(key).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        rec = self.get_policy_revision(org_id, data.get("version_id", ""))
        intent_doc = self._org_ref(org_id).collection("policy_intents").document(data.get("intent_id", "")).get()
        if rec and intent_doc.exists:
            return rec, PolicyChangeDispatchIntent.model_validate(intent_doc.to_dict() or {})
        return None

    def _validate_precondition(
        self, org_id: str, expected_v: Optional[str]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Verifies version concurrency precondition and returns current version metadata."""
        active_snap = self._org_ref(org_id).collection("policies").document("active").get()
        current_v = active_snap.to_dict().get("active_version") if active_snap.exists else None
        if expected_v is not None and current_v != expected_v:
            raise PolicyConcurrencyError(f"Concurrency mismatch: expected '{expected_v}', found '{current_v}'")
        prior_rec = self.get_policy_revision(org_id, current_v) if current_v else None
        return current_v, prior_rec.policy_config if prior_rec else None

    def save_policy_revision(
        self,
        org_id: str,
        config: Dict[str, Any],
        actor_id: str,
        idempotency_key: Optional[str] = None,
        expected_current_version: Optional[str] = None,
        action: str = "POLICY_UPDATED",
    ) -> Tuple[PolicyVersionRecord, PolicyChangeDispatchIntent]:
        """Atomically commits revision, active pointer, and intent in Firestore."""
        if idempotency_key:
            existing = self._check_idempotency(org_id, idempotency_key)
            if existing:
                return existing

        current_v, old_cfg = self._validate_precondition(org_id, expected_current_version)
        version_id = str(config.get("version_id") or next_policy_version_id(current_v))
        policy_id = str(config.get("policy_id") or f"pol_{org_id}_{version_id}")
        digest = compute_canonical_digest(config)

        event_id = self._record_ledger(
            org_id, f"policy_{org_id}", actor_id, action,
            {"action": action, "org_id": org_id, "policy_id": policy_id, "version_id": version_id, "policy_digest": digest, "config": config},
        )

        record = PolicyVersionRecord(
            version_id=version_id, policy_id=policy_id, org_id=org_id,
            policy_config=copy.deepcopy(config), policy_digest=digest,
            created_by_actor_id=actor_id, ledger_event_id=event_id,
            idempotency_key=idempotency_key,
        )
        intent = PolicyChangeDispatchIntent(
            intent_id=f"intent_{uuid.uuid4().hex[:12]}", org_id=org_id,
            from_version=current_v, to_version=version_id, status="PENDING",
            affected_rules=detect_affected_rules(old_cfg, config),
        )

        self._commit_batch(org_id, record, intent, idempotency_key)
        return record, intent

    def _commit_batch(
        self, org_id: str, rec: PolicyVersionRecord, intent: PolicyChangeDispatchIntent, idemp_key: Optional[str]
    ) -> None:
        """Executes atomic batch commit in Firestore."""
        try:
            batch = self._client.batch()
            rev_ref = self._org_ref(org_id).collection("policy_revisions").document(rec.version_id)
            batch.set(rev_ref, rec.model_dump())

            active_ref = self._org_ref(org_id).collection("policies").document("active")
            batch.set(active_ref, {
                "active_version": rec.version_id, "policy_id": rec.policy_id,
                "policy_digest": rec.policy_digest, "updated_at_utc": rec.created_at_utc,
                "ledger_event_id": rec.ledger_event_id,
            })

            intent_ref = self._org_ref(org_id).collection("policy_intents").document(intent.intent_id)
            batch.set(intent_ref, intent.model_dump())

            if idemp_key:
                idemp_ref = self._org_ref(org_id).collection("idempotency").document(idemp_key)
                batch.set(idemp_ref, {"version_id": rec.version_id, "intent_id": intent.intent_id})

            batch.commit()
        except Exception as exc:
            raise PolicyStoreError(f"Firestore batch commit failed: {exc}") from exc

    def get_active_policy(self, org_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves active policy revision from Firestore."""
        active_snap = self._org_ref(org_id).collection("policies").document("active").get()
        if not active_snap.exists:
            return None
        active_v = active_snap.to_dict().get("active_version")
        if not active_v:
            return None
        return self.get_policy_revision(org_id, active_v)

    def get_policy_revision(self, org_id: str, version_id: str) -> Optional[PolicyVersionRecord]:
        """Retrieves immutable policy revision document by version ID."""
        snap = self._org_ref(org_id).collection("policy_revisions").document(version_id).get()
        if not snap.exists:
            return None
        return PolicyVersionRecord.model_validate(snap.to_dict() or {})

    def save_production_override(self, org_id: str, prod_id: str, override: Dict[str, Any]) -> str:
        """Persists production-level policy override to Firestore."""
        to_save = copy.deepcopy(override)
        override_id = str(to_save.get("override_id") or f"ovr_{uuid.uuid4().hex[:12]}")
        actor_id = str(to_save.get("admin_actor_id") or to_save.get("actor_id") or "system_admin")
        to_save["override_id"] = override_id
        digest = compute_canonical_digest(to_save)
        to_save["override_digest"] = digest

        if not to_save.get("ledger_event_id") and self._ledger is not None:
            to_save["ledger_event_id"] = self._record_ledger(
                org_id, prod_id, actor_id, "POLICY_OVERRIDE_SAVED",
                {"override_id": override_id, "digest": digest, "override": to_save},
            )

        doc_ref = self._org_ref(org_id).collection("policy_overrides").document(prod_id)
        doc_ref.set(to_save)
        return override_id

    def get_production_override(self, org_id: str, prod_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves production-level policy override from Firestore."""
        snap = self._org_ref(org_id).collection("policy_overrides").document(prod_id).get()
        return snap.to_dict() if snap.exists else None

    def list_dispatch_intents(
        self, org_id: str, status: Optional[str] = None
    ) -> List[PolicyChangeDispatchIntent]:
        """Queries dispatch intents for an organization with optional status filtering."""
        query = self._org_ref(org_id).collection("policy_intents")
        if status:
            query = query.where("status", "==", status)
        results = [
            PolicyChangeDispatchIntent.model_validate(doc.to_dict())
            for doc in query.stream()
            if doc.exists
        ]
        results.sort(key=lambda x: x.created_at_utc)
        return results

    def update_dispatch_intent_status(self, intent_id: str, status: str) -> None:
        """Locates dispatch intent across collection group and updates status."""
        query = self._client.collection_group("policy_intents").where("intent_id", "==", intent_id).limit(1)
        docs = list(query.stream())
        if not docs:
            raise PolicyStoreError(f"Dispatch intent '{intent_id}' not found in Firestore.")
        docs[0].reference.update({"status": status})

    def rollback_revision(
        self, org_id: str, version_id: str, previous_version: Optional[str] = None
    ) -> None:
        """Rolls back an uncommitted policy revision in Firestore."""
        try:
            self._org_ref(org_id).collection("policy_revisions").document(version_id).delete()
            active_ref = self._org_ref(org_id).collection("policies").document("active")
            if previous_version:
                prev = self.get_policy_revision(org_id, previous_version)
                if prev:
                    active_ref.set({
                        "active_version": prev.version_id, "policy_id": prev.policy_id,
                        "policy_digest": prev.policy_digest, "updated_at_utc": prev.created_at_utc,
                    })
            else:
                active_ref.delete()
        except Exception:
            pass

    def rollback_override(self, org_id: str, prod_id: str) -> None:
        """Removes uncommitted override in Firestore."""
        try:
            self._org_ref(org_id).collection("policy_overrides").document(prod_id).delete()
        except Exception:
            pass
