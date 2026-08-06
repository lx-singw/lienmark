# Vision & Mission

## Mission (now — what Lienmark does today)

Give every high-stakes production an independent, sourced, auditable answer to "is this actually clear to use" — replacing manual, expensive, invisible rights research with an agentic verification ledger.

## Vision (the monopoly picture)

Entertainment is the proof, not the ceiling. Lienmark's actual architecture — extract a claim, verify it against a live, credible source, log it immutably, arbitrate conflicting evidence deterministically, escalate uncertainty to a human, produce a sourced report — is not an entertainment-specific pattern wearing industry-specific clothes. It's a general answer to a general problem: **in any market where money or legal exposure changes hands based on a claim about ownership, origin, or authenticity, and where the parties involved can't fully trust each other or see each other's records, someone has to independently verify the claim before the deal closes.** Title insurance solved a narrow version of this for real estate, generations ago, with manual processes. Lienmark's bet is to become the general-purpose version of that role — an agentic verification layer — for every industry that has the same underlying shape, entertainment first.

The long-run picture, stated plainly: **not a company that sells one vertical product, but the infrastructure layer other companies' trust decisions run on** — the way Plaid became the layer bank-account verification runs on for fintech, or the way Stripe became the layer payment execution runs on for e-commerce. Neither Plaid nor Stripe invented the underlying need (banks and payment rails already existed); they built the trusted, automated, auditable connective layer that made the existing need fast and reliable instead of manual and slow. That is the shape of the company this document describes.

## The core mechanic, named explicitly and abstracted from entertainment

Every vertical below is a re-application of the same five-part pattern already built for entertainment (`09-agent-orchestration.md`), with only the claim types, source registries, and buyer segment changing:

1. **Ingest** — a document, filing, dataset, or transaction that contains one or more claims requiring verification
2. **Extract** — identify the discrete, individually-verifiable claims within it (entertainment: a music cue, a brand mention; another vertical: a deed transfer, a training-data source, a beneficial owner)
3. **Verify** — check each claim live against a credible external source of truth, with the finding sourced and cited, never asserted without evidence
4. **Log** — write the claim and finding to an append-only, versioned ledger, so the record compounds and remains auditable over time rather than resetting with every check
5. **Arbitrate & escalate** — deterministically score confidence, resolve or flag conflicting sources, and route genuine uncertainty to a human rather than forcing an automated verdict

This is the actual intellectual property of the company, in the sense that matters most: not the entertainment-specific claim taxonomy, but the discipline of building *this exact pattern* correctly — deterministic where it needs to be, sourced everywhere, immutable by construction, honest about its own uncertainty. Anyone can copy the code (`17-moat-mechanics.md`); replicating the discipline behind getting this pattern right, repeatedly, across verticals, is harder.

## Expansion criteria — the rubric, so vertical selection isn't vibes

Not every industry with an "ownership" or "authenticity" problem is a good next vertical. Each candidate below was evaluated against the same five questions used to validate entertainment in the first place (`03-post-mvp-scope.md` §2):

1. **Is there a real, quantifiable cost to the current manual process?** (Entertainment: $51M/year floor, `04-prd.md` §1.1)
2. **Is the field genuinely open, or already dominated by entrenched, well-funded incumbents?** (This is the single most important filter, and the one most tempting to skip when a vertical sounds exciting — see the real estate section below for what happens when this check is done honestly instead of assumed away.)
3. **Is there a regulatory or market tailwind making the problem more urgent now, not just persistently present?**
4. **Are the parties involved structurally unable to fully trust each other or see each other's records** — i.e., does the problem actually need an *independent* verifier, or would a better internal tool solve it just as well?
5. **Does a credible, checkable external source of truth exist to verify claims against** — Lienmark's mechanic depends on there being something real to check claims against; a vertical where the "truth" is itself unverifiable or purely subjective doesn't fit the pattern.

## Tier 1 — the strongest near-term candidates, validated with real evidence

### AI training data provenance & rights verification

**The problem:** every company training or fine-tuning an AI model needs to know, and increasingly must legally document, the rights status of every source in its training data. This is not a hypothetical future concern — <cite index="52-1">under the EU AI Act, providers of general-purpose AI models are now required to publish a public summary of the datasets used to train the model, disclosing what type of data was used and respecting copyright opt-outs, with this obligation taking effect starting in 2026.</cite> <cite index="49-1">Failing to document data provenance is what separates a defensible AI startup from a legally exposed one — the largest copyright settlement in U.S. history turned on how training data was sourced, not on the act of training itself.</cite>

