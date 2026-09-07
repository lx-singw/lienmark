---
trigger: always_on
---

# Security & Dependencies

## Security (never traded off for speed, style, or coverage numbers)

- No hardcoded secrets/keys/tokens/connection strings anywhere, including tests,
  fixtures, and comments. Source from env vars or the repo's existing secrets
  mechanism. Never commit real values to `.env` — only `.env.example` placeholders.
- Parameterize/escape/sanitize every sink that touches user input: SQL, shell args,
  `innerHTML`/`dangerouslySetInnerHTML`, template rendering, file paths (check for
  traversal).
- Never hand-roll crypto or auth primitives — use the repo's existing vetted library.
- State the access-control assumption (public / authenticated / role-gated) for every
  new route in your plan, and make sure the actual check exists in code, not just the
  assumption.
- Disabling a security lint rule, TLS check, or CSRF guard "to make the build pass"
  requires explicit user approval and a documented reason. Never do it silently.

## Dependencies

- Adding a new package requires justification in the pre-flight plan: why it's
  needed, and what native-code or already-installed-library alternative was
  considered.
- Preference order: native language feature > already-installed library > new
  well-maintained package. Don't add a second library that duplicates one already
  in the tree.
- Note the license of any new dependency; flag copyleft/restrictive licenses.
- Update the lockfile in the same change — never leave manifest and lockfile
  out of sync.
- When adding/bumping a dependency, check for known high/critical CVEs at that
  version via the audit command in quality_gate.md and flag findings rather than
  proceeding silently.
