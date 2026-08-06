# Demo Content — Script Excerpt, Claims, and Narration

This is the actual content the demo runs against — not a placeholder description of what the demo content should eventually be. Everything here needs to be validated against a real Parallel Search API call during Week 0-1 (see `10-build-timeline.md`), since claims about how Parallel will resolve these are informed guesses based on public knowledge, not confirmed API responses yet.

## 1. The script excerpt (`demo/sample_script.pdf` source text)

```
                                    "MIDNIGHT DINER"

INT. ROADSIDE DINER - NIGHT

A cramped diner, neon flickering. RAY (50s, tired eyes) sits alone
at the counter. The jukebox in the corner plays a soft, familiar
piano melody — CLAIR DE LUNE — as rain streaks the window.

Behind the counter, a small television, muted, plays grainy black-
and-white footage: the APOLLO 11 MOON LANDING BROADCAST, the
astronaut's boots touching the surface for the first time.

RAY reaches for a bottle on the counter. He takes a long drink of
COCA-COLA, sets it down hard enough to rattle the ice.

Behind him, tucked into a cracked leather jacket pocket, a pack of
MARLBORO cigarettes is just visible.

RAY
    (to no one)
It's been fifty years and we still
watch that tape like it's happening
right now.

He doesn't look away from the screen.
```

## 2. Expected Intake Agent output

Per the extraction rules in `09-agent-orchestration.md` §3 — minimal, non-identifying, no plot/emotional context carried through:

```json
[
  {
    "claim_id": "clm_001",
    "type": "music",
    "scene_ref": "p.1, INT. ROADSIDE DINER - NIGHT",
    "extracted_description": "instrumental piece 'Clair de Lune' by Claude Debussy — sync licensing status",
    "needs_clarification": false
  },
  {
    "claim_id": "clm_002",
    "type": "footage",
    "scene_ref": "p.1, INT. ROADSIDE DINER - NIGHT",
    "extracted_description": "archival footage — Apollo 11 moon landing broadcast — ownership/licensing status",
    "needs_clarification": false
  },
  {
    "claim_id": "clm_003",
    "type": "brand",
    "scene_ref": "p.1, INT. ROADSIDE DINER - NIGHT",
    "extracted_description": "Coca-Cola product shown on-screen — trademark/product placement clearance",
    "needs_clarification": false
  },
  {
    "claim_id": "clm_004",
    "type": "brand",
    "scene_ref": "p.1, INT. ROADSIDE DINER - NIGHT",
    "extracted_description": "Marlboro cigarette packaging shown on-screen — trademark clearance",
    "needs_clarification": false
  }
]
```

## 3. Why each claim was chosen — the reasoning behind the demo set, not just the content

### `clm_001` — Clair de Lune (the "clean" claim)
Debussy died in 1918; the composition itself has been in the public domain for decades in essentially every jurisdiction (copyright term is life of the author plus 70 years in most countries, meaning this passed into the public domain around 1988). This should resolve cleanly and quickly — a good "clean" demo beat, and it's chosen specifically because it's *verifiably, unambiguously* true, not a convenient assumption. **Validation note:** confirm during the Week 0 spike test that Parallel's search actually surfaces this clearly, since the demo depends on this resolving fast and clean on camera.

### `clm_002` — Apollo 11 moon landing broadcast footage (the engineered-conflict claim)
This is a real, well-documented rights ambiguity, not a contrived one — which matters, because it makes the demo's conflict-arbitration beat honest rather than gamed. The underlying facts: raw NASA-originated footage of the moon landing is a U.S. government work and is public domain under 17 U.S.C. § 105. However, the *broadcast* footage most people actually picture — with network commentary, graphics, and camera coverage decisions layered on by CBS (Walter Cronkite's coverage) or another network — is separately copyrighted by that network, since the broadcast itself is a distinct copyrightable work from the underlying government footage it's built on. A real Parallel search on "Apollo 11 moon landing broadcast footage ownership" is plausible to surface both facts from different sources — one emphasizing the NASA/public-domain angle, one emphasizing the network-broadcast-copyright angle — which is exactly the kind of genuine disagreement the Risk Scoring Agent's arbitration logic is built to catch and explain (see `09-agent-orchestration.md` §6).

**This is the claim the whole demo's centerpiece moment depends on — treat it as the highest-priority item to validate early**, not late. If live Parallel results don't naturally produce this split during the Week 0-1 spike test, the fallback (documented honestly, not hidden) is to phrase the extracted claim in a way likely to surface both angles, or to pre-identify the two specific source URLs during demo-content prep and confirm the query reliably returns them before committing to this as the recorded take.

### `clm_003` — Coca-Cola (the "flagged/licensing required" claim)
A real, live, actively-enforced trademark, clearly requiring clearance for any commercial use, especially in an unlicensed product-placement-style appearance. This should resolve to `licensing_required` reliably and predictably — a good second demo beat showing the system correctly flagging a real, non-ambiguous risk that isn't just "unknown."

