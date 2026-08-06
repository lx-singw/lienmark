# Company Formation & IP Readiness

This document exists because the original framing of this entire effort — stated at the very beginning of this planning process — was to use the hackathon as a genuine pre-seed step toward a real company, not merely to win a competition and stop. Everything below is about making sure the *legal and ownership foundation* is as solid as the technical and product planning already is, so that a strong hackathon placement can actually convert into fundable momentum rather than being undermined by avoidable structural problems discovered later.

## 1. The single most urgent item: IP assignment, before real building starts in earnest

**The problem, stated plainly:** if multiple people write code for this hackathon project without a signed agreement establishing that the resulting IP belongs to the company (not to each individual contributor personally), the company's ownership of its own core product is ambiguous from day one. This is one of the most common and most avoidable problems that surfaces during real due diligence — an investor's lawyer will ask for exactly this documentation, and "we didn't get around to it" is a genuinely bad answer to have to give after the fact.

**What to actually do, concretely, before Week 1 of building (per `10-build-timeline.md`):**
- Every team member contributing code, design, or product work should sign a simple IP assignment agreement, even a short one, stating that work product created for this project is owned by the company (or, pre-incorporation, assigned to the founding group collectively with a clear conversion mechanism once incorporated)
- This does not need to be expensive or complicated at this stage — a standard, short-form founder IP assignment template (many exist publicly, and this is a case where using a well-established template is more sensible than drafting from scratch) is sufficient for a pre-seed-stage project
- **Do this before, not after, the hackathon submission** — the code being submitted publicly under an MIT license (per `01-hackathon-scope.md` §6) doesn't remove the need for clean internal ownership; the public license governs what others can do with the code, not who owns the underlying company asset

## 2. Entity formation — timing and structure

- **Recommended structure, if and when incorporation happens: Delaware C-corporation.** This is the standard structure for any startup planning to raise from U.S. venture investors, including angel/pre-seed — it's what investors expect to see, and converting from a different structure later (an LLC, for instance) adds real cost and complexity that's avoidable by starting correctly.
- **Timing:** incorporation does not need to happen before the hackathon submission — the Devpost form's "Company Name" field accepts a working name or "N/A" without issue (as already noted when filling out the credits request form). But incorporation **should** happen before any real money changes hands — before accepting pilot customer payments, before taking angel investment, and ideally before extensive unpaid work continues much further, since unclear ownership becomes harder to untangle the longer multiple people have contributed without a formal structure in place.
- **Cap table discipline from day one:** once incorporated, equity splits among founders/early contributors should be documented formally (even a simple founder agreement) rather than left as an informal understanding — "we'll figure out the percentages later" is a common source of founder disputes that's entirely avoidable by deciding early, even if the initial split is later renegotiated as roles clarify.

## 3. Trademark and domain — status and next steps

Per the naming research already done in this process: **Lienmark** was checked and came back clear via general web search visibility (no registered trademark, live company, or software product found under this exact name), with **Provenus** confirmed clear as a backup. This was explicitly flagged at the time as *not* a formal legal clearance — worth restating and acting on now, given the stakes of building real brand equity on the name:

- **Before any serious marketing or fundraising activity under the Lienmark name**, run an actual USPTO TESS trademark search (or engage a trademark attorney for a formal clearance search) — this catches pending applications and nuances a general web search cannot
- **Register the domain(s)** — lienmark.com/.ai/.io — now, while the name is confirmed available, rather than risking it being taken by the time formal trademark clearance is complete. Domain squatting on a name that's gaining visibility (via a public hackathon submission) is a real, if modest, risk once the name is publicly associated with a visible project.

## 4. What NOT to worry about yet

In the spirit of not over-building structure ahead of actual need: no need yet for a formal cap table management tool (Carta, etc.), no need for a lawyer on retainer, no need for D&O insurance, no need for a formal board structure. These all become relevant once there's real funding or real revenue — building them prematurely is its own form of wasted effort. The two items in §1 and the domain registration in §3 are the genuinely time-sensitive ones; everything else can wait until there's a concrete triggering event (an investment offer, a paying customer, a co-founder dispute risk).

## 5. A practical near-term checklist, ordered by urgency

1. **This week:** every current contributor signs a short-form IP assignment agreement
2. **This week:** register the Lienmark domain(s), even just to hold them
3. **Before any pilot customer or investor conversation:** run a formal USPTO trademark search on "Lienmark"
4. **Before accepting any money (customer or investor):** incorporate as a Delaware C-corp, with a documented founder equity split
5. **Ongoing:** keep a simple, written record of who contributed what and when — not for legal necessity alone, but because this kind of informal history becomes genuinely hard to reconstruct accurately months later if a formal cap table or IP dispute question ever arises
