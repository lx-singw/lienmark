# Canonical clearance workflow

## Services and configuration

The frontend calls `/api/clearance`. Both the API and worker must use the same store:

- Local: `CLEARANCE_SQLITE_PATH=.data/clearance.sqlite3`, `BUDGET_STORE_MODE=local_disk`, `USE_LOCAL_STORAGE=true`.
- Cloud: `CLEARANCE_STORE=firestore`, `GOOGLE_CLOUD_PROJECT`, workload credentials. A store failure never silently selects an in-memory alternative.
- Live providers: `CLEARANCE_LIVE_ENABLED=true`, `PARALLEL_API_KEY`, and either `GEMINI_API_KEY` or `GOOGLE_GENAI_USE_VERTEXAI=true` with `GOOGLE_CLOUD_PROJECT`, region and application-default credentials. Do not commit credentials.

Run `python -m backend.clearance.worker` in a persistent process. The API and browser do not own its lifetime. Alternatively run `uvicorn backend.clearance.runtime:app --host 0.0.0.0 --port 8081` for a dedicated worker service with `/health` and `/eventarc` endpoints.

In Workspace settings, save a production name, enable automatic processing and authorize per-run and cumulative reservation allowances. The cumulative allowance is never reset by saving the form. Active jobs reserve their full per-run allowance transactionally; on completion it is replaced by their actual dispatch reservations. An exhausted allowance leaves events queued with a visible reason. Pausing stops new jobs, not already authorized work. These allowances are dispatch controls, not billing reconciliation.

## Source connection

Set `CLEARANCE_WATCH_ROOT` to a dedicated local directory, or `CLEARANCE_WATCH_BUCKET` to a GCS bucket that the worker identity can read. Only configured server roots are accepted; clients cannot supply arbitrary file paths or buckets.

Within that root or bucket:

```
organizations/{organization_id}/productions/{production_id}/locked/{filename}
organizations/{organization_id}/productions/{production_id}/agreements/{filename}
```

The production and organization identifiers must match the invited workspace. Do not put private files in another production's folder. Folder details appear under Workspace settings. A separate producer or DCC application can write files there while the browser is closed. The worker periodically scans enabled productions and durably records source events. Duplicate content under another filename does not enqueue duplicate research. Uploads through Revisions or Investigations use the same source inbox.

For an exact clarification binding, put the agreement under `agreements/{clarification_id}/{filename}`, or use the question's upload control. Otherwise Gemini attempts an unambiguous work/scope match. Ambiguous documents remain available for a producer to assign to an open question. Matching only resumes investigation; the evidence reviewer still evaluates the document and may retain the question.

PDF text extraction uses pypdf; FDX uses hardened XML parsing. Unsupported, oversized or unreadable documents fail visibly. No fallback inserts example claims. A JSON cut can supply `{"uses": [...]}` using the `Use` schema in `backend/clearance/models.py`; this is a complete cut with explicit stable occurrence keys. Plain text and PDF cuts use model-assisted occurrence alignment against the baseline. Removed, added and changed occurrences are compared using the same canonical fields. Human decisions never come from extracted document text.

## Eventarc and Cloud Run

Deploy the dedicated runtime as a separate private worker service using the backend image and the runtime entry point. Configure instance-based CPU allocation (CPU throttling disabled) and at least one warm instance so polling, scheduled monitoring and crash recovery work without active HTTP traffic. Use the same Firestore project as the API. Apply the collection-group status indexes in `docs/deployment/clearance-firestore.indexes.json` as part of your deployment configuration. Configure least-privilege storage read and Firestore access, and Vertex access where applicable.

To receive Eventarc finalization events, set `CLEARANCE_EVENTARC_AUDIENCE` to the expected ID-token audience and `CLEARANCE_EVENTARC_SERVICE_ACCOUNT` to the permitted service account email. The runtime verifies Google ID tokens and email identity, checks the bucket and production prefix, downloads the exact object generation, and persists the event before responding. Keep Cloud Run IAM invocation restricted too. Polling provides a recovery path if event delivery is interrupted. Test the token audience/forwarding and actual Eventarc trigger in the destination environment before claiming cloud readiness.

