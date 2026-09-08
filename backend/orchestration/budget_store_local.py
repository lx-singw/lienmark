"""
backend/orchestration/budget_store_local.py

Thread-safe, process-safe, file-locked JSON budget store for development and testing.
Pathing: output/budgets/{org_id}/{production_id}/{period_id}.json
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.orchestration.budget_store_types import (
    BudgetExceededError,
    BudgetPeriodSummary,
    BudgetReservation,
    BudgetSettlementRecord,
    BudgetStoreError,
    ReservationNotFoundError,
    ReservationStatus,
    atomic_save_json,
    file_lock,
    is_reservation_expired,
    read_json_file,
    utc_now_iso,
)


class LocalBudgetStore:
    """Thread-safe and process-safe file-locked local budget persistence store."""

    def __init__(self, base_dir: str = "output/budgets", **kwargs: Any) -> None:
        self._base_dir = os.path.normpath(base_dir)
        self._lock = threading.RLock()
        self._index: Dict[str, Tuple[str, str, str]] = {}
        self._config: Dict[str, Any] = kwargs

    def _resolve_paths(self, org_id: str, prod_id: str, period_id: str) -> Tuple[str, str]:
        """Resolves target JSON file path and accompanying lock file path."""
        p_dir = os.path.join(self._base_dir, org_id.strip(), prod_id.strip())
        os.makedirs(p_dir, exist_ok=True)
        f_path = os.path.join(p_dir, f"{period_id.strip()}.json")
        return f_path, f"{f_path}.lock"

    def _load_data(self, f_path: str, org_id: str, prod_id: str, period_id: str) -> Dict[str, Any]:
        """Loads JSON content from disk or returns default schema."""
        data = read_json_file(f_path)
        if data is not None:
            return data
        return {
            "org_id": org_id, "production_id": prod_id, "budget_period_id": period_id,
            "budget_limit_micros": 0, "settled_spend_micros": 0,
            "outstanding_reservations_micros": 0, "updated_at_utc": utc_now_iso(),
            "reservations": {}, "settlements": {},
        }

    def _expire_active(self, data: Dict[str, Any]) -> bool:
        """Marks expired reservations and recomputes outstanding amount."""
        mutated = False
        for res in data.get("reservations", {}).values():
            if res.get("status") == ReservationStatus.ACTIVE.value and is_reservation_expired(res["expires_at_utc"]):
                res["status"] = ReservationStatus.EXPIRED.value
                mutated = True
        data["outstanding_reservations_micros"] = sum(
            r["max_cost_micros"] for r in data.get("reservations", {}).values()
            if r.get("status") == ReservationStatus.ACTIVE.value
        )
        return mutated

    def _locate_reservation(self, res_id: str) -> Tuple[str, str, str]:
        """Locates (org_id, prod_id, period_id) for reservation."""
        if res_id in self._index:
            return self._index[res_id]
        if os.path.exists(self._base_dir):
            for root, _, files in os.walk(self._base_dir):
                for file in [f for f in files if f.endswith(".json") and not f.endswith(".lock")]:
                    with contextlib.suppress(Exception):
                        d = read_json_file(os.path.join(root, file))
                        if d and res_id in d.get("reservations", {}):
                            loc = (d["org_id"], d["production_id"], d["budget_period_id"])
                            self._index[res_id] = loc
                            return loc
        raise ReservationNotFoundError(res_id)

    def reserve_budget(
        self, org_id: str, production_id: str, budget_period_id: str, run_id: str,
        action_id: str, provider: str, model_or_mode: str, max_cost_micros: int,
        expires_in_seconds: int = 300,
    ) -> BudgetReservation:
        """Atomically reserves max estimated spend under budget period cap."""
        with self._lock:
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                self._expire_active(data)
                limit = data.get("budget_limit_micros", 0)
                proj = data["settled_spend_micros"] + data["outstanding_reservations_micros"] + max_cost_micros
                if limit > 0 and proj > limit:
                    raise BudgetExceededError(
                        f"Spend limit exceeded for '{budget_period_id}': {proj} > {limit} micros.",
                        period_id=budget_period_id, current_spend_micros=proj - max_cost_micros, limit_micros=limit,
                    )
                res_id = f"res_{uuid.uuid4().hex[:12]}"
                now_dt = datetime.now(timezone.utc)
                exp_dt = now_dt + timedelta(seconds=expires_in_seconds)
                res = BudgetReservation(
                    reservation_id=res_id, action_id=action_id, org_id=org_id, production_id=production_id,
                    budget_period_id=budget_period_id, run_id=run_id, provider=provider,
                    model_or_mode=model_or_mode, max_cost_micros=max_cost_micros,
                    status=ReservationStatus.ACTIVE, created_at_utc=now_dt.isoformat(),
                    expires_at_utc=exp_dt.isoformat(),
                )
                data["reservations"][res_id] = res.model_dump()
                data["outstanding_reservations_micros"] += max_cost_micros
                data["updated_at_utc"] = utc_now_iso()
                atomic_save_json(fp, data)
                self._index[res_id] = (org_id, production_id, budget_period_id)
                return res

    def settle_reservation(
        self, reservation_id: str, actual_cost_micros: int, usage_measurements: Dict[str, Any],
        provider_confirmed_cost_micros: Optional[int] = None, cache_hit: bool = False,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> BudgetSettlementRecord:
        """Converts an active reservation into settled expenditure."""
        with self._lock:
            if not (org_id and production_id and budget_period_id):
                org_id, production_id, budget_period_id = self._locate_reservation(reservation_id)
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                res = data.get("reservations", {}).get(reservation_id)
                if not res:
                    raise ReservationNotFoundError(reservation_id)
                if res.get("status") == ReservationStatus.SETTLED.value:
                    raise BudgetStoreError(f"Reservation '{reservation_id}' is already settled.")
                if res.get("status") == ReservationStatus.ACTIVE.value:
                    data["outstanding_reservations_micros"] = max(
                        0, data["outstanding_reservations_micros"] - res.get("max_cost_micros", 0)
                    )
                res["status"] = ReservationStatus.SETTLED.value
                data["settled_spend_micros"] += actual_cost_micros
                stl_id = f"stl_{uuid.uuid4().hex[:12]}"
                record = BudgetSettlementRecord(
                    settlement_id=stl_id, reservation_id=reservation_id, actual_cost_micros=actual_cost_micros,
                    usage_measurements=usage_measurements, provider_confirmed_cost_micros=provider_confirmed_cost_micros,
                    cache_hit=cache_hit, settled_at_utc=utc_now_iso(),
                )
                data.setdefault("settlements", {})[stl_id] = record.model_dump()
                data["updated_at_utc"] = utc_now_iso()
                atomic_save_json(fp, data)
                return record

    def recover_reservation(
        self, reservation_id: str, status: ReservationStatus = ReservationStatus.UNCERTAIN,
        org_id: Optional[str] = None, production_id: Optional[str] = None,
        budget_period_id: Optional[str] = None,
    ) -> None:
        """Recovers an orphaned or failed reservation by setting terminal/uncertain status."""
        with self._lock:
            if not (org_id and production_id and budget_period_id):
                org_id, production_id, budget_period_id = self._locate_reservation(reservation_id)
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                res = data.get("reservations", {}).get(reservation_id)
                if not res:
                    raise ReservationNotFoundError(reservation_id)
                if res.get("status") == ReservationStatus.ACTIVE.value:
                    data["outstanding_reservations_micros"] = max(
                        0, data["outstanding_reservations_micros"] - res.get("max_cost_micros", 0)
                    )
                st_val = status.value if isinstance(status, ReservationStatus) else str(status)
                res["status"] = st_val
                data["updated_at_utc"] = utc_now_iso()
                atomic_save_json(fp, data)

    def get_summary(self, org_id: str, production_id: str, budget_period_id: str) -> BudgetPeriodSummary:
        """Retrieves period spending summary, updating any expired reservations."""
        with self._lock:
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                if self._expire_active(data):
                    data["updated_at_utc"] = utc_now_iso()
                    atomic_save_json(fp, data)
                return BudgetPeriodSummary(
                    org_id=data["org_id"], production_id=data["production_id"],
                    budget_period_id=data["budget_period_id"],
                    budget_limit_micros=data.get("budget_limit_micros", 0),
                    settled_spend_micros=data.get("settled_spend_micros", 0),
                    outstanding_reservations_micros=data.get("outstanding_reservations_micros", 0),
                    updated_at_utc=data.get("updated_at_utc", utc_now_iso()),
                )

    def set_budget_limit(self, org_id: str, production_id: str, budget_period_id: str, limit_micros: int) -> None:
        """Sets hard budget spending ceiling in micro-cents for a budget period."""
        with self._lock:
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                data["budget_limit_micros"] = max(0, limit_micros)
                data["updated_at_utc"] = utc_now_iso()
                atomic_save_json(fp, data)

    def list_reservations(
        self, org_id: str, production_id: str, budget_period_id: str,
        status: Optional[ReservationStatus] = None,
    ) -> List[BudgetReservation]:
        """Lists reservations for budget period, optionally filtered by status."""
        with self._lock:
            fp, lp = self._resolve_paths(org_id, production_id, budget_period_id)
            with file_lock(lp):
                data = self._load_data(fp, org_id, production_id, budget_period_id)
                if self._expire_active(data):
                    data["updated_at_utc"] = utc_now_iso()
                    atomic_save_json(fp, data)
                st_filter = status.value if isinstance(status, ReservationStatus) else (status if status else None)
                return [
                    BudgetReservation.model_validate(r)
                    for r in data.get("reservations", {}).values()
                    if st_filter is None or r.get("status") == st_filter
                ]

    def reset(self) -> None:
        """Clears local storage directory and in-memory caches."""
        with self._lock:
            self._index.clear()
            if os.path.exists(self._base_dir):
                shutil.rmtree(self._base_dir, ignore_errors=True)
