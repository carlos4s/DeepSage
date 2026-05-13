"""Tool selector agent.

Given a knowledge gap, decides which tool(s) to invoke and with what input.
The MVP supports two tools:

* `search` — input is a web-search query string
* `crawl`  — input is a URL to fetch and read

The selector emits an `AgentSelectionPlan` containing 1-3 `ToolCall` items.
The orchestrator then dispatches each call concurrently.
"""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from ..llm_config import ModelRef
from .base import Agent

ToolName = Literal["search", "crawl"]


class ToolCall(BaseModel):
    tool: ToolName = Field(description="Which tool to invoke.")
    input: str = Field(description="Search query or URL, depending on tool.")
    rationale: str = Field(default="", description="One short sentence of justification.")


class AgentSelectionPlan(BaseModel):
    tasks: List[ToolCall] = Field(min_length=1, max_length=3)


SYSTEM = (
    "You are a tool dispatcher. Given a knowledge gap and any prior research "
    "context, choose 1-3 tool calls that will best fill the gap. Available "
    "tools:\n"
    "  - search: general web search; input is a 3-7 word query.\n"
    "  - crawl: fetch and read a specific URL; input is the URL.\n"
    "Prefer search when the answer is broad or sources are unknown; prefer "
    "crawl when prior findings already point to a specific authoritative "
    "page (an official spec, a company site, a primary source). Return JSON "
    "only matching: "
    '{"tasks": [{"tool": "search"|"crawl", "input": str, "rationale": str}]}'
)


def init_tool_selector(model: ModelRef) -> Agent[AgentSelectionPlan]:
    return Agent(
        name="tool_selector",
        system=SYSTEM,
        model=model,
        output_type=AgentSelectionPlan,
        max_tokens=512,
    )


async def select_tools(
    gap: str,
    history: str = "",
    *,
    model: ModelRef,
) -> AgentSelectionPlan:
    agent = init_tool_selector(model)
    parts = [f"KNOWLEDGE GAP:\n{gap}"]
    if history:
        parts.append(f"RESEARCH HISTORY SO FAR:\n{history}")
    result = await agent.run("\n\n".join(parts))
    assert isinstance(result, AgentSelectionPlan)
    return result
