# Lienmark — Legacy Architecture & Foundational Archive
## Master Historical Index & Provenance Register

> **Status**: Archived / Reference Only  
> **Original Provenance**: Sprint 0 Foundational Design (Commit `6218f43`, Parent of `14388028`)  
> **Archival Location**: `docs/legacy/`  
> **Active Production Suite**: [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md), [`docs/EVALUATION_AND_TRACEABILITY.md`](../EVALUATION_AND_TRACEABILITY.md), [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md), [`docs/compliance/`](../compliance/)  

---

## 1. Provenance & Archival Context

This directory preserves the complete set of **40 foundational design and planning documents** authored during **Sprint 0** of the Lienmark project (frozen at commit `6218f43`, immediately preceding the Phase 0 Google AntiGravity compliance transition at commit `14388028`).

### 1.1 Purpose of Preservation
These documents are preserved in `docs/legacy/` to satisfy two crucial governance goals:
1. **Clean Root Presentation**: Keep the root `docs/` workspace clean, concise, and focused for Devpost hackathon judges, underwriters, and external auditors who need immediate access to active production specifications.
2. **Total Historical Traceability**: Maintain an unbroken chain of custody for the original Product Requirements Documents (PRDs), agentic prompt libraries, entity-relationship schemas, threat models, and competitive analyses that shaped the Lienmark platform from day zero.

### 1.2 Compliance & Remediation Note
In accordance with Devpost Hackathon Manager Janet Fang's official ruling on [Topic 44644](https://agentic-cinema.devpost.com/forum_topics/44644-question-about-the-ai-usage-limitation-grafana-track), Lienmark conducted a formal Phase 0 compliance audit during Sprint 0A and Sprint 0B. All production implementations—including the pure Python fail-closed invalidation engine ([`backend/core/invalidation_engine.py`](../../backend/core/invalidation_engine.py)), canonical Pydantic v2 schemas ([`backend/domain/models.py`](../../backend/domain/models.py)), golden V7/V8 datasets ([`backend/fixtures/golden_dataset.py`](../../backend/fixtures/golden_dataset.py)), Next.js 15 App Router frontend ([`frontend/`](../../frontend/)), and comprehensive test suites ([`tests/`](../../tests/))—were independently authored and verified inside **Google AntiGravity**.

The documents cataloged below represent the historical design bedrock upon which the production architecture was engineered.

---

## 2. Active Modern Counterparts

The table below maps core functional areas from the legacy archive to their active, production-grade successors:

| Core Functional Area | Legacy Documents (Sprint 0) | Active Modern Counterpart | Primary Focus in Production |
|---|---|---|---|
| **System Architecture** | [`architecture.md`](architecture.md), [`09-agent-orchestration.md`](09-agent-orchestration.md), [`08-directory-structure.md`](08-directory-structure.md) | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) | Next.js 15 + FastAPI architecture, fail-closed invalidation engine, ADK workflow, Cloud Run specs |
| **Quality & Traceability** | [`12-qa-checklist.md`](12-qa-checklist.md), [`13-technical-validation.md`](13-technical-validation.md) | [`docs/EVALUATION_AND_TRACEABILITY.md`](../EVALUATION_AND_TRACEABILITY.md) | Multi-dimensional evaluation, test traces, mathematical conservation proofs (12 → 10/2 → 1/1) |
| **Devpost Submission** | [`26-hackathon-alignment-matrix.md`](26-hackathon-alignment-matrix.md), [`28-devpost-submission-manifest.md`](28-devpost-submission-manifest.md) | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) | Complete Devpost pitch dossier, track alignment, architectural justification, and judging criteria |
| **Submission Mirror** | [`00-README.md`](00-README.md), [`19-executive-summary.md`](19-executive-summary.md) | [`docs/DEVPOST_SUBMISSION.md`](../DEVPOST_SUBMISSION.md) | Root submission document mirror for offline review and automated linters |
| **Narrative Pitch Script** | [`05-pitch-deck.md`](05-pitch-deck.md), [`11-demo-content.md`](11-demo-content.md) | [`docs/pitch_script.md`](../pitch_script.md) & [`docs/story/story_lock.md`](../story/story_lock.md) | Locked 7-beat, 168-second video narration script with timing invariants and presenter cues |
| **Eligibility & Provenance** | [`16-liability-and-trust-posture.md`](16-liability-and-trust-posture.md), [`18-company-formation-readiness.md`](18-company-formation-readiness.md) | [`docs/compliance/01_stage1_eligibility_gate.md`](../compliance/01_stage1_eligibility_gate.md) & [`02_provenance_inventory_and_remediation.md`](../compliance/02_provenance_inventory_and_remediation.md) | Devpost Topic 44644 compliance certification, asset class audit, and toolchain provenance proofs |
| **Scope & Demolition** | [`01-hackathon-scope.md`](01-hackathon-scope.md), [`02-mvp-scope.md`](02-mvp-scope.md), [`03-post-mvp-scope.md`](03-post-mvp-scope.md) | [`docs/compliance/04_scope_demolition_and_p0_boundary.md`](../compliance/04_scope_demolition_and_p0_boundary.md) | P0 scope demolition, deferred module isolation, category freeze, and single-sentence demo contract |
| **Claims & Defense** | [`17-moat-mechanics.md`](17-moat-mechanics.md), [`20-adversarial-input-defense.md`](20-adversarial-input-defense.md) | [`docs/compliance/05_claims_register_and_language_defense.md`](../compliance/05_claims_register_and_language_defense.md) | Defensible claims register, precise legal vocabulary, and statutory disclaimer invariants |
| **Golden Fixtures** | [`06-data-schema.md`](06-data-schema.md) | [`docs/compliance/06_acceptance_contract_and_golden_fixtures.md`](../compliance/06_acceptance_contract_and_golden_fixtures.md) | Formal acceptance contract, V7/V8 production wedge, and expected-delta test oracle |
| **Master Entrypoint** | [`00-README.md`](00-README.md) | [`README.md`](../../README.md) | Repository landing page, quick start instructions, live Cloud Run links, and architectural summary |

