"""Inspect just the report plan without running the section-research loops.

Useful when you want to iterate on the planner prompt, or to preview the
outline a deep run would produce before committing to the LLM/search cost.
"""
import asyncio

from mvp_researcher.agents import plan_report
from mvp_researcher.llm_config import default_config


async def main() -> None:
    cfg = default_config()
    plan = await plan_report(
        "Compare lithium-iron-phosphate and sodium-ion grid storage chemistries.",
        model=cfg.planner,
    )

    print(f"Title: {plan.report_title}\n")
    if plan.background_context:
        print(f"Background:\n{plan.background_context}\n")
    print("Sections:")
    for i, section in enumerate(plan.report_outline, 1):
        print(f"  {i}. {section.title}")
        print(f"     Q: {section.key_question}")


if __name__ == "__main__":
    asyncio.run(main())
