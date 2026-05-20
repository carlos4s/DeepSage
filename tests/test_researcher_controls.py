from __future__ import annotations

import asyncio
import time

from deep_researcher.researcher import IterativeResearcher, _gather_limited


def test_time_budget_exhaustion():
    researcher = IterativeResearcher(max_time_minutes=0.001)
    researcher._started_at = time.monotonic() - 1
    assert researcher._time_budget_exhausted()


def test_zero_time_budget_is_disabled():
    researcher = IterativeResearcher(max_time_minutes=0)
    researcher._started_at = time.monotonic() - 10_000
    assert not researcher._time_budget_exhausted()


def test_gather_limited_caps_concurrency():
    active = 0
    max_seen = 0

    async def task(value: int) -> int:
        nonlocal active, max_seen
        active += 1
        max_seen = max(max_seen, active)
        await asyncio.sleep(0)
        active -= 1
        return value

    async def run():
        return await _gather_limited((task(i) for i in range(8)), 2)

    assert asyncio.run(run()) == list(range(8))
    assert max_seen <= 2
