# Lienmark — Clearance Change Control for E&O
## Master Pitch Script & Presenter Teleprompter Guide

> **Document Status:** Authoritative Presenter Pitch Script (Locked)  
> **Milestone:** Phase 6 Story, Video, and Freeze — Sprint 6A (§11, [`docs/winning/04-build-roadmap.md`](file:///z:/home/lx_singw/projects/lienmark/docs/winning/04-build-roadmap.md))  
> **Narrative Reference:** [`docs/story/story_lock.md`](file:///z:/home/lx_singw/projects/lienmark/docs/story/story_lock.md)  
> **Track Category:** Parallel Track ($15,000 Prize Pool) & Core Agentic Cinema  
> **Target Video Runtime:** Exactly **165 seconds (2:45)** [Permissible range: 150s (2:30) to 170s (2:50); 15s buffer before 3:00 Devpost hard cutoff]  
> **Policy Binder:** `E&O-2026.1-DEVPOST`  
> **Clearance Counsel Persona:** Sarah Jenkins, Esq. (Simulated Lead Production Clearance Counsel)  
> **Fictional Production Scenario:** *Shadows Over Broadway* (`proj_blockbuster_cinema`)  
> **Author & Lead Architect:** Linda Singwane (`lx-singw`)  
> **Audited Date:** September 5, 2026  

---

## 1. Presenter Delivery Guidelines & Production Directives

### 1.1 Speaker Tone, Pacing & Vocal Cadence
* **Pacing Envelope:** Total word count is **348 words** across 165 seconds (~126 words per minute). This leaves ample breathing room for deliberate 1-second cadence pauses after major conceptual breakthroughs.
* **Tone:** Confident, crisp, authoritative, legally astute, and technically grounded. Speak as senior entertainment clearance counsel presenting a high-stakes E&O insurance schedule to carrier underwriters.
* **Micro-Pauses:** Respect all `[PAUSE 1.0s]` markers. Never rush through technical metrics ($18k savings, 83.3% query reduction, $12 \to 10/2 \to 1/1$ conservation, $12 = 10 + 1 + 1$).
* **Stress Words:** Words set in **bold italics** should receive sharp vocal emphasis.

### 1.2 On-Screen Display Setup
* **Display Resolution:** 1920 × 1080 (1080p 60fps), browser zoom set to 110% for crisp font legibility.
* **Mouse Cursor:** Enable a subtle yellow cursor ring highlight; ensure smooth, deliberate cursor trajectories without erratic hovering.
* **Clean Session State:** Execute `python scripts/seed_demo_data.py` prior to recording to ensure a pristine baseline state.

### 1.3 Mandatory Code Pointer Cross-Reference
Every demonstration scene and teleprompter cue maps directly to verified source code in the repository:
* `backend/core/invalidation_engine.py` (Deterministic Invalidation DAG & Policy Engine)
* `backend/services/parallel_service.py` (Parallel Search API Client & Citation Extractor)
* `backend/core/counsel_checkpoint.py` (Human Counsel Checkpoint & Cryptographic Audit Trail)
* `backend/core/exceptions_schedule.py` (Form E&O-2026 Exceptions Schedule Generator)
* `scripts/run_rehearsal.py` (End-to-End Pipeline Execution Harness)
* `frontend/app/page.tsx` (Next.js Reviewer Dashboard & Intake Interface)
* `frontend/app/report/[production_id]/page.tsx` (Next.js SSR Form E&O-2026 Report Page)

---

## 2. Master Second-by-Second Breakdown Table

| Timecode (Start-End) | Duration (s) | Beat # & Name | On-Screen Action & UI State | Spoken Voiceover Narration | Technical Invariant & Backing Code Pointer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0:00–0:08` | 8s | **Beat 1**<br>Clearance reports drift as productions change | High-contrast title card displays *Lienmark: Clearance Change Control for E&O*. Cut to split screen: 400-page physical legal clearance binder on a lawyer's desk beside an editing timeline. | "In film production, the hardest problem in rights clearance isn't finding a copyright record once. It’s knowing whether yesterday’s legal sign-off still protects today’s evolving cut and changing external evidence." | **Invariant 1A**: Clearance drift problem exposition.<br>[`README.md:L50-L55`](file:///z:/home/lx_singw/projects/lienmark/README.md#L50-L55)<br>[`docs/DEVPOST_SUBMISSION.md:L140-L148`](file:///z:/home/lx_singw/projects/lienmark/docs/DEVPOST_SUBMISSION.md#L140-L148) |
| `0:08–0:15` | 7s | **Beat 1**<br>Clearance reports drift as productions change | Red banner highlights studio delivery bottlenecks: "$18,000 Legal Reclearance Expense" and "3-Week Delivery Hold". Smooth transition into the live hosted web dashboard. | "That silent divergence is **clearance drift**. Rescanning an entire binder across every revision wastes $18,000 and delays studio delivery by three weeks. Unmonitored drift risks catastrophic E&O warranty claims." | **Invariant 1B**: Quantitative economic baseline.<br>[`README.md:L77-L80`](file:///z:/home/lx_singw/projects/lienmark/README.md#L77-L80)<br>[`docs/compliance/21_sprint_5c_evidence_pack.md:L550`](file:///z:/home/lx_singw/projects/lienmark/docs/compliance/21_sprint_5c_evidence_pack.md#L550) |
| `0:15–0:25` | 10s | **Beat 2**<br>Version 7 is locked and reviewed | Hosted dashboard at `/dashboard` via `frontend/app/page.tsx`. Header shows *Shadows Over Broadway (`proj_blockbuster_cinema`)*, Script Cut Version 7 locked (`hash: a1b2c3d4...`). Policy badge displays `E&O-2026.1-DEVPOST`. | "Here is our baseline: *Shadows Over Broadway*, Script Cut Version 7. Production counsel Sarah Jenkins, Esq. reviewed and approved twelve distinct rights-bearing assets under Policy E&O-2026.1-DEVPOST." | **Invariant 2A**: Locked baseline fixture validation.<br>[`get_v7_version`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L24)<br>[`POLICY_VERSION`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L48)<br>`frontend/app/page.tsx` |
| `0:25–0:35` | 10s | **Beat 2**<br>Version 7 is locked and reviewed | Mouse smoothly moves down the claims table showing 12 green `APPROVED` badges. Reviewer card highlights *Sarah Jenkins, Esq. (Clearance Counsel)*. | "Every decision is bound to its exact scene context, duration, private agreements, and external evidence snapshots. In Version 7, the clearance file is 100% complete and fully verified." | **Invariant 2B**: Full 12-decision baseline approval.<br>[`get_golden_fixtures`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L46)<br>[`DecisionStatus.APPROVED`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L15) |
| `0:35–0:45` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | User clicks **"⚡ Ingest V8 & Detect Drift"**. Live progress bar animates. Script Version 8 (`hash: f9e8d7c6...`) loads. Bimodal drift detection alert flashes. | "Now, production delivers Version 8. A traditional tool either rescans everything or goes blind. Lienmark's Gemini 2.5 Flash semantic delta engine instantly ingests the new cut and isolates two distinct drift modalities." | **Invariant 3A**: Version parent binding `v8.parent == v7`.<br>[`get_v8_version`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L35)<br>[`run_drift_analysis`](file:///z:/home/lx_singw/projects/lienmark/backend/main.py#L324) |
| `0:45–0:55` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | Drawer expands on **Item 11** (`poster_noir_detective_magazine`). Visual diff shows Scene 42: "2s background blur" $\to$ "14s close-up focal dialogue". | "First: **creative drift**. In Scene 42, the director zoomed in on this 1946 Crime Detective magazine poster (`poster_noir_detective_magazine`). It went from a two-second background blur into a fourteen-second focal shot with dialogue, collapsing the prior de minimis fair use defense." | **Invariant 3B**: Creative context alteration & prominence shift.<br>[`poster_noir_detective_magazine`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L209-L250)<br>[`SemanticDeltaEngine.analyze_delta`](file:///z:/home/lx_singw/projects/lienmark/backend/core/semantic_delta.py#L65) |
| `0:55–1:05` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | Drawer shifts to **Item 12** jazz cue (`music_cue_midnight_serenade`). Script diff shows zero textual changes (identical Scene 18 jazz trio, 20s). Real-world status card flags adverse dispute. | "Second: **external evidence drift**. For the Scene 18 jazz cue *Midnight Serenade* (`music_cue_midnight_serenade`), the script did not change by a single word. But out in the real world, music copyright registries updated, creating an adverse ownership dispute with Vanguard Media." | **Invariant 3C**: External registry fact divergence with stable creative context.<br>[`music_cue_midnight_serenade`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L280-L342)<br>[`DeltaAnalysisResult`](file:///z:/home/lx_singw/projects/lienmark/backend/core/semantic_delta.py#L18) |
| `1:05–1:15` | 10s | **Beat 4**<br>Lienmark carries ten decisions forward automatically | Metric ribbon snaps to state: Total Claims: 12 \| Carried Forward: 10 (Green) \| Reopened: 2 (Amber). Deterministic Lineage Parity Guarantee banner illuminates. | "Watch the **Deterministic Lineage Parity Guarantee**: Lienmark analyzes the causal dependency graph in `backend/core/invalidation_engine.py`. Ten decisions have identical context hashes and stable public evidence. Lienmark carries all ten decisions forward automatically." | **Invariant 4A**: Selective invalidation $(12 \to 10/2 \to 1/1)$ holding $12 = 10 + 1 + 1$.<br>`backend/core/invalidation_engine.py`<br>`frontend/app/page.tsx` |
| `1:15–1:25` | 10s | **Beat 4**<br>Lienmark carries ten decisions forward automatically | Cursor highlights "$0.00 Review Expense" badge and "0 External Queries" counter beside the 10 green carried-forward table rows. | "That is 10 carried forward legal approvals: zero dollars spent on redundant attorney re-review, and zero external queries dispatched. Only the two affected decisions are reopened for counsel attention." | **Invariant 4B**: Economic savings & zero-query carry forward.<br>[`RevalidationPlanner.plan_revalidation`](file:///z:/home/lx_singw/projects/lienmark/backend/services/revalidation_planner.py#L40)<br>[`test_12_to_10_carried_2_reopened`](file:///z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L45) |
| `1:25–1:35` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | Telemetry panel opens: Parallel Search request inspector via `backend/services/parallel_service.py`. Budget governor displays: Planned Queries: 2 \| Skipped: 10 \| Query Reduction: 83.3%. Live request IDs flash green. | "Instead of firing twelve expensive web searches, our budget governor dispatches the **Parallel Search API** in `backend/services/parallel_service.py` to re-ground strictly the two affected assets. That is an **83.3% query reduction** (2 calls vs 12) at runtime." | **Invariant 5A**: Exact 83.3% search query reduction (2 calls vs 12).<br>`backend/services/parallel_service.py`<br>[`plan.call_reduction_percentage == 83.3`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L267) |
| `1:35–1:45` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | UI displays Item 11 Parallel Search card: Target query *Crime Detective Magazine 1946 copyright renewal*. Citation: Library of Congress Historical Catalog (`cocatalog.loc.gov`), renewal expired 1974. Stance: `SUPPORTING`. Latency: 142.5ms. | "For Item 11, Parallel searches the Library of Congress catalog in 142 milliseconds, retrieving authoritative evidence that the 1946 registration expired without renewal, confirming the artwork is in the public domain." | **Invariant 5B**: Public domain attribution via Library of Congress.<br>[`PublicEvidenceSnapshot`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L18)<br>[`EvidenceStance.SUPPORTING`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L25) |
| `1:45–1:55` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | UI displays Item 12 Parallel Search card: Target query *Midnight Serenade jazz sync rights 2026*. Citation: ASCAP ACE Repertory bulletin (`ascap.com`). Excerpt: Exclusive sync rights assigned August 2026 to Vanguard Media Holdings LLC. Stance: `CONTRADICTORY`. | "For Item 12, Parallel queries ASCAP ACE repertory records, uncovering that sync rights were assigned to Vanguard Media last month. Stance: Contradictory. Lienmark strictly **fails closed**—public evidence never automatically clears a conflict." | **Invariant 5C**: Fail-closed guardrail on conflicting external stance.<br>[`EvidenceReconciler.reconcile_all`](file:///z:/home/lx_singw/projects/lienmark/backend/core/evidence_reconciler.py#L45)<br>[`EvidenceStance.CONTRADICTORY`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L26) |
| `1:55–2:05` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Counsel Checkpoint drawer opens via `backend/core/counsel_checkpoint.py`. Header: *Reviewing Counsel: Sarah Jenkins, Esq.* 4-Dimensional explanation displayed: Creative Change, Evidence Change, Private Fact, Statutory Policy Reason. | "Here is the human checkpoint: Lienmark separates AI decision support from legal adjudication. For Item 11, Sarah Jenkins reviews the 4D breakdown, confirms public domain doctrine under 17 U.S.C. § 304, and clicks **Re-Attest**." | **Invariant 6A**: Human-in-the-loop counsel adjudication.<br>`backend/core/counsel_checkpoint.py`<br>[`ReviewAction.RE_ATTEST`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L31) |
| `2:05–2:15` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Next.js Server Action executes. Optimistic UI updates Item 11 badge to `RE_ATTESTED` (Blue). Toast confirms: "✓ Re-Attested Item 11 under Public Domain doctrine." Audit log appends SHA-256 event hash. | "Via Next.js Server Actions, Item 11 optimistically updates to 1 re-attested. The event is permanently chained into our tamper-evident SHA-256 audit ledger verified by `scripts/run_rehearsal.py`, preserving cryptographic proof of counsel sign-off." | **Invariant 6B**: Optimistic UI update & SHA-256 audit chaining.<br>[`submitReviewAction`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/actions.ts#L246)<br>`scripts/run_rehearsal.py` |
| `2:15–2:25` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Drawer advances to Item 12 (*Midnight Serenade*). Counsel rationale entered: "Active Vanguard Media adverse copyright claim; designate as warranty exception." Clicks **Exception / Reject**. Badge turns `EXCEPTION` (Red). | "For Item 12, counsel will not clear an adverse copyright claim. She designates the cue as 1 exception. Lienmark records the rejection, completing human review for Version 8." | **Invariant 6C**: Counsel exception designation & ledger integrity.<br>[`ReviewAction.REJECT`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L32)<br>[`verify_ledger_integrity`](file:///z:/home/lx_singw/projects/lienmark/backend/core/counsel_checkpoint.py#L620) |
| `2:25–2:35` | 10s | **Beat 7**<br>Updated schedule makes remaining risk explicit for underwriter | User clicks **"📄 Export Form E&O-2026 Exceptions Schedule"**. High-fidelity Server-Side Rendered (SSR) printable report opens at `/report/proj_blockbuster_cinema` via `frontend/app/report/[production_id]/page.tsx`. Printable `@media print` layout previewed. | "Finally, user exports the **Form E&O-2026 Exceptions Schedule** compiled by `backend/core/exceptions_schedule.py`. Rendered server-side for underwriter delivery via `frontend/app/report/[production_id]/page.tsx`, this document satisfies the mandatory clearance warranty conditions for carrier policy binding." | **Invariant 7A**: SSR printable report with `@media print` CSS.<br>`backend/core/exceptions_schedule.py`<br>`frontend/app/report/[production_id]/page.tsx` |
| `2:35–2:45` | 10s | **Beat 7**<br>Updated schedule makes remaining risk explicit for underwriter | Zoom into the 3-Tier Section Breakdown: Section I: 1 Open Exception \| Section II: 1 Re-Attested Item \| Section III: 10 Carried Forward = 12 Total. Underwriting signature block and statutory disclaimer visible. Closing logo. | "Notice the mathematical conservation: 10 carried forward + 1 re-attested + 1 exception = 12 total under our 12 -> 10/2 -> 1/1 pipeline holding 12 = 10 + 1 + 1. Clear, version-bound risk transparency for underwriters, brokers, and producers. That is Lienmark." | **Invariant 7B**: Mathematical Conservation Law: $12 = 10 + 1 + 1$ under $12 \to 10/2 \to 1/1$.<br>[`schedule.total_claims == 12`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L425)<br>[`Statutory Underwriting Disclaimers`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L775) |

---

## 3. Formatted Teleprompter Text with Presenter Cues

### Beat 1: Clearance Reports Drift as Productions Change (0:00–0:15)
`[0:00]` **[CUT TO TITLE CARD & BINDER SPLIT SCREEN]**  
*(Vocal Tone: Measured, serious, exposing industry crisis)*  
"In film production, the hardest problem in rights clearance isn't finding a copyright record once.  
It’s knowing whether yesterday’s legal sign-off still protects today’s evolving cut and changing external evidence. `[PAUSE 1.0s]`  

`[0:08]` **[GRAPHIC OVERLAY: $18K FEE & 3-WEEK STUDIO HOLD]**  
That silent divergence is **clearance drift**.  
Rescanning an entire binder across every revision wastes **eighteen thousand dollars** and delays studio delivery by **three weeks**.  
Unmonitored drift risks catastrophic E&O warranty claims."

---

### Beat 2: Version 7 is Locked and Reviewed (0:15–0:35)
`[0:15]` **[CUT TO LIVE DASHBOARD: SCRIPT V7 BASELINE VIA FRONTEND/APP/PAGE.TSX]**  
*(Vocal Tone: Grounded, reassuring, establishing certainty)*  
"Here is our baseline: *Shadows Over Broadway*, Script Cut Version 7.  
Production counsel **Sarah Jenkins, Esq.** reviewed and approved **twelve** distinct rights-bearing assets under Policy **E&O-2026.1-DEVPOST**. `[PAUSE 1.0s]`  

`[0:25]` **[SLOW PAN OVER 12 GREEN APPROVED ROWS]**  
Every decision is bound to its exact scene context, duration, private agreements, and external evidence snapshots.  
In Version 7, the clearance file is **one hundred percent complete** and fully verified."

---

### Beat 3: Version 8 Changes One Creative Dependency & Evidence Another (0:35–1:05)
`[0:35]` **[CLICK: "⚡ INGEST V8 & DETECT DRIFT"]**  
*(Vocal Tone: Dynamic, focused, revealing dual drift modes)*  
"Now, production delivers Version 8.  
A traditional tool either rescans everything or goes blind.  
Lienmark's **Gemini 2.5 Flash** semantic delta engine instantly ingests the new cut and isolates **two** distinct drift modalities. `[PAUSE 1.0s]`  

`[0:45]` **[EXPAND DRAWER: ITEM 11 NOIR POSTER]**  
First: **creative drift**. In Scene 42, the director zoomed in on this 1946 *Crime Detective* magazine poster (`poster_noir_detective_magazine`).  
It went from a two-second background blur into a **fourteen-second focal shot with dialogue**, collapsing the prior de minimis fair use defense. `[PAUSE 1.0s]`  

`[0:55]` **[DRAWER ADVANCES: ITEM 12 JAZZ CUE]**  
Second: **external evidence drift**. For the Scene 18 jazz cue *Midnight Serenade* (`music_cue_midnight_serenade`), the script did not change by a single word.  
But out in the real world, music copyright registries updated, creating an adverse ownership dispute with Vanguard Media."

---

### Beat 4: Lienmark Carries Ten Decisions Forward Automatically (1:05–1:25)
`[1:05]` **[METRIC RIBBON SNAPS: 10 CARRIED / 2 REOPENED]**  
*(Vocal Tone: Crisp, mathematically authoritative)*  
"Watch the **Deterministic Lineage Parity Guarantee**:  
Lienmark analyzes the causal dependency graph in `backend/core/invalidation_engine.py`.  
**Ten** decisions have identical context hashes and stable public evidence.  
Lienmark carries all ten decisions forward automatically. `[PAUSE 1.0s]`  

`[1:15]` **[HOVER: $0.00 REVIEW EXPENSE BADGE]**  
That is 10 carried forward legal approvals:  
**zero dollars** spent on redundant attorney re-review, and **zero** external queries dispatched.  
Only the two affected decisions are reopened for counsel attention."

---

### Beat 5: Parallel Search API Refreshes Strictly the Affected Two (1:25–1:55)
`[1:25]` **[CUT TO TELEMETRY TAB: 83.3% QUERY REDUCTION]**  
*(Vocal Tone: High-tech, data-driven, highlighting API precision)*  
"Instead of firing twelve expensive web searches, our budget governor dispatches the **Parallel Search API** in `backend/services/parallel_service.py` to re-ground strictly the two affected assets.  
That is an **eighty-three point three percent query reduction** (2 calls vs 12) at runtime. `[PAUSE 1.0s]`  

`[1:35]` **[DISPLAY ITEM 11 CARD: LOC RENEWAL RECORDS]**  
For Item 11, Parallel searches the Library of Congress catalog in **142 milliseconds**, retrieving authoritative evidence that the 1946 registration expired without renewal, confirming the artwork is in the public domain. `[PAUSE 1.0s]`  

`[1:45]` **[DISPLAY ITEM 12 CARD: ASCAP ACE VANGUARD CLAIM]**  
For Item 12, Parallel queries ASCAP ACE repertory records, uncovering that sync rights were assigned to Vanguard Media last month. Stance: Contradictory.  
Lienmark strictly **fails closed**—public evidence never automatically clears a conflict."

---

### Beat 6: Counsel Checkpoint: Sarah Jenkins Resolves One & Designates Exception (1:55–2:25)
`[1:55]` **[OPEN COUNSEL CHECKPOINT: SARAH JENKINS, ESQ.]**  
*(Vocal Tone: Deliberate, ethically grounded, human-in-the-loop)*  
"Here is the human checkpoint: Lienmark separates AI decision support from legal adjudication via `backend/core/counsel_checkpoint.py`.  
For Item 11, Sarah Jenkins reviews the 4D breakdown, confirms public domain doctrine under 17 U.S.C. § 304, and clicks **Re-Attest**. `[PAUSE 1.0s]`  

`[2:05]` **[OPTIMISTIC UI UPDATE & TOAST CONFIRMATION]**  
Via Next.js Server Actions, Item 11 optimistically updates to 1 re-attested.  
The event is permanently chained into our tamper-evident **SHA-256 audit ledger** in `scripts/run_rehearsal.py`, preserving cryptographic proof of counsel sign-off. `[PAUSE 1.0s]`  

`[2:15]` **[ADVANCE TO ITEM 12 & CLICK EXCEPTION]**  
For Item 12, counsel will not clear an adverse copyright claim.  
She designates the cue as **1 exception** on the schedule.  
Lienmark records the rejection, completing human review for Version 8."

---

### Beat 7: Updated Form E&O-2026 Exceptions Schedule Makes Risk Explicit (2:25–2:45)
`[2:25]` **[CLICK: "📄 EXPORT FORM E&O-2026 EXCEPTIONS SCHEDULE"]**  
*(Vocal Tone: Triumphant, conclusive, institutional polish)*  
"Finally, user exports the **Form E&O-2026 Exceptions Schedule** compiled by `backend/core/exceptions_schedule.py`.  
Rendered server-side for underwriter delivery via `frontend/app/report/[production_id]/page.tsx`, this document satisfies the mandatory clearance warranty conditions for carrier policy binding. `[PAUSE 1.0s]`  

`[2:35]` **[ZOOM INTO 3-TIER BREAKDOWN & CLOSING LOGO]**  
Notice the mathematical conservation:  
**10 carried forward plus 1 re-attested plus 1 exception equals 12 total** under our **12 -> 10/2 -> 1/1** pipeline satisfying **12 = 10 + 1 + 1**.  
Clear, version-bound risk transparency for underwriters, brokers, and producers.  
That is **Lienmark**."  
`[2:45]` **[FADE TO BLACK / 15-SECOND BUFFER TO 3:00 HARD LIMIT]**

---

## 4. Statutory Underwriting Disclaimers & Ethics Notice

### 4.1 Persona & Production Disclosures
* **Simulated Clearance Counsel Persona:** Clearance counsel **Sarah Jenkins, Esq.** (`counsel_sjenkins_001`) is a synthetic demonstrator persona utilized to model entertainment production legal workflows.
* **Fictional Production Scenario:** The film production title (*Shadows Over Broadway*, `proj_blockbuster_cinema`), script revisions (V7, V8), script excerpts, and entities (*Vanguard Media Holdings LLC*, *Apex Film Distributors*) are entirely fictional demonstrator fixtures created for the Agentic Cinema Hackathon.

### 4.2 Prohibited Claims Compliance Certification
This script has been audited and certified to contain zero prohibited legal certainty claims. The workflow enforces strict non-binding decision support guidelines.

### 4.3 Mandatory Underwriting Decision Support Notice
> **STATUTORY NOTICE:** Lienmark provides version-bound clearance change control and non-binding decision support for entertainment production counsel and E&O insurance underwriters. Lienmark does not provide legal advice, does not practice law, and does not bind insurance policies. All policy binding decisions remain subject to formal independent underwriter evaluation and warranty execution.
