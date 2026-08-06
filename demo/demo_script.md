# Lienmark: 3-Minute Hackathon Demo Script
**Track:** Parallel | **Challenge:** Agentic Cinema
**Target Word Count:** ~400 words (Approx. 2 mins 45 seconds at standard speaking pace).
**Visual Style:** Screen recording of the UI, combined with split-screen terminal output to satisfy the "show the agent functioning" judging requirement. No cinematic trailers.

---

## Act I: The Problem & Architecture (0:00 - 0:30)

**[0:00 - 0:15] Visual:** Title slide briefly, then cross-fade to a split screen: Left side shows a standard folder `poller_watch_dir/`, Right side shows the dark-mode Lienmark React UI with empty Claims Table.

**Speaker (Voiceover):**
"Every film production carries hundreds of unresolved rights claims, costing the industry over 50 million dollars a year in manual legal clearance. We built Lienmark to fix this. It’s an autonomous, 6-agent verification ledger powered by Gemini and the Parallel Search API. It acts as title insurance for Hollywood."

**[0:15 - 0:30] Visual:** A mouse cursor drags `sample_script_adversarial.pdf` into the `poller_watch_dir/` on the left. The right side immediately fires a glowing toast notification: *“Discovery Agent: New Script Detected.”* 

**Speaker:**
"Unlike legacy tools, Lienmark is truly agentic. You don't have to click a button. Our proactive Discovery Agent detects a new script drop and triggers the pipeline. The Intake Agent extracts claims and uses SHA-256 deduplication to instantly bypass unchanged scenes, saving API costs."

## Act II: Agentic Execution & Conflict Arbitration (0:30 - 1:45)

**[0:30 - 1:15] Visual:** The UI populates with rows of claims. The camera zooms in on one row: *"Archival Audio: Apollo 11 Mission."* A terminal overlay shows the Parallel MCP Client making live API requests.

**Speaker:**
"Here is where Lienmark excels: Multi-step, live verification. For this Apollo 11 audio claim, our Research Agent dynamically calls the Parallel API to verify ownership. Parallel returns a conflict: NASA claims the footage is public domain, but a private entity claims rights to the synchronized audio master."

**[1:15 - 1:45] Visual:** The row turns yellow (Human Review Flag). The UI displays the Gemini Pro Risk Scoring Agent’s output, separating the conflicting sources and pre-populating a *Fair Use (17 U.S.C. § 107)* defense.

**Speaker:**
"Instead of hallucinating a guess, our Gemini Pro Risk Scoring agent deterministically arbitrates the conflict. It tags the discrepancy, pre-populates a Fair Use legal defense, and halts the pipeline for Human-in-the-Loop review."

## Act III: The Human & The Ledger (1:45 - 2:30)

**[1:45 - 2:15] Visual:** The user clicks the flagged row. The `AttorneyOverrideModal.tsx` opens. The user checks a box accepting the Fair Use defense, and clicks "Sign & Clear."

**Speaker:**
"The production attorney steps in, reviews the Parallel API evidence, and accepts the Fair Use defense. An RSA-256 digital signature is generated, and the Ledger Agent writes the final decision to an immutable Firestore database."

**[2:15 - 2:30] Visual:** The UI quickly shows a prompt injection trap. A toast reads: *“Security Alert: Suspicious Embedded Instruction Blocked.”* 

**Speaker:**
"And because we’re enterprise-grade, Lienmark automatically traps embedded prompt-injections hidden inside adversarial scripts, isolating the malicious commands before they hit the agent orchestrator."

## Act IV: The Close (2:30 - 3:00)

**[2:30 - 2:50] Visual:** The user clicks "Export E&O Binder." A clean PDF certificate downloads. The screen cuts to a terminal running `python scripts/verify_ledger_integrity.py`, returning a green *“SHA-256 Hash Chain Valid”* output.

**Speaker:**
"Finally, the Report Agent generates a pristine Form E&O-2026 title certificate for the insurance binder. Every decision is backed by a cryptographic hash chain, proving to insurers that the ledger hasn't been tampered with. This is Lienmark. The verification ledger entertainment can’t close without."

**[2:50 - 3:00] Visual:** Final slide. GitHub Repo link. "Vote for Lienmark on Devpost."
