"""Tests for run merge helpers."""

from datetime import datetime

from agentft.core.result import EvaluationResult
from agentft.engine.artifact_store import SqliteArtifactStore
from agentft.reporting.merge import merge_run_dirs


def test_merge_run_dirs(tmp_path):
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()

    store_a = SqliteArtifactStore(run_a, schema_version="1.1.0")
    store_b = SqliteArtifactStore(run_b, schema_version="1.1.0")
    try:
        store_a.append_result(
            EvaluationResult(
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
        )
        store_b.append_result(
            EvaluationResult(
                run_id="rb",
                task_id="2",
                scenario="s",
                agent="a",
                judge="j",
                raw_input={},
                agent_output={},
                scores={},
                passed=False,
                created_at=datetime.utcnow(),
            )
        )
    finally:
        store_a.close()
        store_b.close()

    out_dir = tmp_path / "merged"
    result = merge_run_dirs([str(run_a), str(run_b)], str(out_dir), run_name="m")
    assert result["total_results"] == 2
    assert (out_dir / "results.jsonl").exists()
    assert (out_dir / "run_metadata.json").exists()
    assert (out_dir / "report.html").exists()
