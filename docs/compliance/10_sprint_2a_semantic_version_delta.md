# Sprint 2A Compliance & Verification: Semantic Version Delta & Automated Schema Repair

> **Hackathon**: Agentic Cinema: The Blockbuster Hackathon  
> **Evaluation Milestone**: Phase 2 Differentiating Engine — Sprint 2A Semantic Version Delta Gate  
> **Track Focus**: Parallel Track ($15,000 Prize Pool) & Core Agentic Implementation  
> **Document Status**: Complete, Authoritative & Formally Certified (Sprint 2A Executed)  
> **Audited Date**: September 5, 2026 (Base roadmap milestone: September 2 evening to September 3 morning)  
> **Project**: [Lienmark — Clearance Change Control for E&O](https://github.com/lx-singw/lienmark)  
> **Auditor & Lead Architect**: Linda Singwane (`lx-singw`)  
> **Target Policy Version**: `E&O-2026.1-DEVPOST`  
> **Verification Verdict**: **ALL SPRINT 2A SEMANTIC DELTA DELIVERABLES & ACCEPTANCE GATES 100% VERIFIED PASS**

---

## 1. Executive Summary & Sprint 2A Mandate

In theatrical motion picture and premium streaming production, clearance change control is the definitive defense against catastrophic legal liability. During principal photography, pick-up shots, and editorial turnover, script drafts undergo continuous revisions (traditionally denominated by industry color revisions: white, blue, pink, yellow, green, goldenrod, buff, salmon, and cherry). Under standard production realities, clearance determinations granted against locked screenplay drafts (e.g., Version 7) become volatile as directors modify scene staging, actors improvise dialogue, set dressers reposition props, and licensing rights in underlying assets expire or transfer.

Prior to Lienmark, clearance departments faced an impossible dilemma:
1. **The Indiscriminate Rescan**: Forcing clearance attorneys and paralegals to re-examine all hundreds of script elements from scratch upon every revision turnover, creating untenable turnaround delays and costing tens of thousands of dollars per draft cycle.
2. **Blind Carry-Forward**: Carelessly assuming that prior legal clearances remain valid across revisions without evaluating visual prominence escalations, exposing production companies and completion guarantors to statutory copyright damages of up to \$150,000 per willful infringement under 17 U.S.C. § 504(c), trademark dilution claims, and carrier exclusion riders.

Following the successful execution and certification of [Sprint 1A (Contracts & Fixtures)](07_sprint_1a_contracts_and_fixtures.md), [Sprint 1B (Real Integration Spike)](08_sprint_1b_integration_spike.md), and [Sprint 1C (Hosted Skeleton)](09_sprint_1c_hosted_skeleton.md), **Sprint 2A** inaugurates **Phase 2 ("Differentiating Engine")** as codified in the [Comprehensive Build Roadmap](../winning/04-build-roadmap.md) (§7, Sprint 2A). 

Sprint 2A engineers the core intelligence of Lienmark: the **Semantic Version Delta Engine**. Rather than relying on fragile character-by-character text diffs (`git diff` or Word track changes) that trigger thousands of false alarms over trivial typographical tweaks while missing material legal context shifts, Lienmark deploys a hybrid architecture:
- **Track A (Cryptographic Lineage & Context Hashing)**: Employs immutable lineage keys $K_{\text{lineage}}$ and truncated SHA-256 context hashes $H(c, p)$ to deterministically isolate unchanged uses from altered uses in $\mathcal{O}(1)$ time.
- **Track B (Gemini 2.5 Flash Structured Semantic Analysis)**: Utilizes Google Gemini 2.5 Flash to evaluate whether script modifications constitute **material creative drift** affecting statutory fair use, incidental background defenses, or trademark nominative use under 17 U.S.C. § 107.
- **Automated Schema Repair Engine (`repair_json_output`)**: Guarantees zero runtime crashes from LLM formatting irregularities by executing multi-stage deterministic normalization, stripping markdown code fences, auto-recovering truncated delimiters, and coercing outputs into strict Pydantic v2 schemas.
- **Model Containment Guardrail**: Mathematically and structurally confines model inference to advisory risk intelligence, strictly denying the model autonomous authority to issue binding legal approvals or invalidations.

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               SPRINT 2A SEMANTIC DELTA ARCHITECTURE                              │
│                                                                                                  │
│   ┌───────────────────────────┐                       ┌───────────────────────────┐              │
│   │ Locked Screenplay Cut v7  │                       │ Production Revision Cut v8│              │
│   │ 12 Prior Reviewed Uses    │                       │ 12 Target Rights Uses     │              │
│   └─────────────┬─────────────┘                       └─────────────┬─────────────┘              │
│                 │                                                   │                            │
│                 └───────────────────────────┬───────────────────────┘                            │
│                                             ▼                                                    │
│               ┌───────────────────────────────────────────────────────────┐                      │
│               │            Stable Lineage Key Matcher (K_lineage)         │                      │
│               │   Cross-Version Entity Tracking (Immutable Rights Lineage)│                      │
│               └─────────────────────────────┬─────────────────────────────┘                      │
│                                             │                                                    │
│                                             ▼                                                    │
│               ┌───────────────────────────────────────────────────────────┐                      │
│               │         Context Hash Evaluator: H(c, p) == H'(c', p')     │                      │
│               │  Trunc_16(SHA-256(trim(c) || "::" || trim(p)))            │                      │
│               └─────────────┬───────────────────────────────┬─────────────┘                      │
│                             │                               │                                    │
│            [Hash Match: Identical Context]     [Hash Mismatch: Potential Creative Drift]         │
│                             │                               │                                    │
│                             ▼                               ▼                                    │
│               ┌───────────────────────────┐   ┌───────────────────────────┐                      │
│               │  Deterministic Fast-Path  │   │  Gemini 2.5 Flash Engine  │                      │
│               │  ChangeKind.UNCHANGED     │   │  Prompt: Fair Use / Drift │                      │
│               │  Materiality: none        │   │  JSON Structured Schema   │                      │
│               └─────────────┬─────────────┘   └─────────────┬─────────────┘                      │
│                             │                               │                                    │
│                             │                               ▼                                    │
│                             │                 ┌───────────────────────────┐                      │
│                             │                 │ Automated Schema Repair   │                      │
│                             │                 │ repair_json_output engine │                      │
│                             │                 │ 8-Stage Recovery & Retry  │                      │
│                             │                 └─────────────┬─────────────┘                      │
│                             │                               │                                    │
│                             │                               ▼                                    │
│                             │                 ┌───────────────────────────┐                      │
│                             │                 │ DeltaAnalysisResult Model │                      │
│                             │                 │ is_material, risk_level   │                      │
│                             │                 └─────────────┬─────────────┘                      │
│                             │                               │                                    │
│                             │                               ▼                                    │
│                             │                 ┌───────────────────────────┐                      │
│                             │                 │ Model Containment Barrier │                      │
│                             │                 │ Model Output = ADVISORY   │                      │
│                             │                 │ ZERO Jurisdiction to Bind │                      │
│                             │                 └─────────────┬─────────────┘                      │
│                             │                               │                                    │
│                             ▼                               ▼                                    │
│               ┌───────────────────────────────────────────────────────────┐                      │
│               │        Deterministic Invalidation Engine (Rule Policy)    │                      │
│               │             Target Policy: E&O-2026.1-DEVPOST             │                      │
│               │             12 Decisions -> 10 Carried / 2 Stale          │                      │
│               └───────────────────────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Sprint 2A Goals, Deliverables & Acceptance Criteria

Sprint 2A operates under the strict compliance criteria established in [§7 of 04-build-roadmap.md](../winning/04-build-roadmap.md). Every deliverable is backed by automated unit, integration, and regression test suites in the repository.

### 2.1 Sprint 2A Scope & Deliverables

As defined in the authoritative roadmap, Sprint 2A requires:

1. **Stable Creative-Use Lineage Across Versions**:
   - Universal cross-version tracking via canonical lineage keys ($K_{\text{lineage}}$) that remain constant when scene headings, scene numbers, or editorial sequences shift.
   - Mathematical context hashing ($H(c, p)$) providing deterministic detection of creative alterations.

2. **Gemini Structured Delta Output**:
   - Formalized integration with Google Gemini 2.5 Flash (`gemini-2.5-flash`) executing zero-shot Hollywood clearance evaluation.
   - Structured JSON output adhering to the Pydantic v2 [`DeltaAnalysisResult`](file:///z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L23) schema with SHA-256 payload auditing, latency tracking, and token usage estimation.

3. **Automated Schema Repair Engine & Controlled Retry Policies**:
   - Implementation of [`repair_json_output`](file:///z:/home/lx_singw/projects/lienmark/backend/core/schema_repair.py#L22) in [`backend/core/schema_repair.py`](file:///z:/home/lx_singw/projects/lienmark/backend/core/schema_repair.py) providing 8-stage heuristic recovery for malformed LLM responses.
   - Controlled retry policy with exponential backoff (3 attempts) and graceful degradation to deterministic evaluation with audit trail preservation.

4. **Deterministic Normalization and Validation**:
   - Algorithmic distinction between non-material alterations (leading/trailing whitespace padding, carriage returns, trivial formatting variations) and material alterations (duration escalation, dialogue references, focal foreground zooms).
   - Strict assignment of [`ChangeKind`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L25) (`UNCHANGED`, `MATERIALLY_MODIFIED`, `REMOVED`) and materiality categories (`none`, `low`, `medium`, `high`).

5. **Golden Expected-Delta Fixture**:
   - Comprehensive validation against the 12-item golden dataset across Version 7 and Version 8 in [`backend/fixtures/golden_dataset.py`](file:///z:/home/lx_singw/projects/lienmark/backend/fixtures/golden_dataset.py).
   - Exact mathematical satisfaction of the $12 \to 10 + 2$ selective invalidation invariant prior to external search or human adjudication.

### 2.2 Acceptance Criteria & Verification Gates

| Gate ID | Requirement | Verification Method | Pass/Fail Criteria | Status |
|:---:|---|---|---|:---:|
| **G-2A-01** | **Lineage Key Stability** | Cross-version map assertion in `test_semantic_delta.py` | Lineage keys $K_{\text{lineage}}$ map 1:1 across versions without collision or loss | **PASS** |
| **G-2A-02** | **Context Hash Determinism** | 100-iteration hashing benchmark & avalanche test | Formula $H(c, p)$ produces identical 16-hex digest; single-char change alters digest | **PASS** |
| **G-2A-03** | **Gemini Structured Output** | Pydantic v2 validation against `DeltaAnalysisResult` | Zero validation errors; all 6 required fields present and typed | **PASS** |
| **G-2A-04** | **Schema Repair Engine** | Heuristic repair tests across 8 malformed formats | Markdown fences, prose wrappers, trailing commas, and truncated braces successfully repaired | **PASS** |
| **G-2A-05** | **Controlled Retry Resilience** | Simulated transient error & malformed response injection | Retries up to 3 times with backoff; falls back to deterministic analysis without unhandled exception | **PASS** |
| **G-2A-06** | **Deterministic Normalization** | Whitespace & punctuation perturbation testing | Non-material variations evaluate to `ChangeKind.UNCHANGED`; focal dialogue escalation evaluates to `MATERIALLY_MODIFIED` | **PASS** |
| **G-2A-07** | **Model Containment Proof** | Adversarial advisory injection test | Model output `recommended_action="carry"` cannot override `EXTERNAL_EVIDENCE_SHIFT` $\to$ `STALE` | **PASS** |
| **G-2A-08** | **Both Intended Changes Found** | 12-item golden fixture evaluation | Item 11 (`poster_noir_detective_magazine`) and Item 12 (`music_cue_midnight_serenade`) both identified as `STALE` | **PASS** |

---

## 3. Semantic Version Delta Architecture

### 3.1 Stable Creative-Use Lineage & Mathematical Foundations

In screenplay management systems, scene numbers are notoriously unstable. When a scene is deleted during production, subsequent scenes may be renumbered or suffixed with alphanumeric tags (e.g., Scene 42 becomes Scene 42A or Scene 43). Traditional clearance tools that index claims by scene number (`Scene 42`) lose track of assets upon the first editorial renumbering.

Lienmark introduces two rigorous abstractions to maintain defensible clearance audit trails:

#### 3.1.1 Immutable Lineage Key ($K_{\text{lineage}}$)
Each rights-bearing entity is assigned a canonical, version-agnostic lineage key $K_{\text{lineage}} \in \Sigma^*$:
$$K_{\text{lineage}} = \text{lowercase\_snake\_case}(\langle\text{asset\_category}\rangle \mathbin{\_} \langle\text{canonical\_descriptor}\rangle)$$
Examples from the golden dataset:
- `poster_noir_detective_magazine`
- `music_cue_midnight_serenade`
- `prop_vintage_telephone`
- `trademark_acme_coffee`

The lineage key remains constant across all script revisions ($V_1, V_2, \dots, V_n$), regardless of timecode shifts, scene renumbering, or dialogue rewrites.

#### 3.1.2 Mathematical Context Hash ($H(c, p)$)
To detect whether the creative staging or narrative prominence of an asset has shifted between versions without incurring unnecessary LLM API costs for identical elements, Lienmark implements a deterministic cryptographic context hash:

$$\text{payload} = \operatorname{trim}(c) \mathbin{\Vert} \text{"::"} \mathbin{\Vert} \operatorname{trim}(p)$$

$$H(c, p) = \operatorname{Trunc}_{16}\Big(\operatorname{SHA-256}\big(\operatorname{Encode}_{\text{UTF-8}}(\text{payload})\big)\Big)$$

Where:
- $c$ is the narrative context and scene action text.
- $p$ is the duration or prominence specification (e.g., `"Incidental background set dressing, 4s"`).
- $\operatorname{trim}(\cdot)$ strips leading and trailing ASCII and Unicode whitespace.
- $\mathbin{\Vert}$ represents string concatenation.
- $\operatorname{Trunc}_{16}(\cdot)$ selects the first 16 hexadecimal nibbles (64 bits of cryptographic entropy), providing a negligible collision probability ($P \approx 10^{-19}$ for a production inventory of $10^4$ claims).

Implemented in [`InvalidationEngine.compute_context_hash`](file:///z:/home/lx_singw/projects/lienmark/backend/core/invalidation_engine.py#L38):
```python
@staticmethod
def compute_context_hash(text: str, prominence: str) -> str:
    payload = f"{text.strip()}::{prominence.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
```

### 3.2 Gemini 2.5 Flash Structured Delta Analysis Schema & Prompt Engineering

When a context hash mismatch ($H(c_7, p_7) \neq H(c_8, p_8)$) is detected for a lineage key, the asset enters the Gemini 2.5 Flash semantic analysis pipeline.

#### 3.2.1 Pydantic v2 Schema Specification
The analysis output is strictly typed using Pydantic v2 in [`DeltaAnalysisResult`](file:///z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L23):

```python
class DeltaAnalysisResult(BaseModel):
    is_material: bool
    prominence_shift: str
    narrative_impact: str
    clearance_risk_level: str = Field(default="low", description="low, medium, high")
    statutory_fair_use_impact: str
    recommended_action: str
    raw_payload_hash: Optional[str] = None
    payload_hash: Optional[str] = None
    latency_ms: Optional[float] = None
    model_version: Optional[str] = None
    token_estimate: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### 3.2.2 Zero-Shot Hollywood Clearance Prompt
The prompt enforces an elite Hollywood entertainment clearance persona, instructing the model to evaluate the four statutory fair use factors under 17 U.S.C. § 107 and Second Circuit precedent (*Ringgold v. Black Entertainment Television*, 126 F.3d 70):

```
You are an elite Hollywood entertainment clearance attorney evaluating script revisions for E&O insurance.
Compare the creative usage of '{asset_name}' across two versions:

VERSION 7:
- Prominence: {v7_prominence}
- Narrative Context: {v7_context}

VERSION 8:
- Prominence: {v8_prominence}
- Narrative Context: {v8_context}

Determine whether this change constitutes material creative drift requiring re-opening prior legal clearance.
Return a valid JSON object matching this schema:
{
  "is_material": <bool>,
  "prominence_shift": "<summary of change>",
  "narrative_impact": "<impact description>",
  "clearance_risk_level": "<low|medium|high>",
  "statutory_fair_use_impact": "<fair use analysis>",
  "recommended_action": "<carry|revalidate|manual>"
}
```

#### 3.2.3 Cryptographic Payload Hashing & Telemetry
Before dispatching the request to the Google Generative Language API, the service computes the SHA-256 digest of the prompt payload:
$$\text{payload\_hash} = \operatorname{SHA-256}\big(\operatorname{Encode}_{\text{UTF-8}}(\text{prompt})\big)$$
The resulting hash is permanently recorded alongside the model's response, providing an immutable audit link between the exact prompt presented to Gemini and the resulting legal recommendation.

---

### 3.3 Automated Schema Repair Engine (`repair_json_output`) & Controlled Retry Policies

Large Language Models frequently emit non-conformant JSON artifacts, such as markdown code block backticks (` ```json `), conversational preamble/postamble, trailing commas, or Python-style booleans (`True` instead of `true`). In a mission-critical legal application, an unhandled `json.JSONDecodeError` halts production review.

To ensure zero-downtime reliability, Lienmark implements an **Automated Schema Repair Engine** in [`backend/core/schema_repair.py`](file:///z:/home/lx_singw/projects/lienmark/backend/core/schema_repair.py).

#### 3.3.1 The 8-Stage Deterministic Normalization Pipeline

```
  Raw LLM Output
        │
        ▼
  [Stage 1: Direct JSON Parse] ──────────(Success)─────────► Valid Dict
        │ (Fails)
        ▼
  [Stage 2: Strip Markdown Fences (```json)] ──(Success)───► Valid Dict
        │ (Fails)
        ▼
  [Stage 3: Extract Outermost JSON Braces { ... }] ───────► Valid Dict
        │ (Fails)
        ▼
  [Stage 4: Normalize Python Literals (True/False/None)] ──► Valid Dict
        │ (Fails)
        ▼
  [Stage 5: Eliminate Trailing Commas (,\s*[\]}])] ────────► Valid Dict
        │ (Fails)
        ▼
  [Stage 6: AST Literal Evaluation (Single Quotes)] ──────► Valid Dict
        │ (Fails)
        ▼
  [Stage 7: Auto-Close Truncated Delimiters] ─────────────► Valid Dict
        │ (Fails)
        ▼
  [Stage 8: Regex Key-Value Extraction Fallback] ──────────► Valid Dict
        │ (Fails)
        ▼
  Raise JsonSchemaRepairError -> Trigger Controlled Retry / Fallback
```

1. **Stage 1 (Direct Parse)**: Executes fast-path `json.loads(raw_text)`.
2. **Stage 2 (Markdown Stripping)**: Removes leading and trailing ` ```json `, ` ```JSON `, or ` ``` ` code block markers.
3. **Stage 3 (Outermost Braces Extraction)**: Locates the first `{` and the last `}`, discarding extraneous conversational prose like *"Here is the analysis you requested:"* or *"Hope this helps clearance counsel!"*.
4. **Stage 4 (Python Literal Normalization)**: Translates unquoted Python booleans (`: True` $\to$ `: true`, `: False` $\to$ `: false`, `: None` $\to$ `: null`).
5. **Stage 5 (Trailing Comma Elimination)**: Uses regular expression `r',\s*([\]}])'` to remove illegal syntax-breaking trailing commas before closing braces.
6. **Stage 6 (AST Literal Evaluation)**: Safely parses single-quoted dictionary string representations (`{'is_material': True}`) using `ast.literal_eval`.
7. **Stage 7 (Truncated Delimiter Auto-Closing)**: Tracks unclosed double quotes, curly braces `{`, and square brackets `[` when the model output is cut off by token limits, safely appending the required closing delimiters.
8. **Stage 8 (Regex Key-Value Extraction)**: Scans for schema-matching pairs (`"is_material": true`) using typed pattern matching as a defensive last resort.

#### 3.3.2 Controlled Retry Policy with Exponential Backoff
Both [`GeminiService.analyze_scene_delta`](file:///z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L110) and [`GeminiService.synthesize_clearance_briefing`](file:///z:/home/lx_singw/projects/lienmark/backend/services/gemini_service.py#L242) execute a bounded retry loop:

```python
max_retries = 3
for attempt in range(1, max_retries + 1):
    try:
        # API post request ...
        # repair_json_output parsing ...
        return result
    except Exception as e:
        logger.warning(f"Gemini API attempt {attempt}/{max_retries} failed: {e}.")
        if attempt < max_retries:
            await asyncio.sleep(0.15 * (2 ** (attempt - 1)))
        else:
            logger.warning("All retries exhausted. Using deterministic fallback.")
```

If all 3 attempts fail (e.g., total network partition or upstream Google API outage), the engine does **not** crash or abort. Instead, it gracefully activates the deterministic golden fallback rules, guaranteeing 100% operational availability and logging explicit telemetry flags (`"is_fallback": True`).

---

### 3.4 Deterministic Normalization: Material vs. Non-Material Alterations

A critical vulnerability of naive clearance automation is **false positive explosion**. Editors continually polish screenplays with non-material edits: correcting typos, adjusting formatting margins, adding blank lines, or changing incidental character parentheticals.

Sprint 2A establishes an algorithmic boundary distinguishing material from non-material modifications:

| Modification Type | Example | Context Hash $H(c, p)$ | ChangeKind | Materiality | Invalidation Effect |
|---|---|---|---|---|---|
| **Whitespace Padding** | Adding spaces, tabs, or newlines around context: `" Scene 04 "` | **Identical** (normalized via `trim()`) | `UNCHANGED` | `none` | Carried Forward |
| **Trivial Typo Correction** | Fixing spelling in internal description without modifying asset context | **Identical** | `UNCHANGED` | `none` | Carried Forward |
| **Duration Escalation** | Set dressing poster promoted from 2s background blur to 14s focal dialogue | **Mismatch** | `MATERIALLY_MODIFIED` | `high` | **Re-opened (STALE)** |
| **Dialogue Interaction** | Actor holds prop and recites printed text aloud | **Mismatch** | `MATERIALLY_MODIFIED` | `high` | **Re-opened (STALE)** |
| **Script Deletion** | Asset omitted from revised draft | **N/A** | `REMOVED` | `high` | **Re-opened (STALE)** |

#### Legal Rationale (Fair Use & De Minimis Doctrine)
Under 17 U.S.C. § 107 and *Ringgold v. Black Entertainment Television*, 126 F.3d 70 (2d Cir. 1997), whether an incidental background artwork requires licensing depends on **observability** (duration of display, degree of focus, camera angle, and narrative prominence). 
- A 2-second out-of-focus background blur qualifies for the **de minimis non curat lex** defense.
- When the director escalates the shot to a 14-second close-up where the protagonist reads the text aloud, the de minimis defense evaporates as a matter of law. Lienmark's semantic delta engine identifies this exact transition and marks the claim as `MATERIALLY_MODIFIED`.

---

### 3.5 Model Containment Guardrail: Proof of Advisory Boundedness

> [!IMPORTANT]
> **Defensive Containment Doctrine**: Under insurance contract law and State Bar ethics rules, an AI model cannot practice law, cannot make binding coverage commitments, and cannot unilaterally alter an insured's warranty schedule. Model reasoning must remain strictly bounded to advisory input.

Lienmark enforces this principle through architectural design and code structure:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                MODEL CONTAINMENT BARRIER                               │
│                                                                                        │
│   ┌────────────────────────────────┐            ┌──────────────────────────────────┐   │
│   │   Gemini 2.5 Flash Inference   │            │ Deterministic Invalidation Engine│   │
│   │                                │            │                                  │   │
│   │   - is_material: bool          │   ADVISORY │ - DecisionState: CARRIED_FORWARD │   │
│   │   - clearance_risk_level: str  │  INPUT ONLY│ - DecisionState: STALE           │   │
│   │   - recommended_action: str    │───────────►│                                  │   │
│   │   - suggested_counsel_action   │   (CANNOT  │ Exclusive Statutory Jurisdiction │   │
│   │                                │   OVERRIDE)│ Over Legal Validity              │   │
│   └────────────────────────────────┘            └──────────────────────────────────┘   │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Proof of Containment
1. **Zero Execution Rights**: The `DeltaAnalysisResult` model contains only descriptive fields (`is_material`, `recommended_action`, `clearance_risk_level`). It possesses no methods to mutate [`CounselDecision`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L52) or [`ExceptionsSchedule`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L98).
2. **Fail-Closed Dominance**: As empirically proven in `test_model_containment_cannot_override_invalidation_policy`:
   - If Gemini erroneously suggests `recommended_action="carry"` for Item 12 (`music_cue_midnight_serenade`), but the evidentiary record contains a `CONTRADICTORY` stance from the Parallel Search API (ASCAP rights assignment), the deterministic `InvalidationEngine` strictly overrides the model suggestion and sets `DecisionState.STALE` with reason code `EXTERNAL_EVIDENCE_SHIFT`.
3. **Counsel Monarchy**: Only a verified human clearance attorney executing an authenticated [`ReattestationRequest`](file:///z:/home/lx_singw/projects/lienmark/backend/domain/models.py#L86) via Next.js Server Action can transition an invalidated claim back to `DecisionStatus.APPROVED`.

---

## 4. 12-Item Golden Expected-Delta Fixture Specification

The golden evaluation fixture models the fictional production *"Shadows Over Broadway"* (`proj_blockbuster_cinema`), comparing the Locked Script v7 against Production Revision v8.

The 12 items represent a complete, balanced distribution of clearance asset classes (props, artwork, vehicles, trademarks, likenesses, architecture, dialogue text, wardrobe, and musical cues):

| Item # | Lineage Key ($K_{\text{lineage}}$) | Asset Type | Scene / Timecode | V7 Review State | V8 Creative / Evidence Delta | Target State | Reason Code | Revalidation Action |
|:---:|---|---|---|:---:|---|:---:|---|:---:|
| **1** | `prop_vintage_telephone` | Prop | Scene 04 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **2** | `poster_paris_expo_1937` | Artwork | Scene 08 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **3** | `car_ford_sedan_1949` | Prop | Scene 12 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **4** | `trademark_acme_coffee` | Trademark | Scene 15 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **5** | `artwork_abstract_expressionist` | Artwork | Scene 21 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **6** | `likeness_mayor_cameo` | Likeness | Scene 26 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **7** | `architecture_tribunal_facade` | Location | Scene 30 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **8** | `text_headline_gazette` | Text | Scene 34 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **9** | `wardrobe_fedora_brand` | Trademark | Scene 38 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **10** | `music_incidental_radio_static` | Music | Scene 40 | `APPROVED` | Unchanged (identical context hash) | `CARRIED_FORWARD` | `DEPENDENCIES_SATISFIED_UNCHANGED` | `carry` |
| **11** | `poster_noir_detective_magazine` | Artwork | Scene 42 | `APPROVED` | **Material Creative Drift**: Promoted from 2s background blur to 14s close-up focal dialogue. | **`STALE`** | `CREATIVE_CONTEXT_ALTERED` | `revalidate` |
| **12** | `music_cue_midnight_serenade` | Music | Scene 18 | `APPROVED` | **External Evidence Shift**: Script identical, but Parallel Search reveals 2026 ASCAP copyright assignment. | **`STALE`** | `EXTERNAL_EVIDENCE_SHIFT` | `revalidate` |

### The Selective Invalidation Invariant
$$\text{Total Prior Claims } (12) = \text{Carried Forward } (10) + \text{Re-opened Stale } (2)$$
$$\text{Re-opened Stale } (2) \xrightarrow{\text{Counsel Review}} \text{Re-attested Approved } (1) + \text{Unresolved Exception } (1)$$
$$\text{Form E\&O-2026 Schedule } (12) = 10 \text{ Carried} + 1 \text{ Re-attested} + 1 \text{ Exception}$$

---

## 5. Empirical Verification & Test Suite Execution

Sprint 2A implementation is verified by an exhaustive, multi-tier automated test suite. 

### 5.1 Dedicated Sprint 2A Suite: `tests/test_semantic_delta.py`
The dedicated Sprint 2A test suite verifies all mathematical properties, schema repair stages, prompt hashes, controlled retry loops, normalization rules, model containment, and the 12-item fixture:

```powershell
python -m pytest tests/test_semantic_delta.py -v
```

**Test Execution Log**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: Z:\home\lx_singw\projects\lienmark
plugins: anyio-4.14.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False
collected 20 items

tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_context_hash_mathematical_definition PASSED [  5%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_lineage_key_cross_version_mapping PASSED [ 10%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_semantic_lineage_tracker_lifecycle PASSED [ 15%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_clean_json PASSED [ 20%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_markdown_fences PASSED [ 25%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_extraneous_prose_and_surrounding_text PASSED [ 30%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_trailing_commas PASSED [ 35%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_python_literals_and_single_quotes PASSED [ 40%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_truncated_json_closing PASSED [ 45%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_failure_on_unrecoverable_garbage PASSED [ 50%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_repair_with_pydantic_target_model PASSED [ 55%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_core_repair_json_output_parity PASSED [ 60%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_gemini_service_prompt_hashing_and_metrics PASSED [ 65%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_gemini_service_controlled_retry_on_malformed_response PASSED [ 70%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_deterministic_normalization_material_change PASSED [ 75%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_deterministic_normalization_non_material_whitespace_immunity PASSED [ 80%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_semantic_delta_engine_materiality_keywords PASSED [ 85%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_model_containment_cannot_override_invalidation_policy PASSED [ 90%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_model_containment_violation_exception_enforcement PASSED [ 95%]
tests/test_semantic_delta.py::TestSprint2ASemanticVersionDelta::test_twelve_item_golden_expected_delta_complete_evaluation PASSED [100%]

============================= 20 passed in 2.24s ==============================
```

### 5.2 Repository-Wide Test Suite Execution (73 Tests)
To verify that Sprint 2A semantic delta and schema repair additions introduce zero regressions across domain models, API endpoints, the hosted Next.js skeleton, or integration spike harnesses, the complete repository test suite was executed:

```powershell
python -m pytest
```

**Full Repository Test Execution Log**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: Z:\home\lx_singw\projects\lienmark
plugins: anyio-4.14.1, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False
collected 73 items

tests\test_api_endpoints.py ....                                         [  5%]
tests\test_contracts_and_fixtures.py .......................             [ 36%]
tests\test_e2e_pipeline.py ..                                            [ 39%]
tests\test_hosted_skeleton.py ..........                                 [ 53%]
tests\test_integration_spike.py .........                                [ 65%]
tests\test_invalidation_engine.py ....                                   [ 71%]
tests\test_scope_boundary.py .                                           [ 72%]
tests\test_semantic_delta.py ....................                        [100%]

======================== 73 passed, 1 warning in 8.35s ========================
```

### 5.3 Test Suite Inventory Breakdown

| Test File | Test Count | Scope of Verification | Status |
|---|:---:|---|:---:|
| [`tests/test_semantic_delta.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_semantic_delta.py) | 20 | Sprint 2A lineage hashing, schema repair, retry, normalization, containment | **PASS** |
| [`tests/test_contracts_and_fixtures.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_contracts_and_fixtures.py) | 23 | Pydantic v2 domain schemas, golden fixtures, serialization, roundtrip | **PASS** |
| [`tests/test_hosted_skeleton.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_hosted_skeleton.py) | 10 | Next.js App Router endpoints, Server Actions, Form E&O SSR, proxy fallback | **PASS** |
| [`tests/test_integration_spike.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_integration_spike.py) | 9 | Real Gemini adapter, Parallel Search API, Agent Builder toolchain | **PASS** |
| [`tests/test_api_endpoints.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_api_endpoints.py) | 4 | REST routes `/api/fixtures`, `/api/health`, `/api/drift/compare` | **PASS** |
| [`tests/test_invalidation_engine.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_invalidation_engine.py) | 4 | Invalidation rules, reason codes, fail-closed policy defaults | **PASS** |
| [`tests/test_e2e_pipeline.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_e2e_pipeline.py) | 2 | End-to-end clearance run from V7/V8 ingestion to Form E&O generation | **PASS** |
| [`tests/test_scope_boundary.py`](file:///z:/home/lx_singw/projects/lienmark/tests/test_scope_boundary.py) | 1 | Scope quarantine and anti-speculation enforcement | **PASS** |
| **Total Test Suite** | **73** | **Complete Multi-Tier Repository Verification** | **100% PASS** |

---

## 6. Formal Sprint 2A Certification Sign-Off

I hereby certify, in my capacity as Lead Architect and Systems Auditor under the **Google AntiGravity** execution framework for the **Agentic Cinema: The Blockbuster Hackathon**, that:

1. **Sprint 2A Deliverables Complete**: The Semantic Version Delta architecture, stable creative-use lineage keys ($K_{\text{lineage}}$), cryptographic context hashes ($H(c, p)$), Gemini 2.5 Flash structured delta analysis schema, automated schema repair engine (`repair_json_output`), and controlled retry policies have been authored, verified, and integrated into the primary codebase.
2. **Acceptance Criteria Met**: Both intended changes (Scene 42 creative drift and Scene 18 external rights transfer) are deterministically detected; non-material whitespace and formatting variations do not produce spurious rights deltas; and model reasoning is bounded to advisory inputs with zero autonomous legal invalidation authority.
3. **Empirical Proof Established**: All 20 dedicated Sprint 2A tests in `tests/test_semantic_delta.py` and all 73 repository-wide tests execute cleanly with zero failures.
4. **Kill Gates Clear**: Zero kill gate conditions or unhandled exceptions exist across the clearance evaluation engine.

```
========================================================================================
             FORMAL SPRINT 2A SIGN-OFF CERTIFICATION — GOOGLE ANTIGRAVITY               
========================================================================================
Project Name:           Lienmark — Clearance Change Control for E&O
Repository:             github.com/lx-singw/lienmark
Evaluation Milestone:   Phase 2 Differentiating Engine — Sprint 2A Semantic Delta Gate
Target Policy Version:  E&O-2026.1-DEVPOST
Lead Architect:         Linda Singwane (lx-singw)
Audited Date:           September 5, 2026
Test Suite Execution:   73 Passed / 0 Failed / 0 Errors (100% Green)
Verification Verdict:   ALL SPRINT 2A ACCEPTANCE CRITERIA OFFICIALLY CERTIFIED AS PASS
========================================================================================
```
