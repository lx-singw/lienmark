"""
contract_redactor.py

Server-side PII and Sensitive Legal Clause Redaction Engine.
Enforces INV-S62-02 (zero-leak compensation and PII protection for non-legal roles).
Sprint 6.2: Evidence Explorer & Decision History.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Set

from backend.core.rbac import LienmarkRole


class ContractRedactor:
    """Server-side sanitization of private contract terms, PII, and financial figures."""

    LEGAL_ROLES: Set[LienmarkRole] = {LienmarkRole.ADMIN, LienmarkRole.REVIEWER}

    @classmethod
    def is_legal_role(cls, roles: Set[LienmarkRole]) -> bool:
        """Determines if the principal holds clearance counsel authority."""
        return bool(roles.intersection(cls.LEGAL_ROLES))

    @classmethod
    def redact_clause(cls, clause: Dict[str, Any], is_legal: bool) -> Dict[str, Any]:
        """Redacts sensitive compensation, tax IDs, and confidential tiers for non-legal callers."""
        clean = dict(clause)
        if is_legal:
            return clean
        text = str(clean.get("text", ""))
        text = re.sub(r"\$[0-9,]+(\.[0-9]{2})?", "[REDACTED COMPENSATION]", text)
        text = re.sub(r"\b\d{2}-\d{7}\b", "[REDACTED TAX ID]", text)
        clean["text"] = text
        if clean.get("confidentiality_tier") == "production_legal_only":
            clean["text"] = "[RESTRICTED: Legal Counsel Eyes Only]"
        return clean
