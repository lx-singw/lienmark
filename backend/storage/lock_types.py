"""
Lienmark Distributed Lock Domain Types and Exceptions.

Provides domain exceptions, distributed lock records, and ISO 8601 UTC
timestamp helpers for distributed concurrency coordination.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class LockAcquisitionError(Exception):
    """Raised when a distributed lock cannot be acquired."""
    pass


class LockExpiredError(Exception):
    """Raised when attempting to operate on an already expired distributed lock."""
    pass


class LockReleaseError(Exception):
    """Raised when an illegal or unauthorized lock release or renewal is attempted."""
    pass


def parse_utc_timestamp(ts: str) -> datetime:
    """
    Parses an ISO 8601 UTC timestamp string into a timezone-aware datetime object.

    Supports both 'Z' suffix and explicit '+00:00' timezone offsets.
    """
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(f"Invalid timestamp string: {ts!r}")
    normalized = ts.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class DistributedLockRecord(BaseModel):
    """
    Represents an immutable snapshot of a distributed lock state.

    Includes monotonic fencing token for split-brain mitigation and
    safe downstream transaction fencing.
    """
    model_config = ConfigDict(extra="ignore")

    lock_key: str
    owner_id: str
    acquired_at_utc: str
    expires_at_utc: str
    fence_token: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_expired(self, now_utc: Optional[str] = None) -> bool:
        """
        Determines whether the lock lease has expired.

        Compares expires_at_utc against now_utc if provided, or current UTC time.
        Returns True if current time is greater than or equal to expiration time.
        """
        ref_dt = (
            parse_utc_timestamp(now_utc)
            if now_utc is not None
            else datetime.now(timezone.utc)
        )
        exp_dt = parse_utc_timestamp(self.expires_at_utc)
        return ref_dt >= exp_dt


class DistributedLock(BaseModel):
    """
    Legacy/compatibility model representing an acquired lease with Unix timestamps.
    Maintains compatibility with early storage watcher interfaces.
    """
    model_config = ConfigDict(extra="ignore")

    lock_key: str
    fence_token: int
    owner_id: str
    acquired_at: float
    expires_at: float

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        """Checks whether the lease has expired based on Unix epoch seconds."""
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at


__all__ = [
    "LockAcquisitionError",
    "LockExpiredError",
    "LockReleaseError",
    "DistributedLockRecord",
    "DistributedLock",
    "parse_utc_timestamp",
]
