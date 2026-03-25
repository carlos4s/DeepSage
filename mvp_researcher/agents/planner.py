"""Planner agent: turn a question into a small set of search queries."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from .base import Agent


class SearchPlan(BaseModel):
    queries: List[str] = Field(min_length=1, max_length=6)


SYSTEM = (
    "You are a research planner. Given a question, output a JSON object "
    "with a `queries` array of 3-5 specific web-search queries that, taken "
    "together, would let a researcher answer the question. Cover different "
    "angles; do not repeat phrasing. Return JSON only."
)


def init_planner(model: str) -> Agent[SearchPlan]:
    return Agent(name="planner", system=SYSTEM, model=model, output_type=SearchPlan, max_tokens=512)


async def plan_searches(query: str, *, model: str) -> SearchPlan:
    agent = init_planner(model)
    user = f"Today's date: {datetime.now().strftime('%Y-%m-%d')}\nQuestion: {query}"
    result = await agent.run(user)
    assert isinstance(result, SearchPlan)
    return result
