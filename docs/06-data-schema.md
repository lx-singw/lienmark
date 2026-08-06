# Data Schema — Lienmark

## 1. Design principles, and why each one matters

### 1.1 Append-only for anything ledger-related
No `UPDATE` or `DELETE` operation may ever touch a claim, finding, or ledger record. Every state change is expressed as a new row, with a `superseded_by` pointer added to whatever record it replaces. This is not a stylistic preference or premature optimization — it is the direct technical implementation of the product's entire trust claim. If a ledger record could be silently edited or deleted, the "tamper-evident record" pitch (see `04-prd.md` §2.2 and §5.5) would simply be false, and any buyer who audited the system closely enough would find that out. The append-only constraint needs to be enforced at the storage layer itself (see §5 below), not just followed as an application-level convention that a future bug, or a future engineer unfamiliar with the reasoning, could accidentally violate.

### 1.2 Every finding must carry its source
No row in `research_findings` may exist without a non-null `source_url` and a `retrieved_at` timestamp. This directly enables the Report Agent's hard requirement (see `04-prd.md` §5.7) that no verdict in the final output can be unsourced. Enforcing this at the schema level — rather than trusting every code path that writes a finding to remember to include a source — closes off an entire category of bug where a future feature addition accidentally produces an unsourced claim that undermines the product's core trust proposition.

### 1.3 Confidentiality by construction
The `claims` collection stores only extracted, minimal search terms — never full scene or script text. The complete original source document lives in a separate, access-restricted storage location (Cloud Storage, not Firestore) and is never duplicated into any record that might later be logged, transmitted to Parallel, or exposed in a report. This schema-level separation is what makes the confidentiality requirement in `04-prd.md` §5.6 actually true, rather than just an intention that depends on every future engineer remembering not to violate it.

## 2. MVP schema (Firestore, hackathon build)

Firestore is a document database, so the schema below describes logical collections and document shape rather than SQL tables — but field names are deliberately kept in `snake_case` throughout, specifically so the eventual migration to Postgres (§4 below) doesn't require a renaming pass across the whole codebase. This is a small amount of upfront discipline that removes a real category of migration risk later.

### `productions`
The top-level container for a single clearance run — corresponds to one script or cut being processed.

```
production_id: string (doc id)
title: string
created_at: timestamp
source_document_ref: string     # storage path to the uploaded script/cut in Cloud Storage,
                                  # never duplicated into any other collection
status: enum [processing, complete, needs_review]
```

**Why `status` lives here and not derived on the fly:** having a denormalized top-level status field lets the UI's live-updating claims table (see `02-mvp-scope.md` §3) query a single cheap document rather than aggregating across every claim/finding/ledger-entry on every render — this matters specifically because the demo needs this table to feel responsive and live, not laggy.

### `claims`
Every rights-triggering element extracted by the Intake Agent or proposed mid-run by the Research Agent.

```
claim_id: string (doc id)
production_id: string (ref)
type: enum [music, footage, brand, real_person, genai_flag, other]
scene_ref: string                # e.g. "INT. WAREHOUSE - NIGHT, p.14" — traceability back to source
extracted_description: string    # short, non-identifying — e.g. "song 'X' by artist Y"
needs_clarification: boolean     # true if the Intake Agent couldn't confidently type/describe this claim
proposed_by_agent: string (nullable) # agent ID if claim was discovered mid-run during multi-hop search
is_delta_modified: boolean       # true if newly introduced or modified in script draft delta diff
co_occurring_claim_ids: array[string] # claim IDs sharing scene-level proximity (e.g. brand + music)
genai_provenance_required: boolean # true if synthetic media keywords detected in stage directions
opt_out_registry_flagged: boolean # true if training opt-out notice found on Spawning.ai/HaveIBeenTrained
territory_codes: array[string]  # target distribution jurisdictions e.g. ["US", "EU", "UK", "JP"]
estimated_licensing_cost_min: float (nullable) # estimated cost floor for clearance rate cards
estimated_licensing_cost_max: float (nullable) # estimated cost ceiling
created_at: timestamp
```

**Concrete example document**, to make the abstraction tangible:
```json
{
  "claim_id": "clm_7f3a9b",
  "production_id": "prod_demo_01",
  "type": "music",
  "scene_ref": "p.34, INT. CAR - NIGHT",
  "extracted_description": "song 'Bohemian Rhapsody' by Queen — sync licensing status",
  "needs_clarification": false,
  "proposed_by_agent": null,
  "is_delta_modified": true,
  "co_occurring_claim_ids": ["clm_brand_88a"],
  "genai_provenance_required": false,
  "opt_out_registry_flagged": false,
  "territory_codes": ["US", "EU"],
  "estimated_licensing_cost_min": 15000.0,
  "estimated_licensing_cost_max": 35000.0,
  "created_at": "2026-08-15T14:22:03Z"
}
```

### `research_findings`
Every result returned by Parallel Search/Task API calls, one per claim per query attempt.

