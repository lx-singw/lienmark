# Lienmark — Executive Summary

*One page, deliberately. If someone reads nothing else in this package, this is the page.*

## The problem
Every film or TV production carries 200+ unresolved rights claims — music, footage, brands, real people, AI-assisted content. Clearing them is manual, costs $250-700/hour in entertainment counsel, and stays invisible until it breaks a deal or triggers a lawsuit. Conservatively, this is a **$51M/year problem** among U.S.-based major productions alone (857 productions/year × 200+ claims × ~$300/claim — see `04-prd.md` §1.1 for the full sourcing).

## Why now
In February 2026, Disney, Paramount, and the MPA sent the industry's first-ever cease-and-desist letters from a major studio body to a generative AI company (ByteDance, over its Seedance model). SAG-AFTRA condemned it publicly. As of mid-2026, the dispute remains unresolved even as a more capable successor model has already launched. The regulatory ground is moving faster than manual clearance processes can track (full sourcing: `14-sources-appendix.md`).

## What Lienmark does
An agentic verification layer, built on Google's Gemini Enterprise Agent Platform and Parallel's Search API. Upload a script or cut; five agents (Intake, Research, Ledger, Risk Scoring, Report) extract every rights-triggering claim, research it live against the open web, log it to an immutable ledger, arbitrate conflicting sources deterministically, and produce a sourced, audit-ready clearance report — with any uncertain claim routed to a human, never auto-resolved on a guess.

## Who pays
Not indie filmmakers — they're cash-poor and one-off. The real buyers: **completion bond companies** and **E&O insurers**, who already pay humans to do this research and would pay for a faster, sourced, auditable version; and **post-production supervisors** at mid-size production companies as the faster-cycle entry point.

## The long-term bet
The real-estate title insurance model, applied to entertainment. Not a tool studios choose because it's good — a verification layer the surrounding ecosystem (insurers, bond companies) increasingly *requires*. Unglamorous, mandatory once adopted, hard to dislodge. The moat isn't the code (which is open-sourced for this hackathon) — it's the accumulated, verified ledger history and the switching cost once an insurer's underwriting workflow depends on it (full argument: `17-moat-mechanics.md`).

## Why nobody's already built this
Adjacent categories — script coverage, VFX budgeting, dubbing, piracy protection, trailer generation, streaming-acquisition analytics — are all saturated with funded, live competitors. Rights clearance specifically is open: existing tools document decisions a human already made; none actively research and verify ownership live (full competitive landscape: `03-post-mvp-scope.md` §2).

## Roadmap
**Now:** rights clearance core loop. **Phase 2:** synthetic/AI-content rights (talent consent, digital doubles), timed to the current regulatory moment. **Phase 3:** the full compliance operating system — territorial windows, tax rebates, union residuals — where "Lienmark Certified" becomes what insurers and bond companies require.

## Status
Built for **Agentic Cinema: The Blockbuster Hackathon** (Parallel track, Google Cloud, Sep 7 2026 deadline) as the deliberate first step of a real company, not a standalone competition entry — see `18-company-formation-readiness.md` for how the team is treating this as genuine pre-seed groundwork, not just a submission.

---
*Full documentation package: 19 documents covering hackathon scope, product requirements, technical architecture, go-to-market, and execution planning. This page is the map; everything else is the territory.*
