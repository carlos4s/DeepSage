# mvp-deep-researcher

A minimum-viable deep research agent. Takes a question, runs an iterative
plan → search → read → reflect loop, then writes a cited markdown report.

Designed as a tiny, readable counterpart to the larger
[`agents-deep-research`](../agents-deep-research) project — one provider
(Anthropic), one search tool, one loop, no agent framework.

## Install

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY
```

## Use

```bash
mvp-research "How are small modular reactors being deployed in 2026?"
# or
python -m mvp_researcher "your question here"
```

Programmatic:

```python
import asyncio
from mvp_researcher import DeepResearcher

report = asyncio.run(DeepResearcher().run("your question"))
print(report)
```

## How it works

1. **Plan** — Claude generates 3–5 focused search queries.
2. **Search & fetch** — Serper (if `SERPER_API_KEY`) or DuckDuckGo; top pages
   are fetched and reduced to readable text.
3. **Reflect** — Claude decides whether the current findings answer the
   question or proposes follow-up queries (up to `MAX_ITERATIONS`).
4. **Write** — Claude produces a markdown report with inline `[n]` citations
   and a numbered sources list.

Prompt caching is applied to the system prompt and accumulated findings so
later iterations are cheap.

## What's intentionally missing

- Multi-section long-form reports
- Multi-provider LLM abstraction
- Crawling beyond the initial fetch
- Trace/observability hooks

If you need those, use the full `agents-deep-research` package.
