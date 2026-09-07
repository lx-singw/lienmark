---
description: Produce and gate a pre-flight architecture plan before any code is written (Primary/Root Agent only)
---

> **CRITICAL FOR SUBAGENTS**: If you are a subagent, DO NOT run this workflow. You have already been granted execution approval by your parent agent. Proceed directly to implementation and testing.

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
8. **User Approval Gate (Primary User-Facing Agent Only)**:
   If and only if you are the main agent chatting with the human user, stop and output:
   "Please review the architecture plan above. Reply with 'APPROVED' to execute or specify changes."
   Do not call any file-writing tool until the user's next message contains explicit approval.
9. **Subagents NEVER Output Approval Prompts**:
   Subagents must NEVER output the "Please review the architecture plan..." prompt or wait for approval. Subagents MUST execute their code and testing immediately upon receiving the task.
10. If, during implementation, a file outside this plan turns out to be necessary,
    stop, show only the delta to steps 3–4, and re-confirm before continuing (primary agent re-requests user approval; subagent checks within its parent-assigned scope).
