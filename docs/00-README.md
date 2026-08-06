# Lienmark — Documentation Package

**Lienmark** is an independent Clearance Intelligence & Verification Audit platform for entertainment rights clearance — an agentic multi-agent system operating on the principle of **Bounded Autonomy ("Flexible Investigation, Deterministic Validation")**. It ingests a script or cut, extracts rights-triggering elements, dynamically selects Parallel's Search & Task APIs for deep multi-hop research, proposes mid-run discovered claims, and records automated findings and human attorney sign-offs to an append-only audit ledger.

## Long-term thesis, stated once here and in full

The real-estate title insurance model, applied to entertainment. Nobody loves title insurance, but nobody closes a deal without it — boring, mandatory, and hard to dislodge once embedded in standard practice. Lienmark aims to become that layer for entertainment IP: an independent verification service sitting between a studio and everyone it can't fully trust or see — vendors on one side, rights-holders on the other. The full reasoning behind why this specific analogy was chosen, rather than a more generic "SaaS for studios" framing, is in `03-post-mvp-scope.md` §1 — worth reading before pitching this to anyone, since the analogy only lands if the person explaining it actually understands why it's structurally, not just rhetorically, apt.

This is being built first as a submission to **Agentic Cinema: The Blockbuster Hackathon** (Google Cloud + partner ecosystem, deadline September 7, 2026, 2:00 PM PDT), on the **Parallel** track, with the explicit intent to use hackathon placement as a pre-seed forcing function for a real company — not as a one-off competition entry that gets abandoned the day after judging.

## Documents in this package, and what each one is actually for

| # | Doc | Purpose | Read this if you need to know... |
|---|---|---|---|
| 01 | [Hackathon Scope](01-hackathon-scope.md) | Rules, requirements, judging criteria, and how we map to them | Exactly what the hackathon requires, and why a specific design choice satisfies (or risks failing) a specific rule |
| 02 | [MVP Scope](02-mvp-scope.md) | What ships for the hackathon submission, precisely | Whether a feature idea is in-scope, and what "done" looks like for each in-scope feature |
| 03 | [Post-MVP Scope](03-post-mvp-scope.md) | Phase 2 and Phase 3 roadmap toward the company vision | Why the company is sequenced the way it is, and the full competitive-landscape research behind the core bet |
| 04 | [PRD](04-prd.md) | Full product requirements — problem, users, functional/non-functional specs | The single source of truth for what the product is and why — if any other doc conflicts with this one, this one wins |
| 05 | [Pitch Deck](05-pitch-deck.md) | Slide-by-slide narrative for judges and future investors, plus the full demo video shot list | Exactly what to say, when, and why each slide is framed the way it is |
| 06 | [Data Schema](06-data-schema.md) | Firestore (MVP) and Postgres (post-MVP) schemas, ledger design | The exact shape of every record, with worked examples of the versioning pattern |
| 07 | [Environment Variables](07-env-vars.md) | Full `.env` reference and secrets management | Every variable the system needs, and the exact per-agent IAM mapping |
| 08 | [Directory Structure](08-directory-structure.md) | Repo layout, per-agent module organization | Where a specific piece of logic should live, and why the structure is shaped this way for judging |
| 09 | [Agent Orchestration](09-agent-orchestration.md) | Full agent-by-agent spec, message contracts, control flow, worked examples | Exactly how each agent behaves, with concrete input/output examples for every step |
| 10 | [Build Timeline](10-build-timeline.md) | Week-by-week plan from today to the Sep 7 deadline | What should be done, and demonstrable, by the end of any given week |
| 11 | [Demo Content](11-demo-content.md) | The actual script excerpt, claims, and narration used in the demo | The real content the demo runs against, and why each claim was specifically chosen |
| 12 | [QA Checklist](12-qa-checklist.md) | Pre-submission verification, run against production before submitting | Exactly what to check, line by line, before hitting submit |
| 13 | [Technical Validation](13-technical-validation.md) | De-risking findings for Parallel and Gemini, plus the Agent Builder code gap | What's actually been tested, what's still assumed, and the exact Week 0 test plan |
| 14 | [Sources Appendix](14-sources-appendix.md) | Every specific factual claim, with a real checkable source | Verification for any number, date, or named competitor used elsewhere in the package |
| 15 | [Judge Q&A Prep](15-judge-qna-prep.md) | Anticipated tough questions and prepared answers | What to preemptively address in the video/repo, given judging is fully asynchronous with no live Q&A |
| 16 | [Liability & Trust Posture](16-liability-and-trust-posture.md) | Lienmark's own risk exposure, not just its customers' | What a sophisticated buyer or judge would ask about data security, retention, and liability boundaries |
| 17 | [Moat Mechanics](17-moat-mechanics.md) | The specific, mechanical answer to "why can't this be cloned" | What's actually defensible (accumulated ledger data, switching costs) versus what isn't (the code itself) |
| 18 | [Company Formation Readiness](18-company-formation-readiness.md) | IP assignment, entity formation, trademark/domain next steps | How to treat this as real pre-seed groundwork, not just a hackathon entry |
| 19 | [Executive Summary](19-executive-summary.md) | One-page leave-behind covering the entire thesis | The 60-second version, if that's all someone has time for |
| 20 | [Adversarial Input Defense](20-adversarial-input-defense.md) | Prompt injection risk and layered defenses | What happens if an uploaded document tries to manipulate the extraction agent |
| 21 | [Agent Prompts](21-agent-prompts.md) | The actual drafted system prompts for every agent | Real starting content for `prompts.py`, not a placeholder |
| 22 | [Pre-Mortem](22-pre-mortem.md) | Strategic and competitive risks, examined before they happen | Why this might not win even if everything is built correctly |
| 23 | [Competitor Comparison Matrix](23-competitor-comparison-matrix.md) | A consolidated, scannable comparison table | How Lienmark differs from Vitrina, Filmustage, and enforcement-side tools, in one place |
| 24 | [Vision & Mission](24-vision-and-mission.md) | The long-term multi-industry expansion picture, beyond entertainment | Which future industries the verification-ledger pattern could extend to |
| 25 | [Agentic Maturity Roadmap](25-agentic-maturity-roadmap.md) | An honest assessment of how agentic this actually is | Workflow-vs-agent distinction and path to bounded agency |
| 26 | [Hackathon Alignment Matrix](26-hackathon-alignment-matrix.md) | Devpost judging criteria & sponsor requirements alignment | Direct mapping of judging rules to code files and CLI commands |
| 27 | [Feature Toggles & Demo Selection](27-feature-toggles-and-demo-selection.md) | Modular feature toggle architecture & 3-min video demo features | Opt-in config payload and 6 active hero features for hackathon demo |
| -- | [API Reference](api-reference.md) | Complete REST API specification, JSON payloads, HTTP status codes | Untruncated request/response contracts for backend endpoints |
| -- | [Installation Guide](installation.md) | Hardware requirements, step-by-step setup commands, troubleshooting matrix | Local dev runner, GCP provisioning, and error resolutions |
| -- | [Contributing Guidelines](contributing.md) | Code quality standards, testing strategies, trunk-based branching | Linting, pytest coverage, PR workflow, and semantic commits |
| -- | [Security Architecture](security.md) | Threat modeling, authentication, token lifecycles, and CORS/CSP hardening | 3 architectural attack surfaces, Argon2id/AES-256 encryption, and MPA standards |
| -- | [System Architecture](architecture.md) | High-level system architecture, ASCII diagram, and data flow trace | Component specs, gateway layer, and end-to-end trace |
| -- | [Project Scope](project-scope.md) | Consolidated 3-tier project scope | Hackathon (48-hour POC), MVP baseline, and Post-MVP roadmap |
| -- | [Vision Document](vision.md) | Executive summary, problem statement, value proposition, 3-5 year vision | Mission statement and title insurance model thesis |
| -- | [PRD Reference](prd.md) | Unnumbered exact-match PRD reference | Direct entry point linking to 04-prd.md |
| -- | [Directory Structure Ref](directory-structure.md) | Unnumbered exact-match directory structure reference | Direct entry point linking to 08-directory-structure.md |