### `clm_004` — Marlboro (the deliberately-triggered failure claim)
This claim is not meant to resolve normally — it's the one deliberately routed through the `DEMO_MODE` simulated-failure path (see `07-env-vars.md` §2 and `demo/failure_trigger.md`) to reliably demonstrate graceful failure handling on camera. It was chosen as the failure-trigger candidate specifically because it's narratively minor (a background prop, not a focal point of the scene), so simulating a research failure on it doesn't disrupt the demo's narrative flow the way failing on the moon-landing claim (the centerpiece) would.

## 4. Expected resolution summary (for validation against real Week 0-1 spike test results)

| Claim | Expected `ownership_status` | Expected `confidence` band | Routes to human review? |
|---|---|---|---|
| clm_001 (Clair de Lune) | `clear` | High (>0.85) | No |
| clm_002 (Apollo 11 footage) | Conflicting findings → arbitrated verdict, likely `licensing_required` with both sources logged | Moderate, `conflict_detected: true` | **Yes** — this is the point |
| clm_003 (Coca-Cola) | `licensing_required` | High (>0.85) | No — confidently flagged, not uncertain |
| clm_004 (Marlboro) | N/A — `call_status: failed` (simulated) | N/A | Yes — "research incomplete" |

**If real spike-test results don't match this table**, update the table to match reality, not the other way around — this document describes the intended demo, but the actual live behavior of a real API against real claims is the ground truth, and the demo narration should never claim something the software doesn't actually do.

## 5. Narration script (`demo/demo_script.md`), mapped to the pitch deck shot list

Matches `05-pitch-deck.md`'s timing exactly — this is the words-to-say version of that shot list.

**[0:00–0:15]** *(over the cost-baseline stat visual)*
"Every production carries dozens to hundreds of unresolved rights claims. Clearing them manually runs $250 to $700 an hour, and most productions handle it inconsistently, under time pressure, with no audit trail. Lienmark automates that research."

**[0:15–0:30]** *(architecture slide)*
"Five agents: Intake extracts every rights-triggering claim. Research verifies each one live against the web using Parallel's Search API. Ledger logs everything immutably. Risk Scoring arbitrates and scores. Report produces a sourced, auditable output."

**[0:30–0:45]** *(the watcher beat — the answer to 'does this just wait for a human')*
"This is where a production already keeps its scripts — nothing special, just a shared folder. Watch: I'll drop this scene in... and there — nobody clicked run. The Discovery Agent noticed the new file and started processing on its own."

**[0:45–1:45]** *(live run, narrating as it happens)*
"Here's a real scene — a diner, a jukebox playing Debussy, a TV showing Apollo 11 footage, a Coca-Cola bottle, a pack of Marlboros in the background. Watch the claims table populate live... Clair de Lune resolves clean — Debussy's been public domain for decades... Coca-Cola comes back flagged, licensing required... and here — the Marlboro claim — a research call just failed. Watch what happens: it doesn't crash the pipeline, it routes to manual review and keeps going."

**[1:45–2:10]** *(the arbitration beat)*
"Now the interesting one: Apollo 11 footage. A single-pass agent would've grabbed the first result — 'NASA footage, public domain' — and stopped there. But the raw footage and the network broadcast of it are legally distinct. Lienmark's arbitration step catches both: NASA's footage is public domain, but this appears to be the CBS broadcast, which is separately copyrighted. Both sources logged, conflict flagged, routed to a human — because a real clearance decision here needs a person, not a guess."

**[2:10–2:25]** *(the Discovery Agent beat — the answer to 'is this really agentic')*
"Watch this claim sit in review for a moment... and there — nobody clicked anything. The Discovery Agent noticed it was still pending and resurfaced it on its own. That's the difference between a pipeline that reacts when told to, and one that's actually pursuing a goal — keeping this production's clearance status current, without being asked."

**[2:25–2:45]** *(final report)*
"Every finding here links to its actual source — nothing in this report is a verdict without a citation."

**[2:45–2:55]** *(vision line)*
"This is the title insurance model, applied to entertainment — unglamorous, but the record everyone has to check before a deal closes."

**[2:55–3:00]** *(close)*
"Lienmark. Parallel track. Thanks for watching."

## 6. `demo/failure_trigger.md` — how the simulated failure actually works

```markdown
# Failure Trigger — Demo Reproduction Steps

With `DEMO_MODE=true` set (see 07-env-vars.md §2), the Research Agent's
`parallel_client.py` should check the claim_id being processed against a
small hardcoded demo-only list, and for clm_004 specifically, skip the real
API call and instead deterministically return a `call_status: failed` finding
after a short artificial delay (~2 seconds, long enough to be visible on
screen as "in progress" before failing, short enough not to drag the pacing).

This must NEVER be active when DEMO_MODE is unset or false — verify this
explicitly before any real deployment, since shipping this simulated-failure
logic live to a real customer would be actively harmful (a real user
deserves real results, not a scripted failure).
```
