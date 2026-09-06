# Product Requirements Document (PRD): Clearance Change Control & Continuous Invalidation Engine

**Document Reference**: `docs/planning/02_prd_clearance_change_control.md`  
**System**: Lienmark Clearance Intelligence & Change Control Platform  
**Specification Version**: 2.5.0-ENTERPRISE  
**Date**: September 2026  
**Status**: Authoritative Product Specification  
**Classification**: Legal Operations & Insurance Technology Standard  
**Underwriting Benchmark**: Draft Clearance Exceptions Schedule for counsel and underwriter review (Policy Binder Reference: E&O-2026.1-DEVPOST)

---

## 1. Executive Summary & Strategic Shift

### 1.1 The Entertainment Clearance Crisis: Silent Clearance Drift
Every theatrical film, streaming episodic, documentary, or interactive narrative is an assembly of hundreds of distinct intellectual property, privacy, and proprietary rights. A typical mid-budget feature film ($15M–$45M) carries between 150 and 350 rights-bearing creative uses embedded across its timeline:
- Background music cues and featured source music
- Fine art, prints, sculptures, and murals on set
- Branded consumer products, logos, and commercial packaging
- Scripted fictional character names, corporate entities, and dialogue quotations
- Archival newsreels, documentary footage, and still photography
- Architectural monuments, private facades, and distinctive vehicle designs
- Talent likenesses, voice doubles, and synthetic/generative AI elements

Traditionally, entertainment Errors & Omissions (E&O) clearance is performed as a **monolithic, manual audit at "picture lock"**. A clearance coordinator compiles an 80-to-200 page manual binder; an entertainment law firm bills between $250 and $1,200 per hour to cross-reference every item against public registries, copyright circulars, and licensing agreements.

However, modern cinematic and episodic production is **fundamentally non-linear and continuous**. Production scripts undergo weekly color-coded revisions (*White*, *Blue*, *Pink*, *Yellow*, *Green*, *Goldenrod*, *Salmon*, *Cherry*); post-production editorial generates dozens of offline and online picture assemblies. In this fluid environment, productions fall victim to **Silent Clearance Drift**:
1. **Prominence & Context Escalation**: A background detective magazine poster previously cleared under the *de minimis* doctrine as a 2-second out-of-focus blur in Scene 4 is re-framed in Revision 8 into a 14-second focal close-up where the lead actor reads the cover headline aloud. The statutory *de minimis* defense (17 U.S.C. § 107) collapses completely.
2. **Adverse External Rights Assignment**: A background jazz instrumental cleared under a 1998 catalog license is creatively unchanged, but an external rights transaction transfers exclusive worldwide synchronization rights to a private equity catalog consolidator, rendering the prior license void upon distribution.
3. **Dialogue and Character Interaction**: A prop beverage bottle cleared as incidental set dressing is rewritten so that a villain poisons a victim from it, triggering actionable trademark tarnishment under the Lanham Act (15 U.S.C. § 1125(c)).

When a revision is delivered, entertainment legal teams face an untenable dilemma:
- **Option A (Exhaustive Rescan)**: Re-examine every single asset from scratch. This costs tens of thousands of dollars in redundant legal fees, delays lab delivery, and causes friction with post-production supervisors.
- **Option B (Informal Manual Notes)**: Rely on human memory and margin scribbles. This exposes the production to catastrophic copyright injunctions, distributor delivery rejections, or insurer policy exclusions where statutory damages reach up to $150,000 per willful infringement (17 U.S.C. § 504(c)).

```
Traditional Clearance Binder (Static Point-in-Time)
[Draft v1 Audit] ──► (Revisions v2-v8 Occur Silently) ──► [Distribution Injunction / E&O Denial]
                                                              ▲
                                                    Silent Drift Gap
─────────────────────────────────────────────────────────────────────────────────────────────
Lienmark Version-Bound Dependency Graph (Continuous Change Control)
[Version k Graph] ──► [Revision Ingest] ──► [Selective Invalidation] ──► [Draft Exceptions Schedule]
  - 90% Carried Forward ($0.00 spend)       - Targeted Parallel Search    - Underwriter Review Ready
  - 10% Stale Invalidation                 - Counsel Checkpoint Gate
```

---

### 1.2 The Strategic Shift: From Static Search Reports to Continuous Clearance Change Control

> **Authoritative Core Positioning:**  
> **Lienmark monitors production revisions and rights evidence, identifies which prior clearance decisions need renewed attention, and coordinates investigation and counsel review while preserving unaffected approvals and their evidence.**

> [!IMPORTANT]
> **Defensibility & Legal Non-Delegation Mandate:**  
> This definition establishes the exact operational promise without implying that the software independently establishes legal clearance or renders binding legal determinations. In entertainment law, software cannot engage in the unauthorized practice of law or bind an insurance underwriter. Human entertainment clearance counsel remains the sole legal authority empowered to sign off on rights; Lienmark acts as the continuous change control engine and evidence coordinator.

In the Lienmark paradigm:
1. **Clearance Is Never a Global Boolean**: An asset is never simply "Cleared." Clearance is a version-anchored attestation:
   $$\text{Decision} = f\left(\text{Asset Lineage}, \text{Creative Context Hash}_{V_k}, \text{Prominence Metrics}_{V_k}, \text{Corroborated Evidence}_{T}, \text{Counsel Identity}\right)$$
2. **Selective Fail-Closed Invalidation**: When a new script draft or timeline cut $V_{k+1}$ is ingested, Lienmark executes deterministic lineage diffing. Unchanged items carry forward with unbroken cryptographic lineage proofs at **$0.00 marginal legal and API cost**. Only assets exhibiting material creative delta or adverse external evidence shifts are invalidated into `STALE`.
3. **Targeted Autonomous Research**: High-powered research tools—specifically the **Parallel Search API**—are dispatched exclusively for invalidated nodes. The system executes multi-hop, domain-steered investigation passes without wasting API spend or human attention on stable assets.
4. **Human Counsel Sovereignty**: Autonomous agents extract facts, formulate registry queries, and synthesize legal briefings; **only a licensed human attorney can grant clearance or approve an exception**. The system strictly enforces the doctrine that artificial intelligence cannot engage in the unauthorized practice of law (UPL) or bind insurance coverage.
5. **Auditable Underwriter Lineage**: Every state transition, research excerpt, clarification response, and counsel attestation is immutably committed to an append-only SHA-256 hash-chained ledger, generating an exportable **Draft Clearance Exceptions Schedule for counsel and underwriter review**.
6. **The Deterministic Boundary & Comparison Certainty Nuance**: A deterministic graph consistently propagates changes across recorded dependencies, but cannot guarantee an AI extractor identified every asset or dependency correctly. Store source locations, extraction versions, extraction uncertainty, and reviewer corrections. **"No relevant change detected"** must remain strictly distinguishable from **"we could not reliably compare these inputs."** Incomparable or uncertain inputs fail closed to human review rather than silently carrying forward.

---

## 2. The 6 Command Center Destinations

The Lienmark Enterprise Command Center is structured into six dedicated, interconnected destinations. Each destination fulfills a distinct operational mandate for legal teams, post-production supervisors, and insurance underwriters.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                LIENMARK ENTERPRISE COMMAND CENTER WORKSPACE                             │
├────────────────────────────────┬──────────────────────────────────────────┬─────────────────────────────┤
│ 1. INBOX                       │ 2. PRODUCTIONS                           │ 3. INVESTIGATIONS           │
│ Action-oriented work queue for │ Production digital twins, version trees, │ Real-time autonomous agent  │
│ triage, blockers, & reviewer   │ timeline conformers, baseline vs target  │ runs, multi-hop search DAGs,│
│ escalations.                   │ semantic delta logs.                     │ tool traces & spend meters. │
├────────────────────────────────┼──────────────────────────────────────────┼─────────────────────────────┤
│ 4. EVIDENCE                    │ 5. DECISIONS                             │ 6. CONNECTIONS & POLICY     │
│ Bifurcated public registry     │ Sovereign counsel ledger, 4D legal       │ Organization settings, GCS  │
│ snapshots vs private contract  │ briefings, attestation checkpoints &     │ Eventarc watchers, API keys,│
│ clauses with authority scores. │ supersession audit trail.                │ spend caps & E&O profiles.  │
└────────────────────────────────┴──────────────────────────────────────────┴─────────────────────────────┘
```

---

### 2.1 Destination 1: Inbox (Triage, Urgency Routing & Action Queue)

#### 2.1.1 Purpose & Role
The **Inbox** is the high-velocity operational cockpit for the production legal office. It eliminates fragmented email chains, scattered post-it notes, and disconnected Slack threads by consolidating all clearance events requiring human intervention into a prioritized, SLA-tracked action queue.

#### 2.1.2 Personas & Primary Workflows
- **Clearance Coordinator / Legal Analyst**: Reviews newly extracted claims from raw script drops, assigns unassigned tasks to specialist attorneys (e.g., Music Counsel vs. Trademark Counsel), and triages pending clarification requests.
- **Lead Clearance Counsel**: Focuses strictly on P0 and P1 review escalations, reviewing 4-dimensional briefings and issuing binding attestations.
- **Post-Production Supervisor**: Monitors clearance velocity, tracks delivery blockers scheduled within 72 hours of editorial turnovers, and uploads requested contracts.

#### 2.1.3 Urgency Tiers & SLA Engine
Items in the Inbox are automatically classified by an automated urgency engine:
- **P0: Delivery Blocker (Critical)**: Production shooting or distributor lab delivery scheduled within 72 hours with unresolved clearance exceptions or unvetted focal assets. *SLA: 4 hours*.
- **P1: Reopened Decision (High)**: A previously approved baseline claim invalidated due to creative drift (e.g., background set piece moved to focal dialogue) or newly discovered adverse catalog ownership. *SLA: 12 hours*.
- **P2: Clarification Pending (Medium)**: Autonomous investigation blocked awaiting an internal production artifact (e.g., missing composer work-for-hire contract, art department purchase receipt, or actor crowd release). *SLA: 24 hours*.
- **P3: Routine Intake Review (Standard)**: Newly parsed incidental assets from early drafts with supporting public registry corroboration ready for batch clearance. *SLA: 72 hours*.

#### 2.1.4 UX Architecture & Interactive Capabilities
- **High-Density Keyboard Navigation**: Full `j`/`k` keyboard selection, allowing counsel to triage dozens of claims per hour without pointer fatigue.
- **Split-Pane Quick Peek**: Selecting any item opens a slide-over drawer showing the script context delta, the external search excerpt, and immediate action buttons.
- **Batch Reassignment & Escalation**: Ability to reassign multiple claims to specific attorneys, export blocker summaries, or snooze an item with mandatory written justification.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ INBOX: Clearance Blockers & Action Queue                                         [Filter: All Titles ▾]│
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Active Queue: [ 2 P0 Blockers ]  [ 5 P1 Reopened ]  [ 3 Clarifications ]  [ Avg Triage: 3.4h ]         │
├────┬───────┬────────────────────┬─────────────────────────────┬──────────────────┬──────────┬──────────┤
│PRI │ LEVEL │ PRODUCTION         │ ASSET LINEAGE & TRIGGER     │ ASSIGNED TO      │ AGE/DUE  │ ACTION   │
├────┼───────┼────────────────────┼─────────────────────────────┼──────────────────┼──────────┼──────────┤
│[!] │ P0    │ Shadows Over B'way │ music_cue_midnight_serenade │ Sarah Jenkins    │ 3h / 18h │ Review ➔ │
│    │ CRIT  │ Ep 102 Cut v8      │ Worldwide Sync Dispute      │ Lead Counsel     │ SHOOTING │          │
├────┼───────┼────────────────────┼─────────────────────────────┼──────────────────┼──────────┼──────────┤
│[!] │ P1    │ Shadows Over B'way │ poster_noir_detective_mag   │ Sarah Jenkins    │ 8h / 36h │ Diff ➔   │
│    │ HIGH  │ Ep 102 Cut v8      │ Framing Drift (2s ➔ 14s)    │ Lead Counsel     │          │          │
├────┼───────┼────────────────────┼─────────────────────────────┼──────────────────┼──────────┼──────────┤
│[?] │ P2    │ Apex Racing 2026   │ prop_energy_drink_canister  │ Marcus Vance     │ 22h / 48h│ Ping AD  │
│    │ MED   │ Feature Cut v3     │ Missing Art Dept Receipt    │ Clearance Coord. │          │          │
└────┴───────┴────────────────────┴─────────────────────────────┴──────────────────┴──────────┴──────────┘
```

