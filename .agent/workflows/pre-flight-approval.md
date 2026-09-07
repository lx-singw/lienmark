---
trigger: always_on
---

# Pre-Flight Approval Gate

Never write, modify, or delete a source file before the plan for it has been approved.

Before any code generation on a non-trivial task, run the `/architecture_review`
workflow (see .agent/workflows/architecture_review.md) and stop. Do not proceed to
code until the user replies "APPROVED" or equivalent explicit go-ahead.

If, mid-implementation, you discover you need to touch a file that was not in the
approved file tree: **stop immediately**, show only the delta (new file tree entries +
updated flow), and re-request approval before continuing. Do not quietly expand scope.

## Subagent Autonomous Execution Rule (Parent-Gated, Worker-Executed)
- **Inherited Approval**: When a parent agent spawns or dispatches a subagent to carry out an implementation or refactoring task, the subagent **inherits execution approval** from the parent agent.
- **Plan and Execute Immediately**: Subagents MUST create their internal plan and **immediately execute it** (write files, modify code, run tests) without stopping to ask the parent or user for approval, and without returning unexecuted plans.
- **Do Not Send Plans Back to Parent**: Subagents must NEVER send raw implementation plans or unexecuted code back to the parent agent. Subagents report back only after execution is complete, providing concise diff metrics, verification logs, and status.
- **Scope Boundary**: Subagents remain strictly bounded to the files and components explicitly assigned to them by the parent agent.

Exception: trivial, single-file, clearly-scoped requests (e.g. "fix this typo," "add a
console.log here") do not need the full checklist — use judgment, but when in doubt,
show the plan.

Irreversible or destructive actions — deleting files outside the approved plan,
altering a database schema, force-pushing, rewriting git history — always require
their own explicit confirmation. A general "APPROVED" on the architecture plan does
not cover these; ask again, specifically, at the moment you're about to do it.
