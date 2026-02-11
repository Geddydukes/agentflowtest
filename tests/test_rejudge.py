"""Tests for cached-output rejudge workflow."""

import json
from pathlib import Path

from agentft.reporting.rejudge import rejudge_cached_outputs
from agentft.engine.artifact_store import SqliteArtifactStore


class ExactJudge:
    name = "exact"

    async def score(self, task, result):
        expected = (task.expected or {}).get("answer")
        actual = result.get("response")
        passed = str(expected) == str(actual)
        return {
            "scores": {"exact": 1.0 if passed else 0.0},
            "pass": passed,
            "explanation": None,
            "metadata": None,
        }


def test_rejudge_cached_outputs(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    row = {
        "schema_version": "1.1.0",
        "run_id": "r1",
        "scenario": "s",
        "task_id": "1",
        "agent": "a",
        "task_input": {"prompt": "x"},
        "task_expected": {"answer": "42"},
        "task_metadata": None,
        "agent_output": {"response": "42"},
        "created_at": "2026-01-01T00:00:00",
    }
    (run_dir / "agent_outputs.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    results = rejudge_cached_outputs(str(run_dir), [ExactJudge()])
    assert len(results) == 1
    assert results[0].passed is True
    assert (run_dir / "rejudge_results.jsonl").exists()


def test_rejudge_cached_outputs_sqlite_backend(tmp_path):
    run_dir = tmp_path / "run_sqlite"
    run_dir.mkdir()

    store = SqliteArtifactStore(run_dir, schema_version="1.1.0")
    try:
        store.append_cached_output(
            {
                "schema_version": "1.1.0",
                "run_id": "r1",
                "scenario": "s",
                "task_id": "1",
                "agent": "a",
                "task_input": {"prompt": "x"},
                "task_expected": {"answer": "42"},
                "task_metadata": None,
                "agent_output": {"response": "42"},
                "created_at": "2026-01-01T00:00:00",
            }
        )
    finally:
        store.close()

    results = rejudge_cached_outputs(str(run_dir), [ExactJudge()])
    assert len(results) == 1
    assert results[0].passed is True
    assert (run_dir / "rejudge_results.jsonl").exists()
