"""Writer agent: assemble a cited markdown report from numbered findings."""
from __future__ import annotations

from .. import llm


SYSTEM = (
    "You are a research writer. Produce a thorough, well-structured "
    "markdown report that answers the user's question using ONLY the "
    "numbered findings provided. Cite claims inline as [n] referencing "
    "the source numbers. End the report with a `## Sources` section "
    "listing each cited source as `[n] Title — URL`. Be specific, "
    "neutral, and concise; omit anything the sources do not support."
)


async def write_report(query: str, sources_digest: str, *, model: str) -> str:
    user = f"QUESTION: {query}\n\nNUMBERED SOURCES:\n{sources_digest}"
    return await llm.complete(SYSTEM, user, model=model, max_tokens=4096)
