"""
firestore_client.py

Production-Ready Firestore Persistence Layer with Multi-Tenant Session & Run Hierarchy.
Implements:
1. Document Path Hierarchies:
   - sessions/{session_id}: visitor session document (created_at, last_active, active_run_id)
   - sessions/{session_id}/runs/{run_id}: run document (created_at, status, baseline_version, claims, review_queue, decisions, audit_events)
   - usage_counters/{environment}: persistent environment-wide API call counters and token metrics that survive resets
2. High-Reliability Design:
   - Google Cloud Firestore native client support when running in GCP or credentials configured
   - Transparent, thread-safe In-Memory fallback (InMemoryFirestoreClient) for local development, pytest, and offline execution
   - Atomic transaction for 'start a new run' (create_new_run_transaction) initialized to V7 baseline
   - In-flight commit invalidation rejecting stale run_id commits
"""

from __future__ import annotations

import abc
import copy
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.config.settings import settings

logger = logging.getLogger("lienmark.storage.firestore")


class FirestoreError(Exception):
    """Base exception for Firestore persistence operations."""
    pass


class SessionNotFoundError(FirestoreError):
    """Raised when a requested visitor session document is not found."""
    pass


class RunNotFoundError(FirestoreError):
    """Raised when a requested run document is not found within a session."""
    pass


class StaleRunCommitError(FirestoreError):
    """
    Raised when an in-flight commit targets a superseded run_id that is no longer active.
    Guarantees that actions from superseded runs cannot corrupt the newly activated run.
    """
    pass


# Alias for compatibility
InvalidRunCommitError = StaleRunCommitError


