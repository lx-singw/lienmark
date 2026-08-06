# Judge Q&A Preparation — Anticipated Questions and Answers

**Why this document exists, and why it's higher-priority than it might first appear:** per `01-hackathon-scope.md` §1, this hackathon is judged entirely asynchronously — there is no live pitch, no Q&A round, no opportunity to clarify or defend a decision after submission. Every question a judge might silently ask themselves while watching the video or reading the repo has to already be answered *inside* those artifacts, or it never gets answered at all. This document exists to surface those questions now, while there's still time to build the answers into the video narration, the README, and the pitch deck — not to be read by a judge directly.

## Questions about the idea and market

**"Isn't this just RAG (retrieval-augmented generation) with extra steps?"**
No — and the distinction is worth being able to state crisply. RAG describes retrieving relevant context to inform a single generated answer. Lienmark does retrieve and inform, but the actual product is the **verification ledger** — an append-only, versioned, source-cited record designed to be trusted and audited by a third party (an insurer) over time, with deterministic scoring and multi-source conflict arbitration layered on top. A RAG chatbot answering "is this song cleared?" once, in a chat window, with no persistent audit trail, would not satisfy a completion bond company's actual requirement. The retrieval is a means; the ledger is the product.

**"Doesn't Vitrina or Filmustage already do this?"**
No — see `04-prd.md` §8 for the full answer. Short version: Vitrina is deal/vendor intelligence (announced 2021, now covering 360K+ companies — see `14-sources-appendix.md`); Filmustage is AI-assisted budgeting and scheduling via its "AI Dude" agent. Neither performs live, sourced, per-claim ownership verification against the open web, and neither maintains an immutable audit ledger. Worth naming both specifically and confidently if this comes up, since vague deflection ("we're different") reads worse than a precise, sourced distinction.

**"Why hasn't a large incumbent (LexisNexis, Thomson Reuters, or Google/Microsoft themselves) already built this?"**
This wasn't previously answered anywhere in the docs — worth having ready. Broad legal-research incumbents (LexisNexis, Thomson Reuters) serve general legal research across every industry, not entertainment-specific rights workflows with entertainment-specific claim types (music sync rights, right-of-publicity, VFX-adjacent IP). Big tech platforms have no existing trust relationship with entertainment-industry buyers (insurers, bond companies) and no reason to prioritize a vertical this specific. This is the classic startup wedge shape: a problem big enough to be a real business, specific enough that a horizontal incumbent has no natural reason to prioritize it ahead of larger, broader markets.

**"What's the actual market size?"**
$51M/year, conservatively, from U.S.-based major productions alone — the full sourced calculation is in `04-prd.md` §1.1. Have this number ready verbatim; it's the single most concrete, repeatable fact in the whole submission.

## Questions about the technology

**"What happens when Parallel returns nothing useful for an obscure claim?"**
This is explicitly designed for — see `04-prd.md` §5.4 and the Risk Scoring Agent spec in `09-agent-orchestration.md` §6. A low-confidence or ambiguous result routes to human review rather than forcing a confident verdict the system can't back up. This is a feature of the design, not a gap discovered under questioning — worth stating it that way rather than sounding defensive if it comes up.

**"How is 'deterministic' actually enforced, given LLMs are involved?"**
The pipeline is deliberately split: LLM-driven extraction (flexible, handles messy real-world input) feeds into rule-based, deterministic scoring (reproducible, auditable). The scoring function itself is not an LLM call — see the illustrative code in `09-agent-orchestration.md` §6. `tests/test_risk_scoring_determinism.py` exists specifically to make this a checkable claim, not just an assertion.

**"What stops a competitor from cloning this in a weekend?"**
The code isn't the moat, and that's deliberate — see `17-moat-mechanics.md` for the full argument. The moat is the accumulated, source-cited, immutable ledger data itself (which only exists after real usage, not on day one) and the switching cost once an insurer's underwriting workflow references a Lienmark score. A clone could replicate the architecture in a weekend; it couldn't replicate months of verified clearance history or an insurer's integrated workflow.

**"Why Firestore instead of a 'real' database for something claiming to be an audit ledger?"**
Firestore was a deliberate, scoped choice for hackathon timeline speed, with the actual immutability guarantee enforced at the security-rules layer regardless of the underlying database technology (see `06-data-schema.md` §3). The Phase 2 migration path to Postgres, and Phase 3 to a graph database, is planned and documented (`03-post-mvp-scope.md` §7) — this isn't an oversight, it's sequencing.

## Questions about the business and buyers

**"How do you make money if insurers and bond companies are slow enterprise sales?"**
Fair challenge, worth acknowledging directly rather than dodging: enterprise insurance sales cycles are genuinely long. The mitigation is sequencing — post-production supervisors at mid-size companies (§3 in `04-prd.md`) are the faster-cycle entry point, with insurer/bond relationships built in parallel as the ledger accumulates enough real usage data to be a credible underwriting input. This is stated as a hypothesis, not a solved problem — see the honest framing already built into `05-pitch-deck.md`'s business model slide.

**"What if Lienmark is wrong — who's liable?"**
This needed a real answer and didn't fully have one until `16-liability-and-trust-posture.md` — see that document for the full treatment. Short version: Lienmark surfaces risk and research; it does not replace legal counsel's final clearance decision, and that boundary needs to be explicit in any real terms of service, not just implied.

**"Is this really an entertainment company, or a generic compliance/verification platform wearing a cinema costume for the hackathon?"**
Worth being honest about this one internally, not just for judges: the core mechanic (extract a claim, verify against a source of truth, log immutably, score, arbitrate) is genuinely generalizable — that's *why* the DriftLock/Overrun second product line works (`03-post-mvp-scope.md` §6). But the specific claim types, buyer segments, and regulatory tailwind in this submission are entertainment-specific and were arrived at through real competitive research (`03-post-mvp-scope.md` §2), not chosen arbitrarily to fit the hackathon's theme. The honest answer: the architecture is general, the go-to-market is specifically and deliberately entertainment-first.

## The meta-question worth asking before submission

**If a judge only watches the video once, with no pause button, and never opens the repo — does the video alone answer the hardest 3-4 questions above?** If not, that's a narration gap worth closing before the final recording, not something to hope a generous judge infers.
