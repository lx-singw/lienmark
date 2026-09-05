# Lienmark: Technical Target Architecture
## Clearance Change Control & E&O Invalidation Engine for Agentic Cinema

> **Provenance & Authority Notice:**  
> This technical architecture document was authored strictly under **Google AntiGravity**, the approved developer environment for *Agentic Cinema: The Blockbuster Hackathon*. It accurately reflects the operational, tested codebase residing in `backend/` and `tests/`, implementing the **Parallel Track ($15,000 Prize Pool)** vertical slice: deterministic clearance drift detection, real Gemini 2.5 Flash semantic analysis, active Parallel Search API evidence retrieval, and Google Cloud Agent Builder / ADK orchestration.

---

## 1. Executive Summary & Core Architectural Premise

### 1.1 The Industry Problem: Silent Clearance Drift
In cinematic production and post-production, legal clearance for intellectual property (music, artwork, trademarks, likenesses, props, and architectural locations) is negotiated against a specific script draft or rough cut. However, film post-production is inherently fluid: scenes are re-cut, camera angles tighten from background blurs into featured focal shots, dialogue is improvised, and external rights ownership changes dynamically (e.g., copyright expiration or corporate catalog acquisition).

Traditionally, entertainment errors & omissions (E&O) insurance underwriter clearance is conducted as a monolithic, manual legal review at picture lock. When a film cut changes from Version 7 to Version 8:
- Clearance attorneys must either manually re-examine all 100+ creative uses across the script, incurring prohibitive delay and legal expense; or
- Production relies on informal clearance notes, risking catastrophic copyright infringement claims, distribution injunctions, or underwriter policy invalidation.

### 1.2 The Lienmark Solution: Version-Bound Selective Invalidation
Lienmark transforms entertainment clearance from a static, fragile document into a **deterministic, version-bound dependency graph**. Rather than treating legal clearance as a global binary state ("Approved"), Lienmark models each clearance decision as conditionally bound to:
1. Specific creative context, prominence, and timecode metrics within a defined `ProductionVersion`;
2. Attributable external evidence retrieved at a verified timestamp; and
3. Explicit human attorney attestations.

When Version 8 is ingested, Lienmark executes a **fail-closed selective invalidation engine**:
- **10 Unchanged Claims** carry forward automatically with version-bound cryptographic lineage proof, avoiding redundant legal expense.
- **2 Reopened Claims** are selectively flagged:
  - **Item 11 (Creative Drift):** A background 1946 detective magazine poster escalates from a 2-second out-of-focus blur in Scene 42 into a 14-second focal close-up with characters reading the headline aloud, invalidating statutory *de minimis* fair-use defenses.
  - **Item 12 (External Evidence Drift):** A background jazz trumpet cue ("Midnight Serenade") in Scene 18 is creatively unchanged, but an external rights query detects a catalog acquisition where worldwide synchronization rights were assigned to Vanguard Media Holdings.
- **Runtime Parallel Search API** queries are launched exclusively for the invalidated claims, capturing verifiable source URLs, excerpts, and stances.
- **Gemini 2.5 Flash** synthesizes actionable 15-second clearance briefings for entertainment counsel.
- Counsel re-attests the cleared item (Item 11, verified in public domain via Library of Congress records) and marks the unresolved item (Item 12) as an exception on the **Form E&O-2026 Underwriter Exceptions Schedule**.

---

## 2. Canonical Domain Model & Data Schemas

The domain model is implemented in `backend/domain/models.py` using **Pydantic v2**, enforcing strict typing, field validations, and RFC 3339 UTC ISO timestamps.

```
+------------------------------------------------------------------------------------+
|                                 CANONICAL DOMAIN GRAPH                             |
+------------------------------------------------------------------------------------+
|                                                                                    |
|   +-------------------+        1:N        +-------------------+                    |
|   | ProductionVersion | ----------------> |    CreativeUse    |                    |
|   +-------------------+                   +-------------------+                    |
|             |                                       |                              |
|             | Delta Analysis                        | Lineage Binding              |
|             v                                       v                              |
|   +-------------------+                   +-------------------+                    |
|   |   CreativeDelta   |                   |  CounselDecision  |                    |
|   +-------------------+                   +-------------------+                    |
|             |                                       |                              |
|             |                                       | Bound to V7                  |
|             +---------------\       /---------------+                              |
|                              v     v                                               |
|                    +-------------------+       Query        +--------------------+ |
|                    | DecisionValidity  | -----------------> | PublicEvidenceSnap | |
|                    +-------------------+                    +--------------------+ |
|                              |                                                     |
|                              | Reconciled via Human Attestation                    |
|                              v                                                     |
|                    +--------------------+                                          |
|                    | ExceptionsSchedule |                                          |
|                    +--------------------+                                          |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

### 2.1 Enumerations
```python
class ChangeKind(str, Enum):
    ADDED = "added"
    MATERIALLY_MODIFIED = "materially_modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    UNCERTAIN = "uncertain"

class DecisionState(str, Enum):
    CARRIED_FORWARD = "carried_forward"
    STALE = "stale"
    RE_ATTESTED = "re_attested"
    EXCEPTION = "exception"