---

### 2.2 Destination 2: Productions (Registry, Version Histories & Delta Logs)

#### 2.2.1 Purpose & Role
The **Productions** destination acts as the central registry for all production digital twins across the studio portfolio. It stores complete version histories, maintains immutable baseline references ($V_{\text{baseline}}$), computes semantic and structural deltas across revisions, and exposes cloud storage connector health.

#### 2.2.2 Version Lineage DAG & Revision Tree
Cinematic projects branch and converge across departments (screenplay revisions, storyboards, conform edits, VFX cuts). Productions models every milestone as an immutable node in a Directed Acyclic Graph (DAG):
- **Version Metadata**: Version ID, parent version pointers, content SHA-256 digests, format types (Screenplay PDF, Final Draft FDX, DaVinci Resolve EDL, Avid AAF, Final Cut Pro XML).
- **Revision Coloring**: Automatically identifies industry-standard draft revisions (White, Blue, Pink, Yellow, Green, Goldenrod, Salmon, Cherry) based on header markers and revision metadata.
- **Branch Comparison**: Arbitrary version-to-version diffing ($V_{\text{base}}$ vs $V_{\text{target}}$), enabling counsel to compare Shooting Script v8 directly against Writer's First Draft v1 or Editorial Cut v12.

#### 2.2.3 Semantic Delta Logs
The delta engine categorizes changes between versions into four distinct categories:
1. **Added Assets**: Newly introduced dialogue, background props, music cues, or character names.
2. **Removed Assets**: Dropped scenes or cut elements. Clearance liability is released and archived.
3. **Material Prominence Alterations**: Unchanged asset identity, but significant shift in camera focal length, shot duration, dialogue interaction, or narrative defamation.
4. **Unchanged Set Dressing**: Mathematically identical context hash; eligible for automated fail-closed carry-forward.

```
Version DAG Architecture:
[Draft v1 (White)] ──► [Draft v2 (Blue)] ──► [Draft v7 LOCKED BASELINE]
                                                      │
                       ┌──────────────────────────────┴─────────────────────────────┐
                       ▼                                                            ▼
            [Revision v8 (Pink)]                                        [Alt-Ending Shooting Cut]
            - Hash: f9e8d7c6b5a4...                                      - Hash: 3c8b1a99f012...
            - 10 Unchanged / 2 Reopened                                  - Independent Lineage Branch
```

---

### 2.3 Destination 3: Investigations (Autonomous Research & Multi-Hop Telemetry)

#### 2.3.1 Purpose & Role
The **Investigations** destination provides complete, transparent observability into the autonomous agent research engine. It visualizes how agents decompose clearance goals, formulate registry queries, traverse external web graphs via the **Parallel Search API**, enforce budget constraints, and reconcile raw evidence into legal stances.

#### 2.3.2 Autonomous Goal Decomposition
When an asset enters `STALE` status, the agent planner dynamically decomposes the clearance objective into a structured execution tree:
- *Example (Music Cue)*:
  - Sub-Goal 1: Identify composition copyright owner and performance rights organization (ASCAP / BMI / SESAC / PRS).
  - Sub-Goal 2: Identify master recording owner (Record Label / Master Rights Holder).
  - Sub-Goal 3: Detect underlying samples or interpolations requiring chain-of-title verification.
- *Example (Fine Art / Poster)*:
  - Sub-Goal 1: Determine initial publication date and country of origin.
  - Sub-Goal 2: Query Library of Congress records for statutory 28-year renewal filings (works published pre-1978 under 1909 Copyright Act).
  - Sub-Goal 3: Evaluate artist estate and Artists Rights Society (ARS) representation.

#### 2.3.3 Multi-Hop Parallel Search Traces
Rather than executing single keyword queries, the agent executes bounded multi-hop discovery:
1. **Hop 1 (Registry Discovery)**: Query authoritative domain (`site:cocatalog.loc.gov` or `site:ascap.com/repertory`).
2. **Hop 2 (Lead Traversal)**: If the registry indicates a corporate catalog acquisition (e.g., *"Catalog acquired by Vanguard Media Holdings in 2026"*), the agent autonomously parses the lead and issues a secondary query targeting the acquiring entity's active rights roster.
3. **Hop 3 (Dispute Corroboration)**: If conflicting claims appear in trade press or legal filings (e.g., *Variety* or *Justia*), a third query isolates litigation history.

#### 2.3.4 Bounded Retries, Spend Governors & Circuit Breakers
- **Hard Query Budget**: Max 3 external queries per claim by default, configurable up to 5 for complex claims.
- **Run Cost Governor**: Hard financial cap (e.g., $5.00 USD per investigation run). If the spend governor is reached, the run transitions to `waiting_for_budget` rather than continuing to consume API credits.
- **Circuit Breaker**: If external search endpoints return consecutive 5xx or 429 rate limits, the system trips to `OPEN`, switches to cached registry mirrors or offline fixtures, flags evidence as `INSUFFICIENT`, and alerts counsel without pipeline crash.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ INVESTIGATIONS: Live Run #inv_9921 — Shadows Over Broadway (v7 ➔ v8)               [State: COMPLETED]  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Spend Telemetry: [API Calls: 2 / 10]  [Cost: $0.16 / $5.00 Cap]  [Latency: 1,420ms]  [Worker: pod-04]  │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ RUNTIME EXECUTION TRACE & TELEMETRY STREAM                                                             │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [14:20:01.012] [ORCHESTRATOR] Evaluated 12 claims against Policy E&O-2026.1. Invariant: 10 Carried / 2 Stale │
│ [14:20:01.240] [TOOL: Parallel Search] Target: `poster_noir_detective_magazine`                        │
│                Query: "Crime Detective Magazine 1946 Shadows Over Broadway copyright renewal"          │
│                Status: HTTP 200 | Latency: 142ms | Provider Call ID: `call_par_loc_8812`               │
│                Source: cocatalog.loc.gov (Library of Congress)                                         │
│                Snippet: "Registration Class B, No. 44102, Oct 1946. Renewal search: ZERO renewals filed"│
│                Stance Verdict: [SUPPORTING: Public Domain Expiration Confirmed]                        │
│ [14:20:01.510] [TOOL: Parallel Search] Target: `music_cue_midnight_serenade`                           │
│                Query: "Midnight Serenade jazz sync rights copyright owner 2026 Vanguard"               │
│                Status: HTTP 200 | Latency: 184ms | Provider Call ID: `call_par_ascap_9941`             │
│                Source: ascap.com / billboard.com                                                       │
│                Snippet: "Exclusive worldwide sync rights assigned to Vanguard Media Holdings LLC 2026" │
│                Stance Verdict: [CONTRADICTORY: Active Commercial Rightsholder Dispute]                 │
│ [14:20:02.100] [GATEWAY] Synthesized 4D Legal Briefings. Run ready for counsel adjudication.           │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.4 Destination 4: Evidence (Bifurcated Repository & Source Inspector)

#### 2.4.1 Purpose & Role
The **Evidence** destination is the tamper-evident archive of all corroborating records supporting clearance decisions. To protect attorney-client privilege and commercial confidentiality, Evidence enforces a **strict architectural bifurcation** between public open-web findings and confidential private production contracts.

#### 2.4.2 Repository A: Public Web & Registry Snapshots
Houses attributable third-party public records retrieved at runtime:
- **Registry Sources**: Library of Congress Copyright Catalog (`cocatalog.loc.gov`), USPTO Trademark Search (TESS), ASCAP ACE Repertory, BMI Songview, UK Intellectual Property Office (UKIPO), WIPO Global Brand Database.
- **Cryptographic Provenance**: Every web snapshot stores the full request payload SHA-256 hash, raw response payload SHA-256 hash, HTTP status code, provider call ID, retrieval timestamp, and live-cached binary mirror.
- **Evidence Stance Scoring**:
  - `SUPPORTING`: Conclusively proves absence of active copyright/trademark (e.g., lapsed pre-1978 renewal) or nominative fair use.
  - `CONTRADICTORY`: Proves active, adverse commercial ownership or ungranted third-party rights.
  - `INFORMATIONAL`: Contextual data (e.g., general Wikipedia biography or discography) without chain-of-title authority.
  - `INSUFFICIENT`: Ambiguous search hits requiring deeper manual archival discovery.