---

## 3. Master Catalog of 40 Foundational Documents

The 40 archived documents are cataloged below across four operational groupings.

### Group 1: Foundational Scope & PRD (10 Documents)
This group defines the core business problem, domain mechanics, product requirements, and strategic boundaries established during initial ideation.

| Document | Title / Focus | Core Architectural Contribution | Modern Successor |
|---|---|---|---|
| [`00-README.md`](00-README.md) | Documentation Package Overview | Original documentation master index and Sprint 0 roadmap structure | [`README.md`](../../README.md) |
| [`01-hackathon-scope.md`](01-hackathon-scope.md) | Hackathon Scope Definition | Initial hackathon scope boundaries, user personas, and target outcomes | [`docs/compliance/04_scope_demolition_and_p0_boundary.md`](../compliance/04_scope_demolition_and_p0_boundary.md) |
| [`02-mvp-scope.md`](02-mvp-scope.md) | MVP Scope Specification | Core wedge definition, intake formats, and minimal viable clearance workflow | [`docs/compliance/04_scope_demolition_and_p0_boundary.md`](../compliance/04_scope_demolition_and_p0_boundary.md) |
| [`03-post-mvp-scope.md`](03-post-mvp-scope.md) | Post-MVP Scope & Commercial Roadmap | Enterprise clearance platform expansion, multi-studio sync, and carrier integrations | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§11) |
| [`04-prd.md`](04-prd.md) | Comprehensive PRD | Full product specifications, functional requirements, and actor interaction models | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) |
| [`05-pitch-deck.md`](05-pitch-deck.md) | Pitch Deck Slide Outline | Slide-by-slide narrative, visual wireframes, and problem-solution articulation | [`docs/pitch_script.md`](../pitch_script.md) |
| [`06-data-schema.md`](06-data-schema.md) | Data Schema & Entity Models | Initial TypeScript and JSON schemas for claims, evidence, and clearance reports | [`backend/domain/models.py`](../../backend/domain/models.py) |
| [`prd.md`](prd.md) | Concise PRD Summary | High-level PRD summary and foundational invariant statements | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) |
| [`project-scope.md`](project-scope.md) | Project Scope & Problem Statement | High-level problem framing: the multi-million dollar cost of E&O recuts | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`vision.md`](vision.md) | Foundational Vision & Mission | Original vision statement on autonomous legal operations for entertainment | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§1) |

---

### Group 2: System Architecture & Engineering (8 Documents)
This group documents early system topology, multi-agent orchestration blueprints, directory layouts, and runtime environment specifications.

