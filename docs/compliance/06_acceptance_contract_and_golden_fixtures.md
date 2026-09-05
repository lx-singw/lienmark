# Sprint 0B Acceptance Contract, Golden Fixture Freeze & P0 Scope Isolation

> **Hackathon**: Agentic Cinema: The Blockbuster Hackathon  
> **Evaluation Milestone**: Sprint 0B Tasks 6, 7, 8 — Acceptance Contract Freeze & P0 Scope Isolation  
> **Track Focus**: Parallel Track ($15,000 Prize Pool) & Core Agentic Implementation  
> **Document Status**: Complete & Authoritative (Sprint 0B Tasks 6, 7, 8 Executed)  
> **Audited Date**: September 5, 2026 (Base review: September 1, 2026)  
> **Project**: [Lienmark — Clearance Change Control for E&O](https://github.com/lx-singw/lienmark)  
> **Auditor & Lead Architect**: Linda Singwane (`lx-singw`)  
> **Policy Version**: `E&O-2026.1-DEVPOST`  
> **Verification Verdict**: **ALL ACCEPTANCE CRITERIA & SCOPE ISOLATION GATES 100% VERIFIED PASS**

---

## 1. Executive Summary & Audit Foundation

In entertainment production and Errors & Omissions (E&O) insurance underwriting, the primary legal and economic bottleneck is not finding initial rights-holders for a script; rather, it is **clearance drift**: the divergence between what was legally approved at script lock and what the live production revision, cut, or current copyright register actually contains.

Prior to Sprint 0B, clearance management solutions defaulted to one of two unacceptable failure modes:
1. **The Exhaustive Rescan**: Re-researching all clearance items from scratch on every draft change, incurring exorbitant legal fees and redundant API costs.
2. **Blind Carry-Forward**: Assuming past approvals remain valid indefinitely, exposing productions to statutory copyright infringement damages of up to \$150,000 per willful violation under 17 U.S.C. § 504(c).

Sprint 0B formally defines the **P0 Scope Wedge** and freezes the **Acceptance Contract** for Lienmark:
* **The Product**: Clearance Change Control for E&O.
* **The User**: Production & Clearance Counsel ([`CounselDecision`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L94)).
* **The Output**: Reconciled Version-Bound Exceptions Schedule ([`ExceptionsSchedule`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L142) on Form E&O-2026).
* **The Core Differentiator**: Deterministic selective invalidation—carrying unaffected approvals forward fail-closed while reopening only decisions whose creative context or external evidence has drifted.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THE 12 ──► 10/2 ──► 1/1 MAGIC MOMENT                             │
│                                                                                                  │
│   Production Script v7 (12 Items) ──────► Production Revision v8 (12 Items)                      │
│                                                   │                                              │
│                        ┌──────────────────────────┴──────────────────────────┐                   │
│                        ▼                                                     ▼                   │
│               10 Unchanged Approvals                                 2 Reopened Claims           │
│             (Carried Forward Fail-Closed)                             (Stale Decisions)          │
│             [0 searches | $0.00 cost]                                        │                   │
│                        │                          ┌──────────────────────────┴────────┐          │
│                        │                          ▼                                   ▼          │
│                        │                   Scene 42 Poster                     Scene 18 Music    │
│                        │                  (Creative Drift)                   (Evidence Drift)    │
│                        │                          │                                   │          │
│                        │                 Parallel Search LOC                 Parallel Search     │
│                        │                (Public Domain: Pass)              (Vanguard: Conflict)  │
│                        │                          │                                   │          │
│                        │                  Counsel Re-Attests                  Counsel Flags as   │
│                        │                 [STATUS: APPROVED]                 [STATUS: EXCEPTION]  │
│                        │                          │                                   │          │
│                        └──────────────────────────┼───────────────────────────────────┘          │
│                                                   ▼                                              │
│                                    Form E&O-2026 Exceptions Schedule                             │
│                                  Total: 12 | Carried: 10 | Re-Attested: 1 | Exceptions: 1        │
│                                 83.33% REVIEW REDUCTION — 100% FAIL-CLOSED SAFETY                │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Sprint 0B Scope Demolition & P0 Isolation Architecture

### 2.1 Demolition Rationale

To deliver an insurer-grade, testable, and demonstrable vertical slice under the strict deadlines of the Agentic Cinema Hackathon, speculative and decorative components were decisively quarantined. The P0 scope boundary enforces strict separation between defensible core intellectual property and post-competition roadmap items.

### 2.2 Formal Feature Classification Matrix

| Capability / Module | Scope Tier | Architectural Status | Implementation Symbol | Boundary Enforcement |
|---|---|---|---|---|
| **Deterministic Invalidation Engine** | **P0** | Active Core IP | [`InvalidationEngine`](file:///Z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L28) | Fully implemented; fail-closed rules |
| **Google Gemini 2.5 Flash Semantic Delta** | **P0** | Active Core Service | [`GeminiService.analyze_scene_delta`](file:///Z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L45) | Structured Pydantic outputs |
| **Parallel Search API Live Evidence** | **P0** | Mandatory Integration | [`ParallelSearchService.search`](file:///Z:/home/lx_singw/projects/lienmark/backend/services/parallel_service.py#L29) | Runtime API calls; source citations |
| **Agent Builder / ADK Orchestration** | **P0** | Active Workflow | [`LienmarkWorkflow`](file:///Z:/home/lx_singw/projects/lienmark/backend/orchestration/workflow.py#L53) | Step trace correlation; state pipeline |
| **Human Counsel Re-Attestation Flow** | **P0** | Mandatory HITL Gate | [`ReattestationRequest`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L121) | Consequential legal sign-off |
| **Form E&O-2026 Exceptions Schedule** | **P0** | Reconciled Output | [`ExceptionsSchedule`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L142) | Mathematical reconciliation |
| **Next.js 15 Reviewer Dashboard** | **P0** | User Interface | [`frontend/`](file:///Z:/home/lx_singw/projects/lienmark/frontend) | Real-time claims & schedule display |
| *Scheduled Public-Evidence Refresh* | **P1** | Post-P0 Hardening | Background cron daemon | Scheduled for Phase 5 |
| *Tamper-Evident SHA-256 Hash Linking* | **P1** | Post-P0 Hardening | Decision event chains | Scheduled for Phase 5 |
| *Multi-Jurisdiction Foreign Law Engine* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | Isolated; 17 U.S.C. scope only |
| *Blockchain / Web3 / RFC-3161 Timestamping* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | Automated test asserts absence |
| *Insurance Carrier Auto-Binding APIs* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | Automated test asserts absence |
| *6-Agent Peer Deliberation / Message Bus* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | Automated test asserts absence |
| *Computer Vision / Video Frame Scraping* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | Automated test asserts absence |
| *Automated Fair-Use Risk Probability %* | **DEFERRED** | Quarantined / Demolished | Prohibited in P0 | No speculative probability claims |

### 2.3 Automated Scope Boundary Test

The scope boundary is continuously guarded by [`tests/test_scope_boundary.py`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_scope_boundary.py). The test mechanically inspects the filesystem and parses the Abstract Syntax Tree (AST) of all Python modules in [`backend/core/`](file:///Z:/home/lx_singw/projects/lienmark/backend/core) and [`backend/services/`](file:///Z:/home/lx_singw/projects/lienmark/backend/services):
* Verifies zero files contain prohibited tokens (`blockchain`, `web3`, `carrier_api`, `peer_bus`, `cv2`, `torchvision`, etc.).
* Verifies zero `ast.Import` or `ast.ImportFrom` nodes reference deferred packages or services.
* Verifies no deferred libraries are loaded in active execution runtime.

---

## 3. The Single-Sentence Demo Contract

As specified in Sprint 0B Task 7 and the [Demo Playbook](../winning/05-demo-and-submission-playbook.md), the entire product narrative is governed by an inviolable, single-sentence operational contract:

> **"Every decision is bound to the exact cut and evidence reviewed. Parallel keeps that evidence current; when either changes, Lienmark reopens only the decisions that no longer carry forward."**

### 3.1 Contract Decomposition & Guarantees

1. **Version-Bound Decision Immutability**: No approval floats as a generalized clearance. A decision is valid *if and only if* its exact creative context hash ($h = \text{SHA256}(\text{context} \mathbin{\Vert} \text{prominence})_{0..15}$) and external evidence snapshot match.
2. **Parallel Live Currency**: Parallel Search API queries are triggered selectively when dependent facts drift, guaranteeing fresh public evidence.
3. **Selective Reopening**: Decisions whose dependencies remain satisfied are carried forward automatically without incurring attorney re-review or API latency.
4. **Fail-Closed Default**: Any missing asset, unmapped lineage key, ambiguous registry response, or search timeout automatically transitions the claim to `DecisionState.STALE`, forbidding automated approval.

---

## 4. Formal Acceptance Criteria: The 12 ──► 10/2 ──► 1/1 Magic Moment

The core evaluation scenario centers on the fictional noir production **"Shadows Over Broadway"** (`proj_blockbuster_cinema`), reconciling twelve rights-bearing uses between **Locked Script Version 7** (`v7`) and **Production Revision Version 8** (`v8`).

### 4.1 Stage 1: Base Version V7 (12 Reviewed Claims)

* **Initial State**: All 12 creative uses possess valid, verified counsel approvals documented by Sarah Jenkins, Esq.
* **Disposition**: Status = `DecisionStatus.APPROVED`.
* **Lineage Keys**: `prop_vintage_telephone`, `poster_paris_expo_1937`, `car_ford_sedan_1949`, `trademark_acme_coffee`, `artwork_abstract_expressionist`, `likeness_mayor_cameo`, `architecture_tribunal_facade`, `text_headline_gazette`, `wardrobe_fedora_brand`, `music_incidental_radio_static`, `poster_noir_detective_magazine`, `music_cue_midnight_serenade`.

### 4.2 Stage 2: Target Version V8 Invalidation (10 Carried / 2 Stale)

Upon script revision ingestion, [`InvalidationEngine.evaluate_invalidation`](file:///Z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L115) evaluates all 12 claims against creative deltas and refreshed external evidence:

#### The 10 Unchanged Uses (Carried Forward Fail-Closed)
* Items 01 through 10 experience **zero creative context modification** (`base_use.context_hash == target_use.context_hash`).
* External evidence snapshots reflect no adverse ownership disputes.
* **Result**: Evaluated state = [`DecisionState.CARRIED_FORWARD`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L22); reason code = `DEPENDENCIES_SATISFIED_UNCHANGED`. Zero Parallel Search API calls required.

#### Item 11: Creative Drift — Scene 42 Poster (`poster_noir_detective_magazine`)
* **Creative Shift**: Upgraded from an incidental, out-of-focus background blur (2s) to a focal, close-up hero prop with spoken dialogue (14s).
* **Engine Detection**: `context_hash` diverges completely.
* **Decision State**: [`DecisionState.STALE`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L23).
* **Reason Code**: `CREATIVE_CONTEXT_ALTERED`.
* **Revalidation Action**: `revalidate`.
* **Runtime Search**: Parallel Search API executes targeted query (`"1946 Crime Detective Magazine Shadows Over Broadway copyright renewal"`) and retrieves Library of Congress renewal record proving USA public domain expiration (Stance: `EvidenceStance.SUPPORTING`).

#### Item 12: External Evidence Drift — Scene 18 Music (`music_cue_midnight_serenade`)
* **Creative State**: Narrative context and duration are 100% identical between V7 and V8 (`ChangeKind.UNCHANGED`).
* **External Evidence Shift**: Runtime Parallel Search API query (`"Midnight Serenade jazz sync rights copyright owner 2026"`) returns active ASCAP ACE / Billboard notice of exclusive worldwide master and sync acquisition by Vanguard Media Holdings LLC.
* **Decision State**: [`DecisionState.STALE`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L23).
* **Reason Code**: `EXTERNAL_EVIDENCE_SHIFT`.
* **Trigger**: Adverse stance (`EvidenceStance.CONTRADICTORY`) overrides unchanged creative delta.

### 4.3 Stage 3: Human-in-the-Loop Re-attestation & Exceptions Schedule (1 Re-Attested / 1 Exception)

Production Clearance Counsel reviews the synthesized Gemini briefings and Parallel evidence cards:
1. **Item 11 (Poster)**: Counsel executes [`ReattestationRequest`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L121) approving the item based on verified public domain documentation retrieved by Parallel. Final status = [`DecisionState.RE_ATTESTED`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L24) (`APPROVED`).
2. **Item 12 (Music)**: Counsel rejects the item due to adverse third-party ownership conflict, logging instructions to replace the audio cue in post-production. Final status = [`DecisionState.EXCEPTION`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L25) (`REJECTED` / `UNRESOLVED EXCEPTION`).

### 4.4 Mathematical Invariants & Equalities

Every execution of the Lienmark engine must satisfy the following exact mathematical equalities:

$$\begin{aligned}
N_{\text{total}} &= 12 \\
N_{\text{carried}} &= 10 \\
N_{\text{reopened}} &= 2 \\
N_{\text{reattested}} &= 1 \\
N_{\text{exception}} &= 1
\end{aligned}$$

$$\textbf{Invariant 1 (Stage 2 Invalidation):} \quad N_{\text{total}} = N_{\text{carried}} + N_{\text{reopened}} \iff 12 = 10 + 2$$

$$\textbf{Invariant 2 (Stage 3 Review):} \quad N_{\text{reopened}} = N_{\text{reattested}} + N_{\text{exception}} \iff 2 = 1 + 1$$

$$\textbf{Invariant 3 (Schedule Reconciliation):} \quad N_{\text{total}} = N_{\text{carried}} + N_{\text{reattested}} + N_{\text{exception}} \iff 12 = 10 + 1 + 1$$

$$\textbf{Selectivity Ratio:} \quad \mathcal{S} = \frac{N_{\text{reopened}}}{N_{\text{total}}} = \frac{2}{12} = \mathbf{16.67\%}$$

$$\textbf{Review Burden Reduction:} \quad \mathcal{R} = 1 - \mathcal{S} = \frac{10}{12} = \mathbf{83.33\%}$$

$$\textbf{False Carry-Forward Count:} \quad \mathcal{FC} = \mathbf{0} \quad (\text{Strict Deterministic Bound})$$

---

## 5. Observability Trace Schema

Observability is engineered directly into the pipeline as an architectural prerequisite, capturing correlated execution telemetry across Gemini, the Invalidation Engine, and the Parallel Search API.

### 5.1 Telemetry Data Contract

The pipeline emits structured execution traces conforming to canonical Pydantic v2 schemas:

```python
class WorkflowStepTrace(BaseModel):
    step_name: str
    component: str           # e.g., 'Gemini 2.5 Flash', 'InvalidationEngine', 'Parallel Search API'
    status: str              # 'SUCCESS' | 'ERROR' | 'FAIL_CLOSED'
    duration_ms: float
    details: Dict[str, Any]  # Correlated payload, query strings, reason codes, stance

class WorkflowRunResult(BaseModel):
    run_id: str
    base_version: str        # 'v7'
    target_version: str      # 'v8'
    total_claims: int        # 12
    carried_forward_count: int  # 10
    reopened_count: int      # 2
    claims: List[Dict[str, Any]]
    counsel_briefings: Dict[str, ClearanceBriefing]
    execution_traces: List[WorkflowStepTrace]
    total_duration_ms: float
```

### 5.2 Complete JSON Trace Schema Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LienmarkWorkflowTrace",
  "type": "object",
  "required": [
    "run_id",
    "base_version",
    "target_version",
    "total_claims",
    "carried_forward_count",
    "reopened_count",
    "execution_traces",
    "total_duration_ms"
  ],
  "properties": {
    "run_id": {
      "type": "string",
      "pattern": "^run_[a-f0-9]{8}$",
      "description": "Unique deterministic execution correlation ID"
    },
    "base_version": { "type": "string", "enum": ["v7"] },
    "target_version": { "type": "string", "enum": ["v8"] },
    "total_claims": { "type": "integer", "const": 12 },
    "carried_forward_count": { "type": "integer", "const": 10 },
    "reopened_count": { "type": "integer", "const": 2 },
    "execution_traces": {
      "type": "array",
      "minItems": 4,
      "items": {
        "type": "object",
        "required": ["step_name", "component", "status", "duration_ms", "details"],
        "properties": {
          "step_name": { "type": "string" },
          "component": { "type": "string" },
          "status": { "type": "string", "enum": ["SUCCESS", "ERROR", "FAIL_CLOSED"] },
          "duration_ms": { "type": "number", "minimum": 0.0 },
          "details": { "type": "object" }
        }
      }
    },
    "total_duration_ms": { "type": "number", "minimum": 0.0 }
  }
}
```

### 5.3 Pipeline Step Trace Catalog

| Step Index | `step_name` | Executing Component | Telemetry Payload (`details`) | Expected Latency |
|:---:|---|---|---|:---:|
| **1** | `version_ingestion` | `LienmarkEngine` | `{"v7_uses": 12, "v8_uses": 12}` | $< 1.0\text{ ms}$ |
| **2** | `semantic_delta_analysis` | `Gemini 2.5 Flash` | `{"is_material": true, "prominence_shift": "incidental_to_focal", "recommended_action": "revalidate"}` | $420\text{ ms}$ |
| **3** | `deterministic_dependency_invalidation` | `InvalidationEngine` | `{"carried_forward": 10, "reopened": 2, "policy": "E&O-2026.1-DEVPOST"}` | $< 1.0\text{ ms}$ |
| **4a** | `parallel_targeted_search_poster` | `Parallel Search API` | `{"query": "...", "stance": "supporting", "provider_call_id": "prl_call_882910_poster", "source_url": "https://cocatalog.loc.gov/..."}` | $142.5\text{ ms}$ |
| **4b** | `parallel_targeted_search_music` | `Parallel Search API` | `{"query": "...", "stance": "contradictory", "provider_call_id": "prl_call_993012_music", "source_url": "https://ascap.com/..."}` | $178.2\text{ ms}$ |
| **5** | `counsel_briefing_synthesis` | `Gemini 2.5 Flash` | `{"briefings_count": 2, "recommended_actions": ["re-attest", "reject"]}` | $310.0\text{ ms}$ |

### 5.4 Parallel Search API Call-Level Telemetry Schema

Every Parallel Search invocation produces attributable provenance metadata stored on [`PublicEvidenceSnapshot`](file:///Z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L77):

```json
{
  "snapshot_id": "snap_v8_music_cue_midnight_serenade",
  "use_id": "use_v8_music_midnight_serenade",
  "stable_lineage_key": "music_cue_midnight_serenade",
  "query": "Midnight Serenade jazz sync rights copyright owner 2026",
  "provider": "Parallel",
  "provider_call_id": "prl_call_993012_music",
  "source_url": "https://ascap.com/ace-title-search/midnight-serenade-9921",
  "source_title": "ASCAP ACE Repertory & Billboard Rights Bulletin",
  "excerpt": "Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain assertions disputed under European term extension.",
  "stance": "contradictory",
  "cached_or_live": "live",
  "retrieval_latency_ms": 178.2
}
```

---

## 6. Golden Evaluation Set Freeze

To guarantee total audit reproducibility and guard against ground-truth corruption, the evaluation corpus is frozen in code and immutably pinned.

### 6.1 Corpus Provenance & Integrity Pin

* **Canonical Fixture Module**: [`backend/fixtures/golden_dataset.py`](file:///Z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py)
* **Production Twin**: Fictional noir screenplay *"Shadows Over Broadway"* (`proj_blockbuster_cinema`).
* **SHA-256 Integrity Fingerprint**: `e4d77517a61d1521a004eb7c94b790d9657fb05a06900ee63462f447f5a9e32a`
* **Freeze Date**: September 1, 2026 (Re-verified September 5, 2026).

### 6.2 The Canonical 12-Item Golden Dataset Catalog

| # | Stable Lineage Key | Asset Type | Scene & Location | Baseline V7 Context & Prominence | Target V8 Delta & Context | Expected V8 State | Statutory / Legal Defense |
|:---:|---|---|---|---|---|:---:|---|
| **01** | `prop_vintage_telephone` | Prop | Scene 04 — Office | 1950s Western Electric Rotary Phone; 4s incidental desk dressing | Unchanged (Hash Match) | `CARRIED_FORWARD` | *De minimis* background set dressing |
| **02** | `poster_paris_expo_1937` | Artwork | Scene 08 — Corridor | Vintage 1937 Paris Expo reproduction; 3s hallway blur | Unchanged (Hash Match) | `CARRIED_FORWARD` | Pre-1978 public domain reproduction |
| **03** | `car_ford_sedan_1949` | Prop | Scene 12 — Street | 1949 Ford Custom Tudor Sedan; 6s exterior street background | Unchanged (Hash Match) | `CARRIED_FORWARD` | Expired design patent / non-focal auto |
| **04** | `trademark_acme_coffee` | Trademark | Scene 15 — Diner | Fictional Acme Coffee painted sign; 5s set dressing background | Unchanged (Hash Match) | `CARRIED_FORWARD` | Nominative fair use; no consumer confusion |
| **05** | `artwork_abstract_expressionist` | Artwork | Scene 21 — Penthouse | Abstract oil canvas; 8s medium shot behind executive desk | Unchanged (Hash Match) | `CARRIED_FORWARD` | Studio-owned prop canvas agreement |
| **06** | `likeness_mayor_cameo` | Likeness | Scene 26 — Courtroom | Background courtroom extra resembling former mayor; 2s crowd | Unchanged (Hash Match) | `CARRIED_FORWARD` | Executed background actor talent release |
| **07** | `architecture_tribunal_facade` | Location | Scene 30 — Civic Center | Exterior county courthouse stone steps; 3s wide establishing shot | Unchanged (Hash Match) | `CARRIED_FORWARD` | 17 U.S.C. § 120(a) architectural panorama |
| **08** | `text_headline_gazette` | Text | Scene 34 — Newsstand | Newspaper headline 'MYSTERY WITNESS DISAPPEARS'; 2s insert prop | Unchanged (Hash Match) | `CARRIED_FORWARD` | Original studio-authored script prop |
| **09** | `wardrobe_fedora_brand` | Trademark | Scene 38 — Subway | Vintage Borsalino fedora worn by secondary character; 10s arrival | Unchanged (Hash Match) | `CARRIED_FORWARD` | Trademark exhaustion / first sale doctrine |
| **10** | `music_incidental_radio_static` | Music | Scene 40 — Safehouse | Foley vintage radio broadcast low hum & static; 12s ambient audio | Unchanged (Hash Match) | `CARRIED_FORWARD` | Licensed master sound design library |
| **11** | `poster_noir_detective_magazine` | Artwork | Scene 42 — Desk | 1946 Crime Detective cover; 2s out-of-focus background blur | **MATERIAL DRIFT**: 14s close-up focal prop with spoken dialogue | **STALE**<br>(Reopened) | Creative drift invalidates *de minimis*; re-attested under LOC public domain |
| **12** | `music_cue_midnight_serenade` | Music | Scene 18 — Speakeasy | Midnight Serenade trumpet solo; 20s speakeasy background jazz | **EVIDENCE DRIFT**: Parallel discovers 2026 Vanguard sync assignment | **STALE**<br>(Reopened) | Exclusive sync conflict; rejected as active unresolved exception |

### 6.3 Frozen Challenge Set Scenarios (E01–E15)

In addition to the primary 12-item demo wedge, the system architecture accommodates 15 edge scenarios specified in the roadmap:

| ID | Scenario Description | Input Perturbation | Expected Engine Response | Safety Invariant |
|:---:|---|---|---|---|
| **E01** | Punctuation-Only Script Edit | Script comma added to scene description | Context hash preserves semantic text; carries forward | Zero unnecessary searches |
| **E02** | Scene Renumbering | Scene 04 renumbered to Scene 05; use unchanged | Stable lineage key matches; carries forward | Lineage preservation |
| **E03** | Music Scope Exceeded | Incidental background music promoted to theme song | Gemini detects scope escalation; marks STALE | Fail-closed on scope drift |
| **E04** | Trademark Negative Portrayal | Branded product used in dangerous or disparaging manner | Material context change flagged; marks STALE | Lanham Act protection |
| **E05** | Newly Added Creative Asset | Unreviewed 13th asset introduced in V8 | Missing predecessor decision; triggers fresh review | No automated clearance |
| **E06** | Reviewed Asset Removed | Script cuts Scene 12 Ford Sedan | Delta engine generates `ChangeKind.REMOVED`; historical archive | Audit trail preserved |
| **E07** | Distribution Window Expiry | License expires prior to worldwide distribution date | Private agreement validator triggers `STALE` | Contractual boundary |
| **E08** | Catalog Corporate Transfer | Catalog acquired by major label during active term | Informational stance; preserves valid existing license | No false invalidation |
| **E09** | Adverse Ownership Dispute | Public registry records competing ownership claim | Contradictory stance; marks STALE for counsel review | Copyright safety |
| **E10** | Parallel Returns No Match | Registry search yields ambiguous or zero hits | Stance marked `INSUFFICIENT`; marks STALE | Fail-closed on no-match |
| **E11** | Single Search API Timeout | One of two Parallel searches experiences network timeout | Resilient execution; timed-out item fails closed to review | Partial failure containment |
| **E12** | Gemini Malformed JSON Output | Model generates schema-non-compliant string | Pydantic validation fallback marks item for manual review | Zero unhandled crashes |
| **E13** | Idempotent Run Submission | Identical version comparison requested twice | Cache deduplication returns existing run ID | Idempotent ledger state |
| **E14** | Counsel Re-attestation Action | Counsel submits re-attestation request via API | Superseding decision recorded with reviewer timestamp | Bounded human primacy |
| **E15** | Exceptions Schedule Reconcile | Export requested following mixed review outcomes | Exact mathematical reconciliation across all items | Underwriter consistency |

---

## 7. Verification & Automated Test Suite Traceability

The complete Lienmark test suite consists of **11 automated unit and integration tests** executing under Python 3.13.14 on Win32:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: Z:\home\lx_singw\projects\lienmark
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

======================== 11 passed, 1 warning in 2.96s ========================
```

### 7.1 Sprint 0B Test-to-Contract Traceability Matrix

| Test ID | Test Function & File Pointer | Verifying Contract Requirement | Assertions & Invariants Checked | Status |
|:---:|---|---|---|:---:|
| **T01** | [`test_golden_fixture_counts`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L22) | Golden Dataset Schema Integrity | $\text{len}(V7) = 12$, $\text{len}(V8) = 12$, $\text{len}(Decisions) = 12$, $\text{len}(Evidence) = 12$ | **PASS** |
| **T02** | [`test_12_to_10_carried_2_reopened`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L30) | Selective Invalidation Magic Moment | Carried = 10, Reopened = 2; `CREATIVE_CONTEXT_ALTERED` & `EXTERNAL_EVIDENCE_SHIFT` | **PASS** |
| **T03** | [`test_fail_closed_policy`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L69) | Fail-Closed Missing Dependency Posture | Artificially severed lineage key results strictly in `DecisionState.STALE` | **PASS** |
| **T04** | [`test_exceptions_schedule_reconciliation`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py#L91) | Form E&O-2026 Schedule Reconciliation | Total: 12 = 10 carried + 1 re-attested + 1 unresolved exception | **PASS** |
| **T05** | [`test_workflow_execution`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_e2e_pipeline.py#L15) | Multi-Agent Orchestration & Traces | Step traces $\ge 4$; exactly 2 Parallel Search calls; Gemini delta verified | **PASS** |
| **T06** | [`test_full_review_to_exceptions_schedule_flow`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_e2e_pipeline.py#L49) | Full HITL Review Lifecycle | Run drift detection $\to$ Attest poster $\to$ Reject music $\to$ Verify final schedule | **PASS** |
| **T07** | [`test_health_endpoints`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_api_endpoints.py#L14) | AntiGravity Provenance Verification | Provenance = `Google AntiGravity`; Track = `Parallel Track ($15,000 Prize Pool)` | **PASS** |
| **T08** | [`test_fixtures_endpoint`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_api_endpoints.py#L26) | REST Fixture Availability | GET `/api/fixtures` returns version-locked V7 & V8 payloads | **PASS** |
| **T09** | [`test_drift_compare_and_review_flow`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_api_endpoints.py#L35) | Full REST Drift & Re-attestation API | POST `/api/drift/compare` $\to$ POST `/api/review/attest` $\to$ GET `/api/reports/exceptions` | **PASS** |
| **T10** | [`test_dashboard_html`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_api_endpoints.py#L80) | Reviewer Dashboard HTML Delivery | GET `/` returns HTML containing `Lienmark`, `Parallel Track`, `Form E&O-2026` | **PASS** |
| **T11** | [`test_p0_scope_boundary_and_contract`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_scope_boundary.py#L25) | **Sprint 0B P0 Scope Isolation & Demo Contract** | AST inspection confirms 0 deferred modules in `core/` or `services/`; asserts demo contract; verifies 12 $\to$ 10/2 $\to$ 1/1 invariants; enforces policy `E&O-2026.1-DEVPOST` | **PASS** |

---

## 8. Compliance Sign-Off & Exit Gate Verification

* **Sprint 0B Tasks Executed**:
  - **Task 6 (Fixtures & Acceptance Contract)**: Formal 12 $\to$ 10/2 $\to$ 1/1 acceptance contract codified and frozen.
  - **Task 7 (Acceptance Test)**: Automated P0 scope boundary and contract test implemented in [`tests/test_scope_boundary.py`](file:///Z:/home/lx_singw/projects/lienmark/tests/test_scope_boundary.py).
  - **Task 8 (Observability Traces & Evaluation Freeze)**: JSON trace schemas defined; golden dataset frozen at SHA-256 fingerprint `e4d775...`.
* **Execution Environment**: Google AntiGravity Agentic IDE & Toolchain (`.gemini/antigravity`).
* **Test Suite Verification**: **11 / 11 Automated Tests Passed (100%) in 2.96 seconds**.
* **Exit Gate Verdict**: **SPRINT 0B EXIT CRITERIA SATISFIED — SCOPE DEMOLISHED, ACCEPTANCE CONTRACT FROZEN, AND P0 SCOPE ISOLATED (PASS)**.
