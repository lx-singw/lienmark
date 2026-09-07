# Rule: Deep Think Ultra Orchestrator (Complete 12-Ingredient Architecture)

This rule governs agent behavior when `[DEEP THINK]`, `[ULTRA]`, `/goal`, or high-autonomy execution is requested. It enforces all 12 structural ingredients of a true high-autonomy multi-agent system.

---

## 1. Task Intake, Scope & Decomposition Layer
- **Intent Parsing & Scope Boundary**: Parse the explicit goal and declare forbidden systems, external networks, or out-of-scope files.
- **Complexity Routing**: For trivial one-line edits or basic questions, execute directly. For multi-file changes, refactoring, or bug investigation, activate the full 12-ingredient orchestration.
- **DAG Task Graph**: Construct a dependency graph of subtasks in the `implementation_plan.md` artifact.

---

## 2. Dedicated Role Architecture & Model Tiering
Execute subagent delegation using `define_subagent` or specialized `invoke_subagent` roles with distinct system prompts:

| Role | Responsibility | Model Tier | Tool Permissions (Least Privilege) |
| :--- | :--- | :---: | :--- |
| **Explorer & Analyst** | AST mapping, call-site discovery, API specs | `flash 3.8` | **Read-Only** (`enable_write_tools: false`) |
| **Adversarial Critic** | Race conditions, null safety, security, edge-case attacks | `flash 3.8` | **Read-Only** (`enable_write_tools: false`) |
| **Lead Implementer** | Scoped, cohesive code modifications | `flash 3.8` | **Write-Enabled** (`enable_write_tools: true`) |
| **Empirical Verifier** | Test execution, linting, build pipelines, benchmark logs | `flash 3.8` | **Execution-Only** |

---

## 3. Communication, Coordination & Audit Trail
- **Shared State / Blackboard**: Maintain active state in `implementation_plan.md` and persist per-agent reasoning logs in `audit_trail.md`.
- **Compact IPC Protocol**: Subagents report concise JSON/Markdown summaries (`{ status, diff_metrics, risks, verdict }`) to prevent context bloat.
- **Conflict Resolution**: The Adversarial Critic arbitrates contradictory findings before the Implementer writes code.

---

## 4. Multi-Hypothesis Exploration & Failure Pre-Mortem
Before modifying code on complex tasks:
1. **Parallel Generation**: Formulate at least 2–3 competing implementation paths.
2. **Weighted Evaluation Matrix**: Score across *Complexity*, *Performance*, *Regression Risk*, and *Reversibility*.
3. **Failure Pre-Mortem as Active Filter**: For each hypothesis, answer: *"If this solution breaks under high load or edge cases, why did it fail?"* Discard hypotheses with high failure risks.
4. **Primary & Fallback Selection**: Explicitly declare Hypothesis A (Selected) and Hypothesis B (Fallback).

---

## 5. Execution Environment, Sandboxing & Scratchpads
- **Least-Privilege Enforcement**: Subagents operate under strict tool permissions matching their role.
- **Workspace Isolation**: Use `Workspace: "branch"` when performing speculative multi-agent prototyping.
- **Scratchpad Testing**: Execute exploratory micro-benchmarks or prototypes in `<appDataDir>/brain/<conversation-id>/scratch/` before committing to the main repository.

---

## 6. 4-Stage Quality & Verification Gates
Every code modification must satisfy all four gates:
- **Gate 1 (Strict TDD / Reproduction)**: Create reproduction or unit tests specifying expected behavior.
- **Gate 2 (Static Checks)**: Linters and typecheckers clean (`tsc --noEmit`, `pyright`, `mypy`, `cargo check`, `npm run lint`).
- **Gate 3 (Empirical Pass)**: 100% green test suite pass with clean exit code `0`.
- **Gate 4 (Adversarial Audit)**: Adversarial Critic confirms no regressions across adjacent modules.

---

## 7. Self-Correction & Deterministic Pivot Heuristic
- **Diagnosis Before Retry**: Inspect raw stack traces and root causes rather than applying speculative micro-patches.
- **Deterministic Pivot Rule**: If an implementation hypothesis fails Gate 2 or 3 **twice consecutively**, immediately revert unverified diffs and **pivot to Hypothesis B**.

---

## 8. Safety Guardrails & Autonomy Limits (Ceilings)
- **Approval Gate for Irreversible Actions**: The swarm is STRICTLY FORBIDDEN from performing irreversible or destructive actions without explicit user confirmation:
  - Deleting files (`rm -rf`, file removal)
  - Force-pushing or resetting git history (`git push --force`, `git reset --hard`)
  - Modifying `.env`, secrets, or production credentials
  - Invoking external paid APIs or destructive network requests.
- **Scope Lock**: Changes must strictly remain within the declared target directory boundaries.

---

## 9. Termination Conditions & Human Escalation
- **Hard Ceiling**: If both Hypothesis A and Fallback Hypothesis B fail twice consecutively (or total self-healing loops reach the limit), the autonomous loop MUST HALT.
- **Escalation Incident Report**: Write a structured escalation report in `audit_trail.md` detailing: (1) Root cause of failure, (2) Hypotheses attempted, (3) Full stack traces, and (4) Concrete options for user direction.

---

## 10. Observability & Cost-Aware Resource Management
- **Audit Trail Persistence**: Record all per-agent reasoning, critic verdicts, test runs, and pivot events in `audit_trail.md`.
- **Cost-Aware Routing**: `flash 3.8` performs the heavy reasoning every time across all phases and roles (including high-uncertainty exploration, adversarial critic reviews, architecture planning, and verification), delivering full deep-thinking reasoning and high throughput.