#### 2.4.3 Repository B: Private Production Contracts & Permissions
Houses executed agreements uploaded by production legal:
- **Contract Categories**: Composer Work-for-Hire Agreements, Master Sync Licenses, Talent Appearance Releases, Location Releases, Option Purchase Agreements (OPA), Stock Footage Pack Deliveries.
- **Clause Extraction & Anchors**: High-precision extraction of Licensor, Licensee, Permitted Media Scope (*"All media now known or hereafter devised"*), Permitted Territory (*"Worldwide"*), Expiration Term, Warranty Clauses, and PDF page/paragraph anchors.
- **Confidentiality Tiers**: Role-based access control isolating confidential financial terms (producer eyes only) from clearance scopes (underwriter auditable).

#### 2.4.4 Source Authority Scoring & Expiry Engine
- **Authority Weighting**:
  - LOC / USPTO / Government Registries: `1.00`
  - ASCAP / BMI / Performing Rights Societies: `0.95`
  - Verified Corporate Trade Press (Variety / Hollywood Reporter / Billboard): `0.70`
  - Unverified Web Pages / Fan Wikis: `0.25`
- **Contract Expiry Watcher**: Monitors contract expiration dates against projected distribution windows, triggering automated alerts 60 days before distribution rights lapse in key territories.

---

### 2.5 Destination 5: Decisions (Counsel Clearance Ledger & Checkpoint Gate)

#### 2.5.1 Purpose & Role
The **Decisions** destination is the sovereign legal terminal for Lead Clearance Counsel. It operationalizes the core principle of **Bounded Autonomy**: artificial intelligence and automated search engines propose; licensed human counsel disposes.

#### 2.5.2 Four-Dimensional Clearance Briefings
When counsel inspects any invalidated or pending item, the interface presents a structured 4-dimensional analysis synthesized from the creative delta, evidence repository, and statutory rules:
1. **Dimension 1 (Creative Context Shift)**: Explains exact prominence changes, camera framing drift, timecode duration shifts, and actor dialogue interactions.
2. **Dimension 2 (External Evidence Finding)**: Highlights primary source registry excerpts, ASCAP/LOC catalog records, and Parallel Search stance classifications.
3. **Dimension 3 (Private Contract Scope)**: Displays active agreements, license term validity, and territory coverage (or explicitly highlights contractual absence).
4. **Dimension 4 (Statutory Policy Reason)**: Identifies statutory copyright and trademark doctrine (e.g., *de minimis* non-infringement under 17 U.S.C. § 107; public domain lapse under 17 U.S.C. § 304; trademark exhaustion; or catastrophic exposure under § 504(c)).

#### 2.5.3 The Four Sovereign Counsel Actions
Counsel has four non-delegable actions for each adjudicated claim:
1. **Affirmative Re-Attestation (`re_attest`)**: Counsel affirms that the creative delta or public registry proof satisfies clearance standards. The decision is committed as `APPROVED`.
2. **Approval with Condition (`approve_with_condition`)**: Counsel clears the asset subject to strict operational conditions (e.g., *"Clearance conditioned on end-credit screen attribution to Library of Congress"*, or *"Sound editor must lower dialogue bleed below -24dB"*).
3. **Underwriting Exception (`exception`)**: Counsel acknowledges an unresolved third-party claim, blocks the asset from production warranty, and lists it on the **Draft Clearance Exceptions Schedule for counsel and underwriter review**.
4. **Reject with Reinvestigation Directive (`reject_and_reinvestigate`)**: Counsel rejects the agent's research as insufficient and enters a binding directive (e.g., *"Check ASCAP co-publisher splits for mechanical license exceptions before classifying as disputed"*), automatically restarting the investigation run.

#### 2.5.4 Tamper-Evident Supersession Ledger
Clearance decisions are never overwritten or mutated. Every adjudication creates an immutable `SupersessionEvent` linked into a cryptographic hash chain:
$$H_n = \text{SHA256}\left(H_{n-1} \mathbin{\Vert} \text{DecisionID} \mathbin{\Vert} \text{Action} \mathbin{\Vert} \text{ReviewerBarID} \mathbin{\Vert} \text{Rationale} \mathbin{\Vert} \text{Timestamp}\right)$$
This gives completion bond guarantors and E&O carriers an unbroken, verifiable audit trail of who approved what, when, and on what legal basis.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ DECISIONS: Sovereign Counsel Checkpoint Gate (Item 12 of 12)                      [Reviewer: S. Jenkins]│
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ASSET: `music_cue_midnight_serenade` | Type: Music Sync | Scene: SC 18 (00:18:24) | Status: [STALE]   │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ FOUR-DIMENSIONAL LEGAL BRIEFING                                                                        │
│ 1. Creative Context: 20s background jazz trumpet cue; staging unchanged between Cut v7 and Cut v8.    │
│ 2. External Evidence: Parallel Search identified 2026 catalog acquisition by Vanguard Media Holdings.   │
│ 3. Private Fact:     Production cue sheet references 1998 archival master; term expired July 2026.     │
│ 4. Statutory Policy: CRITICAL LIABILITY — Distribution without sync license exposes studio to         │
│                      statutory damages up to $150,000 under 17 U.S.C. § 504(c).                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ COUNSEL ADJUDICATION DISPOSITION                                                                       │
│ Statutory Basis: [ Express License Exclusion / Underwriter Exception Rider ▾ ]                         │
│ Mandatory Counsel Rationale:                                                                           │
│ ┌────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Listed as Draft Clearance Exceptions Schedule Exception Item 1. Post-production coordinator must   │ │
│ │ either obtain Vanguard master sync quotation or replace audio cue prior to final mix lock.         │ │
│ └────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│ [ ✓ RE-ATTEST ]  [ ⚠️ APPROVE W/ CONDITION ]  [ 🚫 FLAG AS EXCEPTION ]  [ 🔄 REJECT & REINVESTIGATE ]   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.6 Destination 6: Connections & Policy (Governance, Bucket Watchers & Spend)

#### 2.6.1 Purpose & Role
The **Connections & Policy** destination governs organization-level configurations, automated storage watchers, API credential security, autonomous spend governors, and studio policy inheritance.

#### 2.6.2 Cloud Storage Watchers & Connectors
Provides continuous, background synchronization with studio file systems:
- **Google Cloud Storage (GCS)**: Listens for `google.storage.object.finalize` events via Cloud Eventarc. Automatically detects new screenplays or timeline files deposited into `gs://studio-intake-{org}/`.
- **Dropbox Business**: Long-polling and webhook listener on designated project folders (`/Productions/{Title}/Scripts/`).
- **Google Drive**: Push notifications via Drive API v3 change watchers on designated shared drives.
- **Content Deduplication**: Ingested files are immediately hashed (SHA-256). Identical files bypass processing immediately, spending zero compute.

#### 2.6.3 Enterprise Spend Governors & Rate Limits
Protects studios against runaway autonomous agent loops:
- **Max Cost Per Investigation Run**: Hard cap (default: $5.00 USD).
- **Max Monthly Organization Budget**: Global spend limit across all active productions.
- **Max Parallel Search Calls Per Claim**: Strict bound (default: 3 queries).
- **Graceful Degradation Policy**: Configures behavior when budget limits are reached (`pause_and_notify`, `switch_to_offline_cache`, or `fail_closed`).

#### 2.6.4 Studio Policy Inheritance & Underwriter Profiles
Enables enterprise studios to define clearance rules hierarchically:
- **Parent Studio Level** (e.g., *Universal Pictures* / *Warner Bros. Discovery*): Global default insurance carrier (e.g., *Gallagher / Front Row*), standard deductible ($50,000), mandatory bar number requirement for all counsel sign-offs.
- **Production Series Level** (e.g., *Prestige Drama Season 3*): Inherited defaults with custom territory scopes (*Worldwide All-Media Perpetual*).
- **Individual Episode Level**: Scene-specific fair-use thresholds.

---

## 3. Real Input-Driven Clearance Lifecycle (End-to-End)

The complete end-to-end operational lifecycle illustrates how an arbitrary production file progresses from initial background ingestion through autonomous investigation, human-in-the-loop clarification, counsel adjudication, and export of the final underwriting schedule.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   END-TO-END CLEARANCE LIFECYCLE                                       │
│                                                                                                        │
│  [1. INGEST] ──────► [2. PARSE] ──────► [3. BASELINE] ──────► [4. REVISION] ──────► [5. SEMANTIC DELTA]│
│  Storage Drop        Element Intake     Ingest Baseline        Script Revision       Gemini 2.5 Flash   │
│  (GCS/Dropbox)       N Claims Extracted Mixed States (v0)      Drop (v1)             Prominence Diffs   │
│                                                                                            │           │
│  [10. EXPORT] ◄───── [9. ADJUDICATE] ◄── [8. CLARIFY] ◄────── [7. INVESTIGATE] ◄──── [6. INVALIDATE]   │
│  Draft Exceptions    Counsel Sign-Off   Missing Fact Loop     Parallel Search       Pure Python Engine │
│  Schedule Export     Approve/Condition  Assign Coordinator    Bounded Multi-Hop     Fail-Closed Stale  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Step-by-Step Lifecycle Specification

#### Step 1: Baseline Draft / Timeline Ingestion
- **Trigger**: A production coordinator drops a locked screenplay PDF or DaVinci Resolve EDL into the watched cloud storage bucket (`gs://studio-intake-prestige/shadows_v7_locked.pdf`).
- **Processing**: Eventarc fires an authenticated webhook to `/api/v1/ingest/gcs-event`. The Ingestion Gateway validates the HMAC signature, streams the file into the Encrypted Asset Vault, and computes the master content SHA-256 digest.

