"""
backend/core/statutory_public_domain.py

95-Year Rolling Public Domain Calculator under 17 U.S.C. §§ 304, 302, and 305.
Sprint 3.3 - Pure deterministic Python calculation across historical copyright eras.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from backend.core.statutory_types import (
    InvalidPublicationYearError,
    PublicDomainEvaluation,
    StatutoryEra,
)

CITATION_PRE_1923 = "17 U.S.C. §§ 304, 305; Pub. L. 105-298 (Sonny Bono Copyright Term Extension Act)"
CITATION_1923_1977 = "17 U.S.C. §§ 304(a)-(b), 305 (95-year renewal term from publication)"
CITATION_POST_1977 = "17 U.S.C. §§ 302(a), (c), 305 (Copyright Act of 1976)"


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


def _resolve_pre_1923(
    pub_year: int, ref_year: int, thresh_year: int, eval_date: date, jur: str, wt: str, vf: bool
) -> PublicDomainEvaluation:
    conf = 1.0 if vf else 0.8
    return PublicDomainEvaluation(
        is_public_domain=True,
        confidence=conf,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.PRE_1923,
        statutory_citation=CITATION_PRE_1923,
        rationale=f"Work published in {pub_year} (< 1923) is unconditionally in U.S. public domain.",
        is_work_made_for_hire=False,
        author_death_year=None,
        evaluation_date=eval_date,
        jurisdiction=jur,
        work_type=wt,
        applicable_term="Pre-1923 rules",
        verified_facts=vf,
    )


def _resolve_1923_to_1977(
    pub_year: int, ref_year: int, thresh_year: int, eval_date: date, jur: str, wt: str, vf: bool
) -> PublicDomainEvaluation:
    is_pd = pub_year <= thresh_year
    expiry = pub_year + 95
    rat = (
        f"Published in {pub_year} <= rolling threshold {thresh_year} ({ref_year} - 96). Term expired Dec 31, {expiry}."
        if is_pd
        else f"Published in {pub_year} > threshold {thresh_year}. Protected through Dec 31, {expiry}, entering PD Jan 1, {expiry+1}."
    )
    conf = 1.0 if vf else 0.8
    return PublicDomainEvaluation(
        is_public_domain=is_pd,
        confidence=conf,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.YEARS_1923_TO_1977,
        statutory_citation=CITATION_1923_1977,
        rationale=rat,
        is_work_made_for_hire=False,
        author_death_year=None,
        evaluation_date=eval_date,
        jurisdiction=jur,
        work_type=wt,
        applicable_term="95 years from publication",
        verified_facts=vf,
    )


def _resolve_post_1977_wfh(
    pub_year: int, ref_year: int, thresh_year: int, death_year: Optional[int], eval_date: date, jur: str, wt: str, vf: bool
) -> PublicDomainEvaluation:
    is_pd = pub_year <= thresh_year
    exp = pub_year + 95
    rat = (
        f"Work made for hire published in {pub_year} <= {thresh_year}; 95-year term expired Dec 31, {exp}."
        if is_pd
        else f"Work made for hire published in {pub_year}; protected through Dec 31, {exp} under § 302(c)."
    )
    conf = 1.0 if vf else 0.8
    return PublicDomainEvaluation(
        is_public_domain=is_pd,
        confidence=conf,
        publication_year=pub_year,
        reference_year=ref_year,
        threshold_year=thresh_year,
        statutory_era=StatutoryEra.POST_1977,
        statutory_citation=CITATION_POST_1977,
        rationale=rat,
        is_work_made_for_hire=True,
        author_death_year=death_year,
        evaluation_date=eval_date,
        jurisdiction=jur,
        work_type=wt,
        applicable_term="95 years from publication",
        verified_facts=vf,
    )


def _resolve_post_1977_individual(
    pub_year: int, ref_year: int, thresh_year: int, death_year: Optional[int], eval_date: date, jur: str, wt: str, vf: bool
) -> PublicDomainEvaluation:
    if death_year is not None:
        term_end = death_year + 70
        is_pd = ref_year > term_end
        rat = (
            f"Author died in {death_year}. 70-year post-mortem term expired Dec 31, {term_end}."
            if is_pd
            else f"Author died in {death_year}. Protected for life + 70 years through Dec 31, {term_end}."
        )
        conf = 1.0 if vf else 0.8
    else:
        is_pd = False
        if ref_year < 2048:
            conf = 1.0 if vf else 0.8
        else:
            conf = 0.5 if vf else 0.4
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
        evaluation_date=eval_date,
        jurisdiction=jur,
        work_type=wt,
        applicable_term="Life of author + 70 years",
        verified_facts=vf,
    )


def eval_public_domain(
    publication_year: int,
    reference_year: Optional[int] = None,
    is_work_made_for_hire: bool = False,
    author_death_year: Optional[int] = None,
    evaluation_date: Optional[date] = None,
    jurisdiction: str = "US",
    work_type: str = "unspecified",
    verified_facts: bool = True,
) -> PublicDomainEvaluation:
    if evaluation_date is None:
        evaluation_date = datetime.now(timezone.utc).date()
    if reference_year is None:
        reference_year = evaluation_date.year
        
    _validate_publication_year(publication_year, reference_year)
    thresh_year = reference_year - 96

    if publication_year < 1923:
        return _resolve_pre_1923(publication_year, reference_year, thresh_year, evaluation_date, jurisdiction, work_type, verified_facts)
    if publication_year <= 1977:
        return _resolve_1923_to_1977(publication_year, reference_year, thresh_year, evaluation_date, jurisdiction, work_type, verified_facts)
    if is_work_made_for_hire:
        return _resolve_post_1977_wfh(publication_year, reference_year, thresh_year, author_death_year, evaluation_date, jurisdiction, work_type, verified_facts)
    return _resolve_post_1977_individual(publication_year, reference_year, thresh_year, author_death_year, evaluation_date, jurisdiction, work_type, verified_facts)
