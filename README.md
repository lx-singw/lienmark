# Lienmark — Clearance Change Control for E&O

[![Agentic Cinema: Parallel Track](https://img.shields.io/badge/Hackathon-Agentic%20Cinema%20(Parallel%20Track)-38bdf8)](https://agentic-cinema.devpost.com/)
[![Toolchain-Google AntiGravity](https://img.shields.io/badge/Toolchain-Google%20AntiGravity%20(Approved)-10b981)](https://agentic-cinema.devpost.com/forum_topics/44644-question-about-the-ai-usage-limitation-grafana-track)
[![Tests Passing](https://img.shields.io/badge/Pytest-10%2F10%20Passing-emerald)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Lienmark is clearance change control for E&O: it determines whether prior entertainment-rights clearance decisions still carry forward when a film's cut or attributable external evidence changes.**

Rather than a generic search report or contract scanner, Lienmark binds counsel clearance decisions to a deterministic dependency graph. When a cut changes, Lienmark carries unaffected approvals forward, reopens only affected claims, uses **Parallel Search API** for targeted live re-investigation, and produces an underwriter-ready **Exceptions Schedule**.

---

## ⚡ 60-Second Judge Verification

Judges can verify all technical implementations, fail-closed dependency evaluations, and live integration calls in under a minute:

```bash
# 1. Run complete automated test suite (10 passed in ~6s)
python -m pytest tests/ -v

# 2. Run 10-second CLI integration verification suite
python scripts/verify_integrations.py

# 3. Launch the interactive Reviewer Dashboard and REST API
python -m uvicorn backend.main:app --reload --port 8000
```
Open **`http://localhost:8000`** in your browser to experience the 40-second magic demo.

---

## 🎬 The Core Magic Moment (12 → 10/2 → 1/1)

Lienmark demonstrates a real Hollywood entertainment clearance scenario comparing **Version 7** (Baseline) vs **Version 8** (Revision):

1. **12 Prior Approvals (V7):** Baseline screenplay has 12 counsel-approved clearance items (props, set dressings, art, wardrobe, music).
2. **Version 8 Ingestion:**
   - **Creative Drift:** Item 11 (*Crime Detective Magazine* poster, Scene 42) was a 2-second background blur in V7. In V8, the director zooms in for 14 seconds of focal dialogue where the protagonist reads the headline aloud.
   - **External Evidence Drift:** Item 12 (*Midnight Serenade* jazz cue, Scene 18) was approved as public domain. In V8, the script is unchanged, but live **Parallel Search** retrieves an August 2026 worldwide exclusive copyright assignment to *Vanguard Media Holdings LLC*.
3. **Deterministic Invalidation:**
   - **10 Claims Carried Forward:** Unaffected items carry forward automatically with fail-closed deterministic verification.
   - **2 Claims Reopened (Stale):** Exactly 2 claims require counsel attention with explicit reason codes (`CREATIVE_CONTEXT_ALTERED` and `EXTERNAL_EVIDENCE_SHIFT`).
4. **Targeted Parallel Re-Investigation:**
   - Parallel Search queries US Copyright Office renewal records for the poster (retrieving attributable public evidence regarding public domain expiration in 1974).
   - Parallel Search extracts Vanguard Media licensing bulletin for the jazz cue.
5. **Counsel Disposition & Exceptions Schedule:**
   - Counsel re-attests the poster under Public Domain doctrine.
   - Counsel marks the jazz cue as an unresolved exception (to be replaced or licensed).
   - Emits the version-bound **Form E&O-2026 Exceptions Schedule**.

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Reviewer Dashboard (FastAPI / HTML5)        │
│   (Live 12-Claim Grid | Parallel Citations | Exceptions)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP REST API
┌──────────────────────────────▼──────────────────────────────┐
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

* **Backend:** FastAPI, Python 3.11+, Pydantic v2.
* **Orchestration:** Google Cloud Agent Builder / ADK patterns with Gemini 2.5 Flash.
* **Partner Integration:** Parallel Search API (`https://api.parallel.ai/v1/search`) with latency tracking and attributable citations.
* **Deterministic Core:** Pure Python dependency graph with fail-closed invalidation logic.

---

## 📜 Devpost & Toolchain Compliance

* **Competition:** Agentic Cinema: The Blockbuster Hackathon (Google Cloud + Devpost).
* **Track:** Parallel Track ($15,000 Prize Pool).
* **Official Deadline:** September 9, 2026 at 2:00 PM PDT / 23:00 SAST.
* **Compliance:** Reconstructed directly inside **Google AntiGravity** in strict adherence to Devpost Manager Janet Fang's official ruling ([Forum Topic 44644](https://agentic-cinema.devpost.com/forum_topics/44644-question-about-the-ai-usage-limitation-grafana-track)).

---

## 📂 Project Structure

```
├── backend/
│   ├── domain/               # Pydantic v2 canonical data schemas
│   │   ├── models.py         # ProductionVersion, CreativeUse, CreativeDelta, ExceptionsSchedule
│   │   └── __init__.py
│   ├── core/                 # The defensible IP: fail-closed invalidation
│   │   ├── invalidation_engine.py
│   │   └── __init__.py
│   ├── fixtures/             # Golden 12-item V7/V8 dataset
│   │   ├── golden_dataset.py
│   │   └── __init__.py
│   ├── services/             # Gemini 2.5 Flash & Parallel Search services
│   │   ├── parallel_service.py
│   │   ├── gemini_service.py
│   │   └── __init__.py
│   ├── orchestration/        # Google Agent Builder workflow
│   │   └── workflow.py
│   └── main.py               # FastAPI server & interactive reviewer dashboard
├── scripts/
│   └── verify_integrations.py# 60-second CLI judge verification script
├── tests/
│   ├── test_invalidation_engine.py
│   ├── test_e2e_pipeline.py
│   └── test_api_endpoints.py
├── docs/winning/             # Quarantined concept blueprints & strategy
├── requirements.txt
└── LICENSE
```

---

## ⚖️ License

MIT License. See [LICENSE](LICENSE) for details.
