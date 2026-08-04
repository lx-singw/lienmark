# Product Requirements Document — Lienmark

**Status:** Draft, locked for hackathon build
**Owner:** [Team]
**Last updated:** August 2026

This is the single source of truth for what Lienmark is and why. Every other document in this package (data schema, agent orchestration, directory structure, pitch deck) should be read as an implementation of what's specified here — if any of them ever conflict with this document, this document wins, and the other should be updated to match.

## 1. Problem statement, in full

Every film, series, or documentary production accumulates dozens to hundreds of unresolved rights claims over its lifecycle: music cues that need sync licensing, archival or stock footage of uncertain provenance, brand mentions that could trigger trademark disputes, real people or historical figures whose depiction carries defamation or right-of-publicity risk, and — increasingly — AI-generated or AI-assisted content whose underlying training data provenance is unknown even to the people who used the tool.

Clearing these claims today is manual, ad hoc, and structurally invisible until it causes a concrete problem: a distribution deal collapses during due diligence, an insurer refuses to underwrite a completion bond, or a lawsuit lands months after release when it's far too late to cheaply fix. There is no point in the current production process where someone is systematically, proactively checking every claim against current, live ownership data — it happens reactively, expensively, and usually only when someone with legal training happens to notice a specific risk.

This is expensive by design, not by accident: entertainment counsel typically runs $250-700 per hour (with top-tier LA/NY counsel running $800-1,200+/hour), and a single mid-budget production can carry 200 or more distinct claims requiring some form of clearance research. At even a conservative estimate, that's a five-to-six-figure cost center that most productions handle inconsistently, under time pressure, and without any systematic audit trail.

Meanwhile, the risk landscape is actively worsening, not staying static:

- In February 2026, ByteDance's Seedance 2.0 AI video model produced viral, unauthorized depictions of copyrighted characters and real celebrities' likenesses; Disney, Paramount, and eventually the Motion Picture Association sent formal cease-and-desist letters — the MPA's first-ever such letter to a generative AI company. SAG-AFTRA separately condemned the tool as disregarding "law, ethics, industry standards and basic principles of consent." As of mid-2026, these disputes remain unresolved even as a more capable successor model has already launched — signaling that the industry now treats AI-content provenance as an active, unsettled legal battleground, not a theoretical future concern (full sourcing in `14-sources-appendix.md`)
- This specific dispute is evidence of a broader pattern: the *category* of claims a production needs to track is expanding faster than manual processes can adapt to
- Indie producers — who can least afford $250-700/hour entertainment counsel — are hit hardest by this shift, and simultaneously have the fewest institutional resources to build systematic clearance tracking on their own

No existing tool actively, autonomously researches and verifies rights status against current, live sources. The tools that exist in adjacent spaces (see §8 for the specific competitive comparison) help a production *document* clearance decisions that a human has already manually made — none of them independently go and check ownership, licensing status, or dispute history, and none of them maintain an auditable, tamper-evident record of that research over time.

## 2. Product vision

### 2.1 One-line description
An agentic verification layer that ingests a script or cut, extracts every rights-triggering element, and autonomously researches and verifies current ownership and clearance status — producing an auditable, sourced clearance ledger.

### 2.2 Long-term vision, and why this specific framing matters
> The independent verification layer sitting between a studio and everyone it can't fully trust or see — vendors on one side, rights-holders on the other. The ledger both sides check before money or content moves.

This is deliberately modeled on the real-estate title insurance industry, and the reasoning for that specific analogy (rather than a more generic "SaaS tool for studios" framing) is laid out in full in `03-post-mvp-scope.md` §1. The short version: the goal is not to build a tool studios *choose* to use because it's good, but a verification step that surrounding institutions (insurers, bond companies) increasingly *require* as a condition of doing business — unglamorous, mandatory, and difficult to dislodge once embedded in standard deal-closing practice.

### 2.3 Hackathon framing alignment
The hackathon's own promotional language frames three roles for participants: **Director** (building production-ready autonomous agent networks), **Technical Producer** (connecting secure data pipelines via managed protocol adapters), and **Studio Head** (enforcing Cloud IAM security and governance across multi-agent workflows). Rather than treating this as marketing flavor text to ignore, Lienmark is deliberately built to embody all three simultaneously, because doing so happens to align exactly with what makes the product good, not just what makes a good pitch:

