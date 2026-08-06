# Agent Orchestration — Lienmark

This is the deepest technical document in the package — the full agent-by-agent specification, including message contracts, control flow, worked examples, and the reasoning behind every design choice that isn't self-evident. Where `04-prd.md` says *what* the system must do and *why* it matters to the product, this document says *how* it actually works, in enough detail to build from directly.

## 0. A note on what actually makes this agentic, not just automated

Worth addressing directly, because it's the sharpest possible critique of the original five-agent design and it's correct: a pipeline that only runs when a human uploads a file and clicks a button is not agentic at the entry point, regardless of how much autonomous reasoning happens once it's running. Genuine agentic behavior — "goal-driven, reasons about what it observes, takes action with limited step-by-step human instruction" — requires *deciding when to act*, not just reasoning well once told to. §1 below reflects this: the Discovery Agent now sits before Intake specifically to close this gap, not as an afterthought bolted onto a design that was already "done."

## 1. Control flow overview

```
                    ┌──────────────────────┐
                    │   Discovery Agent      │  autonomously decides WHEN to
                    │                        │  trigger a run — new document
                    │                        │  detected, or a re-check
                    │                        │  warranted by an external signal
                    └───────────┬──────────┘
                                │  triggers a run, with either a
                                │  new source document or a
                                │  re-verification target
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

**Why each arrow is a real message boundary, not just a function call:** agents communicate via structured data contracts (defined per-agent below), not free-text handoffs between LLM calls. This distinction is what makes the Risk Scoring stage genuinely deterministic (§6) — if agents passed unstructured natural-language summaries to each other, the downstream scoring logic would be at the mercy of however the upstream agent happened to phrase its output on a given run, reintroducing exactly the non-determinism the hackathon's own language explicitly asks us to avoid (see `01-hackathon-scope.md` §2). Structured contracts also make the whole pipeline independently testable agent-by-agent, which is what makes `tests/test_risk_scoring_determinism.py` and `tests/test_ledger_immutability.py` (see `08-directory-structure.md`) possible to write at all — you can't unit-test a boundary that doesn't have a defined shape.

## 2. Discovery Agent — the genuinely agentic entry point

**Responsibility:** decide *when* a verification run should happen, autonomously — replacing a human-initiated upload as the sole trigger with an agent that reasons about incoming signals and acts on its own judgment.

**Three distinct autonomous behaviors, not two — this was revised after an honest self-check.** An earlier version of this document scoped only §2.2 (autonomous re-verification) for the MVP and deferred all of new-document discovery to Phase 2, reasoning that it required real customer system access. That reasoning conflated two genuinely different things: a full production integration with a real customer's actual systems (which does need Phase 2) and a demo-scale autonomous watcher (which doesn't). Splitting these out:

**2.1 Demo-scale autonomous document watching — MVP scope, and the most important of the three.** A simple, genuinely independent polling loop or webhook listener watches a designated location (a folder, a simple endpoint) and starts a clearance run when a new document appears — with no human clicking a "process this" action to initiate it. The critical implementation requirement, worth stating precisely because it's easy to fake: **this must be a decoupled, independently-running process that would fire identically regardless of what put the file there** — a human, a script, an unrelated automated system. A UI where dragging a file directly invokes the pipeline via an event handler is the same human-triggered pattern with different visual dressing, not a fix. Build an actual watcher (e.g., a lightweight polling loop checking a Cloud Storage bucket or local directory on an interval, or a real webhook endpoint) that is architecturally separate from the act of a file arriving.

**Why this belongs in MVP scope, not deferred, and why it's more important than §2.3 below:** this is the behavior that actually determines whether the demo's *primary, opening action* is agentic or reactive. The re-verification behavior (§2.3) is real and worth keeping, but it's a secondary flourish on a run a human still had to start. This is the one that changes the fundamental shape of the demo's first beat — from "watch a human click upload" to "watch the system notice something on its own." Given the hackathon's own coverage names exactly this distinction as the difference between meeting the brief and missing it entirely (`25-agentic-maturity-roadmap.md` §7), this is not optional polish.

**2.2 Full production system integration — genuinely Phase 2, this part of the original scoping was correct.** Connecting to a real customer's actual document management platform, shared production drive, or script-tracking tool via a managed, secure data pipeline — this is the literal, direct embodiment of the hackathon's own "Technical Producer connecting secure data pipelines via managed MCP servers" framing (`01-hackathon-scope.md` §7.4) at full scale, but it correctly requires a real customer relationship and real system access that doesn't exist yet. The MVP's §2.1 watcher is architecturally the same *pattern* at demo scale — worth stating this connection explicitly in the pitch, since it means the MVP isn't a toy version of a different idea, it's a small, honest instance of the same real capability.

**2.3 Autonomous re-verification, triggered by the world changing.** Still valuable, still in MVP scope, but now correctly positioned as the secondary behavior rather than the only one. It monitors for conditions that should prompt a re-check of an *already-logged* claim, without a human deciding to ask:
- A claim previously routed to `needs_human_review` (per the Risk Scoring Agent, §6) that has sat unresolved past a reasonable window — the agent should proactively flag this as stale, not wait indefinitely for a human to remember it
- A borderline-confidence `clear` or `licensing_required` verdict, where re-running the Research Agent's query periodically could surface new information (a dispute that's since been filed, a license that's since expired) that the original one-time check couldn't have known about
- An external signal relevant to a specific logged claim type — for instance, if the claim taxonomy includes a `genai_flag` claim and a new, relevant legal development occurs (the kind of event already tracked in `14-sources-appendix.md`'s Seedance-dispute research), claims of that type across the ledger could be proactively surfaced for re-review

**Output contract (covers all three behaviors):**
```json
{
  "trigger_id": "string",
  "trigger_type": "new_document_watched | new_document_integrated | scheduled_recheck | signal_triggered_recheck",
  "production_id": "string | null",     // null if this is a genuinely new production
  "source_document_ref": "string | null",  // populated for new_document triggers
  "recheck_claim_ids": ["string"] | null,  // populated for recheck triggers
  "reasoning": "string"                  // a short, logged explanation of WHY this
                                            // agent decided to act now — this reasoning
                                            // trace is itself worth logging to the
                                            // ledger, since "why did the system decide
                                            // to re-check this" is exactly the kind of
                                            // question an auditor would ask later
}
```

**Why the `reasoning` field matters beyond documentation:** every other agent in this pipeline produces output that's checked against a deterministic rule or a sourced fact. The Discovery Agent is different — its core value is a judgment call about *when* to act, and judgment calls need to be explainable after the fact, especially in a compliance product where "why did you flag this claim for re-review three weeks after it was cleared" is a completely reasonable question a customer could ask.

## 3. Intake Agent

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
- **A self-reflection pass, not a single one-shot extraction.** After the first extraction pass over a document, the agent should re-read its own output against the source document once more and explicitly ask whether anything was missed, before finalizing the claim list — rather than treating the first pass as final by default. This is a genuine, if modest, instance of agentic self-correction (see `25-agentic-maturity-roadmap.md` §5) rather than a single-shot LLM call dressed up as an agent. Concretely: a second Gemini call, given the document plus the first-pass claim list, prompted specifically to identify anything the first pass missed — cheap to add, and a real quality improvement, not just a compliance checkbox.

## 4. Research Agent

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
- **Dynamic Multi-Tool Parallel API Selection.** The agent dynamically evaluates each claim's complexity and selects the appropriate Parallel API tool:
  - **Parallel Search API** (`parallel_search_api`): Selected for standard, high-speed public domain and trademark registry queries.
  - **Parallel Task / Deep Extract API** (`parallel_task_api`): Selected for complex, ambiguous claims (e.g. multi-party copyright assignments, estate transfers, or conflicting broadcast licenses) requiring multi-page synthesis.
- **Domain-targeted, registry-steered query construction.** The agent constructs query strings formatted specifically for authoritative databases per claim type:
  - `music`: `"ownership, PRO sync rights, ASCAP BMI HFA registry status for {extracted_description}"`
  - `brand`: `"trademark registration status, USPTO WIPO TESS filing for {extracted_description}"`
  - `footage`: `"copyright registration status, US Copyright Office catalog for {extracted_description}"`
  - `real_person`: `"right of publicity, SAG-AFTRA guild clearance considerations for {extracted_description}"`
  - `genai_flag`: `"copyright training data provenance, U.S. Copyright Office AI guidance for {extracted_description}"`
  - `other`: `"{extracted_description} ownership and legal status"`

- **Self-Directed Multi-Hop Chained Research.** If an initial search result snippet references a connected licensee, estate, or subsidiary rights-holder (e.g., discovering CBS broadcast rights attached to an Apollo 11 NASA clip), the Research Agent autonomously issues a follow-up query (`multi_hop_depth: 1`) chasing the lead without waiting for human intervention.
- **Mid-Run Secondary Claim Discovery.** If web research on a claim surfaces an unextracted secondary rights-triggering element (e.g. a background musical cue mentioned in a trademark document), the Research Agent proposes a new claim (`proposed_by_agent: "research_agent"`). The proposed claim is passed to the Intake Agent for schema validation before being committed to the ledger.

**Example call shape** (illustrative — confirm exact current parameter names and method signatures against `docs.parallel.ai` before implementation, since SDK interfaces evolve):
```python
from parallel import Parallel

