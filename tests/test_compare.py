"""Tests for run comparison functions."""

import json
import tempfile
from pathlib import Path
from agentft.reporting.compare import compare_runs, load_results_jsonl
from agentft.engine.artifact_store import SqliteArtifactStore
from agentft.core.result import EvaluationResult
from datetime import datetime


def test_load_results_jsonl():
    """Test loading results from JSONL file."""
    results = [
        {"task_id": "1", "agent": "agent1", "judge": "judge1", "passed": True},
        {"task_id": "2", "agent": "agent1", "judge": "judge1", "passed": False},
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "results.jsonl"
        with open(path, "w") as f:
            for result in results:
                f.write(json.dumps(result) + "\n")
        
        loaded = load_results_jsonl(str(path))
        assert len(loaded) == 2
        assert loaded[0]["task_id"] == "1"
        assert loaded[1]["passed"] is False


def test_compare_runs():
    """Test comparing two runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_a_dir = Path(tmpdir) / "run_a"
        run_b_dir = Path(tmpdir) / "run_b"
        run_a_dir.mkdir()
        run_b_dir.mkdir()
        
        results_a = [
            {"task_id": "1", "agent": "agent1", "judge": "judge1", "passed": True},
            {"task_id": "2", "agent": "agent1", "judge": "judge1", "passed": True},
        ]
        
        results_b = [
            {"task_id": "1", "agent": "agent1", "judge": "judge1", "passed": True},
            {"task_id": "2", "agent": "agent1", "judge": "judge1", "passed": False},
        ]
        
        with open(run_a_dir / "results.jsonl", "w") as f:
            for r in results_a:
                f.write(json.dumps(r) + "\n")
        
        with open(run_b_dir / "results.jsonl", "w") as f:
            for r in results_b:
                f.write(json.dumps(r) + "\n")
        
        comparison = compare_runs(str(run_a_dir), str(run_b_dir))
        assert comparison["run_a"]["pass_rate"] == 1.0
        assert comparison["run_b"]["pass_rate"] == 0.5
        assert len(comparison["regressions"]) == 1
        assert len(comparison["improvements"]) == 0
        assert "delta_pass_rate" in comparison
        assert "delta_pass_rate_ci_95" in comparison
        assert "p_value" in comparison


def test_compare_runs_handles_missing_entries_and_scenario_keys():
    """Compare should account for rows present in only one run and preserve scenario identity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_a_dir = Path(tmpdir) / "run_a"
        run_b_dir = Path(tmpdir) / "run_b"
        run_a_dir.mkdir()
        run_b_dir.mkdir()

        results_a = [
            {"scenario": "s1", "task_id": "1", "agent": "agent1", "judge": "judge1", "passed": True},
            {"scenario": "s2", "task_id": "1", "agent": "agent1", "judge": "judge1", "passed": False},
        ]

        results_b = [
            {"scenario": "s1", "task_id": "1", "agent": "agent1", "judge": "judge1", "passed": False},
            {"scenario": "s3", "task_id": "9", "agent": "agent1", "judge": "judge1", "passed": True},
        ]

        with open(run_a_dir / "results.jsonl", "w") as f:
            for r in results_a:
                f.write(json.dumps(r) + "\n")

        with open(run_b_dir / "results.jsonl", "w") as f:
            for r in results_b:
                f.write(json.dumps(r) + "\n")

        comparison = compare_runs(str(run_a_dir), str(run_b_dir))
        assert len(comparison["regressions"]) == 1
        assert comparison["regressions"][0]["scenario"] == "s1"
        assert len(comparison["missing_in_run_b"]) == 1
        assert comparison["missing_in_run_b"][0]["scenario"] == "s2"
        assert len(comparison["missing_in_run_a"]) == 1
        assert comparison["missing_in_run_a"][0]["scenario"] == "s3"


def test_compare_runs_with_sqlite_backend(tmp_path):
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()

    store_a = SqliteArtifactStore(run_a, schema_version="1.1.0")
    store_b = SqliteArtifactStore(run_b, schema_version="1.1.0")
    try:
        base = EvaluationResult(
            run_id="ra",
            task_id="1",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
            created_at=datetime.utcnow(),
        )
        cand = EvaluationResult(
            run_id="rb",
            task_id="1",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={},
            passed=False,
            created_at=datetime.utcnow(),
        )
        store_a.append_result(base)
        store_b.append_result(cand)
    finally:
        store_a.close()
        store_b.close()

    comparison = compare_runs(str(run_a), str(run_b))
    assert comparison["run_a"]["total"] == 1
    assert comparison["run_b"]["total"] == 1
    assert len(comparison["regressions"]) == 1
