# Lienmark — Independent Clearance Intelligence & Verification Audit Platform

**Lienmark** is an independent Clearance Intelligence & Verification Audit layer for entertainment rights clearance — an agentic multi-agent platform built for **Agentic Cinema: The Blockbuster Hackathon (Parallel Track)**. It ingests scripts or edit timelines, extracts rights-triggering elements, verifies ownership/licensing status live against domain-targeted public registries via **Parallel's Search API**, and records every automated finding and human attorney sign-off on an append-only, tamper-evident ledger.

---

> [!IMPORTANT]
> ### ⚡ Required Integrations for Judges (60-Second Verification)
> Evaluators reviewing code compliance can inspect primary integration points and verify live connectivity immediately:
> 1. **Parallel Search API SDK Integration**: [`backend/agents/research/parallel_client.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/research/parallel_client.py)
> 2. **Google Cloud Agent Builder Orchestration Config**: [`backend/agents/agent_builder_config.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/agent_builder_config.py)
> 
> **Run the 60-Second Live Verification Script:**
> ```bash
> python scripts/verify_integrations.py
> ```
> *(Outputs live Parallel API query response, service account IAM checks, and Firestore append-only ledger write verification in under 5 seconds).*
> 
> **One-Click Local Launcher & Test Suite:**
> ```bash
> ./scripts/run_local_demo.sh      # Launches backend & frontend demo locally
> pytest tests/test_e2e_pipeline.py  # Executes end-to-end benchmark test suite
> ```

---

## 🎯 Core Thesis: Title Insurance for Entertainment IP

Nobody loves title insurance, but nobody closes a real estate deal without it. Lienmark applies this exact structural model to entertainment IP rights clearance: an independent verification layer sitting between a studio and everyone it can't fully trust or see — vendors on one side, rights-holders on the other. 

Insurers (**E&O**) and **completion bond companies** require verifiable, auditable chain-of-title records before money or content moves. Lienmark replaces $250–$700/hr manual legal research with a fast, domain-steered, auditable verification ledger backed by human attorney override workflows.

> ### 🌐 The Paradigm Shift: From Chatbots to Persistent Autonomous Agents
> *"Persistent, autonomous agents are becoming the new baseline."*
> 
> ### 🔍 Open Web Search vs. Gated Rights Databases (Public Mirror Strategy)
> ASCAP/BMI/HFA music registries, USPTO trademark databases, and US Copyright Office records often sit behind interactive search forms or paywalls. `query_builder.py` formats Parallel Search API queries to target **public web mirrors and open registry indices** (`site:ascap.com/repertoire`, `site:uspto.report`, `site:cocatalog.loc.gov`), ensuring high-confidence results without hitting paywall blockers.
> 
> ### ⚖️ Enforced Human-in-the-Loop (HITL) Guardrails
> Rights clearance carries real legal liability. Lienmark explicitly frames all outputs as **Clearance Intelligence & Verification Audit** — providing structured research and deterministic conflict arbitration while enforcing human attorney sign-offs (`action_type: attorney_override`) on all flagged claims.
> 
> ### 🛡️ Concurrency Throttling & SHA-256 Script Deduplication
> An `asyncio.Semaphore(10)` governor in `parallel_client.py` throttles multi-claim research loops, preventing Parallel API rate-limit errors. Meanwhile, `script_hasher.py` computes SHA-256 content hashes to instantly return existing ledger entries for duplicate script drops without wasting search API credits.
> 
> ### 🔐 Cryptographic Hash-Chain Ledger Integrity Verification
> E&O underwriters require proof that historical clearance records were never tampered with. Run `python scripts/verify_ledger_integrity.py` to audit SHA-256 hash chains across Firestore entries in <5 seconds.

---

## 🤖 5-Agent Bounded Autonomy Architecture & Autonomous Beats

