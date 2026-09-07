---
description: Fix a file/function that exceeds architecture.md's size limit by splitting along real responsibility boundaries — the only valid remediation
---

Trigger this whenever quality_gate.md's size check flags a file or function. This is
the only acceptable way to resolve that flag.

1. Read the full file and name the distinct responsibilities mixed inside it (e.g.
   rendering vs. business logic vs. data access vs. several unrelated utilities).
   If you can't name more than one responsibility, the file may not actually need
   splitting — flag that back to the size check instead of forcing a split.
2. Group code by responsibility, not by line-count arithmetic. Don't chop the file
   in half at whatever line number gets you under the limit.
3. Before creating anything, run `/architecture_review` with the proposed new file
   tree — this is a scope change like any other and needs approval, even though it
   was triggered by an automated check rather than a user request.
4. Give each extracted unit one clear name and export, matching the repo's existing
   naming/export conventions.
5. Update every import/call site that referenced the original file.
6. Preserve behavior exactly. This is a refactor, not a rewrite — don't change logic
   while splitting unless separately asked to.
7. Move or add companion tests to match the new file boundaries; don't lose coverage
   in the split.
8. Re-run `/quality_gate` on the result.

Never resolve a size-limit flag by: deleting or shortening comments, collapsing blank
lines, merging statements onto fewer lines, minifying, or dumping code into a vaguely
named catch-all file. Any of these gets the number down without addressing what the
limit is actually a proxy for — too many responsibilities living in one place — and
counts as a failed check, not a passed one.