#### Step 2: Autonomous Element Extraction & Baseline Parsing
- **Execution**: The Intake Agent parses the document structure.
- **Output**: Identifies $N$ rights-bearing creative uses across the timeline (e.g., 42 music cues, 18 artwork items, 24 brand props, 12 talent likenesses, 6 architectural locations).
- **Source Location & Extraction Provenance**: Captures exact source locations (page number, line number, character span offsets, and scene heading), extractor model/prompt version (`extraction_version`), extraction uncertainty score (`extraction_uncertainty`), and any reviewer manual corrections.
- **Fingerprinting**: For each creative use, the agent assigns a `stable_lineage_key` and computes a 16-character SHA-256 context hash:
  $$\text{context\_hash} = \text{SHA256}\left(\text{context} \mathbin{\Vert} \text{"::"} \mathbin{\Vert} \text{duration\_or\_prominence}\right)[0:16]$$

#### Step 3: Initial Counsel Clearance Baseline & Mixed Starting States
- **Flexible Baseline Ingestion**: A production does not need a perfectly cleared baseline to use Lienmark. The platform supports mixed starting states across imported or reviewed claims:
  - `APPROVED`: Prior counsel clearance on file with valid chain-of-title or license grant.
  - `CONDITIONAL`: Approved subject to specific operational deliverables (e.g., end-credit screen attribution, volume threshold, or territory holdback).
  - `UNRESOLVED`: Identified rights-bearing asset with outstanding investigation or pending negotiations.
  - `REJECTED`: Clearance denied or asset explicitly prohibited by legal counsel.
  - `UNKNOWN`: Newly extracted asset with no recorded historical legal determination.
- **Import & Adjudication**: Productions may import actual prior decisions from legacy clearance spreadsheets, paper binders, and legal memoranda, or obtain explicit initial review from Lead Clearance Counsel.
- **Version Binding**: Each initial baseline record is anchored to $V_{\text{baseline}}$ along with its recorded status, source evidence, and counsel attribution. Downstream change control operates seamlessly against this realistic, heterogeneous baseline.

#### Step 4: Revision Introduction (Shooting Revision Drop)
- **Trigger**: Two weeks later, the director issues a revised shooting script (*Pink Revision v8*), modifying scenes, altering dialogue, and changing prop placements.
- **Ingestion**: The file lands in the watched bucket. The system registers $V_{\text{target}}$ as a child node of $V_{\text{baseline}}$ in the production version tree.

#### Step 5: Semantic Delta Detection & Comparison Certainty
- **Execution**: The system dispatches **Gemini 2.5 Flash** in structured JSON mode (`DeltaAnalysisResult`) to evaluate narrative text differences between baseline and target spans.
- **Analysis**: The model detects qualitative framing shifts (e.g., background blur vs focal dialogue, character interaction, pejorative or defamatory dialogue) and produces structured materiality metrics (`ChangeKind: MATERIALLY_MODIFIED`, `Materiality: HIGH`).
- **Distinguishing Comparison Certainty**: The delta engine strictly differentiates between:
  - `UNCHANGED`: **"No relevant change detected"** across comparable inputs with verified extraction integrity.
  - `UNCERTAIN` / `INCOMPARABLE`: **"We could not reliably compare these inputs"** (due to extraction uncertainty, OCR degradation, structural formatting shifts, or missing contextual spans).

#### Step 6: Deterministic Fail-Closed Invalidation
- **Execution**: The deterministic Invalidation Engine (`invalidation_engine.py`) executes in pure Python without LLM non-determinism.
- **State Machine Evaluation**:
  - Unmodified claims with identical context hashes and non-adverse evidence evaluate to `CARRIED_FORWARD` (preserving prior authorized status within recorded scope).
  - Claims with modified context hashes evaluate to `STALE` (`CREATIVE_CONTEXT_ALTERED`).
  - Claims with unmapped lineage or missing data evaluate to `STALE` (`FAIL_CLOSED_MISSING_DELTA`).
  - Claims with adverse external evidence evaluate to `STALE` (`EXTERNAL_EVIDENCE_SHIFT`).
  - Claims where inputs could not be reliably compared evaluate to `STALE` (`EXTRACTION_UNCERTAIN_FAIL_CLOSED`).

#### Step 7: Targeted Parallel Live Investigation
- **Execution**: The Research Agent initiates an investigation run exclusively for claims in `STALE` status.
- **Parallel Search Dispatch**: Formulates domain-steered queries to the **Parallel Search API v1**, retrieving live registry evidence from Library of Congress, USPTO, and ASCAP. Captures source URLs, attributable excerpts, provider call IDs, and latency metrics.

#### Step 8: Clarification Loop (Human-in-the-Loop Wait State)
- **Condition**: If an investigation reveals that clearance hinges on a private fact (e.g., *"Did the art department purchase the painting from a student artist or build it in-house?"*), the agent halts automated research.
- **Execution**: The agent generates a `ClarificationRequest` linked to the exact claim and revision, assigns it to the Clearance Coordinator, and transitions the investigation to `waiting_for_information`.
- **Resolution**: The coordinator uploads the artist purchase receipt; the investigation automatically wakes up, ingests the document, and resumes.

#### Step 9: Sovereign Counsel Adjudication Gate
- **Execution**: Counsel inspects the `ReviewQueue` in the Decisions workspace.
- **Briefing Review**: Counsel reviews the 4D briefing: creative change, external evidence, private contract scope, and statutory liability.
- **Action**: Counsel issues binding dispositions:
  - Clears public domain artwork via `RE_ATTEST` with public domain citation.
  - Flags unresolved music sync dispute via `FLAG_EXCEPTION` with directive to replace track.
- **Ledger Commit**: Generates tamper-evident `SupersessionEvent` records chained to the cryptographic ledger.

#### Step 10: Draft Clearance Exceptions Schedule for Counsel and Underwriter Review Export
- **Generation**: The system compiles the underwriting review package:
  - Total Claims Count ($N$)
  - Carried-Forward Count (unchanged claims carried at $0.00 spend)
  - Re-Attested Count (reopened claims verified and approved)
  - Unresolved Exceptions Count (items scheduled as underwriter policy exclusions)
- **Deliverable**: Emits the **Draft Clearance Exceptions Schedule for counsel and underwriter review** containing carrier warranty headers, non-binding underwriter advisory notices, and complete cryptographic hash audit proofs.

---

## 4. Removing Fixture Assumptions (Generalized Arbitrary-$N$ Engine)

A critical architectural mandate of this PRD is the **total elimination of hardcoded fixture assumptions**. Early prototype demonstrations frequently rely on fixed $10+1+1$ fixtures (10 carried forward, 1 creative drift item, 1 evidence drift item) or hardcoded asset rules (e.g., hardcoded logic assuming Item 11 is a poster that clears, or Item 12 is music that fails). Lienmark's production architecture is strictly input-driven, generalized, and scale-invariant.

### 4.1 Dismantling Hardcoded $10+1+1$ Constraints
1. **Support for Arbitrary $N$ Claims**:
   - The engine operates across arbitrary claim counts: $N \in [1, 1000+]$. A 5-minute animated short with 4 claims or a 10-episode historical drama with 450 claims execute under the exact same state machine logic.
   - The number of carried forward vs. reopened claims is purely a function of actual detected creative and factual deltas:
     $$\text{Reopened Claims} = \{c \in C \mid \text{Delta}(c) \neq \emptyset \lor \text{Stance}(c) \in \{\text{CONTRADICTORY}, \text{INSUFFICIENT}\}\}$$
2. **Dynamic Asset Categories**:
   - Assets are not restricted to predefined enumerations. The system dynamically categorizes any rights-bearing element: `music_composition`, `music_master`, `artwork_fine`, `artwork_graffiti`, `trademark_logo`, `trademark_packaging`, `prop_weapon`, `architecture_facade`, `talent_likeness`, `talent_voice`, `synthetic_genai`, `dialogue_quote`, `documentary_footage`.

### 4.2 Eliminating Fixed Asset Outcomes & Contractual Evidence Boundaries
- **No Pre-Selected Legal Conclusions**:
  - The system **never assumes** an artwork clears as public domain. If an artwork published in 1946 had a valid copyright renewal filed in 1974, the Parallel Search API extracts the active renewal registration (`RE-14-892`), classifying the evidence as `CONTRADICTORY` and driving counsel toward an `EXCEPTION` or licensing requirement.
  - The system **never assumes** a music track fails, nor can newly discovered contracts silently manufacture approval. If production legal uploads an executed Worldwide Master Synchronization License from the new copyright owner, this newly discovered agreement **does not automatically produce `CARRIED_FORWARD`**. Instead, new evidence updates the investigation record and generates a proposed resolution for counsel review. Carry-forward must preserve an existing authorized decision within its recorded scope; a newly interpreted agreement cannot silently create approval without explicit counsel adjudication.
- **Bidirectional Prominence Drift**:
  - Prominence drift can escalate *or* de-escalate. If a featured 30-second dialogue scene featuring a luxury watch is trimmed into a 1-second background blur, the system logs the de-escalation delta, enabling counsel to transition the asset from a paid commercial license requirement into a standard *de minimis* fair-use clearance.

### 4.3 Handling Arbitrary Edits & Dynamic Script Mutations
- **Additions**: Brand new assets appearing in $V_{\text{target}}$ have no predecessor lineage key in $V_{\text{base}}$. They receive state `NEW`, are routed immediately to the Inbox as P3 intake tasks, and are scheduled for full primary investigation.
- **Deletions**: Assets present in $V_{\text{base}}$ but omitted in $V_{\text{target}}$ transition to state `REMOVED`. Their clearance obligations are archived; they are excluded from the target Draft Clearance Exceptions Schedule for counsel and underwriter review, preventing unnecessary licensing expenditure.
- **Prominence Shifts without Text Changes**: Editorial timeline conforms (EDLs) often alter shot duration without script text changes. The EDL conformer updates duration metrics, detecting when an incidental audio track extends across scene boundaries.
- **Secondary Claim Discovery**: When Parallel Search explores a primary lead, it can uncover nested secondary IP (e.g., discovering that an uncredited musical cue contains a prominent sample of a 1970s funk record). The agent dynamically spawns a child claim linked to the parent lineage key.

### 4.4 The Deterministic Boundary: Comparison Certainty vs. Extraction Uncertainty
A fundamental design invariant of Lienmark is that **a deterministic dependency graph consistently propagates changes across recorded dependencies, but cannot guarantee that an AI extractor identified every asset or dependency correctly**.

