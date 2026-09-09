"""Google ADK execution for the canonical worker's bounded model and tool calls.

Durable recovery belongs to the worker ledger. ADK sessions are per invocation:
replaying a completed worker call never creates a second model invocation.
"""
import asyncio
import json
import uuid
from typing import Any

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.run_config import RunConfig
from google.adk.events import Event
from google.adk.models import BaseLlm, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from pydantic import PrivateAttr


class GuardedGemini(BaseLlm):
    """ADK model adapter retaining our single-attempt, observable HTTP boundary."""
    _invoke: Any = PrivateAttr()
    _schema: dict = PrivateAttr()
    _receipt: dict = PrivateAttr(default_factory=dict)

    def __init__(self, invoke, response_schema):
        super().__init__(model="gemini-2.5-flash")
        self._invoke, self._schema = invoke, response_schema

    async def generate_content_async(self, llm_request, stream=False):
        instruction = llm_request.config.system_instruction
        if isinstance(instruction, str):
            instruction = {"parts": [{"text": instruction}]}
        elif instruction:
            instruction = instruction.model_dump(exclude_none=True)
        payload = {"systemInstruction": instruction,
            "contents": [c.model_dump(exclude_none=True) for c in llm_request.contents],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 4096,
                "thinkingConfig": {"thinkingBudget": 0}, "responseMimeType": "application/json",
                "responseSchema": self._schema}}
        response, trace = await asyncio.to_thread(self._invoke, payload)
        self._receipt.update(response=response, trace=trace)
        # Preserve strict finish/schema validation in Providers.generate.
        candidate = (response.get("candidates") or [{}])[0]
        content = candidate.get("content", {})
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=p["text"])
            for p in content.get("parts", []) if "text" in p and not p.get("thought")]),
            usage_metadata=types.GenerateContentResponseUsageMetadata.model_validate(response['usageMetadata']) if response.get('usageMetadata') else None,
            partial=False, turn_complete=True)


class SearchAgent(BaseAgent):
    _invoke: Any = PrivateAttr()
    _result: dict = PrivateAttr(default_factory=dict)

    def __init__(self, invoke):
        super().__init__(name="parallel_research", description="Retrieve attributable public evidence using Parallel Search.")
        self._invoke = invoke

    async def _run_async_impl(self, ctx):
        query = ctx.user_content.parts[0].text
        async def parallel_search(query: str) -> dict:
            """Search public sources for this scoped research question."""
            return await asyncio.to_thread(self._invoke, query)
        tool = FunctionTool(func=parallel_search)
        call_id = "search_" + uuid.uuid4().hex
        yield Event(author=self.name, invocation_id=ctx.invocation_id, content=types.Content(role="model", parts=[types.Part(
            function_call=types.FunctionCall(id=call_id, name=tool.name, args={"query": query}))]))
        result = await tool.run_async(args={"query": query}, tool_context=ToolContext(ctx, function_call_id=call_id))
        self._result.update(result)
        yield Event(author=self.name, invocation_id=ctx.invocation_id, content=types.Content(role="user", parts=[types.Part(
            function_response=types.FunctionResponse(id=call_id, name=tool.name,
                response={"sources": len(result["evidence"]), "request_id": result["trace"]["request_id"]}))]))


async def _run(agent, text):
    sessions = InMemorySessionService()
    session = await sessions.create_session(app_name="clearance", user_id="bounded_worker")
    runner = Runner(app_name="clearance", agent=agent, session_service=sessions)
    events = []
    try:
        async for event in runner.run_async(user_id=session.user_id, session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
                run_config=RunConfig(max_llm_calls=1)):
            events.append({"event_id": event.id, "invocation_id": event.invocation_id,
                "author": event.author, "timestamp": event.timestamp,
                "tool_calls": [c.name for c in event.get_function_calls()],
                "tool_responses": [r.name for r in event.get_function_responses()]})
    finally:
        await runner.close()
    return {"framework": "Google ADK", "agent": agent.name, "session_id": session.id, "events": events}


def generate(instruction, data, response_schema, role, invoke):
    model = GuardedGemini(invoke, response_schema)
    # Callable instructions avoid interpreting braces in documents as state templates.
    agent = LlmAgent(name=role, model=model, instruction=lambda ctx: instruction,
        disallow_transfer_to_parent=True, disallow_transfer_to_peers=True)
    trace = asyncio.run(_run(agent, json.dumps(data)))
    return model._receipt["response"], {**model._receipt["trace"], "orchestration": trace}


def search(query, invoke):
    agent = SearchAgent(invoke)
    trace = asyncio.run(_run(agent, query))
    result = agent._result
    result["trace"]["orchestration"] = trace
    return result
