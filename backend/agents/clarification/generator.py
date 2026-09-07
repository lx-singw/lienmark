"""
Lienmark Targeted Clarification Generator.
Synthesizes legally non-generic clearance questions for production department heads.
Dual-mode engine: Live Google GenAI ADK with defensive schema repair and offline CI rule-based fallback.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional, Union

from backend.agents.clarification.clarification_types import (
    ClarificationInput,
    ClarificationOutput,
    TargetedClarification,
)
from backend.agents.clarification.heuristics import (
    generate_rule_based_clarification,
)
from backend.agents.clarification.prompts import (
    CLARIFICATION_SYSTEM_INSTRUCTION,
    build_clarification_prompt,
    build_schema_repair_prompt,
)
from backend.core.schema_repair import repair_json_output

logger = logging.getLogger("lienmark.clarification.generator")


class ClarificationGenerator:
    """Clarification Generator Agent producing targeted questions citing exact anchors and options."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        use_fallback: bool = False,
        max_repair_retries: int = 2,
    ):
        self.model_name = model_name
        self.max_repair_retries = max(0, min(max_repair_retries, 5))
        raw_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        has_valid_key = bool(
            raw_key and not any(raw_key.lower().startswith(p) for p in ("mock", "sandbox", "test"))
        )
        self.is_offline = use_fallback or not has_valid_key
        self.client = None
        if not self.is_offline:
            try:
                from google import genai
                self.client = genai.Client(api_key=raw_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google.genai.Client: {e}. Fallback to offline.")
                self.is_offline = True

    async def generate_clarification(
        self, input_data: Union[ClarificationInput, Dict[str, Any]]
    ) -> TargetedClarification:
        """Main async entry point: generates a targeted legal clarification."""
        inp = input_data if isinstance(input_data, ClarificationInput) else ClarificationInput(**input_data)
        if self.is_offline or self.client is None:
            return generate_rule_based_clarification(inp)
        return await self._generate_via_genai(inp)

    def generate_clarification_sync(
        self, input_data: Union[ClarificationInput, Dict[str, Any]]
    ) -> TargetedClarification:
        """Synchronous wrapper for offline CI and deterministic execution."""
        inp = input_data if isinstance(input_data, ClarificationInput) else ClarificationInput(**input_data)
        return generate_rule_based_clarification(inp)

    async def generate_batch(
        self, inputs: List[Union[ClarificationInput, Dict[str, Any]]]
    ) -> ClarificationOutput:
        """Generates clarifications for multiple ambiguous claims asynchronously."""
        results = [await self.generate_clarification(item) for item in inputs]
        mode = "rule_based_fallback" if self.is_offline else "genai_live"
        return ClarificationOutput(clarifications=results, generation_mode=mode, total_count=len(results))

    def generate_batch_sync(
        self, inputs: List[Union[ClarificationInput, Dict[str, Any]]]
    ) -> ClarificationOutput:
        """Generates clarifications for multiple claims synchronously using deterministic rules."""
        results = [self.generate_clarification_sync(item) for item in inputs]
        return ClarificationOutput(
            clarifications=results, generation_mode="rule_based_fallback", total_count=len(results)
        )

    async def _execute_generation_attempt(self, prompt: str, config: Any) -> str:
        """Invokes google.genai model asynchronously."""
        response = await self.client.aio.models.generate_content(
            model=self.model_name, contents=prompt, config=config
        )
        return response.text or ""

    def _parse_and_validate_attempt(
        self, raw_text: str, inp: ClarificationInput
    ) -> TargetedClarification:
        """Parses and repairs raw LLM JSON output into a validated TargetedClarification."""
        repaired = repair_json_output(raw_text, target_model=TargetedClarification)
        repaired.setdefault("claim_id", inp.claim_id)
        repaired.setdefault("stable_lineage_key", inp.stable_lineage_key or inp.claim_id)
        repaired.setdefault("revision_id", inp.revision_id)
        return TargetedClarification.model_validate(repaired)

    async def _generate_via_genai(self, inp: ClarificationInput) -> TargetedClarification:
        """Executes live structured generation via Google GenAI with repair retries."""
        from google.genai import types

        base_prompt = build_clarification_prompt(inp)
        config = types.GenerateContentConfig(
            system_instruction=CLARIFICATION_SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=TargetedClarification,
        )
        last_error, raw_text = "", ""
        for attempt in range(self.max_repair_retries + 1):
            try:
                cur_prompt = base_prompt if attempt == 0 else build_schema_repair_prompt(raw_text, last_error)
                raw_text = await self._execute_generation_attempt(cur_prompt, config)
                return self._parse_and_validate_attempt(raw_text, inp)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Clarification schema validation error on attempt {attempt}: {e}")

        logger.error("Clarification schema repair exhausted; using rule-based generator.")
        return generate_rule_based_clarification(inp)
