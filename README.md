# Lienmark — Clearance change control for E&O

Detect clearance drift, selectively revalidate affected evidence, and keep reviewer sign-offs aligned with production versions.

Lienmark watches a production's incoming documents, compares creative uses against a recorded baseline, preserves unaffected reviewer decisions, and investigates affected claims using Gemini and Parallel Search. Missing private facts become durable clarifications. An arriving agreement can resume the relevant investigation. A draft Exceptions Schedule reflects the same immutable snapshot as the workspace.

## Current execution path

`backend/clearance/` is the canonical workspace pipeline. It uses transactional SQLite locally and Firestore in cloud configuration. The older ingestion and orchestration modules remain in the repository but are not proof that the canonical flow runs through those modules.

The workflow records tasks for document intake, deterministic change scoping, Gemini research planning, Parallel-backed research, independent Gemini evidence review, agreement matching, and delivery preparation. The evidence reviewer can return a task for another targeted search. All provider calls have durable checkpoints and bounded reservations. Agents never grant legal clearance.

## Run and verify

See [the workflow guide](docs/live-clearance-workflow.md) for credentials, worker configuration, watched folders, permissions and a complete demonstration sequence.

```bash
pip install -r backend/requirements.txt
BUDGET_STORE_MODE=local_disk USE_LOCAL_STORAGE=true uvicorn backend.main:app --port 8000
# Separate process, same environment and database:
BUDGET_STORE_MODE=local_disk USE_LOCAL_STORAGE=true python -m backend.clearance.worker
# Frontend, separate terminal:
cd frontend
npm install
npm run dev -- --port 3100
```

Authenticate through a private production invitation. In Workspace settings, authorize automatic processing and its allowance. The worker must have the live provider credentials configured; the UI does not simulate successful calls when they are absent.

```bash
BUDGET_STORE_MODE=local_disk USE_LOCAL_STORAGE=true python -m pytest tests/test_clearance_workflow.py tests/test_clearance_automation.py tests/test_auth_routes.py -q
cd frontend
npx --no-install tsx --test tests/*.test.ts
npm run build
```

Acceptance tests exercise mounted application routes, real local persistence and workers. External provider HTTP is replaced in those tests. Separately, this opt-in command incurs actual provider calls in an isolated verification production:

```bash
python -m scripts.verify_autonomous_live --allowance 0.70
```

The September 9 local live verification completed two jobs and ten provider calls, covering intake and agreement-triggered resumption. It reserved $0.42, which is not a reconciled provider invoice. It recorded no legal approval. The agreement input was an explicitly labeled test scope note, not a rights grant. Local details are written under `.data/` and are not submission assets.

## Demonstrating the value

Start with a baseline that an authorized human has actually reviewed. Introduce an unfamiliar changed cut into the watched folder with the workspace closed. Open the workspace to see the trigger, task handoffs, preserved decisions, targeted evidence and specific unresolved facts. Supply the requested agreement, observe automatic resumption, then have the assigned reviewer decide. Export the resulting draft schedule.

Counts come from stored records. A sample screenplay can be fictional, but source results, task traces and decisions must be identified honestly. Historical fixture scripts and reports under `demo/` and `output/` are not evidence of current live execution. Fixed 12-to-10/2 narratives, universal 83.3% savings and attorney-hour savings are not measured product results.

## Operational boundaries

- Automatic work requires a production-scoped allowance. Pausing prevents new dispatch; already accepted jobs retain their bounded allowance.
- Human authority remains required for sign-off. Public web evidence does not establish a private license.
- Supported input is readable PDF, TXT, Fountain, FDX, Markdown or a structured JSON cut. Limits are explicit: 4 MB, 60 PDF pages, 24,000 readable characters and 20 creative occurrences. Scans need OCR before ingestion.
- Source monitoring uses attributable Parallel results and a materiality review. Missing search excerpts are inconclusive, not proof that a right changed.
- Cloud Run needs a separately operated worker with CPU available between requests. Cloud deployment and real Eventarc delivery require environment-specific validation; local tests do not prove them.
- This README makes no assertion about competition eligibility or authorship tools.

[MIT license](LICENSE)
