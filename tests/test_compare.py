"""Tests for run comparison functions."""

import json
import tempfile
from pathlib import Path
from agentft.reporting.compare import compare_runs, load_results_jsonl


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