- The **Director** story is the genuine five-agent orchestration (Intake, Research, Ledger, Risk Scoring, Report) — a real production-ready network, not a single wrapped prompt
- The **Technical Producer** story is the live, per-claim Parallel Search API integration at runtime — a real secure data pipeline connection, not a mocked demo
- The **Studio Head** story is, distinctively, not just a nice-to-have theme — it *is* the actual core product thesis. The append-only governance ledger and the least-privilege per-agent IAM design aren't decorative alignment with the hackathon's marketing copy; they're the literal mechanism by which Lienmark becomes trustworthy enough to be the record an insurer relies on. This is worth stating explicitly in the pitch (see `05-pitch-deck.md`), because it signals to judges that the team understood the spirit of what was being asked for, not just the letter of the technical requirements.

## 3. Target users and buyers

**Important distinction, worth stating explicitly because it shapes every downstream design decision: users are not necessarily buyers.** The person who benefits day-to-day from using Lienmark (a post-production supervisor) is frequently not the person who holds the budget to purchase it (an insurer or bond company). Designing only for the user's workflow, without designing the *output* specifically for the buyer's evaluation process, would be a mistake.

| Role | Who | What they do with Lienmark |
|---|---|---|
| Primary buyer | Completion bond companies | Require a clearance certificate as a condition of underwriting production completion risk; currently pay human researchers to produce something functionally similar, manually |
| Primary buyer | E&O insurers | Use clearance quality and completeness as a direct, quantifiable input into how they price a policy |
| Primary user + secondary buyer | Post-production supervisors, mid-size indie/documentary production companies | Run the actual day-to-day clearance workflow; have real, if modest, budget authority and a faster sales cycle than a major studio |
| Future buyer (Phase 2+, not immediate) | Major studios | Enforcement side — verifying their own IP isn't being scraped or misused by AI models, and clearing their own large-scale productions systematically |
| Explicitly not the target buyer | Individual indie filmmakers | Genuine, acute pain, but structurally the wrong segment: cash-poor, one-off projects, no recurring budget line — see `03-post-mvp-scope.md` §3 for the full reasoning |

## 4. Success metrics

### 4.1 Hackathon success
- 1st place in the Parallel track (primary, explicit goal)
- A working demonstration that genuinely satisfies all four judging criteria on their own terms, not just superficially — see `01-hackathon-scope.md` §6 for the detailed mapping
- A repo and video that could plausibly be shown to a real completion bond company or insurer post-hackathon without embarrassment — this is a useful internal bar, because it's a higher standard than "good enough to win a hackathon" and building to it tends to also satisfy the hackathon bar as a side effect

### 4.2 Company success (post-hackathon, directional — these will need real baselines once there's actual usage data)
- Number of distinct productions with at least one completed clearance report
- Proportion of claims resolved without human-review escalation (an efficiency metric that should improve over time as the Ledger Agent's delta-based retrieval and historical data accumulate — see §5.5 and the Agent Orchestration doc)
- Time-to-clearance-report compared against the manual baseline ($250-700/hour counsel, typically days-to-weeks turnaround for a full production)
- Number of completion bond or insurer partnerships actively using a Lienmark certificate as a real underwriting input, not just a courtesy reference

## 5. Functional requirements

### 5.1 Input handling
- Must accept a script excerpt (text/PDF) or an edit timeline (EDL/XML-style structured input) as the source document
- Must handle ambiguous or incomplete input gracefully — the correct behavior when a claim can't be confidently identified or described is to flag it as needing clarification, not to confidently guess and present a wrong answer as if it were certain. This requirement is deliberately borrowed from patterns observed in "Autopilot Agent"-style hackathon tracks focused on real-world business workflow automation, where handling messy, ambiguous input is treated as a core competency rather than an edge case to be assumed away.

### 5.2 Claim extraction (Intake Agent)
- Must identify every rights-triggering element in the source document: music cues, footage/stock references, brand mentions, named real people or historical figures, and content likely to involve GenAI generation or assistance
- Must tag each claim with a type and a scene/location reference sufficient to trace it back to the exact point in the source document
- Must generate a minimal, non-identifying search term per claim rather than passing along the full surrounding narrative context — see §5.6 for the full confidentiality rationale, since this requirement exists specifically to prevent leaking unreleased script content to a third-party service

### 5.3 Live research (Research Agent)
- Must issue a live call to Parallel's Search API for every extracted claim — this is the hackathon-required integration point, and the specific compliance bar (Search API specifically, called via an official SDK, genuinely present in code) is detailed in `01-hackathon-scope.md` §4
- Must retrieve current ownership status, licensing contact information where available, and any known prior disputes for each claim
- Each claim's research must be independently traceable back to its own specific call and result — batched or blended queries that can't be attributed to a single claim are not acceptable, both because they violate the "one sourced finding per claim" requirement (§5.7) and because they would undermine the demo's ability to show N distinct, purposeful calls happening live

### 5.4 Deterministic risk scoring (Risk Scoring Agent)
- Risk scores must be computed via rule-based logic operating on top of LLM-extracted facts — explicitly not a freehand LLM-generated score with no reproducible logic behind it
- The same input must produce the same output on every repeated run — this directly addresses the hackathon's own explicit language calling for "a deterministic, multi-step agent" (see `01-hackathon-scope.md` §2), and is independently good practice for a compliance-facing product where an insurer needs to trust that a verdict won't silently change between two runs on the same data
- Claims with low confidence or conflicting sources must route to a human-in-the-loop review state rather than auto-resolving — this is a deliberate design decision, not a fallback for insufficient confidence in the technology. No completion bond company or insurer would trust a fully-automated "yes, this is clear" verdict with zero human gate on genuinely uncertain claims, and building the human checkpoint in from the start is both more honest and a stronger product story than adding it later under pressure from a skeptical buyer
- Where the Research Agent surfaces conflicting findings from multiple sources for the same claim, the Risk Scoring Agent must perform explicit arbitration — weighing source authority, recency, and corroboration — and must log the conflict rather than silently picking one finding and discarding the other. This is not just a data-integrity requirement; it's also the specific mechanic that produces the strongest demo moment in the entire submission (see the Pitch Deck's demo video shot list for how this gets shown on camera)

