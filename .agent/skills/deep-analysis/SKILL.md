---
name: deep-analysis
description: >-
  Explores deep design uncertainty by generating and steelmanning multiple competing approaches before committing.
  Use when facing high-stakes architectural decisions, unfamiliar codebase territory, security or concurrency concerns, or when /deep_analysis is requested.
---

# Deep Analysis Skill

Perform deep-uncertainty exploration and steelman multiple genuinely different approaches before committing to an architecture.

## Trigger Conditions
Use this before `architecture-review` whenever the task has real design uncertainty:
- More than one reasonable approach
- Unfamiliar codebase territory
- High stakes (security, concurrency, data migration, external integration, irreversible actions)

## Analysis Steps

1. **State the Core Uncertainty**: State precisely what is uncertain or high-stakes about this task — not "this is complex", but the specific decision that could go multiple defensible ways.
2. **Generate Competing Candidates**: Generate at least 2, ideally 3, candidate approaches that are genuinely different in structure (not superficial variations). If you can only think of one, force yourself to find a second before proceeding.
3. **Steelman Both Sides**: For each candidate, write the strongest case *for* it and the strongest case *against* it, as if arguing both sides to a skeptical reviewer. Include concrete failure modes, not generic ones.
4. **Edge-Case Stress Test**: For the leading candidate specifically, list the edge cases or conditions under which it breaks or degrades.
5. **Decide & Justify Rejections**: Choose one winning approach. State explicitly why the rejected candidates lost — not just why the winner is good.
6. **Hand-off to Plan**: Carry this reasoning into the `architecture-review` implementation plan. The rejected-alternatives rationale belongs in the plan's summary so the user can challenge the choice if they disagree.
