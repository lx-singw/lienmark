"""
backend/core/dual_review_exceptions.py

Custom domain exceptions for Accountable Dual-Review Clearance Sign-Off.
Sprint 5.2: Invariant enforcement and HTTP status code mappings.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations


class DualReviewError(Exception):
    """Base error for all dual review workflow failures."""

    status_code: int = 400

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DistinctReviewerError(DualReviewError, PermissionError):
    """Raised when the primary reviewer attempts to self-approve the second review."""

    status_code: int = 403

    def __init__(
        self,
        message: str = "Second review must be executed by a distinct authorized counsel.",
    ) -> None:
        super().__init__(message, status_code=403)


class ConflictAttestationError(DualReviewError, ValueError):
    """Raised when counsel attempts approval without mandatory conflict-of-interest attestation."""

    status_code: int = 400

    def __init__(
        self,
        message: str = "Conflict-of-interest attestation is mandatory for clearance sign-off.",
    ) -> None:
        super().__init__(message, status_code=400)


class ConflictOfInterestError(DualReviewError, PermissionError):
    """Raised when counsel has an ethical wall or declared conflict of interest."""

    status_code: int = 403

    def __init__(
        self,
        message: str = "Reviewer has a declared ethical conflict of interest.",
    ) -> None:
        super().__init__(message, status_code=403)


class StalePackageError(DualReviewError, ValueError):
    """Raised when attempting an approval action on a stale or superseded package."""

    status_code: int = 409

    def __init__(
        self,
        message: str = "Decision package is stale and cannot be approved.",
    ) -> None:
        super().__init__(message, status_code=409)


class PackageNotFoundError(DualReviewError, ValueError):
    """Raised when a requested decision package is not found."""

    status_code: int = 404

    def __init__(self, message: str = "Decision package not found.") -> None:
        super().__init__(message, status_code=404)
