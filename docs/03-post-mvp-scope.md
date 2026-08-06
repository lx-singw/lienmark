# Post-MVP Scope — Company Roadmap

This document captures everything deliberately deferred from the hackathon MVP, organized into the phased roadmap toward the long-term company vision, with the full reasoning behind each phase — not just what's coming, but why it's sequenced the way it is and what has to be true before each phase starts. Nothing here is scope creep for the hackathon; the hackathon architecture (append-only ledger, agent-per-responsibility separation, source-cited findings) was deliberately designed so this roadmap doesn't require a rewrite later. That design discipline is the entire point of doing this planning now rather than after the hackathon.

## 1. The long-term thesis, stated in full

> An independent verification layer that sits between a studio and everyone it can't fully trust or see — vendors on one side, rights-holders on the other — and becomes the ledger everyone has to check before money or content moves.

This is the real-estate title insurance model, applied to entertainment. Worth spelling out why that specific analogy is the right one to build toward, not just a nice line for a pitch deck:

- Title insurance is not a product anyone wants to buy for its own sake — nobody gets excited about title insurance. It's bought because the *transaction* requires it, not because the buyer independently valued it.
- It's mandatory not by law in most cases, but by industry convention so deeply embedded that skipping it would be considered reckless by every party in a deal — lenders won't lend without it, buyers won't close without it.
- It's provided by an *independent* party — not the buyer, not the seller, not either side's own lawyer — because the entire value proposition depends on neither side being able to unilaterally vouch for the property's history.
- Once embedded in a transaction workflow, it is extremely difficult to dislodge, because doing so would require every participant in the ecosystem (lenders, title companies, real estate agents, buyers, sellers) to simultaneously agree to a new process — which almost never happens once a convention is set.

Lienmark's bet is that entertainment rights clearance can follow the same adoption path: not a tool a studio chooses to use because it's good, but a verification step a deal (a distribution agreement, a completion bond, an E&O policy) increasingly requires, provided by a party independent of both the studio and the rights-holder.

## 2. Competitive landscape validation — the full research trail

This isn't an assumption; it was checked against the actual current market before committing to this thesis. Here's what the research found, category by category, and why each conclusion was reached.

| Category | Status | Evidence |
|---|---|---|
| Script coverage | Saturated | Multiple funded, live competitors (Prescene, ScreenplayIQ, Callaia, and others); large production companies already running AI coverage in-house as part of development, marketing, and casting decisions |
| VFX pipeline/budgeting | Saturated | Filmustage runs a live AI "Production Agent" doing script breakdown, automated budgeting, and production risk flagging; Flow Production Tracking and ftrack dominate the task-tracking layer; only 38% of productions use any formal vendor scoring, but the *tooling* gap for cross-vendor visibility (see §5 below) is different from a general saturation claim |
| Localization/dubbing | Saturated | CAMB.AI is already deployed at IMAX; Rask, Noiz, Dubformer, and Poolday are all funded and live, competing directly on emotional voice matching and lip-sync |
| Piracy/content protection | Saturated, entrenched | MUSO, Corsearch, Friend MTS, and AiPlex have years of fingerprinting infrastructure and existing legal/ISP relationships that would be extremely difficult to replicate from zero |
| Trailer/marketing generation | Saturated | TRAILR.ai is live doing AI-driven clip discovery and campaign-ready asset generation; every major studio is already running internal AI marketing pipelines |
| Streaming acquisition analytics | Closed market, not accessible | Netflix and Amazon build this in-house on proprietary watch-through and drop-off data; this isn't a market a startup can sell into, because the only companies with a real need for it are also the only companies with the data to build it themselves |
| **Rights clearance / chain-of-title** | **Open** | Existing tools (general documentation trackers) help a production *document* clearance decisions after they're made manually; none of them actively, autonomously research ownership and chase clearance status to completion. This is the gap Lienmark is built to fill. |
| **Cross-vendor VFX cost/scope-drift governance** | **Open** | Individual VFX studios track their own shots through their own internal systems (ftrack, Flow); no tool gives a studio the *cross-vendor* view across multiple external vendors simultaneously — see §5 for the full second-product-line rationale |

