# Agent Orchestration — Lienmark

This is the deepest technical document in the package — the full agent-by-agent specification, including message contracts, control flow, worked examples, and the reasoning behind every design choice that isn't self-evident. Where `04-prd.md` says *what* the system must do and *why* it matters to the product, this document says *how* it actually works, in enough detail to build from directly.

## 1. Control flow overview

```
[Upload: script/cut]
        │
        ▼
┌───────────────────┐
│   Intake Agent      │  extracts claims, builds minimal search terms
└─────────┬─────────┘
          │  Claim[] (structured, non-identifying)
          ▼
┌───────────────────┐
│  Research Agent     │  parallel-calls Parallel Search API per claim
└─────────┬─────────┘
          │  Finding[] (sourced, per-claim)
          ▼
┌───────────────────┐
│   Ledger Agent       │  append-only write, versioned
└─────────┬─────────┘
          │  LedgerEntry[] (immutable)
          ▼
┌───────────────────┐
│ Risk Scoring Agent  │  deterministic scoring + conflict arbitration
└─────────┬─────────┘
          │  RiskScore[] (some flagged for human review)
          ▼
┌───────────────────┐
│   Report Agent       │  final sourced, cited report
└───────────────────┘
```

**Why each arrow is a real message boundary, not just a function call:** agents communicate via structured data contracts (defined per-agent below), not free-text handoffs between LLM calls. This distinction is what makes the Risk Scoring stage genuinely deterministic (§4) — if agents passed unstructured natural-language summaries to each other, the downstream scoring logic would be at the mercy of however the upstream agent happened to phrase its output on a given run, reintroducing exactly the non-determinism the hackathon's own language explicitly asks us to avoid (see `01-hackathon-scope.md` §2). Structured contracts also make the whole pipeline independently testable agent-by-agent, which is what makes `tests/test_risk_scoring_determinism.py` and `tests/test_ledger_immutability.py` (see `08-directory-structure.md`) possible to write at all — you can't unit-test a boundary that doesn't have a defined shape.

## 2. Intake Agent

**Responsibility:** turn an unstructured script or cut into a structured, minimal, non-identifying claim list.

**Input:** raw document (PDF/text) or edit timeline (EDL/XML-style structured input)

**Output contract:**
```json
{
  "production_id": "string",
  "claims": [
    {
      "claim_id": "string",
      "type": "music | footage | brand | real_person | genai_flag | other",
      "scene_ref": "string",
      "extracted_description": "string — short, non-identifying",
      "needs_clarification": "boolean"
    }
  ]
}
```

**Worked example, to make the extraction behavior concrete:**

Given this script excerpt:
> *MARIA turns up the radio. "Bohemian Rhapsody" by Queen fills the car as she drives toward the cliff, tears streaming down her face. On the dashboard, a half-empty bottle of Jack Daniel's rattles with each bump in the road.*

The Intake Agent should produce **two** distinct claims, not one blended extraction:
```json
[
  {
    "claim_id": "clm_001",
    "type": "music",
    "scene_ref": "p.34, INT. CAR - NIGHT",
    "extracted_description": "song 'Bohemian Rhapsody' by Queen — sync licensing status",
    "needs_clarification": false
  },
  {
    "claim_id": "clm_002",
    "type": "brand",
    "scene_ref": "p.34, INT. CAR - NIGHT",
    "extracted_description": "Jack Daniel's brand shown on-screen — trademark/product placement risk",
    "needs_clarification": false
  }
]
```

Notice what's deliberately **not** in either `extracted_description`: the emotional context (tears, driving toward a cliff), the character name, or the narrative stakes of the scene. This is the confidentiality requirement (`04-prd.md` §5.6) being applied concretely — everything needed to research the *rights* question is present; everything that would reveal plot content to a third party is stripped out.

