"""Research orchestrators.

* IterativeResearcher: single gap-driven loop (plan → search → reflect → write).
* DeepResearcher: multi-section workflow that plans an outline and runs an
  IterativeResearcher concurrently for each section, then stitches the drafts
  into a single report.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

from . import llm
from .agents import (
    AgentSelectionPlan,
    KnowledgeGapOutput,
    ReportPlan,
    ReportPlanSection,
    SearchPlan,
    SectionDraft,
    ToolCall,
    evaluate_gaps,
    plan_report,
    plan_searches,
    proofread,
    select_tools,
    write_long_report,
    write_report,
)
from .conversation import Conversation
from .llm_config import LLMConfig, default_config
from .search import Page, SearchResult, fetch_many, search
from .tools import crawl_url

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


# --------------------------------------------------------------------------- #
# IterativeResearcher                                                         #
# --------------------------------------------------------------------------- #


class IterativeResearcher:
    """Single gap-driven research loop for one focused question."""

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
        # First iteration starts from the search plan; subsequent iterations
        # use the tool selector to pick tools per gap.
        next_calls: List[ToolCall] = [
            ToolCall(tool="search", input=q, rationale="initial plan") for q in plan.queries
        ]
        iteration = 0

        while iteration < self.max_iterations and next_calls:
            iteration += 1
            self._log(
                f"\n--- Iteration {iteration}: {len(next_calls)} tool call(s) ---"
            )
            it = conversation.start_iteration()
            it.queries = [f"{tc.tool}:{tc.input}" for tc in next_calls]

            new_sources = await self._dispatch(next_calls, seen_urls)
            for s in new_sources:
                s.n = len(sources) + 1
                sources.append(s)
            it.findings = [s.text[:600] for s in new_sources]
            self._log(
                f"Collected {len(new_sources)} new sources (total {len(sources)})."
            )
            seen_queries.update(tc.input for tc in next_calls)

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
            selection: AgentSelectionPlan = await select_tools(
                next_gap, history=conversation.compile(), model=self.config.planner
            )
            next_calls = [
                tc for tc in selection.tasks if tc.input not in seen_queries
            ]

        if not sources:
            markdown = f"# {query}\n\n_No sources could be retrieved._"
        else:
            markdown = await write_report(
                query, _format_sources_full(sources), model=self.config.writer
            )
        return ResearchReport(
            query=query, markdown=markdown, sources=sources, iterations=iteration
        )

    async def _dispatch(
        self, calls: List[ToolCall], seen_urls: set[str]
    ) -> List[Source]:
        """Run a mixed batch of search/crawl tool calls concurrently."""
        async def run(call: ToolCall) -> List[Source]:
            if call.tool == "search":
                results = await search(call.input, self.results_per_search)
                urls = [r.url for r in results if r.url and r.url not in seen_urls]
                if not urls:
                    return []
                pages = await fetch_many(urls, self.fetch_char_limit)
                meta = {r.url: r for r in results}
                out: List[Source] = []
                for p in pages:
                    if p.url in seen_urls:
                        continue
                    seen_urls.add(p.url)
                    sr = meta.get(p.url)
                    title = p.title or (sr.title if sr else p.url)
                    out.append(Source(n=0, title=title, url=p.url, text=p.text))
                return out
            if call.tool == "crawl":
                if call.input in seen_urls:
                    return []
                pages = await crawl_url(call.input, char_limit=self.fetch_char_limit)
                out = []
                for p in pages:
                    if p.url in seen_urls:
                        continue
                    seen_urls.add(p.url)
                    out.append(Source(n=0, title=p.title, url=p.url, text=p.text))
                return out
            return []

        batches = await asyncio.gather(*(run(c) for c in calls))
        return [s for batch in batches for s in batch]

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)


# --------------------------------------------------------------------------- #
# DeepResearcher                                                              #
# --------------------------------------------------------------------------- #


class DeepResearcher:
    """Plans a multi-section report and runs an IterativeResearcher per section."""

    def __init__(
        self,
        *,
        max_iterations: int | None = None,
        results_per_search: int | None = None,
        fetch_char_limit: int | None = None,
        verbose: bool = True,
        config: LLMConfig | None = None,
        proofread: bool = True,
    ):
        self.max_iterations = max_iterations
        self.results_per_search = results_per_search
        self.fetch_char_limit = fetch_char_limit
        self.verbose = verbose
        self.config = config or default_config()
        self.do_proofread = proofread

    async def run(self, query: str) -> ResearchReport:
        self._log(f"=== Building report plan for: {query} ===")
        plan: ReportPlan = await plan_report(query, model=self.config.planner)
        self._log(
            f"Report '{plan.report_title}' — {len(plan.report_outline)} sections."
        )

        section_reports = await asyncio.gather(
            *(self._research_section(s, plan.background_context) for s in plan.report_outline)
        )

        self._log("=== Stitching final report ===")
        drafts = [
            SectionDraft(title=section.title, markdown=rep.markdown)
            for section, rep in zip(plan.report_outline, section_reports)
        ]
        markdown = await write_long_report(
            plan.report_title,
            plan.background_context,
            drafts,
            model=self.config.writer,
        )

        if self.do_proofread:
            self._log("=== Proofreading ===")
            markdown = await proofread(markdown, model=self.config.writer)

        all_sources: List[Source] = []
        for rep in section_reports:
            all_sources.extend(rep.sources)
        return ResearchReport(
            query=query,
            markdown=markdown,
            sources=all_sources,
            iterations=sum(r.iterations for r in section_reports),
        )

    async def _research_section(
        self, section: ReportPlanSection, background: str
    ) -> ResearchReport:
        researcher = IterativeResearcher(
            max_iterations=self.max_iterations,
            results_per_search=self.results_per_search,
            fetch_char_limit=self.fetch_char_limit,
            verbose=self.verbose,
            config=self.config,
        )
        return await researcher.run(section.key_question, background_context=background)

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
