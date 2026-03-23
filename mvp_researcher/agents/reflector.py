"""Reflector agent: decide whether findings answer the question yet."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .. import llm


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


async def reflect_on_findings(query: str, findings_digest: str, *, model: str) -> Reflection:
    user = f"QUESTION: {query}\n\nFINDINGS SO FAR:\n{findings_digest}"
    text = await llm.complete(SYSTEM, user, model=model, max_tokens=512)
    return llm.parse_json(text, Reflection)
