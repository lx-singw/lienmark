# MVP Scope — Hackathon Submission

This document defines exactly what ships by September 7, 2026, at the level of detail needed to actually build against — not just a feature list, but what each feature needs to do, what "done" looks like for it, and where the boundary sits against things that sound related but are explicitly deferred. Anything not listed as in-scope here is out of scope, regardless of how good an idea it is — see `03-post-mvp-scope.md` for everything deferred and why.

## 1. The demo narrative & 3 Autonomous Beats

Before the feature list, every scope decision traces back to this core narrative: **a user uploads a script excerpt, watches five distinct agents process it live, sees real web research happen in front of them, and receives a sourced, trustworthy report they could hand to a real insurer.**

To decisively satisfy Devpost's **Technological Implementation** and **Quality of Idea** criteria, the MVP explicitly demonstrates three visible autonomous beats:
1. **Beat A (Proactive Background Discovery)**: The Discovery Agent runs independently, periodically polling for stale claims or new document drops and surfacing proactive glowing toast notifications (`ToastContainer.tsx`) without human interaction.
2. **Beat B (Bounded Iterative Search)**: When Parallel's initial query returns thin or low-confidence results, the Research Agent autonomously reformulates its search string and executes a second targeted pass before committing findings.
3. **Beat C (Interactive Human-in-the-Loop Action)**: When hitting genuine ambiguity, the Risk Scoring Agent surfaces a targeted `ClarifyingQuestionModal.tsx` asking a specific question, pausing pipeline execution and seamlessly resuming once answered.

## 2. In-scope: the six-agent core pipeline

### 2.1 Discovery Agent — the genuinely autonomous trigger, not just a reactive pipeline

**What it does:** decides *when* a verification run happens, rather than requiring a human to manually initiate every run. Full architectural reasoning in `09-agent-orchestration.md` §2.

**Revised after an honest self-check, worth stating directly:** an earlier version of this scope only included the secondary re-verification behavior and deferred document discovery entirely to Phase 2. That was a mistake — it left the demo's *primary, opening action* still human-triggered (upload a file, pipeline reacts), which is close to exactly the failure mode the hackathon's own coverage names as missing the brief (see `25-agentic-maturity-roadmap.md` §7). The corrected scope below fixes the more important half first.

**In scope for MVP, in priority order:**

1. **A genuinely autonomous document watcher (`09-agent-orchestration.md` §2.1) — build this first, it matters more than item 2.** A real, independently-running polling loop or webhook listener watches a designated location and starts a clearance run when a new document appears, with no human clicking a "process this" action. **Hard requirement for this to count as real:** the watcher must be architecturally decoupled from the act of the file arriving — it would fire the same way regardless of what put the file there. A drag-and-drop UI that directly invokes the pipeline via a click handler is the old pattern with new styling, not a fix, and shouldn't be built even though it would look similar on screen.
2. **The autonomous re-verification behavior (`09-agent-orchestration.md` §2.3)** — any claim sitting in `needs_human_review` past a defined window (compressed to a short, demo-visible interval) triggers the Discovery Agent to proactively resurface it, without a human asking. Still valuable, still worth building, but secondary — it's a flourish on a run that item 1 is what actually makes agent-initiated from the start.

**Why item 1 belongs in MVP scope, not deferred, and why the earlier reasoning for deferring it was wrong:** deferring it assumed a real customer's document system was required — but a demo-scale watcher needs neither a real customer nor much engineering, and it's simpler to build than item 2. Given the judging criteria explicitly reward "true agentic behavior" and the hackathon's own coverage explicitly names "waits for a user to [act] and spits out a response" as missing the brief entirely, this is the single highest-leverage item in the entire MVP scope, not a nice-to-have layered on top of the "real" pipeline.

