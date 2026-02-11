from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentft.core.result import EvaluationResult
from agentft.engine.storage import load_results_from_run_dir


def _serialize_results(results: list[EvaluationResult]) -> list[dict[str, Any]]:
    rows = []
    for r in results:
        rows.append(
            {
                "run_id": r.run_id,
                "scenario": r.scenario,
                "task_id": r.task_id,
                "agent": r.agent,
                "judge": r.judge,
                "passed": bool(r.passed),
                "latency_ms": r.latency_ms,
                "cost_total_usd": r.cost.total_usd if r.cost else None,
                "error_type": r.error_type,
                "retries_attempted": r.retries_attempted,
                "created_at": r.created_at.isoformat(),
                "scores_json": json.dumps(r.scores, ensure_ascii=True),
                "metadata_json": json.dumps(r.metadata, ensure_ascii=True) if r.metadata is not None else None,
            }
        )
    return rows


def export_results_to_parquet(results: list[EvaluationResult], output_path: str) -> str:
    """
    Export run results into a Parquet file.

    Requires optional dependency:
    - `duckdb`
    """
    try:
        import duckdb  # type: ignore
    except Exception as exc:
        raise ImportError("Parquet export requires optional dependency `duckdb`.") from exc

    rows = _serialize_results(results)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(database=":memory:")
    try:
        conn.execute(
            """
            CREATE TABLE results (
                run_id VARCHAR,
                scenario VARCHAR,
                task_id VARCHAR,
                agent VARCHAR,
                judge VARCHAR,
                passed BOOLEAN,
                latency_ms DOUBLE,
                cost_total_usd DOUBLE,
                error_type VARCHAR,
                retries_attempted INTEGER,
                created_at VARCHAR,
                scores_json VARCHAR,
                metadata_json VARCHAR
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["run_id"],
                    row["scenario"],
                    row["task_id"],
                    row["agent"],
                    row["judge"],
                    row["passed"],
                    row["latency_ms"],
                    row["cost_total_usd"],
                    row["error_type"],
                    row["retries_attempted"],
                    row["created_at"],
                    row["scores_json"],
                    row["metadata_json"],
                )
                for row in rows
            ],
        )
        conn.execute(f"COPY results TO '{out}' (FORMAT PARQUET)")
    finally:
        conn.close()

    return str(out)


def export_run_to_parquet(run_dir: str, output_path: str) -> str:
    return export_results_to_parquet(load_results_from_run_dir(run_dir), output_path)
