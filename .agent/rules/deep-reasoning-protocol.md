---
trigger: always_on
---

# Deep Reasoning Protocol

This rule shapes *how* you reason, not how many tokens the underlying model spends —
that's controlled by the model/thinking-level picker in Settings, which this file
cannot set. Follow this regardless of which tier is active, but know it's a
complement to picking a high thinking tier, not a substitute for it.

- For any non-trivial design decision, consider at least two genuinely different
  approaches before committing, and say why the others were rejected — not just why
  the winner is good. If you notice you jumped straight to the first workable idea,
  stop and generate a real second option before proceeding.
- Before presenting a plan or a finished piece of work, actively look for the
  strongest reason it could be wrong or get rejected — argue against yourself as a
  skeptical reviewer would — rather than presenting the first version that seems to
  work. See architecture_review.md and deep_analysis.md for where this is required,
  not optional.
- State assumptions and remaining uncertainty explicitly rather than silently picking
  a default and moving on. "I assumed X because Y" is fine; silently assuming X is
  not.
- Never treat "tests pass" or "it looks right" as verification. Trace at least one
  concrete edge case through the actual logic before calling something done (see
  quality_gate.md step 5a).
- Escalate to `/deep_analysis` for genuinely uncertain or high-stakes decisions
  (security, concurrency, data migrations, unfamiliar codebase areas, external
  integrations). Don't escalate routine, well-understood work — that just burns
  time and quota for no quality gain. Calibrate to the actual stakes of the decision,
  not a blanket policy.
- If you're on a fast/routine tier and hit a decision that turns out to be higher-
  stakes than expected mid-task, say so and suggest the user switch to a
  higher-thinking model/tier for that specific decision rather than pushing through
  on the wrong tier.
