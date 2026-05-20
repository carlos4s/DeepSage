"""Provider-dispatching async chat wrapper.

`complete` takes a ModelRef (provider + name) and routes to the matching SDK,
applying ephemeral prompt caching where supported.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .llm_config import ModelRef

T = TypeVar("T", bound=BaseModel)

_anthropic_client = None
_openai_client = None


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic()
    return _anthropic_client


def _openai():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI()
    return _openai_client


async def complete(
    system: str,
    user: str,
    *,
    model: ModelRef | str,
    max_tokens: int = 2048,
    cache_system: bool = True,
) -> str:
    """Return the assistant text for a single-turn message."""
    # Back-compat: string model names assume the default provider.
    if isinstance(model, str):
        from .llm_config import ModelRef as _MR
        model = _MR(provider="anthropic", name=model)

    if model.provider == "anthropic":
        return await _complete_anthropic(system, user, model.name, max_tokens, cache_system)
    if model.provider == "openai":
        return await _complete_openai(system, user, model.name, max_tokens)
    raise ValueError(f"Unsupported provider: {model.provider}")


async def _complete_anthropic(
    system: str, user: str, model: str, max_tokens: int, cache_system: bool
) -> str:
    system_blocks = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}
    resp = await _anthropic().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


async def _complete_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    resp = await _openai().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def parse_json(text: str, model: Type[T]) -> T:
    """Extract the first JSON object/array in `text` and validate against `model`."""
    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*(.+?)```", text, re.DOTALL | re.IGNORECASE)
    candidates = fenced + candidates
    candidates.extend(_balanced_json_candidates(text))
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


def _balanced_json_candidates(text: str) -> List[str]:
    """Return balanced JSON-looking object/array substrings from left to right.

    LLMs often produce valid JSON followed by explanatory text that contains
    more braces. A simple first-open/last-close slice can swallow too much, so
    this scanner stops at the first balanced close while respecting strings.
    """
    candidates: List[str] = []
    pairs = {"{": "}", "[": "]"}
    closers = set(pairs.values())

    for start, char in enumerate(text):
        if char not in pairs:
            continue

        stack = [pairs[char]]
        in_string = False
        escaped = False

        for pos in range(start + 1, len(text)):
            current = text[pos]

            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue

            if current == '"':
                in_string = True
            elif current in pairs:
                stack.append(pairs[current])
            elif current in closers:
                if not stack or current != stack[-1]:
                    break
                stack.pop()
                if not stack:
                    candidates.append(text[start : pos + 1])
                    break

    return candidates


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw else default
