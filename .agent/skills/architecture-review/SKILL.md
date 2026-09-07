---
name: architecture-review
description: >-
  Produce and gate a pre-flight architecture plan before any code is written (Primary/Root Agent only).
  Use when planning non-trivial code modifications, new features, or architectural changes,
  or when the user requests /architecture_review.
---

# Architecture Review Skill

Produce and gate a pre-flight architecture plan before any code is written.

> **CRITICAL FOR SUBAGENTS**: If you are a subagent, DO NOT run this workflow. You have already been granted execution approval by your parent agent. Proceed directly to implementation and testing.

## Workflow Instructions

1. **Scope Confirmation**: Restate the task in one sentence to confirm scope.
2. **Convention Discovery**: Scan the relevant part of the repo to identify existing naming, export, and architecture conventions (do not skip this — see `architecture.md`).
3. **File Tree Delta**: Produce a markdown file tree block showing every file to be created, modified, or deleted, using `└──` notation. (If triggered by `file-split`, clearly identify extracted responsibilities and modular boundaries).
4. **Data-Flow Diagram**: Produce a concise ASCII data-flow diagram showing how data moves between the proposed modules.
5. **Implementation Plan**: Produce a structured, bulleted implementation plan.
6. **Blast Radius Analysis**: Produce a one-line "blast radius" note stating what existing functionality this touches.
7. **Security & Dependencies**: Note any new dependency (with justification/license) or any security-relevant assumption (auth, data exposure) the plan introduces.
8. **Adversarial Critic Pass**: Before presenting the plan, argue against your own plan as a skeptical senior reviewer would. State the single most likely way this plan fails, gets rejected in review, or breaks under an edge case. Either revise the plan to address it, or state explicitly why it's an acceptable risk. Do not skip this step.
9. **Deep Analysis Trigger**: If the task involves genuine design uncertainty (more than one reasonable architecture, an unfamiliar part of the codebase, security/concurrency/data-migration stakes), invoke the `deep-analysis` skill (`/deep_analysis`) first, then return to step 3 with its output. Routine, well-understood tasks skip this.
10. **Approval Gate (Primary / Parent Agent Only)**: When operating as the primary agent interacting directly with the user, stop. Output exactly:
    > "Please review the architecture plan above. Reply with 'APPROVED' to execute or specify changes."
    Do not call any file-writing tool until the user's next message contains explicit approval.
11. **Subagent Autonomous Execution Exemption**: Subagents dispatched by a parent agent do NOT halt for user approval and must NEVER send unexecuted plans back to the parent. Once dispatched, subagents formulate their plan and **execute it immediately** (make edits, run tests, verify). Subagents report back only completed execution results, diff stats, and test logs.
12. **Scope Creep Detection**: If, during implementation, a file outside this plan turns out to be necessary, stop immediately, show only the delta, and re-confirm before continuing (primary agent re-requests user approval; subagent checks within its parent-assigned scope).
