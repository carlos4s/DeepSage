"""Core iterative deep-research loop.

plan → (search + fetch) → reflect → maybe iterate → write report

Findings accumulate as a numbered source list; the writer cites them as [n].
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from . import llm
from .search import Page, SearchResult, fetch_many, search

load_dotenv(override=False)


class SearchPlan(BaseModel):
    queries: List[str] = Field(min_length=1, max_length=6)


class Reflection(BaseModel):
    enough: bool = Field(description="True if findings already answer the question.")
    missing: str = Field(default="", description="What's still missing, if anything.")
    next_queries: List[str] = Field(default_factory=list, max_length=4)


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
    ):
        self.max_iterations = max_iterations or llm.env_int("MAX_ITERATIONS", 4)
        self.results_per_search = results_per_search or llm.env_int("RESULTS_PER_SEARCH", 5)
        self.fetch_char_limit = fetch_char_limit or llm.env_int("FETCH_CHAR_LIMIT", 6000)
        self.verbose = verbose
        self.planner_model = llm.env("PLANNER_MODEL", "claude-sonnet-4-6")
        self.reflect_model = llm.env("REFLECT_MODEL", "claude-sonnet-4-6")
        self.writer_model = llm.env("WRITER_MODEL", "claude-sonnet-4-6")

    async def run(self, query: str) -> ResearchReport:
        self._log(f"=== Researching: {query} ===")

        sources: List[Source] = []
        seen_urls: set[str] = set()
        seen_queries: set[str] = set()

        queries = await self._plan(query)
        iteration = 0

        while iteration < self.max_iterations and queries:
            iteration += 1
            self._log(f"\n--- Iteration {iteration}: {len(queries)} queries ---")
            new_sources = await self._gather(queries, seen_urls)
            for s in new_sources:
                s.n = len(sources) + 1
                sources.append(s)
            self._log(f"Collected {len(new_sources)} new sources (total {len(sources)}).")
            seen_queries.update(queries)

            if not sources:
                self._log("No sources retrieved; stopping.")
                break

            if iteration >= self.max_iterations:
                break

            reflection = await self._reflect(query, sources)
            if reflection.enough:
                self._log("Reflection: sufficient findings.")
                break
            queries = [q for q in reflection.next_queries if q and q not in seen_queries]
            if not queries:
                break
            self._log(f"Reflection: still missing → {reflection.missing}")

        markdown = await self._write(query, sources)
        return ResearchReport(
            query=query,
            markdown=markdown,
            sources=sources,
            iterations=iteration,
        )

    # --- pipeline steps -------------------------------------------------

    async def _plan(self, query: str) -> List[str]:
        system = (
            "You are a research planner. Given a question, output a JSON object "
            "with a `queries` array of 3-5 specific web-search queries that, taken "
            "together, would let a researcher answer the question. Cover different "
            "angles; do not repeat phrasing. Return JSON only."
        )
        today = datetime.now().strftime("%Y-%m-%d")
        user = f"Today's date: {today}\nQuestion: {query}"
        text = await llm.complete(system, user, model=self.planner_model, max_tokens=512)
        plan = llm.parse_json(text, SearchPlan)
        self._log(f"Plan: {plan.queries}")
        return plan.queries

    async def _gather(self, queries: List[str], seen_urls: set[str]) -> List[Source]:
        search_results: List[List[SearchResult]] = await asyncio.gather(
            *(search(q, self.results_per_search) for q in queries),
            return_exceptions=False,
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

    async def _reflect(self, query: str, sources: List[Source]) -> Reflection:
        system = (
            "You are a research critic. Given the original question and the "
            "findings collected so far, decide whether they already answer the "
            "question. If yes, set `enough` to true. If not, list up to 3 "
            "concrete follow-up search queries in `next_queries` and describe "
            "what is `missing`. Return JSON only matching: "
            '{"enough": bool, "missing": str, "next_queries": [str]}'
        )
        digest = _format_sources_brief(sources)
        user = f"QUESTION: {query}\n\nFINDINGS SO FAR:\n{digest}"
        text = await llm.complete(system, user, model=self.reflect_model, max_tokens=512)
        return llm.parse_json(text, Reflection)

    async def _write(self, query: str, sources: List[Source]) -> str:
        if not sources:
            return f"# {query}\n\n_No sources could be retrieved._"

        system = (
            "You are a research writer. Produce a thorough, well-structured "
            "markdown report that answers the user's question using ONLY the "
            "numbered findings provided. Cite claims inline as [n] referencing "
            "the source numbers. End the report with a `## Sources` section "
            "listing each cited source as `[n] Title — URL`. Be specific, "
            "neutral, and concise; omit anything the sources do not support."
        )
        digest = _format_sources_full(sources)
        user = f"QUESTION: {query}\n\nNUMBERED SOURCES:\n{digest}"
        return await llm.complete(system, user, model=self.writer_model, max_tokens=4096)

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