Lienmark operates under the core design principle **"Flexible Investigation, Deterministic Validation"**: agents possess unconstrained autonomy over research depth, tool choice, multi-hop lead chasing, and mid-run claim discovery, while all ledger commits and liability boundaries remain strictly validated and human-governed.

Orchestrated natively via **Google Cloud Agent Builder / Gemini Enterprise Agent Platform**:

1. **Intake Agent** (`IntakeAgent`): Reads script PDFs via Gemini multimodal vision; extracts minimal search phrases (`extracted_description`) while stripping narrative plot to guarantee confidentiality.
2. **Research Agent** (`ResearchAgent`): Multi-tool investigation agent. Dynamically selects between Parallel's **Search API** (standard registry lookups) and **Task / Deep Extract API** (complex multi-party claims), and executes self-directed multi-hop lead chasing.
3. **Ledger Agent** (`LedgerAgent`): Enforces append-only immutability at the storage layer; logs automated findings (`agent_finding`), mid-run proposed claims, and formal attorney overrides (`attorney_override`).
4. **Risk Scoring Agent** (`RiskScoringAgent`): Performs cross-claim relationship reasoning, computes rule-based deterministic confidence scores, and arbitrates source conflicts (e.g. Apollo 11 public domain vs. private footage rights).
5. **Report Agent** (`Report Agent`): Generates a structured Clearance Intelligence & Verification Audit report complete with inline source citations, notification urgency routing, and attorney sign-off sections.

### 🌟 Bounded Autonomy Capabilities
- **Beat A (Proactive Discovery & Urgency Routing)**: Background poller surfacing stale/disputed claims via glowing toast alerts (`ToastContainer.tsx`).
- **Beat B (Multi-Tool & Multi-Hop Iteration)**: Research Agent selects optimal Parallel tools and autonomously chases secondary leads (subsidiaries, licensees, estates) across search snippets.
- **Beat C (Mid-Run Claim Discovery & HITL Action)**: Research Agent proposes newly discovered claims mid-run (validated before ledger write) and surfaces context-aware `ClarifyingQuestionModal.tsx` for human legal sign-off.

> [!NOTE]
> ### 🎯 Architectural Posture: Pragmatic Agency vs. Architectural Purity
> *The full leap to dynamic planning stays exactly where it belongs: named, reasoned through, and deliberately not attempted under a hackathon clock where it would trade demo reliability for architectural purity.*
> 
> Lienmark enforces **Bounded Autonomy ("Flexible Investigation, Deterministic Validation")**: agents possess unconstrained freedom over research strategy, dynamic tool selection (Parallel Search vs. Task API), multi-hop lead chasing, and mid-run claim discovery. However, the core scoring and storage pipeline remains strictly deterministic because a compliance verdict that varies between identical runs would undermine the entire title-insurance trust model. Full dynamic planning is explicitly targeted for Phase 2 (LangGraph migration), protecting 100% demo reliability while maintaining legal-grade auditability.

---

## 📁 Full Documentation Index (`docs/`)

