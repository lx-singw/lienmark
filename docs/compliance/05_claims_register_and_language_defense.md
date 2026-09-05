# Sprint 0B Claims Register, Language Defense & Submission Accuracy Audit

> **Hackathon**: Agentic Cinema: The Blockbuster Hackathon  
> **Evaluation Milestone**: Sprint 0B Task 4 — Claims Register & Language Defense Audit  
> **Track Focus**: Parallel Track ($15,000 Prize Pool) & Core Agentic Implementation  
> **Document Status**: Complete & Authoritative (Sprint 0B Task 4 Executed)  
> **Audited Date**: September 5, 2026  
> **Project**: [Lienmark — Clearance Change Control for E&O](https://github.com/lx-singw/lienmark)  
> **Author & Lead Architect**: Linda Singwane (`lx-singw`)  
> **Policy Version**: `E&O-2026.1-DEVPOST`  
> **Verification Verdict**: **100% AUDIT PASS / ZERO PROHIBITED CLAIMS / ALL ACTIVE ARTIFACTS CERTIFIED**

---

## 1. Executive Summary & Legal Defense Posture

In competitive hackathons, especially those evaluated by professional industry judges and corporate sponsors, the boundary between ambitious marketing and fraudulent or legally impermissible claims is decisive. Entertainment clearance and Errors & Omissions (E&O) insurance are heavily regulated, high-liability legal domains. Misrepresenting software as "title insurance," claiming "automated insurance binding," or asserting that an AI model "determines fair use" creates immediate disqualification risks, exposes productions to statutory liability, and alienates expert legal and underwriting judges.

Sprint 0B Task 4 establishes an immutable **Claims Register & Language Defense Matrix** for Lienmark. Every claim presented in the repository, submission video, Devpost description, and API metadata has been audited against demonstrable runtime capabilities.

```
+----------------------------------------------------------------------------------------------------+
|                                THE THREE RULES OF LIENMARK CLAIMS                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   1. IF WE CANNOT PROVE IT IN 60 SECONDS WITH TESTS, WE DO NOT CLAIM IT.                          |
|   2. THE SYSTEM NEVER CLEARS A CLAIM; THE SYSTEM RECOMMENDS A REVIEW STATE, AND COUNSEL DECIDES.   |
|   3. NO INSURANCE IS BOUND; A VERSION-BOUND FORM E&O-2026 EXCEPTIONS SCHEDULE IS EMITTED.          |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Defensible Claims Register (Empirically Verified)

The following claims are formally certified as defensible. Each claim maps directly to automated unit tests, integration benchmarks, and verified codebase symbols:

| Claim ID | Defensible Claim Statement | Codebase Proof Symbol | Automated Test Verification |
|---|---|---|---|
| **CLM-01** | *"Lienmark starts where a clearance report stops: maintaining whether prior decisions still apply to the current production cut."* | [`InvalidationEngine`](file:///Z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L28) | `test_drift_compare_and_review_flow` |
| **CLM-02** | *"Lienmark detects clearance drift across production revisions and refreshed external public evidence."* | [`InvalidationEngine.evaluate_drift`](file:///Z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L65) | `test_12_to_10_carried_2_reopened` |
| **CLM-03** | *"Each clearance decision is bound to the creative use, agreement facts, public-evidence snapshot, and production version that supported it."* | [`CounselDecision`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L94) | `test_golden_fixture_counts` |
| **CLM-04** | *"When a material dependency changes, Lienmark carries unaffected approvals forward fail-closed and reopens only impacted decisions."* | [`InvalidationEngine.evaluate_drift`](file:///Z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L90) | `test_fail_closed_policy` |
| **CLM-05** | *"Parallel Search performs targeted live re-verification for affected claims rather than rerunning a generic, costly full report."* | [`ParallelSearchService.search`](file:///Z:/home/lx_singw/projects/lienmark/backend/services/parallel_service.py#L29) | `test_workflow_execution` |
| **CLM-06** | *"On the 12-item golden fixture, Lienmark reduces legal re-review by 83.33% (10 carried forward, 2 reopened) with 0.0% false carry-forwards."* | [`evaluate_golden_drift`](file:///Z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L236) | `test_12_to_10_carried_2_reopened` |
| **CLM-07** | *"The final deliverable is a version-bound Form E&O-2026 Exceptions Schedule displaying carried, re-attested, and active exception items."* | [`ExceptionsSchedule`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L142) | `test_exceptions_schedule_reconciliation` |
| **CLM-08** | *"The software does not practice law or bind insurance; clearance counsel retains full agency and adjudicative responsibility."* | [`ReattestationRequest`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L121) | `test_p0_scope_boundary_and_contract` |

---

## 3. Prohibited & Unsupported Claims Register

The following statements are strictly prohibited across all Lienmark code, documentation, UI strings, and submission presentations:

| Forbidden Phrase / Category | Why It Is Prohibited | Mandatory Safe Alternative |
|---|---|---|
| **"Title insurance for film IP"** | Legally false. Software cannot issue statutory indemnity policies or hold capital reserves. | *"Clearance change control for E&O"* |
| **"Automated policy binding" / "Instant E&O insurance"** | Factually impossible. No motion picture underwriter allows automated API policy issuance. | *"Export / API for underwriting warranty review"* |
| **"Guarantees coverage" / "Eliminates legal liability"** | Legally untenable. Violates insurance contract law and guarantees unauthorized legal outcome. | *"Mitigates clearance drift and maintains defensible audit lineage"* |
| **"Clears the claim" / "AI clears your movie"** | Unauthorized Practice of Law (UPL). Software provides structured evidence; attorneys clear claims. | *"Recommends a review state; counsel decides"* |
| **"Determines fair use" / "Fair use scoring engine"** | U.S. fair use (17 U.S.C. § 107) is an affirmative defense decided exclusively by federal judges. | *"Synthesizes statutory factor checklists for counsel deliberation"* |
| **"First or only AI clearance platform"** | Factually inaccurate and unprovable. Adjacent competitors claim overlapping features. | *"First clearance change control platform with dependency-aware selective invalidation"* |
| **"Chubb / Hiscox integrated API"** | Deceptive without an authorized, formal corporate partnership contract. | *"Designed to populate standard insurer underwriting schedules (Form E&O-2026)"* |
| **"RSA-256 digital legal audit"** | Cryptographically nonsensical terminology (RSA uses key sizes like 2048/4096; SHA-256 is a digest). | *"Tamper-evident audit event log with SHA-256 digest verification"* |
| **"ISO 27001 legal audit manifest"** | Misuse of ISO terminology. ISO 27001 is an organizational ISMS standard, not a document export. | *"Structured audit trail export"* |
| **"100% autonomous rights clearance"** | Contradicts human-in-the-loop legal ethics rules (ABA Model Rule 5.3). | *"Human-in-the-loop counsel re-attestation workflow"* |

---

## 4. Language Substitution Matrix

All submission artifacts, comments, docstrings, and frontend components adhere strictly to this substitution standard:

```
+----------------------------------------------------+---------------------------------------------------------------+
|                       AVOID                        |                              USE                              |
+----------------------------------------------------+---------------------------------------------------------------+
|  "verifies ownership"                              |  "retrieves attributable public evidence regarding ownership" |
|  "clears the claim"                                |  "recommends review state; counsel decides"                   |
|  "immutable ledger"                                |  "append-only decision history"                               |
|  "insurer-grade"                                   |  "structured for E&O underwriter review"                      |
|  "E&O certificate"                                 |  "version-bound exceptions schedule (Form E&O-2026)"          |
|  "automatic policy binding"                        |  "export for underwriter warranty review"                     |
|  "legal risk score"                                |  "policy-based review priority"                               |
|  "title insurance for IP"                          |  "clearance change control for E&O"                           |
|  "AI lawyer / counsel"                             |  "AI decision support for clearance counsel"                  |
|  "legal clearance guarantee"                       |  "fail-closed drift detection and dependency tracking"        |
+----------------------------------------------------+---------------------------------------------------------------+
```

---

## 5. Comprehensive Repository & Submission Audit Log

A systematic audit across all repository files confirms zero occurrences of prohibited phrases in active code, configuration, or submission-facing documentation:

### 5.1 Documentation Audit Summary

| File Audited | Prohibited Terms Found | Corrective Action Taken | Current Audit Status |
|---|---|---|---|
| [`README.md`](file:///Z:/home/lx_singw/projects/lienmark/README.md) | None | Category frozen as Clearance Change Control; clean AntiGravity badge | **PASS** |
| [`docs/DEVPOST_SUBMISSION.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/DEVPOST_SUBMISSION.md) | None | Exact 3-minute video script audited; 12 -> 10/2 -> 1/1 verified | **PASS** |
| [`docs/TARGET_ARCHITECTURE.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/TARGET_ARCHITECTURE.md) | None | Modernized Next.js App Router + FastAPI Cloud Run architecture | **PASS** |
| [`docs/EVALUATION_AND_TRACEABILITY.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/EVALUATION_AND_TRACEABILITY.md) | None | Empirical test-to-claim mapping; zero unsupported metric claims | **PASS** |
| [`docs/compliance/01_stage1_eligibility_gate.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/compliance/01_stage1_eligibility_gate.md) | None | 20/20 Stage 1 eligibility gates verified | **PASS** |
| [`docs/compliance/02_provenance_inventory_and_remediation.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/compliance/02_provenance_inventory_and_remediation.md) | None | Full AI provenance recorded under Devpost Topic 44644 ruling | **PASS** |
| [`docs/compliance/03_technical_gate_proofs.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/compliance/03_technical_gate_proofs.md) | None | Technical proofs for Gemini 2.5 Flash & Parallel Search captured | **PASS** |
| [`docs/compliance/04_scope_demolition_and_p0_boundary.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/compliance/04_scope_demolition_and_p0_boundary.md) | None | P0 vs P1 vs Deferred boundaries locked; kill criteria frozen | **PASS** |
| [`docs/compliance/06_acceptance_contract_and_golden_fixtures.md`](file:///Z:/home/lx_singw/projects/lienmark/docs/compliance/06_acceptance_contract_and_golden_fixtures.md) | None | 12 -> 10/2 -> 1/1 acceptance contract mathematically sealed | **PASS** |

### 5.2 Codebase Configuration Audit Summary

| File Audited | Legacy Terms Sanitized | Replacement Standard Applied |
|---|---|---|
| [`backend/config/preset_profiles.json`](file:///Z:/home/lx_singw/projects/lienmark/backend/config/preset_profiles.json) | Sanitized `can_bind_insurance`, `ENABLE_DUAL_KEY_DIGITAL_SIGNATURES`, `ENABLE_ISO_LEGAL_AUDIT_EXPORTER`, `ENABLE_CHAIN_OF_TITLE_CERT_GENERATOR` | Replaced with `ENABLE_COUNSEL_ATTESTATION_TRACKER`, `ENABLE_AUDIT_TRAIL_EXPORTER`, `ENABLE_EXCEPTIONS_SCHEDULE_GENERATOR`, `ENABLE_POLICY_REVIEW_PRIORITY` |
| [`backend/config/feature_iam_policy.json`](file:///Z:/home/lx_singw/projects/lienmark/backend/config/feature_iam_policy.json) | Removed `can_bind_insurance` capability from all roles | Replaced with `can_export_exceptions_schedule` (advisory export only) |
| [`backend/config/clearance_config.json`](file:///Z:/home/lx_singw/projects/lienmark/backend/config/clearance_config.json) | Sanitized legacy toggles matching outdated claims | Harmonized with P0 capability toggles |

---

## 6. Automated Scope & Claims Enforcement Test

To guarantee that no future commits or contributors introduce prohibited claims or out-of-scope modules, the automated AST and regex test [`tests/test_scope_boundary.py`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_scope_boundary.py) enforces the following rules on every test execution:

```python
# Verified excerpt from tests/test_scope_boundary.py
def test_p0_scope_boundary_and_contract():
    # 1. Assert zero prohibited / deferred architectural symbols
    prohibited_modules = [
        "blockchain", "crypto_ledger", "carrier_binding_api",
        "peer_bus", "video_cv_scanner", "smart_contract"
    ]
    ...
    # 2. Assert single-sentence demo contract
    expected_statement = (
        "Lienmark is the change-triggered, version-bound evidence and sign-off layer "
        "that detects clearance drift across script revisions, cuts, and refreshed public evidence."
    )
    ...
    # 3. Assert mathematical 12 -> 10/2 -> 1/1 invariants
    assert drift_result.total_claims == 12
    assert drift_result.carried_forward == 10
    assert drift_result.reopened_claims == 2
```

### Test Suite Execution Proof
```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 11 items

tests/test_api_endpoints.py::test_health_endpoints PASSED                [  9%]
tests/test_api_endpoints.py::test_fixtures_endpoint PASSED               [ 18%]
tests/test_api_endpoints.py::test_drift_compare_and_review_flow PASSED   [ 27%]
tests/test_api_endpoints.py::test_dashboard_html PASSED                  [ 36%]
tests/test_e2e_pipeline.py::test_workflow_execution PASSED               [ 45%]
tests/test_e2e_pipeline.py::test_full_review_to_exceptions_schedule_flow PASSED [ 54%]
tests/test_invalidation_engine.py::test_golden_fixture_counts PASSED     [ 63%]
tests/test_invalidation_engine.py::test_12_to_10_carried_2_reopened PASSED [ 72%]
tests/test_invalidation_engine.py::test_fail_closed_policy PASSED        [ 81%]
tests/test_invalidation_engine.py::test_exceptions_schedule_reconciliation PASSED [ 90%]
tests/test_scope_boundary.py::test_p0_scope_boundary_and_contract PASSED [100%]

======================== 11 passed, 1 warning in 1.31s ========================
```

---

## 7. Formal Compliance Certification

I hereby certify on behalf of the Lienmark project:
1. **Accuracy of Statements**: All statements in `README.md`, `docs/DEVPOST_SUBMISSION.md`, `docs/TARGET_ARCHITECTURE.md`, and `docs/EVALUATION_AND_TRACEABILITY.md` accurately reflect the actual implemented code in `backend/` and `frontend/`.
2. **Zero Unauthorized Claims**: No claim of automated insurance binding, statutory title insurance, or autonomous legal representation is made.
3. **Reproducible Demonstrability**: Every claim regarding review reduction, deterministic invalidation, and external evidence grounding is reproducible in under 60 seconds using the provided test suite.

**Signed**:  
*Linda Singwane (`lx-singw`)*  
Lead Architect & Developer, Project Lienmark  
September 5, 2026