**Acceptance criteria:**
- The demo opens by showing a file being placed in the watched location — framed as an ordinary business action (saving a script to a shared drive), not as "operating the tool" — and the pipeline visibly starting on its own, with no upload button clicked on camera
- The watcher process can be shown (in the repo, or briefly in the video) to be a real, independent loop/listener, not client-side code that directly triggers the pipeline on a UI event
- After the Apollo 11 conflict claim (see `11-demo-content.md`) is routed to human review, the Discovery Agent should — after a short, visible interval — proactively surface a notification-style UI moment ("this claim has been pending review — resurfacing for attention") without any human clicking anything to request it

### 2.2 Intake Agent

**What it does:** Accepts a script excerpt or edit timeline (text/PDF upload), reads it using Gemini's native multimodal capability (no separate OCR/parsing step needed), and extracts every rights-triggering claim into a structured list.

**Claim types it must recognize:**
- Music cues (a song title, artist, or described musical moment)
- Footage/stock references (archival footage, stock clips, described "insert shot of X" moments)
- Brand mentions (named real products, logos, or corporate entities)
- Named real people (living or historical figures referenced by name)
- Likely GenAI-flagged content (any stage direction suggesting AI-generated or AI-assisted visual/audio content)

**For each claim, it must produce:** a claim type, a scene reference (so a human can trace it back to the source document), and — critically — a **minimal, non-identifying search term** rather than the full surrounding context. Example: if the script reads *"MARIA turns up the radio. 'Bohemian Rhapsody' by Queen fills the car as she drives toward the cliff, tears streaming down her face,"* the extracted claim should be something like `{type: "music", scene_ref: "p.34, INT. CAR - NIGHT", extracted_description: "song 'Bohemian Rhapsody' by Queen — sync licensing status"}` — not the full emotional scene description. This is a confidentiality requirement, not a style preference (see §6 below).

**Acceptance criteria:**
- Given a 3-5 page script excerpt with a deliberately mixed set of claim types, the agent extracts all of them without missing an obvious one and without duplicating a claim
- No `extracted_description` field exceeds roughly 15-20 words or includes plot/character/emotional context beyond what's needed to identify the specific rights-triggering element
- A claim that can't be confidently typed or minimally described is flagged `needs_clarification: true` rather than the agent guessing (see §7, ambiguous input handling)
- **A self-reflection pass runs after the first extraction** — a second pass checking the initial claim list against the source document for anything missed — and this pass is demonstrably capable of catching at least one deliberately hard-to-spot claim in a test document that the first pass alone missed (see `25-agentic-maturity-roadmap.md` §5 for why this is worth building rather than treating extraction as single-shot)

### 2.3 Research Agent

**What it does:** For each claim produced by the Intake Agent, issues a live call to Parallel's Search API and returns a sourced finding.

**This is the hackathon-required integration point** — see `01-hackathon-scope.md` §4 for the exact compliance bar. Concretely: this agent must call the real Parallel Search API, per claim, at runtime, using the official SDK, and the call must be a genuine, imported, callable function in the submitted repo.

**For each claim, the Research Agent must produce:** a `source_url` (non-null, required — no finding may exist without a checkable source), a short `source_snippet` supporting the finding, an `ownership_status` classification (clear / disputed / unknown / licensing_required), and a `call_status` (success / failed / timeout).

