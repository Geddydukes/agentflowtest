"""Tests for reporting functions."""

import pytest
from agentbench.core.result import EvaluationResult
from agentbench.reporting.summary import build_summary, print_summary


def test_build_summary():
    """Test build_summary function."""
    results = [
        EvaluationResult(
            run_id="run_1",
            task_id="task_1",
            scenario="test",
            agent="agent1",
            judge="judge1",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
        ),
        EvaluationResult(
            run_id="run_1",
            task_id="task_2",
            scenario="test",
            agent="agent1",
            judge="judge1",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
        ),
        EvaluationResult(
            run_id="run_1",
            task_id="task_3",
            scenario="test",
            agent="agent2",
            judge="judge1",
            raw_input={},
            agent_output={},
            scores={},
            passed=False,
        ),
    ]
    
    summary = build_summary(results)
    assert summary["total"] == 3
    assert summary["passed"] == 2
    assert summary["pass_rate"] == pytest.approx(2/3)
    assert "agent1" in summary["per_agent"]
    assert "agent2" in summary["per_agent"]
    assert summary["per_agent"]["agent1"]["passed"] == 2
    assert summary["per_agent"]["agent2"]["passed"] == 0


def test_build_summary_empty():
    """Test build_summary with empty results."""
    summary = build_summary([])
    assert summary["total"] == 0
    assert summary["passed"] == 0
    assert summary["pass_rate"] == 0.0
    assert summary["per_agent"] == {}


def test_print_summary(capsys):
    """Test print_summary function."""
    summary = {
        "total": 2,
        "passed": 1,
        "pass_rate": 0.5,
        "per_agent": {
            "agent1": {"total": 2, "passed": 1},
        },
    }
    print_summary(summary)
    captured = capsys.readouterr()
    assert "Evaluation Summary" in captured.out
    assert "Total tasks: 2" in captured.out
    assert "Passed: 1" in captured.out

