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

Exception: trivial, single-file, clearly-scoped requests (e.g. "fix this typo," "add a
console.log here") do not need the full checklist — use judgment, but when in doubt,
show the plan.

Irreversible or destructive actions — deleting files outside the approved plan,
altering a database schema, force-pushing, rewriting git history — always require
their own explicit confirmation. A general "APPROVED" on the architecture plan does
not cover these; ask again, specifically, at the moment you're about to do it.