```
finding_id: string (doc id)
claim_id: string (ref)
source_url: string               # REQUIRED, non-null — enforced at write time, not just by convention
cached_snapshot_url: string (nullable) # Web Archive fallback if HEAD check fails on source_url
source_snippet: string           # short excerpt supporting the finding, used for inline citation display
ownership_status: enum [clear, disputed, unknown, licensing_required]
retrieved_at: timestamp
parallel_query: string           # actual query string sent to Parallel — kept for auditability
tool_used: enum [parallel_search_api, parallel_task_api] # dynamic multi-tool selection
multi_hop_depth: integer         # 0 for initial pass, 1+ for self-directed secondary lead chasing
consensus_verified: boolean      # true if dual independent query passes yielded identical verdict
escalation_level: integer        # 1 = standard dashboard toast, 2 = automated email/Slack escalation
source_authority_tier: enum [official_registry, secondary_news, unverified_blog] # authority weighting
corroboration_factor: float      # source authority weight score (1.0 = PRO database, 0.2 = blog)
call_status: enum [success, failed, timeout]
```

**Precise definitions for each `ownership_status` value** — this wasn't previously specified precisely enough to guarantee consistent agent behavior, which is a real implementation-ambiguity risk worth closing before code gets written, since two engineers (or two runs of an LLM-assisted extraction) could otherwise reasonably classify the same finding differently:

- **`clear`** — a credible source affirmatively states the work is public domain, unrestricted, or otherwise usable without further licensing action. Requires a positive statement, not just an absence of found restrictions — "no licensing information found" is `unknown`, not `clear`.
- **`licensing_required`** — a credible source confirms active, enforceable rights exist (a live trademark, an active copyright with an identifiable holder) and some licensing or clearance action is required before use. This is a confident, actionable finding, not a vague risk flag.
- **`disputed`** — multiple credible sources make contradictory claims about ownership or clearance status for the same claim. This is the state that triggers `conflict_detected: true` in the Risk Scoring Agent (§5 below) — by definition, a claim cannot be `disputed` from a single finding alone; it requires at least two findings in tension.
- **`unknown`** — the search returned no sufficiently credible or specific result either way. This is meaningfully different from `disputed` (contradiction) and different from a failed call (`call_status: failed`, which means the search itself didn't complete) — `unknown` means the search completed successfully but didn't produce a usable answer.

**Why `parallel_query` is stored verbatim:** beyond auditability, this field is what lets a judge (or a future engineer) verify that the confidentiality requirement (§1.3) is actually being honored — anyone can inspect this field and confirm the query sent to Parallel was the minimal, non-identifying description, not the full scene text. This turns a design *claim* into something independently checkable.

### `ledger_entries` — append-only, the core governance artifact
This is the single most important collection in the entire schema — everything else exists to feed this one, and this one is what a real buyer would eventually want to audit directly.

```
entry_id: string (doc id)
claim_id: string (ref)
finding_id: string (ref, nullable — an entry can exist before a finding does, e.g. "claim registered, research pending")
version: integer                 # increments per claim; a version number is never reused
action_type: enum [agent_finding, attorney_approval, attorney_override] # distinguishes automated finding from human legal sign-off
status: enum [pending, cleared, flagged, needs_human_review, attorney_cleared, attorney_flagged]
superseded_by: string (nullable, ref to a later entry_id — set when a newer entry replaces this one)
written_at: timestamp
written_by_agent: string         # agent ID or human attorney ID/email — part of the audit trail
reviewed_by: string (nullable)   # attorney name/ID/email when action_type is attorney_approval or attorney_override
override_reason: string (nullable) # detailed legal rationale for attorney override or approval
legal_citation_ref: string (nullable) # legal document, license contract ref, or statutory exemption cited by attorney
```

**Worked example 1 (Automated Research Versioning):** imagine claim `clm_7f3a9b` is first researched and comes back `cleared` (version 1, `action_type: agent_finding`). Weeks later, the production is re-evaluated before a distribution deal closes, and a new Parallel search surfaces a fresh dispute over that same song's rights. The correct behavior is **not** to edit the version-1 entry. Instead:
1. A new `research_findings` document is created reflecting the new dispute
2. A new `ledger_entries` document is created: `version: 2`, `status: flagged`, `action_type: agent_finding`, referencing the new finding
3. The version-1 entry gets its `superseded_by` field set to the version-2 entry's ID
4. Both entries remain permanently queryable — anyone auditing the ledger can see the full history: it was cleared, then later flagged, and exactly when and why each state existed

**Worked example 2 (Human Attorney Override Versioning):** Continuing from Example 1, suppose production legal counsel reviews the `flagged` claim (version 2) and provides an executed synchronization license agreement (#SYNC-2026-884) proving rights were secured off-platform. The attorney submits an override in the UI:
1. A new `ledger_entries` document is created: `version: 3`, `status: attorney_cleared`, `action_type: attorney_override`, `reviewed_by: "attorney_jane_doe@productionlegal.com"`, `override_reason: "Executed master & sync license agreement verified on file"`, `legal_citation_ref: "License Agreement #SYNC-2026-884"`
2. The version-2 entry gets its `superseded_by` field set to the version-3 entry's ID
3. The complete audit trail (v1 automated clear $\rightarrow$ v2 automated flag $\rightarrow$ v3 human attorney clearance) is preserved immutably for underwriters and bond companies without erasing the historical agent findings.

### `risk_scores`
The deterministic output of the Risk Scoring Agent for each claim.

```
score_id: string (doc id)
claim_id: string (ref)
ledger_entry_id: string (ref)
confidence: float (0.0-1.0)
conflict_detected: boolean
conflict_sources: array<string>   # source_urls in conflict, if any — populated only when conflict_detected is true
scoring_method: string             # name of the deterministic rule applied, e.g. "authority_recency_corroboration_v1"
                                     # kept for auditability — if the scoring logic changes over time,
                                     # historical scores remain interpretable against the rule version that produced them
computed_at: timestamp
```

### `reports`
The final, buyer-facing output of a completed clearance run.

```
report_id: string (doc id)
production_id: string (ref)
generated_at: timestamp
overall_risk_summary: string
cleared_claim_ids: array<string>
flagged_claim_ids: array<string>
pending_review_claim_ids: array<string>
```

### `agent_state_store`
Checkpoints execution state for the persistent Discovery Agent to survive serverless cold starts.

```
agent_id: string (doc id e.g. "discovery_poller_01")
last_polled_at: timestamp
active_watchers: array<string>         # watched GCS bucket URIs or local folders
pending_reverifications: array<string> # claim IDs queued for scheduled re-check
last_heartbeat_at: timestamp
status: enum [active_listening, polling, recovering, idle]
```

## 3. Firestore security rules (the actual enforcement mechanism for §1.1)

The append-only invariant on `ledger_entries` is enforced here, not merely described in this document. A simplified illustration of the rule shape (confirm exact Firestore Security Rules syntax against current documentation before implementation):

```
match /ledger_entries/{entryId} {
  allow create: if request.auth.token.agent == "ledger_agent";
  allow update: if false;   // no code path, no exception, ever
  allow delete: if false;   // same
  allow read: if true;      // reports/UI need to read this collection freely
}
```

This is the concrete artifact `tests/test_ledger_immutability.py` (see `08-directory-structure.md`) tests against — the test should attempt an update and a delete using the Ledger Agent's actual service account credentials and confirm both are rejected by Firestore itself, not just by application logic that could be bypassed.

## 4. Post-MVP migration: Cloud SQL (Postgres)

Move to Postgres once cross-production queries and row-level audit logging become real, customer-driven requirements (Phase 2 — see `03-post-mvp-scope.md` §7 for the full phased infrastructure roadmap). The Firestore schema above translates directly into relational tables with foreign keys; because field names were kept in `snake_case` from the start (§1), the main migration work is proper indexing and relational integrity, not a renaming pass.

**Key additions at this stage:**
- `productions.buyer_org_id` — a foreign key to a new `organizations` table, which supports the insurer/bond-company buyer model directly at the schema level (a production is associated with the buying organization that requires its clearance certificate)
- Row-level security policies scoped by `buyer_org_id`, so one insurer's productions are never visible to another
- A materialized view specifically for "delta since last check" queries — this is the concrete infrastructure that makes the Ledger Agent's memory-efficiency goal (see `04-prd.md` §5.5 and `09-agent-orchestration.md`) actually fast at scale, rather than just theoretically correct

## 5. Phase 3: graph layer

Chain-of-title is structurally a graph, not a flat relational shape — ownership assignments, option chains, and estate transfers all involve traversal-style questions ("who owns this now, given three prior assignments and one estate transfer") that relational joins handle awkwardly and graph queries handle naturally. At Phase 3 (see `03-post-mvp-scope.md` §5), introduce a graph store — Neo4j, or Postgres with a graph extension such as AGE — alongside the existing Postgres deployment, rather than replacing it:

- **Nodes:** `Work`, `RightsHolder`, `Estate`, `Assignment`
- **Edges:** `ASSIGNED_TO`, `OPTIONED_BY`, `INHERITED_BY`, `DISPUTED_BY`

This is explicitly not needed for MVP or Phase 2 — it's documented here only so early schema decisions (keeping `claims` and `research_findings` normalized rather than deeply nested, for instance) don't accidentally make this future migration harder than it needs to be.

## 6. Non-negotiable invariants — enforce in code and storage rules, not just in this document

1. No write path may update or delete a `ledger_entries` document — enforced via Firestore security rules restricting the Ledger Agent's service account to `create` only on that collection (see §3)
2. Every `research_findings` write must include a non-null `source_url` — worth adding an application-level validation check in addition to any storage-layer constraint, since catching this early (before write) produces a better error message than discovering a malformed document later
3. `claims.extracted_description` must never contain more than a short, claim-specific phrase — enforce a length and content check in the Intake Agent's write path before the document is created, not merely as a prompting instruction to the LLM that could be silently ignored on an unusual input
