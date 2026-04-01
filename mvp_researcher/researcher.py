"""Core iterative deep-research loop.

plan → (search + fetch) → reflect → maybe iterate → write report

Findings accumulate as a numbered source list; the writer cites them as [n].
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

from . import llm
from .agents import (
    KnowledgeGapOutput,
    SearchPlan,
    evaluate_gaps,
    plan_searches,
    write_report,
)
from .conversation import Conversation
from .llm_config import LLMConfig, default_config
from .search import Page, SearchResult, fetch_many, search

load_dotenv(override=False)


@dataclass
class Source:
    n: int
    title: str
    url: str
    text: str


@dataclass
class ResearchReport:
    query: str
    markdown: str
    sources: List[Source] = field(default_factory=list)
    iterations: int = 0


class DeepResearcher:
    def __init__(
        self,
        *,
        max_iterations: int | None = None,
        results_per_search: int | None = None,
        fetch_char_limit: int | None = None,
        verbose: bool = True,
        config: LLMConfig | None = None,
    ):
        self.max_iterations = max_iterations or llm.env_int("MAX_ITERATIONS", 4)
        self.results_per_search = results_per_search or llm.env_int("RESULTS_PER_SEARCH", 5)
        self.fetch_char_limit = fetch_char_limit or llm.env_int("FETCH_CHAR_LIMIT", 6000)
        self.verbose = verbose
        self.config = config or default_config()

    async def run(self, query: str, background_context: str = "") -> ResearchReport:
        self._log(f"=== Researching: {query} ===")

        sources: List[Source] = []
        seen_urls: set[str] = set()
        seen_queries: set[str] = set()
        conversation = Conversation()

        plan: SearchPlan = await plan_searches(query, model=self.config.planner)
        self._log(f"Plan: {plan.queries}")
        queries = plan.queries
        iteration = 0

        while iteration < self.max_iterations and queries:
            iteration += 1
            self._log(f"\n--- Iteration {iteration}: {len(queries)} queries ---")
            it = conversation.start_iteration()
            it.queries = list(queries)

            new_sources = await self._gather(queries, seen_urls)
            for s in new_sources:
                s.n = len(sources) + 1
                sources.append(s)
            it.findings = [s.text[:600] for s in new_sources]
            self._log(f"Collected {len(new_sources)} new sources (total {len(sources)}).")
            seen_queries.update(queries)

            if not sources:
                self._log("No sources retrieved; stopping.")
                break
            if iteration >= self.max_iterations:
                break

            gap_eval: KnowledgeGapOutput = await evaluate_gaps(
                query,
                conversation.compile(),
                background_context=background_context,
                model=self.config.reflector,
            )
            if gap_eval.research_complete or not gap_eval.outstanding_gaps:
                self._log("Knowledge gaps closed.")
                break

            next_gap = gap_eval.outstanding_gaps[0]
            it.gap = next_gap
            self._log(f"Next gap → {next_gap}")
            queries = [next_gap] if next_gap not in seen_queries else []

        if not sources:
            markdown = f"# {query}\n\n_No sources could be retrieved._"
        else:
            markdown = await write_report(
                query, _format_sources_full(sources), model=self.config.writer
            )
        return ResearchReport(
            query=query, markdown=markdown, sources=sources, iterations=iteration
        )

    async def _gather(self, queries: List[str], seen_urls: set[str]) -> List[Source]:
        search_results: List[List[SearchResult]] = await asyncio.gather(
            *(search(q, self.results_per_search) for q in queries)
        )
        urls: List[str] = []
        meta: dict[str, SearchResult] = {}
        for results in search_results:
            for r in results:
                if r.url and r.url not in seen_urls and r.url not in meta:
                    meta[r.url] = r
                    urls.append(r.url)
        if not urls:
            return []
        pages: List[Page] = await fetch_many(urls, self.fetch_char_limit)
        out: List[Source] = []
        for p in pages:
            seen_urls.add(p.url)
            sr = meta.get(p.url)
            title = p.title or (sr.title if sr else p.url)
            out.append(Source(n=0, title=title, url=p.url, text=p.text))
        return out

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)


def _format_sources_brief(sources: List[Source]) -> str:
    parts = []
    for s in sources:
        snippet = s.text[:400].replace("\n", " ")
        parts.append(f"[{s.n}] {s.title} ({s.url})\n  {snippet}…")
    return "\n\n".join(parts)


def _format_sources_full(sources: List[Source]) -> str:
    parts = []
    for s in sources:
        parts.append(f"[{s.n}] {s.title}\nURL: {s.url}\n{s.text}")
    return "\n\n---\n\n".join(parts)
