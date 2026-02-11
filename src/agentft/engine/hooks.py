"""Optional external hooks for streaming run events to other systems."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from agentft.core.metadata import RunMetadata
from agentft.core.result import EvaluationResult
from agentft.core.trace import Trace
from agentft.engine.storage import append_jsonl, serialize_result, serialize_trace


class RunEventSink(Protocol):
    """Protocol for run lifecycle hooks."""

    def on_run_start(self, metadata: RunMetadata, config: dict[str, Any]) -> None:
        ...

    def on_result(self, result: EvaluationResult) -> None:
        ...

    def on_trace(self, trace: Trace) -> None:
        ...

    def on_run_end(self, metadata: RunMetadata, stats: dict[str, Any]) -> None:
        ...


class JsonlRunEventSink:
    """Writes structured run events to a JSONL stream."""

    def __init__(self, output_path: str, schema_version: str = "1.1.0") -> None:
        self.output_path = str(Path(output_path))
        self.schema_version = schema_version

    def on_run_start(self, metadata: RunMetadata, config: dict[str, Any]) -> None:
        append_jsonl(
            self.output_path,
            {
                "schema_version": self.schema_version,
                "event_type": "run_start",
                "run_id": metadata.run_id,
                "metadata": {
                    "name": metadata.name,
                    "framework_version": metadata.framework_version,
                    "created_at": metadata.created_at.isoformat(),
                    "artifact_schema_version": metadata.artifact_schema_version,
                },
                "config": config,
            },
        )

    def on_result(self, result: EvaluationResult) -> None:
        append_jsonl(
            self.output_path,
            {
                "schema_version": self.schema_version,
                "event_type": "result",
                "run_id": result.run_id,
                "result": serialize_result(result, schema_version=self.schema_version),
            },
        )

    def on_trace(self, trace: Trace) -> None:
        append_jsonl(
            self.output_path,
            {
                "schema_version": self.schema_version,
                "event_type": "trace",
                "run_id": trace.run_id,
                "trace": serialize_trace(trace, schema_version=self.schema_version),
            },
        )

    def on_run_end(self, metadata: RunMetadata, stats: dict[str, Any]) -> None:
        append_jsonl(
            self.output_path,
            {
                "schema_version": self.schema_version,
                "event_type": "run_end",
                "run_id": metadata.run_id,
                "status": metadata.status,
                "ended_at": metadata.ended_at.isoformat() if metadata.ended_at else None,
                "stats": stats,
            },
        )


class StdoutJsonEventSink:
    """Emit event payloads as JSON lines to stdout."""

    def __init__(self, schema_version: str = "1.1.0") -> None:
        self.schema_version = schema_version

    def _emit(self, payload: dict[str, Any]) -> None:
        print(json.dumps(payload, ensure_ascii=True))

    def on_run_start(self, metadata: RunMetadata, config: dict[str, Any]) -> None:
        self._emit(
            {
                "schema_version": self.schema_version,
                "event_type": "run_start",
                "run_id": metadata.run_id,
                "config": config,
            }
        )

    def on_result(self, result: EvaluationResult) -> None:
        self._emit(
            {
                "schema_version": self.schema_version,
                "event_type": "result",
                "run_id": result.run_id,
                "task_id": result.task_id,
                "scenario": result.scenario,
                "agent": result.agent,
                "judge": result.judge,
                "passed": result.passed,
                "error_type": result.error_type,
            }
        )

    def on_trace(self, trace: Trace) -> None:
        self._emit(
            {
                "schema_version": self.schema_version,
                "event_type": "trace",
                "run_id": trace.run_id,
                "task_id": trace.task_id,
                "agent": trace.agent,
                "events": len(trace.events),
            }
        )

    def on_run_end(self, metadata: RunMetadata, stats: dict[str, Any]) -> None:
        self._emit(
            {
                "schema_version": self.schema_version,
                "event_type": "run_end",
                "run_id": metadata.run_id,
                "status": metadata.status,
                "stats": stats,
            }
        )