To operationalize this boundary rigorously:
1. **Full Extraction Provenance**: Every `CreativeUse` stores its exact source location (page, line, character offsets, scene heading), extraction engine version (`extraction_version`), model extraction uncertainty (`extraction_uncertainty`), and any reviewer corrections.
2. **Strict Invariant**: **"No relevant change detected"** must remain strictly distinguishable from **"We could not reliably compare these inputs."**
   - When text or formatting shifts prevent reliable semantic or context alignment, the engine marks the change kind as `UNCERTAIN` or `INCOMPARABLE`.
   - Incomparable or uncertain comparisons strictly fail closed to `STALE` with reason code `EXTRACTION_UNCERTAIN_FAIL_CLOSED`, ensuring no unverified creative shift is swept into an automated carry-forward.

---

## 5. Core Data Contracts & Schemas

The domain models enforce strict typing, validation, and serialization. They are implemented in Python via **Pydantic v2** and mirrored in TypeScript for the frontend command center.

### 5.1 Domain Model Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     LIENMARK DOMAIN GRAPH                                        │
├────────────────────┐                 1:N                 ┌───────────────────────────────────────┤
│     Production     │ ──────────────────────────────────► │           ProductionVersion           │
└────────────────────┘                                     └───────────────────────────────────────┘
          │ 1:N                                                                │ 1:N
          ▼                                                                    ▼
┌────────────────────┐ discovery checkpoint                ┌───────────────────────────────────────┤
│     Connection     │ ◄────────────────────────────────── │              CreativeUse              │
│(Cursor/Checkpoint) │                                     │(Location, Uncertainty, Version, Edits)│
└────────────────────┘                                     └───────────────────────────────────────┘
          │                                                                    │
          │ Evaluates Delta across versions                                    │ Lineage Anchor
          ▼                                                                    ▼
┌────────────────────┐                                     ┌───────────────────────────────────────┤
│   CreativeDelta    │ ──────────────────────────────────► │            CounselDecision            │
│ (Unchanged/Uncert) │                                     │(Bound to Policy & Evidence Snapshots) │
└────────────────────┘                                     └───────────────────────────────────────┘
          │ Evaluated by InvalidationEngine                                    │ Adjudicates
          ▼                                                                    ▼
┌────────────────────┐                                     ┌───────────────────────────────────────┤
│ InvalidationRecord │                                     │           SupersessionEvent           │
└────────────────────┘                                     │       (SHA-256 Hash Chained)          │
          │ Reopened claims trigger Run & Plan                     └───────────────────────────────────────┘
          ▼                                                                    │
┌────────────────────┐ 1:N                                                     ▼
│  InvestigationRun  │ ──────► ┌────────────────────┐      ┌───────────────────────────────────────┤
│ (Source Revision)  │         │ InvestigationPlan  │      │       Draft Clearance Exceptions      │
└────────────────────┘         │(Results & Budget)  │      │       Schedule (Counsel/Underwriter)  │
                               └────────────────────┘      └───────────────────────────────────────┘
                                         │
                                         ▼
                               ┌────────────────────┐ missing fact ┌───────────────────────────────┤
                               │    EvidenceItem    │ ───────────► │      ClarificationRequest     │
                               │(Public & Contracts)│              │  (Linked to Claim & Revision) │
                               └────────────────────┘              └───────────────────────────────┘
```

---

### 5.2 Schema Specifications

#### 5.2.1 Production (`Production`)
The root entity representing an enterprise cinematic, television, or gaming project.
```python
class Production(BaseModel):
    production_id: str = Field(..., description="Unique production identifier (e.g., 'proj_shadows_broadway')")
    organization_id: str = Field(..., description="Multi-tenant studio / company ID")
    title: str = Field(..., description="Working or official title of the production")
    production_type: str = Field(..., description="feature_film | episodic_series | documentary | commercial")
    primary_carrier: str = Field(default="Gallagher / Front Row", description="Designated E&O insurance carrier")
    policy_binder_id: str = Field(default="E&O-2026.1-DEVPOST", description="Underwriting policy reference number")
    self_insured_retention_usd: float = Field(default=50000.0, description="E&O deductible / SIR threshold in USD")
    active_baseline_version_id: Optional[str] = Field(None, description="Current certified baseline version ID")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### 5.2.2 Connection (`Connection`) — Persisted Concept 1
A persistent cloud storage or digital intake watcher maintaining an immutable discovery cursor/checkpoint to prevent missed revisions or duplicate ingestion loops.
```python
class ConnectionProvider(str, Enum):
    GCS = "gcs"
    DROPBOX = "dropbox"
    GOOGLE_DRIVE = "google_drive"
    LOCAL_FOLDER = "local_folder"
    EVENTARC_WEBHOOK = "eventarc_webhook"

class Connection(BaseModel):
    connection_id: str = Field(..., description="Unique connector identifier (e.g., 'conn_gcs_prestige_01')")
    organization_id: str = Field(..., description="Multi-tenant studio / company ID")
    production_id: Optional[str] = Field(None, description="Optional production scope identifier")
    provider: ConnectionProvider = Field(..., description="Cloud intake provider type")
    target_uri_or_path: str = Field(..., description="Monitored bucket URI, folder path, or webhook target")
    discovery_cursor: Optional[str] = Field(None, description="Persistent discovery cursor / checkpoint token (e.g., GCS generation ID, Dropbox cursor, Drive change token)")
    checkpoint_timestamp: Optional[str] = Field(None, description="UTC timestamp of last successfully processed checkpoint")
    last_sync_at: Optional[str] = Field(None, description="UTC timestamp of most recent poll or webhook notification")
    status: str = Field(default="active", description="active | paused | error | degraded")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific credentials and configuration")
```

#### 5.2.3 Version (`ProductionVersion`)
An immutable milestone representing a specific script draft, edit decision list, or conformed picture cut.
```python
class ProductionVersion(BaseModel):
    version_id: str = Field(..., description="Unique version identifier (e.g., 'v7', 'v8')")
    production_id: str = Field(..., description="Associated production ID")
    parent_version_id: Optional[str] = Field(None, description="Direct predecessor version in lineage DAG")
    label: str = Field(..., description="Human-readable milestone label (e.g., 'Pink Revision v8 - Locked')")
    revision_color: Optional[str] = Field(None, description="White | Blue | Pink | Yellow | Green | Goldenrod | Salmon")
    content_hash: str = Field(..., description="SHA-256 digest of normalized screenplay or timeline text")
    source_type: str = Field(default="screenplay", description="screenplay | edl | aaf | xml | video_cut")
    storage_vault_uri: str = Field(..., description="Permanent CMEK-encrypted Cloud Storage URI")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by_user_id: Optional[str] = None
```

#### 5.2.4 Creative Use (`CreativeUse`) — Source Locations & Extraction Uncertainty
A discrete rights-bearing asset occurrence within a specific production version, capturing full physical source locations and model extraction uncertainty to ground comparison certainty.
```python
class SourceLocation(BaseModel):
    source_file_path: str = Field(..., description="Relative or vault file path of source screenplay or EDL")
    page_number: Optional[int] = Field(None, description="Screenplay page number (1-indexed)")
    line_number: Optional[int] = Field(None, description="Screenplay line number or EDL event index")
    character_span_start: Optional[int] = Field(None, description="Character start offset in normalized script text")
    character_span_end: Optional[int] = Field(None, description="Character end offset in normalized text")
    scene_heading: Optional[str] = Field(None, description="Scene slugline (e.g., 'INT. DETECTIVE OFFICE - NIGHT')")

class ReviewerCorrection(BaseModel):
    correction_id: str = Field(..., description="Unique correction event ID")
    reviewer_id: str = Field(..., description="User ID of attorney or coordinator submitting correction")
    corrected_field: str = Field(..., description="Field corrected (e.g., 'description', 'context', 'prominence')")
    previous_value: Any = Field(...)
    corrected_value: Any = Field(...)
    correction_notes: Optional[str] = None
    corrected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CreativeUse(BaseModel):
    use_id: str = Field(..., description="Unique creative use instance ID (e.g., 'use_v8_poster_noir')")
    version_id: str = Field(..., description="Version containing this use instance")
    stable_lineage_key: str = Field(..., description="Immutable lineage key connecting asset across versions")
    scene_or_timecode: str = Field(..., description="Scene locator (e.g., 'Scene 42 - 00:44:12')")
    asset_type: str = Field(..., description="music | artwork | trademark | likeness | prop | location | text")
    description: str = Field(..., description="Detailed description of the asset appearance")
    duration_or_prominence: str = Field(..., description="Metric: duration, screen area, focal status (e.g., '14s focal close-up')")
    context: str = Field(..., description="Script dialogue, stage action, or narrative framing")
    source_span: Optional[str] = Field(None, description="Exact verbatim lines or EDL timecode span")
    source_location: Optional[SourceLocation] = Field(None, description="Exact physical source location and offsets")
    extraction_version: str = Field(default="gemini-2.5-flash-extract-v2.1", description="Model and prompt schema version used for extraction")
    extraction_uncertainty: float = Field(default=0.0, description="Model uncertainty metric (0.0=certain, 1.0=unreliable)")
    reviewer_corrections: List[ReviewerCorrection] = Field(default_factory=list, description="Audit ledger of human corrections")
    context_hash: str = Field(..., description="16-character SHA-256 fingerprint: context || '::' || duration_or_prominence")
```

#### 5.2.5 Delta (`CreativeDelta`) — Distinguishing Comparison Certainty
The computed difference between corresponding creative uses across versions, strictly distinguishing between "no change detected" and "could not reliably compare".
```python
class ChangeKind(str, Enum):
    ADDED = "added"
    MATERIALLY_MODIFIED = "materially_modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"          # Strictly: "No relevant change detected across comparable inputs"
    UNCERTAIN = "uncertain"          # Strictly: "We could not reliably compare these inputs"
    INCOMPARABLE = "incomparable"    # Format shift, OCR failure, or missing baseline alignment

class CreativeDelta(BaseModel):
    delta_id: str = Field(..., description="Unique delta identifier")
    before_use_id: Optional[str] = Field(None, description="Predecessor use instance ID in V_base")
    after_use_id: Optional[str] = Field(None, description="Target use instance ID in V_target")
    stable_lineage_key: str = Field(..., description="Asset lineage identifier")
    change_kind: ChangeKind = Field(..., description="Classification of modification")
    materiality: str = Field(default="none", description="none | low | medium | high")
    is_material: bool = Field(default=False, description="True if change invalidates statutory clearance defenses")
    changed_fields: List[str] = Field(default_factory=list, description="Fields that drifted (context, prominence, scene)")
    reason_codes: List[str] = Field(default_factory=list, description="Machine-readable codes (e.g., 'PROMINENCE_ESCALATION')")
    narrative_impact: Optional[str] = Field(None, description="Gemini-synthesized summary of legal/narrative impact")
```