**Why this fits the rubric better than almost any other candidate:**
- **Cost/urgency:** legally mandated disclosure (EU AI Act) with real, current litigation exposure — not a someday problem
- **Open field:** the search for existing solutions surfaced law firms and compliance consultancies (Astraea Counsel, various AI-governance advisories) and data marketplaces selling *pre-cleared* datasets (DepositPhotos), but no clearly dominant, agentic, automated verification product that audits a company's *existing* training data provenance the way Lienmark's mechanic would. This looks like a genuine product gap, not an assumed one.
- **Structural trust problem:** an AI company auditing its own training data has an obvious incentive to find it clean — exactly the same structural conflict-of-interest that makes an *independent* verifier valuable in entertainment (`03-post-mvp-scope.md` §1)
- **Direct narrative connection to the existing thesis:** this isn't an unrelated new market — it's the *same regulatory story* already cited as entertainment's "why now" (`14-sources-appendix.md`'s Seedance dispute), generalized from "AI-generated entertainment content" to "AI training data" broadly. A team that already built claim-verification-and-ledger infrastructure for one side of the AI-copyright story is unusually well-positioned to build the other side.

**Sequencing note:** of every vertical in this document, this is the one worth taking most seriously as the actual Phase 2/3-adjacent expansion, not a distant "someday" — it could plausibly be pursued in parallel with entertainment Phase 2 (`03-post-mvp-scope.md` §4) rather than strictly after it, given how directly the underlying claim-verification mechanic transfers.

### Art & collectibles provenance

**The problem:** authenticating fine art, verifying an unbroken chain of legitimate ownership, and screening against known stolen/looted-art registries (Nazi-era restitution claims remain an active, real legal category decades later) is currently a slow, expert-dependent, manual process — auction houses and insurers both bear real risk from provenance fraud and forged documentation.

**Why this fits well:** the claim types map almost directly onto entertainment's own schema (`06-data-schema.md`) — an artwork's ownership history is structurally similar to a chain-of-title problem, and the buyer segment (fine-art insurers, auction houses) directly parallels the E&O insurer / completion bond relationship already established. **Caveat, stated honestly:** this vertical was not independently re-verified with fresh sources in this pass — it's included on the strength of well-known, longstanding industry problems (art forgery and looted-art restitution are extensively documented historically) rather than a fresh, current market-sizing search. Treat as a strong hypothesis, not yet validated to the same standard as entertainment or AI training data.

### Patent & IP chain-of-assignment verification

**The problem:** determining who actually owns a patent today, after decades of corporate acquisitions, spin-offs, and assignments, is a real and recurring diligence problem in tech M&A and licensing — a chain-of-title problem for intellectual property, structurally identical to entertainment rights clearance but for patents instead of creative works.

**Why this fits well:** same mechanic, adjacent buyer (corporate legal/M&A diligence teams instead of entertainment insurers), and a natural extension of skills the team will already have built (rights research, ownership chain verification, source-cited reporting). **Same caveat as above** — included on structural reasoning, not freshly verified market data in this pass.

## Tier 2 — real, regulation-driven, but requiring more validation before committing

- **Beneficial ownership / KYC-AML chain verification** — determining who ultimately owns or controls a corporate entity, especially shell companies, is an enormous and growing compliance requirement globally (driven by U.S. and EU beneficial-ownership-registry regulations). Huge potential TAM, but a heavily regulated entry point with serious compliance/licensing barriers to entry that entertainment and AI-provenance don't carry — worth flagging as higher-friction to enter, not lower-value.
- **Carbon credit / ESG claim verification** — verifying that a carbon offset or ESG claim is real, not "greenwashing," is a fast-growing scrutiny area with real regulatory tailwind. Structurally a strong fit for the mechanic (verify a claim against a source of truth, log immutably, flag disputes) but not independently market-sized in this research pass.
- **Academic credential / diploma-mill fraud verification** — a real, persistent fraud category (employment/credential fraud), structurally a good fit, but a smaller and less urgent TAM than the above candidates on current evidence.

## Tier 3 — real problems, but the honest answer is "not yet, or not directly"

