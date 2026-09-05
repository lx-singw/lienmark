# Lienmark: 3-Minute Hackathon Demo Script

> **Authoritative Demo Script**: Derived from [`docs/DEVPOST_SUBMISSION.md`](../docs/DEVPOST_SUBMISSION.md) and [`docs/winning/05-demo-and-submission-playbook.md`](../docs/winning/05-demo-and-submission-playbook.md).
**Track:** Parallel Track ($15,000 Prize Pool) | **Challenge:** Agentic Cinema  
**Target Duration:** ~2 minutes 45 seconds  
**Visual Style:** Screen recording of the hosted Reviewer Dashboard, split-screen terminal execution, and active Parallel Search API traces. Zero cinematic fluff; 100% functional software proof.

---

## Act I: Problem Framing & The Magic Moment (0:00 - 0:40)

**[0:00 - 0:15] Visual:** Screen opens on the Lienmark Reviewer Dashboard. The header displays *Shadows Over Broadway — Locked Script Version 7*. The left panel displays **12 reviewed counsel approvals** across script scenes.

**Speaker (Voiceover):**  
"In film production, the hard problem in rights clearance isn't finding an initial copyright record once. It’s knowing whether yesterday’s legal sign-off still protects today’s new cut and changing external evidence. That silent divergence is **clearance drift**—the single biggest driver of preventable delivery delays and multi-million-dollar E&O insurance claims."

**[0:15 - 0:40] Visual:** User clicks **"⚡ Ingest V8 & Detect Drift"**. In under 600 milliseconds, the metric ribbon snaps:
- Total Claims: 12
- Carried Forward: 10 (Green)
- Reopened (Drift Detected): 2 (Amber)

**Speaker:**  
"Lienmark is clearance change control for E&O. It binds every counsel approval directly to its creative usage, contractual scope, and external evidence snapshot. When Revision 8 is ingested, Lienmark does not run a wasteful, noisy 12-item rescan. It traverses the dependency graph, safely carries forward ten unaffected decisions, and instantly reopens exactly two—each with an explicit, machine-readable reason code."

---

## Act II: Two Drifts & Targeted Parallel Search Grounding (0:40 - 1:50)

**[0:40 - 1:20] Visual:** User clicks Item 11: *Scene 42 — Noir Detective Magazine Poster*. Right-hand drawer reveals V7 (2-second background blur) vs V8 (14-second focal close-up with character dialogue). Reason code: `CREATIVE_CONTEXT_ALTERED` / `LICENSE_SCOPE_CHANGED`.

**Speaker:**  
"Here is creative drift. In Version 7, this 1946 detective magazine poster was approved as incidental background dressing. But Gemini 2.5 Flash analyzes the semantic delta in Version 8: the director brought the poster into a 14-second focal close-up where the lead actor reads the headline aloud. Our deterministic invalidation engine recognizes that the factual predicate of the de minimis sign-off collapsed, immediately flagging `LICENSE_SCOPE_CHANGED`."

**[1:20 - 1:50] Visual:** User clicks Item 12: *Scene 18 — Midnight Serenade*. Script context is unchanged (speakeasy jazz cue). Parallel Search API card displays live 200 OK query, source citation (ASCAP Repertory & Billboard Rights Bulletin), and `CONTRADICTORY` stance showing August 2026 rights assignment to Vanguard Media Holdings.

**Speaker:**  
"Now watch external evidence drift. The script for this jazz cue did not change by a single syllable. But rights in the real world did. Parallel Search API executes at runtime to refresh the external copyright registry. Parallel retrieves live ASCAP bulletin records proving exclusive synchronization rights were reassigned to Vanguard Media last month. Parallel keeps the evidence current; Lienmark keeps the dependent counsel decision aligned with it, catching the contradiction before post-production wraps."

---

## Act III: Graph Economy & Human Counsel Re-Attestation (1:50 - 2:35)

**[1:50 - 2:15] Visual:** Trace panel displays the 83% search reduction (2 targeted API calls instead of 12 full rescans). Shows fail-closed invariants and reproducible timings.

**Speaker:**  
"Notice the architectural discipline: our dependency graph eliminated 83% of redundant API queries by dispatching live searches only to affected nodes. And our policy is strictly fail-closed: public evidence informs review, but never replaces human legal authority. Missing, conflicting, or stale evidence automatically escalates to counsel."

**[2:15 - 2:35] Visual:** Counsel Re-Attestation modal. User re-attests Item 11 with Public Domain renewal research, leaves Item 12 unresolved, and clicks "Export Exceptions Schedule". The Form E&O-2026 Underwriter Exceptions Schedule renders showing 10 carried forward, 1 re-attested, and 1 active unresolved exception.

**Speaker:**  
"In the reviewer interface, counsel re-attests the poster under public domain renewal findings and marks the jazz cue as an active exception for replacement. Lienmark compiles the reconciled audit trail into a version-bound Form E&O-2026 Exceptions Schedule, giving production counsel and E&O underwriters complete transparency into what was cleared, what changed, and what risks remain."

---

## Act IV: Architectural Trace & Close (2:35 - 2:48)

**[2:35 - 2:48] Visual:** Execution trace showing end-to-end timing: Gemini structured output, Parallel Search latency, and deterministic verification. Closing slide with GitHub repository link and hosted Cloud Run URL.

**Speaker:**  
"From script cut to underwriter schedule: Lienmark provides clearance change control for E&O. Built on Google AntiGravity, Gemini 2.5 Flash, and Parallel Search."
