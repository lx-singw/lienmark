# Lienmark — Clearance Change Control for E&O

[![Agentic Cinema: Parallel Track](https://img.shields.io/badge/Hackathon-Agentic%20Cinema%20(Parallel%20Track)-38bdf8)](https://agentic-cinema.devpost.com/)
[![Toolchain-Google AntiGravity](https://img.shields.io/badge/Toolchain-Google%20AntiGravity%20(Approved)-10b981)](https://agentic-cinema.devpost.com/forum_topics/44644-question-about-the-ai-usage-limitation-grafana-track)
[![Tests Passing](https://img.shields.io/badge/Pytest-463%2F463%20Passing-emerald)](tests/)
[![Quality Gate](https://img.shields.io/badge/Quality%20Gate-5%2F5%20Passing-blue)](scripts/run_quality_gate.py)
[![Query Reduction](https://img.shields.io/badge/Query%20Reduction-83.3%25%20Saved-purple)](#-the-core-magic-moment-12--102--11)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Detect clearance drift, selectively revalidate affected evidence, and keep sign-offs aligned with every production version.**

Lienmark is clearance change control for E&O: it determines whether prior entertainment-rights clearance decisions still carry forward when a film's cut or attributable external evidence changes. Rather than a generic search report or contract scanner, Lienmark binds counsel clearance decisions to a deterministic dependency graph. When a cut changes, Lienmark carries unaffected approvals forward, reopens only affected claims, uses **Parallel Search API** for targeted live re-investigation, and produces an underwriter-ready **Exceptions Schedule**.

---

## ⚡ 60-Second Judge Verification & Reproduction Suite

Judges can verify all technical implementations, fail-closed dependency evaluations, live integration calls, and reproduction commands:

```bash
# 1. Run Master 5-Gate Quality Runner (Deterministic CI, Rehearsal, Smoke, Next.js, AST)
python scripts/run_quality_gate.py

# 2. Run First Complete Rehearsal Harness (7 Phases, 6 Invariants, 44ms runtime)
python scripts/run_rehearsal.py

# 3. Run Live Integration Smoke Probe (Gemini 2.5 Flash, Parallel Search, Agent Builder)
python scripts/run_live_smoke.py

# 4. Run Automated Feature Freeze Auditor (Release candidate baseline lock)
python scripts/verify_feature_freeze.py

# 5. Run Video Take Recording Harness (Three clean deployed runs telemetry)
python scripts/record_take_harness.py

# 6. Run Submission Consistency Validator (Artifact parity across all 7 surfaces)
python scripts/verify_submission_consistency.py

# 7. Run Open-Source License Compliance Audit (20/20 OSI-Approved Permissive)
python scripts/run_license_audit.py

# 8. Run Complete Deterministic Test Suite (463+ passed)
python -m pytest tests/ -v

# 9. Run 10-Second CLI Integration Verification Suite
python scripts/verify_integrations.py

# 10. Launch Interactive Reviewer Dashboard & REST API
python -m uvicorn backend.main:app --reload --port 8000

# 11. Launch Interactive Next.js 15 App Router Frontend
cd frontend && npm run dev
```
Open **`http://localhost:8000`** (or Next.js UI at **`http://localhost:3000`**) in your browser to experience the interactive clearance change control workflow.

---

## 🎬 The Core Magic Moment (12 → 10/2 → 1/1)

Lienmark demonstrates a real Hollywood entertainment clearance scenario comparing **Version 7** (Baseline) vs **Version 8** (Revision):

1. **12 Prior Approvals (V7):** Baseline screenplay has 12 counsel-approved clearance items (props, set dressings, art, wardrobe, music) locked under Policy Standard `E&O-2026.1-DEVPOST`.
2. **Version 8 Ingestion & Semantic Drift:**
   - **Creative Drift:** Item 11 (*Crime Detective Magazine* poster, Scene 42) was a 2-second background blur in V7. In V8, the director zooms in for 14 seconds of focal dialogue where the protagonist reads the headline aloud (`CREATIVE_CONTEXT_ALTERED`).
   - **External Evidence Drift:** Item 12 (*Midnight Serenade* jazz cue, Scene 18) was approved as public domain. In V8, the script is unchanged, but live **Parallel Search** retrieves an August 2026 worldwide exclusive copyright assignment to *Vanguard Media Holdings LLC* (`EXTERNAL_EVIDENCE_SHIFT`).
3. **Deterministic Invalidation:**
   - **10 Claims Carried Forward:** Unaffected items carry forward automatically with fail-closed deterministic verification. Zero search calls issued.
   - **2 Claims Reopened (Stale):** Exactly 2 claims require counsel attention with explicit reason codes (`CREATIVE_CONTEXT_ALTERED` and `EXTERNAL_EVIDENCE_SHIFT`).
4. **Targeted Parallel Re-Investigation:**
   - Parallel Search queries US Copyright Office renewal records for the poster (retrieving attributable public evidence regarding public domain expiration in 1974).
   - Parallel Search extracts Vanguard Media licensing bulletin for the jazz cue.
5. **Counsel Disposition & Exceptions Schedule:**
   - Counsel re-attests the poster under Public Domain doctrine.
   - Counsel marks the jazz cue as an unresolved exception (to be replaced or licensed).
   - Emits the version-bound **Form E&O-2026 Exceptions Schedule** under Policy Standard `E&O-2026.1-DEVPOST`.

### The Mathematical Conservation Invariant ($12 = 10 + 1 + 1$)
The total baseline claims are mathematically conserved across every stage of the workflow:
The conservation law is stated with exact precision: 12 = 10 + 1 + 1 (10 carried forward + 1 re-attested + 1 unresolved exception).
$$\text{Total Baseline Claims } (12) = \text{Carried Forward } (10) + \text{Re-Attested } (1) + \text{Unresolved Exception } (1)$$

$$\mathbf{12 = 10 + 1 + 1}$$

### The 83.3% Query Reduction Ratio & Workflow Economics
- **Query Savings:** Traditional clearances re-search all 12 items. Lienmark issues targeted queries strictly for the 2 reopened claims.
  $$\text{Query Reduction Ratio} = \left( 1 - \frac{2}{12} \right) \times 100\% = \frac{10}{12} \times 100\% = \mathbf{83.3\%}$$
- **Legal Expense Reduction:** Traditional manual reclearance requires 48 attorney hours ($21,600 at $450/hr). Lienmark reduces this to 8 attorney hours ($3,600), delivering an **$18,000 net legal savings per script revision (83.3% cost reduction)**.

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Next.js 15 App Router Frontend              │
│       (Interactive Clearance Grid | Parallel Citations)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST API / Server Actions
┌──────────────────────────────▼──────────────────────────────┐
│             Composite Security & Reliability Middleware      │
│  (Correlation ID | 1MB Limiter | Idempotency | Secret Mask) │
├─────────────────────────────────────────────────────────────┤
│                     FastAPI Application                     │
│                       (backend/main.py)                     │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
┌──────▼─────────────┐ ┌───────▼─────────────┐ ┌───────▼──────┐
│ Google Cloud Agent │ │ Deterministic       │ │ Golden       │
│ Builder / ADK      │ │ Invalidation Engine │ │ V7/V8        │
│ (Gemini 2.5 Flash) │ │ (Fail-Closed Graph) │ │ Fixtures     │
└──────┬─────────────┘ └───────┬─────────────┘ └──────────────┘
       │                       │
┌──────▼───────────────────────▼─────────────┐
│       Parallel Search API Integration      │
│     (Targeted External Evidence Refresh)   │
└────────────────────────────────────────────┘
```

* **Backend:** FastAPI, Python 3.12+, Pydantic v2.
* **Orchestration:** Google Cloud Agent Builder / ADK patterns with Gemini 2.5 Flash.
* **Partner Integration:** Parallel Search API (`https://api.parallel.ai/v1/search`) with latency tracking and attributable citations.
* **Deterministic Core:** Pure Python dependency graph with fail-closed invalidation logic.
* **Frontend:** Next.js 15 App Router, React 19, Tailwind CSS.

---

## 📜 Devpost & Toolchain Compliance

* **Competition:** Agentic Cinema: The Blockbuster Hackathon (Google Cloud + Devpost).
* **Track:** Parallel Track ($15,000 Prize Pool) & Core Agentic Cinema Track.
* **Official Deadline:** September 9, 2026 at 2:00 PM PDT / 23:00 SAST.
* **Compliance:** Reconstructed directly inside **Google AntiGravity** in strict adherence to Devpost Manager Janet Fang's official ruling ([Forum Topic 44644](https://agentic-cinema.devpost.com/forum_topics/44644-question-about-the-ai-usage-limitation-grafana-track)).

---

## 🔗 Integration Code Pointers

| Module Path | Core Exports / Classes | Architectural Responsibility |
|---|---|---|
| `backend/domain/models.py` | `ProductionVersion`, `CreativeUse`, `CreativeDelta`, `ExceptionsSchedule`, `CounselDecision`, `CarrierHeader`, `PublicEvidenceSnapshot` | Canonical Pydantic v2 data schemas, state enums, and content hash validation. |
| `backend/core/invalidation_engine.py` | `InvalidationEngine`, `evaluate_version_delta` | Fail-closed clearance dependency engine; evaluates $12 \to 10/2$ invalidation. |
| `backend/core/security.py` | `SecretRedactingFilter`, `CorrelationIdFilter`, `IdempotencyKeyManager`, `verify_counsel_token`, `redact_secrets` | Composite security middleware: secret redaction, correlation IDs, 1MB limits, and idempotency. |
| `backend/fixtures/golden_dataset.py` | `get_golden_fixtures`, `get_golden_expected_deltas`, `get_v7_version`, `get_v8_version` | Synthetic golden V7/V8 dataset (*Shadows Over Broadway*) with 12 canonical claims. |
| `backend/services/parallel_service.py` | `ParallelSearchService` | Hardened Parallel Search client with bounded retries, jitter, and 5s timeout. |
| `backend/services/gemini_service.py` | `GeminiService`, `ClearanceBriefing` | Hardened Gemini 2.5 Flash client for semantic script delta analysis. |
| `backend/orchestration/workflow.py` | `LienmarkWorkflow`, `WorkflowRunResult`, `WorkflowStepTrace` | Agent Builder workflow coordinator executing the complete 5-stage clearance loop. |
| `backend/main.py` | `app` | FastAPI application entry point, REST route controllers, and SSR renderer. |
| `scripts/run_quality_gate.py` | Unified 5-gate quality runner | Deterministic CI, rehearsal, live smoke, Next.js build, and static syntax audits. |
| `scripts/run_rehearsal.py` | 7-phase rehearsal harness | Clean-session execution validating all 6 invariants in 44ms runtime. |
| `scripts/run_live_smoke.py` | Live integration runner | Live provider probes with explicit UTC timestamp logging and masked credentials. |
| `scripts/run_license_audit.py` | License compliance runner | Verifies 20/20 dependencies satisfy 100% OSI-approved permissive licenses. |
| `scripts/verify_feature_freeze.py` | Release candidate auditor | Standalone gate verifying commit pin, policy lock, dependencies, and media rights. |
| `scripts/record_take_harness.py` | Video takes harness | Executes and validates 3 consecutive clean deployed runs with zero state leakage. |
| `scripts/verify_submission_consistency.py` | Submission consistency validator | Audits artifact parity, mathematical invariants, and zero prohibited phrases across all 7 surfaces. |
| `scripts/verify_integrations.py` | 60-second judge verifier | Fast CLI check for Gemini, Parallel, and Invalidation Engine. |

---

## 📂 Project Structure

```
├── backend/
│   ├── domain/               # Pydantic v2 canonical data schemas
│   │   ├── models.py         # ProductionVersion, CreativeUse, CreativeDelta, ExceptionsSchedule
│   │   └── __init__.py
│   ├── core/                 # The defensible IP: fail-closed invalidation & security
│   │   ├── invalidation_engine.py
│   │   ├── dependency_graph.py
│   │   ├── revalidation_planner.py
│   │   ├── evidence_reconciler.py
│   │   ├── counsel_checkpoint.py
│   │   ├── security.py
│   │   ├── semantic_delta.py
│   │   ├── schema_repair.py
│   │   └── __init__.py
│   ├── fixtures/             # Golden 12-item V7/V8 dataset
│   │   ├── golden_dataset.py
│   │   └── __init__.py
│   ├── services/             # Gemini 2.5 Flash & Parallel Search services
│   │   ├── parallel_service.py
│   │   ├── gemini_service.py
│   │   ├── revalidation_planner.py
│   │   └── __init__.py
│   ├── orchestration/        # Google Agent Builder workflow
│   │   ├── workflow.py
│   │   └── __init__.py
│   ├── requirements.txt      # Backend dependencies specification
│   └── main.py               # FastAPI server & interactive reviewer dashboard
├── frontend/                 # Next.js 15 App Router interactive dashboard
│   ├── app/
│   │   ├── page.tsx          # Interactive clearance review dashboard
│   │   └── components/       # UI components (Header, Cards, Blockers, Grid)
│   ├── package.json
│   └── next.config.mjs
├── scripts/
│   ├── run_quality_gate.py   # Unified 5-gate automated quality runner
│   ├── run_rehearsal.py      # 7-phase clearance lifecycle rehearsal harness
│   ├── run_live_smoke.py     # Live integration smoke runner with UTC timestamp
│   ├── verify_feature_freeze.py # Standalone feature freeze & release candidate auditor
│   ├── record_take_harness.py # Video take recording harness & telemetry validator
│   ├── verify_submission_consistency.py # Cross-surface submission consistency auditor
│   ├── run_license_audit.py  # 100% OSI-approved license compliance audit
│   └── verify_integrations.py# 60-second CLI judge verification script
├── tests/                    # 22 automated test suites (463 deterministic tests)
│   ├── test_invalidation_engine.py
│   ├── test_e2e_pipeline.py
│   ├── test_api_endpoints.py
│   ├── test_export_reconciliation.py
│   ├── test_first_complete_rehearsal.py
│   ├── test_security_and_reliability.py
│   └── test_evidence_pack_and_reproduction.py
├── docs/                     # Strategy blueprints, audit records, and evidence packs
│   ├── compliance/           # Sprint-by-sprint verification records (Sprint 1A - 5C)
│   └── winning/              # Quarantined concept blueprints & build roadmaps
├── requirements.txt          # Root requirements redirecting to backend/requirements.txt
└── LICENSE                   # MIT License
```

---

## ⚖️ Statutory Legal & Underwriting Disclaimer

> **LEGAL & UNDERWRITING DISCLAIMER: THIS ARTIFACT IS A VERSION-BOUND SCHEDULE OF UNRESOLVED CLEARANCE EXCEPTIONS FOR DEMONSTRATION AND INFORMATIONAL PURPOSES ONLY. NO ARTIFACT GENERATED BY LIENMARK CONSTITUTES OR CLAIMS FORMAL UNDERWRITING APPROVAL, POLICY BINDING, INSURANCE COVERAGE, LEGAL OPINION, OR LEGAL CERTAINTY. COVERAGE IS SUBJECT EXCLUSIVELY TO A SEPARATELY EXECUTED POLICY BINDER WITH AN ADMITTED OR SURPLUS LINES CARRIER.**

Lienmark enforces strict underwriting risk containment. The system operates strictly as an automated clearance change control and risk detection tool to assist qualified production clearance counsel. All generated schedules carry `PENDING_REVIEW` underwriting status and require explicit review by authorized carrier syndicates.

---

## ⚠️ Known Limitations & Responsible AI Disclosures

1. **Fictional Demonstration Dataset:** The film production *Shadows Over Broadway* (`proj_blockbuster_cinema`), screenplay revisions Version 7 and Version 8, and associated entities (*Crime Detective Magazine*, *Vanguard Media Holdings LLC*) are synthetic, fictional demonstration fixtures created exclusively for the Agentic Cinema Hackathon to prevent real-world IP infringement or confidentiality exposure.
2. **Fictional Clearance Counsel Persona:** Clearance counsel *Sarah Jenkins, Esq.* (`counsel_demo_secret_2026`) is a synthetic demonstration persona utilized under ABA Model Rule 5.5 to demonstrate underwriter traceability without implying active attorney-client representation.
3. **Non-Binding Advisory Decision Support:** Lienmark is an automated software tool that provides non-binding decision support. It does not provide formal legal opinions, does not replace independent legal advice, and cannot bind insurance underwriting coverage.
4. **Model Containment Guardrails:** Autonomous AI models (Gemini 2.5 Flash) provide advisory semantic delta classifications only; they are strictly prohibited from directly approving or invalidating legal clearance decisions. Affirmative legal clearance disposition requires human clearance counsel action.

---

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
