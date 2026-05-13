from __future__ import annotations

import pytest

from deep_researcher.llm_config import default_config


def test_default_config_uses_anthropic_when_unset(monkeypatch):
    for var in (
        "PLANNER_MODEL_PROVIDER", "PLANNER_MODEL",
        "REFLECT_MODEL_PROVIDER", "REFLECT_MODEL",
        "WRITER_MODEL_PROVIDER", "WRITER_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = default_config()
    assert cfg.planner.provider == "anthropic"
    assert "claude" in cfg.planner.name


def test_env_override_picks_openai(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("PLANNER_MODEL", "gpt-4o-mini")
    cfg = default_config()
    assert cfg.planner.provider == "openai"
    assert cfg.planner.name == "gpt-4o-mini"


def test_unsupported_provider_raises(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL_PROVIDER", "cohere")
    with pytest.raises(ValueError):
        default_config()
