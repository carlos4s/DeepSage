from __future__ import annotations

from deep_researcher.conversation import Conversation


def test_iteration_round_trip():
    c = Conversation()
    it = c.start_iteration()
    it.queries = ["solar deployments 2026"]
    it.findings = ["finding A", "finding B"]
    it.gap = "Need a 2026 capacity figure."
    it.thought = "Numbers from finding A are stale."

    out = c.compile()
    assert "ITERATION 1" in out
    assert "<task>" in out and "Need a 2026 capacity figure." in out
    assert "<action>" in out and "solar deployments 2026" in out
    assert "<findings>" in out and "finding A" in out
    assert "<thought>" in out


def test_all_findings_aggregates_across_iterations():
    c = Conversation()
    a = c.start_iteration()
    a.findings = ["one"]
    b = c.start_iteration()
    b.findings = ["two", "three"]
    assert c.all_findings() == ["one", "two", "three"]
    assert c.latest() is b
