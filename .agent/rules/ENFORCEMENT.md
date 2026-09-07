# Real Enforcement Layer (outside the agent)

The files in `.agent/rules/` and `.agent/workflows/` shape how Antigravity's agents
*behave*. They cannot guarantee compliance the way a failing build can — an agent
under time pressure or a confusing edge case can still write a 300-line file if
nothing outside the conversation stops it. The rules below are enforced by tooling,
not by the model choosing to follow instructions, and they should block a merge
regardless of which agent (or human) authored the change.

Wire these in once per repo. Adjust commands to your actual stack — these are the
common cases.

## 1. Pre-commit hook (stops bad commits before they exist)

**JS/TS** — Husky + lint-staged:
```bash
npm install --save-dev husky lint-staged
npx husky init
echo "npx lint-staged" > .husky/pre-commit
```
`package.json`:
```json
"lint-staged": {
  "*.{ts,tsx,js,jsx}": ["eslint --max-warnings=0", "prettier --check"]
}
```

**Python** — pre-commit framework:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks: [{id: ruff}, {id: ruff-format}]
```

## 2. File/function size limits (backs architecture.md's 250/40-line rule)

**JS/TS** — `.eslintrc`:
```json
"rules": {
  "max-lines": ["error", {"max": 250, "skipBlankLines": true, "skipComments": true}],
  "max-lines-per-function": ["error", {"max": 40, "skipBlankLines": true}]
}
```

**Python** — `ruff` (`pyproject.toml`):
```toml
[tool.ruff.lint]
select = ["E501", "PLR0915"]  # line length, too-many-statements
```

## 3. Coverage thresholds (backs testing-and-escalation.md)

**Jest/Vitest** (`jest.config.js` / `vitest.config.ts`):
```js
coverageThreshold: {
  "./src/business-logic/**": { statements: 100, branches: 100 },
  "./src/components/**": { statements: 80, branches: 80 }
}
```

**pytest** (`pyproject.toml`):
```toml
[tool.coverage.report]
fail_under = 100
```

## 4. Type safety (backs error-handling-and-types.md)

**TypeScript** — `tsconfig.json`: `"strict": true, "noImplicitAny": true`
**Python** — `mypy --strict` in CI.

## 5. Security & dependency scanning (backs security-and-dependencies.md)

```bash
# JS/TS
npm audit --audit-level=high
npx gitleaks detect --no-git   # or truffleHog, for committed secrets

# Python
pip-audit
detect-secrets scan
```

## 6. Commit message enforcement (backs git-and-definition-of-done.md)

```bash
npm install --save-dev @commitlint/cli @commitlint/config-conventional
echo "module.exports = {extends: ['@commitlint/config-conventional']}" > commitlint.config.js
echo "npx --no -- commitlint --edit \$1" > .husky/commit-msg
```

## 7. CI gate (the actual backstop — run all of the above on every PR)

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate
on: [pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage
      - run: npm audit --audit-level=high
```
Make this a required status check on the protected branch. This is the step that
actually matters — everything above is local convenience; this is what nothing can
bypass, including an agent that ran `/quality_gate` and self-reported a pass.

## Note on subagents specifically

Antigravity's built-in subagents (Browser, Terminal) run automatically and inherit
whatever `.agent/rules/` are active in the workspace — no extra wiring needed.
User-defined custom subagent personas are a newer, still-evolving part of Antigravity
(format has varied across recent versions between `.agents/agents/*.md` and
`agent.json`), so before relying on a hand-authored subagent file, check your
installed version's current docs rather than trusting any fixed format here.