### 5.5 Ledger (Ledger Agent)
- Must be append-only and immutable — no updates or deletes on any ledger record, only new versioned inserts with a `superseded_by` pointer connecting an old entry to whatever replaced it
- Must support delta-based retrieval: re-evaluating a production for a new deal or renewal should be able to pull the current state plus only what's changed since the last check, rather than replaying the full history every single time. This requirement is deliberately borrowed from "memory agent" hackathon patterns focused on efficient retrieval under context-window constraints — the underlying problem (how do you keep a growing historical record useful and fast to query, rather than letting it become an unwieldy full-replay burden) is the same shape whether you're talking about conversational memory or claim history, and solving it well here is both a legitimately better product and a stronger technical story about having thought about scale rather than just correctness on a single demo run
- This is the architectural foundation of the entire title-insurance-model thesis — an insurer or bond company will only ever trust a ledger that is provably tamper-evident, and "provably" here means enforced at the storage layer (database security rules), not just promised in documentation or application-level convention that a future bug could silently violate

### 5.6 Confidentiality
- The Intake Agent must extract minimal, non-identifying search terms per claim before anything is transmitted to Parallel — for example, "ownership status of song 'X' by artist Y," never the surrounding scene or plot text that gives that claim its narrative context
- Rationale, stated plainly: sending full scene context to a third-party search index risks leaking a studio's unreleased script to an external service before the film is even publicly announced. This is exactly the kind of question a real studio buyer would ask in the first serious conversation, and the honest answer needs to already be "no, we don't do that" by design, not "we'll add a redaction step" as an afterthought — a bolted-on redaction pass is both less reliable and harder for a skeptical buyer to verify than a system that structurally never has access to the sensitive context in the first place

### 5.7 Reporting (Report Agent)
- Every finding in the final report must cite its specific source (the exact Parallel result it came from) — there must be no unsourced verdicts anywhere in the output, full stop
- The report must clearly separate three categories: cleared claims, flagged/high-risk claims, and claims pending human review — this three-way split is what makes the output usable by a non-technical buyer (an insurer's or bond company's reviewer) rather than only legible to the engineering team that built it
- The report format must be structured and exportable, not merely a conversational text response — a real buyer needs something they can file, reference, and potentially attach to an underwriting decision

### 5.8 Failure handling
- A failed or timed-out Parallel call affecting one claim must never crash the overall pipeline
- Failed claims route to a "research incomplete — needs manual review" state, and the rest of the pipeline continues processing unaffected
- This behavior should be genuinely demonstrable, not just theoretically true — deliberately triggering this failure mode live during the demo video is a stronger, more credible signal of production-readiness than a run where nothing ever goes wrong, which can read to a skeptical viewer as suspiciously scripted or untested against real-world conditions

