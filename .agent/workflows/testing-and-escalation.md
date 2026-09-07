---
trigger: always_on
---

# Testing, Coverage & Escalation

- Every new module, hook, util, or endpoint ships with a companion test file matching
  the repo's existing test naming pattern.
- Coverage targets: 100% statement/branch on new business logic, controllers, and
  utils; ≥80% on UI components, weighted toward interaction paths and edge cases over
  trivial render checks.
- Coverage is a floor, not the goal. A test that asserts nothing real (calling code
  just to bump a percentage) fails review even if the number looks fine. Every test
  must check a real output, behavior, or side effect.
- Mock all network calls, DB calls, and third-party SDKs using whatever mocking
  library the repo already uses — don't introduce a second one.
- Run the local test suite before declaring any task done (see quality_gate.md
  workflow). A failing test means the task is not finished.

## Escalation — bounded retries

Any autonomous fix-and-retry loop (failing test, lint, build, or type-check) is capped
at **3 attempts on the same root cause**. On the 3rd failure: stop, report what you
tried, what changed each time, your current best hypothesis, and ask the user how to
proceed. Do not keep iterating silently past this point.

If a requirement turns out ambiguous once you're mid-implementation, pause and ask
rather than guessing — this is separate from ordinary judgment calls (naming, file
layout) which you're expected to make without asking.