**Acceptance criteria:**
- Given N claims from the Intake Agent, the demo run visibly shows N independent Parallel calls, not one batched query
- At least one call in the demo run is engineered to fail or time out, and the agent handles it by writing a `call_status: failed` finding rather than raising an unhandled exception (see §5, failure handling)
- At least one claim in the demo set is engineered to return **genuinely conflicting findings from two distinct sources** — this is required, not optional, because it's the input the Risk Scoring Agent's arbitration logic needs to have something real to arbitrate on camera (see §2.4 and the Pitch Deck's demo shot list)
- **Reformulate-and-retry works as a bounded, genuine iteration, not a rename of the network-failure retry.** Given a claim whose first query returns a thin or low-confidence result, the agent autonomously issues one reformulated follow-up query before finalizing — capped at one reformulation per claim, and demonstrably a *different* query, not a repeat of the first (see `09-agent-orchestration.md` §4 for the full distinction from network-retry logic)

### 2.4 Ledger Agent

**What it does:** Writes every claim and finding to an append-only, versioned record. This is the architectural expression of the entire product's governance thesis — see PRD §5.5 for why this matters beyond the hackathon.

**Hard invariant:** no code path may update or delete a `ledger_entries` document. Every state change is a new document with an incremented `version` and a `superseded_by` pointer on the prior entry. This must be enforced at the storage layer (Firestore security rules restricting the Ledger Agent's service account to `create` only), not just as an application-level convention that could be bypassed by a bug.

**Acceptance criteria:**
- A dedicated test (`tests/test_ledger_immutability.py`) attempts an update and a delete against the ledger collection using the Ledger Agent's actual service account credentials, and both attempts must fail
- Given a claim whose status changes between two pipeline runs (e.g., a re-check surfaces a new dispute), the ledger shows both the old and new entries, with the old one correctly marked `superseded_by` the new one's ID — the full history remains queryable, nothing is silently overwritten

### 2.5 Risk Scoring Agent

**What it does:** Converts ledger entries into a deterministic, explainable confidence score per claim, and arbitrates when the Research Agent has surfaced conflicting findings.

**Determinism requirement (this is explicit hackathon language — see hackathon scope §2 — "a deterministic, multi-step agent"):** the scoring function must be rule-based, operating on LLM-extracted facts, not itself an LLM freehand judgment. A concrete rule shape: `confidence = f(source_authority_weight, recency, corroboration_count)`, computed the same way every time given the same inputs.

**Conflict arbitration (this is the demo's centerpiece moment):** when two findings for the same claim disagree on `ownership_status`, this agent does not silently pick one and hide the disagreement. It weighs source authority, recency, and corroboration, produces a single confidence-scored verdict, and logs both conflicting sources explicitly in a `conflict_sources` field so the disagreement remains visible and auditable, not erased.

**Human-in-the-loop threshold:** any claim scoring below a configurable confidence threshold (`RISK_CONFIDENCE_THRESHOLD`, default 0.7 — see `07-env-vars.md`), or any claim where `conflict_detected = true`, is routed to `needs_human_review` rather than auto-resolved. This is a deliberate product decision, not a limitation: no completion bond company or insurer would trust a compliance product that claims 100% automated certainty on every claim (see PRD §5.4 for the full reasoning).

**Human-in-the-loop as a callable action, not only a passive flag.** Rather than only marking a claim `needs_human_review` and stopping, the agent should be able to generate a specific, answerable clarifying question when it hits genuine ambiguity (not just a generic "please review" flag), and incorporate a human's answer back into the run once provided. This is a meaningfully more agentic pattern than a passive terminal state — see `09-agent-orchestration.md` §6 for the full behavior and `25-agentic-maturity-roadmap.md` for why this distinction matters to the broader "is this really agentic" question.

**Acceptance criteria:**
- Running the same claim/finding input through the scoring function multiple times produces identical output every time (`tests/test_risk_scoring_determinism.py`)
- The demo's engineered-conflict claim (see §2.2) visibly triggers the arbitration path, and the resulting output shows both sources and the reasoning for the verdict, not just a final number
- When the engineered-conflict claim triggers human review, the system generates a specific question referencing both conflicting sources by name — not a generic "please review this claim" message — demonstrating the callable-action behavior, not just the passive flag

### 2.6 Report Agent

**What it does:** Produces the final, human-readable clearance report — the actual artifact a real buyer (an insurer, a bond company reviewer) would need to see to trust the output.

**Hard requirement:** every claim listed as `cleared` or `flagged` in the report must carry a `source_url` traceable back to a real Research Agent finding. No unsourced verdicts, anywhere in the output. This is the single most trust-building detail in the entire product, and it's cheap to build correctly since the data already exists upstream — there's no excuse for cutting this corner under time pressure.

**Output structure:** three clearly separated buckets — cleared claims, flagged/high-risk claims, and claims pending human review — so a non-technical reviewer can scan the report in seconds rather than parsing a flat list.

**Acceptance criteria:**
- Every claim in the demo run appears in exactly one of the three buckets
- Every claim in "cleared" and "flagged" has a visible, clickable/checkable source
- The "pending review" bucket includes a plain-language reason for why each item needs a human (not just a confidence number with no explanation)

## 3. In-scope: demo-critical UI features & Design Polish Specs

These exist because the Design judging criterion explicitly rewards "a complete, coherent product experience," not just correct backend logic (see `01-hackathon-scope.md` §7.2). To ensure Lienmark wows judges in the first 15 seconds against flashier generative AI tools, the UI enforces rich visual polish and dynamic design:

- **Rich Aesthetics & Color Palette**: Sleek dark mode (`#0B0F17` background) with curated HSL accent colors, subtle glassmorphism (`backdrop-filter: blur(12px)` cards), vibrant risk status glows, and Google Fonts typography (Inter / Outfit).
- **CSS Design Token System (`frontend/app/globals.css`)**:
  ```css
  :root {
    --bg-primary: #0b0f17;
    --bg-surface: rgba(18, 26, 41, 0.75);
    --border-glass: rgba(255, 255, 255, 0.08);
    --accent-emerald: #10b981;  /* Cleared status glow */
    --accent-amber: #f59e0b;    /* Needs Human Review glow */
    --accent-rose: #ef4444;     /* Flagged High Risk glow */
    --accent-cyan: #06b6d4;     /* Parallel Search active indicator */
    --font-heading: 'Outfit', sans-serif;
    --font-body: 'Inter', sans-serif;
  }
  ```
- **Live-Updating Claims Table (`ClaimsTable.tsx`)**: Real-time WebSocket/Firestore listener updating claim row entry, status badges, risk score meters, and inline source citations as each Parallel call resolves.
- **Micro-Animations & Visual Cues**: Pulsating warning badges for `needs_human_review`, smooth CSS slide-in transitions for newly extracted claims, and real-time glowing progress bars during Research Agent query passes.
- **Proactive Toast Notifications (`ToastContainer.tsx`)**: Glowing notification toasts popping up when the Discovery Agent resurfaces a stale claim or when a background retry completes.
- **Interactive Human-in-the-Loop Modal (`ClarifyingQuestionModal.tsx`)**: Modern glassmorphism modal popping up when human input is requested, providing context-aware prompts and resuming pipeline state seamlessly.
- **Inline Source Citations (`SourceCitation.tsx`)**: Displayed directly next to each finding with clickable domain badges, ensuring zero friction for judges verifying search validity.

## 4. In-scope: technical/infrastructure requirements

- Google Cloud Agent Builder / Gemini Enterprise Agent Platform for orchestration (hackathon-required)
- Parallel Search API called via the official `parallel-web` SDK, live at runtime (hackathon-required, see §2.2)
- Firestore for claims/findings/ledger storage — chosen specifically for hackathon-timeline speed; see `03-post-mvp-scope.md` for the planned Postgres migration once real product usage demands it
- Cloud Run for hosting the backend and frontend
- Secret Manager for the Parallel API key and any other credentials — no secrets in code or committed `.env` files, ever (see `07-env-vars.md`)
- Per-agent service account separation implementing least-privilege IAM: only the Research Agent's service account may call Parallel; only the Ledger Agent's service account may write to the ledger collection (see `07-env-vars.md` for the full mapping table). This is not decorative — it's a literal, code-level implementation of the hackathon's own "Studio Head enforcing Cloud IAM security" framing (see `01-hackathon-scope.md` §7.4 and the Pitch Deck).
- Public GitHub repo with a complete OSS license visible at the repo root — MIT recommended specifically because it's the simplest, most permissive option and creates the least friction for a judge doing a quick review

### 4.1 Frontend decision point — make this call deliberately, not by default

Default plan is a lightweight Next.js app (see `08-directory-structure.md`), since the Design judging criterion rewards a coherent, polished experience, and a live-updating claims table is meaningfully easier to make feel real and responsive in React than in a simpler framework. **If build time runs short, Streamlit is the explicit, pre-approved fallback** — faster to stand up, and defensible in the judging context because judges are scoring the agentic workflow, not CSS polish. This decision should be made consciously at the project's build-time midpoint (roughly three weeks in), based on actual velocity so far — not allowed to happen by default drift in the final week under deadline pressure, which is when teams tend to make the worst infrastructure decisions.

## 5. Failure handling — treated as a first-class feature, not an edge case

A failed or timed-out Parallel call on any single claim must never crash the overall pipeline. The failing claim gets a `call_status: failed` finding, routes to human review, and the rest of the pipeline continues processing the other claims normally. This needs to be genuinely tested, not just assumed to work — and, per §3 above, deliberately demonstrated on camera in the video rather than left as a backend detail nobody sees.

## 6. Confidentiality — a real constraint, not a nice-to-have

The Intake Agent must never send full scene or plot context to a third-party service. Only minimal, claim-specific search terms leave the system boundary toward Parallel. Rationale: a real studio buyer would immediately ask "does this leak my unreleased script to a third party," and the honest answer needs to be no — this is designed into the Intake Agent's extraction step, not bolted on as a redaction pass afterward (which would be less reliable and harder to verify).

## 7. Ambiguous input handling

The Intake Agent should not assume every input is a clean, well-formatted script. If a claim can't be confidently typed or minimally described, it gets flagged `type: other, needs_clarification: true` rather than the agent guessing and presenting a confident wrong answer. Worth deliberately testing this against a deliberately messier input (an ambiguous or under-specified brand reference, for instance) before the final demo recording, to confirm graceful degradation actually holds up rather than just being a documented intention.

## 8. Explicitly out of scope for MVP

Being explicit about what's cut, and why each cut is safe, matters as much as the in-scope list — it's what keeps the team from quietly scope-creeping under deadline pressure.

- **Multi-tenant auth / user accounts** — a single-demo-instance is sufficient for the hackathon; real auth is a Phase 2 concern once there are actually two customers who need data isolation from each other (see `03-post-mvp-scope.md`)
- **Cloud SQL / Postgres migration** — Firestore is sufficient at hackathon scale (one demo production, a handful of claims); the relational/audit-logging benefits of Postgres only matter once there's cross-production querying to do
- **Graph database for chain-of-title** — this is a Phase 3 concern tied to option-chain/estate-transfer tracking, which doesn't exist yet in the MVP's claim model at all
- **Async task queue (Cloud Tasks/Pub-Sub)** — synchronous request/response is acceptable at demo scale; this becomes necessary once Parallel's deeper research calls need to not block a studio-facing report generation under real production load
- **Any Phase 2/Phase 3 feature** — synthetic talent rights, territorial distribution windows, tax rebate compliance, union residuals, and everything else in the Post-MVP Scope roadmap
- **Payment/billing infrastructure** — no monetization mechanics needed for a hackathon submission
- **Real customer data** — all demo data is synthetic at the content level; the claims are resolved against real, live Parallel searches on real public web data, but the underlying "production" the claims belong to is a constructed demo artifact, not an actual client's confidential script

## 9. Definition of done

The MVP is the **complete, working clearance pipeline** — six-agent core pipeline, real Parallel Search API calls, real append-only Firestore store, real deterministic scoring, real sourced report output, and a polished Next.js dark-mode UI. It must be production-grade in design, even if scope is intentionally focused.

1. A user can upload a script excerpt and watch the six-agent pipeline run live, end to end, with real Parallel Search API calls
2. At least one claim resolves clean, one resolves high-risk, and one specifically triggers the conflict-arbitration path with two disagreeing sources visibly shown
3. Every finding in the final report links back to a real, checkable Parallel source
4. At least one failure mode is demonstrated gracefully, on camera, without crashing the pipeline
5. The repo, when cloned fresh by someone with zero prior context, runs successfully following only the README instructions
6. The 3-minute demo video shows all of the above as an honest screen recording, not a scripted-feeling, edited-around-the-flaws presentation
