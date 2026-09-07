"""
backend/core/conflict_checker.py

Ethical wall and declared conflict-of-interest screening engine for legal counsel.
Sprint 5.2: Accountable Dual-Review Clearance Sign-Off.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import re
import threading
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConflictCheckResult(BaseModel):
    """Result schema for counsel ethical conflict-of-interest screening."""
    has_conflict: bool
    conflicted_parties: List[str] = Field(default_factory=list)
    details: Optional[str] = None


def _normalize_entity(name: str) -> str:
    """Normalizes entity name for case-insensitive matching."""
    if not name:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", name)
    return " ".join(cleaned.lower().split())


class ConflictRegistry:
    """Thread-safe in-memory registry of declared counsel ethical conflicts."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._conflicts: Dict[str, Dict[str, str]] = {}
        self._seed_default_conflicts()

    def _seed_default_conflicts(self) -> None:
        """Seeds initial realistic ethical walls and adverse representation conflicts."""
        self._conflicts["counsel_conflicted_001"] = {
            "paramount pictures": "Adverse representation in copyright arbitration (Ethical Wall EW-2025-01)",
            "acme productions": "Client adverse conflict declared under ABA Model Rule 1.7",
        }
        self._conflicts["counsel_lead_002_conflicted"] = {
            "warner bros discovery": "Mandatory ethical wall under Rule 1.7 (Prior client adverse engagement)",
        }

    def register(
        self,
        counsel_id: str,
        conflicted_entities: List[str],
        details: Optional[str] = None,
    ) -> None:
        """Registers declared adverse entities for a counsel principal."""
        with self._lock:
            if counsel_id not in self._conflicts:
                self._conflicts[counsel_id] = {}
            for entity in conflicted_entities:
                norm = _normalize_entity(entity)
                if norm:
                    self._conflicts[counsel_id][norm] = details or f"Declared adverse conflict with {entity}"

    def get_conflicts(self, counsel_id: str) -> Dict[str, str]:
        """Retrieves declared conflicts for a specific counsel principal."""
        with self._lock:
            return dict(self._conflicts.get(counsel_id, {}))

    def clear(self, counsel_id: Optional[str] = None) -> None:
        """Clears declared conflicts for counsel or resets entire registry."""
        with self._lock:
            if counsel_id:
                self._conflicts.pop(counsel_id, None)
            else:
                self._conflicts.clear()


_GLOBAL_CONFLICT_REGISTRY = ConflictRegistry()


def register_counsel_conflict(
    counsel_id: str,
    conflicted_entities: List[str],
    details: Optional[str] = None,
) -> None:
    """Registers declared adverse parties or ethical walls for a counsel principal."""
    _GLOBAL_CONFLICT_REGISTRY.register(counsel_id, conflicted_entities, details)


def clear_conflict_registry(counsel_id: Optional[str] = None) -> None:
    """Clears declared conflicts for a specific counsel or resets the registry."""
    _GLOBAL_CONFLICT_REGISTRY.clear(counsel_id)


def get_declared_conflicts(counsel_id: str) -> Dict[str, str]:
    """Retrieves map of normalized conflicted entities and their details for counsel."""
    return _GLOBAL_CONFLICT_REGISTRY.get_conflicts(counsel_id)


def check_counsel_conflict(
    counsel_id: str,
    entity_names: List[str],
) -> ConflictCheckResult:
    """
    Checks counsel against declared conflict-of-interest registry.
    Checks adverse representations and studio ethical walls for declared entity matches.
    """
    declared = _GLOBAL_CONFLICT_REGISTRY.get_conflicts(counsel_id)
    if not declared or not entity_names:
        return ConflictCheckResult(has_conflict=False, conflicted_parties=[], details=None)

    conflicted_parties: List[str] = []
    conflict_notes: List[str] = []

    for entity in entity_names:
        norm_ent = _normalize_entity(entity)
        if not norm_ent:
            continue
        for norm_conf, note in declared.items():
            if norm_ent == norm_conf or norm_conf in norm_ent or norm_ent in norm_conf:
                conflicted_parties.append(entity)
                conflict_notes.append(f"{entity}: {note}")
                break

    if conflicted_parties:
        return ConflictCheckResult(
            has_conflict=True,
            conflicted_parties=conflicted_parties,
            details="; ".join(conflict_notes),
        )

    return ConflictCheckResult(has_conflict=False, conflicted_parties=[], details=None)