| # | Document | Purpose |
|---|---|---|
| 00 | [Documentation Overview](docs/00-README.md) | Package index, long-term thesis, and company identity |
| 01 | [Hackathon Scope](docs/01-hackathon-scope.md) | Devpost rules mapping, judging criteria, and requirements |
| 02 | [MVP Scope](docs/02-mvp-scope.md) | Detailed feature deliverables, UI specifications, and definition of done |
| 03 | [Post-MVP Scope](docs/03-post-mvp-scope.md) | Roadmap for Phase 2 (AI provenance) and Phase 3 (Global Compliance OS) |
| 04 | [PRD](docs/04-prd.md) | Product Requirements Document — single source of truth |
| 05 | [Pitch Deck](docs/05-pitch-deck.md) | Slide-by-slide narrative and 3-minute video shot list |
| 06 | [Data Schema](docs/06-data-schema.md) | Firestore and Postgres schemas, append-only versioning patterns |
| 07 | [Environment Variables](docs/07-env-vars.md) | Complete `.env` reference and per-agent IAM mappings |
| 08 | [Directory Structure](docs/08-directory-structure.md) | Repo layout and agent module organization |
| 09 | [Agent Orchestration](docs/09-agent-orchestration.md) | Multi-agent control flow, payload contracts, and attorney override flow |
| 10 | [Build Timeline](docs/10-build-timeline.md) | Week-by-week implementation schedule |
| 11 | [Demo Content](docs/11-demo-content.md) | Sample script fixtures (`sample_script.pdf` & `sample_script_adversarial.pdf`) |
| 12 | [QA Checklist](docs/12-qa-checklist.md) | Pre-submission verification checklist |
| 13 | [Technical Validation](docs/13-technical-validation.md) | De-risking test results for Parallel API and Gemini |
| 14 | [Sources Appendix](docs/14-sources-appendix.md) | Verified citations for all market sizing and legal claims |
| 15 | [Judge Q&A Prep](docs/15-judge-qna-prep.md) | Prepared answers for asynchronous judge questions |
| 16 | [Liability & Trust Posture](docs/16-liability-and-trust-posture.md) | Product category liability boundary and attorney sign-off posture |
| 17 | [Moat Mechanics](docs/17-moat-mechanics.md) | Defensibility analysis, switching costs, and ledger data network effects |
| 18 | [Company Formation Readiness](docs/18-company-formation-readiness.md) | Entity formation, IP assignment, and domain status |
| 19 | [Executive Summary](docs/19-executive-summary.md) | One-page summary leave-behind |
| 20 | [Adversarial Input Defense](docs/20-adversarial-input-defense.md) | Prompt injection defense architecture and testing |
| 21 | [Agent Prompts](docs/21-agent-prompts.md) | Drafted system prompts and domain-steered query templates |
| 22 | [Pre-Mortem](docs/22-pre-mortem.md) | Strategic risk analysis and mitigation strategies |
| 23 | [Competitor Comparison Matrix](docs/23-competitor-comparison-matrix.md) | Feature matrix vs. Vitrina, Filmustage, and legal tools |
| 24 | [Vision & Mission](docs/24-vision-and-mission.md) | Multi-industry verification expansion thesis |
| 25 | [Agentic Maturity Roadmap](docs/25-agentic-maturity-roadmap.md) | Workflow vs. agentic assessment and roadmap |
| -- | [API Reference](docs/api-reference.md) | Complete REST API specification, JSON payloads, and status codes |
| -- | [Installation Guide](docs/installation.md) | System requirements, setup commands, and troubleshooting matrix |
| -- | [Contributing Guidelines](docs/contributing.md) | Code quality standards, pytest strategies, and branching rules |
| -- | [Security Architecture](docs/security.md) | Threat modeling, authentication lifecycles, and CORS/CSP hardening |
| -- | [System Architecture](docs/architecture.md) | System architecture, ASCII diagram, and data flow trace |
| -- | [Project Scope](docs/project-scope.md) | Consolidated 3-tier project scope (Hackathon, MVP, Post-MVP) |
| -- | [Vision Document](docs/vision.md) | Executive summary, problem statement, and title insurance vision |
| -- | [PRD Reference](docs/prd.md) | Unnumbered exact-match PRD entry point |
| -- | [Directory Structure Ref](docs/directory-structure.md) | Unnumbered exact-match directory structure entry point |

---

## 🛠️ Tech Stack

- **Core AI & Agent Platform**: Google Cloud Agent Builder / Gemini Enterprise Agent Platform (`gemini-2.5-pro` & `flash`)
- **Web Verification**: Parallel Search API (`parallel-web` Python SDK)
- **Database & Governance Ledger**: Google Cloud Firestore (Append-Only Security Rules)
- **Frontend UI**: Next.js / TypeScript / Vanilla CSS (Dark Mode Glassmorphism & Micro-animations)