#### 5.2.6 Invalidation Record (`InvalidationRecord` / `DecisionValidity`)
The computed validity of a prior clearance decision evaluated against a target version.
```python
class DecisionState(str, Enum):
    CARRIED_FORWARD = "carried_forward"
    STALE = "stale"
    RE_ATTESTED = "re_attested"
    EXCEPTION = "exception"
    REMOVED = "removed"
    NEW = "new"

class InvalidationRecord(BaseModel):
    invalidation_id: str = Field(..., description="Unique invalidation evaluation ID")
    decision_id: str = Field(..., description="Prior counsel decision ID evaluated")
    evaluated_for_version_id: str = Field(..., description="Target version ID")
    stable_lineage_key: str = Field(..., description="Asset lineage key")
    state: DecisionState = Field(..., description="Target clearance state")
    reason_code: str = Field(..., description="DEPENDENCIES_SATISFIED_UNCHANGED | CREATIVE_CONTEXT_ALTERED | EXTERNAL_EVIDENCE_SHIFT | FAIL_CLOSED_MISSING_DELTA | EXTRACTION_UNCERTAIN_FAIL_CLOSED")
    revalidation_action: str = Field(default="carry", description="carry | revalidate | manual | close")
    changed_dependency_ids: List[str] = Field(default_factory=list)
    explanation: Optional[str] = Field(None, description="Human-readable causal explanation for invalidation")
```

#### 5.2.7 Investigation Run (`InvestigationRun`) — Persisted Concept 2
An autonomous research session dispatched to verify invalidated or new claims, bound immutably to its source revision.
```python
class InvestigationRunState(str, Enum):
    QUEUED = "queued"
    INVESTIGATING = "investigating"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    WAITING_FOR_BUDGET = "waiting_for_budget"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"

class ToolExecutionRecord(BaseModel):
    step_id: str = Field(..., description="Unique execution step identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tool_name: str = Field(..., description="parallel_search | loc_copyright_api | ascap_ace_lookup | contract_retriever")
    query_issued: str = Field(..., description="Exact query string dispatched to provider")
    provider_status_code: int = Field(default=200)
    latency_ms: float = Field(...)
    stance_verdict: str = Field(..., description="supporting | contradictory | informational | insufficient")
    source_url: str = Field(..., description="Authoritative primary source URL")
    excerpt_snippet: str = Field(..., description="Attributable text quotation extracted from source")
    provider_call_id: Optional[str] = None
    raw_payload_hash: Optional[str] = None
    is_cached_result: bool = False

class InvestigationRun(BaseModel):
    run_id: str = Field(..., description="Unique run identifier (e.g., 'inv_88291')")
    production_id: str = Field(..., description="Associated production ID")
    source_revision_id: str = Field(..., description="Exact source revision ProductionVersion ID being evaluated")
    baseline_version_id: Optional[str] = Field(None, description="Baseline predecessor version ID")
    state: InvestigationRunState = Field(default=InvestigationRunState.QUEUED)
    claims_in_scope: List[str] = Field(default_factory=list, description="Lineage keys of stale claims investigated")
    plan_ids: List[str] = Field(default_factory=list, description="Associated InvestigationPlan identifiers")
    tool_executions: List[ToolExecutionRecord] = Field(default_factory=list, description="Full audit trail of tool results")
    budget_allocated_usd: float = Field(default=5.0)
    budget_spent_usd: float = Field(default=0.0)
    remaining_budget_usd: float = Field(default=5.0, description="Remaining available unspent budget")
    api_calls_count: int = Field(default=0)
    api_calls_limit: int = Field(default=10)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
```

#### 5.2.8 Investigation Plan (`InvestigationPlan`) — Persisted Concept 3
A persisted execution graph representing decomposed legal sub-goals, planned tool tasks, actual tool execution results, and granular remaining budget for each investigated claim.
```python
class PlanTaskStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED_BUDGET = "skipped_budget"

class PlanTask(BaseModel):
    task_id: str = Field(..., description="Unique task identifier within plan")
    sub_goal: str = Field(..., description="Specific legal inquiry (e.g., 'verify_1909_act_renewal')")
    tool_name: str = Field(..., description="Target tool: parallel_search | extract | contract_lookup")
    query_template: str = Field(..., description="Domain-steered query template")
    status: PlanTaskStatus = Field(default=PlanTaskStatus.PENDING)

class InvestigationPlan(BaseModel):
    plan_id: str = Field(..., description="Unique plan identifier (e.g., 'plan_poster_noir_v8')")
    run_id: str = Field(..., description="Parent InvestigationRun ID")
    source_revision_id: str = Field(..., description="Source revision ID under evaluation")
    stable_lineage_key: str = Field(..., description="Target claim lineage key")
    sub_goals: List[str] = Field(default_factory=list, description="Structured legal sub-goals")
    tasks: List[PlanTask] = Field(default_factory=list, description="Planned tool actions")
    tool_results: List[ToolExecutionRecord] = Field(default_factory=list, description="Executed tool results and raw payload hashes")
    initial_budget_usd: float = Field(default=2.50, description="Allocated spend cap for this plan")
    budget_spent_usd: float = Field(default=0.0, description="Cumulative spend consumed by executed tools")
    remaining_budget_usd: float = Field(default=2.50, description="Unspent budget balance available for further queries")
    status: str = Field(default="planned", description="planned | executing | completed | waiting_for_information | budget_exhausted")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

#### 5.2.9 Evidence Item (`EvidenceItem` / `PublicEvidenceSnapshot` & `ContractAgreement`)
Bifurcated container holding either an open-web registry snapshot or a private contract clause.
```python
class EvidenceType(str, Enum):
    PUBLIC_REGISTRY = "public_registry"
    PRIVATE_CONTRACT = "private_contract"

class EvidenceStance(str, Enum):
    SUPPORTING = "supporting"
    INFORMATIONAL = "informational"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT = "insufficient"

class EvidenceItem(BaseModel):
    evidence_id: str = Field(..., description="Unique evidence record ID")
    stable_lineage_key: str = Field(..., description="Associated asset lineage key")
    evidence_type: EvidenceType = Field(..., description="public_registry | private_contract")
    source_title: str = Field(..., description="Registry title or contract document filename")
    source_url_or_path: str = Field(..., description="Public web URL or vault contract path")
    publisher_or_parties: str = Field(..., description="Library of Congress / ASCAP / Licensor name")
    excerpt: str = Field(..., description="Attributable verbatim excerpt or contract clause")
    stance: EvidenceStance = Field(default=EvidenceStance.SUPPORTING)
    authority_score: float = Field(default=1.0, description="Registry reliability weight (0.0 to 1.0)")
    raw_payload_hash: str = Field(..., description="SHA-256 digest of raw response or contract text")
    provider_call_id: Optional[str] = None
    retrieval_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expiration_date: Optional[str] = Field(None, description="License or option term expiration date")
    confidentiality_tier: str = Field(default="public", description="public | legal_only | underwriter_auditable")
```

#### 5.2.10 Clarification Request (`ClarificationRequest`) — Persisted Concept 4
A human-in-the-loop task generated when autonomous research requires missing internal facts, linked explicitly to the exact creative use claim and source revision.
```python
class ClarificationRequest(BaseModel):
    request_id: str = Field(..., description="Unique clarification task ID")
    production_id: str = Field(..., description="Associated production ID")
    investigation_run_id: str = Field(..., description="Blocked investigation run ID")
    plan_id: Optional[str] = Field(None, description="Blocked investigation plan ID")
    stable_lineage_key: str = Field(..., description="Asset lineage key requiring clarification")
    use_id: str = Field(..., description="Exact creative use claim instance ID in source revision")
    source_revision_id: str = Field(..., description="Exact source revision ProductionVersion ID evaluated")
    question_headline: str = Field(..., description="Concise inquiry for production team")
    detailed_context: str = Field(..., description="Explanation of legal ambiguity and required documentation")
    required_document_type: Optional[str] = Field(None, description="purchase_receipt | talent_release | sync_quote")
    assigned_to_user_id: Optional[str] = None
    assigned_to_role: str = Field(default="clearance_coordinator")
    status: str = Field(default="pending", description="pending | answered | waived")
    answer_payload: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
```

#### 5.2.11 Counsel Decision (`CounselDecision` & `SupersessionEvent`) — Persisted Concept 5 & Mixed States
The legally binding human adjudication record committed to the append-only ledger, supporting mixed starting states and explicitly recording the PolicyVersion and EvidenceSnapshot versions that authorized the decision.
```python
class DecisionStatus(str, Enum):
    APPROVED = "approved"
    CONDITIONAL = "conditional"  # Approved with operational condition
    UNRESOLVED = "unresolved"    # Outstanding investigation or negotiation
    REJECTED = "rejected"        # Explicitly denied by counsel
    UNKNOWN = "unknown"          # Extracted with no prior recorded decision

class ReviewAction(str, Enum):
    RE_ATTEST = "re_attest"
    APPROVE_WITH_CONDITION = "approve_with_condition"
    EXCEPTION = "exception"
    REJECT_AND_REINVESTIGATE = "reject_and_reinvestigate"

class ReviewerIdentity(BaseModel):
    reviewer_id: str = Field(..., description="Unique attorney user ID")
    name: str = Field(..., description="Full legal name of clearance counsel")
    title: str = Field(default="Lead Clearance Counsel")
    organization: str = Field(..., description="Law firm or studio legal department")
    bar_number: Optional[str] = Field(None, description="State / jurisdiction bar admission number")

