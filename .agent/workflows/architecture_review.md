---
description: Produce and gate a pre-flight architecture plan before any code is written
---

1. Restate the task in one sentence to confirm scope.
2. Scan the relevant part of the repo to identify existing naming/export/architecture
   conventions (do not skip this — see architecture.md).
3. Produce a markdown file tree block showing every file to be created, modified, or
   deleted, using `└──` notation.
4. Produce a short ASCII data-flow diagram showing how data moves between the
   proposed modules.
5. Produce a bulleted implementation plan.
6. Produce a one-line "blast radius" note: what existing functionality this touches.
7. Note any new dependency (with justification/license) or any security-relevant
   assumption (auth, data exposure) the plan introduces.
7a. Adversarial critic pass — before presenting the plan, argue against your own
    plan as a skeptical senior reviewer would. State the single most likely way this
    plan fails, gets rejected in review, or breaks under an edge case. Either revise
    the plan to address it, or state explicitly why it's an acceptable risk. Do not
    skip this step by declaring the plan obviously correct.
7b. If the task involves genuine design uncertainty (more than one reasonable
    architecture, an unfamiliar part of the codebase, security/concurrency/data-
    migration stakes) — stop here and run `/deep_analysis` first, then return to
    step 3 with its output. Routine, well-understood tasks skip this.
8. Stop. Output exactly: "Please review the architecture plan above. Reply with
   'APPROVED' to execute or specify changes."
9. Do not call any file-writing tool until the user's next message contains explicit
   approval.
10. If, during implementation, a file outside this plan turns out to be necessary,
    stop, show only the delta to steps 3–4, and repeat step 8 before continuing.
