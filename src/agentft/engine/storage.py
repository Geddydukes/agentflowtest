import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

from agentft.core.trace import Trace
from agentft.core.result import EvaluationResult
from agentft.core.metadata import RunMetadata
from agentft.core.cost import Cost


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Cost):
        return {
            "total_usd": value.total_usd,
            "breakdown": value.breakdown,
            "model": value.model,
        }
    if isinstance(value, dict):
        return {str(k): _to_json_compatible(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_compatible(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def serialize_trace(trace: Trace, schema_version: str = "1.1.0") -> Dict[str, Any]:
    return {
        "schema_version": schema_version,
        "run_id": trace.run_id,
        "task_id": trace.task_id,
        "agent": trace.agent,
        "events": [
            {
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "data": _to_json_compatible(event.data),
            }
            for event in trace.events
        ],
    }


def serialize_result(result: EvaluationResult, schema_version: str = "1.1.0") -> Dict[str, Any]:
    return {
        "schema_version": schema_version,
        "run_id": result.run_id,
        "task_id": result.task_id,
        "scenario": result.scenario,
        "agent": result.agent,
        "judge": result.judge,
        "raw_input": _to_json_compatible(result.raw_input),
        "agent_output": _to_json_compatible(result.agent_output),
        "scores": _to_json_compatible(result.scores),
        "passed": result.passed,
        "latency_ms": result.latency_ms,
        "metadata": _to_json_compatible(result.metadata),
        "cost": {
            "total_usd": result.cost.total_usd,
            "breakdown": result.cost.breakdown,
            "model": result.cost.model,
        } if result.cost else None,
        "error": result.error,
        "error_type": result.error_type,
        "retries_attempted": result.retries_attempted,
        "created_at": result.created_at.isoformat(),
    }


def deserialize_result(data: Dict[str, Any]) -> EvaluationResult:
    cost = None
    if data.get("cost"):
        cost = Cost(**data["cost"])

    created_at_raw = data.get("created_at")
    created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.utcnow()

    return EvaluationResult(
        run_id=data["run_id"],
        task_id=data["task_id"],
        scenario=data.get("scenario", ""),
        agent=data["agent"],
        judge=data["judge"],
        raw_input=data.get("raw_input", {}),
        agent_output=data.get("agent_output", {}),
        scores=data.get("scores", {}),
        passed=bool(data.get("passed", False)),
        latency_ms=data.get("latency_ms"),
        metadata=data.get("metadata"),
        created_at=created_at,
        cost=cost,
        error=data.get("error"),
        error_type=data.get("error_type"),
        retries_attempted=int(data.get("retries_attempted", 0)),
    )


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def append_jsonl(path: str, row: Dict[str, Any]) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def write_traces_jsonl(traces: List[Trace], path: str, schema_version: str = "1.1.0") -> None:
    """Write traces to a JSONL file."""
    write_jsonl(path, [serialize_trace(trace, schema_version=schema_version) for trace in traces])


def append_trace_jsonl(trace: Trace, path: str, schema_version: str = "1.1.0") -> None:
    append_jsonl(path, serialize_trace(trace, schema_version=schema_version))


def write_results_jsonl(results: List[EvaluationResult], path: str, schema_version: str = "1.1.0") -> None:
    """Write evaluation results to a JSONL file."""
    write_jsonl(path, [serialize_result(result, schema_version=schema_version) for result in results])


def append_result_jsonl(result: EvaluationResult, path: str, schema_version: str = "1.1.0") -> None:
    append_jsonl(path, serialize_result(result, schema_version=schema_version))


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    path_obj = Path(path)
    if not path_obj.exists():
        return rows
    with open(path_obj, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_results(path: str) -> List[EvaluationResult]:
    return [deserialize_result(row) for row in load_jsonl(path)]


def load_processed_result_keys(path: str) -> set[Tuple[str, str, str, str]]:
    keys: set[Tuple[str, str, str, str]] = set()
    for row in load_jsonl(path):
        keys.add((row.get("scenario", ""), row["task_id"], row["agent"], row["judge"]))
    return keys


def write_metadata_json(metadata: RunMetadata, path: str) -> None:
    """Write run metadata to a JSON file."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    metadata_dict = {
        "run_id": metadata.run_id,
        "name": metadata.name,
        "framework_version": metadata.framework_version,
        "agent_versions": metadata.agent_versions,
        "scenario_versions": metadata.scenario_versions,
        "judge_versions": metadata.judge_versions,
        "environment_state": metadata.environment_state,
        "hardware_info": metadata.hardware_info,
        "created_at": metadata.created_at.isoformat(),
        "git_commit": metadata.git_commit,
        "artifact_schema_version": metadata.artifact_schema_version,
        "status": metadata.status,
        "ended_at": metadata.ended_at.isoformat() if metadata.ended_at else None,
        "resumed_from_run_id": metadata.resumed_from_run_id,
        "seed": metadata.seed,
    }

    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=2, ensure_ascii=True)


def write_checkpoint_json(path: str, checkpoint: Dict[str, Any]) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=True)


def read_checkpoint_json(path: str) -> Dict[str, Any] | None:
    path_obj = Path(path)
    if not path_obj.exists():
        return None
    with open(path_obj, "r", encoding="utf-8") as f:
        return json.load(f)


def load_results_from_run_dir(run_dir: str) -> List[EvaluationResult]:
    run_path = Path(run_dir)
    jsonl_path = run_path / "results.jsonl"
    if jsonl_path.exists():
        return load_results(str(jsonl_path))

    sqlite_path = run_path / "artifacts.db"
    if sqlite_path.exists():
        conn = sqlite3.connect(sqlite_path)
        try:
            rows = conn.execute("SELECT payload FROM results ORDER BY rowid").fetchall()
            return [deserialize_result(json.loads(row[0])) for row in rows]
        finally:
            conn.close()

    raise FileNotFoundError(f"No results backend found in run dir: {run_dir}")
