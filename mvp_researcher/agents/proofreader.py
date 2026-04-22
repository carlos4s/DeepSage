"""Proofreader agent.

Final-pass editor over an assembled markdown report. Tightens prose, fixes
markdown formatting, removes redundancy across sections, and ensures the
Sources block is well-formed — without introducing facts not in the input.
"""
from __future__ import annotations

from ..llm_config import ModelRef
from .base import Agent


SYSTEM = (
    "You are a meticulous proofreader. You will receive a draft markdown "
    "research report. Return a polished version with the same factual "
    "content. Rules:\n"
    "  * Do not add, remove, or alter facts, numbers, or citations.\n"
    "  * Fix grammar, tighten prose, and improve flow.\n"
    "  * Normalize markdown headings (single `#` for the title, `##` for "
    "sections) and ensure consistent list/code formatting.\n"
    "  * If the same citation [n] appears under multiple URLs, keep the "
    "structure as-is — never invent a renumbering you can't verify.\n"
    "  * Make sure the report ends with a `## Sources` section listing each "
    "cited source on its own line as `[n] Title — URL`.\n"
    "Output the polished markdown only — no commentary."
)


def init_proofreader(model: ModelRef) -> Agent[None]:
    return Agent(
        name="proofreader",
        system=SYSTEM,
        model=model,
        output_type=None,
        max_tokens=8192,
    )


async def proofread(markdown: str, *, model: ModelRef) -> str:
    agent = init_proofreader(model)
    result = await agent.run(f"DRAFT REPORT:\n\n{markdown}")
    assert isinstance(result, str)
    return result
