"""Report planner agent.

Given a research query, produces:
  * a report title
  * an outline of independent sections (title + key question)
  * 1-2 paragraphs of shared background context

Each section is later researched independently by its own IterativeResearcher.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from ..llm_config import ModelRef
from .base import Agent


class ReportPlanSection(BaseModel):
    title: str = Field(description="Section title.")
    key_question: str = Field(description="The single question this section answers.")


class ReportPlan(BaseModel):
    report_title: str = Field(description="Title for the whole report.")
    background_context: str = Field(
        default="",
        description="Up to two paragraphs of context shared by all sections.",
    )
    report_outline: List[ReportPlanSection] = Field(min_length=1, max_length=8)


SYSTEM = (
    "You are a research manager. Today's date is "
    f"{datetime.now().strftime('%Y-%m-%d')}. Given a research query, return a "
    "JSON object with: a `report_title`, optional `background_context` (1-2 "
    "paragraphs of orientation that all sections share), and a `report_outline` "
    "array of 2-6 sections. Each section has a `title` and a `key_question` "
    "that is answerable independently of the other sections. Cover the query "
    "with minimal overlap between sections. Return JSON only."
)


def init_report_planner(model: ModelRef) -> Agent[ReportPlan]:
    return Agent(
        name="report_planner",
        system=SYSTEM,
        model=model,
        output_type=ReportPlan,
        max_tokens=1024,
    )


async def plan_report(query: str, *, model: ModelRef) -> ReportPlan:
    agent = init_report_planner(model)
    result = await agent.run(f"QUERY: {query}")
    assert isinstance(result, ReportPlan)
    return result
