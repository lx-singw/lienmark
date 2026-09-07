"""
backend/core/reviewer_types.py

Data models and enums for Reviewer Rejection & Directed Re-Investigation Loop.
Sprint 4.3: Milestone D - Human-in-the-Loop Clarification & Reviewer Reinvestigation.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from backend.domain.models import CensusDisposition, WorkflowReason


class ReviewerAction(str, Enum):
    """Authoritative actions available to legal counsel in reviewer loops."""
    SIGN_OFF = "sign_off"
    REJECT_AND_DIRECT = "reject_and_direct"
    CONDITIONAL_SIGN_OFF = "conditional_sign_off"


STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "for", "with", "at", "by",
    "from", "to", "of", "about", "into", "over", "after", "is", "are",
    "must", "obtain", "check", "verify", "re-search", "specifically",
    "please", "investigate", "search", "all", "any", "be",
}


def sanitize_directive_keywords(text: str) -> List[str]:
    """
    Extracts key legal entities, dates, territories, and subject terms from directive text.
    Filters out noise tokens while preserving domain keywords.
    """
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s\-]", " ", text)
    tokens = cleaned.split()
    seen = set()
    keywords: List[str] = []
    for tok in tokens:
        stripped = tok.strip("-").strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower in STOP_WORDS or len(lower) < 2:
            continue
        if lower not in seen:
            seen.add(lower)
            keywords.append(stripped)
    return keywords


class CounselDirective(BaseModel):
    """
    Structured directive captured when legal counsel rejects a finding
    and instructs targeted re-investigation with mandatory constraints.
    """
    directive_id: str = Field(default_factory=lambda: f"dir_{uuid.uuid4().hex[:12]}")
    claim_id: str
    counsel_id: str
    counsel_name: str
    directive_text: str
    mandatory_constraints: List[str] = Field(default_factory=list)
    sanitized_keywords: List[str] = Field(default_factory=list)
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.mandatory_constraints and self.directive_text:
            self.mandatory_constraints = [self.directive_text]
        if not self.sanitized_keywords and self.directive_text:
            self.sanitized_keywords = sanitize_directive_keywords(self.directive_text)


class AttemptRecord(BaseModel):
    """
    Individual attempt record within an atomic claim's review lineage.
    Preserves prior finding, counsel action, and any revised finding pointer.
    """
    attempt_number: int
    action: Union[ReviewerAction, str]
    counsel_id: str
    counsel_name: Optional[str] = None
    directive_text: Optional[str] = None
    citation_text: Optional[str] = None
    conditions: Optional[List[str]] = None
    prior_finding_id: Optional[str] = None
    revised_finding_id: Optional[str] = None
    status: Optional[str] = None
    disposition: Optional[str] = None
    audit_event_id: Optional[str] = None
    reinvestigation_run_id: Optional[str] = None
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AttemptLineage(BaseModel):
    """
    Immutable lineage of review attempts for a specific atomic claim.
    Ensures rejected attempts are permanently preserved and queryable.
    """
    claim_id: str
    total_attempts: int = 1
    current_attempt_number: int = 1
    attempts: List[AttemptRecord] = Field(default_factory=list)

    def append_attempt(self, record: AttemptRecord) -> None:
        """Appends a new attempt record and updates monotonic attempt count."""
        self.attempts.append(record)
        self.total_attempts = len(self.attempts)
        self.current_attempt_number = max(self.current_attempt_number, record.attempt_number)


class ResearchFinding(BaseModel):
    """
    Represents an automated or directed research finding with provenance.
    """
    finding_id: str = Field(default_factory=lambda: f"find_{uuid.uuid4().hex[:10]}")
    claim_id: str
    attempt_number: int = 1
    directive_id: Optional[str] = None
    constraints_applied: List[str] = Field(default_factory=list)
    keywords_used: List[str] = Field(default_factory=list)
    evidence_summary: str
    source_uri: Optional[str] = None
    confidence_score: float = 0.95
    status: str = "RESOLVED"
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ReinvestigationDispatch(BaseModel):
    """
    Dispatch package resulting from counsel rejecting a claim finding.
    Contains reset claim, structured directive, lineage, and research results.
    """
    dispatch_id: str = Field(default_factory=lambda: f"disp_{uuid.uuid4().hex[:12]}")
    claim_id: str
    tenant_id: str
    production_id: str
    directive: CounselDirective
    attempt_number: int
    disposition: CensusDisposition = CensusDisposition.NEEDS_REVIEW
    workflow_reason: WorkflowReason = WorkflowReason.REINVESTIGATION_REQUESTED
    prior_finding: Optional[Any] = None
    prior_finding_id: Optional[str] = None
    revised_finding_id: Optional[str] = None
    reinvestigation_result: Optional[Any] = None
    lineage: Optional[AttemptLineage] = None
    ledger_event: Optional[Any] = None
    claim: Optional[Any] = None
    status: str = "DISPATCHED"
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ClaimSignOffResult(BaseModel):
    """
    Outcome of an authoritative counsel sign-off action.
    """
    signoff_id: str = Field(default_factory=lambda: f"signoff_{uuid.uuid4().hex[:12]}")
    claim_id: str
    action: ReviewerAction = ReviewerAction.SIGN_OFF
    disposition: CensusDisposition = CensusDisposition.APPROVED
    counsel_id: str
    counsel_name: str
    citation_text: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    ledger_event: Optional[Any] = None
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    claim: Optional[Any] = None
