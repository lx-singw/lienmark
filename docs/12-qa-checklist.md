# Pre-Submission QA Checklist

Run this in full, ideally by a teammate who did **not** write the code being checked — a fresh pair of eyes catches things the builder has stopped seeing. Per `10-build-timeline.md`, this should run at least twice: once mid-Week 5 against staging, and once final against the actual production URL going into the submission. Do not submit until every box is checked against production, not staging.

## 1. The "zero prior context" test — the single most important check

- [ ] On a clean machine (or at minimum, a fresh clone into an empty directory), clone the public repo using only the URL that will be submitted
- [ ] Follow the README's Quickstart section literally, doing nothing the README doesn't tell you to do
- [ ] Confirm the project runs successfully using only those instructions — if you had to guess a step, fix the README, don't just remember it for next time
- [ ] Time how long this takes — if it's more than 10-15 minutes, a time-constrained judge may give up before finishing; consider trimming setup steps or providing a hosted URL as the primary path (see §2)

## 2. Hosted project check

- [ ] The submitted URL is live, loads without errors, and is the **production** deployment, not a staging or local-only link
- [ ] Upload the actual demo script content from `11-demo-content.md` through the live hosted UI, start to finish, exactly as a judge would
- [ ] Confirm the full five-agent pipeline runs end-to-end on the hosted instance specifically — a pipeline that only works locally is not a passing state
- [ ] Reload the page mid-run at least once to confirm the UI doesn't break on refresh (judges may do this without thinking about it)

## 3. Hackathon-required integration checks (the two things that can disqualify, not just lose points)

- [ ] Open `backend/agents/research/parallel_client.py` directly on GitHub and confirm the Parallel SDK import and a real, callable function are visible in the file itself — not just referenced in the README (see `01-hackathon-scope.md` §4 for exactly why this specific check exists)
- [ ] Confirm the call is to the **Search API** specifically, not solely the Task or Extract API, per the exact wording of the requirement
- [ ] Confirm Google Cloud Agent Builder / Gemini usage is similarly visible and callable in `backend/orchestration/agent_builder_config.py`, not just described
- [ ] Trigger a real pipeline run and confirm — via logs, or a visible network call, or a debug panel — that a live API call actually fires against Parallel at that moment, not a cached or pre-recorded response

## 4. License and repo hygiene

- [ ] `LICENSE` file exists at the repo root (not in a subfolder) and GitHub's own UI correctly detects and displays it in the repo's "About" panel
- [ ] Repo is genuinely public — check this from a logged-out browser or an account with no prior access, not just from your own logged-in session
- [ ] No secrets committed anywhere in the repo, including git history — run a search across the full commit history for `PARALLEL_API_KEY`, `.env`, and `service-account` as a final check, not just the current file tree (see `07-env-vars.md` §6 for why this matters)
- [ ] `.env.example` is present and accurate; `.env` itself is absent from the repo

## 5. Automated test suite

- [ ] `tests/test_ledger_immutability.py` passes — and specifically, confirm it's actually testing against the real Firestore security rules, not a mock that would pass regardless of whether the rules are correctly configured
- [ ] `tests/test_risk_scoring_determinism.py` passes, run at least 3 times in a row to build real confidence in the determinism claim, not just once
- [ ] Full test suite (`pytest`) passes cleanly from a fresh clone with no manual setup beyond what the README documents

## 6. Demo video

- [ ] Video is exactly 3 minutes or under — check the actual runtime, don't estimate
- [ ] Public on YouTube or Vimeo, and confirm the privacy setting from a logged-out browser (an "unlisted" video with the wrong setting, or an accidentally-private one, is a real and common failure mode)
- [ ] Shows the software actually functioning — a fresh, honest re-watch asking "does this look like a screen recording of real software, or does it look like a scripted trailer" (see `01-hackathon-scope.md` §6 for why this distinction is explicitly called out in the rules)
- [ ] English audio, or accurate English subtitles if not
- [ ] The conflict-arbitration beat (1:45–2:10 in the shot list) is present and clearly explained, not rushed or cut for time
- [ ] The graceful-failure moment is present and visibly doesn't crash the pipeline

## 7. Devpost submission form

- [ ] Project description accurately matches what's actually built — no aspirational claims about features that don't exist yet in the submitted repo
- [ ] Parallel selected as the track
- [ ] All required links (hosted URL, video, repo) are pasted correctly — click each one from the submitted form itself, not from your own bookmarks, to confirm they resolve correctly as submitted
- [ ] Technologies-used field lists Google Cloud Agent Builder, Gemini, and Parallel explicitly
- [ ] Submission is completed with real buffer time before the Sep 7, 2:00 PM PDT deadline — not attempted for the first time in the final hour, when a form issue or upload failure has no recovery time
- [ ] **Team size is at or under the 4-person cap** (`01-hackathon-scope.md` §5) — confirm this explicitly, not just assume it, especially if the team composition shifted at any point during the build
- [ ] **Every team member is individually registered on the official Devpost portal**, not just the person submitting the form (`01-hackathon-scope.md` §5) — this needs each person to have completed their own registration, and it's worth confirming this a few days before the deadline, not on submission day
- [ ] **Every team member independently meets the age/eligibility requirement** for their country of residence (`01-hackathon-scope.md` §5) — worth a direct one-line confirmation from each person, not an assumption
- [ ] **Repo commit history is consistent with the code being written during the hackathon window** (July 27 – September 7, 2026) — per the no-pre-existing-commercial-product rule (`01-hackathon-scope.md` §5); this should already be true given the build timeline, but worth a conscious check rather than an assumption

## 8. Final sanity pass — read this out loud to the team before hitting submit

- [ ] Every claim made in the video and written submission is something the actual, submitted code genuinely does — not something planned, not something that worked once locally, not something that's "basically there"
- [ ] If a judge did every single check in this document themselves, right now, against exactly what's submitted, would every item still pass? If there's hesitation on any item, fix it before submitting, not after
