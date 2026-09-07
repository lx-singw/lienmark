"""
tests/test_conflict_checker.py

Unit tests for counsel ethical conflict screening and ethical wall registry.
Sprint 5.2: Accountable Dual-Review Clearance Sign-Off.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

import pytest
from backend.core.conflict_checker import (
    ConflictCheckResult,
    check_counsel_conflict,
    clear_conflict_registry,
    get_declared_conflicts,
    register_counsel_conflict,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Ensures clean state for tests."""
    clear_conflict_registry()
    yield
    clear_conflict_registry()


def test_conflict_checker_no_conflict():
    result = check_counsel_conflict("counsel_clean_001", ["Warner Bros", "Legendary"])
    assert isinstance(result, ConflictCheckResult)
    assert not result.has_conflict
    assert result.conflicted_parties == []
    assert result.details is None


def test_conflict_checker_detected_conflict():
    register_counsel_conflict(
        counsel_id="counsel_001",
        conflicted_entities=["Paramount Pictures", "Skydance"],
        details="Prior client adverse representation in litigation",
    )
    result = check_counsel_conflict("counsel_001", ["Paramount Pictures", "Universal"])
    assert result.has_conflict
    assert "Paramount Pictures" in result.conflicted_parties
    assert "Universal" not in result.conflicted_parties
    assert result.details is not None
    assert "Paramount Pictures" in result.details


def test_conflict_checker_case_insensitive_and_punctuation():
    register_counsel_conflict(
        counsel_id="counsel_002",
        conflicted_entities=["Acme, Corp."],
        details="Ethical wall EW-12",
    )
    result = check_counsel_conflict("counsel_002", ["acme corp"])
    assert result.has_conflict
    assert len(result.conflicted_parties) == 1


def test_conflict_registry_clear():
    register_counsel_conflict(
        counsel_id="counsel_003",
        conflicted_entities=["Sony Music"],
        details="Adverse audit",
    )
    assert len(get_declared_conflicts("counsel_003")) > 0
    clear_conflict_registry("counsel_003")
    assert len(get_declared_conflicts("counsel_003")) == 0
    result = check_counsel_conflict("counsel_003", ["Sony Music"])
    assert not result.has_conflict
