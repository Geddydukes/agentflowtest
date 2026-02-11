import random
from datetime import datetime

from agentft.core.result import EvaluationResult
from agentft.engine.storage import write_results_jsonl
from agentft.reporting.compare import compare_runs
from agentft.reporting.summary import build_summary


def _make_row(run_id: str, task_id: str, agent: str, passed: bool) -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        task_id=task_id,
        scenario="s",
        agent=agent,
        judge="j",
        raw_input={},
        agent_output={},
        scores={},
        passed=passed,
        created_at=datetime.utcnow(),
    )


def test_summary_invariants_under_randomized_inputs():
    rng = random.Random(7)
    rows = []
    for i in range(200):
        rows.append(
            _make_row(
                run_id="r",
                task_id=str(i),
                agent=f"a{i % 3}",
                passed=bool(rng.randrange(2)),
            )
        )
    summary = build_summary(rows)
    assert 0.0 <= summary["pass_rate"] <= 1.0
    assert summary["total"] == len(rows)
    assert 0 <= summary["passed"] <= summary["total"]


def test_compare_delta_sign_flips_when_swapping_runs(tmp_path):
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    run_a.mkdir()
    run_b.mkdir()

    rows_a = [_make_row("ra", "1", "a", False), _make_row("ra", "2", "a", False)]
    rows_b = [_make_row("rb", "1", "a", True), _make_row("rb", "2", "a", False)]
    write_results_jsonl(rows_a, str(run_a / "results.jsonl"))
    write_results_jsonl(rows_b, str(run_b / "results.jsonl"))

    ab = compare_runs(str(run_a), str(run_b))
    ba = compare_runs(str(run_b), str(run_a))
    assert ab["delta_pass_rate"] == -ba["delta_pass_rate"]