### Real estate deed-fraud / chain-of-title monitoring

**Include this because it's the example that prompted this document — and because being honest about it is more valuable than pretending it's open.** The research is unambiguous: this is a real, large, and currently *contested* space, not blue ocean.

- <cite index="45-1">First American Title — one of the largest title insurance underwriters in the country — now offers free property title monitoring and fraud alert services as part of its AgentNet platform, citing FBI-reported cyber-enabled losses exceeding $13.7 billion in 2024.</cite>
- <cite index="40-1">EquityProtect, a property-record encryption and monitoring service, won a 2025 "Best of Proptech" award from Inman</cite> — a real, funded, recognized competitor already doing close to exactly the "chain-of-title fraud monitoring" mechanic described.
- A separate competitor, Title Barrier, is also active in this exact space, and — notably — <cite index="43-1">its own founder publicly cautions that title-theft risk is sometimes oversold by companies with a financial incentive to make it sound scarier than it is</cite>, which is itself a useful signal about how crowded and marketing-driven this space has already become.
- The broader title insurance industry that inspired Lienmark's positioning analogy (`03-post-mvp-scope.md` §1) is itself a mature, heavily regulated, capital-intensive, multi-billion-dollar industry dominated by a handful of giant underwriters (First American among them) — entering it directly would mean competing against the very incumbents the business model was inspired by, not finding open space adjacent to them.

**The honest conclusion:** real estate is a poor direct-entry candidate specifically *because* it's the industry the positioning analogy came from — the analogy is a good teaching tool for explaining Lienmark's business model to an outsider, but it is not, itself, a validated next market. If this space is ever entered, it would need a genuinely differentiated angle distinct from what First American, EquityProtect, and Title Barrier already do — not a straightforward port of the entertainment playbook.

### Vehicle title fraud

Similar shape to real estate, similarly likely to be dominated by entrenched incumbents (Carfax, AutoCheck) — not independently researched in this pass, but flagged as probably following the same "already contested" pattern as real estate rather than assumed open.

## Sequencing — how this actually rolls out, disciplined against premature horizontal expansion

**The single most important operating principle in this entire document:** none of the above matters if entertainment isn't won first. `03-post-mvp-scope.md` §8 already establishes this discipline for entertainment-adjacent scope creep ("what NOT to build without a specific paying customer pulling for it") — the same discipline applies here, at a larger scale. A company that starts building AI-training-data-provenance features before it has real entertainment customers and a real, working ledger is repeating the single most common startup failure mode: spreading horizontally before proving the pattern works vertically, once, for real.

**Phase 0 (now):** Win the hackathon, ship entertainment MVP, get real customer usage — everything already specified in `02-mvp-scope.md` through `10-build-timeline.md`.

**Phase 1 (entertainment, proven):** Entertainment Phase 2/3 as already scoped (`03-post-mvp-scope.md` §4-5) — synthetic rights, then the full compliance operating system. This needs to actually work, with real paying customers, before anything in this document becomes a real resourcing decision rather than a vision-deck slide.

**Phase 2 (the first genuine horizontal expansion, if and when entertainment is real):** AI training data provenance — the strongest candidate above, both on evidence and on how directly the underlying mechanic and even the regulatory narrative transfer. This is the most defensible "second vertical" precisely because it requires the least reinvention of the core pattern.

**Phase 3+ (genuinely future, sequenced by then-current evidence, not this document alone):** Art & collectibles, patent chain-of-title, and the Tier 2 candidates — each would need its own dedicated validation pass (the same rigor applied to entertainment and AI-provenance here) before being treated as more than a hypothesis.

**A standing rule worth stating explicitly:** before entering any vertical from this document, re-run the same two checks that mattered most for entertainment and AI-provenance — a real, current competitive-landscape search (not an assumption that the field is open), and a real, sourced cost/TAM estimate. The real estate section above exists specifically as a worked example of what happens when that discipline is applied honestly instead of skipped because a vertical sounds appealing.

## The one-sentence version, for a future pitch

*"We're proving the verification-ledger pattern in entertainment first — the hardest part isn't the idea, it's building the discipline to do sourced, deterministic, auditable verification correctly. Once that's proven, the same pattern extends to every industry with the same underlying problem — starting with AI training data provenance, which is, not coincidentally, the same regulatory story we're already riding in entertainment, one step removed."*
