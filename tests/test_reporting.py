"""Tests for reporting functions."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from agentft.core.result import EvaluationResult
from agentft.core.metadata import RunMetadata
from agentft.reporting.summary import build_summary, print_summary
from agentft.reporting.html_report import generate_html_report


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


def test_build_summary_task_level_any_rule():
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
            passed=False,
        ),
        EvaluationResult(
            run_id="run_1",
            task_id="task_1",
            scenario="test",
            agent="agent1",
            judge="judge2",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
        ),
    ]
    summary = build_summary(results, aggregation_level="task", task_pass_rule="any")
    assert summary["total"] == 1
    assert summary["passed"] == 1


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


def test_html_report_escapes_untrusted_content():
    """HTML report should escape potentially dangerous content."""
    metadata = RunMetadata(
        run_id="run_1",
        name="test_run",
        framework_version="0.1.0",
        agent_versions={"agent1": "1.0.0"},
        scenario_versions={},
        judge_versions={},
        environment_state={"python_version": "3.11"},
        hardware_info={"cpu_count": 4},
        created_at=datetime.utcnow(),
        git_commit=None,
    )
    results = [
        EvaluationResult(
            run_id="run_1",
            task_id="<script>alert(1)</script>",
            scenario="test",
            agent="agent1",
            judge="judge1",
            raw_input={},
            agent_output={},
            scores={},
            passed=False,
            error="<img src=x onerror=alert(1)>",
        )
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "report.html"
        generate_html_report(metadata, results, str(path))
        html = path.read_text()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
