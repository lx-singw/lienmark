"""
Lienmark Automated Schema Repair Engine
Provides defensive parsing, heuristic repair, and controlled recovery for Gemini structured outputs.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import ast
import json
import logging
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("lienmark.schema_repair")


class JsonSchemaRepairError(ValueError):
    """Raised when raw LLM output cannot be repaired into valid JSON or matching schema."""
    pass


def repair_json_output(
    raw_text: str,
    target_model: Optional[Type[BaseModel]] = None,
) -> Dict[str, Any]:
    """
    Automated schema repair engine for Gemini LLM outputs.
    Applies multi-stage deterministic normalization:
    Stage 1: Direct JSON parse.
    Stage 2: Markdown fence stripping (```json ... ```, ``` ... ```).
    Stage 3: Substring extraction between outer `{` and `}` (handles conversational prose).
    Stage 4: Python literal conversion (True/False/None -> true/false/null).
    Stage 5: Trailing comma elimination before closing delimiters.
    Stage 6: Python AST literal evaluation for single-quoted dict strings.
    Stage 7: Truncated delimiter recovery (auto-closing open quotes, brackets, and braces).
    Stage 8: Optional Pydantic schema validation.
    """
    if not raw_text or not raw_text.strip():
        raise JsonSchemaRepairError("Cannot repair empty or whitespace-only LLM output.")

    text = raw_text.strip()

    # Stage 1: Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return _validate_against_model(data, target_model)
    except json.JSONDecodeError:
        pass

    # Stage 2: Strip markdown code blocks
    cleaned = _strip_markdown_fences(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return _validate_against_model(data, target_model)
    except json.JSONDecodeError:
        pass

    # Stage 3: Extract outermost JSON object { ... }
    json_candidate = _extract_outer_braces(cleaned)
    if json_candidate:
        try:
            data = json.loads(json_candidate)
            if isinstance(data, dict):
                return _validate_against_model(data, target_model)
        except json.JSONDecodeError:
            pass
    else:
        json_candidate = cleaned

    # Stage 4: Normalize Python literals (True, False, None)
    normalized = _normalize_python_literals(json_candidate)
    try:
        data = json.loads(normalized)
        if isinstance(data, dict):
            return _validate_against_model(data, target_model)
    except json.JSONDecodeError:
        pass

    # Stage 5: Remove trailing commas before } or ]
    no_trailing = _remove_trailing_commas(normalized)
    try:
        data = json.loads(no_trailing)
        if isinstance(data, dict):
            return _validate_against_model(data, target_model)
    except json.JSONDecodeError:
        pass

    # Stage 6: AST safe evaluation (handles Python repr / single-quoted dicts)
    try:
        evaluated = ast.literal_eval(no_trailing)
        if isinstance(evaluated, dict):
            return _validate_against_model(evaluated, target_model)
    except (ValueError, SyntaxError, MemoryError):
        pass

    # Stage 7: Auto-close truncated braces and quotes
    repaired_truncated = _repair_truncated_json(no_trailing)
    try:
        data = json.loads(repaired_truncated)
        if isinstance(data, dict):
            return _validate_against_model(data, target_model)
    except json.JSONDecodeError:
        pass

    # Final attempt: regex key-value extraction for essential fields
    fallback_dict = _regex_key_value_fallback(no_trailing)
    if fallback_dict:
        try:
            return _validate_against_model(fallback_dict, target_model)
        except Exception as e:
            raise JsonSchemaRepairError(
                f"Schema repair engine failed after all stages: {e}. Raw input: {raw_text[:200]}"
            ) from e

    raise JsonSchemaRepairError(
        f"Unable to parse or repair LLM output into JSON object. Raw input: {raw_text[:200]}"
    )


def _strip_markdown_fences(text: str) -> str:
    """Removes leading and trailing markdown code block fences."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _extract_outer_braces(text: str) -> Optional[str]:
    """Finds the first '{' and the last '}' in the text and slices it."""
    first_idx = text.find("{")
    last_idx = text.rfind("}")
    if first_idx != -1 and last_idx != -1 and last_idx > first_idx:
        return text[first_idx : last_idx + 1].strip()
    return None


def _normalize_python_literals(text: str) -> str:
    """Replaces unquoted Python literals True, False, None with valid JSON."""
    result = re.sub(r":\s*True\b", ": true", text)
    result = re.sub(r":\s*False\b", ": false", result)
    result = re.sub(r":\s*None\b", ": null", result)
    return result


def _remove_trailing_commas(text: str) -> str:
    """Removes trailing commas immediately preceding closing braces or brackets."""
    return re.sub(r",\s*([\]}])", r"\1", text)


def _repair_truncated_json(text: str) -> str:
    """Closes unterminated strings, brackets, and braces if LLM response was truncated."""
    s = text.strip()
    in_quote = False
    escape = False
    stack = []
    for char in s:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if not in_quote:
            if char in ("{", "["):
                stack.append(char)
            elif char == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
            elif char == "]":
                if stack and stack[-1] == "[":
                    stack.pop()

    if in_quote:
        s += '"'

    s = s.rstrip().rstrip(",")

    while stack:
        opener = stack.pop()
        if opener == "{":
            s += "}"
        elif opener == "[":
            s += "]"

    return s


def _regex_key_value_fallback(text: str) -> Dict[str, Any]:
    """Last-resort regex extractor for key-value pairs matching JSON-like lines."""
    result: Dict[str, Any] = {}
    pattern = re.compile(r'["\']?([a-zA-Z0-9_]+)["\']?\s*:\s*(?:["\']([^"\']*)["\']|([a-zA-Z0-9_.-]+))')
    for match in pattern.finditer(text):
        key = match.group(1)
        str_val = match.group(2)
        raw_val = match.group(3)
        if str_val is not None:
            result[key] = str_val
        elif raw_val is not None:
            if raw_val.lower() == "true":
                result[key] = True
            elif raw_val.lower() == "false":
                result[key] = False
            elif raw_val.lower() in ("null", "none"):
                result[key] = None
            else:
                try:
                    if "." in raw_val:
                        result[key] = float(raw_val)
                    else:
                        result[key] = int(raw_val)
                except ValueError:
                    result[key] = raw_val
    return result


def _validate_against_model(
    data: Dict[str, Any],
    target_model: Optional[Type[BaseModel]] = None,
) -> Dict[str, Any]:
    """Validates data against target Pydantic model if provided, returning dict."""
    if target_model is not None:
        validated = target_model.model_validate(data)
        return validated.model_dump()
    return data
