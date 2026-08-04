# Directory Structure — Lienmark

## 1. Top-level layout

```
lienmark/
├── README.md                     # setup + run instructions (judges will use this directly —
│                                    treat this file as if it will be read by someone with
│                                    zero prior context and five minutes of patience)
├── LICENSE                        # MIT, must be visible/detectable at repo root — GitHub
│                                    surfaces this automatically in the repo "About" panel
│                                    when named and placed correctly
├── .env.example
├── .gitignore
├── docs/                          # this documentation package, in full
│   ├── 00-README.md
│   ├── 01-hackathon-scope.md
│   ├── 02-mvp-scope.md
│   ├── 03-post-mvp-scope.md
│   ├── 04-prd.md
│   ├── 05-pitch-deck.md
│   ├── 06-data-schema.md
│   ├── 07-env-vars.md
│   ├── 08-directory-structure.md
│   └── 09-agent-orchestration.md
├── backend/
│   ├── agents/
│   │   ├── intake/
│   │   │   ├── agent.py
│   │   │   ├── prompts.py
│   │   │   └── claim_extraction.py
│   │   ├── research/
│   │   │   ├── agent.py
│   │   │   ├── parallel_client.py        # THE required hackathon artifact — this file is
│   │   │   │                                where a judge doing a quick code review should be
│   │   │   │                                able to immediately find and verify the real,
│   │   │   │                                live Parallel Search API integration
│   │   │   └── query_builder.py           # builds minimal, non-identifying search terms —
│   │   │                                    the code-level enforcement of the confidentiality
│   │   │                                    requirement in 04-prd.md §5.6
│   │   ├── ledger/
│   │   │   ├── agent.py
│   │   │   └── append_only_store.py       # enforces create-only writes at the application
│   │   │                                    layer, on top of the Firestore security rules
│   │   │                                    enforcement described in 06-data-schema.md §3
│   │   ├── risk_scoring/
│   │   │   ├── agent.py
│   │   │   ├── deterministic_rules.py     # rule-based scoring logic — NOT an LLM freehand
│   │   │   │                                judgment; this file is where the "deterministic,
│   │   │   │                                multi-step agent" hackathon requirement is
│   │   │   │                                literally satisfied in code
│   │   │   └── conflict_arbitration.py    # multi-source conflict resolution — the code
│   │   │                                    behind the demo's centerpiece moment
│   │   └── report/
│   │       ├── agent.py
│   │       └── report_formatter.py
│   ├── orchestration/
│   │   ├── pipeline.py                    # top-level agent orchestration / control flow —
│   │   │                                    the file that wires all five agents together
│   │   │                                    in the sequence described in 09-agent-orchestration.md
│   │   └── agent_builder_config.py        # Google Cloud Agent Builder setup — the other
│   │                                        hackathon-required integration, alongside Parallel
│   ├── storage/
│   │   ├── firestore_client.py
│   │   └── schema.py                      # mirrors docs/06-data-schema.md exactly —
│   │                                        if these two ever drift apart, the doc is
│   │                                        wrong and needs to be updated to match the code,
│   │                                        not the other way around
│   ├── config/
│   │   ├── settings.py                    # loads env vars; contains zero hardcoded secrets
│   │   └── iam_bindings.py                # documents and enforces the per-agent service
│   │                                        account mapping from 07-env-vars.md §4 in code,
│   │                                        not just in documentation
│   └── main.py                            # Cloud Run entrypoint
├── frontend/
│   ├── app/                               # Next.js app directory (default choice — see
│   │   │                                    02-mvp-scope.md §4.1 for the Streamlit
│   │   │                                    fallback decision point if build time runs short)
│   │   ├── page.tsx                       # upload + live claims table — the single
│   │   │                                    highest-leverage screen in the whole product
│   │   ├── report/[production_id]/page.tsx
│   │   └── components/
│   │       ├── ClaimsTable.tsx            # the live-updating demo-critical component —
│   │       │                                see 02-mvp-scope.md §3 for exactly what
│   │       │                                behavior this needs to support
│   │       ├── ClaimRow.tsx
│   │       ├── SourceCitation.tsx         # renders the inline, clickable source for
│   │       │                                every finding — this component exists
│   │       │                                specifically to make the "no unsourced
│   │       │                                verdicts" requirement visible, not just true
│   │       └── HumanReviewFlag.tsx        # a genuinely distinct visual treatment,
│   │                                        not just a red table row — see
│   │                                        02-mvp-scope.md §3 for why this needs to
│   │                                        read as a real product state
│   └── lib/
│       └── api_client.ts
├── demo/
│   ├── sample_script.pdf                  # the deliberately-mixed claim set — one clean,
│   │                                        one high-risk, one engineered to trigger
│   │                                        conflicting Parallel findings (see
│   │                                        02-mvp-scope.md §3 for the exact requirement)
│   ├── demo_script.md                     # narration script for the 3-minute video,
│   │                                        matching the shot list in 05-pitch-deck.md
│   └── failure_trigger.md                 # how to reproduce the graceful-failure demo
│                                            moment reliably, using DEMO_MODE (see
│                                            07-env-vars.md §2)
├── scripts/
│   ├── setup_gcp.sh                       # provisions the GCP project, all five per-agent
│   │                                        service accounts, and their IAM bindings —
│   │                                        should implement the table in
│   │                                        07-env-vars.md §4 exactly
│   ├── deploy.sh
│   └── seed_demo_data.py
└── tests/
    ├── test_intake_agent.py
    ├── test_research_agent.py             # mocks Parallel for fast unit tests; a separate
    │                                        integration test suite should hit the real
    │                                        API to confirm the live integration actually
    │                                        works end to end, not just against a mock
    ├── test_ledger_immutability.py        # explicitly tests that update/delete against
    │                                        ledger_entries is rejected — using the
    │                                        Ledger Agent's real service account
    │                                        credentials, not a superuser bypass
    └── test_risk_scoring_determinism.py   # explicitly tests same input → same output,
                                             run multiple times — this is the concrete
                                             proof behind the "deterministic agent" claim
```

