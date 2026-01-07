import json
import os
from pathlib import Path
from typing import List, Dict, Any

from agentft.core.trace import Trace
from agentft.core.result import EvaluationResult
from agentft.core.metadata import RunMetadata


def write_traces_jsonl(traces: List[Trace], path: str) -> None:
    """Write traces to a JSONL file."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w") as f:
        for trace in traces:
            trace_dict = {
                "run_id": trace.run_id,
                "task_id": trace.task_id,
                "agent": trace.agent,
                "events": [
                    {
                        "timestamp": event.timestamp,
                        "event_type": event.event_type,
                        "data": event.data,
                    }
                    for event in trace.events
                ],
            }
            f.write(json.dumps(trace_dict, default=str) + "\n")


def write_results_jsonl(results: List[EvaluationResult], path: str) -> None:
    """Write evaluation results to a JSONL file."""
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w") as f:
        for result in results:
            result_dict = {
                "run_id": result.run_id,
                "task_id": result.task_id,
                "scenario": result.scenario,
                "agent": result.agent,
                "judge": result.judge,
                "raw_input": result.raw_input,
                "agent_output": result.agent_output,
                "scores": result.scores,
                "passed": result.passed,
                "latency_ms": result.latency_ms,
                "metadata": result.metadata,
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
            f.write(json.dumps(result_dict, default=str) + "\n")


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
    }

    with open(path_obj, "w") as f:
        json.dump(metadata_dict, f, indent=2, default=str)

