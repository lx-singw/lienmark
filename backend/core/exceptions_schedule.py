"""
backend/core/exceptions_schedule.py

Lienmark Form E&O-2026 Exceptions Schedule Engine
Sprint 3B / Sprint 6A Architectural Integration:
Provides automated compilation of the version-bound Exceptions Schedule,
three-tier legal categorization (Unresolved Exceptions, Re-Attested Public Domain Items,
and Certified Carried-Forward Register), and SSR Form E&O-2026 HTML generation.

Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from backend.domain.models import (
    CarrierHeader,
    CounselDecision,
    CreativeUse,
    DecisionState,
    DecisionStatus,
    DecisionValidity,
    ExceptionsSchedule,
    ExceptionsScheduleItem,
    ReattestationRequest,
)
from backend.core.invalidation_engine import InvalidationEngine

logger = logging.getLogger("lienmark.exceptions_schedule")


class ExceptionsScheduleEngine:
    """
    Dedicated facade engine for building, validating, and formatting
    Form E&O-2026 exceptions schedules and underwriter packages.
    """

    @classmethod
    def generate_schedule(
        cls,
        project_id: str,
        base_version_id: str,
        target_version_id: str,
        target_uses: List[CreativeUse],
        validity_results: List[DecisionValidity],
        reattestations: Optional[Dict[str, ReattestationRequest]] = None,
        base_uses: Optional[List[CreativeUse]] = None,
    ) -> ExceptionsSchedule:
        """
        Delegates schedule generation to InvalidationEngine to guarantee 100%
        mathematical conservation (12 = 10 carried + 1 re-attested + 1 exception).
        """
        return InvalidationEngine.generate_exceptions_schedule(
            project_id=project_id,
            base_version_id=base_version_id,
            target_version_id=target_version_id,
            target_uses=target_uses,
            validity_results=validity_results,
            reattestations=reattestations,
            base_uses=base_uses,
        )

    @classmethod
    def render_html(cls, schedule: ExceptionsSchedule) -> str:
        """
        Renders Form E&O-2026 as printable SSR HTML.
        """
        return InvalidationEngine.render_form_eo_2026_html(schedule)

    @classmethod
    def render_html_schedule(cls, schedule: ExceptionsSchedule) -> str:
        """
        Renders Form E&O-2026 as printable SSR HTML with defensive XSS sanitization.
        """
        return InvalidationEngine.render_html_schedule(schedule)


# Top-level functional aliases for direct module invocation
def generate_exceptions_schedule(
    project_id: str,
    base_version_id: str,
    target_version_id: str,
    target_uses: List[CreativeUse],
    validity_results: List[DecisionValidity],
    reattestations: Optional[Dict[str, ReattestationRequest]] = None,
    base_uses: Optional[List[CreativeUse]] = None,
) -> ExceptionsSchedule:
    """Compiles a Form E&O-2026 Exceptions Schedule from version delta evaluation."""
    return ExceptionsScheduleEngine.generate_schedule(
        project_id=project_id,
        base_version_id=base_version_id,
        target_version_id=target_version_id,
        target_uses=target_uses,
        validity_results=validity_results,
        reattestations=reattestations,
        base_uses=base_uses,
    )


def render_form_eo_2026_html(schedule: ExceptionsSchedule) -> str:
    """Renders Form E&O-2026 HTML for underwriter review and counsel export."""
    return ExceptionsScheduleEngine.render_html(schedule)


def render_html_schedule(schedule: ExceptionsSchedule) -> str:
    """Renders Form E&O-2026 HTML for underwriter review and counsel export."""
    return ExceptionsScheduleEngine.render_html_schedule(schedule)


__all__ = [
    "CarrierHeader",
    "ExceptionsSchedule",
    "ExceptionsScheduleItem",
    "ExceptionsScheduleEngine",
    "generate_exceptions_schedule",
    "render_form_eo_2026_html",
    "render_html_schedule",
]
