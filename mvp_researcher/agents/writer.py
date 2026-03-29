"""Writer agent: assemble a cited markdown report from numbered findings."""
from __future__ import annotations

from ..llm_config import ModelRef
from .base import Agent


SYSTEM = (
    "You are a research writer. Produce a thorough, well-structured "
    "markdown report that answers the user's question using ONLY the "
    "numbered findings provided. Cite claims inline as [n] referencing "
    "the source numbers. End the report with a `## Sources` section "
    "listing each cited source as `[n] Title — URL`. Be specific, "
    "neutral, and concise; omit anything the sources do not support."
)


def init_writer(model: ModelRef) -> Agent[None]:
    return Agent(name="writer", system=SYSTEM, model=model, output_type=None, max_tokens=4096)


async def write_report(query: str, sources_digest: str, *, model: ModelRef) -> str:
    agent = init_writer(model)
    user = f"QUESTION: {query}\n\nNUMBERED SOURCES:\n{sources_digest}"
    result = await agent.run(user)
    assert isinstance(result, str)
    return result