No cloud resources are created by importing or testing these modules. The current local verification does not prove deployment, IAM or Eventarc configuration.

## Tasks, decisions and recovery

Intake hands extracted uses to the deterministic change coordinator. A planner sets a public research query and a stop condition for each affected claim. The rights researcher searches Parallel and assesses the findings with Gemini. A separate evidence reviewer challenges source relevance, support and contradictions; it may hand the task back for a targeted follow-up. Three rounds and the job allowance bound the loop. Completed provider responses and task outcomes are persisted, so a recovered worker reuses completed calls. A started call with unknown outcome is not automatically charged again; it remains an operational exception. Explicit transient provider responses (429/5xx) receive one budgeted retry. Invalid model output can receive one budgeted repair. Both attempts remain in the call ledger, and model citations are constrained to the attached evidence IDs. The planner can also choose to request private information directly or assess an arriving document against retained evidence without another web search.

Missing private facts become pinned clarification records. They survive restarts and are not silently deleted by TTL. Replacement investigations supersede old questions in the same claim scope. Agreement arrivals resume only the matching claim and explicit transitive dependents. Unaffected unresolved claims are not restarted by that resumption. Reviewer rejection similarly creates a durable directive event; processing follows the saved policy and allowance.

Scheduled evidence checks examine previously relied-on public URLs through Parallel. Only attributable material changes reopen a claim. Missing sources produce an inconclusive event; formatting changes alone do not invalidate a decision. Periodic checking is opt-in and uses the same allowance as other automatic jobs.

Each job uses a renewable lease and increasing fencing token. Stale workers cannot publish results. Source deduplication and production head updates are transactional. The worker heartbeat, source inbox and task timeline expose operational state. The implementation currently processes claim tasks sequentially; it does not claim simultaneous independent worker agents or an A2A network.

Only a production-assigned reviewer or administrator can sign off or reject. Exact snapshot matching prevents stale decisions. Sign-off requires attached evidence, a completed finding and approved dependencies. A reviewer resolving a clarification is recorded explicitly. Authentication, invitations and source-event authority remain enforced server-side.

## Demonstration sequence

1. Connect an empty watched production folder and authorize a bounded allowance.
2. Add a screenplay or cue sheet that has not already been ingested. Observe automatic intake and live research. An authorized reviewer establishes a baseline by reviewing the actual findings. Never pre-fill these decisions as if they were legal approvals.
3. With the workspace closed, add a changed cut. Return to see the trigger, preserved approvals, affected tasks and live sources. Counts and elapsed time are computed from snapshots, not a fixed 12-to-10/2 script.
4. Supply a requested agreement. Observe the match and resumed investigation without an additional audit click. If it does not resolve the evidence gap, the question should remain open.
5. Have the authorized reviewer decide. The delivery view and PDF read the same immutable snapshot, with before/after blockers, decision identity and evidence digests. Downloading a PDF does not grant clearance.
6. Rename/re-upload an already processed document and verify no duplicate provider work. In a controlled test, expire a killed worker's lease and verify a replacement cannot repeat completed calls or allow the stale worker to write.

The UI leaves raw identifiers in technical references, not production headings. Task objectives/outcomes are observable records, not fabricated agent conversations or hidden reasoning.

## Verification

```bash
BUDGET_STORE_MODE=local_disk USE_LOCAL_STORAGE=true python -m pytest tests/test_clearance_workflow.py tests/test_clearance_automation.py tests/test_auth_routes.py -q
cd frontend
npx --no-install tsx --test tests/*.test.ts
npm run build
```

These mounted-app tests replace external provider HTTP. They cover authority, CSRF, selective invalidation, source dispatch, agreement matching/resumption, adaptive evidence-review handoffs, exact evidence materiality, budget concurrency, duplicate arrivals, durable recovery and PDF parity.

Separately, `python -m scripts.verify_autonomous_live --allowance 0.70` runs actual provider calls in an isolated temporary production. The September 9 run completed two jobs, ten provider calls and seven task roles, with $0.42 reserved. Its scope note explicitly grants no rights; zero legal decisions were recorded. The resulting `.data/autonomous-live-verification.json` separates this live evidence from mocked acceptance tests. No reviewer sign-off or deployed cloud event delivery is implied.

