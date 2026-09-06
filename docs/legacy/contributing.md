# Contributing Guidelines — Lienmark

Thank you for contributing to **Lienmark**! This document outlines our engineering standards, testing expectations, pull request workflows, and code quality requirements.

---

## 1. Code Quality & Format Standards

### Python Backend Standards
- **Formatter & Linter**: We use **Ruff** and **Black** for Python code formatting and linting.
- **Line Length**: 100 characters maximum.
- **Type Annotations**: All public functions and agent methods must include complete Python type hints (`mypy` compliant).
- **Execution Commands**:
  ```bash
  ruff check backend/ tests/
  black --check backend/ tests/
  ```

### TypeScript / Next.js Frontend Standards
- **Formatter & Linter**: We use **ESLint** and **Prettier**.
- **Component Rules**: All React components must be functional components written in TypeScript (`.tsx`).
- **Styling**: Component styles must utilize CSS variables defined in `frontend/app/globals.css` (e.g. `--bg-primary: #0b0f17`, `--border-glass`).
- **Execution Commands**:
  ```bash
  cd frontend
  npm run lint
  npx prettier --check "app/**/*.{ts,tsx}"
  ```

---

## 2. Testing Strategy & Requirements

All code contributions must maintain or improve test coverage. We enforce four distinct testing layers:

| Layer | Target | Command | Requirement |
|---|---|---|---|
| **Unit Tests** | Intake & Research Agent extraction and query logic | `pytest tests/test_intake_agent.py` | 100% pass rate |
| **Security Tests** | Firestore create-only rules & IAM permissions | `pytest tests/test_ledger_immutability.py` | No unauthorized ledger writes |
| **Determinism Tests** | Risk Scoring Agent reproducible output verification | `pytest tests/test_risk_scoring_determinism.py` | 3 consecutive identical runs |
| **Adversarial Tests** | Script prompt injection trap verification | `pytest tests/test_adversarial_defense.py` | Trap `suspicious_embedded_instruction` |
| **E2E Benchmark** | Full multi-agent pipeline verification | `pytest tests/test_e2e_pipeline.py` | Complete end-to-end pass |

---

## 3. Branching Strategy & Workflow

We follow **Trunk-Based Development** with short-lived feature branches:

1. **Main Branch (`main`)**: Production-ready code. All commits to `main` must pass automated CI checks.
2. **Feature Branches**: Named by category and ticket/scope:
   - `feat/multi-tool-research`
   - `fix/firestore-rules-permission`
   - `docs/api-reference-update`
3. **Pull Request Protocol**:
   - Every PR must target `main`.
   - CI pipeline (`.github/workflows/ci.yml`) must pass cleanly before merge.
   - At least 1 peer or reviewer sign-off required.

---

## 4. Semantic Commit Messages

We enforce **Conventional Commits**:
* `feat`: A new feature (e.g. `feat: add multi-tool Parallel API selection`)
* `fix`: A bug fix (e.g. `fix: correct ledger entry version increment`)
* `docs`: Documentation updates (e.g. `docs: add Gherkin user stories to PRD`)
* `test`: Adding or updating test cases (e.g. `test: add E2E benchmark pipeline test`)
* `refactor`: Code refactoring without behavioral changes

---

## 5. Release Versioning

Lienmark follows **Semantic Versioning (SemVer)**:
- `v1.0.0-mvp`: Initial hackathon release for **Agentic Cinema: The Blockbuster Hackathon**.
- `v1.1.0`: Addition of Phase 2 AI provenance features.
- `v2.0.0`: Transition to global compliance operating system with Postgres backend.
