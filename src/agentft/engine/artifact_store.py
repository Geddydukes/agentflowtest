import json
import sqlite3
from pathlib import Path
from typing import Any, Protocol

from agentft.core.metadata import RunMetadata
from agentft.core.result import EvaluationResult
from agentft.core.trace import Trace
from agentft.engine.storage import (
    append_jsonl,
    append_result_jsonl,
    append_trace_jsonl,
    deserialize_result,
    load_processed_result_keys,
    load_results,
    read_checkpoint_json,
    serialize_result,
    serialize_trace,
    write_checkpoint_json,
    write_metadata_json,
)


class ArtifactStore(Protocol):
    def load_results(self) -> list[EvaluationResult]:
        ...

    def load_processed_result_keys(self) -> set[tuple[str, str, str, str]]:
        ...

    def load_checkpoint(self) -> dict[str, Any] | None:
        ...

    def append_result(self, result: EvaluationResult) -> bool:
        ...

    def append_trace(self, trace: Trace) -> None:
        ...

    def append_cached_output(self, row: dict[str, Any]) -> None:
        ...

    def write_metadata(self, metadata: RunMetadata) -> None:
        ...

    def write_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        ...

    def close(self) -> None:
        ...


class JsonlArtifactStore:
    def __init__(self, run_dir: Path, schema_version: str) -> None:
        self.run_dir = run_dir
        self.schema_version = schema_version
        self.results_path = str(run_dir / "results.jsonl")
        self.traces_path = str(run_dir / "traces.jsonl")
        self.metadata_path = str(run_dir / "run_metadata.json")
        self.cache_path = str(run_dir / "agent_outputs.jsonl")
        self.checkpoint_path = str(run_dir / "run_checkpoint.json")

    def load_results(self) -> list[EvaluationResult]:
        return load_results(self.results_path)

    def load_processed_result_keys(self) -> set[tuple[str, str, str, str]]:
        return load_processed_result_keys(self.results_path)

    def load_checkpoint(self) -> dict[str, Any] | None:
        return read_checkpoint_json(self.checkpoint_path)

    def append_result(self, result: EvaluationResult) -> bool:
        append_result_jsonl(result, self.results_path, schema_version=self.schema_version)
        return True

    def append_trace(self, trace: Trace) -> None:
        append_trace_jsonl(trace, self.traces_path, schema_version=self.schema_version)

    def append_cached_output(self, row: dict[str, Any]) -> None:
        append_jsonl(self.cache_path, row)

    def write_metadata(self, metadata: RunMetadata) -> None:
        write_metadata_json(metadata, self.metadata_path)

    def write_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        write_checkpoint_json(self.checkpoint_path, checkpoint)

    def close(self) -> None:
        return None


class SqliteArtifactStore:
    def __init__(self, run_dir: Path, schema_version: str, db_name: str = "artifacts.db") -> None:
        self.run_dir = run_dir
        self.schema_version = schema_version
        self.db_path = run_dir / db_name
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                result_key TEXT PRIMARY KEY,
                scenario TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                judge TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cached_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                scenario TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoint (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    @staticmethod
    def _result_key(scenario: str, task_id: str, agent: str, judge: str) -> str:
        return f"{scenario}|{task_id}|{agent}|{judge}"

    def load_results(self) -> list[EvaluationResult]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT payload FROM results ORDER BY rowid").fetchall()
        output: list[EvaluationResult] = []
        for (payload,) in rows:
            output.append(deserialize_result(json.loads(payload)))
        return output

    def load_processed_result_keys(self) -> set[tuple[str, str, str, str]]:
        cur = self.conn.cursor()
        rows = cur.execute("SELECT scenario, task_id, agent, judge FROM results").fetchall()
        return {(r[0], r[1], r[2], r[3]) for r in rows}

    def load_checkpoint(self) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        row = cur.execute("SELECT payload FROM checkpoint WHERE id = 1").fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def append_result(self, result: EvaluationResult) -> bool:
        payload = json.dumps(serialize_result(result, schema_version=self.schema_version), ensure_ascii=True)
        key = self._result_key(result.scenario, result.task_id, result.agent, result.judge)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO results (result_key, scenario, task_id, agent, judge, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (key, result.scenario, result.task_id, result.agent, result.judge, payload),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def append_trace(self, trace: Trace) -> None:
        payload = json.dumps(serialize_trace(trace, schema_version=self.schema_version), ensure_ascii=True)
        self.conn.execute(
            "INSERT INTO traces (run_id, task_id, agent, payload) VALUES (?, ?, ?, ?)",
            (trace.run_id, trace.task_id, trace.agent, payload),
        )
        self.conn.commit()

    def append_cached_output(self, row: dict[str, Any]) -> None:
        payload = json.dumps(row, ensure_ascii=True)
        self.conn.execute(
            """
            INSERT INTO cached_outputs (run_id, scenario, task_id, agent, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(row.get("run_id", "")),
                str(row.get("scenario", "")),
                str(row.get("task_id", "")),
                str(row.get("agent", "")),
                payload,
            ),
        )
        self.conn.commit()

    def write_metadata(self, metadata: RunMetadata) -> None:
        payload = {
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
        self.conn.execute(
            "INSERT OR REPLACE INTO metadata (id, payload) VALUES (1, ?)",
            (json.dumps(payload, ensure_ascii=True),),
        )
        self.conn.commit()

    def write_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoint (id, payload) VALUES (1, ?)",
            (json.dumps(checkpoint, ensure_ascii=True),),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def build_artifact_store(
    backend: str,
    run_dir: Path,
    schema_version: str,
    sqlite_db_name: str = "artifacts.db",
) -> ArtifactStore:
    if backend == "jsonl":
        return JsonlArtifactStore(run_dir, schema_version=schema_version)
    if backend == "sqlite":
        return SqliteArtifactStore(run_dir, schema_version=schema_version, db_name=sqlite_db_name)
    raise ValueError(f"Unsupported artifact backend: {backend}")
