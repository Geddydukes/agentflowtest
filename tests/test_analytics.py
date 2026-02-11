"""Tests for analytics helpers."""

from datetime import datetime

from agentft.core.result import EvaluationResult
from agentft.core.cost import Cost
from agentft.reporting.analytics import analyze_results


def test_analyze_results():
    results = [
        EvaluationResult(
            run_id="r",
            task_id="1",
            scenario="s1",
            agent="a1",
            judge="j1",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
            latency_ms=100.0,
            cost=Cost(total_usd=0.1),
            created_at=datetime.utcnow(),
        ),
        EvaluationResult(
            run_id="r",
            task_id="2",
            scenario="s2",
            agent="a1",
            judge="j1",
            raw_input={},
            agent_output={},
            scores={},
            passed=False,
            latency_ms=300.0,
            cost=Cost(total_usd=0.2),
            created_at=datetime.utcnow(),
        ),
    ]
    a = analyze_results(results)
    assert a["total"] == 2
    assert a["passed"] == 1
    assert a["pass_rate"] == 0.5
    assert a["total_cost_usd"] == 0.30000000000000004
    assert a["avg_latency_ms"] == 200.0
    assert "s1" in a["per_scenario"]
