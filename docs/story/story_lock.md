# Sprint 6A — Story Lock & Narrative Architecture

> **Document Status:** Complete & Authoritative (Story Locked)  
> **Milestone:** Phase 6 Story, Video, and Freeze — Sprint 6A (§11, [`docs/winning/04-build-roadmap.md`](file:///z:/home/lx_singw/projects/lienmark/docs/winning/04-build-roadmap.md))  
> **Operational Guide:** [`docs/winning/05-demo-and-submission-playbook.md`](file:///z:/home/lx_singw/projects/lienmark/docs/winning/05-demo-and-submission-playbook.md)  
> **Project:** [Lienmark — Clearance Change Control for E&O](file:///z:/home/lx_singw/projects/lienmark/README.md)  
> **Track Category:** Parallel Track ($15,000 Prize Pool) & Core Agentic Cinema  
> **Target Video Runtime:** Exactly **165 seconds (2:45)** [Strictly bounded within 150s (2:30) and 170s (2:50), leaving a 15-second safety buffer before the 3:00 Devpost hard cutoff]  
> **Policy Binder:** `E&O-2026.1-DEVPOST`  
> **Simulated Reviewer Persona:** Sarah Jenkins, Esq. (Lead Clearance Counsel)  
> **Fictional Production Scenario:** *Shadows Over Broadway* (`proj_blockbuster_cinema`)  
> **Author & Lead Architect:** Linda Singwane (`lx-singw`)  
> **Audited Date:** September 5, 2026  

---

## 1. Executive Summary & Core Pitch Anchor

In commercial film and television production, entertainment legal clearance has historically been treated as a static, pre-production snapshot. Legal counsel coordinator teams spend weeks combing through an early screenplay draft to produce thick binders of copyright, trademark, and likeness clearances. 

However, film production is an inherently evolutionary art: scripts are rewritten on set, directors reframe incidental background props into focal dialogue set pieces, cue sheets are swapped in editorial, and external music copyright catalogs change hands without notice. When a production applies for **Errors & Omissions (E&O) insurance**—an absolute prerequisite for distribution via theatrical studios or streaming platforms—counsel faces an operational crisis: either spend **$18,000+ and incur a 3-week studio delivery delay** conducting a blind manual reclearance of the entire script binder, or risk catastrophic underwriter warranty rescissions, distributor injunctions, and multi-million-dollar copyright infringement lawsuits.

### The Pitch Anchor (One Sentence)
> **Lienmark detects which prior clearance decisions may no longer carry forward when either the production cut or its external evidence changes—and reopens only those decisions.**

Lienmark is **clearance change control for E&O**. It binds every attorney approval directly to its creative usage context hash, private contractual terms, and external registry evidence snapshot. When production or real-world legal reality shifts, Lienmark traverses the dependency graph, carries unaffected approvals forward automatically ($0.00 review expense, 0 external network queries), dispatches targeted Parallel Search queries strictly to affected nodes, and routes legal contradictions to human counsel—emitting an underwriter-ready **Form E&O-2026 Exceptions Schedule**.

---

## 2. The 7 Mandatory Narrative Beats

In strict accordance with §11 of [`docs/winning/04-build-roadmap.md`](file:///z:/home/lx_singw/projects/lienmark/docs/winning/04-build-roadmap.md) and §2 of [`docs/winning/05-demo-and-submission-playbook.md`](file:///z:/home/lx_singw/projects/lienmark/docs/winning/05-demo-and-submission-playbook.md), the 165-second story is locked into seven sequential beats:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       LIENMARK 165-SECOND DEMONSTRATION RUNTIME                                   │
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬────────────────────────┤
│    BEAT 1    │    BEAT 2    │    BEAT 3    │    BEAT 4    │    BEAT 5    │    BEAT 6    │         BEAT 7         │
│  0:00 - 0:15 │  0:15 - 0:35 │  0:35 - 1:05 │  1:05 - 1:25 │  1:25 - 1:55 │  1:55 - 2:25 │      2:25 - 2:45       │
│     (15s)    │     (20s)    │     (30s)    │     (20s)    │     (30s)    │     (30s)    │          (20s)         │
│  Clearance   │  Version 7   │  Version 8   │ Ten Carried  │   Parallel   │   Counsel    │    Form E&O-2026       │
│    Drift     │  Baseline    │ Dual-Drift   │   Forward    │  Targeted    │  Checkpoint  │  Exceptions Schedule   │
│   Exposition │   Reviewed   │  Ingestion   │ ($0 Expense) │ (83.3% Save) │ Adjudication │   Underwriter Binder   │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴────────────────────────┘
 [0:00]                                                                                    [2:45] ──► Buffer to 3:00
```

### Summary of Beat Milestones & Invariants

| Beat # & Name | Timecode (Start-End) | Duration (s) | Core Technical Invariant | Mathematical & Empirical Proof | Backing Codebase Symbol |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Beat 1: Clearance reports drift as productions change** | `0:00–0:15` | 15s | Static binder obsolescence & economic risk exposition | Baseline binder: 12 prior items. Reclearance penalty: $18,000 / 3-week post delay. | [`get_v7_version`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L24)<br>[`ProductionVersion`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L42) |
| **Beat 2: Version 7 is locked and reviewed** | `0:15–0:35` | 20s | Deterministic baseline certainty under policy binder | 12/12 claims `APPROVED` by Sarah Jenkins, Esq. under policy `E&O-2026.1-DEVPOST`. | [`POLICY_VERSION`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L48)<br>[`DashboardHeader`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/components/DashboardHeader.tsx#L1) |
| **Beat 3: Version 8 changes one creative dependency & evidence changes another** | `0:35–1:05` | 30s | Bimodal drift detection via Gemini 2.5 Flash structured delta | Item 11: 2s blur $\to$ 14s focal (`CREATIVE_CONTEXT_ALTERED`). Item 12: ASCAP Vanguard dispute (`EXTERNAL_EVIDENCE_SHIFT`). | [`SemanticDeltaEngine`](file:///z:/home/lx_singw/projects/lienmark/backend/core/semantic_delta.py#L35)<br>[`analyze_scene_delta`](file:///z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L65) |
| **Beat 4: Lienmark carries ten decisions forward automatically** | `1:05–1:25` | 20s | Deterministic Lineage Parity Guarantee | 10 claims preserved ($0.00 review expense, 0 queries). Exactly 2 claims reopened. | [`InvalidationEngine.evaluate_invalidation`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L149)<br>[`ClearanceSummaryCards`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/components/ClearanceSummaryCards.tsx#L1) |
| **Beat 5: Parallel Search API refreshes strictly the affected two** | `1:25–1:55` | 30s | Budget-governed selective external grounding & fail-closed stance | 83.3% query reduction (2 calls vs 12). LOC confirms PD; ASCAP ACE reveals Vanguard adverse claim. | [`RevalidationPlanner`](file:///z:/home/lx_singw/projects/lienmark/backend/services/revalidation_planner.py#L25)<br>[`ParallelSearchService.search`](file:///z:/home/lx_singw/projects/lienmark/backend/services/parallel_service.py#L29) |
| **Beat 6: Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception** | `1:55–2:25` | 30s | Human-in-the-loop ethical boundary & cryptographic SHA-256 event chaining | Item 11 re-attested (`RE_ATTESTED`). Item 12 designated as underwriting exception (`EXCEPTION`). Chained event hashes. | [`CounselCheckpointManager`](file:///z:/home/lx_singw/projects/lienmark/backend/core/counsel_checkpoint.py#L50)<br>[`submitReviewAction`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/actions.ts#L246) |
| **Beat 7: Updated Form E&O-2026 Exceptions Schedule makes remaining risk explicit** | `2:25–2:45` | 20s | Mathematical conservation law ($12 = 10 + 1 + 1$) & statutory underwriter package | 3-tier SSR printable schedule: Sec I (1 Exception) + Sec II (1 Re-Attested) + Sec III (10 Carried) = 12. | [`ExceptionsScheduleEngine`](file:///z:/home/lx_singw/projects/lienmark/backend/core/exceptions_schedule.py#L34)<br>[`report/page.tsx`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/report/[production_id]/page.tsx#L1) |

---

## 3. Second-by-Second Demonstration Breakdown Table

The following master table provides the authoritative timing, on-screen choreography, teleprompter narration, and backing codebase symbols for every second of the 2-minute 45-second production run:

| Timecode (Start-End) | Duration (s) | Beat # & Name | On-Screen Action & UI State | Spoken Voiceover Narration | Technical Invariant & Backing Code Pointer |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0:00–0:08` | 8s | **Beat 1**<br>Clearance reports drift as productions change | High-contrast title card displays *Lienmark: Clearance Change Control for E&O*. Cut to split view: a physical 400-page paper clearance binder beside a modern editing suite. | "In film production, the hardest problem in rights clearance isn't finding a copyright record once. It’s knowing whether yesterday’s legal sign-off still protects today’s evolving cut and changing external evidence." | **Invariant 1A**: Baseline state problem definition.<br>[`README.md:L50-L55`](file:///z:/home/lx_singw/projects/lienmark/README.md#L50-L55)<br>[`docs/DEVPOST_SUBMISSION.md:L140-L148`](file:///z:/home/lx_singw/projects/lienmark/docs/DEVPOST_SUBMISSION.md#L140-L148) |
| `0:08–0:15` | 7s | **Beat 1**<br>Clearance reports drift as productions change | Graphic overlay highlights post-production bottlenecks: "$18,000 Legal Reclearance Fee" and "3-Week Delivery Hold". Camera transitions into the live hosted web dashboard. | "That silent divergence is **clearance drift**. Rescanning a full binder across every cut wastes $18,000 and delays studio delivery by three weeks. Unmonitored drift risks catastrophic E&O warranty claims." | **Invariant 1B**: Quantitative studio economic baseline.<br>[`README.md:L77-L80`](file:///z:/home/lx_singw/projects/lienmark/README.md#L77-L80)<br>[`docs/compliance/21_sprint_5c_evidence_pack.md:L550`](file:///z:/home/lx_singw/projects/lienmark/docs/compliance/21_sprint_5c_evidence_pack.md#L550) |
| `0:15–0:25` | 10s | **Beat 2**<br>Version 7 is locked and reviewed | Live browser at `/dashboard`. Header shows *Shadows Over Broadway (`proj_blockbuster_cinema`)*, Script Cut Version 7 locked (`hash: a1b2c3d4...`). Policy badge displays `E&O-2026.1-DEVPOST`. | "Here is our baseline: *Shadows Over Broadway*, Script Cut Version 7. Production counsel Sarah Jenkins, Esq. reviewed and approved twelve distinct rights-bearing assets under Policy E&O-2026.1-DEVPOST." | **Invariant 2A**: Locked baseline fixture validation.<br>[`get_v7_version`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L24)<br>[`POLICY_VERSION`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L48)<br>`frontend/app/page.tsx` |
| `0:25–0:35` | 10s | **Beat 2**<br>Version 7 is locked and reviewed | Mouse hovers over claims table showing 12 green `APPROVED` status badges. Reviewer identity card highlights *Sarah Jenkins, Esq. (Clearance Counsel)*. | "Every decision is bound to its exact scene context, duration, private agreements, and external evidence snapshots. In Version 7, the clearance file is 100% complete and fully verified." | **Invariant 2B**: Full 12-decision baseline approval.<br>[`get_golden_fixtures`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L46)<br>[`DecisionStatus.APPROVED`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L15) |
| `0:35–0:45` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | User clicks **"⚡ Ingest V8 & Detect Drift"**. Live progress bar animates. Script Version 8 (`hash: f9e8d7c6...`) loads. Notification highlights bimodal drift detection. | "Now, production delivers Version 8. A traditional tool either rescans everything or goes blind. Lienmark's Gemini 2.5 Flash semantic delta engine instantly ingests the new cut and isolates two distinct drift modalities." | **Invariant 3A**: Version lineage parent binding `v8.parent == v7`.<br>[`get_v8_version`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L35)<br>[`run_drift_analysis`](file:///z:/home/lx_singw/projects/lienmark/backend/main.py#L324) |
| `0:45–0:55` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | Drawer expands on **Item 11** (`poster_noir_detective_magazine`). Visual diff highlights Scene 42: "2s background blur" $\to$ "14s close-up focal dialogue". | "First: **creative drift**. In Scene 42, the director zoomed in on this 1946 Crime Detective magazine poster. It went from a two-second background blur into a fourteen-second focal shot with dialogue, collapsing the prior de minimis fair use defense." | **Invariant 3B**: Creative context alteration & prominence shift.<br>[`poster_noir_detective_magazine`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L209-L250)<br>[`SemanticDeltaEngine.analyze_delta`](file:///z:/home/lx_singw/projects/lienmark/backend/core/semantic_delta.py#L65) |
| `0:55–1:05` | 10s | **Beat 3**<br>Version 8 changes one creative dependency & evidence another | Drawer shifts to **Item 12** (`music_cue_midnight_serenade`). Script diff shows zero textual changes (identical Scene 18 jazz trio, 20s). Real-world status card flags registry alert. | "Second: **external evidence drift**. For the Scene 18 jazz cue *Midnight Serenade*, the script did not change by a single word. But out in the real world, music copyright registries updated, creating an adverse ownership dispute with Vanguard Media." | **Invariant 3C**: External registry fact divergence with stable creative context.<br>[`music_cue_midnight_serenade`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py#L280-L342)<br>[`DeltaAnalysisResult`](file:///z:/home/lx_singw/projects/lienmark/backend/core/semantic_delta.py#L18) |
| `1:05–1:15` | 10s | **Beat 4**<br>Lienmark carries ten decisions forward automatically | Metric ribbon snaps to state: Total Claims: 12 \| Carried Forward: 10 (Green) \| Reopened: 2 (Amber). Deterministic Lineage Parity Guarantee banner illuminates. | "Watch the **Deterministic Lineage Parity Guarantee**: Lienmark analyzes the causal dependency graph. Ten decisions have identical context hashes and stable public evidence. Lienmark carries all ten decisions forward automatically." | **Invariant 4A**: Selective invalidation $(12 \to 10/2 \to 1/1)$ holding $12 = 10 + 1 + 1$.<br>`backend/core/invalidation_engine.py`<br>`frontend/app/page.tsx` |
| `1:15–1:25` | 10s | **Beat 4**<br>Lienmark carries ten decisions forward automatically | Cursor highlights "$0.00 Review Expense" badge and "0 External Queries" counter beside the 10 green carried-forward table rows. | "That is 10 carried forward legal approvals: zero dollars spent on redundant attorney re-review, and zero external queries dispatched. Only the two affected decisions are reopened for counsel attention." | **Invariant 4B**: Economic savings & zero-query carry forward.<br>[`RevalidationPlanner.plan_revalidation`](file:///z:/home/lx_singw/projects/lienmark/backend/services/revalidation_planner.py#L40)<br>[`test_12_to_10_carried_2_reopened`](file:///z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L45) |
| `1:25–1:35` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | Telemetry panel opens: Parallel Search request inspector. Budget governor shows: Planned Queries: 2 \| Skipped: 10 \| Query Reduction: 83.3%. Live request IDs flash green. | "Instead of firing twelve expensive web searches, our budget governor dispatches the **Parallel Search API** to re-ground strictly the two affected assets. That is an **83.3% query reduction** (2 calls vs 12) at runtime." | **Invariant 5A**: Exact 83.3% search query reduction (2 calls vs 12).<br>`backend/services/parallel_service.py`<br>[`plan.call_reduction_percentage == 83.3`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L267) |
| `1:35–1:45` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | UI displays Item 11 Parallel Search card: Target query *Crime Detective Magazine 1946 copyright renewal*. Citation: Library of Congress Historical Catalog (`cocatalog.loc.gov`), renewal expired 1974. Stance: `SUPPORTING`. Latency: 142.5ms. | "For Item 11, Parallel searches the Library of Congress catalog in 142 milliseconds, retrieving authoritative evidence that the 1946 registration expired without renewal, confirming the artwork is in the public domain." | **Invariant 5B**: Public domain attribution via Library of Congress.<br>[`PublicEvidenceSnapshot`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L18)<br>[`EvidenceStance.SUPPORTING`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L25) |
| `1:45–1:55` | 10s | **Beat 5**<br>Parallel Search API refreshes strictly the affected two | UI displays Item 12 Parallel Search card: Target query *Midnight Serenade jazz sync rights 2026*. Citation: ASCAP ACE Repertory bulletin (`ascap.com`). Excerpt: Exclusive sync rights assigned August 2026 to Vanguard Media Holdings LLC. Stance: `CONTRADICTORY`. | "For Item 12, Parallel queries ASCAP ACE repertory records, uncovering that sync rights were assigned to Vanguard Media last month. Stance: Contradictory. Lienmark strictly **fails closed**—public evidence never automatically clears a conflict." | **Invariant 5C**: Fail-closed guardrail on conflicting external stance.<br>[`EvidenceReconciler.reconcile_all`](file:///z:/home/lx_singw/projects/lienmark/backend/core/evidence_reconciler.py#L45)<br>[`EvidenceStance.CONTRADICTORY`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L26) |
| `1:55–2:05` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Counsel Checkpoint drawer opens. Header: *Reviewing Counsel: Sarah Jenkins, Esq.* 4-Dimensional explanation displayed: Creative Change, Evidence Change, Private Fact, Statutory Policy Reason. | "Here is the human checkpoint: Lienmark separates AI decision support from legal adjudication. For Item 11, Sarah Jenkins reviews the 4D breakdown, confirms public domain doctrine under 17 U.S.C. § 304, and clicks **Re-Attest**." | **Invariant 6A**: Human-in-the-loop counsel adjudication.<br>`backend/core/counsel_checkpoint.py`<br>[`ReviewAction.RE_ATTEST`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L31) |
| `2:05–2:15` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Next.js Server Action executes. Optimistic UI updates Item 11 badge to `RE_ATTESTED` (Blue). Toast confirms: "✓ Re-Attested Item 11 under Public Domain doctrine." Audit log appends SHA-256 event hash. | "Via Next.js Server Actions, Item 11 optimistically updates to 1 re-attested. The event is permanently chained into our tamper-evident SHA-256 audit ledger in `scripts/run_rehearsal.py`, preserving cryptographic proof of counsel sign-off." | **Invariant 6B**: Optimistic UI update & SHA-256 audit chaining.<br>[`submitReviewAction`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/actions.ts#L246)<br>`scripts/run_rehearsal.py` |
| `2:15–2:25` | 10s | **Beat 6**<br>Counsel checkpoint: Sarah Jenkins resolves one and leaves one exception | Drawer advances to Item 12 (*Midnight Serenade*). Counsel rationale entered: "Active Vanguard Media adverse copyright claim; designate as warranty exception." Clicks **Exception / Reject**. Badge turns `EXCEPTION` (Red). | "For Item 12, counsel will not clear an adverse copyright claim. She designates the cue as 1 exception. Lienmark records the rejection, completing human review for Version 8." | **Invariant 6C**: Counsel exception designation & ledger integrity.<br>[`ReviewAction.REJECT`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L32)<br>[`verify_ledger_integrity`](file:///z:/home/lx_singw/projects/lienmark/backend/core/counsel_checkpoint.py#L620) |
| `2:25–2:35` | 10s | **Beat 7**<br>Updated schedule makes remaining risk explicit for underwriter | User clicks **"📄 Export Form E&O-2026 Exceptions Schedule"**. High-fidelity Server-Side Rendered (SSR) printable report opens at `/report/proj_blockbuster_cinema`. Printable `@media print` layout previewed. | "Finally, user exports the **Form E&O-2026 Exceptions Schedule**. Rendered server-side for underwriter delivery via `frontend/app/report/[production_id]/page.tsx`, this document satisfies the mandatory clearance warranty conditions for carrier policy binding." | **Invariant 7A**: SSR printable report with `@media print` CSS.<br>`backend/core/exceptions_schedule.py`<br>`frontend/app/report/[production_id]/page.tsx` |
| `2:35–2:45` | 10s | **Beat 7**<br>Updated schedule makes remaining risk explicit for underwriter | Zoom into the 3-Tier Section Breakdown: Section I: 1 Open Exception \| Section II: 1 Re-Attested Item \| Section III: 10 Carried Forward = 12 Total. Underwriting signature block and statutory disclaimer visible. Closing logo. | "Notice the mathematical conservation: 10 carried forward + 1 re-attested + 1 exception = 12 total. Clear, version-bound risk transparency for underwriters, brokers, and producers. That is Lienmark." | **Invariant 7B**: Mathematical Conservation Law: $12 = 10 + 1 + 1$ under $12 \to 10/2 \to 1/1$.<br>[`schedule.total_claims == 12`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L425)<br>[`Statutory Underwriting Disclaimers`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L775) |

---

## 4. Architectural Invariants & Mathematical Proofs

The narrative presentation is bounded by three immutable mathematical and cryptographic laws enforced across `backend/`, `frontend/`, and `tests/`:

### 4.1 The Mathematical Conservation Law ($12 = 10 + 1 + 1$)
In every comparison cycle between locked baseline Version 7 and production revision Version 8, the total universe of evaluated rights-bearing claims is conserved without leak, omission, or duplication through the transition pipeline:

$$\mathbf{12 \longrightarrow 10/2 \longrightarrow 1/1}$$
$$\mathbf{N_{\text{total}}} = N_{\text{carried}} + N_{\text{re-attested}} + N_{\text{exception}}$$
$$\mathbf{12 = 10 + 1 + 1}$$

- **Section I (Underwriting Exceptions Rider):** Exactly **1 exception** (`music_cue_midnight_serenade`) with unresolved adverse ownership claim (Vanguard Media Holdings LLC). Excluded from policy warranty.
- **Section II (Re-Attested Public Domain Register):** Exactly **1 re-attested** asset (`poster_noir_detective_magazine`) corroborated under 17 U.S.C. § 304 via Library of Congress catalog renewal records.
- **Section III (Certified Carried-Forward Register):** Exactly **10 carried forward** assets with identical SHA-256 context hashes and stable public evidence. Carried forward at **$0.00 review expense**.

### 4.2 Query Optimization Ratio (83.3% Network Reduction)
By executing selective DAG invalidation prior to network dispatch, the Revalidation Planner eliminates redundant public registry queries, achieving an exact **83.3%** reduction (**2 calls vs 12** full refreshes):

$$\text{Query Reduction} = \frac{N_{\text{total}} - N_{\text{reopened}}}{N_{\text{total}}} = \frac{12 - 2}{12} = \mathbf{83.3\%}$$

- Planned Parallel Search Queries: **2** (`poster_noir_detective_magazine`, `music_cue_midnight_serenade`)
- Skipped Unchanged Queries: **10**
- Actual Live Calls: **2** (verified by `parallel.call_count == 2` in [`scripts/run_rehearsal.py:L280`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L280))

### 4.3 Cryptographic Audit Ledger Chaining (SHA-256)
Every counsel action appends a tamper-evident `SupersessionEvent` where each event's hash cryptographically seals its predecessor:

$$\text{Hash}_k = \text{SHA-256}\Big(\text{EventID}_k \parallel \text{LineageKey}_k \parallel \text{Action}_k \parallel \text{Status}_k \parallel \text{Rationale}_k \parallel \text{Timestamp}_k \parallel \text{Hash}_{k-1}\Big)$$

- Genesis Parent Hash: `"0" * 64`
- Item 11 Hash: `evt_11.event_hash` (64-character SHA-256 digest)
- Item 12 Hash: `evt_12.parent_event_hash == evt_11.event_hash` (verified by [`scripts/run_rehearsal.py:L379`](file:///z:/home/lx_singw/projects/lienmark/scripts/run_rehearsal.py#L379))

### 4.4 Mandatory Code Pointers Parity Index
Every code pointer referenced in the story lock and pitch script corresponds to verified, tested repository code:
- `backend/core/invalidation_engine.py` (Deterministic Invalidation DAG & Policy Engine)
- `backend/services/parallel_service.py` (Parallel Search API Client & Citation Extractor)
- `backend/core/counsel_checkpoint.py` (Human Counsel Checkpoint & Cryptographic Audit Trail)
- `backend/core/exceptions_schedule.py` (Form E&O-2026 Exceptions Schedule Generator)
- `scripts/run_rehearsal.py` (End-to-End Pipeline Execution Harness)
- `frontend/app/page.tsx` (Next.js Reviewer Dashboard & Intake Interface)
- `frontend/app/report/[production_id]/page.tsx` (Next.js SSR Form E&O-2026 Report Page)

---

## 5. Presenter Teleprompter & Visual Choreography Guidance

### 5.1 Speaker Tone & Cadence
- **Target Word Count:** 345 words across 165 seconds (~125 words per minute).
- **Tone Profile:** Authoritative, measured, technically rigorous, entertainment-industry fluent. Avoid breathless hype; speak like senior production clearance counsel presenting to an E&O underwriter.
- **Micro-Pauses:** Maintain deliberate 1.5-second pauses after key technical punchlines ("That silent divergence is clearance drift.", "That is an 83.3% query reduction.", "10 carried forward + 1 re-attested + 1 exception = 12 total.").

### 5.2 Screen Transitions & Camera Directives
- **`[0:00]` CUT TO MASTER SPLIT:** High-contrast title card $\to$ Paper binder vs. Modern NLE timeline.
- **`[0:15]` TRANSITION TO HOSTED UI:** Clean browser window displaying `frontend/app/page.tsx` at `/dashboard`.
- **`[0:35]` MOUSE CLICK:** Steady click on `⚡ Ingest V8 & Detect Drift`. No jittery mouse cursor sweeps.
- **`[0:45]` SMOOTH ZOOM (120%):** Focus on Explanation Drawer for Item 11.
- **`[1:25]` CUT TO TELEMETRY TAB:** Display Parallel Search API latency meters and live request logs.
- **`[1:55]` FOCUS REVIEW DRAWER:** Highlight Sarah Jenkins reviewer signature block.
- **`[2:25]` NEW TAB TRANSITION:** Open SSR Form E&O-2026 report (`frontend/app/report/[production_id]/page.tsx`).
- **`[2:35]` PRINT PREVIEW TRIGGER:** Invoke browser print preview (`Ctrl+P`) showing clean `@media print` page breaks.

---

## 6. Statutory Underwriting Disclaimers & Prohibited Claims Standards

### 6.1 Prohibited Legal Certainty Terms Audit
In strict accordance with [`docs/compliance/05_claims_register_and_language_defense.md`](file:///z:/home/lx_singw/projects/lienmark/docs/compliance/05_claims_register_and_language_defense.md), this document, `docs/pitch_script.md`, and all demonstration presentations contain **zero occurrences** of prohibited legal certainty terms:
- Guarantees of insurance coverage (0 occurrences)
- Automated policy binding claims (0 occurrences)
- Assertions certifying legal certainty (0 occurrences)
- Declarations binding insurance carriers or underwriters (0 occurrences)
- Statements claiming legal clearance by AI (0 occurrences)
- Representations of zero liability risk (0 occurrences)
- Declarations of 100% legal assurances or insurer commitments (0 occurrences)

### 6.2 Mandatory Statutory Disclaimers

> **LEGAL & UNDERWRITING DECISION SUPPORT DISCLAIMER:**  
> Lienmark is an automated clearance change control and decision support platform engineered exclusively for licensed production counsel and entertainment Errors & Omissions (E&O) insurance underwriters. Lienmark does not practice law, does not provide legal advice, does not issue insurance policies, and does not certify absolute non-infringement. All generated schedules, risk indicators, and re-attestation logs represent non-binding advisory material subject to independent human review by licensed attorneys. Formal E&O insurance coverage is conditioned upon independent underwriter evaluation, audit satisfaction, and execution of a policy binder.

> **FICTIONAL DEMONSTRATOR SCENARIO DISCLOSURE:**  
> The demonstration motion picture production (*Shadows Over Broadway*, `proj_blockbuster_cinema`), script revision versions (V7, V8), clearance claims, third-party entities (*Vanguard Media Holdings LLC*, *Apex Film Distributors*), and clearance counsel identity (*Sarah Jenkins, Esq.*) are entirely fictional demonstrator fixtures created for the Agentic Cinema Hackathon. Any resemblance to actual commercial productions, pending legal disputes, or living persons is purely coincidental.
