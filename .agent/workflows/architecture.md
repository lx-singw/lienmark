---
trigger: always_on
---

# Architecture & Modularity

- One responsibility per file (component, hook, util, or route handler — never mixed).
- Files ≤250 lines, functions ≤40 lines. Exceptions: generated code, barrel/index files,
  fixtures, snapshots, and a single cohesive state machine you explicitly flag as
  "split rejected — see reasoning" in your summary.
- **These limits are a proxy for "too many responsibilities in one place," not the
  goal itself.** The only valid way to bring an oversized file/function into
  compliance is genuine extraction — pulling a cohesive unit of responsibility into
  its own file/function along SRP lines (see file_split.md). Reducing the number by
  any other means is a rule violation, not compliance, specifically including:
  deleting or shortening comments, collapsing/removing blank lines, merging
  statements onto fewer lines, minifying, or moving code into a vaguely-scoped
  dumping-ground file ("helpers2.ts", "utils.ts" with no clear single purpose) just
  to move lines out of the flagged file. If you find yourself trimming whitespace or
  comments to hit a line count, stop — that's the signal you're solving the metric
  instead of the actual problem.
- Splitting a file to fix a size violation still creates new files outside whatever
  was originally approved — run `/file_split.md`'s workflow, which routes back
  through the pre-flight approval gate before anything is created.
- UI components render only. Business logic lives in hooks/controllers. Network/data
  access lives in isolated API service modules. Never mix these three in one file.
- Enforce SOLID, especially Open/Closed (use interfaces/config objects, not growing
  switch/if-else chains) and Dependency Inversion (depend on abstractions, not
  concrete low-level modules).
- Before writing anything, scan the existing repo for naming convention (camelCase /
  kebab-case / PascalCase), export style (default vs named), and folder pattern.
  Match it. Do not introduce a second convention.
- If two rules in this rules directory conflict for a specific case, implement the
  version you judge correct, then say explicitly in your summary which rule you bent
  and why. Never resolve a conflict silently.
- No drive-by refactors: only touch files inside the approved scope (see
  pre-flight-approval.md). Local cleanup inside a block you're already editing for the
  approved task is fine; rewriting a whole unrelated file is not.
- If existing repo conventions conflict with these rules (e.g. repo is untyped JS,
  these rules want strict typing), follow the *repo's* convention within that
  file/module and flag the mismatch — don't unilaterally impose this document.

Precedence when rules conflict and the above doesn't resolve it: security > passing
tests/build > explicit current-task instruction (flag deviation) > repo convention >
this document's defaults.
