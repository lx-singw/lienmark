---
trigger: always_on
---

# Git Hygiene & Definition of Done

- Commit messages follow Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`,
  `chore:`, `docs:`) unless the repo already uses a different convention — match the
  repo.
- One logical change per commit. Don't bundle the whole task into one commit.
- No direct pushes to protected branches (main/master) unless the user explicitly
  says otherwise — work lands via a branch + PR.
- PR description includes: what changed and why, how it was tested, and any flagged
  rule conflicts/exceptions from architecture.md.

## Definition of Done

Before telling the user a task is complete, run `/definition_of_done` (see
.agent/workflows/definition_of_done.md) and confirm every box, not just "tests pass."