client = Parallel(api_key=settings.PARALLEL_API_KEY)

def research_claim(claim: Claim) -> Finding:
    query_str = build_domain_steered_query(claim) # uses registry-targeted templates above
    try:
        result = client.search(
            query=query_str,
            # confirm current parameter names against docs.parallel.ai before build
        )
        return Finding.from_search_result(claim.claim_id, result)
    except (TimeoutError, ParallelAPIError):
        return Finding.failed(claim.claim_id)
```

**Engineering the demo's conflicting-sources claim:** per `02-mvp-scope.md` §2.3, at least one claim in the demo set must genuinely return conflicting findings from two sources. In practice, this likely means either (a) selecting a real claim ahead of time, through manual research, that's known to have genuinely disputed public information (an obscure song with conflicting rights-holder claims online, for instance), or (b) issuing two separate, deliberately differently-worded queries for the same claim and using whichever combination reliably surfaces disagreement. Option (a) is more honest to the "real live search" spirit of the requirement and should be preferred if a suitable real example can be found during demo-data preparation; option (b) is an acceptable fallback if time runs short, but should be disclosed honestly in the demo narration rather than presented as if it happened naturally.

**Concurrency strategy — how "N independent calls" actually gets implemented.** The Research Agent should issue its per-claim Parallel calls concurrently, not sequentially in a loop — a sequential implementation would make a 4-claim demo run visibly slower than necessary, and would perform badly at real-world scale where a production has 200+ claims. Concretely: `asyncio.gather()` over one async call per claim is the right shape for Python, since Parallel's calls are I/O-bound (waiting on a network response), which is exactly the case `asyncio` is built for — no need for full multiprocessing or a separate task queue at MVP scale (a real task queue like Cloud Tasks is the correct Phase 2 upgrade, per `03-post-mvp-scope.md` §7, once claim volume per run grows large enough that a single Cloud Run request holding open 200+ concurrent connections becomes impractical). At hackathon demo scale (a handful of claims), a simple `asyncio.gather()` is sufficient and keeps the implementation honest and inspectable for a judge reading the code, rather than over-engineered for a problem the demo doesn't actually have yet.

**Retry strategy — one attempt before failing, not zero, not unlimited.** The current failure-handling design (`call_status: failed` on any error) is correct as a final state, but a single network blip shouldn't permanently fail a claim that a second attempt would have resolved. Add one retry with a short fixed backoff (e.g., wait 1-2 seconds, retry once) before writing `call_status: failed` — this is a small addition that meaningfully improves real-world reliability without adding real complexity. Worth being precise in the demo narration about this: the deliberately-triggered failure (`DEMO_MODE`, see `07-env-vars.md` §2) should simulate a failure that persists *through* the retry, so the graceful-degradation moment shown on camera reflects genuinely exhausted retries, not a naive zero-retry design. **Rate limiting:** since concurrent calls could theoretically approach a Parallel API rate limit at higher claim volumes (unlikely at 4-claim demo scale, but worth a one-line mitigation for credibility), a simple `asyncio.Semaphore` capping concurrent in-flight requests to a conservative number (e.g., 10) is a cheap, standard safeguard worth including even though it won't visibly matter until real production scale.

**Reformulate-and-retry — a genuinely different behavior from the network retry above, worth not conflating with it.** The retry described above re-issues the *identical* query after a network failure — that's reliability engineering, not agency. This is different: after a *successful* call that returns a poor-quality result (few results, low relevance, or a result the agent itself judges too thin to support a confident finding), the agent should evaluate that outcome and autonomously issue a *reformulated* follow-up query — different wording, a narrower or broader framing — before accepting a final answer for that claim. This is a real, bounded instance of an agent iterating on its own work based on a judgment about its own output quality, not a human-coded exception-handling rule (see `25-agentic-maturity-roadmap.md` §5 for the fuller framing of why this distinction matters). Cap this at one reformulation attempt per claim for the MVP — unbounded reformulation risks unpredictable demo timing, and one bounded iteration is enough to demonstrate the behavior genuinely.

## 5. Ledger Agent

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

## 6. Risk Scoring Agent

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

**Human-in-the-loop as a callable action, not only a terminal state.** The design above treats `needs_human_review` purely as where a claim ends up — a passive exit ramp. A more agentic version, worth building for the MVP rather than deferring, lets the agent *actively invoke* a targeted clarifying question mid-reasoning and resume once answered, rather than only ever flagging and stopping. Concretely: when the arbitration logic hits genuine, irreducible ambiguity (two equally-authoritative, equally-recent sources in direct conflict, for instance), instead of only writing a passive review flag, the agent generates a specific, answerable question — *"Source A and Source B disagree on whether this footage requires separate broadcast-rights clearance — can you confirm which applies here?"* — surfaces it, and is capable of incorporating a human's answer back into the scoring run rather than requiring an entirely new pipeline execution. This reframes the human from something the pipeline defers to when it fails, into a tool the agent actively reaches for when it judges that's the right move — a meaningfully more agentic framing (see `25-agentic-maturity-roadmap.md` §5), and a stronger demo beat: "the agent asked a specific question" reads as more autonomous than "the agent gave up."

## 7. Report Agent

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

## 7. Human Attorney Review & Override Flow (Human-in-the-Loop)

**Responsibility:** Allow production legal counsel to review `needs_human_review` or `flagged` claims, submit formal legal sign-offs (`attorney_approval` or `attorney_override`), and commit append-only audit entries to the ledger.

**Input:** A target `claim_id`, previous `ledger_entry_id`, attorney credentials (`reviewed_by`), decision (`attorney_cleared` | `attorney_flagged`), rationale (`override_reason`), and optional contract/statutory reference (`legal_citation_ref`).

**Payload contract (UI $\rightarrow$ API):**
```json
{
  "claim_id": "clm_001",
  "action_type": "attorney_override",
  "target_status": "attorney_cleared",
  "reviewed_by": "counsel@productionlaw.com",
  "override_reason": "Executed synchronization and master use license agreement verified on file",
  "legal_citation_ref": "License Contract #SYNC-2026-884"
}
```

**Output behavior:**
1. Validates that the requesting user has `attorney_reviewer` permissions.
2. Retrieves the latest `ledger_entries` record for `claim_id` (e.g. `version: 2`).
3. Writes a new `ledger_entries` document with:
   - `version: 3`
   - `action_type: "attorney_override"` (or `"attorney_approval"`)
   - `status: "attorney_cleared"`
   - `reviewed_by: "counsel@productionlaw.com"`
   - `override_reason: "Executed synchronization..."`
   - `legal_citation_ref: "License Contract #SYNC-2026-884"`
   - `written_by_agent: "attorney_counsel@productionlaw.com"`
4. Updates version 2's `superseded_by` field to point to version 3.
5. Emits an audit event for the Clearance Intelligence Report generator.

This flow enforces that Lienmark acts strictly as a **Clearance Intelligence & Verification Audit** tool, maintaining complete legal attribution for human sign-offs while preserving the full history of automated agent findings.

## 8. Error taxonomy — beyond Parallel call failures

Every prior version of this document addressed one failure mode in depth (a Parallel Search API call failing or timing out, §4 above). That's the right one to feature in the demo, but it's not the only way this system can fail, and a genuinely "robust" system — per the judging criteria's explicit emphasis on error recovery (`01-hackathon-scope.md` §1) — should have a considered answer for each of these, even if only some are built for the MVP:

| Failure mode | Where it happens | Correct behavior |
|---|---|---|
| Malformed or corrupted PDF upload | Intake Agent, input stage | Reject with a clear user-facing error before attempting extraction — never pass a corrupted file to Gemini and hope for a graceful model-side failure |
| Empty or near-empty document (no extractable claims) | Intake Agent | Return a valid, empty claims list with a distinct production status (e.g., `status: no_claims_found`) rather than treating this as an error — an empty result is a legitimate outcome, not a bug, and should be visually distinguishable in the UI from a processing failure |
| Document in a language other than English | Intake Agent | Out of scope for MVP (`02-mvp-scope.md` doesn't claim multilingual support) — but the correct MVP behavior is to detect this and surface a clear "unsupported language" message, not to silently attempt extraction and produce low-quality results without explanation |
| File exceeds a reasonable size/page limit | Intake Agent, input stage | Reject with a clear limit stated in the error (e.g., "50 pages max for this demo") rather than a generic failure or, worse, a silent truncation that could drop claims without anyone noticing |
| Gemini API itself unavailable (not just Parallel) | Intake Agent, Risk Scoring's explanation-generation step | This is a different failure than a Parallel timeout and deserves its own handling — the whole pipeline can't proceed without extraction, so this should surface as a clear "service temporarily unavailable, please retry" state, distinctly different from a per-claim research failure, since it blocks the entire run rather than one claim within it |
| Firestore write failure (network partition, quota, permissions misconfiguration) | Ledger Agent, any write | Should never fail silently — a failed ledger write is a serious integrity event (a claim could appear processed when its result was never actually durably recorded) and should halt the pipeline with a clear error rather than proceeding as if the write succeeded |
| Duplicate/concurrent submission of the same production | Intake Agent, input stage | Not addressed anywhere previously — worth a simple MVP-scope answer: hash the uploaded document content, and if an identical hash is already `processing` for the same user, return the existing in-progress result rather than starting a redundant, resource-wasting second pipeline run |

**Which of these are actually in MVP scope:** per the definition-of-done discipline already established in `02-mvp-scope.md` §9, not every row above needs to be built before the hackathon deadline — but every row should at minimum have this documented, considered answer, so that if a judge's own testing happens to trigger one of these (e.g., uploading an empty file out of curiosity), the system's behavior is a deliberate, explainable choice rather than an undiscovered crash. Worth treating "malformed PDF" and "empty document" as the two highest-priority additions to actually build, given they're the most likely to be accidentally triggered by anyone poking at the hosted demo beyond the intended happy path.

## 9. Orchestration implementation notes

- **Built on Google Cloud Agent Builder / Gemini Enterprise Agent Platform**, per the hackathon's core requirement (see `01-hackathon-scope.md` §2).

- **Decision, made explicitly rather than left open: native Agent Builder/ADK orchestration, not LangGraph.** This was a genuinely weighed choice, not a default:
  - Lienmark's control flow (§1 above) is **mostly linear** — Intake → Research → Ledger → Risk Scoring → Report, with exactly one real branch point (routing a claim to human review). LangGraph's core strength is explicit state-graph modeling for *complex, branching, or cyclical* multi-agent interactions — negotiation loops, conditional re-planning, agents calling each other in non-obvious orders. Lienmark's pipeline doesn't have that shape, so reaching for LangGraph would mean adopting a heavier framework than the actual control-flow complexity justifies.
  - The one property LangGraph would have genuinely helped with — guaranteeing the Report Agent never reads data the Ledger Agent hasn't finalized — is fully achievable in a plain, explicit Python orchestration function that awaits each agent's completion before invoking the next, since the pipeline has no concurrency between agents (only *within* the Research Agent's per-claim calls, which is a different, already-addressed concern — see the concurrency note below). A simple sequential `await` chain in `pipeline.py` provides the same ordering guarantee as a formal state graph would, at a fraction of the implementation and learning cost.
  - Native Agent Builder patterns also align more directly with "visibly using the required platform" for a judge doing a fast review — the orchestration logic reads as unambiguously Google-Cloud-native, rather than requiring a judge to separately understand how LangGraph sits on top of Gemini.
  - Practical factor, stated plainly: adopting LangGraph mid-sprint would mean the team ramping up on a new framework inside an already-tight 5-week window (`10-build-timeline.md`), for a control-flow guarantee achievable more simply. This is exactly the kind of avoidable risk the build timeline's own risk register warns against.
  - **If a future phase's control flow genuinely becomes non-linear** — for instance, if the Risk Scoring Agent's conflict arbitration needs to loop back and request additional Research Agent queries dynamically, rather than working only from what it's given — that's the point to revisit this decision, not before.

- **Correction/addendum, following the agentic-maturity assessment in `25-agentic-maturity-roadmap.md`: the condition above has now been met, but only for a specific future capability, not for the MVP itself.** Two additions were made to this document as part of that assessment — the Research Agent's bounded reformulate-and-retry (§4) and the Risk Scoring Agent's human-in-the-loop-as-callable-action (§6). Both remain implementable as plain, explicit Python control flow (a capped one-time retry loop; a pause-and-resume pattern) and do **not** by themselves require reversing the MVP's native-ADK decision — they're bounded, not genuinely open-ended dynamic planning. **What does trigger the reversal is Phase 2's planning orchestrator** — a system that dynamically decides the *shape* of the pipeline itself per document, rather than executing a fixed sequence with bounded local adaptations inside it. That capability is explicitly out of MVP scope (`25-agentic-maturity-roadmap.md` §5) precisely because it's harder to make reliably demonstrable within a hackathon's fixed video format — but when it is built, **LangGraph is the right choice for it**, for the same reason originally stated in this section: explicit state-graph modeling is built for exactly the branching, looping, self-modifying control flow a real planner needs. The MVP decision and the Phase 2 decision are simply answers to two different questions, and this addendum exists so that distinction is recorded explicitly rather than left for someone to reconstruct later from an outdated, unqualified "native ADK" statement.

- **Per-agent service accounts** (see `07-env-vars.md` §4) are not an IAM nicety layered on afterward — they are the literal, code-level implementation of the "Studio Head enforcing Cloud IAM security" framing from the hackathon's own promotional language (see `01-hackathon-scope.md` §7.4). Worth surfacing this explicitly in the pitch narration, not leaving it as an implementation detail judges might miss if it isn't called out.

- **Testing determinism as an actual test, not just a design claim.** `tests/test_risk_scoring_determinism.py` should run the identical claim/finding input through the Risk Scoring Agent multiple times in a row and assert byte-identical output every time. This converts "our scoring is deterministic" from an assertion in documentation into something independently verifiable by anyone who runs the test suite — including, potentially, a technically thorough judge who clones the repo and runs `pytest` before making a final decision.