class CounselDecision(BaseModel):
    decision_id: str = Field(..., description="Unique decision ID")
    use_id: str = Field(..., description="Target creative use ID")
    stable_lineage_key: str = Field(..., description="Asset lineage key")
    applicable_version_id: str = Field(..., description="Target revision ProductionVersion ID for which approval applies")
    policy_version: str = Field(default="E&O-2026.1-DEVPOST", description="Exact policy ruleset version supporting this decision")
    supporting_evidence_snapshot_ids: List[str] = Field(default_factory=list, description="IDs of evidence snapshots supporting this finding")
    evidence_snapshot_versions: Dict[str, str] = Field(default_factory=dict, description="Mapping of supporting snapshot IDs to their cryptographic raw_payload_hash versions")
    supporting_contract_ids: List[str] = Field(default_factory=list, description="Private contract permission IDs, if applicable")
    status: DecisionStatus = Field(..., description="Clearance status: APPROVED | CONDITIONAL | UNRESOLVED | REJECTED | UNKNOWN")
    action: ReviewAction = Field(..., description="Adjudication action taken")
    statutory_basis: str = Field(..., description="17_usc_107_fair_use | public_domain_expired | express_license | exception")
    rationale: str = Field(..., description="Mandatory attorney legal reasoning")
    conditions: List[str] = Field(default_factory=list, description="Clearance conditions required for delivery")
    reviewer: ReviewerIdentity = Field(...)
    context_hash_evaluated: str = Field(..., description="Exact context hash evaluated by counsel")
    extraction_version: str = Field(default="gemini-2.5-flash-extract-v2.1", description="Upstream extraction model version")
    supersedes_decision_id: Optional[str] = Field(None, description="Predecessor decision ID superseded")
    parent_event_hash: str = Field(default="0" * 64, description="Preceding hash in append-only ledger")
    event_hash: str = Field(..., description="SHA-256 cryptographic digest of this decision event")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

#### 5.2.12 Draft Clearance Exceptions Schedule (`ExceptionsSchedule` & `Item`)
The formal underwriting review document exported for insurance carriers, completion guarantors, and distributors.
```python
class ExceptionsScheduleItem(BaseModel):
    stable_lineage_key: str
    asset_type: str
    description: str
    scene_or_timecode: str
    baseline_status: str  # approved | conditional | unresolved | rejected | unknown
    evaluation_state: str  # carried_forward | re_attested | exception
    invalidation_reason: Optional[str] = None
    counsel_action: str
    statutory_basis: str
    conditions: List[str] = []
    evidence_citations: List[Dict[str, str]] = []

class ExceptionsSchedule(BaseModel):
    schedule_id: str = Field(..., description="Unique schedule export identifier")
    production_id: str = Field(...)
    production_name: str = Field(...)
    target_version_id: str = Field(...)
    baseline_version_id: str = Field(...)
    policy_number: str = Field(default="E&O-2026.1-DEVPOST")
    carrier_name: str = Field(default="Standard Entertainment & Media Underwriters Syndicate")
    broker_name: str = Field(default="Gallagher / Front Row Insurance Brokers")
    deductible_usd: float = Field(default=50000.0)
    disclaimer: str = Field(
        default="NON-BINDING RISK ASSESSMENT: The Draft Clearance Exceptions Schedule for counsel and underwriter review is an informational clearance change control schedule. It does not bind insurance coverage or independently establish legal clearance without carrier underwriter endorsement and human counsel attestation."
    )
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_claims: int
    carried_forward_count: int
    reopened_count: int
    re_attested_count: int
    unresolved_exception_count: int
    items: List[ExceptionsScheduleItem] = []
    ledger_head_hash: str = Field(..., description="Cryptographic tip hash of the append-only ledger")
```

---

## 6. API Specifications & Integration Endpoints

All endpoints are versioned under `/api/v1` and enforce strict JSON schemas, authentication, and correlation headers.

```
API Surface Topology:
├── Ingestion Gateway   [POST /api/v1/ingest/gcs-event, /dropbox, /upload]
├── 1. Inbox            [GET /api/v1/inbox, PATCH /inbox/{id}/assign, POST /inbox/{id}/snooze]
├── 2. Productions      [GET/POST /api/v1/productions, GET /versions, POST /compare]
├── 3. Investigations   [GET /runs, POST /dispatch, GET /runs/{id}/stream (SSE), POST /cancel]
├── 4. Evidence         [GET /evidence/{prod_id}, POST /contracts/upload, GET /verify/{id}]
├── 5. Decisions        [GET /queue, POST /adjudicate, GET /audit-chain]
├── 6. Policy & Connect [GET/PUT /policy/{org_id}, GET /connections/health, POST /override]
└── Underwriting Export [GET /reports/exceptions-schedule/{prod_id}, GET /export]
```

---

### 6.1 Ingestion & Cloud Storage Connectors

#### `POST /api/v1/ingest/gcs-event`
- **Description**: Webhook receiver for Google Cloud Eventarc `storage.objects.v1.finalized` notifications.
- **Headers**:
  - `Ce-Type: google.cloud.storage.object.v1.finalized`
  - `X-Goog-Signature: <HMAC-SHA256>`
- **Request Body**:
  ```json
  {
    "bucket": "lienmark-intake-prestige",
    "name": "productions/shadows_broadway/scripts/shadows_v8_pink.pdf",
    "generation": "1725619200123456",
    "metageneration": "1",
    "contentType": "application/pdf",
    "size": "2451920",
    "md5Hash": "k9e8d7c6b5a43210fe=="
  }
  ```
- **Responses**:
  - `202 Accepted`: Event queued for ingestion; run registered.
  - `200 OK`: Duplicate SHA-256 hash detected; duplicate bypass stamped ($0.00 spend).
  - `401 Unauthorized`: Invalid HMAC signature.

#### `POST /api/v1/ingest/upload`
- **Description**: Direct multipart upload for production screenplays (`.pdf`, `.fdx`) or edit decision lists (`.edl`, `.xml`).
- **Form Data**: `file: Binary`, `production_id: string`, `label: string`, `parent_version_id: string`.

---

### 6.2 Destination 1: Inbox APIs

#### `GET /api/v1/inbox`
- **Description**: Retrieves prioritized work items across active productions.
- **Query Parameters**: `production_id?: string`, `severity?: P0 | P1 | P2 | P3`, `assigned_to?: string`.
- **Response `200 OK`**:
  ```json
  {
    "total_count": 14,
    "p0_count": 2,
    "p1_count": 5,
    "p2_count": 3,
    "items": [
      {
        "inbox_id": "inb_001",
        "production_id": "proj_shadows",
        "production_title": "Shadows Over Broadway",
        "stable_lineage_key": "music_cue_midnight_serenade",
        "asset_name": "Midnight Serenade (Jazz Cue)",
        "asset_type": "music",
        "severity": "P0_CRITICAL",
        "category": "adverse_external_evidence",
        "summary_headline": "Exclusive Worldwide Sync Assignment to Vanguard Media",
        "assigned_to_user_id": "counsel_sjenkins",
        "created_at": "2026-09-06T14:20:00Z",
        "delivery_deadline": "2026-09-07T12:00:00Z",
        "time_to_deadline_hours": 21.6
      }
    ]
  }
  ```

#### `PATCH /api/v1/inbox/{inbox_id}/assign`
- **Description**: Reassigns an inbox triage item to another legal team member.
- **Request Body**: `{"assigned_to_user_id": "counsel_mvance", "reason": "Music licensing specialist required"}`.

---

### 6.3 Destination 2: Productions APIs

#### `GET /api/v1/productions`
- **Description**: Lists all active production digital twins for the authenticated organization.

#### `GET /api/v1/productions/{production_id}/versions`
- **Description**: Returns the version DAG tree, content hashes, and clearance status counters for all milestones.

#### `POST /api/v1/productions/{production_id}/compare`
- **Description**: Computes a semantic and structural delta between any two arbitrary versions.
- **Request Body**:
  ```json
  {
    "base_version_id": "v7",
    "target_version_id": "v8",
    "include_unchanged": false
  }
  ```
- **Response `200 OK`**: Emits array of `CreativeDelta` records with prominence shifts and reason codes.

---

### 6.4 Destination 3: Investigations APIs

#### `POST /api/v1/investigations/dispatch`
- **Description**: Initiates a targeted, bounded research run for invalidated claims.
- **Request Body**:
  ```json
  {
    "production_id": "proj_shadows",
    "target_version_id": "v8",
    "baseline_version_id": "v7",
    "max_budget_usd": 5.0,
    "max_queries_per_claim": 3
  }
  ```

#### `GET /api/v1/investigations/runs/{run_id}/stream`
- **Description**: Real-time Server-Sent Events (SSE) telemetry stream emitting authentic tool execution events (`step_start`, `query_dispatched`, `provider_hit`, `stance_resolved`, `briefing_ready`).

#### `POST /api/v1/investigations/runs/{run_id}/cancel`
- **Description**: Immediately aborts an active run and cancels in-flight external provider calls to conserve budget.

---

### 6.5 Destination 4: Evidence APIs

#### `GET /api/v1/evidence/{production_id}`
- **Description**: Returns the bifurcated evidence repository (Public Registry Snapshots and Private Contracts).
- **Query Parameters**: `lineage_key?: string`, `type?: public_registry | private_contract`.

#### `POST /api/v1/evidence/contracts/upload`
- **Description**: Uploads an executed production contract (`.pdf`) and extracts permission clauses.
- **Form Data**: `file: Binary`, `stable_lineage_key: string`, `contract_type: string`, `confidentiality_tier: string`.

#### `GET /api/v1/evidence/verify/{evidence_id}`
- **Description**: Returns the full cryptographic proof for a piece of evidence: raw payload SHA-256 hash, provider call ID, retrieval timestamp, and live archived response payload.

---

### 6.6 Destination 5: Decisions APIs

#### `GET /api/v1/decisions/queue`
- **Description**: Retrieves pending claims requiring human counsel adjudication for a target version.

#### `POST /api/v1/decisions/adjudicate`
- **Description**: The sovereign legal sign-off endpoint. Commits a binding counsel attestation to the ledger.
- **Request Body**:
  ```json
  {
    "stable_lineage_key": "poster_noir_detective_magazine",
    "applicable_version_id": "v8",
    "action": "re_attest",
    "statutory_basis": "public_domain_lapsed_renewal",
    "rationale": "Crime Detective Magazine Vol. 3 No. 4 published Oct 1946. LOC records confirm zero renewal filed within 28-year window under 1909 Act. Asset in public domain.",
    "conditions": [],
    "reviewer_bar_number": "CA-284910"
  }
  ```
- **Response `200 OK`**: Emits `SupersessionEvent` containing newly minted `event_hash` and updated ledger tip.