| Document | Title / Focus | Core Engineering Specification | Modern Successor |
|---|---|---|---|
| [`07-env-vars.md`](07-env-vars.md) | Environment Variables & Secrets | Environment variable taxonomy, API key configurations, and GCP secret mappings | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§8) |
| [`08-directory-structure.md`](08-directory-structure.md) | Detailed Directory Layout | 118-file directory structure specification and module boundary definitions | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§2) |
| [`09-agent-orchestration.md`](09-agent-orchestration.md) | Agent Orchestration Blueprint | Multi-agent coordination protocols, handoff mechanics, and worker boundaries | [`backend/orchestration/workflow.py`](../../backend/orchestration/workflow.py) |
| [`10-build-timeline.md`](10-build-timeline.md) | 48-Hour Build Timeline | Initial sprint schedules, task milestones, and resource allocations | [`docs/compliance/`](../compliance/) |
| [`architecture.md`](architecture.md) | System Architecture Overview | Early service boundaries, pipeline dataflow, and frontend/backend interfaces | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) |
| [`api-reference.md`](api-reference.md) | REST API Reference | Initial endpoint definitions, payload schemas, and error contract designs | [`backend/main.py`](../../backend/main.py) |
| [`directory-structure.md`](directory-structure.md) | Condensed Directory Tree | Abbreviated codebase topology and key file location quick-reference | [`README.md`](../../README.md) |
| [`installation.md`](installation.md) | Installation & Setup Guide | Local development setup, Python/Node prerequisite installation, and run instructions | [`README.md`](../../README.md) & [`scripts/`](../../scripts/) |

---

### Group 3: Quality, Validation & Moat Mechanics (12 Documents)
This group captures quality assurance protocols, security architecture, threat models, competitive defensibility analyses, and legal liability postures.

| Document | Title / Focus | Core Validation / Moat Posture | Modern Successor |
|---|---|---|---|
| [`11-demo-content.md`](11-demo-content.md) | Demo Content & Script Excerpt | Demo film assets, character descriptions, trademark clearance scenarios | [`backend/fixtures/golden_dataset.py`](../../backend/fixtures/golden_dataset.py) |
| [`12-qa-checklist.md`](12-qa-checklist.md) | Pre-Submission QA Checklist | Verification gates, link validation procedures, and demo rehearsability checks | [`tests/`](../../tests/) |
| [`13-technical-validation.md`](13-technical-validation.md) | Technical Validation Findings | De-risking analysis, latency benchmarks, and external API rate limit mitigations | [`docs/compliance/03_technical_gate_proofs.md`](../compliance/03_technical_gate_proofs.md) |
| [`14-sources-appendix.md`](14-sources-appendix.md) | Sources & Legal Authorities | Statutory references (Lanham Act, Copyright Act), E&O policy standards, citations | [`docs/compliance/05_claims_register_and_language_defense.md`](../compliance/05_claims_register_and_language_defense.md) |
| [`15-judge-qna-prep.md`](15-judge-qna-prep.md) | Judge Q&A Defense Dossier | Anticipated technical and legal objections with structured counter-arguments | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`16-liability-and-trust-posture.md`](16-liability-and-trust-posture.md) | Liability & Trust Architecture | Counsel-in-the-loop safeguards, fail-closed boundaries, and malpractice disclaimers | [`docs/compliance/05_claims_register_and_language_defense.md`](../compliance/05_claims_register_and_language_defense.md) |
| [`17-moat-mechanics.md`](17-moat-mechanics.md) | Defensibility & Moat Mechanics | Why Lienmark's invalidation graph creates defensible IP compared to generic search | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§10) |
| [`18-company-formation-readiness.md`](18-company-formation-readiness.md) | Commercial IP Readiness | Corporate formation structure, IP ownership clarity, and enterprise license tiers | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`19-executive-summary.md`](19-executive-summary.md) | Executive Summary | Condensed pitch for executive stakeholders and legal ops leadership | [`docs/DEVPOST_SUBMISSION.md`](../DEVPOST_SUBMISSION.md) |
| [`20-adversarial-input-defense.md`](20-adversarial-input-defense.md) | Adversarial Input & Injection Defense | Prompt injection mitigation, toxic input defense, and payload size bounds (1MB) | [`backend/main.py`](../../backend/main.py) (Middleware) |
| [`security.md`](security.md) | Security Architecture & Threat Model | MPA security hardening, authentication lifecycle, and secret redaction rules | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§8) |
| [`contributing.md`](contributing.md) | Contributing Guidelines | Git commit hygiene, issue taxonomy, and coding conventions | [`README.md`](../../README.md) |

---

### Group 4: Agentic Strategy & Hackathon Positioning (10 Documents)
This group documents agent prompting strategies, pre-mortem failure analyses, competitive benchmarks, maturity roadmaps, and track compliance matrices.

