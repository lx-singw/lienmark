"""
tests/test_statutory_public_domain.py

Unit tests for 95-Year Rolling Public Domain Calculator (17 U.S.C. §§ 304, 302, 305).
Sprint 3.3 - Invariant: Deterministic mathematical outcomes across statutory regimes.
"""

import pytest

from backend.core.statutory_public_domain import eval_public_domain
from backend.core.statutory_types import (
    InvalidPublicationYearError,
    PublicDomainEvaluation,
    StatutoryEra,
)


def test_pre_1923_unconditionally_public_domain():
    """Works published before 1923 are unconditionally in the public domain."""
    for year in [1790, 1850, 1900, 1920, 1922]:
        result = eval_public_domain(year, reference_year=2026)
        assert isinstance(result, PublicDomainEvaluation)
        assert result.is_public_domain is True
        assert result.confidence == 1.0
        assert result.statutory_era == StatutoryEra.PRE_1923
        assert "unconditionally" in result.rationale.lower()


def test_1923_to_1977_rolling_threshold_boundary():
    """Asserts exact 95-year boundary expiration for 1923-1977 works."""
    # Reference year 2026: threshold = 2026 - 95 = 1931.
    res_1930 = eval_public_domain(1930, reference_year=2026)
    assert res_1930.is_public_domain is True
    assert res_1930.threshold_year == 1931
    assert res_1930.statutory_era == StatutoryEra.YEARS_1923_TO_1977

    res_1931 = eval_public_domain(1931, reference_year=2026)
    assert res_1931.is_public_domain is True

    res_1932 = eval_public_domain(1932, reference_year=2026)
    assert res_1932.is_public_domain is False
    assert "Protected through Dec 31" in res_1932.rationale
    assert "17 U.S.C." in res_1932.statutory_citation


def test_1923_to_1977_reference_year_2025():
    """Asserts threshold behavior against reference year 2025 (threshold 1930)."""
    res_1930 = eval_public_domain(1930, reference_year=2025)
    assert res_1930.is_public_domain is True
    assert res_1930.threshold_year == 1930

    res_1931 = eval_public_domain(1931, reference_year=2025)
    assert res_1931.is_public_domain is False


def test_post_1977_work_made_for_hire():
    """Asserts post-1977 works made for hire have 95-year term under 17 U.S.C. § 302(c)."""
    res_current = eval_public_domain(1985, reference_year=2026, is_work_made_for_hire=True)
    assert res_current.is_public_domain is False
    assert res_current.statutory_era == StatutoryEra.POST_1977
    assert res_current.is_work_made_for_hire is True

    # Future reference year 2085: threshold = 2085 - 95 = 1990
    res_future = eval_public_domain(1985, reference_year=2085, is_work_made_for_hire=True)
    assert res_future.is_public_domain is True


def test_post_1977_individual_author_with_death_year():
    """Asserts post-1977 individual works expire 70 years post-mortem (§ 302(a))."""
    # Author died in 1950, ref 2026: 1950 + 70 = 2020 < 2026 -> PD
    res_expired = eval_public_domain(1978, reference_year=2026, author_death_year=1950)
    assert res_expired.is_public_domain is True
    assert res_expired.confidence == 1.0

    # Author died in 1960, ref 2026: 1960 + 70 = 2030 > 2026 -> Protected
    res_protected = eval_public_domain(1978, reference_year=2026, author_death_year=1960)
    assert res_protected.is_public_domain is False
    assert res_protected.confidence == 1.0


def test_post_1977_individual_author_unknown_death():
    """Asserts post-1977 works without death year are protected before 2048."""
    res_2026 = eval_public_domain(1980, reference_year=2026)
    assert res_2026.is_public_domain is False
    assert res_2026.confidence == 1.0

    # Past 2048, confidence is lowered due to lack of death date
    res_2050 = eval_public_domain(1980, reference_year=2050)
    assert res_2050.is_public_domain is False
    assert res_2050.confidence == 0.5


def test_invalid_publication_year_exceptions():
    """Asserts typed exceptions on negative, zero, non-integer, or distant future years."""
    with pytest.raises(InvalidPublicationYearError):
        eval_public_domain(0, reference_year=2026)
    with pytest.raises(InvalidPublicationYearError):
        eval_public_domain(-100, reference_year=2026)
    with pytest.raises(InvalidPublicationYearError):
        eval_public_domain(2040, reference_year=2026)
    with pytest.raises(InvalidPublicationYearError):
        eval_public_domain("1920", reference_year=2026)  # type: ignore
