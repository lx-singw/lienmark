# Agentic Maturity Roadmap

This document exists because a direct, sharp question deserved a direct, honest answer: is Lienmark natively agentic, or is it workflow automation wearing agentic language? This is the framework for answering that precisely, an honest current assessment, and a prioritized path forward — including one prior architectural decision this framework requires revisiting.

## 1. The distinction that actually matters

There's a meaningful line between two things that both get called "agentic" loosely:

- **A workflow**: an LLM performs real reasoning *inside* predefined steps, but a human designed the sequence and shape of those steps in advance. The same steps run in the same order every time; only the content of the reasoning varies.
- **An agent**: the system itself dynamically decides what steps to take, in what order, with the ability to loop, backtrack, invoke tools it wasn't explicitly told to use for a given case, or reconsider its own prior output.

Most systems marketed as "agentic" are the first thing. That's not necessarily a criticism — for many problems, a well-designed workflow with strong reasoning inside each step is the *correct* engineering choice, not a lesser one. But it's a different thing than genuine autonomous agency, and conflating the two is exactly the kind of imprecision a technically sophisticated judge (or a technically sophisticated future customer) would notice.

## 2. Where Lienmark honestly sits

**The core pipeline is a fixed workflow, not a planned one.** `pipeline.py` hardcodes Discovery → Intake → Research → Ledger → Risk Scoring → Report as an invariant sequence. Nothing currently decides "skip a step for this document" or "loop back because the first pass was insufficient" or "invent an approach for this claim type nobody pre-coded for." Every run takes the same shape.

**Real agentic reasoning exists inside several steps** — the Intake Agent reasons about what constitutes a claim from unstructured text, the Research Agent interprets ambiguous search results, the Risk Scoring Agent's arbitration logic reasons about conflicting evidence. This is genuine LLM-driven judgment, not templated logic — but it's reasoning *within* a fixed step, not reasoning *about what steps to take*.

**The Discovery Agent (`09-agent-orchestration.md` §2) is the one genuine point of autonomous initiative** — it decides *when* to act without being told to, which is real agentic behavior at the level that matters most (deciding to act at all), even though it's narrow in scope.

**Honest net assessment: workflow automation with real agentic reasoning inside it, plus one genuine instance of autonomous initiative.** This is a legitimate, defensible place to be for a compliance product at this stage — but it is not the same claim as "natively agentic," and the difference is worth being precise about rather than blurred in a pitch.

## 3. What's actually missing, specifically

1. **No iteration within a step.** The Research Agent issues one query per claim and accepts whatever comes back — it doesn't evaluate its own result quality and decide to search again with a reformulated query if the first pass was weak.
2. **No self-reflection.** No agent reviews its own output before finalizing it. A reflective Intake Agent would re-scan a document after its first extraction pass and ask "did I miss anything" before committing to a final claim list.
3. **No dynamic tool selection.** The Research Agent → Parallel Search mapping is fixed 1:1. A more agentic version would have multiple tools available and reason about which fits a given claim.
4. **No dynamic planning.** Nothing decides the shape of the pipeline itself based on what a specific document actually needs — every document gets the identical sequence of steps regardless of its content.
5. **Human-in-the-loop is a terminal state, not a callable action.** `needs_human_review` is currently where a run ends up, not something an agent can actively invoke mid-reasoning as a targeted clarifying question and then resume from.

## 4. The governing architectural principle: Bounded Autonomy

The instinct might be "then maximize agentic autonomy everywhere" — that instinct is wrong for this specific product, and it's worth being explicit about why. **Lienmark's core value proposition depends on determinism and auditability** (`04-prd.md` §5.4, §5.5) — the Risk Scoring Agent was deliberately built to be rule-based specifically *because* a compliance verdict that varies between identical runs would undermine the entire trust thesis this company is built on. Full dynamic planning applied indiscriminately would work directly against that.

**The governing principle is Bounded Autonomy ("Flexible Investigation, Deterministic Validation"):**
- **Agents get full investigative autonomy**: Agents possess unconstrained authority over research depth, dynamic tool selection (Parallel Search API vs. Task/Extract API), multi-hop lead chasing across search snippets, mid-run claim discovery proposals, and notification urgency routing.
- **System maintains strict deterministic validation**: All ledger commits, Firestore security rules, risk scoring calculations, and human legal sign-off boundaries remain 100% deterministic and auditable.

## 5. Bounded Autonomy Capabilities (MVP Scope)

