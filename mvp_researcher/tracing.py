"""Lightweight tracing/logging helpers.

A `span` context manager records named, timed, nested operations. When the
researcher runs with `verbose=True`, every span emits an indented line on
entry and exit with elapsed wall time. Set `MVP_TRACE_JSON=1` to also dump a
JSON log of completed spans to stderr — useful for piping into other tools.
"""
from __future__ import annotations

import contextvars
import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


@dataclass
class SpanRecord:
    id: str
    name: str
    parent_id: Optional[str]
    started_at: float
    ended_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        return None if self.ended_at is None else (self.ended_at - self.started_at) * 1000


_records: contextvars.ContextVar[List[SpanRecord]] = contextvars.ContextVar(
    "_mvp_trace_records", default=[]
)
_stack: contextvars.ContextVar[List[str]] = contextvars.ContextVar(
    "_mvp_trace_stack", default=[]
)


def enabled() -> bool:
    return os.environ.get("MVP_TRACE_JSON", "0") not in ("0", "", "false", "False")


@contextmanager
def span(name: str, *, verbose: bool = False, **metadata) -> Iterator[SpanRecord]:
    sid = uuid.uuid4().hex[:8]
    stack = _stack.get()
    parent = stack[-1] if stack else None
    rec = SpanRecord(id=sid, name=name, parent_id=parent, started_at=time.time(), metadata=metadata)

    token_stack = _stack.set(stack + [sid])
    records = _records.get()
    records.append(rec)

    depth = len(stack)
    if verbose:
        print(f"{'  ' * depth}→ {name}", flush=True)
    try:
        yield rec
    finally:
        rec.ended_at = time.time()
        if verbose:
            print(f"{'  ' * depth}← {name} ({rec.duration_ms:.0f} ms)", flush=True)
        _stack.reset(token_stack)
        if enabled() and parent is None:
            # Dump the whole tree at the root level only, then reset.
            for r in records:
                print(
                    json.dumps(
                        {
                            "id": r.id,
                            "name": r.name,
                            "parent": r.parent_id,
                            "ms": r.duration_ms,
                            **r.metadata,
                        }
                    ),
                    file=sys.stderr,
                )
            _records.set([])
