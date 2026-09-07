---
name: quality-gate
description: >-
  Runs real lint, type, test, coverage, and security checks, enforcing a bounded 3-attempt escalation rule.
  Use to verify code changes before completion, after implementation, or when /quality_gate is invoked.
---

# Quality Gate Skill

Run real lint, type, test, coverage, and security checks and enforce the 3-attempt escalation rule.

## Verification Steps

Use whatever scripts the repo already defines (`package.json` scripts, `Makefile`, `pyproject.toml`, `pytest.ini`, etc.) instead of inventing new commands.

1. **Linting**: Run the linter (e.g., `ruff check .`, `npm run lint`, `golangci-lint run`).
2. **Type Checking**: Run the type-checker (e.g., `mypy .`, `pyright`, `tsc --noEmit`, `go vet ./...`).
3. **Test Suite & Coverage**:
   - Run the full test suite with coverage (e.g., `pytest --cov`, `npm test -- --coverage`, `go test ./... -cover`).
   - Fail this step if statement/branch coverage on new business logic is below 100%, or new UI component coverage is below 80%.
4. **Dependency Vulnerability Audit**: Run an audit if any dependency was modified (e.g., `pip-audit`, `npm audit --audit-level=high`, `govulncheck ./...`).
5. **Architectural Limit Checks**:
   - Check file and function size limits against `architecture.md` (files ≤250 lines, functions ≤40 lines).
   - Report any violations not present in the documented exception list.
   - **Remediation**: If flagged, resolve exclusively via `file-split` (`/file_split`) by extracting responsibilities along SRP lines — NEVER by trimming comments, collapsing blank lines, or minifying code (see `architecture.md`).
6. **Manual Trace Pass**: Pick at least one non-trivial edge case or input that automated tests don't obviously cover, and trace it through the actual code by reasoning. State what was traced and the result.

## Escalation & Safety Guardrails

- **3-Attempt Cap**: If any of steps 1–5 fail, fix and re-run. On the 3rd failure of the *same* root check: STOP, report what was tried, what changed, your current hypothesis, and request user guidance.
- **Read-Only Verification**: Do not run destructive commands (no `--force`, no unconfirmed DB migrations, no deploy).
