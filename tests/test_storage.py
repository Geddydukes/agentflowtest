"""Tests for storage functions."""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from agentbench import Trace, TraceEvent, Cost
from agentbench.core.result import EvaluationResult
from agentbench.core.metadata import RunMetadata
from agentbench.engine.storage import (
    write_traces_jsonl,
    write_results_jsonl,
    write_metadata_json,
)


def test_write_traces_jsonl():
    """Test writing traces to JSONL file."""
    trace = Trace(
        run_id="run_1",
        task_id="task_1",
        agent="test_agent",
    )
    trace.events.append(
        TraceEvent(timestamp=1234567890.0, event_type="test", data={"key": "value"})
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "traces.jsonl"
        write_traces_jsonl([trace], str(path))
        
        assert path.exists()
        with open(path) as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["run_id"] == "run_1"
            assert data["task_id"] == "task_1"
            assert len(data["events"]) == 1


def test_write_results_jsonl():
    """Test writing results to JSONL file."""
    result = EvaluationResult(
        run_id="run_1",
        task_id="task_1",
        scenario="test",
        agent="test_agent",
        judge="test_judge",
        raw_input={"prompt": "test"},
        agent_output={"response": "answer"},
        scores={"correctness": 1.0},
        passed=True,
        cost=Cost.zero(),
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "results.jsonl"
        write_results_jsonl([result], str(path))
        
        assert path.exists()
        with open(path) as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["run_id"] == "run_1"
            assert data["passed"] is True
            assert data["scores"]["correctness"] == 1.0


def test_write_metadata_json():
    """Test writing metadata to JSON file."""
    metadata = RunMetadata(
        run_id="run_1",
        name="test_run",
        framework_version="0.0.1",
        agent_versions={"agent1": "1.0.0"},
        scenario_versions={},
        judge_versions={},
        environment_state={"python_version": "3.11"},
        hardware_info={"cpu_count": 4},
        created_at=datetime.utcnow(),
        git_commit=None,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "metadata.json"
        write_metadata_json(metadata, str(path))
        
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
            assert data["run_id"] == "run_1"
            assert data["name"] == "test_run"
            assert data["framework_version"] == "0.0.1"

