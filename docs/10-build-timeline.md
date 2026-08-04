# Build Timeline — Lienmark Hackathon Sprint

**Today:** Monday, August 3, 2026
**Deadline:** Monday, September 7, 2026, 2:00 PM PDT
**Available time:** exactly 5 weeks

This is a working plan, not a wishlist — every week ends with something demonstrable, not just "progress." If a week's deliverable isn't real by its end date, that's the signal to cut scope (see `02-mvp-scope.md` §8 for what's already pre-approved to cut) rather than let the whole schedule slip silently.

## Week 0 — before Week 1 truly starts (do this today or tomorrow, not later)

- [ ] **Redeem the Google Cloud credit coupon now.** Deadline is August 31, separate from and earlier than the submission deadline — see the credits form. Don't let this become a Week 5 fire drill.
- [ ] **The Parallel + Gemini spike test** (30-60 minutes): confirm Parallel's Search API returns usable, checkable results for a real ownership-style query (e.g., search for the actual demo claims drafted in `10-demo-content.md`) before building anything else on top of that assumption. If results are thin or unreliable, this is the week to discover it and adjust the demo claim set — not week 4.
- [ ] Confirm current Gemini model string and Agent Builder setup steps against live Google Cloud docs (the value in `07-env-vars.md` is a placeholder pending this check)

## Week 1 (Aug 3 – Aug 9): Foundation + de-risking

**Goal by end of week:** a running (even if logic-empty) repo skeleton, a provisioned GCP project with correct IAM, and validated demo content to build against.

- Mon-Tue: Spike test (Week 0 item, if not already done); GCP project setup (`scripts/setup_gcp.sh`), five service accounts provisioned per the IAM table in `07-env-vars.md` §4
- Tue-Wed: Repo scaffolding matching `08-directory-structure.md` exactly; Firestore schema stood up per `06-data-schema.md`; Firestore security rules for `ledger_entries` immutability written and tested in isolation
- Wed-Thu: Draft demo script content (`10-demo-content.md` — see that doc, should be done in parallel with this week, not blocking it)
- Thu-Fri: `.env.example`, secrets in Secret Manager, local dev environment confirmed working for at least one teammate other than whoever set it up
- **End-of-week checkpoint:** can you run `pytest` against an empty/stub test suite and have it pass? Can you deploy an empty "hello world" Cloud Run service through the actual pipeline you'll use for the real app? If either answer is no, that's a Week 2 blocker forming now.

## Week 2 (Aug 10 – Aug 16): Intake + Research Agents

**Goal by end of week:** claims go in one end, sourced findings come out the other, for real, against the real Parallel API.

- Mon-Tue: Intake Agent — claim extraction logic, `claim_extraction.py`, the confidentiality length/content check on `extracted_description` (see `09-agent-orchestration.md` §2)
- Tue-Wed: Test Intake Agent against the real demo script content from `10-demo-content.md` — confirm it extracts exactly the claims expected, not more, not fewer
- Wed-Thu: Research Agent — `parallel_client.py` (the hackathon-required integration file), `query_builder.py`
- Thu-Fri: Wire Intake → Research together; confirm real, live Parallel calls happen per claim; build and test the failure-handling path (`call_status: failed`)
- **End-of-week checkpoint:** can you feed the real demo script in and get back real, sourced findings for every claim, including one showing `call_status: failed` when deliberately triggered? If yes, the hackathon's single hardest requirement (real runtime Parallel integration) is now de-risked with five weeks to spare, not one.

## Week 3 (Aug 17 – Aug 23): Ledger + Risk Scoring Agents

**Goal by end of week:** the governance core — immutability and deterministic arbitration — both real and tested.

