---
trigger: glob
globs: ["**/api/**", "**/routes/**", "**/services/**", "**/*.controller.*", "**/jobs/**", "**/workers/**"]
---

# Observability

- New service entry points (API routes, queue consumers, scheduled jobs) log
  start/completion of the operation, not only failure.
- Instrument new business-significant code paths consistently with whatever
  metrics/tracing setup already exists in the repo (OpenTelemetry, StatsD,
  Prometheus, etc.) — don't introduce a new observability stack unilaterally.
- Debug-level logs are subject to the same no-secrets/no-PII rule as error logs.
