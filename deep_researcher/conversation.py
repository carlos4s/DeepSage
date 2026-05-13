"""Iteration-level history used by the knowledge-gap loop.

Each iteration records: the gap being addressed, the queries issued, the
findings extracted, and any free-form thought from the evaluator. The compiled
history is fed back to agents as context for the next iteration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class IterationData:
    gap: str = ""
    queries: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    thought: str = ""


@dataclass
class Conversation:
    history: List[IterationData] = field(default_factory=list)

    def start_iteration(self) -> IterationData:
        self.history.append(IterationData())
        return self.history[-1]

    def latest(self) -> IterationData:
        return self.history[-1]

    def all_findings(self) -> List[str]:
        return [f for it in self.history for f in it.findings]

    def compile(self) -> str:
        out: List[str] = []
        for i, it in enumerate(self.history, start=1):
            out.append(f"[ITERATION {i}]")
            if it.thought:
                out.append(f"<thought>\n{it.thought}\n</thought>")
            if it.gap:
                out.append(f"<task>\nAddress this knowledge gap: {it.gap}\n</task>")
            if it.queries:
                joined = "\n".join(it.queries)
                out.append(f"<action>\nQueries:\n{joined}\n</action>")
            if it.findings:
                joined = "\n\n".join(it.findings)
                out.append(f"<findings>\n{joined}\n</findings>")
            out.append("")
        return "\n".join(out).strip()
