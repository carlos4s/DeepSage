"""Knowledge gap agent.

Critically assesses the current research state and either declares the work
complete or returns an ordered list of specific gaps that still need to be
filled. Replaces the simpler Reflector when conversation history is available.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from ..llm_config import ModelRef
from .base import Agent


class KnowledgeGapOutput(BaseModel):
    research_complete: bool = Field(
        description="Whether the research is sufficient to answer the original query."
    )
    outstanding_gaps: List[str] = Field(
        default_factory=list,
        description="Up to 3 specific knowledge gaps in priority order.",
        max_length=3,
    )


SYSTEM = (
    "You are a Research State Evaluator. Today's date is "
    f"{datetime.now().strftime('%Y-%m-%d')}. Given the original query and a "
    "history of actions, findings, and thoughts, decide whether enough has "
    "been gathered to answer the query. If not, list up to 3 specific gaps in "
    "priority order. Each gap must be self-contained — another agent will act "
    "on it without seeing the rest of this context. Return JSON only matching: "
    '{"research_complete": bool, "outstanding_gaps": [str]}'
)


def init_knowledge_gap_agent(model: ModelRef) -> Agent[KnowledgeGapOutput]:
    return Agent(
        name="knowledge_gap",
        system=SYSTEM,
        model=model,
        output_type=KnowledgeGapOutput,
        max_tokens=512,
    )


async def evaluate_gaps(
    query: str,
    history: str,
    background_context: str = "",
    *,
    model: ModelRef,
) -> KnowledgeGapOutput:
    agent = init_knowledge_gap_agent(model)
    parts = [f"ORIGINAL QUERY:\n{query}"]
    if background_context:
        parts.append(f"BACKGROUND CONTEXT:\n{background_context}")
    parts.append(
        f"HISTORY OF ACTIONS, FINDINGS AND THOUGHTS:\n{history or 'None yet.'}"
    )
    result = await agent.run("\n\n".join(parts))
    assert isinstance(result, KnowledgeGapOutput)
    return result
