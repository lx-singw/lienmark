---
name: file-split
description: >-
  Fix a file or function that exceeds architecture.md's size limits (files ≤250 lines, functions ≤40 lines)
  by splitting along real responsibility boundaries (SRP). Use when quality-gate flags size violations
  or when /file_split is requested.
---

# File Split Skill

Fix a file or function that exceeds `architecture.md`'s size limits by genuine extraction along single-responsibility boundaries — the only valid remediation.

## Trigger Conditions
Trigger this whenever `quality-gate` (`/quality_gate`) flags an oversized file or function.

## Splitting Procedure

1. **Identify Responsibilities**: Read the full file and explicitly name the distinct responsibilities mixed inside it (e.g., rendering vs. business logic vs. data access vs. unrelated utility functions). If you cannot name more than one distinct responsibility, flag this back instead of forcing an unnatural split.
2. **Group by Responsibility**: Group code by cohesion and SRP, not by line-count arithmetic. Do not arbitrarily cut a file in half at an arbitrary line number.
3. **Pre-Flight Approval Gate**: Before creating any new files or modifying imports, run `architecture-review` (`/architecture_review`) with the proposed new file tree and data flow. This is a scope change requiring user approval.
4. **Clean Naming & Exports**: Give each extracted unit a single clear name and export, matching existing repository conventions.
5. **Update Call Sites**: Update every import and call site that referenced the original code.
6. **Preserve Behavior Exactly**: This is a pure refactor, not a feature change or rewrite. Do not change existing logic during the split.
7. **Maintain Test Coverage**: Move or add companion tests matching the new file boundaries without dropping branch or statement coverage.
8. **Re-Verify with Quality Gate**: Re-run `quality-gate` (`/quality_gate`) to ensure the refactored code passes all lint, type, size, and test checks.

## Forbidden Shortcuts (Strict Violations)
Never resolve a size-limit flag by:
- Deleting or shortening comments
- Collapsing or removing blank lines
- Merging statements onto fewer lines
- Minifying code
- Dumping code into vaguely-named dumping-ground files (e.g. `helpers2.ts`, `utils.ts` without single cohesive scope)

Any of the above is considered an immediate review failure.
