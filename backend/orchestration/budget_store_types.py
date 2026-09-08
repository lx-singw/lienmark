"""
backend/orchestration/budget_store_types.py

Canonical domain types, models, pricing constants, and exceptions
for durable budget persistence subsystem.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, Optional
from pydantic import BaseModel, ConfigDict, Field

# Pricing constants (1 USD = 1,000,000 micros)
MICROS_PER_USD: int = 1_000_000
PARALLEL_FAST_MICROS: int = 1_000      # $0.001 per fast lookup
PARALLEL_BASIC_MICROS: int = 5_000     # $0.005 per basic lookup
GEMINI_PROMPT_MICROS_PER_TOKEN: float = 1.25       # $1.25 / 1M tokens
GEMINI_COMPLETION_MICROS_PER_TOKEN: float = 5.0   # $5.00 / 1M tokens


class ReservationStatus(str, Enum):
    """Status lifecycle of a budget reservation."""
    ACTIVE = "active"
    SETTLED = "settled"
    RELEASED = "released"
    UNCERTAIN = "uncertain"
    EXPIRED = "expired"
    RESERVED = "active"
    RECOVERED = "released"



class BudgetStoreError(Exception):
    """Base exception for budget store persistence operations."""
    pass


class BudgetExceededError(BudgetStoreError):
    """Raised when hard spend cap for a budget period would be exceeded."""

    def __init__(
        self, message: str = "", period_id: str = "",
        current_spend_micros: int = 0, limit_micros: int = 0,
    ) -> None:
        self.period_id = period_id
        self.current_spend_micros = current_spend_micros
        self.limit_micros = limit_micros
        msg = message or f"Budget period '{period_id}' exceeded limit: {current_spend_micros}/{limit_micros} micros."
        super().__init__(msg)


class ReservationNotFoundError(BudgetStoreError):
    """Raised when a requested reservation is not found."""

    def __init__(self, reservation_id: str, message: Optional[str] = None) -> None:
        self.reservation_id = reservation_id
        super().__init__(message or f"Reservation '{reservation_id}' not found in budget store.")


class BudgetReservation(BaseModel):
    """Immutable budget reservation record locking estimated spend."""
    model_config = ConfigDict(extra="ignore")

    reservation_id: str = Field(..., min_length=1)
    action_id: str = Field(..., min_length=1)
    org_id: str = Field(..., min_length=1)
    production_id: str = Field(..., min_length=1)
    budget_period_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    model_or_mode: str = Field(..., min_length=1)
    max_cost_micros: int = Field(..., ge=0)
    status: ReservationStatus = Field(default=ReservationStatus.ACTIVE)
    created_at_utc: str
    expires_at_utc: str

    @property
    def period_id(self) -> str:
        return self.budget_period_id


class BudgetSettlementRecord(BaseModel):
    """Settlement record capturing actual verified cost and telemetry."""
    model_config = ConfigDict(extra="ignore")

    settlement_id: str = Field(..., min_length=1)
    reservation_id: str = Field(..., min_length=1)
    actual_cost_micros: int = Field(..., ge=0)
    usage_measurements: Dict[str, Any] = Field(default_factory=dict)
    provider_confirmed_cost_micros: Optional[int] = Field(None, ge=0)
    cache_hit: bool = Field(default=False)
    settled_at_utc: str

    @property
    def settled_cost_micros(self) -> int:
        return self.actual_cost_micros

    @property
    def provider_cost_micros(self) -> int:
        return self.provider_confirmed_cost_micros if self.provider_confirmed_cost_micros is not None else (0 if self.cache_hit else self.actual_cost_micros)



class BudgetPeriodSummary(BaseModel):
    """Aggregated spend and reservation summary for a production budget period."""
    model_config = ConfigDict(extra="ignore")

    org_id: str = Field(..., min_length=1)
    production_id: str = Field(..., min_length=1)
    budget_period_id: str = Field(..., min_length=1)
    budget_limit_micros: int = Field(default=0, ge=0)
    settled_spend_micros: int = Field(default=0, ge=0)
    outstanding_reservations_micros: int = Field(default=0, ge=0)
    updated_at_utc: str


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def parse_utc_timestamp(ts: str) -> datetime:
    """Parses an ISO 8601 UTC timestamp string into timezone-aware datetime."""
    dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def is_reservation_expired(expires_at_utc: str, now: Optional[datetime] = None) -> bool:
    """Checks whether the given expiration timestamp is in the past."""
    return (now or datetime.now(timezone.utc)) >= parse_utc_timestamp(expires_at_utc)


@contextlib.contextmanager
def file_lock(lock_path: str, timeout: float = 10.0) -> Iterator[None]:
    """Process-safe mutual exclusion lock using atomic file creation."""
    start = time.monotonic()
    fd: Optional[int] = None
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except (FileExistsError, OSError):
            if os.path.exists(lock_path) and (time.time() - os.path.getmtime(lock_path) > 30.0):
                with contextlib.suppress(OSError):
                    os.remove(lock_path)
            if time.monotonic() - start >= timeout:
                raise BudgetStoreError(f"Timed out waiting for file lock: '{lock_path}'")
            time.sleep(0.01)
    try:
        yield
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
            with contextlib.suppress(OSError):
                os.remove(lock_path)


def atomic_save_json(f_path: str, data: Dict[str, Any]) -> None:
    """Atomically saves JSON payload using temporary file replacement."""
    os.makedirs(os.path.dirname(os.path.abspath(f_path)), exist_ok=True)
    tmp = f"{f_path}.tmp.{uuid.uuid4().hex}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, f_path)
    except Exception as exc:
        if os.path.exists(tmp):
            with contextlib.suppress(OSError):
                os.remove(tmp)
        raise BudgetStoreError(f"Failed atomic write to '{f_path}': {exc}") from exc


def read_json_file(f_path: str) -> Optional[Dict[str, Any]]:
    """Safely reads JSON payload from disk or returns None if absent."""
    if not os.path.exists(f_path):
        return None
    try:
        with open(f_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        raise BudgetStoreError(f"Corrupted JSON file '{f_path}': {exc}") from exc


__all__ = [
    "MICROS_PER_USD",
    "PARALLEL_FAST_MICROS",
    "PARALLEL_BASIC_MICROS",
    "GEMINI_PROMPT_MICROS_PER_TOKEN",
    "GEMINI_COMPLETION_MICROS_PER_TOKEN",
    "ReservationStatus",
    "BudgetStoreError",
    "BudgetExceededError",
    "ReservationNotFoundError",
    "BudgetReservation",
    "BudgetSettlementRecord",
    "BudgetPeriodSummary",
    "utc_now_iso",
    "parse_utc_timestamp",
    "is_reservation_expired",
    "file_lock",
    "atomic_save_json",
    "read_json_file",
]
