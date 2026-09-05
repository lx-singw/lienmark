# Devpost Gallery Screenshots & Visual Evidence Catalog

> **Milestone**: Sprint 7C Submission Freeze & Final Asset Packaging  
> **Evaluation Window**: September 8 Submission-Freeze Gate (§18)  
> **Policy Version**: `E&O-2026.1-DEVPOST`  
> **Lead Systems Architect**: Linda Singwane (`lx-singw`)  
> **Repository**: [https://github.com/lx-singw/lienmark](https://github.com/lx-singw/lienmark)  
> **Hosted Deployment**: [https://lienmark-prod-6214eb.web.app](https://lienmark-prod-6214eb.web.app)  

---

## 1. Overview & Gallery Packaging Standard

In accordance with **Sprint 7C** in [`docs/winning/04-build-roadmap.md`](../../winning/04-build-roadmap.md) (§12 & §18) and the Devpost Submission Guidelines, this directory catalogs the official visual evidence for the **Lienmark — Clearance Change Control for E&O** hackathon submission.

All gallery screenshot assets are packaged in dual formats:
1. **Binary PNG Format (`.png`)**: Standard rasterized images for Devpost image carousels and gallery uploaders.
2. **Scalable Vector Graphics (`.svg`)**: Crisp, lossless 1920×1080 vector representations for ultra-high-density displays and browser evaluation.
3. **Server-Side Rendered HTML**: Live interactive document artifacts located at `output/form_eo_2026_rehearsal.html`.

---

## 2. Screenshot Asset Manifest

| Sequence | File Name | Format | Aspect Ratio | Title / Surface | Primary Evidence Depicted | Working Reference Route |
|:---:|---|:---:|:---:|---|---|---|
| **01** | `dashboard_v7_baseline.png`<br>`dashboard_v7_baseline.svg` | PNG / SVG | 16:9 | **V7 Locked Baseline Dashboard** | 12 counsel-approved baseline clearance decisions under Policy `E&O-2026.1-DEVPOST`. | `GET /` (Frontend)<br>`GET /api/fixtures` (FastAPI) |
| **02** | `dashboard_v8_drift.png`<br>`dashboard_v8_drift.svg` | PNG / SVG | 16:9 | **V8 Dual-Drift Invalidation & Parallel Budget** | 10 decisions carried forward ($0 cost, 0 queries), 2 decisions reopened stale (Creative & External Evidence Drift), 83.3% search query reduction. | `POST /api/drift/compare`<br>`scripts/run_rehearsal.py` |
| **03** | `counsel_checkpoint_modal.png`<br>`counsel_checkpoint_modal.svg` | PNG / SVG | 16:9 | **Counsel Checkpoint Reviewer Modal** | Sarah Jenkins, Esq. reviewing 4-dimensional audit breakdown; Item 11 re-attested under 17 U.S.C. § 304; Item 12 designated exception; SHA-256 ledger chaining. | `POST /api/review/attest`<br>`frontend/app/components/ReviewModal.tsx` |
| **04** | `form_eo_2026_schedule.png`<br>`form_eo_2026_schedule.svg` | PNG / SVG | 16:9 | **Form E&O-2026 Underwriting Exceptions Schedule** | Continental Entertainment Underwriters Syndicate SSR schedule proving $12 = 10 + 1 + 1$ conservation law with statutory notice and audit seal. | `GET /report/proj_blockbuster_cinema`<br>`output/form_eo_2026_rehearsal.html` |

---

## 3. Deep Asset Descriptions & Rubric Proofs

### Screenshot 01: `dashboard_v7_baseline.png` (Version 7 Locked Baseline)
- **Visual Evidence**: Demonstrates the baseline state for feature noir production *Shadows Over Broadway* (`proj_blockbuster_cinema`). All twelve (12) distinct rights-bearing items (props, set dressings, trademarks, vehicles, foley audio, talent likenesses, and architecture) are displayed with active clearance approvals granted under Policy `E&O-2026.1-DEVPOST`.
- **Rubric Alignment (Design & Potential Impact)**: Proves that Lienmark begins from a structured baseline rather than an unstructured screenplay dump. Demonstrates production counsel review workflows before creative drift occurs.
- **Reference Paths**:
  - Live Frontend: [`frontend/app/page.tsx`](../../../frontend/app/page.tsx)
  - Backend Fixtures: [`backend/fixtures/golden_dataset.py`](../../../backend/fixtures/golden_dataset.py)

### Screenshot 02: `dashboard_v8_drift.png` (Version 7 → Version 8 Drift Analysis)
- **Visual Evidence**: Shows the immediate result of ingesting Production Revision Version 8. Highlights the **Selective Invalidation Engine** KPIs:
  1. **10 Carried Forward**: Unaffected items carry forward automatically with $0 re-review cost.
  2. **2 Reopened Stale**: Item 11 (Scene 42 poster: License scope changed due to focal close-up staging) and Item 12 (Scene 18 jazz cue: ASCAP evidence contradiction).
  3. **83.3% Parallel Search Savings**: Only 2 targeted search queries dispatched rather than 12 blind rescans.
- **Rubric Alignment (Technological Implementation & Parallel Track)**: Proves indispensable Parallel Search API runtime use and selective dependency traversal.
- **Reference Paths**:
  - Engine: [`backend/core/invalidation_engine.py`](../../../backend/core/invalidation_engine.py)
  - Search Service: [`backend/services/parallel_service.py`](../../../backend/services/parallel_service.py)

### Screenshot 03: `counsel_checkpoint_modal.png` (Simulated Counsel Checkpoint)
- **Visual Evidence**: Displays clearance counsel persona **Sarah Jenkins, Esq.** (California Bar #284910) conducting affirmative review inside the 4-Dimensional Audit Breakdown:
  1. *Creative Context Delta*: Incidental blur (2s) expanded to 14s focal close-up with dialogue reading.
  2. *Parallel Search Grounding*: Library of Congress Historical Catalog confirms registration expired in 1974 without renewal.
  3. *Agreement Facts*: Vintage physical prop acquisition verified in art department logs.
  4. *Statutory Reason*: Re-attested under U.S. Public Domain jurisprudence (17 U.S.C. § 304).
- **Rubric Alignment (Responsible AI & Legal Defensibility)**: Demonstrates that autonomous AI models never manufacture legal clearance; affirmative clearance is reserved exclusively for authenticated human counsel.
- **Reference Paths**:
  - Review Modal: [`frontend/app/components/ReviewModal.tsx`](../../../frontend/app/components/ReviewModal.tsx)
  - Ledger Service: [`backend/services/audit_ledger.py`](../../../backend/services/audit_ledger.py)

### Screenshot 04: `form_eo_2026_schedule.png` (Form E&O-2026 Schedule)
- **Visual Evidence**: Renders the printable Server-Side Rendered (SSR) underwriting exceptions schedule for **Continental Entertainment Underwriters Syndicate**.
  - Confirms the **Mathematical Conservation Law**: $12 = 10 \text{ Carried Forward} + 1 \text{ Re-Attested} + 1 \text{ Unresolved Exception}$.
  - Highlights Item 12 (*Midnight Serenade*) as an explicit excluded exception due to adverse Vanguard Media sync assignment.
  - Features the cryptographic SHA-256 event ledger hash (`36c3b07dc12923be8577133af5a9b8bf3830b94f2e7f104aedd47ef321d5410f`).
- **Rubric Alignment (Quality of the Idea & Underwriter Value)**: Proves that insurers receive transparent, version-bound exceptions schedules rather than black-box AI scores.
- **Reference Paths**:
  - Report Endpoint: [`backend/main.py:get_report_ssr`](../../../backend/main.py)
  - Rehearsal HTML Artifact: [`output/form_eo_2026_rehearsal.html`](../../../output/form_eo_2026_rehearsal.html)

---

## 4. Rights, Provenance & Fictional Data Disclosure

In strict adherence to Official Contest Rules §7:
- All screenplay titles (*Shadows Over Broadway*), characters, scene descriptions, and dialogues are original fictional works created by Linda Singwane (`lx-singw`).
- All artwork, brand names, and company entities (*Noir Detective Magazine*, *Acme Coffee*, *Vanguard Media Holdings LLC*, *Continental Entertainment Underwriters Syndicate*) are synthetic, non-infringing demonstration fixtures.
- Zero real-world trademarks, non-public scripts, confidential contracts, or living person likenesses are utilized in these screenshots.

---

## 5. Reproduction & Verification Command

To re-verify the integrity and generation of all screenshot assets:
```bash
python scripts/generate_screenshots.py
python scripts/create_svgs.py
```
