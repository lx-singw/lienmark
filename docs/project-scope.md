# Project Scope — Lienmark

This document defines the 3-tier execution roadmap for **Lienmark**, clearly demarcating the Hackathon Scope (48-hour POC), MVP Scope (commercial baseline release), and Post-MVP Scope (long-term vision).

---

## 1. Hackathon Scope (48-Hour Hyper-Lean Execution Plan)

Designed specifically for submission to **Agentic Cinema: The Blockbuster Hackathon (Parallel Track)**:

* **Core Focus**: Deliver a zero-friction, working proof-of-concept demonstrating live Parallel Search API integration, multi-agent orchestration, and deterministic risk scoring.
* **In-Scope Deliverables**:
  1. **5-Agent Pipeline**: Intake, Research, Ledger, Risk Scoring, and Report Agents operating sequentially in `pipeline.py`.
  2. **Proactive Background Watcher (Beat A)**: Discovery Agent surfacing glowing toast alerts (`ToastContainer.tsx`).
  3. **Multi-Tool & Multi-Hop Iteration (Beat B)**: Research Agent selecting Parallel Search vs. Task API and reformulating queries on low confidence.
  4. **Human-in-the-Loop Action (Beat C)**: Interactive `ClarifyingQuestionModal.tsx` for targeted legal questions.
  5. **Apollo 11 Conflict Arbitration Demo**: Highlighted 45–60s centerpiece beat in the 3-minute video.
  6. **60-Second Verification Tool**: `python scripts/verify_integrations.py` CLI script for judge compliance checks.
  7. **Dual Test Fixtures**: `demo/sample_script.pdf` and `demo/sample_script_adversarial.pdf`.

---

## 2. MVP Scope (Baseline Commercial Release)

The commercial baseline required for early enterprise pilots with completion bond companies and E&O insurance underwriters:

* **Security & IAM**: Complete per-agent service account separation (`sa-intake`, `sa-research`, `sa-ledger`, `sa-scoring`, `sa-report`) with least-privilege IAM bindings (`07-env-vars.md` §4).
* **Formal Attorney Sign-Off Flow**: Full support for `attorney_approval` and `attorney_override` ledger entries with `reviewed_by`, `override_reason`, and `legal_citation_ref` audit fields.
* **Storage-Layer Immutability**: Firestore security rules (`firestore.rules`) enforcing create-only ledger records.
* **UI Polish**: Next.js App Router dashboard (`frontend/app/page.tsx`) with dark mode (`#0B0F17`), glassmorphism cards, inline clickable citations (`SourceCitation.tsx`), and responsive WebSocket updates.
* **Data Retention Engine**: Automated 90-day purge cycle for Cloud Storage script files.

---

## 3. Post-MVP Scope (Phase 2 & Phase 3 Roadmap)

### Phase 2: Synthetic IP & AI Content Provenance (Months 3–6)
* **AI Content Provenance Ledger**: Verification of GenAI training data lineage, synthetic voice cloning, digital double rights, and actor likeness consent.
* **Dynamic Pipeline Orchestration**: Migration to LangGraph state-graph modeling for non-linear dynamic pipeline shaping per document.
* **Task Queue Upgrade**: Cloud Tasks / Celery integration supporting 10,000+ concurrent claim verifications per production.

### Phase 3: Global IP Compliance Operating System (Months 6–18)
* **Multi-Studio Enterprise Ledger**: Postgres database migration (`pgvector` + audit tables) supporting global media conglomerates.
* **Automated Sync Licensing Marketplace**: Direct API integration with music publishers (Sony, Universal, Warner) and stock footage registries for 1-click license execution.
* **Multi-Industry Expansion**: Extending verification ledger architecture to Carbon Credit verification and ESG compliance auditing.