| Document | Title / Focus | Strategic Horizon & Hackathon Angle | Modern Successor |
|---|---|---|---|
| [`21-agent-prompts.md`](21-agent-prompts.md) | Agent Prompts & Few-Shot Templates | Foundational prompts for intake, research, invalidation, and synthesis agents | [`backend/services/gemini_service.py`](../../backend/services/gemini_service.py) |
| [`22-pre-mortem.md`](22-pre-mortem.md) | Failure Pre-Mortem Analysis | Honest exploration of why the project might fail and preventative counter-measures | [`docs/EVALUATION_AND_TRACEABILITY.md`](../EVALUATION_AND_TRACEABILITY.md) |
| [`23-competitor-comparison-matrix.md`](23-competitor-comparison-matrix.md) | Competitor Comparison Matrix | Competitive breakdown against traditional clearance law firms and generic search | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`24-vision-and-mission.md`](24-vision-and-mission.md) | Expanded Vision & Industry Impact | Long-term roadmap for modernizing legal operations in the entertainment ecosystem | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§1) |
| [`25-agentic-maturity-roadmap.md`](25-agentic-maturity-roadmap.md) | Agentic Maturity Roadmap | 5-level maturity model from reactive search to bounded autonomous revalidation | [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md) (§3) |
| [`26-hackathon-alignment-matrix.md`](26-hackathon-alignment-matrix.md) | Hackathon Scoring Alignment Matrix | Direct alignment of features to Devpost rubric criteria (Agency, Parallel, Impact) | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`27-feature-toggles-and-demo-selection.md`](27-feature-toggles-and-demo-selection.md) | Feature Toggles & Demo Selection | Toggle architecture separating hero demo features from extended capabilities | [`backend/config/preset_profiles.json`](../../backend/config/preset_profiles.json) |
| [`28-devpost-submission-manifest.md`](28-devpost-submission-manifest.md) | Devpost Submission Manifest | Initial checklist for hackathon assets, demo links, and repository artifacts | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`29-monetization-and-gtm.md`](29-monetization-and-gtm.md) | Monetization & GTM Strategy | Studio SaaS pricing tiers, production-budget fee structures, and GTM channels | [`docs/submission/devpost_submission.md`](../submission/devpost_submission.md) |
| [`30-ui-design-system.md`](30-ui-design-system.md) | UI Component Design System | Design token system, accessibility standards, and reviewer ergonomics | [`frontend/`](../../frontend/) |

---

## 4. Architectural Lineage & Evolution Summary

The evolution from this 40-document Sprint 0 foundation to the production release deployed on Google Cloud Run followed an intentional, disciplined trajectory:

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                             LIENMARK ARCHITECTURAL LINEAGE                            │
└───────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
      ┌───────────────────────────────────────────────────────────────────────────┐
      │ SPRINT 0: Foundational Concept & Comprehensive Specifications             │
      │ • 40 documents authored covering PRD, schemas, prompts, security, UI     │
      │ • Frozen at commit 6218f43 (Parent of 14388028)                           │
      │ • Preserved under docs/legacy/ for historical completeness                │
      └───────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
      ┌───────────────────────────────────────────────────────────────────────────┐
      │ PHASE 0: Scope Demolition & AntiGravity Compliance (Commit 14388028)      │
      │ • Passed 20/20 Stage 1 eligibility gates under Devpost Topic 44644        │
      │ • Executed Sprint 0B scope demolition: isolated all deferred modules      │
      │ • Sealed exact mathematical invariants (12 -> 10/2 -> 1/1 golden wedge)   │
      └───────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
      ┌───────────────────────────────────────────────────────────────────────────┐
      │ SPRINTS 1–4: Core Implementation & Production Hardening                   │
      │ • Pure Python fail-closed invalidation engine (backend/core/)             │
      │ • Parallel Search API v1 & Gemini 2.5 Flash services (backend/services/)  │
      │ • Counsel-in-the-loop review queue & supersession ledger (backend/main.py)│
      │ • Next.js 15 App Router reviewer dashboard (frontend/)                    │
      └───────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
      ┌───────────────────────────────────────────────────────────────────────────┐
      │ SPRINTS 5–7: Verification, Certification & Submission Freeze              │
      │ • 600+ automated test assertions passing across unit, integration, and UI │
      │ • Multi-project GCP isolation (Dev & Judge environments on Cloud Run)     │
      │ • Form E&O-2026 Exceptions Schedule locked for film underwriter audit     │
      │ • Comprehensive Devpost submission package & 168-second pitch video       │
      └───────────────────────────────────────────────────────────────────────────┘
```

For questions regarding current system architecture, consult [`docs/TARGET_ARCHITECTURE.md`](../TARGET_ARCHITECTURE.md). For verification procedures and test suites, see [`docs/EVALUATION_AND_TRACEABILITY.md`](../EVALUATION_AND_TRACEABILITY.md).