1. **Beat A (Proactive Discovery & Urgency Routing)**: Discovery Agent runs autonomously in the background (`09-agent-orchestration.md` §2), surfacing proactive toast alerts (`ToastContainer.tsx`) and routing urgent disputes to immediate alerts while batching routine flags.
2. **Beat B (Multi-Tool & Multi-Hop Iteration)**: Research Agent dynamically selects between Parallel Search API and Task/Extract API based on claim complexity, reformulates low-confidence queries, and autonomously chases secondary leads (subsidiaries, estates, licensees).
3. **Beat C (Mid-Run Discovery & Interactive HITL Action)**: Research Agent proposes newly discovered claims mid-run (validated by Intake schema checks) and surfaces context-aware `ClarifyingQuestionModal.tsx` asking targeted legal questions, pausing and resuming execution.

### Phase 2 — Dynamic Pipeline Planning (Sequenced Deliberately)

A full dynamic planner that alters the pipeline shape per document (e.g. skipping steps or dynamically adding new agent nodes) is the remaining architectural step. It is sequenced for Phase 2 not because of liability (investigative autonomy is already unconstrained), but because of **demo predictability and recording reliability**: a planner that alters its own pipeline shape introduces runtime variance that risks an unpredictable run during a live 3-minute recorded video take. Bounded autonomy delivers maximum investigative agency while maintaining 100% demo reliability.

**This requires walking back part of the ADK-vs-LangGraph decision in `09-agent-orchestration.md` §9.** That decision was made with an explicit, stated condition for reversal: *"if a future phase's control flow genuinely becomes non-linear... that's the point to revisit this decision."* A real dynamic planner is exactly that condition. **Corrected position:** native Agent Builder orchestration remains the right choice for the MVP's fixed pipeline (the original reasoning — the MVP's control flow is linear, so a heavier framework isn't justified — still holds for what's being built now). But **Phase 2's planning orchestrator is a strong candidate for LangGraph specifically**, since explicit state-graph modeling is built for exactly the branching, looping, self-modifying control flow a real planner needs — this was true when the original decision was made and remains true now; only the phase it applies to needed to be pinned down honestly rather than left implicit.

## 6. What to say if asked directly, worded honestly rather than defensively

*"The core pipeline is a workflow with real agentic reasoning inside every step, plus one genuine point of autonomous initiative in the Discovery Agent. We made that choice deliberately, not out of limitation — a compliance product's value depends on deterministic, auditable scoring, and full dynamic planning would work against that where it matters most. Where autonomy genuinely improves quality — research iteration, self-reflection, active clarification — we're adding it. Where determinism is the actual product, we're keeping it. A fully dynamic planning architecture is the real Phase 2 step, and we know exactly what that requires."*

## 7. External validation that this concern was the right one to act on

Worth recording directly: independent hackathon coverage confirms this wasn't a hypothetical worry. One detailed writeup of the event states plainly: *"This hackathon forces developers to think in terms of real operational workflows rather than superficial chat interactions. If your entry simply waits for a user to type a question and spits out a paragraph of text, you are missing the brief entirely. The goal here is to construct autonomous software that delivers tangible, end-to-end commercial value."* (source: techau.com.au, full citation in `14-sources-appendix.md`).

That's close to a direct description of the exact failure mode this document exists to correct — a system that only acts when a human tells it to. The Discovery Agent addition wasn't a speculative improvement; it was closing a gap the hackathon's own coverage explicitly names as disqualifying in spirit, even if not in the letter of the written rules.

## 8. A correction to the correction — worth recording, not smoothing over

When directly asked whether this was genuinely resolved, a closer look found it wasn't. The first version of the Discovery Agent fix scoped only the *secondary* behavior — re-surfacing an already-flagged stale claim — into MVP scope, and deferred *new-document discovery* (the behavior that actually determines whether the demo's opening action is autonomous or human-triggered) entirely to Phase 2, reasoning it needed real customer system access. That reasoning didn't hold up: a demo-scale watcher needs neither a real customer nor significant engineering — it's simpler than the behavior that *was* prioritized. The practical effect of the first fix was a demo that still opened with a human clicking upload, plus one good autonomous flourish near the end. `09-agent-orchestration.md` §2 and `02-mvp-scope.md` §2.1 have since been corrected to put the watcher first, as the higher-priority item.

**The reason this is worth recording rather than just quietly fixing:** it's a real instance of the exact discipline this whole document argues for — stating a position, checking it against a direct challenge, and correcting it visibly when the check fails, rather than defending the first answer because it was already written down. A pitch or README that only ever shows confident, unwavering positions is less credible than one that shows this kind of correction happened and explains why — it's evidence the reasoning was actually load-bearing, not decorative.
