---
name: definition-of-done
description: >-
  Executes the final verification checklist before declaring a coding task complete.
  Use when completing tasks, before finalizing responses to the user, or when /definition_of_done is invoked.
---

# Definition of Done Skill

Enforce the final verification checklist before notifying the user that a task is complete.

## Verification Checklist

1. **Plan Compliance**: Confirm the implementation matches the approved plan from `architecture-review`, or that every deviation was explicitly re-approved.
2. **Reconcile Narration Against Diff**: For every distinct action stated in your plan (e.g., "extract X into its own file", "relocate Y to a helper"), verify that an actual file creation or git diff exists. If an intended change is not reflected in the real diff, either execute it immediately or explicitly disclose in the summary that it was omitted and explain why. Never allow narration to imply a change occurred that the diff does not show (compilation alone does not prove plan fulfillment).
3. **Quality Gate Pass**: Run `quality-gate` (`/quality_gate`) if it hasn't already been run for this change set.
4. **Hygiene & Safety Audit**:
   - No naked or empty `catch {}` blocks.
   - No `any` escapes without runtime validation.
   - No hardcoded secrets (check for common patterns: `sk-`, `AKIA`, `-----BEGIN`, tokens, passwords).
5. **Dependency Audit**: Confirm any new dependency is justified, license-checked, and added to the lockfile.
6. **Concrete Value Statement**: State explicitly, in plain language, what the user can now do that they couldn't before — not just "tests pass."
7. **Tradeoff & Conflict Disclosure**: State any rule conflict or tradeoff made during the task (per `architecture.md`'s conflict-resolution clause) — do not bury it only in code comments.
