"""Long-writer agent.

Takes a report title, optional background context, and per-section drafts
(each already cited against its own source list) and produces a single
cohesive markdown report with:

* smooth transitions between sections
* one unified, deduplicated Sources list
* citation numbers rewritten to match the unified list
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..llm_config import ModelRef
from .base import Agent


@dataclass
class SectionDraft:
    title: str
    markdown: str  # section body — may contain its own [n] citations + Sources block


SYSTEM = (
    "You are an editor assembling a multi-section research report. You will "
    "receive a report title, optional background context, and a list of "
    "section drafts. Each draft has its own inline [n] citations and its own "
    "Sources block at the bottom.\n\n"
    "Produce ONE cohesive markdown report:\n"
    "  1. Start with `# <report_title>`.\n"
    "  2. If background context is provided, include it under a `## Background` heading.\n"
    "  3. For each section, write `## <section title>` followed by the section "
    "content, smoothing transitions and removing redundancy across sections.\n"
    "  4. Build a single unified `## Sources` list at the end. Deduplicate "
    "sources by URL. Renumber every inline [n] in the body so it points to "
    "the correct entry in the unified list.\n"
    "Do not introduce facts not present in the drafts. Output markdown only."
)


def init_long_writer(model: ModelRef) -> Agent[None]:
    return Agent(
        name="long_writer",
        system=SYSTEM,
        model=model,
        output_type=None,
        max_tokens=8192,
    )


async def write_long_report(
    report_title: str,
    background_context: str,
    sections: List[SectionDraft],
    *,
    model: ModelRef,
) -> str:
    agent = init_long_writer(model)
    parts = [f"REPORT TITLE: {report_title}"]
    if background_context:
        parts.append(f"BACKGROUND CONTEXT:\n{background_context}")
    for s in sections:
        parts.append(f"SECTION: {s.title}\n---\n{s.markdown}")
    user = "\n\n".join(parts)
    result = await agent.run(user)
    assert isinstance(result, str)
    return result
