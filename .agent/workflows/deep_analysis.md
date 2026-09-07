---
description: Deep-uncertainty exploration - generate and steelman multiple genuinely different approaches before committing
---

Use this before architecture_review.md whenever the task has real design uncertainty:
more than one reasonable approach, unfamiliar codebase territory, or high stakes
(security, concurrency, data migration, external integration, anything hard to
reverse).

1. State precisely what is uncertain or high-stakes about this task — not "this is
   complex" but the specific decision that could go multiple defensible ways.
2. Generate at least 2, ideally 3, candidate approaches that are genuinely different
   in structure — not the same idea with a different variable name. If you can only
   think of one, that's a sign you converged too early; force yourself to find a
   second before continuing.
3. For each candidate, write the strongest case *for* it and the strongest case
   *against* it, as if arguing both sides to a skeptical reviewer. Include concrete
   failure modes, not generic ones ("could have bugs" doesn't count).
4. For the leading candidate specifically, list the edge cases or conditions under
   which it breaks or degrades.
5. Choose one. State explicitly why the rejected candidates lost — not just why the
   winner is good.
6. Carry this reasoning into architecture_review.md's implementation plan; don't
   discard it once a choice is made — the rejected-alternatives reasoning belongs in
   the plan's summary so the user can challenge the choice if they disagree.