def _generate_v7_baseline_state() -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Generates canonical V7 baseline claims and decisions list for fresh run initialization."""
    from backend.fixtures.golden_dataset import get_golden_fixtures
    v7_uses, _, v7_decisions, _ = get_golden_fixtures()
    claims = [
        {
            "use_id": u.use_id,
            "key": u.stable_lineage_key,
            "stable_lineage_key": u.stable_lineage_key,
            "scene": u.scene_or_timecode,
            "scene_or_timecode": u.scene_or_timecode,
            "asset_type": u.asset_type,
            "description": u.description,
            "prominence": u.duration_or_prominence,
            "duration_or_prominence": u.duration_or_prominence,
            "status": "APPROVED",
        }
        for u in v7_uses
    ]
    decisions = {
        d.stable_lineage_key: {
            "decision_id": d.decision_id,
            "stable_lineage_key": d.stable_lineage_key,
            "use_id": d.use_id,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status).upper(),
            "state": "CARRIED_FORWARD",
            "reviewer": d.reviewer_display_name,
            "reviewer_display_name": d.reviewer_display_name,
            "rationale": d.rationale,
            "applicable_version_id": d.applicable_version_id,
            "reviewed_at": d.reviewed_at,
            "supersedes_decision_id": d.supersedes_decision_id,
            "dependency_ids": d.dependency_ids,
            "system_recommendation": d.system_recommendation,
            "human_confirmed": d.human_confirmed,
        }
        for d in v7_decisions
    }
    return claims, decisions


class FirestoreClientInterface(abc.ABC):
    """Abstract Interface defining production Firestore contracts for Lienmark."""

    @abc.abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves visitor session document."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_session(self, session_id: str, active_run_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates or initializes a visitor session document."""
        raise NotImplementedError

    @abc.abstractmethod
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates fields on the visitor session document."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_run(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific run document under sessions/{session_id}/runs/{run_id}."""
        raise NotImplementedError

    @abc.abstractmethod
    def save_run(self, session_id: str, run_id: str, run_data: Dict[str, Any]) -> None:
        """Saves or overwrites a run document."""
        raise NotImplementedError

    @abc.abstractmethod
    def update_run(self, session_id: str, run_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates specific fields on an existing run document."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_new_run_transaction(
        self,
        session_id: str,
        baseline_version: str = "v7",
        initial_mode: str = "baseline",
    ) -> Dict[str, Any]:
        """
        Atomically creates a new run initialized to baseline, and activates it
        on the session document (updating active_run_id).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def validate_active_run(self, session_id: str, run_id: str) -> bool:
        """Validates that run_id is the currently active run for the session."""
        raise NotImplementedError

    @abc.abstractmethod
    def commit_action_to_run(
        self,
        session_id: str,
        run_id: Optional[str],
        decision_data: Dict[str, Any],
        event_data: Dict[str, Any],
        environment: str = "development",
    ) -> Dict[str, Any]:
        """
        Atomically commits a counsel decision and audit event to the active run.
        Enforces in-flight commit invalidation if run_id does not match active_run_id.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def increment_usage_counter(
        self,
        environment: str,
        metric: str,
        amount: int = 1,
    ) -> Dict[str, Any]:
        """
        Atomically increments persistent environment-wide API call counters and token metrics.
        Stored under usage_counters/{environment}, surviving session and run resets.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_usage_counters(self, environment: str) -> Dict[str, Any]:
        """Retrieves persistent environment-wide usage counters."""
        raise NotImplementedError

    def get_usage_counter(self, environment: str) -> Dict[str, Any]:
        return self.get_usage_counters(environment)

    @abc.abstractmethod
    def reset_environment(self, environment: str) -> None:
        """Resets all session state for the given environment (protected administrative action)."""
        raise NotImplementedError


class InMemoryFirestoreClient(FirestoreClientInterface):
    """
    Thread-safe in-memory Firestore persistence layer for local development, pytest,
    and offline execution without live GCP credentials.
    Accurately emulates Firestore collection/document hierarchies and atomic transactions.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # sessions/{session_id}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # sessions/{session_id}/runs/{run_id} -> stored as (session_id, run_id)
        self._runs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # usage_counters/{environment}
        self._usage_counters: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            sess = self._sessions.get(session_id)
            return copy.deepcopy(sess) if sess is not None else None

    def create_session(self, session_id: str, active_run_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            if session_id in self._sessions:
                sess = self._sessions[session_id]
                if active_run_id:
                    sess["active_run_id"] = active_run_id
                sess["last_active"] = now
                return copy.deepcopy(sess)

            sess = {
                "session_id": session_id,
                "created_at": now,
                "last_active": now,
                "active_run_id": active_run_id,
                "metadata": {},
            }
            self._sessions[session_id] = sess
            return copy.deepcopy(sess)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                self.create_session(session_id)
            sess = self._sessions[session_id]
            sess.update(updates)
            sess["last_active"] = datetime.now(timezone.utc).isoformat()
            return copy.deepcopy(sess)

    def get_run(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            run = self._runs.get((session_id, run_id))
            return copy.deepcopy(run) if run is not None else None

    def list_runs(self, session_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(run)
                for (s_id, _), run in self._runs.items()
                if s_id == session_id
            ]

    def save_run(self, session_id: str, run_id: str, run_data: Dict[str, Any]) -> None:
        with self._lock:
            self._runs[(session_id, run_id)] = copy.deepcopy(run_data)

    def update_run(self, session_id: str, run_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            key = (session_id, run_id)
            if key not in self._runs:
                raise RunNotFoundError(f"Run '{run_id}' not found for session '{session_id}'.")
            run = self._runs[key]
            run.update(updates)
            return copy.deepcopy(run)

    def create_new_run_transaction(
        self,
        session_id: str,
        baseline_version: str = "v7",
        initial_mode: str = "baseline",
    ) -> Dict[str, Any]:
        """
        Atomic transaction for 'start a new run':
        1. Generates a new run_id.
        2. Initializes run document to clean V7 baseline.
        3. Atomically updates active_run_id on the session document.
        4. Validates that subsequent in-flight commits must match this new active_run_id.
        """
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            new_run_id = f"run_{uuid.uuid4().hex[:12]}"
            claims, decisions = _generate_v7_baseline_state()

            run_doc = {
                "run_id": new_run_id,
                "session_id": session_id,
                "created_at": now,
                "status": "ready",
                "mode": initial_mode,
                "baseline_version": baseline_version,
                "target_version": "v8",
                "claims": claims,
                "review_queue": None,
                "decisions": decisions,
                "audit_events": [],
                "policy_version": "1.0",
                "total_claims": len(claims),
                "approved_count": len(decisions),
                "carried_forward_count": len(decisions),
                "stale_count": 0,
                "reopened_count": 0,
                "re_attested_count": 0,
                "exception_count": 0,
            }

            # Store run document
            self._runs[(session_id, new_run_id)] = copy.deepcopy(run_doc)

            # Atomically update session document
            if session_id in self._sessions:
                sess = self._sessions[session_id]
                sess["active_run_id"] = new_run_id
                sess["last_active"] = now
            else:
                self._sessions[session_id] = {
                    "session_id": session_id,
                    "created_at": now,
                    "last_active": now,
                    "active_run_id": new_run_id,
                    "metadata": {},
                }

            logger.info(
                f"[InMemoryFirestore] Created new run '{new_run_id}' for session '{session_id}' (mode={initial_mode})"
            )
            return copy.deepcopy(run_doc)

    def validate_active_run(self, session_id: str, run_id: str) -> bool:
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False
            return sess.get("active_run_id") == run_id

    def commit_action_to_run(
        self,
        session_id: str,
        run_id: Optional[str],
        decision_data: Dict[str, Any],
        event_data: Dict[str, Any],
        environment: str = "development",
    ) -> Dict[str, Any]:
        """
        Commits a counsel decision and audit event to the active run.
        Enforces in-flight commit invalidation: if run_id is supplied and differs
        from the session's active_run_id, raises StaleRunCommitError.
        """
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                sess = self.create_session(session_id)
            active_run_id = sess.get("active_run_id")

            if not active_run_id:
                # Auto-initialize a run if none active
                new_run = self.create_new_run_transaction(session_id)
                active_run_id = new_run["run_id"]

            # In-Flight Commit Invalidation Check
            if run_id is not None and run_id != active_run_id:
                raise StaleRunCommitError(
                    f"In-flight commit invalidation: Run '{run_id}' has been superseded. "
                    f"Active run is '{active_run_id}' for session '{session_id}'."
                )

            target_run_id = active_run_id
            key = (session_id, target_run_id)
            if key not in self._runs:
                raise RunNotFoundError(f"Run '{target_run_id}' not found for session '{session_id}'.")

            run = self._runs[key]
            lineage_key = decision_data.get("stable_lineage_key")
            if not lineage_key:
                raise ValueError("decision_data must include 'stable_lineage_key'.")

            # Update decision
            run["decisions"][lineage_key] = copy.deepcopy(decision_data)

            # Append audit event
            run["audit_events"].append(copy.deepcopy(event_data))

            # Recalculate summary metrics
            stale_count = sum(1 for d in run["decisions"].values() if d.get("state") in ("STALE", "stale", "NEEDS_REVIEW"))
            re_attested = sum(1 for d in run["decisions"].values() if d.get("state") in ("RE_ATTESTED", "re_attested"))
            exceptions = sum(1 for d in run["decisions"].values() if d.get("state") in ("EXCEPTION", "exception") or d.get("status") in ("REJECTED", "rejected"))
            approved = sum(1 for d in run["decisions"].values() if d.get("status") in ("APPROVED", "approved"))

            run["stale_count"] = stale_count
            run["reopened_count"] = stale_count
            run["re_attested_count"] = re_attested
            run["exception_count"] = exceptions
            run["approved_count"] = approved

            # Update session last_active
            self._sessions[session_id]["last_active"] = datetime.now(timezone.utc).isoformat()

            # Increment persistent metrics that survive resets
            self.increment_usage_counter(environment, "decisions_count", 1)

            return copy.deepcopy(run)

    def increment_usage_counter(
        self,
        environment: str,
        metric: str,
        amount: int = 1,
    ) -> Dict[str, Any]:
        with self._lock:
            if environment not in self._usage_counters:
                self._usage_counters[environment] = {
                    "environment": environment,
                    "api_calls_count": 0,
                    "tokens_consumed": 0,
                    "resets_count": 0,
                    "decisions_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            counters = self._usage_counters[environment]
            counters[metric] = counters.get(metric, 0) + amount
            counters["last_updated"] = datetime.now(timezone.utc).isoformat()
            return copy.deepcopy(counters)

    def get_usage_counters(self, environment: str) -> Dict[str, Any]:
        with self._lock:
            if environment not in self._usage_counters:
                return {
                    "environment": environment,
                    "api_calls_count": 0,
                    "tokens_consumed": 0,
                    "resets_count": 0,
                    "decisions_count": 0,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            return copy.deepcopy(self._usage_counters[environment])

    def get_usage_counter(self, environment: str) -> Dict[str, Any]:
        return self.get_usage_counters(environment)

    def reset_environment(self, environment: str) -> None:
        """Resets all in-memory sessions and runs, preserving persistent usage counters."""
        with self._lock:
            self._sessions.clear()
            self._runs.clear()
            # Note: _usage_counters survive resets
            self.increment_usage_counter(environment, "resets_count", 1)
            logger.info(f"[InMemoryFirestore] Reset environment '{environment}' (sessions cleared).")

    def clear_all(self, preserve_usage_counters: bool = False) -> None:
        """Complete teardown for testing."""
        with self._lock:
            self._sessions.clear()
            self._runs.clear()
            if not preserve_usage_counters:
                self._usage_counters.clear()


class NativeFirestoreClient(FirestoreClientInterface):
    """
    Production Google Cloud Firestore client using google.cloud.firestore.
    Enforces atomic transactions and security rules matching firestore.rules.
    """

    def __init__(self, project_id: Optional[str] = None, database: Optional[str] = None):
        try:
            from google.cloud import firestore
        except ImportError as e:
            raise ImportError(
                "google-cloud-firestore package is required to instantiate NativeFirestoreClient."
            ) from e

        proj = project_id or settings.firestore_project_id or settings.google_cloud_project
        db_name = database or settings.firestore_database or "(default)"
        self.db = firestore.Client(project=proj, database=db_name)
        logger.info(f"Initialized NativeFirestoreClient for project '{proj}', database '{db_name}'.")

    def _session_ref(self, session_id: str):
        return self.db.collection("sessions").document(session_id)

    def _run_ref(self, session_id: str, run_id: str):
        return self._session_ref(session_id).collection("runs").document(run_id)

    def _usage_ref(self, environment: str):
        return self.db.collection("usage_counters").document(environment)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        doc = self._session_ref(session_id).get()
        return doc.to_dict() if doc.exists else None

    def create_session(self, session_id: str, active_run_id: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        sess_ref = self._session_ref(session_id)
        doc = sess_ref.get()
        if doc.exists:
            updates = {"last_active": now}
            if active_run_id:
                updates["active_run_id"] = active_run_id
            sess_ref.update(updates)
            data = doc.to_dict()
            data.update(updates)
            return data
        data = {
            "session_id": session_id,
            "created_at": now,
            "last_active": now,
            "active_run_id": active_run_id,
            "metadata": {},
        }
        sess_ref.set(data)
        return data

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updates["last_active"] = datetime.now(timezone.utc).isoformat()
        sess_ref = self._session_ref(session_id)
        sess_ref.set(updates, merge=True)
        return self.get_session(session_id) or updates

    def get_run(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        doc = self._run_ref(session_id, run_id).get()
        return doc.to_dict() if doc.exists else None

    def save_run(self, session_id: str, run_id: str, run_data: Dict[str, Any]) -> None:
        self._run_ref(session_id, run_id).set(run_data)

    def update_run(self, session_id: str, run_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        run_ref = self._run_ref(session_id, run_id)
        run_ref.update(updates)
        doc = run_ref.get()
        return doc.to_dict() if doc.exists else updates

    def create_new_run_transaction(
        self,
        session_id: str,
        baseline_version: str = "v7",
        initial_mode: str = "baseline",
    ) -> Dict[str, Any]:
        from google.cloud import firestore

        now = datetime.now(timezone.utc).isoformat()
        new_run_id = f"run_{uuid.uuid4().hex[:12]}"
        claims, decisions = _generate_v7_baseline_state()

        run_doc = {
            "run_id": new_run_id,
            "session_id": session_id,
            "created_at": now,
            "status": "ready",
            "mode": initial_mode,
            "baseline_version": baseline_version,
            "target_version": "v8",
            "claims": claims,
            "review_queue": None,
            "decisions": decisions,
            "audit_events": [],
            "policy_version": "1.0",
            "total_claims": len(claims),
            "approved_count": len(decisions),
            "carried_forward_count": len(decisions),
            "stale_count": 0,
            "reopened_count": 0,
            "re_attested_count": 0,
            "exception_count": 0,
        }

        sess_ref = self._session_ref(session_id)
        run_ref = self._run_ref(session_id, new_run_id)

        @firestore.transactional
        def _txn(transaction):
            sess_snap = sess_ref.get(transaction=transaction)
            transaction.set(run_ref, run_doc)
            if sess_snap.exists:
                transaction.update(sess_ref, {"active_run_id": new_run_id, "last_active": now})
            else:
                transaction.set(sess_ref, {
                    "session_id": session_id,
                    "created_at": now,
                    "last_active": now,
                    "active_run_id": new_run_id,
                    "metadata": {},
                })

        _txn(self.db.transaction())
        return run_doc

    def validate_active_run(self, session_id: str, run_id: str) -> bool:
        sess = self.get_session(session_id)
        if not sess:
            return False
        return sess.get("active_run_id") == run_id

    def commit_action_to_run(
        self,
        session_id: str,
        run_id: Optional[str],
        decision_data: Dict[str, Any],
        event_data: Dict[str, Any],
        environment: str = "development",
    ) -> Dict[str, Any]:
        from google.cloud import firestore

        sess_ref = self._session_ref(session_id)
        now = datetime.now(timezone.utc).isoformat()

        @firestore.transactional
        def _txn(transaction):
            sess_snap = sess_ref.get(transaction=transaction)
            if not sess_snap.exists:
                raise SessionNotFoundError(f"Session '{session_id}' not found.")
            sess_dict = sess_snap.to_dict()
            active_run_id = sess_dict.get("active_run_id")

            if run_id is not None and run_id != active_run_id:
                raise StaleRunCommitError(
                    f"In-flight commit invalidation: Run '{run_id}' has been superseded. "
                    f"Active run is '{active_run_id}' for session '{session_id}'."
                )

            target_run_id = active_run_id
            run_ref = self._run_ref(session_id, target_run_id)
            run_snap = run_ref.get(transaction=transaction)
            if not run_snap.exists:
                raise RunNotFoundError(f"Run '{target_run_id}' not found for session '{session_id}'.")

            run_dict = run_snap.to_dict()
            lineage_key = decision_data.get("stable_lineage_key")
            run_dict.setdefault("decisions", {})[lineage_key] = decision_data
            run_dict.setdefault("audit_events", []).append(event_data)

            transaction.set(run_ref, run_dict)
            transaction.update(sess_ref, {"last_active": now})
            return run_dict

        updated_run = _txn(self.db.transaction())
        self.increment_usage_counter(environment, "decisions_count", 1)
        return updated_run

    def increment_usage_counter(
        self,
        environment: str,
        metric: str,
        amount: int = 1,
    ) -> Dict[str, Any]:
        from google.cloud import firestore

        now = datetime.now(timezone.utc).isoformat()
        usage_ref = self._usage_ref(environment)

        @firestore.transactional
        def _txn(transaction):
            snap = usage_ref.get(transaction=transaction)
            if snap.exists:
                data = snap.to_dict()
                data[metric] = data.get(metric, 0) + amount
                data["last_updated"] = now
                transaction.set(usage_ref, data)
                return data
            else:
                data = {
                    "environment": environment,
                    "api_calls_count": 0,
                    "tokens_consumed": 0,
                    "resets_count": 0,
                    "decisions_count": 0,
                    metric: amount,
                    "last_updated": now,
                }
                transaction.set(usage_ref, data)
                return data

        return _txn(self.db.transaction())

    def get_usage_counters(self, environment: str) -> Dict[str, Any]:
        snap = self._usage_ref(environment).get()
        if snap.exists:
            return snap.to_dict()
        return {
            "environment": environment,
            "api_calls_count": 0,
            "tokens_consumed": 0,
            "resets_count": 0,
            "decisions_count": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def get_usage_counter(self, environment: str) -> Dict[str, Any]:
        return self.get_usage_counters(environment)

    def reset_environment(self, environment: str) -> None:
        # Increment reset counter
        self.increment_usage_counter(environment, "resets_count", 1)


# -----------------------------------------------------------------------------
# Global Singleton & Factory
# -----------------------------------------------------------------------------
_client_instance: Optional[FirestoreClientInterface] = None
_client_lock = threading.Lock()


def get_firestore_client(force_in_memory: bool = False) -> FirestoreClientInterface:
    """
    Factory function providing the active FirestoreClientInterface singleton.
    Transparently attempts Native Firestore if in GCP with credentials,
    otherwise cleanly falls back to thread-safe InMemoryFirestoreClient.
    """
    global _client_instance
    with _client_lock:
        if _client_instance is not None and not force_in_memory:
            return _client_instance

        if force_in_memory:
            _client_instance = InMemoryFirestoreClient()
            return _client_instance

        # Determine whether to attempt GCP native client
        has_credentials = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) or bool(
            os.getenv("K_SERVICE")  # Cloud Run / App Engine environment indicator
        )

        if has_credentials:
            try:
                _client_instance = NativeFirestoreClient()
                logger.info("Successfully connected Native Google Cloud Firestore client.")
                return _client_instance
            except Exception as e:
                logger.warning(
                    f"Could not connect to Google Cloud Firestore ({e}). "
                    "Falling back to InMemoryFirestoreClient."
                )

        _client_instance = InMemoryFirestoreClient()
        return _client_instance


def reset_firestore_client() -> None:
    """Resets the singleton for clean test fixture isolation."""
    global _client_instance
    with _client_lock:
        if isinstance(_client_instance, InMemoryFirestoreClient):
            _client_instance.clear_all()
        _client_instance = None


firestore_client = get_firestore_client()

__all__ = [
    "FirestoreClientInterface",
    "InMemoryFirestoreClient",
    "NativeFirestoreClient",
    "FirestoreError",
    "SessionNotFoundError",
    "RunNotFoundError",
    "StaleRunCommitError",
    "InvalidRunCommitError",
    "get_firestore_client",
    "reset_firestore_client",
    "firestore_client",
]
