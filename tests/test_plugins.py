"""Tests for plugin discovery registry."""

from agentft.plugins.registry import discover_plugins


class DummyEP:
    def __init__(self, name, value):
        self.name = name
        self._value = value

    def load(self):
        return self._value


def test_discover_plugins(monkeypatch):
    groups = {
        "agentft.judges": [DummyEP("judge_a", object())],
        "agentft.scenarios": [DummyEP("scenario_a", object())],
        "agentft.agents": [DummyEP("agent_a", object())],
    }

    def fake_entry_points(group):
        return groups.get(group, [])

    monkeypatch.setattr("agentft.plugins.registry.entry_points", fake_entry_points)
    registry = discover_plugins()
    assert "judge_a" in registry.judges
    assert "scenario_a" in registry.scenarios
    assert "agent_a" in registry.agents