- Mon-Tue: Ledger Agent — `append_only_store.py`, versioning/`superseded_by` logic
- Tue: `tests/test_ledger_immutability.py` — write this test *before* declaring the Ledger Agent done, not after
- Wed-Thu: Risk Scoring Agent — `deterministic_rules.py` (the scoring function), `conflict_arbitration.py`
- Thu: `tests/test_risk_scoring_determinism.py` — same principle, write it early, not as an afterthought
- Fri: Wire all four agents together (Intake → Research → Ledger → Risk Scoring); confirm the engineered-conflict demo claim from `10-demo-content.md` actually triggers the arbitration path end-to-end
- **End-of-week checkpoint:** does the conflict-arbitration demo beat (see `05-pitch-deck.md` shot list, 1:45–2:10) actually work, live, against real data? This is the single most important checkpoint in the whole schedule — if it's not working by end of Week 3, it needs dedicated Week 4 time pulled from somewhere else, because this is the strongest differentiation moment in the entire submission.

## Week 4 (Aug 24 – Aug 30): Report Agent + orchestration + frontend

**Goal by end of week:** the full five-agent pipeline runs end-to-end, and there's a real UI a judge could look at without narration.

- Mon: Report Agent — sourced report generation, the three-way cleared/flagged/pending-review split
- Mon-Tue: Full pipeline orchestration (`pipeline.py`, `agent_builder_config.py`) — all five agents wired together as one real, callable flow
- Tue-Thu: Frontend — commit to Next.js or fall back to Streamlit **now**, per the decision point in `02-mvp-scope.md` §4.1, based on actual velocity so far, not by default drift. Build `ClaimsTable.tsx` (live-updating), `SourceCitation.tsx`, `HumanReviewFlag.tsx` in that priority order — the claims table is the single highest-leverage screen, build it first and best.
- Thu-Fri: Deploy the full stack to Cloud Run (staging URL); per-agent IAM enforcement confirmed working in the deployed environment, not just locally
- **End-of-week checkpoint:** can someone who isn't you upload the demo script to the live staging URL and watch the full pipeline run, live, in a browser? If not, this is the most urgent possible fix for the first two days of Week 5.

## Week 5 (Aug 31 – Sep 7): Demo, polish, submission

**Hard deadline reminder:** Sep 7, 2:00 PM PDT. Treat Sep 6 evening as the real deadline, not Sep 7 — leave a buffer day for anything that goes wrong with the submission form, video upload, or a last-minute deploy issue.

- Sun Aug 31: **Google Cloud credit redemption hard deadline** (separate from submission — see Week 0)
- Mon-Tue: Full run-through of the pre-submission QA checklist (`11-qa-checklist.md`) — ideally by a teammate who didn't write the code being tested
- Tue-Wed: Record the demo video — multiple takes, following the shot list in `05-pitch-deck.md`; do a dry run with a stopwatch before the take you intend to actually submit
- Wed: Final README pass — assume zero prior context, per `08-directory-structure.md` §3
- Thu: Production Cloud Run deployment (the actual URL going in the submission, not the staging one); final full QA checklist run against the *production* URL specifically, not staging
- Fri Sep 4 – Sat Sep 5: Buffer. Use this time to fix whatever the QA pass surfaced, not to add new features. New features stop being acceptable to start after this point in the schedule.
- Sun Sep 6: Submit. Complete the Devpost form, attach all links, do a final click-through of every submitted link as if you were a judge seeing it cold.
- Mon Sep 7, before 2:00 PM PDT: Nothing left to do except confirm the submission is actually visible and complete on Devpost's side.

## Risk register — the things most likely to blow this schedule

| Risk | Likely week it bites | Mitigation |
|---|---|---|
| Parallel Search API doesn't return clean, checkable results for entertainment-rights-style queries | Week 0-1 | This is exactly why the spike test is first, not last |
| The engineered-conflict demo claim doesn't reliably trigger arbitration | Week 3 | Build 2-3 candidate conflict claims during Week 1-2 demo content drafting, not just one, so there's a fallback if the first choice doesn't behave as expected against live search results |
| Frontend takes longer than expected, crowding out demo prep | Week 4 | The Streamlit fallback decision exists specifically for this — use it if Week 4 velocity is behind schedule, don't stay committed to Next.js out of sunk-cost momentum |
| Team member availability gaps (day jobs, other commitments) during a 5-week unpaid sprint | Any week | Not solvable in a doc — but worth an honest conversation now about who has how many real hours per week, so the schedule above is checked against actual capacity, not aspirational capacity |
