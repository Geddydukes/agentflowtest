"""Tests for core types: Task, Cost, EvaluationResult, Trace, etc."""

import pytest
from datetime import datetime
from agentft import Task, Cost, Trace, TraceEvent
from agentft.core.result import EvaluationResult


def test_task_creation():
    """Test Task dataclass creation."""
    task = Task(
        id="test_1",
        input={"prompt": "What is 2+2?"},
        expected={"answer": "4"},
        metadata={"difficulty": "easy"},
    )
    assert task.id == "test_1"
    assert task.input == {"prompt": "What is 2+2?"}
    assert task.expected == {"answer": "4"}
    assert task.metadata == {"difficulty": "easy"}


def test_task_optional_fields():
    """Test Task with optional fields."""
    task = Task(id="test_2", input={"prompt": "Hello"})
    assert task.expected is None
    assert task.metadata is None


def test_cost_creation():
    """Test Cost dataclass creation."""
    cost = Cost(total_usd=0.5, breakdown={"input": 0.2, "output": 0.3}, model="gpt-4")
    assert cost.total_usd == 0.5
    assert cost.breakdown == {"input": 0.2, "output": 0.3}
    assert cost.model == "gpt-4"


def test_cost_zero():
    """Test Cost.zero() class method."""
    cost = Cost.zero()
    assert cost.total_usd == 0.0
    assert cost.breakdown == {}
    assert cost.model is None


def test_evaluation_result_creation():
    """Test EvaluationResult dataclass creation."""
    result = EvaluationResult(
        run_id="run_1",
        task_id="task_1",
        scenario="test_scenario",
        agent="test_agent",
        judge="test_judge",
        raw_input={"prompt": "test"},
        agent_output={"response": "answer"},
        scores={"correctness": 1.0},
        passed=True,
    )
    assert result.run_id == "run_1"
    assert result.task_id == "task_1"
    assert result.passed is True
    assert result.scores == {"correctness": 1.0}
    assert result.error is None
    assert result.retries_attempted == 0


def test_evaluation_result_with_errors():
    """Test EvaluationResult with error fields."""
    result = EvaluationResult(
        run_id="run_1",
        task_id="task_1",
        scenario="test_scenario",
        agent="test_agent",
        judge="test_judge",
        raw_input={},
        agent_output={},
        scores={},
        passed=False,
        error="Test error",
        error_type="agent_crash",
        retries_attempted=2,
    )
    assert result.error == "Test error"
    assert result.error_type == "agent_crash"
    assert result.retries_attempted == 2


def test_trace_event_creation():
    """Test TraceEvent creation."""
    event = TraceEvent(
        timestamp=1234567890.0,
        event_type="agent_start",
        data={"task_id": "task_1"},
    )
    assert event.timestamp == 1234567890.0
    assert event.event_type == "agent_start"
    assert event.data == {"task_id": "task_1"}


def test_trace_creation():
    """Test Trace creation."""
    trace = Trace(
        run_id="run_1",
        task_id="task_1",
        agent="test_agent",
    )
    assert trace.run_id == "run_1"
    assert trace.task_id == "task_1"
    assert trace.agent == "test_agent"
    assert len(trace.events) == 0

    event = TraceEvent(timestamp=1234567890.0, event_type="test", data={})
    trace.events.append(event)
    assert len(trace.events) == 1