## 2. Rationale for key structural decisions, explained rather than just asserted

- **`agents/` is split by responsibility, not by generic "utils" grouping.** Each agent is a fully self-contained module with its own prompts and logic, directly mirroring the five-agent architecture described in `04-prd.md` and `09-agent-orchestration.md`. This makes it trivial for anyone — a judge doing a fast code review, a future engineer joining the project, or the current team six weeks from now — to find exactly what code implements what claim in the PRD, without having to trace logic scattered across generic shared files.

- **`research/parallel_client.py` is deliberately isolated into its own file, not inlined into `agent.py`.** This single file is what satisfies the hackathon's hardest, most specific requirement (see `01-hackathon-scope.md` §4: "imported and called in code, not README-only"). Keeping it isolated means it's easy to point a judge directly at exactly the file that proves compliance, rather than making them read through a larger, mixed-purpose file to find the relevant lines.

- **`ledger/append_only_store.py` is its own file, not inline logic inside `agent.py`.** The immutability guarantee is the single core governance claim of the entire product — it deserves to be independently readable, independently testable (see `tests/test_ledger_immutability.py`), and independently auditable by someone who wants to verify the claim without reading unrelated agent logic.

- **`demo/` is a first-class top-level directory, not an afterthought bolted on in the final week.** Given that the Design judging criterion explicitly rewards "a complete, coherent product experience" (see `01-hackathon-scope.md` §6.2), the demo data and the failure-trigger mechanism are treated as real engineering deliverables with their own directory and their own files, planned for from the start — not scrambled together the night before recording.

- **`config/iam_bindings.py` exists specifically to make the least-privilege design real and checkable in code**, rather than leaving it as something only described in `07-env-vars.md`. A judge or future security reviewer should be able to open this one file and see the actual permission boundaries enforced, not have to trust that the documentation matches an implementation they can't easily locate.

## 3. README.md structure (top-level, judge-facing — this is the file a judge will actually open first)

```markdown
# Lienmark

[One paragraph: the problem, the solution, the long-term vision in one sentence]

## Quickstart
[Exact commands to run locally — copy-pasteable, tested by someone other than
the person who wrote them, ideally on a clean machine or fresh clone]

## Architecture
[Link to docs/09-agent-orchestration.md, plus one simple diagram —
the five-agent control-flow diagram from that document works well here]

## Required integrations (for judges — make this section impossible to miss)
- Google Cloud Agent Builder: see backend/orchestration/agent_builder_config.py
- Parallel Search API: see backend/agents/research/parallel_client.py

## Demo
[Link to the hosted Cloud Run URL, link to the 3-minute YouTube/Vimeo video]

## License
MIT — see LICENSE
```

**Why the "Required integrations" section is called out this explicitly, with direct file links rather than just a general architecture description:** given that `01-hackathon-scope.md` §4 quotes the hackathon's own rule that "referencing Parallel in your README alone does not satisfy this requirement," the README's job here isn't to *claim* compliance — it's to make it as fast and easy as possible for a time-constrained judge to independently verify compliance themselves by clicking straight to the exact file. A judge who has to hunt through an unfamiliar codebase to find the required integration is a judge who might reasonably give up and assume it isn't there. Removing that friction entirely is a small effort with an outsized effect on judging outcomes.
