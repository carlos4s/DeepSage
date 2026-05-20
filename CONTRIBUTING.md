# Contributing to DeepSage

Thank you for taking the time to improve DeepSage. This project is a compact
Python research agent, so the best contributions keep the code easy to inspect,
test, and run locally.

Please also read and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to Contribute

- Fix bugs in the CLI, orchestration loop, LLM provider dispatch, search, crawl,
  tracing, or PDF export paths.
- Improve tests for network-free behavior.
- Clarify documentation, examples, and configuration notes.
- Add focused agent, tool, or provider improvements without making the core
  workflow harder to understand.

For larger changes, open an issue first with the problem, proposed design, and
expected impact.

## Development Setup

DeepSage requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in at least one LLM provider key in `.env`:

- `ANTHROPIC_API_KEY` for Anthropic models.
- `OPENAI_API_KEY` for OpenAI models.
- `SERPER_API_KEY` optionally enables Serper search; without it, the project
  falls back to DuckDuckGo.

Never commit `.env`, API keys, generated reports with sensitive content, or
local virtual environments.

## Running the Project

Run the CLI in deep mode:

```bash
deepsage "How are small modular reactors being deployed in 2026?"
```

Run a shorter single-loop research pass:

```bash
deepsage --mode iterative "What's the current state of HALEU fuel supply?"
```

Render Markdown and PDF outputs:

```bash
deepsage "Battery chemistries beyond lithium-ion" -o report.md --pdf report.pdf
```

## Tests

Run the network-free test suite before opening a pull request:

```bash
pytest
```

Current tests focus on JSON parsing fallbacks, conversation state, tracing, and
configuration resolution. If a change touches a networked path, prefer testing
the parsing, normalization, state transition, or error-handling behavior without
calling live external services.

## Project Structure

- `deep_researcher/cli.py` contains the command-line entry point.
- `deep_researcher/researcher.py` orchestrates deep and iterative research.
- `deep_researcher/agents/` contains small prompt-backed agents and their
  Pydantic output schemas.
- `deep_researcher/llm.py` and `deep_researcher/llm_config.py` contain provider
  dispatch and model selection.
- `deep_researcher/search.py` and `deep_researcher/tools/crawl.py` handle web
  retrieval.
- `deep_researcher/tracing.py` records nested spans for verbose runs.
- `tests/` contains pytest coverage for deterministic behavior.

## Code Guidelines

- Keep changes scoped. Avoid broad refactors unless they are necessary for the
  bug or feature.
- Preserve the small-agent architecture: planner, report planner, knowledge-gap
  evaluator, tool selector, writer, long writer, and proofreader should remain
  individually understandable.
- Use typed data objects or Pydantic models for structured LLM outputs.
- Keep live network and LLM calls out of unit tests. Use small deterministic
  fixtures or monkeypatching instead.
- Handle missing credentials and external-service failures clearly.
- Prefer readable Python over clever abstractions.
- Update `README.md`, examples, or `.env.example` when a change affects setup,
  configuration, or user-facing behavior.

## Pull Request Checklist

Before requesting review, confirm that:

- Tests pass with `pytest`.
- New or changed behavior is covered by focused tests when practical.
- Documentation reflects user-facing changes.
- Secrets, generated local files, and environment-specific paths are not
  committed.
- The pull request explains the problem, the solution, and any remaining risks.

## Reporting Security Issues

Do not open public issues for suspected security vulnerabilities, exposed
credentials, or prompt/data handling issues that could put users at risk. Contact
the maintainers privately through the repository owner or another established
private project channel.
