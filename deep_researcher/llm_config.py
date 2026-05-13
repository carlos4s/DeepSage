"""Provider-agnostic LLM config.

Selects between Anthropic and OpenAI based on `*_PROVIDER` env vars. The model
identifier carried in the config is opaque to callers — `llm.complete` reads
the provider tag and dispatches accordingly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

Provider = Literal["anthropic", "openai"]

SUPPORTED_PROVIDERS: tuple[Provider, ...] = ("anthropic", "openai")


@dataclass(frozen=True)
class ModelRef:
    provider: Provider
    name: str

    def __str__(self) -> str:  # for logging
        return f"{self.provider}:{self.name}"


@dataclass(frozen=True)
class LLMConfig:
    planner: ModelRef
    reflector: ModelRef
    writer: ModelRef


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _model_from_env(role: str, default_provider: str, default_model: str) -> ModelRef:
    provider = _env(f"{role}_MODEL_PROVIDER", default_provider).lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported {role} provider: {provider!r}. "
            f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}"
        )
    name = _env(f"{role}_MODEL", default_model)
    return ModelRef(provider=provider, name=name)  # type: ignore[arg-type]


def default_config() -> LLMConfig:
    return LLMConfig(
        planner=_model_from_env("PLANNER", "anthropic", "claude-sonnet-4-6"),
        reflector=_model_from_env("REFLECT", "anthropic", "claude-sonnet-4-6"),
        writer=_model_from_env("WRITER", "anthropic", "claude-sonnet-4-6"),
    )