**Key behaviors:**
- **Multimodal extraction via Gemini** — can read a script PDF directly, with no separate OCR or parsing pipeline needed. This is a genuine build-time saving worth calling out in the pitch as an example of effectively using the required Google Cloud technology, not just a convenience.
- **The confidentiality constraint is a hard requirement, not a style guideline.** Enforce it with an actual length/content check on write (e.g., reject or flag any `extracted_description` exceeding roughly 15-20 words, or containing character names beyond what's needed to disambiguate a claim), not merely as an instruction inside the extraction prompt that a model could ignore on an unusual input. Prompts are guidance; validation checks are guarantees.
- **Ambiguous input handling:** if a claim can't be confidently typed or minimally described — for instance, a vague stage direction like *"a popular song plays"* with no title given — the agent should set `needs_clarification: true` and `type: other` rather than guessing a specific song and presenting a confident wrong answer downstream. This behavior is deliberately borrowed from the "Autopilot Agent" pattern of handling ambiguous real-world input gracefully rather than assuming clean, well-formatted data (see `04-prd.md` §5.1 for the full reasoning). Worth deliberately testing this path with an intentionally vague input before the final demo recording, to confirm the graceful-degradation behavior actually holds rather than just being a documented intention that was never verified.

## 3. Research Agent

**Responsibility:** the hackathon-required integration point. For each claim, issue a live call to Parallel's Search API and return sourced findings.

**Input:** `Claim[]` from the Intake Agent

**Output contract:**
```json
{
  "findings": [
    {
      "finding_id": "string",
      "claim_id": "string",
      "source_url": "string — required, non-null",
      "source_snippet": "string",
      "ownership_status": "clear | disputed | unknown | licensing_required",
      "parallel_query": "string — the actual query sent",
      "call_status": "success | failed | timeout",
      "retrieved_at": "timestamp"
    }
  ]
}
```

**Key behaviors:**
- **Parallelized, per-claim calls — not one blended query.** This matters for two independent reasons: technically, it's the only way to keep each finding traceable back to a specific claim (a requirement in `06-data-schema.md` §1.2); and for the demo, judges need to see N distinct, live calls happening, not one aggregate call that's harder to visually attribute to individual claims on screen.
- **Integration method:** the official `parallel-web` SDK (Python), calling the Search API directly. This must be a real, imported, callable function in the submitted repo — see `backend/agents/research/parallel_client.py` in `08-directory-structure.md`, which is deliberately isolated into its own file specifically so a judge can find and verify it quickly.
- **Failure handling:** on a timeout or API failure, the agent writes a finding with `call_status: failed` and `ownership_status: unknown`, rather than raising an unhandled exception that would kill the entire pipeline run. This is deliberately the moment worth triggering on camera during the demo — see `05-pitch-deck.md`'s shot list and `07-env-vars.md` §2's `DEMO_MODE` flag, which enables a reliable, repeatable way to simulate this failure for recording purposes rather than hoping a real timeout happens to occur during a live take.

**Example call shape** (illustrative — confirm exact current parameter names and method signatures against `docs.parallel.ai` before implementation, since SDK interfaces evolve):
```python
from parallel import Parallel

client = Parallel(api_key=settings.PARALLEL_API_KEY)

def research_claim(claim: Claim) -> Finding:
    try:
        result = client.search(
            query=claim.extracted_description,
            # confirm current parameter names against docs.parallel.ai before build —
            # e.g. result-count limits, freshness/recency filters if available,
            # and whether a domain-allowlist parameter exists that could be useful
            # for prioritizing authoritative sources like copyright registries
        )
        return Finding.from_search_result(claim.claim_id, result)
    except (TimeoutError, ParallelAPIError):
        return Finding.failed(claim.claim_id)
```

**Engineering the demo's conflicting-sources claim:** per `02-mvp-scope.md` §2.2, at least one claim in the demo set must genuinely return conflicting findings from two sources. In practice, this likely means either (a) selecting a real claim ahead of time, through manual research, that's known to have genuinely disputed public information (an obscure song with conflicting rights-holder claims online, for instance), or (b) issuing two separate, deliberately differently-worded queries for the same claim and using whichever combination reliably surfaces disagreement. Option (a) is more honest to the "real live search" spirit of the requirement and should be preferred if a suitable real example can be found during demo-data preparation; option (b) is an acceptable fallback if time runs short, but should be disclosed honestly in the demo narration rather than presented as if it happened naturally.

## 4. Ledger Agent

**Responsibility:** write every claim and finding to an append-only, versioned record. This agent's write behavior is the literal, code-level implementation of the product's entire governance thesis — see `04-prd.md` §2.2 and §5.5.

**Input:** `Claim[]` + `Finding[]`

**Output contract:**
```json
{
  "ledger_entries": [
    {
      "entry_id": "string",
      "claim_id": "string",
      "finding_id": "string | null",
      "version": "integer — increments per claim, never reused",
      "status": "pending | cleared | flagged | needs_human_review",
      "superseded_by": "string | null",
      "written_at": "timestamp",
      "written_by_agent": "string"
    }
  ]
}
```

**Key behaviors:**
- **Hard invariant: create-only, enforced at the storage layer.** Firestore security rules restrict this agent's service account to `create` operations only on the `ledger_entries` collection — see `06-data-schema.md` §3 for the actual rule and `tests/test_ledger_immutability.py` for how this gets verified, not just asserted.
- **Delta-based retrieval, for memory efficiency at scale.** When a production is re-evaluated (e.g., before a distribution deal closes, months after the initial clearance run), the Ledger Agent should expose a query path that returns only ledger entries newer than the last check-in, rather than the full history every time. This directly implements the "recall critical memories within limited context windows" pattern borrowed from memory-focused agent architectures (see `04-prd.md` §5.5 for the full reasoning) — as a production's ledger history grows over months of re-checks, this is what keeps re-evaluation fast and cheap rather than degrading linearly with accumulated history.
- **Versioning, never deletion.** If a claim's status changes — new research contradicts an old finding, a dispute surfaces after initial clearance — write a new entry with an incremented `version`, and set `superseded_by` on the prior entry to point at it. See the full worked example of this pattern in `06-data-schema.md` §2, under `ledger_entries`. The complete history remains permanently queryable; nothing is ever silently overwritten or lost.

## 5. Risk Scoring Agent

**Responsibility:** convert findings into a deterministic, explainable risk score, and arbitrate when sources genuinely conflict.

**Input:** `LedgerEntry[]`

**Output contract:**
```json
{
  "risk_scores": [
    {
      "score_id": "string",
      "claim_id": "string",
      "confidence": "float 0.0-1.0",
      "conflict_detected": "boolean",
      "conflict_sources": ["string — source_urls, if any"],
      "scoring_method": "string — named rule applied",
      "route_to_human_review": "boolean"
    }
  ]
}
```

**Key behaviors:**

**Determinism requirement (explicit, hackathon-required — see `01-hackathon-scope.md` §2, "a deterministic, multi-step agent").** Scoring logic must be rule-based, operating over LLM-extracted facts — not itself a freehand LLM judgment where "how confident are you" is answered by a model's variable, unreproducible output. A concrete rule shape worth implementing:

```python
def compute_confidence(finding: Finding, source_authority_weight: float,
                         recency_days: int, corroboration_count: int) -> float:
    """
    Deterministic scoring function — same inputs always produce the same output.
    NOT an LLM call. This is the literal answer to 'how do we make this
    deterministic' — the extraction upstream can be flexible and LLM-driven;
    this function cannot be.
    """
    recency_factor = max(0, 1 - (recency_days / 365))  # fresher sources score higher
    base_score = (source_authority_weight * 0.5
                  + recency_factor * 0.3
                  + min(corroboration_count / 3, 1.0) * 0.2)
    return round(base_score, 2)
```

The exact weights and formula shape here are illustrative and should be tuned based on what actually produces sensible-looking scores against real demo data — the important, non-negotiable property is that the function is pure and reproducible, not that these specific coefficients are correct.

**Conflict arbitration — the demo's centerpiece mechanic.** When the Research Agent surfaces multiple findings for the same claim with different `ownership_status` values, this agent must not silently pick one and discard the other. It weighs source authority, recency, and corroboration (the same signals as the confidence function above), produces a single verdict, and — critically — logs both conflicting sources explicitly in `conflict_sources` rather than hiding the disagreement. This is the concrete implementation of the "measurable efficiency gain over single-agent baseline" framing borrowed from multi-agent collaboration hackathon patterns (see `04-prd.md` §5.4): the demo should be able to show, side by side, what a naive single-pass agent would have surfaced and stopped at, versus what the arbitration step catches and explains. See `05-pitch-deck.md`'s demo shot list, 1:45-2:10 window, for exactly how this gets shown on camera — this is flagged there as the single most concrete "Quality of the Idea" moment in the entire submission, and it should not be cut under time pressure even if other parts of the demo need to be trimmed.

**Human-in-the-loop threshold.** `route_to_human_review = true` when `confidence < RISK_CONFIDENCE_THRESHOLD` (env var, default 0.7 — see `07-env-vars.md` §2) or when `conflict_detected = true`. No production-critical claim should ever auto-resolve purely on the basis of low confidence — this is a deliberate design choice appropriate for a compliance-facing product, not a limitation of the current technology that a future version should aim to eliminate. Building this in from the start, rather than adding it later after a skeptical buyer asks "what happens when the AI isn't sure," is both more honest and a stronger product story.

## 6. Report Agent

**Responsibility:** produce the final, sourced, human-readable clearance report — the actual artifact a real buyer would need to see and trust.

**Input:** `RiskScore[]` + `LedgerEntry[]` + `Finding[]`

**Output contract:**
```json
{
  "report_id": "string",
  "production_id": "string",
  "generated_at": "timestamp",
  "overall_risk_summary": "string",
  "cleared_claims": [ { "claim_id", "summary", "source_url" } ],
  "flagged_claims": [ { "claim_id", "summary", "source_url", "risk_reason" } ],
  "pending_review_claims": [ { "claim_id", "summary", "reason_for_review" } ]
}
```

**Key behaviors:**
- **No unsourced verdicts, anywhere, ever.** Every claim in `cleared_claims` and `flagged_claims` must carry a `source_url` traceable back to a real Research Agent finding — this is the single most trust-building detail visible to a judge or a real insurer reviewing the output, and it costs nothing extra to build correctly since the data already exists upstream in the pipeline by the time it reaches this agent.
- **Clear three-way separation** (cleared / flagged / pending review) — this is what makes the output usable by a non-technical buyer (an insurer's or bond company's reviewer scanning the report in seconds) rather than only legible to the engineering team that built the system.

## 7. Orchestration implementation notes

- **Built on Google Cloud Agent Builder / Gemini Enterprise Agent Platform**, per the hackathon's core requirement (see `01-hackathon-scope.md` §2). Within that platform, there are two reasonable implementation paths worth weighing deliberately rather than defaulting into one:
  - **Native ADK/Agent Builder orchestration patterns** — a tighter fit with "visibly using the required platform," which may matter for how legible the Google Cloud integration is to a judge doing a fast review
  - **LangGraph on top of Gemini** — gives more explicit control over state transitions between agents, which matters specifically for the Ledger Agent's gating behavior: the Report Agent must never be allowed to read anything the Ledger Agent hasn't yet finalized, and LangGraph's explicit state-machine model makes that guarantee easier to enforce and easier to reason about than an implicit orchestration pattern. If the team has LangGraph experience already, this is likely the better choice for correctness; if not, the ramp-up cost within a six-week window is a real factor against it.
- **Per-agent service accounts** (see `07-env-vars.md` §4) are not an IAM nicety layered on afterward — they are the literal, code-level implementation of the "Studio Head enforcing Cloud IAM security" framing from the hackathon's own promotional language (see `01-hackathon-scope.md` §6.4). Worth surfacing this explicitly in the pitch narration, not leaving it as an implementation detail judges might miss if it isn't called out.
- **Testing determinism as an actual test, not just a design claim.** `tests/test_risk_scoring_determinism.py` should run the identical claim/finding input through the Risk Scoring Agent multiple times in a row and assert byte-identical output every time. This converts "our scoring is deterministic" from an assertion in documentation into something independently verifiable by anyone who runs the test suite — including, potentially, a technically thorough judge who clones the repo and runs `pytest` before making a final decision.
