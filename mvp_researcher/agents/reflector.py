"""Reflector agent: decide whether findings answer the question yet."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from ..llm_config import ModelRef
from .base import Agent


class Reflection(BaseModel):
    enough: bool = Field(description="True if findings already answer the question.")
    missing: str = Field(default="", description="What's still missing, if anything.")
    next_queries: List[str] = Field(default_factory=list, max_length=4)


SYSTEM = (
    "You are a research critic. Given the original question and the "
    "findings collected so far, decide whether they already answer the "
    "question. If yes, set `enough` to true. If not, list up to 3 "
    "concrete follow-up search queries in `next_queries` and describe "
    "what is `missing`. Return JSON only matching: "
    '{"enough": bool, "missing": str, "next_queries": [str]}'
)


def init_reflector(model: ModelRef) -> Agent[Reflection]:
    return Agent(name="reflector", system=SYSTEM, model=model, output_type=Reflection, max_tokens=512)


async def reflect_on_findings(query: str, findings_digest: str, *, model: ModelRef) -> Reflection:
    agent = init_reflector(model)
    user = f"QUESTION: {query}\n\nFINDINGS SO FAR:\n{findings_digest}"
    result = await agent.run(user)
    assert isinstance(result, Reflection)
    return result
