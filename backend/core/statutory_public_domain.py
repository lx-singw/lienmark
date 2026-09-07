"""
backend/core/statutory_public_domain.py

95-Year Rolling Public Domain Calculator under 17 U.S.C. §§ 304, 302, and 305.
Sprint 3.3 - Pure deterministic Python calculation across historical copyright eras.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from backend.core.statutory_types import (
    InvalidPublicationYearError,
    PublicDomainEvaluation,
    StatutoryEra,
)

CITATION_PRE_1923 = "17 U.S.C. § 304; Pub. L. 105-298 (Sonny Bono Copyright Term Extension Act)"
CITATION_1923_1977 = "17 U.S.C. § 304(a)-(b) (95-year renewal term from publication)"
CITATION_POST_1977 = "17 U.S.C. § 302(a), (c) (Copyright Act of 1976)"


def _validate_publication_year(pub_year: int, ref_year: int) -> None:
    """Ensures publication year is a valid positive integer within physical bounds."""
    if not isinstance(pub_year, int) or isinstance(pub_year, bool):
        raise InvalidPublicationYearError(f"publication_year must be an integer, got {type(pub_year).__name__}")
    if pub_year < 1:
        raise InvalidPublicationYearError(f"publication_year must be positive, got {pub_year}")
    if pub_year > ref_year + 5:
        raise InvalidPublicationYearError(
            f"publication_year {pub_year} cannot exceed reference year {ref_year} + 5"
        )


def _resolve_pre_1923(pub_year: int, ref_year: int, thresh_year: int) -> PublicDomainEvaluation:
    """Resolves works published prior to 1923 (unconditionally public domain)."""
    return PublicDomainEvaluation(
        is_public_domain=True,
        confidence=1.0,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.PRE_1923,
        statutory_citation=CITATION_PRE_1923,
        rationale=f"Work published in {pub_year} (< 1923) is unconditionally in U.S. public domain.",
        is_work_made_for_hire=False,
        author_death_year=None,
    )


def _resolve_1923_to_1977(pub_year: int, ref_year: int, thresh_year: int) -> PublicDomainEvaluation:
    """Resolves 1923-1977 works under 95-year statutory renewal rule (17 U.S.C. § 304)."""
    is_pd = pub_year <= thresh_year
    expiry = pub_year + 95
    rat = (
        f"Published in {pub_year} <= rolling threshold {thresh_year} ({ref_year} - 95). Term expired."
        if is_pd
        else f"Published in {pub_year} > threshold {thresh_year}. Protected through Dec 31, {expiry}."
    )
    return PublicDomainEvaluation(
        is_public_domain=is_pd,
        confidence=1.0,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.YEARS_1923_TO_1977,
        statutory_citation=CITATION_1923_1977,
        rationale=rat,
        is_work_made_for_hire=False,
        author_death_year=None,
    )


def _resolve_post_1977_wfh(
    pub_year: int, ref_year: int, thresh_year: int, death_year: Optional[int]
) -> PublicDomainEvaluation:
    """Resolves post-1977 work-for-hire (95 years from publication under § 302(c))."""
    is_pd = pub_year <= thresh_year
    exp = pub_year + 95
    rat = (
        f"Work made for hire published in {pub_year} <= {thresh_year}; 95-year term expired."
        if is_pd
        else f"Work made for hire published in {pub_year}; protected through Dec 31, {exp} under § 302(c)."
    )
    return PublicDomainEvaluation(
        is_public_domain=is_pd,
        confidence=1.0,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.POST_1977,
        statutory_citation=CITATION_POST_1977,
        rationale=rat,
        is_work_made_for_hire=True,
        author_death_year=death_year,
    )


def _resolve_post_1977_individual(
    pub_year: int, ref_year: int, thresh_year: int, death_year: Optional[int]
) -> PublicDomainEvaluation:
    """Resolves post-1977 works by individual authors (life+70 under § 302(a))."""
    if death_year is not None:
        term_end = death_year + 70
        is_pd = ref_year > term_end
        rat = (
            f"Author died in {death_year}. 70-year post-mortem term expired Dec 31, {term_end}."
            if is_pd
            else f"Author died in {death_year}. Protected for life + 70 years through Dec 31, {term_end}."
        )
        conf = 1.0
    else:
        is_pd = False
        conf = 1.0 if ref_year < 2048 else 0.5
        rat = (
            f"Published post-1977 under § 302(a). Earliest theoretical expiry is 2048; protected."
            if ref_year < 2048
            else f"Published post-1977 under § 302(a). Expiry requires author death year beyond 2048."
        )

    return PublicDomainEvaluation(
        is_public_domain=is_pd,
        confidence=conf,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.POST_1977,
        statutory_citation=CITATION_POST_1977,
        rationale=rat,
        is_work_made_for_hire=False,
        author_death_year=death_year,
    )


def eval_public_domain(
    publication_year: int,
    reference_year: Optional[int] = None,
    is_work_made_for_hire: bool = False,
    author_death_year: Optional[int] = None,
) -> PublicDomainEvaluation:
    """
    Evaluates copyright status under 95-Year Rolling Public Domain Calculator (17 U.S.C. § 304).
    Pure deterministic formula: works published <= reference_year - 95 are public domain.
    """
    if reference_year is None:
        reference_year = datetime.now(timezone.utc).year
    _validate_publication_year(publication_year, reference_year)
    thresh_year = reference_year - 95

    if publication_year < 1923:
        return _resolve_pre_1923(publication_year, reference_year, thresh_year)
    if publication_year <= 1977:
        return _resolve_1923_to_1977(publication_year, reference_year, thresh_year)
    if is_work_made_for_hire:
        return _resolve_post_1977_wfh(publication_year, reference_year, thresh_year, author_death_year)
    return _resolve_post_1977_individual(publication_year, reference_year, thresh_year, author_death_year)
