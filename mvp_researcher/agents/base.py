"""Shared baseclass for all agents.

An Agent owns a system prompt, a model identifier, and (optionally) a Pydantic
output schema. `Agent.run(user)` calls the LLM and returns either the raw text
or a validated Pydantic instance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, Type, TypeVar

from pydantic import BaseModel

from .. import llm
from ..llm_config import ModelRef

T = TypeVar("T", bound=BaseModel)


@dataclass
class Agent(Generic[T]):
    name: str
    system: str
    model: ModelRef
    output_type: Optional[Type[T]] = None
    max_tokens: int = 2048
    cache_system: bool = True

    async def run(self, user: str) -> T | str:
        text = await llm.complete(
            self.system,
            user,
            model=self.model,
            max_tokens=self.max_tokens,
            cache_system=self.cache_system,
        )
        if self.output_type is None:
            return text
        return llm.parse_json(text, self.output_type)
