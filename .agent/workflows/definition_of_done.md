---
description: Final checklist before telling the user a task is complete
---

1. Confirm the implementation matches the approved plan from architecture_review.md,
   or that every deviation was re-approved.
1a. Reconcile narration against diff — for every distinct action you stated you'd
    take (e.g. "extract X into its own file," "relocate Y to a helper"), confirm
    there is an actual corresponding file creation or diff. If something you said
    you'd do isn't reflected in the real changes, either go do it now or say plainly
    in your summary that it wasn't done and why. Never let the stated plan imply
    something happened that the diff doesn't show — this is checked separately from
    "does it build," which only proves compilation, not plan fulfillment.
2. Run `/quality_gate` if it hasn't already been run for this change set.
3. Confirm: no naked catch blocks, no `any` escapes, no hardcoded secrets
   (grep for common patterns: `sk-`, `AKIA`, `-----BEGIN`, etc. as a sanity check —
   not a substitute for a real secrets scanner if the repo has one).
4. Confirm any new dependency is justified, license-checked, and in the lockfile.
5. State explicitly, in plain language, what the user can now do that they couldn't
   before — not just "tests pass."
6. State any rule conflict or tradeoff made during the task (architecture.md's
   conflict-resolution clause) — don't bury it in a code comment only.
