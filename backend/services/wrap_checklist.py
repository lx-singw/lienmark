"""
wrap_checklist.py

Post-Production Wrap Delivery Checklist Engine.
Sprint 6.3: Studio Deliverables.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
from backend.api.routes.underwriting_schemas import (
    WrapChecklistItem,
    WrapChecklistResponse,
)


class WrapChecklistEngine:
    """Evaluates clearance completeness to gate post-production distributor funds release."""

    CATEGORY_MAP = {
        "script": "Screenplay Chain of Title & WGA Accords",
        "screenplay": "Screenplay Chain of Title & WGA Accords",
        "music": "Music Synchronization & Master Use",
        "prop": "Prop House & Set Dressing Releases",
        "set_dressing": "Prop House & Set Dressing Releases",
        "visual_art": "Fine Art & Mural Releases",
        "trademark": "Trademarks & Brand Identifiers",
        "brand": "Trademarks & Brand Identifiers",
        "talent": "SAG-AFTRA & Background Likeness",
    }

    @classmethod
    def _evaluate_claim(cls, claim: Dict[str, Any], idx: int) -> WrapChecklistItem:
        """Evaluates a single claim against wrap clearance gating criteria."""
        cat_key = str(claim.get("right_category") or claim.get("category") or "general").lower()
        category = cls.CATEGORY_MAP.get(cat_key, "General Rights Clearance")
        title = claim.get("title") or claim.get("name") or f"Asset #{idx}"
        state = str(claim.get("state") or "").upper()
        status = str(claim.get("status") or "").upper()
        lin_key = claim.get("stable_lineage_key") or claim.get("lineage_key") or f"item_{idx}"

        if state in ("CARRIED_FORWARD", "RE_ATTESTED") or status == "APPROVED":
            return WrapChecklistItem(
                item_id=f"chk_{idx}",
                category=category,
                title=title,
                description="Affirmed and corroborated by counsel; clearance complete.",
                status="CLEARED",
                lineage_key=lin_key,
            )

        if state == "EXCEPTION" or status in ("EXCEPTION", "FLAGGED"):
            return WrapChecklistItem(
                item_id=f"chk_{idx}",
                category=category,
                title=title,
                description="Adverse claim scheduled on underwriter warranty exclusion rider.",
                status="CLEARED",
                lineage_key=lin_key,
            )

        return WrapChecklistItem(
            item_id=f"chk_{idx}",
            category=category,
            title=title,
            description="Pending counsel adjudication or missing executed license agreement.",
            status="BLOCKED",
            blocking_reason=f"Claim '{title}' has state '{state or status}'; requires counsel clearance.",
            lineage_key=lin_key,
        )

    @staticmethod
    def _empty_wrap_response(pid: str, off: bool, by: Optional[str], at: Optional[str]) -> WrapChecklistResponse:
        """Constructs empty checklist response when no claims are ingested."""
        return WrapChecklistResponse(
            production_id=pid, is_ready_for_funds_release=False, cleared_percentage=0.0,
            total_items=0, cleared_items=0,
            blocking_reasons=["Production has zero ingested claims. Run intake analysis first."],
            items=[], signed_off=off, signed_off_by=by, signed_off_at=at,
        )

    @classmethod
    def evaluate_wrap_checklist(
        cls,
        production_id: str,
        claims: List[Dict[str, Any]],
        signed_off: bool = False,
        signed_off_by: Optional[str] = None,
        signed_off_at: Optional[str] = None,
    ) -> WrapChecklistResponse:
        """Computes comprehensive wrap checklist gating distributor funds release."""
        if not claims:
            return cls._empty_wrap_response(production_id, signed_off, signed_off_by, signed_off_at)

        items = [cls._evaluate_claim(c, i) for i, c in enumerate(claims, start=1)]
        cleared = [item for item in items if item.status == "CLEARED"]
        blocked = [item for item in items if item.status == "BLOCKED"]
        blocking_reasons = [b.blocking_reason for b in blocked if b.blocking_reason]
        pct = round((len(cleared) / len(items)) * 100.0, 1)

        return WrapChecklistResponse(
            production_id=production_id,
            is_ready_for_funds_release=(len(blocked) == 0 and len(items) > 0),
            cleared_percentage=pct,
            total_items=len(items),
            cleared_items=len(cleared),
            blocking_reasons=blocking_reasons,
            items=items,
            signed_off=signed_off,
            signed_off_by=signed_off_by,
            signed_off_at=signed_off_at,
        )
