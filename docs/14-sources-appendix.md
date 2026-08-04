# Sources & Citations Appendix

Every specific factual claim repeated across this documentation package is listed here with its actual source, so a judge or teammate can independently verify it rather than taking the docs' word for it. **Two corrections came out of compiling this list** — flagged clearly below, because a source appendix that quietly hides its own corrections defeats the purpose of having one.

## Correction 1: the "$150–500/hour" entertainment counsel figure is understated

This figure was used throughout the PRD, Pitch Deck, and Hackathon Scope docs. On checking it against real sources, actual rates skew higher:

| Source | Rate cited |
|---|---|
| Wrapbook (industry blog) | "No less than $250 per hour... at the low end" |
| SetHero | "Can charge upwards of $250/hr" |
| Lemoine Law Firm | "$350 per hour to $600 or more per hour" |
| Nolo (legal reference site) | "$300 and $700 an hour" |
| Pitt Entertainment Law | "$200 - $1,000 dollars per hour" |
| LawLinq | "Top-tier LA entertainment attorneys: approximately $800-$1,200+ per hour" |

**Recommended corrected figure for all docs: "$250–700/hour," with "$800-1,200+/hour for top-tier LA/NY counsel" as an optional upper-bound callout.** This is a stronger number for the pitch, not a weaker one — the true cost problem is bigger than what the docs previously claimed. Every doc using the old "$150-500" figure should be updated to reflect this.

**Sources:**
- https://www.wrapbook.com/blog/entertainment-lawyer-most-asked-questions
- https://sethero.com/blog/what-does-an-entertainment-lawyer-do-and-how-to-find-one/
- http://lemoinefirm.com/how-much-does-an-entertainment-lawyer-cost/
- https://www.nolo.com/legal-encyclopedia/hiring-entertainment-lawyer.html
- https://www.pittentertainmentlaw.com/how-representatives-are-paid
- https://www.lawlinq.com/how-much-does-it-cost-to-hire-an-entertainment-lawyer-california/

## Correction 2: the "cease-and-desist trend" claim was vague — here is the specific, citable case behind it

Docs previously referenced "studios moving from complaints to cease-and-desist actions" without naming the actual case. There is a specific, well-documented, ongoing dispute this refers to, and citing it by name is both more credible and more current than the vague version:

**The Seedance dispute (ByteDance vs. Hollywood, Feb–July 2026):**
- ByteDance launched an AI video model, Seedance 2.0, in China on February 11-12, 2026. Within 24 hours, an AI-generated fight scene depicting Tom Cruise and Brad Pitt (made from a two-line text prompt) went viral with millions of views.
- Disney sent a cease-and-desist letter to ByteDance on February 13, 2026 — Axios reported this was obtained directly, alleging Seedance was "pre-packaged... with a pirated library of copyrighted characters" including Spider-Man and Darth Vader.
- Paramount followed with its own cease-and-desist letter shortly after.
- On February 20-22, 2026, the Motion Picture Association sent its own letter — described in reporting as **the first cease-and-desist the MPA has ever sent to a generative AI company** — characterizing the infringement as "a feature, not a bug." Warner Bros., Sony, and Netflix also sent letters.
- **SAG-AFTRA**, representing roughly 160,000 performers, condemned the tool as showing disregard for "law, ethics, industry standards and basic principles of consent" — this is the specific, citable source for the "SAG-AFTRA tightening consent" claim used elsewhere in the docs.
- ByteDance paused the global rollout in March 2026 and added C2PA watermarking and content filters blocking recognizable faces/characters — but as of a July 16, 2026 report, **every major studio's cease-and-desist letter remains unanswered and unresolved in court**, even as ByteDance launched the more capable Seedance 2.5.
- One report noted an irony worth being aware of if this comes up in Q&A: studios are reportedly tolerating employee use of Seedance internally on a "don't ask, don't tell" basis even while publicly opposing it — worth knowing this nuance exists, though it doesn't undermine the core claim.

**Recommended framing for the docs: name this dispute specifically** ("the ongoing Disney/Paramount/MPA cease-and-desist dispute with ByteDance over Seedance") rather than the vague original phrasing — it's more credible to a judge who might independently check it, and it's more current (this is an actively unresolved situation as of the most recent reporting, not a settled historical event).

**Sources:**
- https://www.axios.com/2026/02/13/disney-bytedance-seedance
- https://mlq.ai/news/mpa-sends-first-ever-ai-cease-and-desist-to-bytedance-over-seedance-deepfakes/
- https://copyrightlately.com/meet-seedance-2-0-hollywoods-newest-ai-copyright-headache/
- https://www.techtimes.com/articles/320683/20260716/seedance-25-api-live-bytedances-30-second-ai-video-carries-unresolved-copyright-risk.htm
- https://www.techtimes.com/articles/319639/20260703/bytedance-seedance-25-launches-this-week-30-second-ai-video-carries-copyright-cloud.htm
- https://pexo.ai/blog/seedance-2-0-ai-video-copyright-risk-1007

## Verified, not corrected: the demo claim source material

**Clair de Lune public domain status:**
- https://commons.wikimedia.org/wiki/File:Clair_de_Lune_by_Claude_Debussy_(1905,_piano_solo).opus
- https://www.trademarkia.com/news/copyrights/is-classical-music-copyrighted
- https://www.easysong.com/search/songs/song-copyright-holder-information.aspx?s=24801 (listed as "PD" in a commercial rights database)

**Apollo 11 footage — the NASA/public-domain side:**
- https://archive.org/details/Apollo11MoonLanding — explicitly cites 17 U.S.C. § 105 (U.S. government works are not eligible for copyright)
- https://www.nasa.gov/history/afj/ap11fj/videoindex.html — "No copyright is asserted for NASA video"

**Apollo 11 footage — the network-broadcast/documented-conflict side:**
- https://www.openculture.com/2018/07/watch-original-tv-coverage-historic-apollo-11-moon-landing-recorded-july-20-1969.html — documents the CBS broadcast with Walter Cronkite as a distinct production layer over the raw NASA feed
- https://boingboing.net/2022/07/21/copyright-trolls-claim-public-domain-footage-of-apollo-moon-landing-on-youtube.html/amp — a documented, real case of a film archivist's public-domain NASA footage uploads being hit with false ownership claims via YouTube's ContentID system, illustrating exactly the kind of ownership confusion this claim type is meant to demonstrate

## Not yet independently re-verified in this pass — flagged honestly

The following claims were used earlier in this conversation's research but were not re-confirmed with fresh, saved URLs in this appendix-building pass (the original search results were not retained). They should be treated as **plausible but not yet re-verified** until someone runs a fresh check:

- The specific competitive-landscape claims about Filmustage, Vitrina, MUSO, Corsearch, Friend MTS, AiPlex, CAMB.AI, TRAILR.ai, and other named competitors in `03-post-mvp-scope.md` §2
- The specific "38% of productions use a formal vendor scoring framework" statistic used in the DriftLock/Overrun second-product-line reasoning

**Recommended action:** re-run a verification pass on these specific claims before they're used in any external-facing pitch material (as opposed to internal planning docs), using the same standard applied in this document — a real, checkable URL for every specific number or named-competitor claim.

## How to keep this appendix honest going forward

Any new specific factual claim added to any other document in this package (a statistic, a named competitor, a dated event) should get a corresponding entry here with a real URL, added in the same pass — not deferred to "we'll source it later," which is exactly how the two corrections above ended up needing to be made after the fact.
