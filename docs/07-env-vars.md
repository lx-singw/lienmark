# Environment Variables — Lienmark

## 1. Principles, and why each one is non-negotiable

- **No secrets in code, ever.** Not as a "temporary for the demo" exception, not hardcoded "just to get the hackathon build working faster" — this is the kind of shortcut that's easy to take under deadline pressure and easy to forget to undo before the repo goes public. Given the repo *must* be public for submission (see `01-hackathon-scope.md` §5), a hardcoded API key isn't just bad practice, it's a real, immediate security incident the moment the repo is pushed.
- **No secrets in `.env` files committed to the repo, ever.** Actual credential values live only in **Google Secret Manager**. Local `.env` files reference secret names for local development convenience only, and must be listed in `.gitignore` from the very first commit — not added after someone notices the omission.
- **Each agent's service account should only have access to the secrets it actually needs.** This is the same least-privilege principle from `04-prd.md` §5.9, applied specifically to credential access — the Research Agent's service account should be able to read the Parallel API key; no other agent's service account should be able to.

## 2. `.env.example` — commit this file, never commit `.env` itself

```bash
# ── Google Cloud ──────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT=lienmark-hackathon
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./secrets/service-account.json   # local dev only;
                                                                    # Cloud Run uses its attached
                                                                    # service account automatically,
                                                                    # this var is never read in production

# ── Gemini / Agent Builder ────────────────────────────────────
GEMINI_MODEL=gemini-2.5-pro          # confirm the current, correct model string against
                                        # live Google Cloud documentation before build — this string
                                        # changes over time and an outdated value will fail silently
                                        # or fall back to unexpected behavior
AGENT_BUILDER_PROJECT_ID=lienmark-hackathon
AGENT_BUILDER_LOCATION=us-central1

# ── Parallel ───────────────────────────────────────────────────
PARALLEL_API_KEY=                     # NEVER filled in here — stored only in Secret Manager
                                        # as `parallel-api-key`; only the Research Agent's
                                        # service account may access it (see §4 below)
PARALLEL_SEARCH_API_BASE_URL=https://api.parallel.ai   # confirm exact base URL against
                                                            # current Parallel SDK docs before build

# ── Firestore ──────────────────────────────────────────────────
FIRESTORE_PROJECT_ID=lienmark-hackathon
FIRESTORE_DATABASE=(default)

# ── App config ─────────────────────────────────────────────────
ENVIRONMENT=development               # development | staging | production
LOG_LEVEL=info
DEMO_MODE=true                        # enables the deliberate-failure demo trigger (see below);
                                        # must be false in any real, non-demo deployment —
                                        # this flag should never ship enabled to a real customer

# ── Frontend ───────────────────────────────────────────────────
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
NEXT_PUBLIC_ENVIRONMENT=development

# ── Human-in-the-loop threshold ───────────────────────────────
RISK_CONFIDENCE_THRESHOLD=0.7         # claims scoring below this value route to needs_human_review
                                        # (see 04-prd.md §5.4 for why this threshold exists at all,
                                        # and 09-agent-orchestration.md for exactly how it's applied)
```

**On `DEMO_MODE` specifically:** this deserves a moment of explanation, since it's an unusual variable to include in a production-shaped `.env` file at all. The MVP scope deliberately requires demonstrating a graceful failure on camera (see `02-mvp-scope.md` §3 and the Pitch Deck's demo shot list) — rather than hoping a real Parallel timeout happens to occur naturally during the recording window (unreliable, and not something you can plan a video around), `DEMO_MODE=true` should enable a code path that deterministically simulates one claim's Parallel call failing, so the failure-handling behavior can be shown reliably and repeatedly while rehearsing the video. This flag existing at all is itself a small piece of evidence of deliberate engineering, worth mentioning if a judge asks how the failure moment in the video was achieved — the honest answer ("we built a controlled way to demonstrate our own failure handling") is a *better* answer than pretending it was a lucky, unplanned real failure.

## 3. Secret Manager mapping (production/hackathon deployment)

| Secret name in Secret Manager | Used by | Access scope |
|---|---|---|
| `parallel-api-key` | Research Agent only | Research Agent service account, read-only |
| `firestore-writer-creds` | Ledger Agent, Intake Agent (for the `claims` collection only) | Respective agent service accounts, write-scoped per collection, not project-wide |
| `gemini-api-key` (if not using Application Default Credentials) | All agents, via Agent Builder | Shared across agents, but prefer Application Default Credentials over a raw API key wherever the Agent Builder setup allows it — ADC avoids having a long-lived key material to manage and rotate at all |

## 4. Per-agent IAM / service account mapping — this is the literal implementation of §1's least-privilege principle, and of the hackathon's "Studio Head enforcing Cloud IAM" framing

This table is not a nice-to-have documentation exercise — it should be the actual source of truth that `backend/config/iam_bindings.py` (see `08-directory-structure.md`) implements in code, and that `scripts/setup_gcp.sh` provisions when the project is first set up.

| Agent | Service account | Permissions |
|---|---|---|
| Intake Agent | `sa-intake@...` | Read uploaded documents from Cloud Storage; write to the `claims` collection only |
| Research Agent | `sa-research@...` | Access the `parallel-api-key` secret; read `claims`; write to `research_findings` only |
| Ledger Agent | `sa-ledger@...` | Read `claims` and `research_findings`; **create-only** (no update, no delete — enforced by Firestore security rules, see `06-data-schema.md` §3) on `ledger_entries` |
| Risk Scoring Agent | `sa-scoring@...` | Read `ledger_entries`; write to `risk_scores` only |
| Report Agent | `sa-report@...` | Read all collections (it needs the full picture to compile a report); write to `reports` only |

**Worth stating explicitly why this granularity matters, beyond "it's good practice":** if any single agent's code has a bug — say, an errant write attempt from the Risk Scoring Agent that accidentally targets the `ledger_entries` collection instead of `risk_scores` — the least-privilege IAM setup means that write attempt fails at the infrastructure level, regardless of what the application code tried to do. This is a meaningfully stronger guarantee than "our code is careful not to do that," and it's the kind of design detail a technically sophisticated judge (or a real security-conscious buyer down the line) would specifically look for.

## 5. Local development setup

```bash
cp .env.example .env
# Fill in local values, or point GOOGLE_APPLICATION_CREDENTIALS at a downloaded
# service account key for local testing only — this key file must never be committed.

gcloud auth application-default login   # Preferred alternative to a downloaded key file
                                          # for most local development workflows
```

## 6. Never commit checklist — check this before every push, not just once at project setup

- [ ] `.env`
- [ ] `secrets/*.json`
- [ ] Any file matching `*-service-account*.json`
- [ ] `.env` is listed in `.gitignore` **before** the first commit is made, not added retroactively after noticing the omission — if a secret is ever committed and pushed, even briefly, treat it as compromised and rotate it immediately rather than just removing it from a later commit (git history retains it regardless of subsequent deletions unless history is explicitly rewritten, which is its own risk once a repo is public)
