"""
backend/services/agreement_verifier_rules.py

Rule evaluators and scoring engines for contract verification checklist.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

from typing import List, Tuple
from backend.services.agreement_verifier_types import (
    AgreementDocumentInput,
    ExecutionValidity,
    GrantScopeAnalysis,
    MediaScope,
    ProductionRequirements,
    RightType,
    TermScope,
    TerritoryScope,
    VerificationCitation,
    VerificationStatus,
)


def _check_signatures(doc: AgreementDocumentInput) -> Tuple[bool, bool, List[str], List[VerificationCitation]]:
    """Evaluates presence of licensor and licensee/producer signature blocks."""
    licensor_signed, licensee_signed = False, False
    citations: List[VerificationCitation] = []
    deficiencies: List[str] = []

    for sig in doc.signatures:
        role = sig.party_role.lower()
        if role == "licensor" and sig.is_signed:
            licensor_signed = True
            citations.append(VerificationCitation(
                clause_type="execution_licensor",
                quoted_clause=f"Executed by Licensor {sig.party_name} on {sig.signed_date or 'undated'}",
            ))
        elif role in ("licensee", "producer") and sig.is_signed:
            licensee_signed = True
            citations.append(VerificationCitation(
                clause_type="execution_licensee",
                quoted_clause=f"Executed by Licensee {sig.party_name} on {sig.signed_date or 'undated'}",
            ))

    if not licensor_signed:
        deficiencies.append("Missing licensor execution signature block.")
    if not licensee_signed:
        deficiencies.append("Missing licensee/producer execution signature block.")
    return licensor_signed, licensee_signed, deficiencies, citations


def evaluate_execution_validity(
    doc: AgreementDocumentInput,
    req: ProductionRequirements,
) -> Tuple[ExecutionValidity, List[VerificationCitation]]:
    """Verifies execution validity: signature block detection and production window date."""
    lic_signed, lse_signed, deficiencies, citations = _check_signatures(doc)
    is_date_valid = True

    if doc.execution_date and req.distribution_window_start:
        if doc.execution_date > req.distribution_window_start:
            is_date_valid = False
            deficiencies.append(
                f"Execution date {doc.execution_date} postdates distribution start {req.distribution_window_start}."
            )
        else:
            citations.append(VerificationCitation(
                clause_type="execution_date",
                quoted_clause=f"Agreement executed on {doc.execution_date} prior to distribution window.",
            ))

    exec_validity = ExecutionValidity(
        is_executed=(lic_signed and lse_signed),
        licensor_signed=lic_signed,
        licensee_signed=lse_signed,
        execution_date=doc.execution_date,
        is_date_within_window=is_date_valid,
        execution_deficiencies=deficiencies,
    )
    return exec_validity, citations


def _evaluate_territory(
    doc: AgreementDocumentInput,
    req: ProductionRequirements,
) -> Tuple[TerritoryScope, bool, List[str], List[VerificationCitation]]:
    """Evaluates territory scope: Worldwide vs Restricted."""
    citations, deficiencies = [], []
    doc_terr = [t.lower().strip() for t in doc.territories]
    raw = (doc.raw_text or "").lower() + " " + " ".join(doc_terr)
    is_ww = any(kw in raw for kw in ("worldwide", "universe", "all territories", "world"))

    if is_ww:
        citations.append(VerificationCitation(clause_type="territory", quoted_clause="Territory: Worldwide, all universe."))
        return TerritoryScope.WORLDWIDE, True, deficiencies, citations

    scope = TerritoryScope.NORTH_AMERICA if ("north america" in raw or ("usa" in doc_terr and "canada" in doc_terr)) else TerritoryScope.RESTRICTED
    if "worldwide" in req.required_territory.lower():
        deficiencies.append("Territory is restricted (Worldwide distribution required).")
        return scope, False, deficiencies, citations
    return scope, True, deficiencies, citations


def _evaluate_media(
    doc: AgreementDocumentInput,
    req: ProductionRequirements,
) -> Tuple[MediaScope, bool, bool, List[str], List[VerificationCitation]]:
    """Evaluates media scope: All media known or hereafter devised vs restricted."""
    citations, deficiencies = [], []
    combined = " ".join(doc.media).lower() + " " + (doc.raw_text or "").lower()
    has_devised = any(kw in combined for kw in ("now known or hereafter devised", "hereafter devised", "all media", "any and all media"))

    if has_devised:
        citations.append(VerificationCitation(clause_type="media", quoted_clause="Media: In any and all media now known or hereafter devised."))
        return MediaScope.ALL_MEDIA, True, True, deficiencies, citations

    doc_media = {m.lower().strip() for m in doc.media}
    missing = [m for m in req.required_media if m.lower().strip() not in doc_media]
    if missing:
        deficiencies.append(f"Restricted media scope: Missing {', '.join(missing)}.")
        return MediaScope.RESTRICTED, False, False, deficiencies, citations

    citations.append(VerificationCitation(clause_type="media", quoted_clause=f"Media granted: {', '.join(doc.media)}."))
    return MediaScope.ALL_MEDIA, True, False, deficiencies, citations


def _evaluate_term_and_rights(
    doc: AgreementDocumentInput,
    req: ProductionRequirements,
) -> Tuple[TermScope, bool, List[RightType], bool, List[str], List[VerificationCitation]]:
    """Evaluates term duration and atomic rights grants."""
    citations, deficiencies = [], []
    raw = (doc.raw_text or "").lower() + " " + (doc.term or "").lower()
    is_perpetual = any(kw in raw for kw in ("perpetual", "in perpetuity", "perpetuity"))
    term_scope = TermScope.PERPETUAL if is_perpetual else (TermScope.IN_LICENSE_TERM if (doc.term or doc.term_expiry) else TermScope.UNKNOWN)
    sat_term = is_perpetual if req.requires_perpetual else (term_scope != TermScope.UNKNOWN)
    if not sat_term:
        deficiencies.append(f"Term is non-perpetual: {doc.term or 'limited in-license term'}.")

    raw_rights = " ".join(doc.granted_rights).lower() + " " + raw
    detected: List[RightType] = []
    if "sync" in raw_rights or "synchronization" in raw_rights:
        detected.append(RightType.SYNCHRONIZATION)
    if "master" in raw_rights or "sound recording" in raw_rights:
        detected.append(RightType.MASTER_RECORDING)
    if "trademark" in raw_rights or "logo" in raw_rights or "appearance" in raw_rights:
        detected.append(RightType.TRADEMARK_APPEARANCE)

    missing = [r for r in req.required_rights if r not in detected]
    if missing:
        deficiencies.append(f"Missing required rights: {', '.join(r.value for r in missing)}.")
    return term_scope, sat_term, detected, len(missing) == 0, deficiencies, citations


def evaluate_grant_scope(
    doc: AgreementDocumentInput,
    req: ProductionRequirements,
) -> Tuple[GrantScopeAnalysis, List[str], List[VerificationCitation]]:
    """Comprehensive grant scope evaluator assessing territory, media, term, and rights."""
    t_scope, sat_t, def_t, cit_t = _evaluate_territory(doc, req)
    m_scope, sat_m, has_dev, def_m, cit_m = _evaluate_media(doc, req)
    term_scope, sat_term, rights, sat_r, def_tr, cit_tr = _evaluate_term_and_rights(doc, req)

    analysis = GrantScopeAnalysis(
        territory_scope=t_scope,
        permitted_territories=doc.territories,
        is_worldwide=(t_scope == TerritoryScope.WORLDWIDE),
        media_scope=m_scope,
        permitted_media=doc.media,
        has_all_media_devised=has_dev,
        term_scope=term_scope,
        is_perpetual=(term_scope == TermScope.PERPETUAL),
        term_expiry=doc.term_expiry,
        rights_granted=rights,
        satisfies_territory=sat_t,
        satisfies_media=sat_m,
        satisfies_term=sat_term,
        satisfies_rights=sat_r,
        scope_deficiencies=(def_t + def_m + def_tr),
    )
    return analysis, (def_t + def_m + def_tr), (cit_t + cit_m + cit_tr)


def calculate_compliance(
    exec_val: ExecutionValidity,
    scope: GrantScopeAnalysis,
    missing_clauses: List[str],
) -> Tuple[float, bool, bool, List[str], VerificationStatus]:
    """Calculates weighted compliance score and determines rider requirements."""
    weights = [
        (exec_val.licensor_signed, 0.15),
        (exec_val.licensee_signed, 0.10),
        (exec_val.is_date_within_window, 0.10),
        (scope.satisfies_territory, 0.20),
        (scope.satisfies_media, 0.20),
        (scope.satisfies_term, 0.15),
        (scope.satisfies_rights, 0.10),
    ]
    score = round(sum(w for cond, w in weights if cond), 2)
    rider_reasons: List[str] = []

    if not scope.satisfies_territory:
        rider_reasons.append("Counsel rider required: Territory restricted; territorial holdback or expansion needed.")
    if not scope.satisfies_term:
        rider_reasons.append("Counsel rider required: In-license term limitation; renewal step-up needed.")
    if not scope.satisfies_media:
        rider_reasons.append("Counsel rider required: Missing digital exploitation channels.")

    requires_rider = len(rider_reasons) > 0
    is_valid = exec_val.is_executed and (score >= 0.65)
    if not exec_val.is_executed or score < 0.50:
        status = VerificationStatus.REJECTED
    elif not is_valid:
        status = VerificationStatus.NON_COMPLIANT
    elif requires_rider:
        status = VerificationStatus.CONDITIONALLY_COMPLIANT
    else:
        status = VerificationStatus.VERIFIED_COMPLIANT

    return score, is_valid, requires_rider, rider_reasons, status
