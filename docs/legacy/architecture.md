# System Architecture — Lienmark

This document defines the system architecture, component design, data flow pipelines, and infrastructure layout for **Lienmark**.

---

## 1. High-Level System Architecture

Lienmark is an event-driven, multi-agent microservice architecture orchestrated natively on **Google Cloud Agent Builder** and **Gemini Enterprise Agent Platform**, utilizing **Parallel's Search API** for live web rights verification and **Google Cloud Firestore** for storage-enforced immutable ledger governance.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       CLIENT / USER LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Next.js Frontend Dashboard (App Router, Tailwind/Vanilla CSS, dark mode #0B0F17)          │  │
│  │  - ClaimsTable.tsx (live WebSocket/Firestore update)                                     │  │
│  │  - ToastContainer.tsx (Beat A: proactive discovery toasts)                               │  │
│  │  - ClarifyingQuestionModal.tsx (Beat C: human-in-the-loop legal action)                  │  │
│  └──────────────────────────────┬───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┼──────────────────────────────────────────────────────────────┘
                                  │ HTTPS REST / WSS
                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     API & GATEWAY LAYER                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ FastAPI Gateway (Google Cloud Run)                                                       │  │
│  │  - Authentication & JWT Validation (OIDC / OAuth 2.0)                                    │  │
│  │  - Rate Limiting (asyncio.Semaphore(10))                                                 │  │
│  │  - Route Handlers (/api/v1/pipeline, /api/v1/claims, /api/v1/attorney-override)          │  │
│  └──────────────────────────────┬───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┼──────────────────────────────────────────────────────────────┘
                                  │ gRPC / IAM Scoped Calls
                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC ORCHESTRATION LAYER (Google Cloud Agent Builder)               │
│                                                                                                │
│  ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐                  │
│  │  Discovery Agent   │ ──> │    Intake Agent    │ ──> │   Research Agent   │                  │
│  │  (Background       │     │  (Gemini 2.5 Pro   │     │  (Multi-Tool       │                  │
│  │   Poller Beat A)   │     │   Vision & Regex)  │     │   Parallel SDK)    │                  │
│  └────────────────────┘     └────────────────────┘     └─────────┬──────────┘                  │
│                                                                  │                             │
│  ┌────────────────────┐     ┌────────────────────┐     ┌─────────▼──────────┐                  │
│  │    Report Agent    │ <── │ Risk Scoring Agent │ <── │    Ledger Agent    │                  │
│  │  (Verification     │     │  (Deterministic    │     │  (Append-Only      │                  │
│  │   Audit Output)    │     │   Rules Engine)    │     │   Store & Hash)    │                  │
│  └─────────┬──────────┘     └─────────┬──────────┘     └─────────┬──────────┘                  │
└────────────┼──────────────────────────┼──────────────────────────┼─────────────────────────────┘
             │                          │                          │ Immutable Ledger Writes
             ▼                          ▼                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 STORAGE & GOVERNANCE LAYER                                     │
│  ┌─────────────────────────────────┐      ┌─────────────────────────────────────────────────┐  │
│  │ Google Cloud Storage (GCS)      │      │ Google Cloud Firestore Database                 │  │
│  │  - Access-controlled script PDFs│      │  - ledger_entries (create-only security rules)  │  │
│  │  - 90-day retention purge       │      │  - claims & research_findings collections       │  │
│  └─────────────────────────────────┘      └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Frontend UI Layer (`frontend/`)
* **Framework**: Next.js 14+ (App Router) with TypeScript.
* **Styling**: Vanilla CSS Design Tokens (`frontend/app/globals.css`) enforcing dark mode (`#0B0F17`), glassmorphism (`backdrop-filter: blur(12px)`), and status glowing keyframes.
* **Key Components**:
  - `ClaimsTable.tsx`: Live-updating claims breakdown (cleared, flagged, pending human review) via Firestore real-time client listeners.
  - `ToastContainer.tsx`: Proactive notification alerts surfaced by the Discovery Agent (Beat A).
  - `ClarifyingQuestionModal.tsx`: Modern glassmorphism modal for mid-run human legal input (Beat C).
  - `AttorneyOverrideModal.tsx`: Modern split-pane legal sign-off modal with pre-populated citations and RSA-256 signature canvas.
  - `FeatureTogglePanel.tsx`: 32-capability feature toggle panel drawer.
  - `PresetProfileSelector.tsx`: 1-click clearance profile selector.

### 2.2 API & Gateway Layer (`backend/main.py`)
* **Framework**: FastAPI hosted on Google Cloud Run.
* **Authentication**: OIDC JWT validation via Google Identity Platform; IAM service account credentials.
* **Concurrency**: `asyncio.gather()` for parallel claim research with `asyncio.Semaphore(10)` rate limiting.
* **Endpoints**: `/api/v1/pipeline/run`, `/api/v1/claims`, `/api/v1/attorney-override`, `/api/v1/report/{production_id}`, `/api/v1/ledger/{production_id}`, `/api/v1/underwriting/bind-policy`.

### 2.3 Agentic Orchestration Layer (`backend/orchestration/`)
* **Platform**: Google Cloud Agent Builder / Gemini Enterprise Agent Platform.
* **Agents**:
  1. `DiscoveryAgent`: Background watcher (`poller.py`) & heartbeat monitor (`heartbeat.py`).
  2. `IntakeAgent`: Script extraction & confidential term minimalization (`script_hasher.py`, `genai_provenance.py`).
  3. `ResearchAgent`: Dynamic tool selector (`parallel_client.py`, `parallel_mcp_client.py`, `query_builder.py`).
  4. `LedgerAgent`: Application-layer append-only ledger coordinator (`append_only_store.py`, `dual_key_signer.py`).
  5. `RiskScoringAgent`: Rule-based deterministic risk engine & conflict arbiter (`statutory_rule_engine.py`, `fair_use_analyzer.py`).
  6. `ReportAgent`: Clearance Intelligence audit report generator (`report_formatter.py`, `chain_of_title_cert.py`, `eo_binder_api.py`).

### 2.4 Storage & Governance Layer (`backend/storage/`)
* **Database**: Google Cloud Firestore.
* **Security Rules**: `firestore.rules` enforces storage-layer immutability (`allow create: if true; allow update, delete: if false;`).
* **Cloud Storage**: GCS buckets for encrypted script storage with 90-day automated purge policy.

---

## 3. End-to-End Data Flow Trace (Sequence A)

```
[1. Discovery / Upload] ──> Script PDF placed in watched GCS bucket or uploaded via dropzone
                                   │
[2. Intake Agent] ───────> Multimodal vision extracts claims & builds minimal search terms (query_builder.py)
                                   │
[3. Research Agent] ─────> Parallel Search/Task API / MCP called concurrently per claim
                                   │
[4. Ledger Agent] ───────> Writes raw findings & initial ledger entry (supersedes_entry_id backward pointer)
                                   │
[5. Risk Scoring Agent] ──> Pure Python statutory engine computes risk scores & arbitrates conflicts
                                   │
[6. Attorney HITL] ──────> Human counsel reviews flagged claim & submits attorney_override in UI modal
                                   │
[7. Report Agent] ───────> Generates audit report & Form E&O-2026 title clearance certificate with citations
```
