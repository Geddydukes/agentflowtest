"""Tests for Scenario and ListScenario."""

import pytest
from agentbench import Task, ListScenario


def test_list_scenario_creation():
    """Test ListScenario creation."""
    tasks = [
        Task(id="1", input={"prompt": "test1"}),
        Task(id="2", input={"prompt": "test2"}),
    ]
    scenario = ListScenario(name="test_scenario", tasks=tasks)
    assert scenario.name == "test_scenario"
    assert len(list(scenario.iter_tasks())) == 2


def test_list_scenario_iter_tasks():
    """Test ListScenario.iter_tasks() returns all tasks."""
    tasks = [
        Task(id="1", input={"prompt": "test1"}),
        Task(id="2", input={"prompt": "test2"}),
        Task(id="3", input={"prompt": "test3"}),
    ]
    scenario = ListScenario(name="test", tasks=tasks)
    iterated = list(scenario.iter_tasks())
    assert len(iterated) == 3
    assert all(isinstance(t, Task) for t in iterated)
    assert [t.id for t in iterated] == ["1", "2", "3"]


def test_list_scenario_empty():
    """Test ListScenario with no tasks."""
    scenario = ListScenario(name="empty", tasks=[])
    assert len(list(scenario.iter_tasks())) == 0

