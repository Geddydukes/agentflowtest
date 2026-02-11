import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from agentft.core.task import Task
from agentft.core.result import EvaluationResult
from agentft.core.judge import Judge
from agentft.core.cost import Cost
from agentft.engine.storage import load_jsonl, append_result_jsonl


def rejudge_cached_outputs(run_dir: str, judges: List[Judge], output_filename: str = "rejudge_results.jsonl") -> List[EvaluationResult]:
    """
    Re-score cached agent outputs without rerunning agents.

    Supports cached outputs from either:
    - `agent_outputs.jsonl` (JSONL backend), or
    - SQLite `cached_outputs` table in `artifacts.db` (SQLite backend).
    """
    run_path = Path(run_dir)
    rows = _load_cached_output_rows(run_path)
    out_path = str(run_path / output_filename)
    Path(out_path).write_text("", encoding="utf-8")

    results: List[EvaluationResult] = []
    for row in rows:
        task = Task(
            id=row["task_id"],
            input=row.get("task_input", {}),
            expected=row.get("task_expected"),
            metadata=row.get("task_metadata"),
        )
        agent_output = row.get("agent_output", {})
        for judge in judges:
            score = _run_judge_sync_compatible(judge, task, agent_output)
            result = EvaluationResult(
                run_id=row.get("run_id", "unknown"),
                task_id=row["task_id"],
                scenario=row.get("scenario", ""),
                agent=row.get("agent", ""),
                judge=judge.name,
                raw_input=task.input,
                agent_output=agent_output,
                scores=score.get("scores", {}),
                passed=bool(score.get("pass", False)),
                latency_ms=None,
                metadata=score.get("metadata"),
                created_at=datetime.utcnow(),
                cost=_safe_cost(agent_output.get("cost")),
                error=None,
                error_type=None,
                retries_attempted=0,
            )
            append_result_jsonl(result, out_path, schema_version=row.get("schema_version", "1.1.0"))
            results.append(result)
    return results


def _load_cached_output_rows(run_path: Path) -> list[dict]:
    cache_path = run_path / "agent_outputs.jsonl"
    if cache_path.exists():
        return load_jsonl(str(cache_path))

    sqlite_candidates = [run_path / "artifacts.db", *sorted(run_path.glob("*.db"))]
    checked: set[str] = set()
    for db_path in sqlite_candidates:
        db_str = str(db_path)
        if db_str in checked or not db_path.exists():
            continue
        checked.add(db_str)
        rows = _load_cached_outputs_from_sqlite(db_path)
        if rows:
            return rows

    raise FileNotFoundError(
        "Cached outputs not found. Expected `agent_outputs.jsonl` or SQLite `cached_outputs` table."
    )


def _load_cached_outputs_from_sqlite(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    try:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cached_outputs'"
        ).fetchone()
        if not table:
            return []
        payload_rows = conn.execute(
            "SELECT payload FROM cached_outputs ORDER BY id"
        ).fetchall()
        out: list[dict] = []
        for (payload,) in payload_rows:
            if payload:
                out.append(json.loads(payload))
        return out
    finally:
        conn.close()


def _safe_cost(raw_cost):
    if isinstance(raw_cost, Cost):
        return raw_cost
    if isinstance(raw_cost, dict):
        return Cost(**raw_cost)
    return None


def _run_judge_sync_compatible(judge: Judge, task: Task, agent_output: dict):
    import asyncio
    coro = judge.score(task, agent_output)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("rejudge_cached_outputs must be called outside an active event loop.")
