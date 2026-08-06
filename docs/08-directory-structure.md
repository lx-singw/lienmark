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
│   ├── 09-agent-orchestration.md
│   ├── 10-build-timeline.md
│   ├── 11-demo-content.md
│   ├── 12-qa-checklist.md
│   ├── 13-technical-validation.md
│   ├── 14-sources-appendix.md
│   ├── 15-judge-qna-prep.md
│   ├── 16-liability-and-trust-posture.md
│   ├── 17-moat-mechanics.md
│   ├── 18-company-formation-readiness.md
│   ├── 19-executive-summary.md
│   ├── 20-adversarial-input-defense.md
│   ├── 21-agent-prompts.md
│   ├── 22-pre-mortem.md
│   ├── 23-competitor-comparison-matrix.md
│   ├── 24-vision-and-mission.md
│   └── 25-agentic-maturity-roadmap.md
├── backend/
│   ├── agents/
│   │   ├── intake/
│   │   │   ├── agent.py
│   │   │   ├── prompts.py
│   │   │   ├── claim_extraction.py
│   │   │   └── self_reflection.py        # self-reflection pass & prompt-injection defense —
│   │   │                                    see 02-mvp-scope.md §1 & 20-adversarial-input-defense.md §2
│   │   ├── research/
│   │   │   ├── agent.py
│   │   │   ├── parallel_client.py        # THE required hackathon artifact — live Parallel SDK integration
│   │   │   ├── multi_tool_router.py      # dynamic multi-tool selection (Parallel Search API vs Task API) —
│   │   │   │                                see 04-prd.md §5.3 & 09-agent-orchestration.md §4
│   │   │   └── query_builder.py           # builds minimal, non-identifying search terms —
│   │   │                                    the code-level enforcement of confidentiality in 04-prd.md §5.6
│   │   ├── ledger/
│   │   │   ├── agent.py
│   │   │   └── append_only_store.py       # enforces create-only writes at the application
│   │   │                                    layer, on top of Firestore security rules (06-data-schema.md §3)
│   │   ├── risk_scoring/
│   │   │   ├── agent.py
│   │   │   ├── deterministic_rules.py     # rule-based scoring logic — NOT an LLM freehand judgment
│   │   │   └── conflict_arbitration.py    # multi-source conflict resolution — the code behind the demo centerpiece
│   │   ├── report/
│   │   │   ├── agent.py
│   │   │   └── report_formatter.py
│   │   └── discovery/                     # autonomous proactive re-review poller — 6th agent module (02-mvp-scope.md §1)
│   │       ├── agent.py
│   │       └── poller.py
│   ├── orchestration/
│   │   ├── pipeline.py                    # top-level agent orchestration / control flow (09-agent-orchestration.md)
│   │   └── agent_builder_config.py        # Google Cloud Agent Builder setup — hackathon-required orchestration config
│   ├── storage/
│   │   ├── firestore_client.py
│   │   ├── firestore.rules                # protocol-level create-only rules for ledger_entries (06-data-schema.md §3)
│   │   └── schema.py                      # mirrors docs/06-data-schema.md exactly
│   ├── config/
│   │   ├── settings.py                    # loads env vars; contains zero hardcoded secrets
│   │   └── iam_bindings.py                # enforces per-agent service account mapping (07-env-vars.md §4)
│   ├── Dockerfile                         # Cloud Run container definition
│   └── main.py                            # Cloud Run entrypoint
├── frontend/
│   ├── app/                               # Next.js app directory
│   │   ├── globals.css                    # CSS Design Token system — dark mode (#0B0F17), glassmorphism, status glows
│   │   ├── page.tsx                       # upload + live claims table — primary product view
│   │   ├── report/[production_id]/page.tsx
│   │   └── components/
│   │       ├── ClaimsTable.tsx            # live-updating demo-critical component (02-mvp-scope.md §3)
│   │       ├── ClaimRow.tsx
│   │       ├── SourceCitation.tsx         # inline clickable source citation component
│   │       ├── HumanReviewFlag.tsx        # distinct visual treatment for human review state
│   │       ├── DiscoveryNotification.tsx  # proactive resurfacing alert toast component
│   │       └── ClarifyingQuestionModal.tsx # interactive modal for human-in-the-loop action
│   ├── lib/
│   │   └── api_client.ts
│   └── package.json
├── demo/
│   ├── sample_script.pdf                  # primary test fixture (mixed claim set + conflict arbitration)
│   ├── sample_script_adversarial.pdf      # adversarial prompt-injection test fixture (20-adversarial-input-defense.md)
│   ├── parallel_conflict_example.json     # sample conflict JSON payload fixture (11-demo-content.md)
│   ├── demo_script.md                     # narration script for 3-minute video (05-pitch-deck.md)
│   └── failure_trigger.md                 # graceful-failure demo trigger mechanism (07-env-vars.md §2)
├── tests/
│   ├── test_intake_agent.py
│   ├── test_research_agent.py             # unit tests mocking Parallel API calls
│   ├── test_ledger_immutability.py        # storage-layer create-only security rule tests
│   ├── test_risk_scoring_determinism.py   # scoring engine determinism tests
│   ├── test_adversarial_defense.py        # prompt injection trap test fixture
│   └── test_e2e_pipeline.py               # E2E benchmark pipeline runner under pytest
├── scripts/
│   ├── setup_gcp.sh                       # provisions GCP project, service accounts, IAM bindings
│   ├── deploy.sh
│   ├── run_local_demo.sh                  # one-click local runner launching backend + frontend
│   ├── seed_demo_data.py
│   ├── test_week0_validation.py           # Week 0 API de-risking script (13-technical-validation.md)
│   └── verify_integrations.py             # 60-second judge compliance verification helper (12-qa-checklist.md §3)
├── .github/
│   └── workflows/
│       └── ci.yml                         # runs automated test suite on every PR
```

## 2. Rationale for key structural decisions, explained rather than just asserted

- **`agents/` is split by responsibility, not by generic "utils" grouping.** Each agent is a fully self-contained module with its own prompts and logic, directly mirroring the architecture described in `04-prd.md` and `09-agent-orchestration.md`. This includes `discovery/`, which implements the proactive re-review poller (`02-mvp-scope.md` §1) to demonstrate true autonomous initiative rather than purely reactive execution.

- **`research/parallel_client.py` is deliberately isolated into its own file, not inlined into `agent.py`.** This single file is what satisfies the hackathon's hardest, most specific requirement (see `01-hackathon-scope.md` §4: "imported and called in code, not README-only"). Keeping it isolated means it's easy to point a judge directly at exactly the file that proves compliance, rather than making them read through a larger, mixed-purpose file to find the relevant lines.

- **`ledger/append_only_store.py` and `storage/firestore.rules` work together for immutability.** The immutability guarantee is the single core governance claim of the entire product — application-layer enforcement in `append_only_store.py` is backed by protocol-level security rules in `firestore.rules` (`06-data-schema.md` §3). It deserves to be independently readable, independently testable (`tests/test_ledger_immutability.py`), and independently auditable.

- **`intake/self_reflection.py` isolates prompt-injection defenses and extraction reflection.** Prompt injection is a major risk for LLM-driven compliance tools (`20-adversarial-input-defense.md`). Keeping self-reflection and instruction-hierarchy defenses isolated makes the Technological Implementation story clean and checkable.

- **`demo/` is a first-class top-level directory, not an afterthought bolted on in the final week.** Given that the Design judging criterion explicitly rewards "a complete, coherent product experience" (see `01-hackathon-scope.md` §6.2), the demo data, adversarial fixtures (`sample_script_adversarial.pdf`), and the failure-trigger mechanism are treated as real engineering deliverables with their own directory and their own files, planned for from the start — not scrambled together the night before recording.

- **`scripts/verify_integrations.py` provides a 60-second compliance check.** As noted in `22-pre-mortem.md` §4 and `12-qa-checklist.md` §3, judges reviewing asynchronously need an immediate, foolproof path to verify required API calls without debugging environment issues.

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