#### `GET /api/v1/decisions/audit-chain/{production_id}`
- **Description**: Traverses and cryptographically validates the entire SHA-256 append-only ledger from genesis to head.

---

### 6.7 Destination 6: Connections & Policy APIs

#### `GET /api/v1/policy/{organization_id}`
- **Description**: Retrieves organization-level E&O insurance parameters, budget governors, and connector settings.

#### `PUT /api/v1/policy/{organization_id}`
- **Description**: Updates spend limits, circuit breaker trip thresholds, and carrier profiles.

#### `GET /api/v1/connections/health`
- **Description**: Diagnostic health check for external services: Parallel Search API latency, Gemini API quota, and Google Cloud Eventarc webhook listener status.

---

### 6.8 Underwriting Reports & Exports

#### `GET /api/v1/reports/exceptions-schedule/{production_id}`
- **Description**: Generates the complete, version-bound `ExceptionsSchedule` DTO (Draft Clearance Exceptions Schedule for counsel and underwriter review).

#### `GET /api/v1/reports/exceptions-schedule/{production_id}/export`
- **Description**: Exports the Draft Clearance Exceptions Schedule in printable format (`format=pdf` or `format=csv`) with non-binding disclaimer for counsel and underwriter review.

---

## 7. Verification & Acceptance Criteria (Gherkin Scenarios)

The system's integrity and compliance with E&O underwriter standards are verified through rigorous, automated test scenarios written in standard Gherkin syntax.

### 7.1 Scenario 1: Mathematical Conservation Invariant ($f(V_k, V_k) = N/N$)
```gherkin
Feature: Mathematical Conservation Invariant
  As Lead Clearance Counsel
  I want identical script cuts to carry forward all prior approvals automatically
  So that production incurs zero redundant legal expense or external API spend

  Scenario: Re-evaluating an unchanged version against itself
    Given an established production baseline version "v7" containing 12 approved claims
    And all 12 prior counsel decisions have valid SHA-256 context hashes
    When a user or webhook triggers clearance comparison with base="v7" and target="v7"
    Then the Invalidation Engine evaluates all 12 claims
    And exactly 12 claims evaluate to state "carried_forward"
    And exactly 0 claims evaluate to state "stale"
    And zero Parallel Search API queries are dispatched
    And total financial expenditure incurred is exactly $0.00
    And the resulting Draft Clearance Exceptions Schedule lists 0 unresolved exceptions
```

---

### 7.2 Scenario 2: Dynamic Creative Drift Invalidation
```gherkin
Feature: Creative Prominence Drift Invalidation
  As an E&O Underwriter
  I want framing escalations to invalidate prior incidental clearance defenses
  So that statutory de minimis fair-use failures are caught before broadcast

  Scenario: Background artwork escalated to focal dialogue
    Given a baseline version "v7" where asset "poster_noir_detective_magazine" was approved
    And the v7 prominence was "2s out-of-focus background blur" with context hash "h_v7_poster"
    When target revision "v8" is ingested
    And the v8 prominence shifts to "14s focal close-up with character reading headline"
    And the target context hash "h_v8_poster" diverges from "h_v7_poster"
    Then the Invalidation Engine strictly invalidates the claim to state "stale"
    And the assigned reason code is "CREATIVE_CONTEXT_ALTERED"
    And the item is placed into the Counsel Review Queue
    And the system forbids carrying forward the v7 approval without counsel re-attestation
```

---

### 7.3 Scenario 3: External Catalog Acquisition Invalidation
```gherkin
Feature: External Rights Evidence Drift
  As Studio Legal Counsel
  I want external music catalog sales to invalidate prior sync clearances
  So that the studio avoids willful copyright infringement under 17 U.S.C. 504(c)

  Scenario: Creative staging unchanged but sync rights sold externally
    Given a baseline version "v7" where "music_cue_midnight_serenade" was approved
    And the creative staging and timecode are identical between "v7" and "v8"
    When an external investigation queries the Parallel Search API
    And Parallel Search returns an excerpt from ASCAP proving rights acquisition by "Vanguard Media Holdings"
    And the evidence stance is classified as "CONTRADICTORY"
    And no private contract exists shielding this catalog assignment
    Then the Evidence Reconciliation Engine flags the claim as state "stale"
    And the assigned reason code is "EXTERNAL_EVIDENCE_SHIFT"
    And the item is escalated to the Inbox as a P0 Critical Delivery Blocker
```

---

### 7.4 Scenario 4: Fail-Closed Behavior on External API Degradation
```gherkin
Feature: Fail-Closed Security Perimeter
  As Chief Risk Officer
  I want external network failures and rate limits to degrade safely
  So that an API timeout never accidentally clears an unvetted asset

  Scenario: Parallel Search API returns HTTP 504 Gateway Timeout
    Given an invalidated stale claim requiring external registry verification
    When the Research Agent dispatches a query to "https://api.parallel.ai/v1/search"
    And the provider returns HTTP 504 Gateway Timeout on all bounded retries
    Then the system trips the circuit breaker for that request
    And the evidence record is stamped with stance "INSUFFICIENT"
    And the claim status remains strictly "NEEDS_REVIEW"
    And the system raises a FailClosedSecurityViolation if any code attempts auto-approval
    And the issue is surfaced in the Inbox with a diagnostic degraded network badge
```

---

### 7.5 Scenario 5: Human-in-the-Loop Clarification Lifecycle
```gherkin
Feature: Human-in-the-Loop Clarification Loop
  As an Autonomous Research Agent
  I want to pause execution when a private factual contract is required
  So that internal production documents can be uploaded before final legal scoring

  Scenario: Research blocked on missing talent release
    Given an active investigation run for a featured background talent likeness
    When public search cannot corroborate whether the actor signed a standard crowd release
    Then the investigation run transitions to state "waiting_for_information"
    And a ClarificationRequest is posted to the Inbox assigned to the Clearance Coordinator
    When the coordinator uploads "talent_release_signed_scene26.pdf"
    Then the investigation run automatically wakes up
    And the Evidence Parser extracts the release terms
    And the investigation completes, routing the verified briefing to Counsel Checkpoint
```

---

### 7.6 Scenario 6: Cryptographic Append-Only Ledger Integrity
```gherkin
Feature: Tamper-Evident Ledger Integrity
  As an E&O Insurance Auditor
  I want every counsel attestation to be cryptographically hash-chained
  So that post-hoc tampering or unauthorized status modification is mathematically impossible

  Scenario: Counsel re-attests an invalidated claim with statutory basis
    Given an invalidated claim "poster_noir_detective_magazine" in the review queue
    And prior ledger tip hash is "h_prev_64chars"
    When Sarah Jenkins, Esq. submits adjudication action "re_attest"
    And provides bar number "CA-284910" and rationale "Public domain expired under 1909 Act"
    Then the system mints a new SupersessionEvent
    And computes event_hash = SHA256(h_prev || event_data)
    And updates the ledger tip to the new event hash
    When an auditor runs GET /api/v1/decisions/audit-chain
    Then the audit chain verifies 100% valid from genesis to head with zero breaks
```

---

### 7.7 Scenario 7: Arbitrary $N$ Claim Scaling and Removal Handling
```gherkin
Feature: Input-Driven Arbitrary N Scaling
  As a Production Legal Supervisor
  I want the system to handle 100+ claims and dropped scenes correctly
  So that the platform functions on real, complex feature productions

  Scenario: Target script drops 5 scenes and adds 8 new musical cues
    Given a baseline script with 85 extracted claims
    When revised shooting script "v9" is ingested
    And 12 scenes containing 15 baseline claims are cut from the script
    And 4 new scenes introducing 8 new musical cues are added
    Then the system processes all 93 distinct lineage items
    And the 15 dropped claims evaluate to state "removed" and are excluded from the active schedule
    And the 8 new claims evaluate to state "new" and are queued for intake investigation
    And the remaining 70 claims are evaluated for creative and external drift
```

---

### 7.8 Scenario 8: Enterprise Spend Governor Hard Cap
```gherkin
Feature: Enterprise API Spend Protection
  As Studio Financial Controller
  I want runaway agent investigations to halt when budget caps are reached
  So that production never incurs unexpected cloud or search API overages

  Scenario: Investigation run hits $5.00 maximum budget cap
    Given a production with max_budget_usd set to 5.00
    And an active investigation run that has spent $4.85 across 18 search queries
    When the next planned search query would incur $0.20
    Then the SpendGuardMiddleware blocks the outbound request
    And the run state transitions to "waiting_for_budget"
    And an alert is dispatched to the studio administrator
    And existing gathered evidence is preserved without data loss
```

---

## 8. Summary Traceability Matrix

| Destination / Requirement | Core Entity | Primary API Endpoint | Invariant / Security Guarantee |
|---|---|---|---|
| **1. Inbox** | `InboxItem` | `GET /api/v1/inbox` | Delivery SLA tracking; P0 shoot blocker alerts. |
| **2. Productions** | `Production`, `ProductionVersion` | `POST /api/v1/productions/{id}/compare` | Mathematical conservation: $f(v_k, v_k) = N/N$ at $0.00 spend. |
| **3. Investigations** | `InvestigationRun`, `ToolExecutionRecord` | `GET /api/v1/investigations/runs/{id}/stream` | Real-time tool traces; no fake timer progress bars; hard budget caps. |
| **4. Evidence** | `EvidenceItem` (Public & Contract) | `GET /api/v1/evidence/{prod_id}` | Strict bifurcation: public web findings isolated from confidential contracts. |
| **5. Decisions** | `CounselDecision`, `SupersessionEvent` | `POST /api/v1/decisions/adjudicate` | Non-delegable human legal sovereignty; SHA-256 hash-chained ledger. |
| **6. Connections & Policy** | `CompanyPolicyConfig` | `PUT /api/v1/policy/{org_id}` | Workload Identity; constant-time webhook HMAC verification; circuit breakers. |
| **Underwriting Export** | `ExceptionsSchedule` | `GET /api/v1/reports/exceptions-schedule/{id}` | Draft Clearance Exceptions Schedule for counsel and underwriter review with non-binding risk assessment. |
| **Fixture Elimination** | Arbitrary $N$ Claims | Multi-endpoint pipeline | Dynamic discovery; no hardcoded 10+1+1 fixtures; generalized outcomes. |