## 3. Buyer segment — deliberately narrow, and why

Indie filmmakers are, deliberately, not the primary target buyer, despite being the segment with arguably the most acute day-to-day pain. The reasoning:

- **Cash-poor**: indie productions are chronically underfunded relative to their ambitions, and rights clearance competes against every other line item for a nearly-nonexistent discretionary budget
- **One-off projects**: an indie filmmaker making one film has no reason to invest in a recurring tool relationship — they need clearance once, for one project, and then they're gone
- **No recurring budget line**: there's no institutional buyer inside an indie production who owns "compliance tooling" as an ongoing responsibility

The actual buyer segment, in priority order:

1. **Completion bond companies** — these firms underwrite production completion risk professionally, as a business, across many productions simultaneously. They currently pay humans to do exactly the research Lienmark automates, and they have both the budget and the repeat-purchase pattern that indie filmmakers lack.
2. **E&O (Errors & Omissions) insurers** — clearance quality is a direct input into how these firms price risk. A Lienmark clearance certificate is not just a nice report; it's underwriting-relevant data these companies would pay for directly.
3. **Post-production supervisors at mid-size indie/documentary production companies** — these are the people who would actually run the day-to-day workflow, and mid-size companies (as opposed to true micro-indies) have real, if modest, operational budgets and faster sales cycles than a major studio's procurement process.
4. **Major studios (Phase 2+, not immediate)** — the enforcement side of this problem (verifying their own IP isn't being scraped or misused by AI models) is a longer-term, larger-contract opportunity, but studio sales cycles are long and this is realistically a later-stage expansion, not a first customer.

## 4. Phase 2 — Lienmark Synthetic

**Architectural addition alongside the feature set below: the planning orchestrator.** Everything in the MVP (`02-mvp-scope.md`) is a fixed pipeline with real agentic reasoning inside each step, plus bounded local adaptations (research reformulation, a callable human-in-the-loop action) — but the sequence of steps itself never varies per document. Phase 2 is the right point to build a genuine planning orchestrator that dynamically decides pipeline shape per document, rather than executing an invariant sequence — the real, larger step toward full agentic architecture (see `25-agentic-maturity-roadmap.md` for the complete reasoning on why this is deliberately deferred past the hackathon, and `09-agent-orchestration.md` §9 for the specific, corrected recommendation that this is the point at which LangGraph becomes the right orchestration framework, reversing the MVP's native-ADK choice for this specific capability only).

**Timing rationale:** this phase is sequenced immediately after MVP validation specifically because it's riding a *live, currently-unfolding* regulatory shift, not a speculative future trend. Major studios have already moved from complaints to formal cease-and-desist actions against AI video generation platforms, and SAG-AFTRA/MPA guidance is actively tightening around consent for synthetic performers. Waiting on this phase risks building it after the regulatory window has already normalized into settled practice that competitors have caught up to.

**Full feature set:**

- **PersonaLock** — a synthesized talent right-of-publicity guardian. Parses talent contracts to map the exact scope of consent for digital replication (geography, duration, technology type), then scans final delivered assets to flag instances of digital face-swapping or voice cloning, cross-referencing each detected instance against the specific consent rider that governs it. Non-compliant synthetic shots halt the export process pending executive review or an additional talent payout.
- **GlitchAudit** — a third-party generative AI asset verifier. Flags vendor use of un-cleared commercial AI generation tools inside delivered assets, since a vendor quietly using an uncertified AI tool to fill in background environments or textures can expose the studio to inherited copyright liability the studio never agreed to take on.
- **VoiceProof** — an AI ADR (automated dialogue replacement) dialogue provenance ledger. As synthetic voice work becomes more common in post-production, studios need to be able to prove to actors' estates and guilds that any synthesized voice was generated exclusively from legally-approved training data, not scraped internet audio. This agent watermark-checks and hash-verifies delivered audio against known-approved training sets.
- **PromptProbe / IP-Quarantine** — monitors internal generative-AI tool usage (e.g., a production designer using an AI image tool for concept art) to detect and prevent the studio's own proprietary script or character IP from being fed into a third-party model's training loop, which would permanently and irreversibly compromise future copyright enforceability.
- **CastTrack** — a background/extra digital-double usage auditor. As digital scanning of background talent becomes standard for crowd scenes, this agent cross-references how many times and in which sequences a specific extra's scanned likeness was reused against their original contracted usage scope, flagging any reuse that exceeds the union-negotiated boundary.

**Why this is a natural extension, not a pivot:** every feature in this phase reuses the exact same core mechanic already built for the MVP — extract a claim, verify it against a source of truth, log it immutably, score confidence, route uncertain cases to a human. The only thing that changes is *what kind* of claim is being verified (synthetic-media consent, rather than pure ownership/licensing). This is precisely why the MVP's agent architecture was built generically around "claims" and "findings" rather than hardcoding "music licensing" as a special case.

## 5. Phase 3 — Lienmark Territory: the full compliance operating system

This is the phase where the product stops being a tool a studio chooses to use and becomes infrastructure the surrounding ecosystem (insurers, bond companies, and eventually regulators) increasingly *requires*.

**Full feature set:**

- **TerritoryLock** — an international media distribution window compliance engine, tracking the complex matrix of regional theatrical/streaming holdback windows and flagging any scheduled release that would breach a still-active exclusivity window in a given territory.
- **GeoBan** — an adaptive regional content compliance guard, monitoring shifting international censorship board rules and flagging content elements (historical map depictions, political iconography, sensitive themes) that would trigger a ban or forced edit in a specific market.
- **TaxShield** — a cross-border tax rebate compliance auditor. Regional film tax incentives typically require a minimum percentage of spend to occur within the incentivizing jurisdiction; this agent tracks live production spend against that threshold and flags risk of a retroactive multi-million-dollar clawback if a vendor relationship accidentally tips the production below the required ratio.
- **GuildGuard** — a SAG-AFTRA/DGA/WGA residuals calculator and compliance ledger, automating the notoriously complex process of calculating downstream residual payments owed to actors and directors across theatrical, streaming, and international distribution windows, each governed by different multi-hundred-page guild rulebooks.
- **FontProof** — a typographic license auditor for in-scene graphic assets (prop documents, street signage, title sequences), since a font licensed only for personal use that ends up in commercial theatrical distribution can trigger a real, and surprisingly common, retroactive claim from a type foundry.
- **LocClear** — a physical location agreement boundary compliance guard, cross-referencing signed location contracts (geographic boundaries, permitted hours) against live GPS telemetry from production equipment to flag encroachment before it becomes a trespassing dispute.
- **PropGuard** — a product placement and trademark collision inspector, flagging real-world branded props used in narratively compromising contexts (a crime scene, drug use) that could expose the studio to a trademark tarnishment claim.
- **MinorGuard** — an international child-labor and entertainment compliance tracker, monitoring on-set time logs against the specific (and internationally varying) legal work-hour limits for minor actors, with proactive alerts before a legal threshold is breached rather than after.

**The endgame adoption mechanic:** "Lienmark Certified" becomes a credential vendors and productions need in order to satisfy insurer and completion bond underwriting requirements — mirroring the exact adoption dynamic that made SOC 2 compliance a de facto requirement in enterprise software procurement, even though SOC 2 certification is not legally mandated by any government. Nobody requires SOC 2 by law; the market requires it because the parties who bear risk (customers, auditors, insurers) collectively decided they wouldn't do business without it. That's the specific model Lienmark is aiming to replicate.

## 6. Second product line (Year 2, deliberately separate from the core roadmap) — DriftLock / Overrun

A structurally identical thesis, applied to a different fragmented ecosystem within entertainment: cross-vendor VFX budget and scope-drift risk, sitting between a studio and the multiple external VFX vendors it works with simultaneously but can't fully see across.

**Why this validates the core thesis rather than diluting it:** the fact that the exact same architectural pattern — ingest a change event, verify it against an external source of truth, log it immutably, score risk, arbitrate conflicts — maps cleanly onto a completely different fragmented ecosystem (vendor cost governance, not rights ownership) is itself evidence that the underlying company thesis (independent verification layer for fragmented, high-stakes entertainment workflows) is a genuine platform play, not a single-product idea that happened to work once.

**Phased build-out, mirroring the Lienmark phase structure:**

- **Phase 1 (own MVP-equivalent build):** ingest editorial EDL/XML diffs, map affected shots to their assigned external vendors, calculate the cost cascade across all affected vendors simultaneously, and cross-check vendor invoices against independently verifiable signals (frame counts, milestone velocity, review-latency data) rather than trusting vendor self-reporting.
- **Phase 2:** move earlier in the sales funnel with pre-contract vendor bid risk scoring and scenario simulation — catching risk before contracts lock rather than only after cost overruns have already occurred.
- **Phase 3:** deep technical pipeline certification (render efficiency auditing, cross-vendor asset handoff integrity, color/format drift detection) — only viable once vendors are already routing real production data through the platform, since this phase requires a level of trust and data access that has to be earned through the earlier phases first.

**Recommended track fit: Clickhouse, not Grafana.** This distinction matters and was deliberately reasoned through, not arbitrary: the agent's core reasoning loop is *querying* cost and vendor data at real-time scale to detect cascading overruns — that querying capability is what Clickhouse actually provides, and it's what the agent calls in order to think. Grafana, by contrast, would be a visualization layer sitting on top of already-computed results — genuinely useful for a human-facing dashboard, but not the thing doing the actual reasoning work inside the agent's decision loop. A hackathon-style build for this second product line should pick the partner that powers the *agent's* cognition, not just the partner that makes the prettiest dashboard.

**Sequencing relative to Lienmark:** deliberately built second, only once Lienmark has real customer traction and the team has genuine Google Cloud / data infrastructure experience already in place from building it. Same underlying architecture pattern, different customer segment, different partner integration — a lower-risk second bet than trying to build both simultaneously from zero.

## 7. Infrastructure migration path, phase by phase

| Phase | Storage | Reasoning |
|---|---|---|
| Hackathon MVP | Firestore | Fast to build with no migrations required, sufficient for single-demo-production scale, integrates natively with Cloud Run and Agent Builder |
| Phase 2 | Cloud SQL (Postgres) | Real relational integrity becomes necessary once there are cross-production queries to run (e.g., "show every unresolved music claim across all productions covered by insurer X"), and Postgres provides proper row-level audit logging, which compliance-focused buyers will eventually ask about directly and specifically |
| Phase 3 | Graph database (Neo4j, or a Postgres graph extension such as AGE) alongside Postgres | Chain-of-title is structurally a graph, not a flat relational shape — ownership assignments, option chains, and estate transfers all involve traversal-style queries ("who owns this now, given three prior assignments and one estate transfer") that graph databases handle far more naturally than repeated relational joins |

| Phase | Auth | Reasoning |
|---|---|---|
| Hackathon MVP | None | A single demo instance has no multi-user isolation requirement |
| Phase 2 | Firebase Auth / Google Identity Platform | Multi-tenant data isolation becomes a genuine, non-optional requirement the moment there are two paying customers whose claim data must never be visible to each other |

## 8. What NOT to build, even post-MVP, without a specific paying customer actively pulling for it

This section exists because ambitious roadmaps have a natural tendency to drift toward scope creep once early traction creates momentum. These are deliberate boundaries:

- **Anything indie-filmmaker-facing as a primary product** — this is the wrong buyer segment (see §3), and building for it would mean optimizing for a customer who structurally cannot sustain a real business
- **A general-purpose entertainment analytics platform** — this would dilute the verification-ledger core into something broader and less defensible; the moat comes from being the mandatory, trusted, independent record, not from being a broad analytics dashboard
- **Any video or content generation feature, of any kind** — this is a different company with a different thesis entirely (content creation vs. content verification), and the temptation to bolt on "and also we generate trailers" should be actively resisted, since it would blur the "independent, trusted third party" positioning that the whole moat depends on. A verification layer that also generates content for the parties it's supposed to be independently verifying would undermine its own credibility.