### 5.9 Governance / access control
- Per-agent service accounts with least-privilege IAM: only the Research Agent's service account may call Parallel; only the Ledger Agent's service account may write to the ledger collection; other agents are similarly scoped to exactly what they need and nothing more (full mapping in `07-env-vars.md`)
- This requirement satisfies two things simultaneously: a genuine security best practice that any serious engineering review would expect, and a literal, code-level implementation of the hackathon's own "Studio Head enforcing Cloud IAM security across multi-agent workflows" framing — worth surfacing explicitly in the pitch as evidence the team understood the assignment at more than a surface level

## 6. Non-functional requirements

- **Determinism:** structured output schemas and low/zero temperature settings on every scoring-critical step, so results are reproducible rather than varying run to run
- **Auditability:** every ledger entry is timestamped, versioned, and traceable back to both its source claim and the specific research finding that produced it
- **Gracefulness:** partial failures degrade in a contained, visible way — they do not cascade into a full pipeline failure
- **Demonstrability:** the entire pipeline must be observable, live, within a 3-minute window for the hackathon video — this is a real constraint that shapes scope as much as any functional requirement does. A feature that's technically valuable but can't be made visible and understandable within that window is a weaker hackathon investment than one that's simpler but clearly demonstrable, even if the simpler feature is less impressive in isolation.

## 7. Explicit non-goals

Stating these clearly matters as much as stating the goals, because ambiguity here is exactly what leads to scope creep under deadline pressure:

- Not a script-generation or content-creation tool of any kind
- Not a general-purpose entertainment analytics platform
- Not building for individual indie filmmakers as the primary buyer (see §3 and `03-post-mvp-scope.md` §3 for the full reasoning)
- Not attempting to fully automate legal sign-off — Lienmark surfaces risk and research to support a human decision; it does not replace an entertainment lawyer's final clearance judgment, and no messaging (internal or external) should imply otherwise, both because it would be inaccurate and because overclaiming here would undermine the exact trust the product depends on

## 8. Competitive positioning — the direct objection-handling answer

**Anticipated question: "Doesn't Vitrina or Filmustage already do this?"**

**Answer:** No, and it's worth being specific about why, rather than just asserting differentiation. Vitrina is deal and vendor intelligence — it helps a studio figure out which vendor to hire or which deal terms are competitive, based on market/company data. Filmustage is AI-assisted production budgeting — it helps break down a script into cost estimates and schedules. Neither of these products performs live, per-claim, sourced ownership verification against the open web; neither maintains an immutable, auditable research ledger; and neither is built around the specific buyer segment (insurers, bond companies) that Lienmark targets. They solve adjacent but genuinely different problems. Lienmark is a research and verification agent, not a production-management database or a vendor marketplace.

## 9. Risks and open questions

| Risk | Mitigation |
|---|---|
| Parallel Search API returns incomplete or genuinely ambiguous ownership data for obscure claims (e.g., an obscure song from a defunct small label) | Route to human review rather than force a confident verdict the system can't actually back up with good evidence |
| Judges perceive this as "just a search API wrapper" with insufficient technical depth | Actively emphasize the deterministic scoring layer, the append-only ledger's storage-layer enforcement, and the multi-source conflict arbitration logic in both the pitch and the demo — none of these are "just search," and making that distinction legible to a judge watching a 3-minute video requires deliberate narration, not just good code |
| A real studio buyer raises confidentiality concerns about sending claim data to a third-party search service | Already addressed architecturally in §5.6; worth stating this explicitly and proactively in any real sales conversation, rather than waiting to be asked |
| Tension between wanting LLM flexibility for extraction and needing deterministic behavior for scoring | Resolved by splitting the pipeline: flexible, LLM-driven extraction (Intake Agent) feeding into rule-based, deterministic scoring (Risk Scoring Agent) — the split itself is the answer, and explaining this split clearly is a genuinely good technical talking point, not just a workaround |
| The regulatory tailwind (cease-and-desist trend, SAG-AFTRA rules) could shift or normalize faster than expected, weakening the "why now" argument | Keep the core rights-clearance value proposition (§1) independent of the regulatory narrative — the underlying $250-700/hour manual-cost problem exists regardless of how the AI-specific regulatory environment evolves, so the business case doesn't collapse if the current news cycle cools down |
