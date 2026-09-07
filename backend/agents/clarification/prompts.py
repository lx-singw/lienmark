"""
Lienmark Targeted Clarification Prompts.
System instructions and formatting prompts for the Clarification Generator Agent.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import json
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agents.clarification.clarification_types import ClarificationInput


CLARIFICATION_SYSTEM_INSTRUCTION = """You are the Lienmark Senior Clearance Counsel and Rights Delivery Supervisor.
Your mission is to transform ambiguous intellectual property claims and missing contractual prerequisites
into targeted, legally non-generic clarification requests.

MANDATORY STRUCTURAL REQUIREMENTS:
For every ambiguous claim, you must identify and formulate:
1. Exact Scene Beat or Timecode Anchor: Cite the specific scene heading, page, or timecode (e.g. "Scene 14, 00:18:22").
2. Exact Asset Identity & Ambiguous Attribute: Name the precise asset and what makes it uncertain (e.g. "Uncredited jazz solo cue playing in the background diner").
3. Missing Legal Scope: Specify the exact statutory or contractual grant missing (e.g. "Master recording ownership and synchronization rights are unresolved").
4. Specific Suggested Options: Provide at least 2-3 mutually exclusive, actionable clearance pathways (e.g. ["Commissioned original score", "Commercial track needing sync clearance", "Library/production music (e.g. APM/Extreme)"]).
5. Specific Required Document Type: Identify the exact industry contract or release needed (e.g. "Executed Synchronization License" or "Composer Work-for-Hire Agreement").
6. Designated Production Role: Assign the accountable production department head (e.g. "Music Supervisor", "Clearance Counsel", "Line Producer", "Clearance Coordinator", "Archival Producer").

BENCHMARK SCENARIO REFERENCE:
Screenplay cue: "an uncredited jazz solo plays in the background of the diner scene"
Targeted Formulation:
- Scene Anchor: "Scene 14, 00:18:22" (or scene heading cited)
- Asset Identity: "Uncredited jazz solo cue playing in the background diner"
- Ambiguous Attribute: "Uncredited background score with unknown master recording and publishing source"
- Missing Legal Scope: "Master recording ownership and synchronization rights are unresolved"
- Suggested Options:
  1. "Commissioned original score (Composer Work-for-Hire)"
  2. "Commercial track needing sync clearance (Master Use + Sync License)"
  3. "Library/production music (e.g. APM/Extreme with pre-cleared sync)"
- Required Document: "Executed Synchronization License" or "Composer Work-for-Hire Agreement"
- Designated Role: "Music Supervisor"

NEVER emit generic questions such as "Please clarify this music" or "Do you have rights?".
Always return a valid JSON object matching the TargetedClarification schema.
"""


def build_clarification_prompt(input_data: ClarificationInput) -> str:
    """
    Constructs the targeted generation prompt for an ambiguous claim.
    """
    anchor = input_data.scene_anchor or "Unassigned Scene Beat"
    context = input_data.context_snippet or "No additional script context provided"
    reason = input_data.flagged_reason or "Unresolved rights status flagged during intake pass"
    missing = input_data.missing_legal_scope or "Underlying IP grant and chain-of-title unverified"
    existing = ", ".join(input_data.existing_licenses) if input_data.existing_licenses else "None"
    role_hint = f"\nPreferred Assigned Role: {input_data.designated_role}" if input_data.designated_role else ""

    return f"""Formulate a targeted, legally non-generic clarification request for the following clearance deficiency:

CLAIM DETAILS:
- Claim ID: {input_data.claim_id}
- Asset Name / Cue: {input_data.asset_name_or_cue}
- Category: {input_data.category or 'unspecified'}
- Scene / Timecode Anchor: {anchor}
- Context Snippet: {context}
- Flagged Reason: {reason}
- Missing Legal Scope: {missing}
- Existing Licenses on File: {existing}{role_hint}
- Revision ID: {input_data.revision_id}

OUTPUT REQUIREMENT:
Return ONLY a valid JSON object conforming strictly to the TargetedClarification schema.
The question_text MUST be formal, legally precise, and synthesize the anchor, asset identity, missing scope, suggested options, and required document type.
"""


def build_batch_clarification_prompt(inputs: List[ClarificationInput]) -> str:
    """
    Constructs a multi-claim generation prompt for batch clarification processing.
    """
    items_text = []
    for idx, inp in enumerate(inputs, start=1):
        items_text.append(
            f"Item {idx}:\n"
            f"  - Claim ID: {inp.claim_id}\n"
            f"  - Asset / Cue: {inp.asset_name_or_cue}\n"
            f"  - Scene Anchor: {inp.scene_anchor or 'Unassigned'}\n"
            f"  - Context: {inp.context_snippet or 'None'}\n"
            f"  - Flagged Reason: {inp.flagged_reason or 'Ambiguity flagged'}\n"
            f"  - Category: {inp.category or 'unspecified'}"
        )
    joined_items = "\n\n".join(items_text)

    return f"""Formulate targeted clarification requests for each of the following ambiguous claims:

{joined_items}

OUTPUT REQUIREMENT:
Return a valid JSON object with key 'clarifications' containing an array of TargetedClarification objects.
Ensure each item cites exact scene anchors, missing legal scope, suggested options, required document, and designated role.
"""


def build_schema_repair_prompt(original_output: str, error_details: str) -> str:
    """
    Builds a targeted correction prompt when model output fails schema validation.
    """
    return f"""Your previous clarification output failed schema validation or contained structural defects.

VALIDATION ERRORS:
{error_details}

ORIGINAL RAW OUTPUT:
{original_output}

REPAIR INSTRUCTIONS:
1. Output ONLY a valid JSON object conforming to the TargetedClarification schema.
2. Ensure 'suggested_options' has at least 2 distinct, non-empty options.
3. Ensure 'required_document_type', 'designated_role', and 'question_text' are non-empty strings.
4. Do NOT output conversational preamble or markdown commentary. Pure JSON only.
"""
