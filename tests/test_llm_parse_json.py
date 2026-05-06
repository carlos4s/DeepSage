"""Coverage for llm.parse_json — the fallback ladder that lets the loop tolerate
LLMs that wrap JSON in code fences or chatty preamble."""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from mvp_researcher.llm import parse_json


class Shape(BaseModel):
    queries: list[str]


def test_plain_json():
    out = parse_json('{"queries": ["a", "b"]}', Shape)
    assert out.queries == ["a", "b"]


def test_fenced_json():
    raw = "Here you go:\n```json\n{\"queries\": [\"a\"]}\n```\nDone."
    assert parse_json(raw, Shape).queries == ["a"]


def test_unfenced_with_preamble():
    raw = "Sure thing! {\"queries\": [\"x\", \"y\", \"z\"]} and that's all."
    assert parse_json(raw, Shape).queries == ["x", "y", "z"]


def test_invalid_raises():
    with pytest.raises(ValueError):
        parse_json("not json at all", Shape)
