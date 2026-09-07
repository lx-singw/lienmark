"""
backend/api/routes/clarification_schemas.py

Pydantic v2 request and response schemas for Clarification API endpoints.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.domain.models import ClarificationRequest


class ClarificationStatusFilter(str, Enum):
    """Allowed status filter values for run clarification queries."""
    PENDING = "pending"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class ClarificationRespondRequest(BaseModel):
    """Payload for answering and resolving a pending ClarificationRequest."""
    response_text: Optional[str] = Field(
        None,
        description="Detailed legal or factual clarification response",
    )
    attached_document_id: Optional[str] = Field(
        None,
        description="Document record ID or storage reference for attached clearance artifact",
    )
    selected_option: Optional[str] = Field(
        None,
        description="Selected option chosen from suggested clearance pathways",
    )
    responder_role: str = Field(
        ...,
        min_length=1,
        description="Role of the responding personnel (e.g. Producer, Reviewer, Admin)",
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ClarificationRespondResponse(BaseModel):
    """Outcome envelope returned upon successful clarification resolution."""
    success: bool = True
    request_id: str
    status: str
    resolved_at: str
    resolved_by: str
    responder_role: str
    event_id: Optional[str] = None
    clarification: ClarificationRequest
    message: str = "Clarification resolved and cryptographic audit event recorded."

    model_config = ConfigDict(arbitrary_types_allowed=True)