class DecisionStatus(str, Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITION = "approved_with_condition"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"

class EvidenceStance(str, Enum):
    SUPPORTING = "supporting"
    INFORMATIONAL = "informational"
    CONTRADICTORY = "contradictory"
    INSUFFICIENT = "insufficient"
```

### 2.2 Entity Schemas

#### ProductionVersion
Represents an immutable script cut, EDL, or video timeline milestone.
```python
class ProductionVersion(BaseModel):
    version_id: str             # e.g., "v7", "v8"
    project_id: str             # e.g., "proj_blockbuster_cinema"
    label: str                  # e.g., "Shadows Over Broadway - Production Revision v8"
    created_at: str             # RFC 3339 UTC ISO timestamp
    content_hash: str           # SHA-256 digest of normalized script/timeline
    parent_version_id: Optional[str] = None  # Immediate predecessor ("v7")
    source_type: str = "screenplay"          # "screenplay", "edl", "video_cut"
```

#### CreativeUse
A concrete rights-bearing asset appearance within a specific version.
```python
class CreativeUse(BaseModel):
    use_id: str                 # Unique instance ID: "use_v8_poster_noir"
    version_id: str             # Version container: "v8"
    scene_or_timecode: str      # Locator: "Scene 42 - 00:44:12"
    asset_type: str             # "music", "trademark", "artwork", "likeness", "prop", "location"
    description: str            # Detailed asset description
    duration_or_prominence: str # Qualitative & quantitative prominence metric
    context: str                # Script dialogue, narrative context, camera framing
    stable_lineage_key: str     # Lineage identifier preserved across versions ("poster_noir_detective_magazine")
    source_span: Optional[str] = None
    context_hash: str           # SHA-256 fingerprint of (context + prominence)
```

#### CreativeDelta
The structured delta between corresponding `CreativeUse` records across versions.
```python
class CreativeDelta(BaseModel):
    delta_id: str
    before_use_id: Optional[str] = None
    after_use_id: Optional[str] = None
    stable_lineage_key: str
    change_kind: ChangeKind
    materiality: str = "none"   # "none", "low", "high"
    match_confidence: float = 1.0
    changed_fields: List[str] = []
    reason_codes: List[str] = []
```

#### PublicEvidenceSnapshot
Attributable third-party verification retrieved at runtime from Parallel Search API.
```python
class PublicEvidenceSnapshot(BaseModel):
    snapshot_id: str
    use_id: str
    stable_lineage_key: str
    query: str
    retrieved_at: str
    provider: str = "Parallel"
    source_url: str
    source_title: str
    excerpt: str
    publisher: Optional[str] = None
    stance: EvidenceStance = EvidenceStance.SUPPORTING
    cached_or_live: str = "live"
    provider_call_id: Optional[str] = None
    retrieval_latency_ms: Optional[float] = None
```

#### CounselDecision
The binding, legally authoritative attestation recorded by human clearance counsel.
```python
class CounselDecision(BaseModel):
    decision_id: str
    use_id: str
    stable_lineage_key: str
    applicable_version_id: str  # Version for which this approval applies ("v7")
    status: DecisionStatus      # APPROVED, APPROVED_WITH_CONDITION, REJECTED, NEEDS_REVIEW
    rationale: str
    reviewer_display_name: str = "Sarah Jenkins, Esq. (Clearance Counsel)"
    reviewed_at: str
    supersedes_decision_id: Optional[str] = None
    dependency_ids: List[str] = []
    system_recommendation: Optional[str] = None
    human_confirmed: bool = True
```

#### DecisionValidity
The computed validity of a prior decision evaluated against a target version.
```python
class DecisionValidity(BaseModel):
    decision_id: str
    evaluated_for_version_id: str
    stable_lineage_key: str
    state: DecisionState        # CARRIED_FORWARD, STALE, RE_ATTESTED, EXCEPTION
    reason_code: str            # Machine-readable reason code
    changed_dependency_ids: List[str] = []
    revalidation_action: str = "carry"  # "carry", "revalidate", "close", "manual"
    evidence_snapshot: Optional[PublicEvidenceSnapshot] = None
    creative_delta: Optional[CreativeDelta] = None
```

#### ExceptionsSchedule & Item
The final, version-bound deliverable exported for E&O underwriters.
```python
class ExceptionsScheduleItem(BaseModel):
    stable_lineage_key: str
    asset_type: str
    description: str
    scene_or_timecode: str
    v7_decision_status: str
    v8_evaluation_state: str   # "carried_forward", "re_attested", "exception"
    invalidation_reason: Optional[str] = None
    counsel_action: str
    evidence_citations: List[Dict[str, str]] = []

class ExceptionsSchedule(BaseModel):
    schedule_id: str
    project_id: str
    project_name: str = "Lienmark Production Digital Twin"
    target_version_id: str
    base_version_id: str
    generated_at: str
    policy_version: str = "E&O-2026.1-DEVPOST"
    total_claims: int
    carried_forward_count: int
    reopened_count: int
    re_attested_count: int
    unresolved_exception_count: int
    items: List[ExceptionsScheduleItem] = []
```

---

## 3. Deterministic Invalidation Engine Architecture & Fail-Closed State Machine

### 3.1 The Engine Design: Pure Python vs. Non-Deterministic LLMs
A foundational engineering principle of Lienmark is that **LLMs never make legal clearance decisions or execute state transitions**. LLMs are utilized solely for semantic interpretation (extracting shifts in framing, dialogue prominence, and summarization). 

The state transitions of `DecisionValidity` are executed by a pure, deterministic Python engine (`backend/core/invalidation_engine.py`) enforcing **Policy `E&O-2026.1-DEVPOST`**.

```
+--------------------------------------------------------------------------------------------------+
|                            FAIL-CLOSED STATE TRANSITION MACHINE                                  |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   Prior Counsel Decision (v7: APPROVED)                                                          |
|                    |                                                                             |
|                    v                                                                             |
|   +---------------------------------+                                                            |
|   | Deterministic Lineage Matching  |                                                            |
|   +---------------------------------+                                                            |
|                    |                                                                             |
|         [Stable Key Present?]                                                                    |
|          /               \                                                                       |
|        YES                NO (Asset Deleted or Unmapped)                                         |
|        /                    \                                                                    |
|       v                      v                                                                   |
|   +--------------------+   +----------------------------------+                                  |
|   | Context Hash Check |   | STALE (FAIL_CLOSED_MISSING_DELTA)|                                  |
|   +--------------------+   +----------------------------------+                                  |
|       /            \                                                                             |
|   HASH EQUAL    HASH CHANGED                                                                     |
|     /                \                                                                           |
|    v                  v                                                                          |
|  [External Stance?]  +-------------------------------------+                                     |
|    /          \      | STALE (CREATIVE_CONTEXT_ALTERED)    |                                     |
| CONTRADICTORY  SUPPORTING +-------------------------------------+                                |
|  /              \                                                                                |
| v                v                                                                               |
|+---------------+ +---------------------------------------+                                       |
|| STALE         | | CARRIED_FORWARD                       |                                       |
||(EXTERNAL_     | | (DEPENDENCIES_SATISFIED_UNCHANGED)    |                                       |
|| EVIDENCE_     | +---------------------------------------+                                       |
|| SHIFT)        |                                                                                 |
|+---------------+                                                                                 |
|       \                               /                                                          |
|        \-----------------------------/                                                           |
|                       |                                                                          |
|                       v                                                                          |
|          +--------------------------+                                                            |
|          | Human Counsel Review Gate|                                                            |
|          +--------------------------+                                                            |
|             /                    \                                                               |
|       RE-ATTEST                REJECT                                                            |
|          /                        \                                                              |
|         v                          v                                                             |
|   +-------------+           +---------------+                                                    |
|   | RE_ATTESTED |           |   EXCEPTION   | (Unresolved on Form E&O)                           |
|   +-------------+           +---------------+                                                    |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+
```

### 3.2 Context Fingerprinting & Hashing
To prevent subtle script modifications from escaping review, `InvalidationEngine` computes a 16-character SHA-256 context hash:
$$\text{context\_hash} = \text{SHA256}(\text{context} \parallel \text{"::"} \parallel \text{prominence})[0:16]$$
If a director tightens camera framing from background to foreground, or adds dialogue that touches an artwork, the context hash changes, triggering a `CREATIVE_CONTEXT_ALTERED` revalidation event.

### 3.3 The Canonical 12 -> 10 Carried / 2 Reopened Golden Fixture

Lienmark's behavior is verified through a canonical, repeatable fixture representing the production *"Shadows Over Broadway"* (`backend/fixtures/golden_dataset.py`):

| # | Stable Lineage Key | Asset Type | Scene / Locator | V7 Status | V8 Modification / Trigger | Invalidation State | Reason Code | Revalidation Action |
|---|---|---|---|---|---|---|---|---|
| 1 | `prop_vintage_telephone` | Prop | Scene 04 | APPROVED | Identical set dressing | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 2 | `poster_paris_expo_1937` | Artwork | Scene 08 | APPROVED | Identical hallway blur | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 3 | `car_ford_sedan_1949` | Prop | Scene 12 | APPROVED | Identical curbside park | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 4 | `trademark_acme_coffee` | Trademark | Scene 15 | APPROVED | Identical diner sign | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 5 | `artwork_abstract_expressionist` | Artwork | Scene 21 | APPROVED | Identical office canvas | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 6 | `likeness_mayor_cameo` | Likeness | Scene 26 | APPROVED | Identical courtroom extra | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 7 | `architecture_tribunal_facade` | Location | Scene 30 | APPROVED | Identical courthouse steps | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 8 | `text_headline_gazette` | Text | Scene 34 | APPROVED | Identical newsstand insert | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 9 | `wardrobe_fedora_brand` | Trademark | Scene 38 | APPROVED | Identical fedora wardrobe | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 10 | `music_incidental_radio_static` | Music | Scene 40 | APPROVED | Identical radio static hum | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| 11 | `poster_noir_detective_magazine` | Artwork | Scene 42 | APPROVED | **Creative Drift:** 2s blur -> 14s close-up focal dialogue | **`STALE`** | **`CREATIVE_CONTEXT_ALTERED`** | **`revalidate`** |
| 12 | `music_cue_midnight_serenade` | Music | Scene 18 | APPROVED | **Evidence Drift:** Creative unchanged, but sync rights sold | **`STALE`** | **`EXTERNAL_EVIDENCE_SHIFT`** | **`revalidate`** |

### 3.4 Fail-Closed Invariants
1. **Material Change Invalidation:** Any material creative change strictly invalidates prior clearance (`STALE`).
2. **Missing Delta Rejection:** Any unmapped asset or dropped lineage strictly defaults to `STALE` (`FAIL_CLOSED_MISSING_DELTA`).
3. **Adverse Evidence Isolation:** Any external evidence whose stance is `CONTRADICTORY` or `INSUFFICIENT` immediately flags the claim for counsel review.
4. **No Autonomous Legal Exoneration:** A language model cannot create an `APPROVED` legal decision.
5. **Traceable Attribution:** Every output row contains machine-readable reason codes, policy version strings, and timestamps.

---

## 4. Runtime Integration Architecture

Lienmark unifies three core cloud and intelligence services into a coherent, observable workflow (`backend/orchestration/workflow.py`).

```
+----------------------------------------------------------------------------------------------------+
|                                LIENMARK RUNTIME ORCHESTRATION                                      |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    Client Request (POST /api/drift/compare)                                                        |
|         |                                                                                          |
|         v                                                                                          |
|    +------------------------------------------------------------------------------------------+    |
|    | LienmarkWorkflow (Google Cloud Agent Builder / ADK Execution Pattern)                    |    |
|    |                                                                                          |    |
|    |   Step 1: Version Ingestion & Fixtures                                                   |    |
|    |           - Ingests V7 and V8 Script Records                                             |    |
|    |           - Traced: duration_ms, items count                                             |    |
|    |                                                                                          |    |
|    |   Step 2: Semantic Delta Analysis (Gemini 2.5 Flash)                                     |    |
|    |           - Model: gemini-2.5-flash                                                      |    |
|    |           - Mode: Structured JSON (DeltaAnalysisResult)                                  |    |
|    |           - Evaluates Scene 42 narrative shift: 2s background -> 14s focal dialogue      |    |
|    |                                                                                          |    |
|    |   Step 3: Deterministic Invalidation Engine                                              |    |
|    |           - Evaluates 12 claims against Policy E&O-2026.1-DEVPOST                         |    |
|    |           - Output: 10 Carried Forward, 2 Reopened (Stale)                               |    |
|    |                                                                                          |    |
|    |   Step 4: Targeted Search (Parallel Search API)                                          |    |
|    |           - Query 1: Crime Detective Magazine 1946 Shadows Over Broadway renewal         |    |
|    |           - Query 2: Midnight Serenade jazz sync rights copyright owner 2026             |    |
|    |           - Captures: Source URL, LOC/ASCAP excerpts, provider call IDs, latencies       |    |
|    |                                                                                          |    |
|    |   Step 5: Clearance Briefing Synthesis (Gemini 2.5 Flash)                                |    |
|    |           - Generates 15-second concise attorney action recommendations                  |    |
|    |                                                                                          |    |
|    |   Step 6: Trace & Event Aggregation                                                      |    |
|    |           - Bundles WorkflowStepTrace records with millisecond timings                   |    |
|    +------------------------------------------------------------------------------------------+    |
|         |                                                                                          |
|         v                                                                                          |
|    WorkflowRunResult Emitted -> Interactive Counsel Review Dashboard                               |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### 4.1 Gemini 2.5 Flash Integration (`backend/services/gemini_service.py`)
- **Model Choice:** `gemini-2.5-flash` provides low-latency inference, robust semantic reasoning over screenplay dialogue, and reliable native JSON schema emission.
- **Role 1: Semantic Script Delta Analysis:**
  Computes `DeltaAnalysisResult` across script drafts:
  ```json
  {
    "is_material": true,
    "prominence_shift": "Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue.",
    "narrative_impact": "The character actively interacts with the artwork and quotes text aloud, eliminating incidental background defense.",
    "clearance_risk_level": "high",
    "statutory_fair_use_impact": "De minimis doctrine under 17 U.S.C. 107 no longer applies; requires public domain verification or license.",
    "recommended_action": "revalidate"
  }
  ```
- **Role 2: Counsel Clearance Synthesis:**
  Synthesizes legal research and Parallel evidence into an executive briefing (`ClearanceBriefing`) recommending actionable legal remedies (e.g., public domain re-attestation vs. cue replacement).

### 4.2 Parallel Search API Integration (`backend/services/parallel_service.py`)
- **API Endpoint:** `https://api.parallel.ai/v1/search`
- **Selective Scoping:** Parallel Search is **never invoked for carried or closed claims**. Calls are triggered strictly for claims entering `STALE` status requiring external public-record verification.
- **Attributable Metadata Capture:**
  Each query returns a `PublicEvidenceSnapshot` containing:
  - `source_url`: Verifiable government or industry catalog URL (e.g., Library of Congress `cocatalog.loc.gov` or ASCAP Repertory).
  - `excerpt`: Attributable quotation verifying public domain expiration or active license assignment.
  - `stance`: Classified as `SUPPORTING`, `CONTRADICTORY`, or `INSUFFICIENT`.
  - `provider_call_id` & `retrieval_latency_ms`: Verifiable audit telemetry.
- **Offline Deterministic Fallback:** When running in hermetic test environments or without external network credentials, the service emits verified offline snapshots matching the golden dataset, ensuring 100% test reproducibility.

### 4.3 Google Cloud Agent Builder & ADK Orchestration Pattern
The execution follows Google's Agent Development Kit (ADK) specification:
- **Explicit Step Lifecycle:** Each phase (`version_ingestion`, `semantic_delta_analysis`, `deterministic_dependency_invalidation`, `parallel_targeted_search`, `clearance_briefings`) is logged as a discrete `WorkflowStepTrace`.
- **Latency & State Accountability:** Every step records component origin, status, elapsed milliseconds, and contextual metadata, enabling auditors to trace the decision path from script ingest to underwriter packet.

---

## 5. Security, Trust Boundaries, and E&O Underwriter Posture

### 5.1 Trust Architecture & Defense in Depth
Entertainment legal insurance clearance requires rigorous defensibility against adversarial scrutiny, unauthorized clearance modification, and statutory compliance audits. Lienmark enforces a defense-in-depth security perimeter structured across four distinct trust domains:

```
+------------------------------------------------------------------------------------+
|                             SECURITY & TRUST BOUNDARIES                            |
+------------------------------------------------------------------------------------+
|                                                                                    |
|   [ UNTRUSTED EXTERNAL INTERNET ]                                                  |
|   Parallel Search API / Public Web Records / ASCAP / Library of Congress           |
|                |                                                                   |
|                v (Sanitized excerpts; untrusted source content)                    |
|   +----------------------------------------------------------------------------+   |
|   | APPLICATION TRUST BOUNDARY: FASTAPI BACKEND (Cloud Run :8080)              |   |
|   |                                                                            |   |
|   |  - Untrusted text treated as data, never as prompt instructions            |   |
|   |  - Pydantic v2 input sanitization & strict enum validation                 |   |
|   |  - Deterministic state machine isolates LLM outputs                        |   |
|   |  - Service Account Workload Identity; zero committed API secrets           |   |
|   +----------------------------------------------------------------------------+   |
|                ^                                  |                                |
|                | Server-to-Server RPC             | Ground-Truth Data Feeds        |
|                | (Signed Mutations)               | (JSON DTOs & Schedules)        |
|                |                                  v                                |
|   +----------------------------------------------------------------------------+   |
|   | PRESENTATION TRUST BOUNDARY: NEXT.JS APP ROUTER (Cloud Run :3000)          |   |
|   |                                                                            |   |
|   |  - Server Actions: Authenticated RPC boundary for counsel re-attestation   |   |
|   |  - SSR: Ground-truth rendering of printable Form E&O-2026 schedule        |   |
|   |  - Route Handlers: BFF API gateway, credential isolation & rate limiting   |   |
|   +----------------------------------------------------------------------------+   |
|                ^                                  |                                |
|                | Form Actions / Mutations         | Read-Only SSR HTML / Hydration |
|                |                                  v                                |
|   +----------------------------------------------------------------------------+   |
|   | HUMAN CLEARANCE COUNSEL BOUNDARY (Counsel / Underwriter Browser)           |   |
|   |                                                                            |   |
|   |  - Exclusive authority to grant clearance (new_status = approved)          |   |
|   |  - Named legal reviewer, bar identity & mandatory legal rationale          |   |
|   |  - Supersedes decision history in an append-only, version-bound audit trail|   |
|   +----------------------------------------------------------------------------+   |
|                |                                                                   |
|                v                                                                   |
|   [ E&O UNDERWRITING PACKET: FORM E&O-2026 EXCEPTIONS SCHEDULE ]                   |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

### 5.2 Next.js App Router Architecture & Security Posture

The presentation tier is implemented in **Next.js 15 (React 19)** using the **App Router** paradigm (`frontend/app/`), establishing a hardened boundary between client interactivity and backend domain logic.

```
+------------------------------------------------------------------------------------+
|                    NEXT.JS APP ROUTER TRUST & INTEGRATION TOPOLOGY                 |
+------------------------------------------------------------------------------------+
|                                                                                    |
|   Browser (Counsel / Underwriter)                                                  |
|     |                                                                              |
|     |-- 1. Attestation Submission --------------------+                            |
|     |-- 2. SSR Page Request (GET /report/v8) -------- | --------------------+      |
|     |-- 3. Client Interaction / Drift Poll ---------- | --------------+     |      |
|     v                                                 v               v     v      |
|  +-------------------------------------------------------------------------------+ |
|  | NEXT.JS SERVER RUNTIME (Node.js 20 LTS)                                        | |
|  |                                                                               | |
|  |  +---------------------------+  +-----------------------+  +---------------+  | |
|  |  | Server Actions            |  | Route Handlers (BFF)  |  | SSR Generator |  | |
|  |  | ("use server")            |  | (app/api/.../route.ts)|  | (app/report)  |  | |
|  |  |                           |  |                       |  |               |  | |
|  |  | - Attestation validation |  | - API proxy & headers |  | - Data fetch  |  | |
|  |  | - Counsel session binding |  | - Credential shielding|  | - Print CSS   |  | |
|  |  | - Cache invalidation      |  | - SSE stream conduit  |  | - Zero drift  |  | |
|  |  +---------------------------+  +-----------------------+  +---------------+  | |
|  |                |                            |                      |          | |
|  +----------------|----------------------------|----------------------|----------+ |
|                   v                            v                      v            |
|         POST /api/review/attest      POST /api/drift/compare   GET /api/reports/...|
|                   |                            |                      |            |
|                   +----------------------------+----------------------+            |
|                                                |                                   |
|                                                v                                   |
|                          +------------------------------------------+              |
|                          | FASTAPI BACKEND (:8080)                  |              |
|                          | Invalidation Engine, Gemini, Parallel    |              |
|                          +------------------------------------------+              |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

#### 5.2.1 Server Actions: Tamper-Evident Counsel Re-Attestation
In entertainment clearance, legal decisions carry multimillion-dollar liability. Re-attestation cannot be entrusted to client-side logic where network payloads can be forged or local state manipulated.

- **Encapsulated Server Execution (`"use server"`):** When clearance counsel confirms an override via `AttorneyOverrideModal.tsx`, the action is submitted to a Next.js Server Action (`recordAttestationAction`). Execution is confined strictly to the Node.js server environment; no proprietary business rules or backend authentication secrets are exposed to the client bundle.
- **Fail-Closed Payload & Identity Validation:** Before invoking the backend, the Server Action validates all required legal fields against the canonical `CounselDecision` schema:
  - `stable_lineage_key`: Bound to the exact asset lineage being cleared.
  - `version_id`: Strictly locked to the target production version (e.g., `"v8"`).
  - `new_status`: Enum-validated (`approved`, `approved_with_condition`, `rejected`, `needs_review`).
  - `counsel_rationale`: Non-empty legal justification citing supporting evidence.
  - `reviewer_name`: Authenticated legal counsel identity.
- **Atomic Backend Mutation:** The Server Action executes an internal server-to-server `POST` to the FastAPI backend at `/api/review/attest`. The backend updates the append-only in-memory decision store and records the superseding decision.
- **Instantaneous Cache Invalidation (`revalidatePath`):** Upon successful attestation, the Server Action invokes:
  ```typescript
  revalidatePath('/report/[production_id]', 'page');
  revalidateTag('exceptions-schedule');
  ```
  This immediately flushes server-cached report representations and triggers background re-validation, ensuring that any subsequent underwriter view reflects the re-attested state without race conditions or stale client-side caching.

#### 5.2.2 Server-Side Rendering (SSR): Printable Form E&O-2026 Exceptions Schedule
The **Form E&O-2026 Exceptions Schedule** (`frontend/app/report/[production_id]/page.tsx`) serves as the version-bound exceptions schedule deliverable structured for insurance underwriter review and production bond evaluation.

- **Direct Server-Side Data Ingestion:** The report page is implemented as an async React Server Component. During the SSR request lifecycle, the page directly queries the FastAPI backend (`GET /api/reports/exceptions` or internal service URL) on the server tier. The HTML document is generated with fully baked data before transmitting a single byte to the client.
- **Zero Client Hydration Drift:** Client-side rendering frameworks are prone to hydration discrepancies, layout shifts, or DOM manipulation via browser extensions. Next.js SSR ensures that the reviewer receives a reliable, bit-for-bit accurate document reflecting backend state at the exact millisecond of rendering.
- **Printable High-Fidelity Design (`@media print`):** The SSR template utilizes specialized Tailwind print utilities and CSS print media rules:
  - Header with statutory insurance metadata: Policy ID (`E&O-2026.1-DEVPOST`), Underwriter Carrier, Production Title, Target Cut Hash, and UTC Timestamp.
  - Non-breaking table layouts (`break-inside-avoid`) ensuring individual claim rows, legal rationales, and Parallel Search citations never split awkwardly across physical page breaks.
  - Underwriter signature blocks with verifiable counsel digital attestation stamps.
- **Read-Only Evidentiary Mode:** The SSR view can be rendered without client JavaScript enabled, fulfilling statutory legal requirements for archival in underwriter document management systems (DMS) and headless PDF generation.

#### 5.2.3 Route Handlers: BFF Gateway & Secure Backend Interface
Next.js Route Handlers (`frontend/app/api/.../route.ts`) function as a secure Backend-For-Frontend (BFF) reverse proxy:

- **Credential & Infrastructure Shielding:** Client browsers never communicate directly with internal FastAPI backend ports, internal Cloud Run microservice hostnames, or third-party APIs. Route Handlers maintain private environment variables (`INTERNAL_BACKEND_URL`, internal service-to-service IAM tokens) strictly on the server.
- **Proxy Endpoints:**
  - `POST /app/api/attorney-override/route.ts`: Forwards interactive attorney overrides from client components to FastAPI `POST /api/review/attest`, providing standardized error handling, CORS isolation, and JSON payload normalization.
  - `POST /app/api/drift/compare`: Proxies clearance drift comparison requests to FastAPI, handling long timeouts (up to 300s) and streaming execution progress telemetry (`WorkflowStepTrace`) back to the dashboard.
- **Resilience & Graceful Degradation:** Route Handlers intercept network failures, rate limits, or backend maintenance states, returning typed error responses to the UI and preventing raw backend stack traces from leaking to the end user.

### 5.3 The E&O Underwriter Posture & Audit Lineage
1. **Clearance Is Version-Bound:** A clearance opinion is valid solely for the script/cut version it was evaluated against. Lienmark prevents the common studio failure mode where an early clearance is mistakenly assumed to cover subsequent edits.
2. **Append-Only Audit Provenance:** Re-attestations require an authenticated reviewer (`reviewer_name`), target version binding (`version_id`), and an explicit rationale explaining why the item is non-infringing.
3. **Fail-Closed Unresolved Exceptions:** The demo flow intentionally leaves **Item 12 (`music_cue_midnight_serenade`)** unresolved as an active exception. This demonstrates to insurance underwriters that Lienmark does not artificially manufacture green "approved" statuses, but surfaces real legal exposure.

---

## 6. Deployment Topology & Container Architecture

### 6.1 Frontend Architecture & Next.js App Router Structure
The frontend application resides in `frontend/` and follows standard Next.js 15 App Router conventions:

```
frontend/
├── app/
│   ├── layout.tsx                     # Root layout with Tailwind styling and typography
│   ├── page.tsx                       # Interactive Clearance Dashboard (Client & Server boundary)
│   ├── globals.css                    # Tailwind base, components, and @media print rules
│   ├── report/
│   │   └── [production_id]/
│   │       └── page.tsx               # SSR-rendered Form E&O-2026 Exceptions Schedule
│   ├── api/
│   │   └── attorney-override/
│   │       └── route.ts               # BFF Route Handler proxying to FastAPI backend
│   └── components/
│       ├── ClaimsTable.tsx            # Interactive claims list with state badges
│       ├── ClaimRow.tsx               # Individual claim row with delta indicators
│       ├── AttorneyOverrideModal.tsx  # Counsel re-attestation modal invoking Server Actions
│       ├── HumanReviewFlag.tsx        # Visual callout for STALE claims requiring action
│       ├── SourceCitation.tsx         # Attributable Parallel Search citation viewer
│       ├── IntakeDropzone.tsx         # Production script / EDL upload interface
│       ├── PresetProfileSelector.tsx  # Quick-switch presets (e.g., Shadows Over Broadway)
│       ├── FeatureTogglePanel.tsx     # Demo controls for fail-closed policy simulation
│       ├── DiscoveryNotification.tsx  # Real-time banner for newly detected drift
│       ├── ClarifyingQuestionModal.tsx# Interactive dialogue for ambiguous clearances
│       └── ToastContainer.tsx         # Ephemeral feedback alerts
├── lib/
│   └── api_client.ts                  # Typed isomorphic HTTP client for backend integration
├── next.config.js                     # Standalone build output, rewrites, and backend env
├── package.json                       # Next.js 15, React 19, Tailwind, Lucide React dependencies
├── postcss.config.js                  # PostCSS plugin pipeline
└── tsconfig.json                      # Strict TypeScript 5 configuration with @/* path aliases
```

### 6.2 Google Cloud Run Deployment Topology

In production on **Google Cloud**, Lienmark deploys as a modern decoupled multi-container architecture orchestrated via Google Cloud Run:

```
                                  +-------------------------------------------------------------+
                                  |                 GOOGLE CLOUD PLATFORM                       |
                                  |                                                             |
                                  |  +-------------------------------------------------------+  |
                                  |  | Cloud Run: lienmark-frontend (Container :3000)        |  |
                                  |  |  - Node.js 20 Alpine (Standalone Build)               |  |
                                  |  |  - Next.js 15 App Router (React 19)                   |  |
    HTTPS (Port 443)              |  |  - Server-Side Rendering (SSR) for Form E&O-2026      |  |
    Clearance Counsel / Judge --->|  |  - Server Actions for Counsel Re-Attestation          |  |
    Browser Session               |  |  - BFF Route Handlers for Backend API Isolation       |  |
                                  |  +-------------------------------------------------------+  |
                                  |                             |                               |
                                  |                             | Internal VPC / Authenticated  |
                                  |                             | Cloud Run Service-to-Service  |
                                  |                             v                               |
                                  |  +-------------------------------------------------------+  |
                                  |  | Cloud Run: lienmark-backend (Container :8080)         |  |
                                  |  |  - Python 3.11-slim Base                              |  |
                                  |  |  - FastAPI Web Application & API (Uvicorn ASGI)       |  |
                                  |  |  - InvalidationEngine (Deterministic State Machine)   |  |
                                  |  |  - LienmarkWorkflow (ADK Orchestration Pattern)       |  |
                                  |  |  - Healthcheck: GET /health (30s)                     |  |
                                  |  +-------------------------------------------------------+  |
                                  |         |                                    |              |
                                  |         | Workload Identity                  | Secret Mgr   |
                                  |         v                                    v              |
                                  |  +-------------------+              +--------------------+  |
                                  |  | Google GenAI /    |              | Secret Manager:    |  |
                                  |  | Gemini 2.5 Flash  |              | PARALLEL_API_KEY   |  |
                                  |  +-------------------+              +--------------------+  |
                                  +-------------------------------------------------------------+
                                                                         |
                                                                         v Outbound HTTPS
                                                              +--------------------+
                                                              | Parallel Search    |
                                                              | API (api.parallel) |
                                                              +--------------------+
```

### 6.3 Multi-Container Specifications

#### 6.3.1 Backend Container Specification (`Dockerfile`)
The backend is packaged as a multi-stage Docker image using `python:3.11-slim`:
- **Builder Stage:** Compiles dependencies into an isolated virtual environment `/opt/venv`.
- **Runner Stage:** Copies `/opt/venv`, runs as non-root user `appuser` (UID 10001), exposes port 8080, and configures automated health checking via `GET /health`.
- **Command:** `uvicorn backend.main:app --host 0.0.0.0 --port 8080`

#### 6.3.2 Frontend Container Specification (`frontend/Dockerfile`)
The frontend container leverages Next.js 15 standalone output for an ultra-compact production footprint (<120MB):
- **Stage 1 (deps):** `node:20-alpine` installs production and development dependencies using frozen manifests.
- **Stage 2 (builder):** Compiles the Next.js App Router application with `npm run build`, generating the self-contained `.next/standalone` bundle.
- **Stage 3 (runner):** `node:20-alpine` sets `NODE_ENV=production`, creates an unprivileged system user `nextjs` (UID 1001), copies only `.next/standalone` and static public assets, and exposes port 3000.
- **Command:** `node server.js`

#### 6.3.3 Local Multi-Service Development (`docker-compose.yml`)
For local developer testing, `docker-compose.yml` mounts source code directories and connects the frontend and backend over a bridge network:
- **Backend Service:** Bound to `http://localhost:8080` with hot-reloading volume mounts.
- **Frontend Service:** Bound to `http://localhost:3000` with `NEXT_PUBLIC_BACKEND_URL=http://localhost:8080`.


---

## 7. API Reference Specification

All endpoints are implemented in `backend/main.py` and validated via automated integration tests in `tests/test_api_endpoints.py`.

### 7.1 Health & Readiness Probe
```http
GET /health
GET /api/health
```

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "Lienmark E&O Clearance Change Control",
  "provenance": "Google AntiGravity (Agentic Cinema Approved Toolchain)",
  "track": "Parallel Track ($15,000 Prize Pool)",
  "integrations": {
    "gemini": "configured",
    "parallel_search": "configured",
    "agent_platform": "Google Cloud Agent Builder / ADK"
  },
  "policy_version": "E&O-2026.1-DEVPOST"
}
```

---

### 7.2 Version Fixtures
```http
GET /api/fixtures
```
Returns the baseline V7 and V8 production versions and 12 canonical V7 claims.

#### Response (200 OK)
```json
{
  "v7_version": {
    "version_id": "v7",
    "project_id": "proj_blockbuster_cinema",
    "label": "Shadows Over Broadway - Locked Script v7",
    "created_at": "2026-09-04T12:00:00Z",
    "content_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
    "parent_version_id": null,
    "source_type": "screenplay"
  },
  "v8_version": {
    "version_id": "v8",
    "project_id": "proj_blockbuster_cinema",
    "label": "Shadows Over Broadway - Production Revision v8",
    "created_at": "2026-09-04T14:30:00Z",
    "content_hash": "f9e8d7c6b5a43210fedcba9876543210",
    "parent_version_id": "v7",
    "source_type": "screenplay"
  },
  "v7_claims": [
    {
      "use_id": "use_v7_prop_vintage_telephone",
      "key": "prop_vintage_telephone",
      "scene": "Scene 04 - Detective Office",
      "asset_type": "prop",
      "description": "1950s Western Electric Rotary Phone prop on mahogany desk.",
      "prominence": "Incidental background set dressing, 4s",
      "status": "APPROVED"
    }
  ]
}
```

---

### 7.3 Execute Clearance Drift Analysis
```http
POST /api/drift/compare
```
Triggers the full multi-step agentic workflow: script delta analysis, invalidation engine evaluation, targeted Parallel searches, and Gemini clearance briefings.

#### Response (200 OK)
```json
{
  "run_id": "run_9a12bc34",
  "base_version": "v7",
  "target_version": "v8",
  "total_claims": 12,
  "carried_forward_count": 10,
  "reopened_count": 2,
  "claims": [
    {
      "stable_lineage_key": "poster_noir_detective_magazine",
      "asset_type": "artwork",
      "description": "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
      "scene": "Scene 42 - 00:44:12",
      "prominence": "Featured close-up focal shot with dialogue, 14s",
      "state": "stale",
      "reason_code": "CREATIVE_CONTEXT_ALTERED",
      "revalidation_action": "revalidate",
      "evidence": {
        "provider": "Parallel",
        "source_title": "US Copyright Office Historical Catalog - Renewal Records",
        "source_url": "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective",
        "excerpt": "Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.",
        "stance": "supporting",
        "latency_ms": 138.2,
        "call_id": "prl_call_882910_poster"
      }
    },
    {
      "stable_lineage_key": "music_cue_midnight_serenade",
      "asset_type": "music",
      "description": "'Midnight Serenade' jazz composition melody.",
      "scene": "Scene 18 - 00:19:40",
      "prominence": "Background jazz trio performance in speakeasy, 20s",
      "state": "stale",
      "reason_code": "EXTERNAL_EVIDENCE_SHIFT",
      "revalidation_action": "revalidate",
      "evidence": {
        "provider": "Parallel",
        "source_title": "ASCAP ACE Repertory & Billboard Rights Bulletin",
        "source_url": "https://ascap.com/ace-title-search/midnight-serenade-9921",
        "excerpt": "Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC...",
        "stance": "contradictory",
        "latency_ms": 165.4,
        "call_id": "prl_call_993012_music"
      }
    }
  ],
  "counsel_briefings": {
    "poster_noir_detective_magazine": {
      "claim_id": "poster_noir_detective_magazine",
      "asset_name": "poster_noir_detective_magazine",
      "counsel_summary": "Scene 42 focal dialogue escalation invalidates de minimis defense, but US Copyright Office records retrieved by Parallel confirm 1946 registration lapsed without renewal in 1974. Cover art is public domain.",
      "parallel_evidence_stance": "SUPPORTING",
      "suggested_counsel_action": "Re-attest as APPROVED under Public Domain doctrine; attach LOC registration excerpt to exceptions schedule.",
      "confidence": 0.96
    }
  },
  "execution_traces": [
    {
      "step_name": "version_ingestion",
      "component": "LienmarkEngine",
      "status": "SUCCESS",
      "duration_ms": 1.2
    },
    {
      "step_name": "semantic_delta_analysis",
      "component": "Gemini 2.5 Flash",
      "status": "SUCCESS",
      "duration_ms": 38.5
    },
    {
      "step_name": "deterministic_dependency_invalidation",
      "component": "InvalidationEngine",
      "status": "SUCCESS",
      "duration_ms": 0.8
    },
    {
      "step_name": "parallel_targeted_search_poster_noir_detective_magazine",
      "component": "Parallel Search API",
      "status": "SUCCESS",
      "duration_ms": 142.5
    }
  ],
  "total_duration_ms": 182.9
}
```

---

### 7.4 Record Human Counsel Re-Attestation
```http
POST /api/review/attest
Content-Type: application/json
```

#### Request Payload
```json
{
  "decision_id": "dec_poster_noir",
  "stable_lineage_key": "poster_noir_detective_magazine",
  "version_id": "v8",
  "new_status": "approved",
  "counsel_rationale": "Artwork verified in public domain via Library of Congress renewal records retrieved by Parallel Search; non-infringing.",
  "reviewer_name": "Sarah Jenkins, Esq. (Clearance Counsel)"
}
```

#### Response (200 OK)
```json
{
  "status": "recorded",
  "stable_lineage_key": "poster_noir_detective_magazine",
  "new_status": "approved",
  "rationale": "Artwork verified in public domain via Library of Congress renewal records retrieved by Parallel Search; non-infringing."
}
```

---

### 7.5 Generate Form E&O-2026 Exceptions Schedule
```http
GET /api/reports/exceptions
```

#### Response (200 OK)
```json
{
  "schedule_id": "sched_proj_blockbuster_cinema_v8_1725498800",
  "project_id": "proj_blockbuster_cinema",
  "project_name": "Lienmark Production Digital Twin",
  "target_version_id": "v8",
  "base_version_id": "v7",
  "generated_at": "2026-09-04T15:00:00Z",
  "policy_version": "E&O-2026.1-DEVPOST",
  "total_claims": 12,
  "carried_forward_count": 10,
  "reopened_count": 2,
  "re_attested_count": 1,
  "unresolved_exception_count": 1,
  "items": [
    {
      "stable_lineage_key": "poster_noir_detective_magazine",
      "asset_type": "artwork",
      "description": "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
      "scene_or_timecode": "Scene 42 - 00:44:12",
      "v7_decision_status": "APPROVED",
      "v8_evaluation_state": "re_attested",
      "invalidation_reason": "CREATIVE_CONTEXT_ALTERED",
      "counsel_action": "Re-attested by Sarah Jenkins, Esq. (Clearance Counsel): Artwork verified in public domain via Library of Congress renewal records retrieved by Parallel Search; non-infringing.",
      "evidence_citations": [
        {
          "source_title": "US Copyright Office Historical Catalog - Renewal Records",
          "source_url": "https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective",
          "excerpt": "Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.",
          "provider": "Parallel"
        }
      ]
    },
    {
      "stable_lineage_key": "music_cue_midnight_serenade",
      "asset_type": "music",
      "description": "'Midnight Serenade' jazz composition melody.",
      "scene_or_timecode": "Scene 18 - 00:19:40",
      "v7_decision_status": "APPROVED",
      "v8_evaluation_state": "exception",
      "invalidation_reason": "EXTERNAL_EVIDENCE_SHIFT",
      "counsel_action": "Marked as UNRESOLVED EXCEPTION by Sarah Jenkins, Esq. (Clearance Counsel): Vanguard Media copyright claim active; cue excluded from final master mix.",
      "evidence_citations": [
        {
          "source_title": "ASCAP ACE Repertory & Billboard Rights Bulletin",
          "source_url": "https://ascap.com/ace-title-search/midnight-serenade-9921",
          "excerpt": "Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC...",
          "provider": "Parallel"
        }
      ]
    }
  ]
}
```

---

## 8. Verification & Test Suite Summary

Lienmark’s technical integrity is validated through an automated test suite executed via `pytest`. All 10 tests execute synchronously and pass cleanly:

```text
tests/test_api_endpoints.py::test_health_endpoints                     PASSED [ 10%]
tests/test_api_endpoints.py::test_fixtures_endpoint                     PASSED [ 20%]
tests/test_api_endpoints.py::test_drift_compare_and_review_flow         PASSED [ 30%]
tests/test_api_endpoints.py::test_dashboard_html                        PASSED [ 40%]
tests/test_e2e_pipeline.py::test_workflow_execution                     PASSED [ 50%]
tests/test_e2e_pipeline.py::test_full_review_to_exceptions_schedule_flow PASSED [ 60%]
tests/test_invalidation_engine.py::test_golden_fixture_counts           PASSED [ 70%]
tests/test_invalidation_engine.py::test_12_to_10_carried_2_reopened     PASSED [ 80%]
tests/test_invalidation_engine.py::test_fail_closed_policy              PASSED [ 90%]
tests/test_invalidation_engine.py::test_exceptions_schedule_reconciliation PASSED [100%]

======================== 10 passed in 3.67s ========================
```

### Coverage Assertions
1. **Fixture Invariants:** Asserts exactly 12 baseline claims in V7 and V8, 12 approved initial decisions, and 12 baseline evidence snapshots.
2. **Deterministic 12 -> 10 + 2:** Proves that exactly 10 claims carry forward, while Item 11 and Item 12 reopen with explicit, distinct reason codes.
3. **Fail-Closed Resilience:** Proves that tampering with inputs or omitting delta objects forces `STALE` status under `FAIL_CLOSED_MISSING_DELTA`.
4. **End-to-End Orchestration:** Validates that `LienmarkWorkflow` records step traces for Gemini, InvalidationEngine, and Parallel Search.
5. **Exceptions Schedule Reconciliation:** Confirms that after counsel re-attestation, the schedule reports 10 carried forward, 1 re-attested, and 1 unresolved exception.
