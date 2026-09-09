# Local release evidence and remaining validation

## Verified September 9, 2026

- Canonical model roles run through Google ADK LlmAgent/Runner; Parallel Search is invoked through an ADK FunctionTool. Tests substitute external HTTP only. The model adapter preserves explicit provider-attempt semantics and returns actual HTTP receipts. No fallback bypasses ADK.
- 43 mounted backend/authentication/automation/ADK tests passed. A Linux child process exits abruptly after its first completed planner call; a replacement worker reuses the stored result, increments the fencing token and rejects stale writes. The lease is deliberately expired in this controlled test instead of waiting three minutes.
- 132 frontend tests passed. The outcome panel distinguishes empty, processing, failed, clarification and reviewer states. Preserved-approval counts require a recorded sign-off. Legacy offline action tests now substitute a failed transport rather than accidentally contacting a running paid backend.
- Next.js production build passed; its configured lint step is skipped, so this is not a lint-pass claim.
- Live ADK verification completed two jobs and ten provider calls, $0.42 reserved, with no decisions. The document arrived through the monitored folder and resumed its saved clarification.
- A larger isolated live run completed 24 provider calls, $0.96 reserved, three jobs. Three **simulated** baseline review actions produced two preserved approvals and two affected claims after a changed cut. A scope note resumed the piano question. One further simulated review action left one unresolved claim. An identical renamed revision produced no additional job. Reviewer actions are explicitly automated test data, never presented as human legal decisions.
- The larger run exported the same final snapshot as PDF and JSON execution record, through the mounted authenticated routes. The record includes source trigger, ADK event IDs, call correlation, returned provider receipts and reviewer history. Its digest is verifiable.
- A read-only smoke check of the actual local frontend passed: anonymous production access denied, authenticated workspace available, twelve ADK calls proven, execution-record digest matched, PDF matched the snapshot, and worker heartbeat was current.
- The five-page rehearsal PDF was rendered and visually inspected. Claim headings stay with their first detail line; page footers identify the draft. Historical research questions are labeled as preceding a recorded reviewer decision.

Artifacts are local under `.data/autonomous-live-verification.json` and `.data/outcome-verification/`. They are not automatically published or submitted. Review production evidence before sharing exports.

## Interactive handoff

The dedicated **The Last Rehearsal — demonstration** production contains live initial research with **no pre-recorded approvals**. Private local invitations are in `.data/last_rehearsal-private-access.md`. They expire after 24 hours and can each be redeemed once. The producer invitation used during UI verification may already be consumed; an established browser session goes directly to the workspace. Use the untouched reviewer invitation in a separate browser profile when the human operator is ready to review.

The local preview uses `SESSION_SQLITE_PATH=.data/sessions.sqlite3` with `USE_LOCAL_STORAGE=true`, so sessions, expiry and revocation survive a backend restart. Its Python environment is now `.data/runtime`, not a temporary directory. To issue fresh local invitations without changing the production or its allowance, use `python -m scripts.prepare_local_rehearsal --allowance 2 --renew-invites`.

Follow `demo/live-clearance/README.md`. The human reviewer supplies the decision rationale. Do not describe the fictional scenario as a real production clearance or the test scope note as a license. An unresolved permission is a valid outcome.

## Existing deployment smoke check

After the owner separately deploys this build and establishes a session, set `LIENMARK_VERIFY_COOKIE` privately to the existing session-cookie value and run:

```bash
python -m scripts.verify_clearance_release --url https://YOUR-WEB-ORIGIN --production YOUR_PRODUCTION
```

This command is read-only. It checks anonymous denial, authenticated scope, completed ADK events, execution-record integrity and PDF snapshot parity. It never uploads, starts research, signs off, creates sessions or deploys. It refuses insecure remote origins and does not follow redirects with the cookie.

## Not yet established

- This build has not been committed, pushed or deployed. Existing public URLs may run an older build.
- Actual Eventarc delivery, deployed IAM/audience configuration and cloud-process recovery require destination-environment verification. Local ADK traces do not prove managed Agent Engine deployment.
- No practitioner evaluation, customer endorsement, human time-saving measurement or insurer acceptance has been obtained. The separate practitioner worksheet is ready for a real evaluator; its results remain blank.
- No final demonstration video or hackathon submission is created by these checks. The packet includes a recording outline for the owner.

Remaining external work must not be relabeled as complete simply because local software checks pass.
