"""Thin async wrapper around the Anthropic Messages API.

Uses ephemeral prompt caching on the system prompt so iterative calls in the
same research run stay cheap.
"""
from __future__ import annotations

import json
import os
import re
from typing import Type, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()
    return _client


async def complete(
    system: str,
    user: str,
    *,
    model: str,
    max_tokens: int = 2048,
    cache_system: bool = True,
) -> str:
    """Return the assistant text for a single-turn message."""
    system_blocks = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    resp = await _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def parse_json(text: str, model: Type[T]) -> T:
    """Extract the first JSON object/array in `text` and validate against `model`."""
    candidates = [text]
    # strip ```json fences
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    # try the largest balanced { … } or [ … ] block
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    last_err: Exception | None = None
    for raw in candidates:
        try:
            return model.model_validate_json(raw.strip())
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            last_err = e
            continue
    raise ValueError(f"Could not parse JSON for {model.__name__}: {last_err}\n---\n{text}")


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default