## How these documents relate to each other

`01` and `02` are hackathon-facing and time-boxed to the September 7 deadline — they define the boundary of the current build. `03` looks past that boundary to the company. `04` (the PRD) is the single source of truth for *what* we're building and *why*; every other document should be read as an implementation of what's specified there. `05` is the external narrative — how this gets communicated to judges and, eventually, investors. `06` through `09` are engineering specs that must stay in lockstep with `04`: if the PRD changes, these need to change with it, not the other way around.

## Company identity (locked)

- **Name:** Lienmark
- **Collision check:** Clear as of last search pass — no registered trademark, live company, or software product found under this exact name. This was checked via general web search visibility, not a formal USPTO TESS search or domain registrar lookup — worth doing that formal check before investing real brand-building time, since search engines catch live companies and major filings but can miss pending applications or exact domain availability.
- **Backup name:** Provenus (also checked clear, same caveat applies)
- **Hackathon track:** Parallel
- **Second future product line (explicitly not in hackathon scope):** a VFX vendor cost/scope-drift governance product (working name: Overrun), targeting a Clickhouse-powered architecture — a Year 2 expansion, built on the same underlying verification-ledger pattern applied to a different fragmented ecosystem within entertainment. Full reasoning in `03-post-mvp-scope.md` §6.

## What "done" looks like for this documentation package

Every document in this set should be detailed enough that someone with no prior context on this conversation could pick up the package cold and understand not just *what* to build, but *why* each specific decision was made — the reasoning is written in, not left implicit. If any future addition to this package (a new feature, a new phase, a new technical decision) doesn't come with its own stated reasoning, that's a signal it hasn't been thought through completely enough yet to add.
