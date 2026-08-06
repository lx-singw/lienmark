# Hackathon Scope — Agentic Cinema: The Blockbuster Hackathon

This document is the binding reference for everything the hackathon actually requires, judges on, and rewards — as distinct from what we've decided to build (that's `02-mvp-scope.md`) or where the company goes after (that's `03-post-mvp-scope.md`). Read this document as "the rules of the game," and the others as "how we intend to win it."

## 1. Event details, in full

- **Name:** Agentic Cinema: The Blockbuster Hackathon
- **Host:** Google Cloud, run through Devpost, with a five-company partner ecosystem: IBM, Grafana, Parallel, Clickhouse, Replit
- **Registration/build window:** July 27 – September 7, 2026 (approximately six weeks)
- **Hard submission deadline:** September 7, 2026, 2:00 PM PDT — equivalently 10:00 PM GMT+1 the same day, per independent confirmation from Google's own hackathon coverage. No stated grace period; treat this as absolute.
- **Judging format — confirmed, and this materially shapes prep:** this is a **fully asynchronous, online hackathon**. There is no live pitch round, no demo day, no Q&A session with judges. Every submission is judged entirely against what's submitted: the hosted URL, the 3-minute video, the public repo, and the Devpost form. This means every argument, every anticipated objection, and every piece of context a judge might need has to be preemptively addressed *inside those four artifacts* — there is no follow-up opportunity to clarify or defend a decision after submission. `15-judge-qna-prep.md` exists specifically because of this constraint.
- **Judging panel:** not yet announced as of early August 2026, described generally as "enterprise experts and elite engineering leaders." Prep should stay general rather than trying to tailor to specific known judges.
- **A direct quote worth internalizing from Google's own hackathon coverage, since it states a real prioritization order:** judges want to see clean architecture that demonstrates true agentic behavior — clear reasoning steps, effective tool usage through external integrations, and robust error recovery when something in the execution chain goes wrong. **A pretty interface with broken backend logic will not survive the evaluation process.** This is a direct, external confirmation that Technological Implementation is not a criterion Design can compensate for if the backend is weak — worth keeping in mind if a build-time tradeoff ever pits UI polish against backend correctness.
- **Prize structure:** $75,000 total pool, split into **five identical, independent prize buckets**, one per partner track:
  - 1st place per track: $7,500
  - 2nd place per track: $4,500
  - 3rd place per track: $3,000
- **Our chosen track:** Parallel
- **Field size:** ~2,300 total registrants across all five tracks as of last check (early August). This number will almost certainly grow before the deadline — worth re-checking closer to submission if you want an updated read on competitive density.
- **Judging structure:** each track is judged **only against other submissions in that same track** — a Grafana-track team's quality has zero bearing on whether we place in the Parallel track. This is important: our actual competitive set is "other Parallel-track submissions," which is very likely narrower than IBM or Grafana given Parallel is a more specialized, less mainstream partner brand.

## 2. The literal build requirement

> Build a functional agent — powered by Gemini and Google Cloud Agent Builder — that integrates a Partner Entity's product or MCP to power a real media & entertainment workflow.

Breaking this sentence down into its actual binding components, because each clause is independently checkable by a judge:

1. **"Functional agent"** — it has to run, live, not be a static mockup or slide deck pretending to be software. A judge (or the video) needs to be able to observe it doing something.
2. **"Powered by Gemini and Google Cloud Agent Builder"** — both of these need to be genuinely present in the architecture, not swapped for a different LLM provider with Gemini mentioned only in the README.
3. **"Integrates a Partner Entity's product or MCP"** — this is the part that determines your track. Integration must be real (see §4 below for the Parallel-specific bar).
4. **"To power a real media & entertainment workflow"** — this is a soft but real constraint on subject matter. It rules out submissions that are generically enterprise (e.g., a generic customer-support agent) without any cinema/entertainment framing. Lienmark clears this cleanly — rights clearance is a workflow that only exists in this industry.

## 3. Partner connection methods (flexibility confirmed)

The overview explicitly lists three acceptable connection methods, in Google Cloud's own words:

> Connect to your partner tool using robust enterprise pipelines, API frameworks, or managed protocol adapters.

This means MCP (Model Context Protocol) is **one option among three**, not a requirement. "API frameworks" — meaning a direct SDK call — is equally valid and, for Parallel specifically, is the documented and expected integration path (see §4). We should stop thinking of MCP as something we're "missing" by not using it; a direct SDK integration is not a lesser or partial solution in the eyes of this hackathon's own rules.

## 4. Parallel-specific requirement (verbatim, this is the one clause that can disqualify us if we get it wrong)

> Your project must actively use Parallel's Search API at runtime — for example, via the official parallel-web SDK (Python or TypeScript), a supported integration such as the Vercel AI SDK's `@parallel-web/ai-sdk-tools` or LangChain's `ParallelWebSearchTool`, or a Grounding configuration using Parallel Web Search as the search provider. Referencing Parallel in your README alone does not satisfy this requirement — the integration must be present in your code.

Unpacking every implication of this paragraph:

- **"At runtime"** rules out a design where Parallel is called once during development to generate a static dataset that the demo then replays. The judge's expectation is that if they re-run your demo, real Parallel calls happen again, live.
- **"Search API"** specifically — not the Task API (deep, multi-step async research) or the Extract API (structured extraction from a known URL) as the *primary* satisfying mechanism. Those are legitimate to use *in addition*, but the Search API needs to be the backbone of what satisfies this requirement. This is good news for us — the Research Agent's actual job (per-claim ownership lookups) maps naturally onto Search, not onto the heavier async Task API.
- **Three named acceptable implementation paths:**
  1. Official `parallel-web` SDK, Python or TypeScript — our chosen path, see `09-agent-orchestration.md` §4
  2. Vercel AI SDK's Parallel tool integration — an alternative if the team ends up building the backend in a Vercel-native stack; not our current plan but worth knowing exists
  3. LangChain's `ParallelWebSearchTool` — relevant if we choose LangGraph as the orchestration layer (see Agent Orchestration doc), since this would let the Research Agent's Parallel call live natively inside a LangChain/LangGraph tool-calling pattern
- **"Referencing Parallel in your README alone does not satisfy this requirement"** — this sentence exists because past hackathons have clearly had teams try exactly this. It tells us the judges (or an automated check) will look at the actual codebase, not just trust the submission description. Our repo structure deliberately isolates the Parallel integration into one clearly-named file (`backend/agents/research/parallel_client.py`) specifically so a judge doing a quick code review can find and verify it in seconds — this is a design decision made *for* the judging process, not just for our own code cleanliness.

## 5. Eligibility and team composition — previously unconfirmed, now verified

Three binding rules surfaced on re-verification that weren't previously captured anywhere in this package:

- **Team size is capped at four eligible individuals.** Solo participation is explicitly allowed too, but if this is a team effort, four is the hard ceiling — worth confirming current team size against this now, not discovering it's a problem at submission time.
- **Age/eligibility:** participants must be above the legal age of majority in their country of residence, and some countries and territories are excluded entirely under the official rules — worth every team member individually confirming this applies to them, particularly if the team is international.
- **No pre-existing commercial products** — the solution must be built during the designated hackathon window (July 27 – September 7, 2026), not a repackaged existing product. This isn't a constraint on Lienmark specifically (the whole point of `10-build-timeline.md` is a fresh build starting within this window), but worth being explicit that *all* submitted code needs a commit history consistent with being written inside this window — a judge or automated check could plausibly verify this via repo commit timestamps.
- **Every team member must be individually registered on the official Devpost portal before the final submission deadline** — this is a per-person action item, not something the team lead can complete on everyone's behalf. Worth adding to `12-qa-checklist.md` as an explicit pre-submission check.

## 6. Full submission requirements checklist

Every item below is independently required — missing any one item risks disqualification regardless of how good the underlying project is.

- [ ] **URL to the hosted project** — must be a live, working deployment (Cloud Run URL), not "runs locally, trust us"
- [ ] **3-minute demo video**, with these sub-requirements:
  - Must show the project/agent **functioning as built** — the rules explicitly distinguish this from a cinematic trailer or concept video. Given the hackathon's whole theme is "cinema," it would be very easy for teams to over-index on making a polished, movie-trailer-style video instead of an honest screen recording of working software. That is explicitly the wrong instinct here.
  - Must be public on YouTube or Vimeo (unlisted is typically acceptable, private is not — confirm against the live rules page before final submission, as this detail is the kind that occasionally changes)
  - Must be in English, or have English subtitles if narrated in another language
- [ ] **URL to a public, open-source code repository** containing:
  - All source code
  - All assets used in the build
  - Complete run instructions (a judge with no prior context should be able to follow the README and get the project running)
- [ ] **Demonstrated runtime use of both Google Cloud and Parallel**, imported and called in code — this is the same "not README-only" standard applied to both required technologies, not just Parallel
- [ ] **Complete open-source license file**, detectable/visible at the top of the repo page (i.e., in the GitHub "About" section / repo root, not buried in a subfolder)
- [ ] **Partner track selected** in the Devpost submission form (Parallel)
- [ ] **Completed Devpost submission form** in full, including project description, technologies used, and any other required fields the form specifies at submission time (worth checking the live form directly a few days before the deadline, since form fields can be added or changed by organizers)

## 7. Judging criteria — full detail, with our specific answer to each

Devpost hackathons typically weight all four criteria equally (25% each) unless stated otherwise; treat them as equally important until/unless the rules page specifies different weights.

### 7.1 Technological Implementation
> How well is the project built, and how effectively does it use Google Cloud and the Partner services as part of the solution?

This criterion rewards **depth of integration**, not just presence of integration. A team that calls Parallel once for a single generic search will score lower here than a team that shows Parallel being called repeatedly, purposefully, per-claim, with visibly different results driving visibly different downstream agent behavior.

**Our specific answer:**
- Five distinct agents (Intake, Research, Ledger, Risk Scoring, Report), each with a clearly separated responsibility — this alone demonstrates more architectural sophistication than a single-prompt wrapper
- The Research Agent issues **N independent Parallel Search API calls** in a single pipeline run (one per extracted claim), not one blended query — this is the clearest way to demonstrate "effective use," since judges can literally count distinct, purposeful calls
- Deterministic, rule-based scoring logic layered on top of LLM-driven extraction — this shows engineering judgment about *where* to use an LLM and where not to, which is a mark of a team that understands the technology rather than just wrapping it
- Real, tested failure handling (a Parallel call can fail/timeout without crashing the pipeline) — production-grade engineering, not hackathon-grade shortcuts

### 7.2 Design
> Does the project deliver a complete, coherent product experience — not just a technical proof of concept?

This is explicitly the criterion most hackathon teams under-invest in, because it's tempting to spend 100% of build time on backend agent logic (which is more intellectually interesting to build) and treat the UI as an afterthought thrown together in the last 48 hours. The rules text itself warns against exactly this failure mode ("not just a technical proof of concept").

**Our specific answer:**
- A live-updating claims table — the single highest-leverage UI element, because it turns an otherwise invisible backend pipeline into something a judge can *watch happen*
- Every finding shown with its source, inline, not buried in a separate tab or log file
- An explicit, visible "needs human review" state in the UI, not just a database flag — this is a genuine product decision (see PRD §5.4) that also happens to be a strong visual demo moment
- A deliberately engineered failure-and-recovery moment shown gracefully in the UI, not a crash the presenter has to explain around

### 7.3 Potential Impact
> Does the project make a credible, specific case for solving a real problem for a real audience, and does the solution actually address it based on what's demonstrated?

The phrase "based on what's demonstrated" is doing real work here — this criterion isn't just about how good your pitch narrative is, it's about whether what you actually *showed* in the demo backs up the claim. A team that pitches a huge vision but demos something that doesn't obviously connect to it will score worse here than a team with a more modest but tightly-matched pitch-to-demo story.

**Our specific answer:**
- Named, specific buyers (completion bond companies, E&O insurers, post-production supervisors) rather than a vague "filmmakers" audience
- A live, current regulatory hook (studio cease-and-desist actions against AI video platforms, tightening SAG-AFTRA consent rules) that makes the timing argument concrete, not hypothetical
- A quantified cost baseline ($250–700/hour for entertainment counsel, 200+ claims typical on a mid-budget production) that gives judges a number to repeat when arguing for us in deliberation
- Critically: the demo has to visibly do what the pitch claims — the sourced, cited report at the end of the demo run is the proof point that ties the "impact" narrative back to "what was demonstrated"

### 7.4 Quality of the Idea
> Is this a creative, non-obvious use of Google Cloud and the Partner services, and does the team show genuine understanding of the problem space?

**Our specific answer:**
- Rights clearance is genuinely under-served — this was validated, not assumed, against a wide competitive-landscape research pass (script coverage, VFX budgeting, dubbing, piracy protection, trailer generation, and streaming-acquisition analytics were all found to be saturated with funded competitors; see `03-post-mvp-scope.md` §"Competitive landscape validation" for the full breakdown)
- The submission narrative deliberately maps onto all three of the hackathon's own framing roles (Director, Technical Producer, Studio Head) rather than optimizing for just one — see PRD §2.3 and the Pitch Deck for how this is made explicit rather than left implicit
- "Genuine understanding of the problem space" is best demonstrated by specificity — knowing that entertainment counsel runs $250-700/hour, knowing the exact regulatory dynamic currently in motion, and building a scoring model that reflects how real ownership disputes actually get resolved (source authority + recency + corroboration, not a black-box confidence number) all signal real domain understanding rather than a surface-level idea.

## 8. Competitive field analysis

At ~2,300 total registrants across five tracks, a naive even split puts each track around 450 teams — but this is very unlikely to be the real distribution. IBM and Grafana are both broadly recognized enterprise brands that will pull a larger share of less-specialized teams; Parallel is a comparatively niche, developer-focused API company, which likely means:

- A smaller absolute number of Parallel-track submissions
- A higher proportion of teams who are genuinely technically capable (since choosing Parallel over a bigger household name is itself a signal of intentionality)
- But also: a real risk that other capable teams have also identified rights/compliance/verification as an obvious fit for a "research API" partner — meaning our differentiation needs to come from **depth and polish of execution**, not from assuming the idea itself is uncontested territory

**What NOT to assume:** that being in a smaller field means an easier path to 1st. It likely means a higher average quality bar per submission, since the teams self-selecting into a technical, less mainstream partner track skew more serious.

## 9. Non-negotiable constraints carried forward into MVP scope

These five constraints are the hard boundary conditions that `02-mvp-scope.md` is built inside of. Any proposed feature or scope addition that would violate one of these should be rejected regardless of how good the idea is on its own merits:

1. Real Parallel Search API calls at runtime, visible in the demo, not mocked or pre-recorded
2. Real Google Cloud Agent Builder / Gemini orchestration — genuinely multi-agent, not a single-prompt wrapper dressed up as "agents"
3. Public repo, complete OSS license visible at repo root, full run instructions that work for someone with zero prior context
4. A 3-minute demo video that is an honest screen recording of functioning software, not a cinematic concept trailer
5. Everything must be realistically buildable within the six-week window by the current team's actual size and skill set — ambition should be calibrated against this, not against the theoretical best version of the idea
