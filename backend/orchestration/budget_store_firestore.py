"""
backend/orchestration/budget_store_firestore.py

Native Google Cloud Firestore persistence adapter for budget reservations and settlements.
Partitions data under /organizations/{org_id}/productions/{production_id}/budget_periods/{period_id}
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.orchestration.budget_store_types import (
    BudgetExceededError,
    BudgetPeriodSummary,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
    utc_now_iso,
)


class FirestoreBudgetStore:
    """Durable Google Cloud Firestore budget store using atomic transactions."""

    def __init__(self, client: Any) -> None:
        if client is None:
            raise BudgetStoreError("Firestore client is required. Silent fallback is prohibited.")
        self._client = client

    def _period_ref(self, org_id: str, prod_id: str, period_id: str) -> Any:
        """Returns DocumentReference for namespaced budget period."""
        return (
            self._client.collection("organizations").document(org_id.strip())
            .collection("productions").document(prod_id.strip())
            .collection("budget_periods").document(period_id.strip())
        )

    def _get_in_txn(self, txn: Any, ref: Any) -> Any:
        """Reads document snapshot inside active transaction context."""
        return txn.get(ref) if hasattr(txn, "get") else ref.get()

    def _run_transaction(self, callback: Callable[[Any], Any]) -> Any:
        """Runs callable inside Firestore transaction, failing closed on errors."""
        if not hasattr(self._client, "transaction"):
            raise BudgetStoreError("Firestore client does not support transactions.")
        try:
            from google.cloud import firestore
            txn = self._client.transaction()
            if isinstance(txn, firestore.Transaction):
                @firestore.transactional
                def _wrapped(t: Any) -> Any:
                    return callback(t)
                return _wrapped(txn)
            res = callback(txn)
            if hasattr(txn, "commit"):
                txn.commit()
            return res
        except BudgetStoreError:
            raise
        except Exception as exc:
            raise BudgetStoreError(f"Firestore transaction execution failed: {exc}") from exc

    def _locate_reservation(self, res_id: str) -> Tuple[str, str, str]:
        """Resolves period path for a reservation using global index."""
        try:
            snap = self._client.collection("budget_reservations_index").document(res_id).get()
            if not snap.exists:
                raise ReservationNotFoundError(res_id)
            d = snap.to_dict() or {}
            return d["org_id"], d["production_id"], d["budget_period_id"]
        except ReservationNotFoundError:
            raise
        except Exception as exc:
            raise BudgetStoreError(f"Failed resolving reservation index '{res_id}': {exc}") from exc

    def _apply_reserve_tx(self, txn: Any, period_ref: Any, res: BudgetReservation) -> None:
        """Validates caps and writes reservation inside active transaction."""
        snap = self._get_in_txn(txn, period_ref)
        p_data = snap.to_dict() or {} if snap.exists else {}
        limit = p_data.get("budget_limit_micros", 0)
        settled, outstanding = p_data.get("settled_spend_micros", 0), p_data.get("outstanding_reservations_micros", 0)
        proj = settled + outstanding + res.max_cost_micros
        if limit > 0 and proj > limit:
            raise BudgetExceededError(
                f"Spend limit exceeded for '{res.budget_period_id}': {proj} > {limit} micros.",
                period_id=res.budget_period_id, current_spend_micros=settled + outstanding, limit_micros=limit,
            )
        now_iso = utc_now_iso()
        if snap.exists:
            txn.update(period_ref, {"outstanding_reservations_micros": outstanding + res.max_cost_micros, "updated_at_utc": now_iso})
        else:
            txn.set(period_ref, {
                "org_id": res.org_id, "production_id": res.production_id, "budget_period_id": res.budget_period_id,
                "budget_limit_micros": 0, "settled_spend_micros": 0,
                "outstanding_reservations_micros": res.max_cost_micros, "updated_at_utc": now_iso,
            })
        txn.set(period_ref.collection("reservations").document(res.reservation_id), res.model_dump())
        txn.set(self._client.collection("budget_reservations_index").document(res.reservation_id), {
            "org_id": res.org_id, "production_id": res.production_id, "budget_period_id": res.budget_period_id,
        })

    def reserve_budget(
        self, org_id: str, production_id: str, budget_period_id: str, run_id: str,
        action_id: str, provider: str, model_or_mode: str, max_cost_micros: int,
        expires_in_seconds: int = 300,
    ) -> BudgetReservation:
        """Atomically reserves spend under budget period spending limit."""
        period_ref = self._period_ref(org_id, production_id, budget_period_id)
        now_dt = datetime.now(timezone.utc)
        res = BudgetReservation(
            reservation_id=f"res_{uuid.uuid4().hex[:12]}", action_id=action_id, org_id=org_id,
            production_id=production_id, budget_period_id=budget_period_id, run_id=run_id,
            provider=provider, model_or_mode=model_or_mode, max_cost_micros=max_cost_micros,
            status=ReservationStatus.ACTIVE, created_at_utc=now_dt.isoformat(),
            expires_at_utc=(now_dt + timedelta(seconds=expires_in_seconds)).isoformat(),
        )
        self._run_transaction(lambda txn: self._apply_reserve_tx(txn, period_ref, res))
        return res

    def _apply_settle_tx(self, txn: Any, p_ref: Any, r_ref: Any, res_id: str, actual: int, rec: BudgetSettlementRecord) -> None:
        """Executes settlement state changes and balance adjustments in transaction."""
        r_snap = self._get_in_txn(txn, r_ref)
        if not r_snap.exists:
            raise ReservationNotFoundError(res_id)
        r_data = r_snap.to_dict() or {}
        if r_data.get("status") == ReservationStatus.SETTLED.value:
            raise BudgetStoreError(f"Reservation '{res_id}' is already settled.")
        p_snap = self._get_in_txn(txn, p_ref)
        p_data = p_snap.to_dict() or {} if p_snap.exists else {}
        out = p_data.get("outstanding_reservations_micros", 0)
        if r_data.get("status") == ReservationStatus.ACTIVE.value:
            out = max(0, out - r_data.get("max_cost_micros", 0))
        txn.update(p_ref, {
            "outstanding_reservations_micros": out,
            "settled_spend_micros": p_data.get("settled_spend_micros", 0) + actual,
            "updated_at_utc": utc_now_iso(),
        })
        txn.update(r_ref, {"status": ReservationStatus.SETTLED.value})
        txn.set(p_ref.collection("settlements").document(rec.settlement_id), rec.model_dump())

    def settle_reservation(
        self, reservation_id: str, actual_cost_micros: int, usage_measurements: Dict[str, Any],
        provider_confirmed_cost_micros: Optional[int] = None, cache_hit: bool = False,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> BudgetSettlementRecord:
        """Atomically transitions reservation to settled spend."""
        if not (org_id and production_id and budget_period_id):
            org_id, production_id, budget_period_id = self._locate_reservation(reservation_id)
        p_ref = self._period_ref(org_id, production_id, budget_period_id)
        r_ref = p_ref.collection("reservations").document(reservation_id)
        record = BudgetSettlementRecord(
            settlement_id=f"stl_{uuid.uuid4().hex[:12]}", reservation_id=reservation_id,
            actual_cost_micros=actual_cost_micros, usage_measurements=usage_measurements,
            provider_confirmed_cost_micros=provider_confirmed_cost_micros,
            cache_hit=cache_hit, settled_at_utc=utc_now_iso(),
        )
        self._run_transaction(lambda txn: self._apply_settle_tx(txn, p_ref, r_ref, reservation_id, actual_cost_micros, record))
        return record

    def recover_reservation(
        self, reservation_id: str, status: ReservationStatus = ReservationStatus.UNCERTAIN,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> None:
        """Sets reservation to terminal recovery status, releasing active spend."""
        if not (org_id and production_id and budget_period_id):
            org_id, production_id, budget_period_id = self._locate_reservation(reservation_id)
        p_ref = self._period_ref(org_id, production_id, budget_period_id)
        r_ref = p_ref.collection("reservations").document(reservation_id)
        st_val = status.value if isinstance(status, ReservationStatus) else str(status)

        def _tx_op(txn: Any) -> None:
            r_snap = self._get_in_txn(txn, r_ref)
            if not r_snap.exists:
                raise ReservationNotFoundError(reservation_id)
            r_data = r_snap.to_dict() or {}
            if r_data.get("status") == ReservationStatus.ACTIVE.value:
                p_snap = self._get_in_txn(txn, p_ref)
                p_data = p_snap.to_dict() or {} if p_snap.exists else {}
                out = max(0, p_data.get("outstanding_reservations_micros", 0) - r_data.get("max_cost_micros", 0))
                txn.update(p_ref, {"outstanding_reservations_micros": out, "updated_at_utc": utc_now_iso()})
            txn.update(r_ref, {"status": st_val})

        self._run_transaction(_tx_op)

    def get_summary(self, org_id: str, production_id: str, budget_period_id: str) -> BudgetPeriodSummary:
        """Retrieves period spending summary from Firestore."""
        try:
            snap = self._period_ref(org_id, production_id, budget_period_id).get()
            if not snap.exists:
                return BudgetPeriodSummary(
                    org_id=org_id, production_id=production_id, budget_period_id=budget_period_id,
                    budget_limit_micros=0, settled_spend_micros=0, outstanding_reservations_micros=0,
                    updated_at_utc=utc_now_iso(),
                )
            d = snap.to_dict() or {}
            return BudgetPeriodSummary(
                org_id=d.get("org_id", org_id), production_id=d.get("production_id", production_id),
                budget_period_id=d.get("budget_period_id", budget_period_id),
                budget_limit_micros=d.get("budget_limit_micros", 0),
                settled_spend_micros=d.get("settled_spend_micros", 0),
                outstanding_reservations_micros=d.get("outstanding_reservations_micros", 0),
                updated_at_utc=d.get("updated_at_utc", utc_now_iso()),
            )
        except Exception as exc:
            raise BudgetStoreError(f"Firestore get_summary failed: {exc}") from exc

    def set_budget_limit(self, org_id: str, production_id: str, budget_period_id: str, limit_micros: int) -> None:
        """Sets hard budget spending ceiling in micro-cents for a budget period."""
        try:
            self._period_ref(org_id, production_id, budget_period_id).set({
                "org_id": org_id, "production_id": production_id, "budget_period_id": budget_period_id,
                "budget_limit_micros": max(0, limit_micros), "updated_at_utc": utc_now_iso(),
            }, merge=True)
        except Exception as exc:
            raise BudgetStoreError(f"Firestore set_budget_limit failed: {exc}") from exc

    def list_reservations(
        self, org_id: str, production_id: str, budget_period_id: str,
        status: Optional[ReservationStatus] = None,
    ) -> List[BudgetReservation]:
        """Lists reservations for budget period, optionally filtered by status."""
        try:
            col = self._period_ref(org_id, production_id, budget_period_id).collection("reservations")
            st_filter = status.value if isinstance(status, ReservationStatus) else (status if status else None)
            results: List[BudgetReservation] = []
            for doc in col.stream():
                d = doc.to_dict() or {}
                if st_filter is None or d.get("status") == st_filter:
                    results.append(BudgetReservation.model_validate(d))
            return results
        except Exception as exc:
            raise BudgetStoreError(f"Firestore list_reservations failed: {exc}") from exc
