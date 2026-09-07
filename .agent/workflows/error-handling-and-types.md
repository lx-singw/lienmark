---
trigger: always_on
---

# Error Handling & Type Safety

- No empty `catch {}` blocks and no bare `console.log(error)` as the only handling.
  Every catch must do something: rethrow as a typed error, recover, or surface to the
  caller with context.
- Expose typed domain errors (`UserNotFoundError`, `ValidationError`, etc.) extending
  the native `Error` class — don't throw raw strings or generic `Error`.
- Every network-facing boundary (incoming request body, outgoing API call response)
  passes through runtime validation (schema or type guard) before use.
- Wrap dynamic UI state/external-service bindings in error boundaries with a real
  fallback UI, not a blank crash.
- Structured logs at error boundaries include error code + operation metadata.
  **Never** log credentials, tokens, or PII, including at debug level.
- No `any`, and no `unknown as X` without a runtime check first. Every function
  signature and return contract has an explicit type.
- Suppressing a type error is not the same as fixing it. `// eslint-disable`,
  `@ts-ignore`, `@ts-expect-error`, or equivalent suppressions used to silence a real
  type violation (rather than a genuine, documented false positive) is a rule
  violation — the underlying type issue must actually be resolved.
