---
description: Run real lint, type, test, coverage, and security checks and enforce the 3-attempt escalation rule
---

Use whatever scripts the repo already defines (package.json `scripts`, `Makefile`,
`pyproject.toml`, etc.) instead of inventing new commands. Typical examples below —
swap for the repo's actual commands.

// turbo
1. Run the linter (e.g. `npm run lint` / `ruff check .` / `golangci-lint run`).

// turbo
2. Run the type-checker (e.g. `tsc --noEmit` / `mypy .` / `go vet ./...`).

// turbo
3. Run the full test suite with coverage
   (e.g. `npm test -- --coverage` / `pytest --cov` / `go test ./... -cover`).
   Fail this step if statement/branch coverage on new business logic is below 100%,
   or new UI component coverage is below 80% (see testing-and-escalation.md).

// turbo
4. Run a dependency vulnerability audit if any dependency changed this task
   (e.g. `npm audit --audit-level=high` / `pip-audit` / `govulncheck ./...`).

// turbo
5. Run a file/function size check against architecture.md's limits
   (e.g. an ESLint `max-lines`/`max-lines-per-function` rule, or
   `grep`-based line count over changed files) and report any file over 250 lines
   or function over 40 lines that isn't in the documented exception list. If flagged,
   fix via `/file_split` — not by trimming comments/whitespace (see architecture.md).

5a. Manual verification pass — pick at least one non-trivial edge case or input the
    automated tests don't obviously cover, and trace it through the actual code by
    reasoning, not by re-running the suite. A green test suite is not itself proof
    of correctness; state what you traced and what you found.

6. If any of steps 1–5 fail: fix and re-run. This counts toward the 3-attempt cap in
   testing-and-escalation.md — on the 3rd failure of the *same* check, stop and report
   to the user instead of retrying again.

7. Do not run destructive commands here (no `--force`, no migrations, no deploy). This
   workflow is read-only verification only.
