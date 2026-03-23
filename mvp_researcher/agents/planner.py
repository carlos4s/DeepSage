"""Planner agent: turn a question into a small set of search queries."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from .. import llm


class SearchPlan(BaseModel):
    queries: List[str] = Field(min_length=1, max_length=6)


SYSTEM = (
    "You are a research planner. Given a question, output a JSON object "
    "with a `queries` array of 3-5 specific web-search queries that, taken "
    "together, would let a researcher answer the question. Cover different "
    "angles; do not repeat phrasing. Return JSON only."
)


async def plan_searches(query: str, *, model: str) -> SearchPlan:
    user = f"Today's date: {datetime.now().strftime('%Y-%m-%d')}\nQuestion: {query}"
    text = await llm.complete(SYSTEM, user, model=model, max_tokens=512)
    return llm.parse_json(text, SearchPlan)
