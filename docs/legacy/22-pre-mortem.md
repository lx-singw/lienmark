# Pre-Mortem — Why This Might Not Win, Examined in Advance

`12-qa-checklist.md` verifies the submission works correctly. This document is a different exercise: assume it's the day after results are announced and Lienmark did *not* place 1st in the Parallel track — work backward and ask why, honestly, before it happens rather than after. Pre-mortems surface risks that pure execution-checking misses, because they force consideration of scenarios where everything was built correctly but still lost.

## 1. "A competing team built something more visually impressive"

**The scenario:** another Parallel-track team builds a flashier, more visually dramatic demo — real-time video generation, a slicker 3D interface, something that produces an immediate "wow" in the first 10 seconds of a video — and wins on visceral impact even if its underlying agentic architecture is thinner than Lienmark's.

**Why this is a real risk, not a hypothetical:** judges watch many submissions in sequence; a demo that's immediately visually striking has a real advantage in a format where attention and memorability compound across dozens of videos watched back-to-back, regardless of the stated judging criteria.

**Mitigation already partially in place:** the wireframes built for this package are functional, not decorative — worth a deliberate pass asking whether the actual built UI (not just the wireframe) has enough visual polish (color, motion on the live-updating table, a clean typographic hierarchy) to hold attention in the first 10-15 seconds, not just be *correct*. This is worth treating as a real design task, not an afterthought, even though the wireframes prioritized information architecture over visual flourish.

**What NOT to do in response:** don't chase flashiness by adding generative-visual features that dilute the actual product thesis (this would directly contradict the explicit non-goal in `03-post-mvp-scope.md` §8 against bolting on content-generation features). The right response is polish on the real product's real UI, not a superficial addition.

## 2. "The judge doesn't have entertainment-industry context and the pitch doesn't land"

**The scenario:** a judge with a strong technical or general-enterprise background, but no specific entertainment-industry knowledge, doesn't intuitively grasp why rights clearance is a real, painful, expensive problem — the pitch assumes more industry context than a judge actually has, and the argument doesn't land in the available viewing time.

**Mitigation:** the demo script content (`11-demo-content.md`) was deliberately built around universally recognizable reference points (a famous piece of classical music, the moon landing, Coca-Cola) specifically so the *stakes* of each claim type are self-evident without requiring entertainment-industry background — this was a good instinct already built in, worth keeping front-of-mind as the video narration gets finalized, and worth stress-testing the narration script (`11-demo-content.md` §5) by reading it to someone with zero entertainment-industry background and checking whether the "why does this matter" lands within the first 30 seconds.

## 3. "The video is technically correct but paced poorly, and the strongest moment gets rushed"

**The scenario:** the conflict-arbitration beat (`05-pitch-deck.md`'s single most important demo moment, per its own framing) gets compressed into 10 seconds because earlier sections ran long, and the most differentiating part of the whole submission ends up feeling like an afterthought rather than the centerpiece it's meant to be.

**Mitigation already in place:** `10-build-timeline.md` Week 5 explicitly calls for a stopwatch dry run before the final recording — worth treating this as non-negotiable, not optional, specifically because this is the single most likely way a strong build could still produce a weak video.

## 4. "The repo is correct but a judge doing a fast review can't find the required integrations quickly enough"

**The scenario:** a judge with limited time per submission opens the repo, doesn't immediately find clear evidence of the required Parallel and Google Cloud integrations, and either assumes they're not there or scores "Technological Implementation" lower than the actual code deserves, simply due to friction in verification.

**Mitigation already in place:** `08-directory-structure.md` §3's README structure exists specifically to solve this — direct links to `parallel_client.py` and `agent_builder_config.py` in a clearly labeled "Required integrations" section. Worth explicitly testing this exact scenario during QA (`12-qa-checklist.md` §3 already covers this) — have someone unfamiliar with the repo try to verify both integrations in under 60 seconds, and treat any friction found as a real bug to fix, not a minor UX nitpick.

## 5. "A judge tests the live conflict-arbitration claim and Parallel's results have drifted since demo recording"

**The scenario:** live web search results are not static — between demo recording and whenever a judge might independently interact with the hosted URL (if they do), the specific Apollo 11 footage query could return different results than what's shown in the video, because the underlying web content has changed or Parallel's index has updated.

**Why this is a real, not hypothetical, risk:** this is the unavoidable tradeoff of building a demo around genuinely live search rather than mocked data — it's the right choice for hackathon compliance and honesty (`01-hackathon-scope.md` §4), but it does mean the exact conflict shown in the video is not guaranteed to reproduce identically on a later live run.

**Mitigation:** this is worth stating proactively rather than hoping it doesn't come up — a line in the README or judge Q&A prep (`15-judge-qna-prep.md`) noting that live search results can shift over time by nature of the live-web-search architecture, and that this is expected, disclosed behavior of a system built on genuinely live data, not a bug. A judge who understands this upfront is far less likely to read a differently-resolved re-run as evidence something's broken.

## 6. "The team's own bandwidth is the actual constraint, not the plan"

**The scenario:** every document in this package assumes execution capacity that may not match the team's actual available hours, especially given this is very likely unpaid, alongside other commitments.

**Mitigation:** `10-build-timeline.md`'s risk register already names this honestly rather than avoiding it — worth revisiting that specific risk item and having a real, current conversation about actual weekly hours available per team member, since every other document in this package assumes the plan gets executed, and no amount of planning quality substitutes for available building time.

## 7. The meta-lesson from doing this exercise at all

Every mitigation above already existed in some form somewhere in the prior 20 documents — this exercise didn't discover entirely new problems so much as it forced them into a single, prioritized, "what could actually go wrong" frame rather than being scattered as asides across a large package. That's the actual value of a pre-mortem done deliberately: not new information, but a forcing function that surfaces what matters most among everything already known. Worth revisiting this document specifically in Week 4-5 (per `10-build-timeline.md`), once there's a real build to evaluate these risks against rather than a plan.
