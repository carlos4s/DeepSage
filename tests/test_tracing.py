from __future__ import annotations

import asyncio
import time

from mvp_researcher.tracing import span


def test_span_records_duration():
    with span("outer") as rec:
        time.sleep(0.01)
    assert rec.ended_at is not None
    assert rec.duration_ms is not None and rec.duration_ms >= 10


def test_nested_spans_track_parent():
    with span("outer") as outer:
        with span("inner") as inner:
            pass
    assert inner.parent_id == outer.id
    assert outer.parent_id is None


def test_span_works_inside_asyncio_run():
    async def go():
        with span("async-step") as rec:
            await asyncio.sleep(0)
        return rec

    rec = asyncio.run(go())
    assert rec.ended_at is not None
