# Technical Validation — De-Risking Findings

This document records what's been genuinely validated so far, what's still assumed, and exactly what to test in Week 0 (see `10-build-timeline.md`). Treat every "assumed, not verified" item below as a real risk to the schedule until it's checked with actual code against actual APIs — this document does not replace that testing, it scopes it precisely.

## 1. Parallel Search API viability — proxy-tested, genuinely promising

**What was actually done:** since this environment can't call Parallel's API directly, the exact queries the Research Agent would issue were run through general web search instead — a reasonable proxy, since Parallel is also a web-scale search API, and if general search returns thin or ambiguous results, that's a real warning sign regardless of provider.

**Result for the "clean" demo claim (Clair de Lune):** strong. Multiple independent sources (Wikimedia Commons, Trademarkia, a specialized music-licensing database) converged cleanly and quickly on "public domain, composer died 1918." This is exactly the kind of fast, confident, well-sourced result the demo's first beat needs.

**Result for the engineered-conflict claim (Apollo 11 footage):** stronger than hoped. This isn't just a plausible ambiguity — it's a documented, live dispute pattern. Search surfaced: (a) archive.org and NASA's own flight journal confirming raw footage is public domain under 17 U.S.C. § 105, and (b) a separate, real, ongoing problem where YouTube copyright-enforcement bots have been filing false ownership claims against public-domain Apollo footage on behalf of unrelated broadcast-footage rightsholders — a film archivist's documented experience of exactly this conflict. This means the demo's centerpiece arbitration moment can be built around a genuinely real, currently-relevant dispute, not a contrived one, which is both more honest and a better story to tell judges.

**What this does NOT prove:** that Parallel's specific API, with its specific ranking and result format, will surface these same sources in the same way. General web search and Parallel's Search API are different products built on different indexes. **The Week 0 spike test using the actual Parallel SDK against these exact queries is still required** — this proxy test lowers the risk significantly but does not eliminate the need for it.

## 2. Gemini multimodal script-reading — not yet tested, here's the specific test plan

**Status: genuinely unverified.** No actual Gemini API call has been made against a real script PDF in this process. The following should be the literal Week 0-1 test plan, not a general intention:

**Test 1 — clean formatting baseline.** Feed Gemini the exact demo script excerpt from `11-demo-content.md` (a short, cleanly-formatted single scene) and confirm it extracts all four intended claims with no more, no fewer. This is the easy case and should work; if it doesn't, that's an urgent, high-priority problem.

**Test 2 — real-world formatting variance.** Industry-standard screenwriting software (Final Draft, Celtx, WriterDuet) produces PDFs with specific formatting conventions (scene numbers, dual-dialogue columns, revision marks in colored text/asterisks) that a hand-typed demo script won't have. Test against at least one real, professionally-formatted script PDF (many are publicly available for well-known films for educational reference) to catch formatting-related extraction failures before they show up during actual demo recording.

**Test 3 — token/length limits.** Confirm the actual context window and file-size behavior for the specific Gemini model string being used (see `07-env-vars.md` — the model string there is a placeholder pending confirmation against current docs). A multi-page script excerpt should comfortably fit, but this needs to be confirmed against the *current* model's actual limits, not assumed from general knowledge that may be stale.

**Test 4 — the ambiguous-input path.** Deliberately feed a vague, underspecified claim (e.g., "a popular song plays" with no title) and confirm the Intake Agent's `needs_clarification: true` behavior (see `09-agent-orchestration.md` §2) actually triggers, rather than the model confidently guessing a specific song. This is the test that validates the ambiguous-input handling requirement is real, not just documented.

**If any of these tests fail or behave unexpectedly**, the fix is almost certainly a prompt-engineering iteration on `backend/agents/intake/prompts.py`, not an architecture change — but this needs actual test cycles, which means it needs to happen early (Week 1), not discovered during Week 4 integration.

## 3. The Agent Builder / Gemini code asymmetry — addressed here

Until now, only the Parallel side of the required dual integration had illustrative code (see `09-agent-orchestration.md` §3). The hackathon's rule that integration must be "imported and called in code, not README-only" applies equally to Google Cloud — this section exists specifically to close that gap with an equivalent illustrative example.

**Illustrative shape for the Intake Agent's Gemini call** (confirm exact current SDK/method names against live Google Cloud Agent Builder documentation before implementation — this is illustrative of the pattern, not a copy-paste-ready snippet):

```python
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part

def extract_claims(document_bytes: bytes, mime_type: str) -> list[Claim]:
    """
    Intake Agent's core extraction call — this is the file a judge should
    be able to open to verify real, callable Google Cloud / Gemini usage,
    the same way parallel_client.py verifies the Parallel side.
    """
    model = GenerativeModel(settings.GEMINI_MODEL)

    document_part = Part.from_data(data=document_bytes, mime_type=mime_type)

    response = model.generate_content(
        [
            document_part,
            EXTRACTION_PROMPT,  # defined in prompts.py — instructs the model
                                  # to extract claims per the minimal,
                                  # non-identifying rule in 04-prd.md §5.6
        ],
        generation_config={
            "response_mime_type": "application/json",  # structured output —
                                                           # feeds the deterministic
                                                           # downstream contract,
                                                           # see 09-agent-orchestration.md §1
        },
    )

    return parse_claims(response.text)
```

**Where this should live in the real repo:** `backend/agents/intake/agent.py`, per `08-directory-structure.md`. Worth calling this file out explicitly in the README's "Required integrations" section alongside `parallel_client.py` (see `08-directory-structure.md` §3), so a judge checking Google Cloud usage has exactly as easy a time finding it as they do finding the Parallel integration.

**Agent Builder orchestration specifically** (as distinct from a raw Gemini SDK call) still needs its own concrete example once the team decides between native ADK patterns and LangGraph (see `09-agent-orchestration.md` §7) — that decision should happen early in Week 1, since it shapes how every agent's code is structured, not just the Intake Agent's.

## 4. Summary — what's genuinely de-risked vs. what still needs Week 0 testing

| Risk | Status after this pass |
|---|---|
| Parallel returns useful results for ownership-style queries | Substantially de-risked via proxy test; final confirmation still needs the real SDK, Week 0 |
| The engineered-conflict demo claim will actually produce a conflict | Strongly de-risked — this is a real, documented dispute pattern, not a hoped-for coincidence |
| Gemini reliably extracts claims from a real script PDF | Not yet tested at all — this is now the single highest-priority Week 0-1 item |
| Google Cloud / Gemini integration code exists and is judge-checkable | Addressed here with an illustrative pattern; still needs to be written as real, running code and placed in the README's required-integrations section |
