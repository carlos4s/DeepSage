# DeepSage

A gap-driven deep research agent. Plans a multi-section report, runs a
reflect-and-search loop per section, and stitches the drafts into a single
cited markdown (or PDF) document.

Built around five small agents — **planner**, **report planner**,
**knowledge-gap evaluator**, **tool selector**, and **writer / long-writer /
proofreader** — that coordinate over two tools: **web search** and
**crawl_url**. Supports Anthropic and OpenAI as LLM backends.

## Install

```bash
pip install -r requirements.txt
cp .env.example .env  # then fill in ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

## Use

```bash
# Multi-section report (default)
deepsage "How are small modular reactors being deployed in 2026?"

# Single focused loop, no section planning
deepsage --mode iterative "What's the current state of HALEU fuel supply?"

# Save to disk and render PDF
deepsage "Battery chemistries beyond lithium-ion" -o report.md --pdf report.pdf

# Skip the proofreader pass (faster, cheaper)
deepsage "..." --no-proofread
```

Programmatic:

```python
import asyncio
from deep_researcher import DeepResearcher

report = asyncio.run(DeepResearcher().run("your question"))
print(report.markdown)
```

## Architecture

```
DeepResearcher.run(query)
├── plan_report           → ReportPlan {title, background, sections[…]}
├── for each section (concurrent):
│     IterativeResearcher.run(section.key_question, background)
│     ├── plan_searches   → initial SearchPlan
│     ├── loop (≤ max_iterations):
│     │     ├── dispatch tool calls (search | crawl)  → Sources
│     │     ├── evaluate_gaps    → KnowledgeGapOutput
│     │     └── select_tools     → AgentSelectionPlan for the next gap
│     └── write_report    → cited markdown for the section
├── write_long_report     → one unified markdown with deduped citations
└── proofread             → final-pass polish (optional)
```

Every step is wrapped in a `tracing.span` so verbose runs print indented
timings; set `MVP_TRACE_JSON=1` to also emit per-span JSON to stderr.

## Configuration

Each agent role (planner, reflector, writer) takes a provider + model name
from env vars — see [`.env.example`](.env.example). The same `LLMConfig` is
passed to every agent, so you can mix providers (e.g. cheap Haiku for
planning, Sonnet for writing) without code changes.

Search backend is **Serper** if `SERPER_API_KEY` is set, otherwise
**DuckDuckGo**. The crawl tool uses `httpx` + `BeautifulSoup` with a polite
user-agent.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Tests cover the network-free pieces: JSON parsing fallbacks, conversation
state, span tracking, and config resolution. LLM/web pieces are exercised
via the examples.

## Relationship to agents-deep-research

DeepSage was built to be a smaller, more readable cousin of the
[`agents-deep-research`](https://github.com/qx-labs/agents-deep-research)
project. The agent breakdown is intentionally similar, but DeepSage uses
direct SDK calls (Anthropic Messages, OpenAI Chat) rather than the OpenAI
Agents SDK, and the surface is one package with no framework dependency.
