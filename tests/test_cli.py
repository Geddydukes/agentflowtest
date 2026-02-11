"""Tests for CLI command handlers."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from agentft.cli import (
    cmd_run,
    cmd_summary,
    cmd_compare,
    cmd_rejudge,
    cmd_gate,
    cmd_analyze,
    cmd_merge,
    cmd_orchestrate,
    cmd_rank,
    cmd_migrate,
    main,
)
from agentft.core.result import EvaluationResult
from agentft.core.cost import Cost
from agentft.engine.artifact_store import SqliteArtifactStore
from agentft.plugins.registry import PluginRegistry


def test_cmd_run_with_config(monkeypatch, tmp_path):
    config_path = tmp_path / "config.py"
    config_path.write_text(
        """
from agentft import RunConfig, ListScenario, Task

class A:
    name = "a"
    version = "1.0.0"
    provider_key = None
    async def setup(self): pass
    async def reset(self): pass
    async def teardown(self): pass
    async def run_task(self, task, context=None): return {"response": "ok"}

class J:
    name = "j"
    async def score(self, task, result):
        return {"scores": {"s": 1.0}, "pass": True, "explanation": None, "metadata": None}

config = RunConfig(name="x", agents=[A()], scenarios=[ListScenario("s", [Task(id="1", input={})])], judges=[J()])
""",
        encoding="utf-8",
    )

    fake = EvaluationResult(
        run_id="run-1",
        task_id="1",
        scenario="s",
        agent="a",
        judge="j",
        raw_input={},
        agent_output={},
        scores={"s": 1.0},
        passed=True,
        created_at=datetime.utcnow(),
    )
    monkeypatch.setattr("agentft.cli.run", lambda config: [fake])

    rc = cmd_run(argparse.Namespace(config=str(config_path)))
    assert rc == 0


def test_cmd_run_with_strict_config_json(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "strict_run",
                "agents": ["dummy_agent"],
                "scenarios": [
                    {
                        "type": "list",
                        "name": "s",
                        "tasks": [{"id": "1", "input": {"prompt": "x"}, "expected": {"answer": "42"}}],
                    }
                ],
                "judges": [{"type": "exact_match"}],
            }
        ),
        encoding="utf-8",
    )

    class DummyAgent:
        name = "dummy_agent"

    monkeypatch.setattr(
        "agentft.cli.discover_plugins",
        lambda: PluginRegistry(agents={"dummy_agent": lambda: DummyAgent()}, scenarios={}, judges={}),
    )

    fake = EvaluationResult(
        run_id="run-1",
        task_id="1",
        scenario="s",
        agent="dummy_agent",
        judge="exact_match",
        raw_input={},
        agent_output={},
        scores={"exact_match": 1.0},
        passed=True,
        created_at=datetime.utcnow(),
    )
    monkeypatch.setattr("agentft.cli.run", lambda config: [fake])

    rc = cmd_run(
        argparse.Namespace(
            config=None,
            config_json=str(config_path),
            strict_config=True,
            output_json=None,
        )
    )
    assert rc == 0


def test_cmd_summary(monkeypatch, tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    row = {
        "run_id": "run-1",
        "task_id": "1",
        "scenario": "s",
        "agent": "a",
        "judge": "j",
        "raw_input": {},
        "agent_output": {},
        "scores": {"s": 1.0},
        "passed": True,
        "cost": {"total_usd": 0.0, "breakdown": {}, "model": None},
    }
    (run_dir / "results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    rc = cmd_summary(argparse.Namespace(run_dir=str(run_dir)))
    assert rc == 0


def test_cmd_compare(monkeypatch):
    monkeypatch.setattr(
        "agentft.reporting.compare.compare_runs",
        lambda a, b: {
            "run_a": {"dir": a, "pass_rate": 0.5, "passed": 1, "total": 2},
            "run_b": {"dir": b, "pass_rate": 1.0, "passed": 2, "total": 2},
            "delta_pass_rate": 0.5,
            "delta_pass_rate_ci_95": [0.1, 0.9],
            "p_value": 0.02,
            "regressions": [],
            "improvements": [],
            "missing_in_run_b": [],
            "missing_in_run_a": [],
        },
    )
    rc = cmd_compare(argparse.Namespace(run_a="a", run_b="b"))
    assert rc == 0


def test_main_no_command(monkeypatch):
    monkeypatch.setattr("sys.argv", ["aft"])
    assert main() == 1


def test_cmd_rejudge(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "agent_outputs.jsonl").write_text(
        json.dumps(
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
        ) + "\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config_rejudge.py"
    config_path.write_text(
        """
from agentft import RunConfig, ListScenario, Task

class A:
    name = "a"
    version = "1.0.0"
    provider_key = None
    async def setup(self): pass
    async def reset(self): pass
    async def teardown(self): pass
    async def run_task(self, task, context=None): return {"response": "ok"}

class J:
    name = "j"
    async def score(self, task, result):
        return {"scores": {"s": 1.0}, "pass": True, "explanation": None, "metadata": None}

config = RunConfig(name="x", agents=[A()], scenarios=[ListScenario("s", [Task(id="1", input={}, expected={"answer": "42"})])], judges=[J()])
""",
        encoding="utf-8",
    )

    rc = cmd_rejudge(argparse.Namespace(run_dir=str(run_dir), config=str(config_path), output=None))
    assert rc == 0
    assert (run_dir / "rejudge_results.jsonl").exists()


def test_cmd_gate_pass_and_fail(monkeypatch):
    monkeypatch.setattr(
        "agentft.reporting.compare.compare_runs",
        lambda a, b: {
            "run_a": {"dir": a, "pass_rate": 0.5, "passed": 1, "total": 2},
            "run_b": {"dir": b, "pass_rate": 0.5, "passed": 1, "total": 2},
            "delta_pass_rate": 0.0,
            "delta_pass_rate_ci_95": [-0.1, 0.1],
            "p_value": 0.5,
            "regressions": [],
            "improvements": [],
            "missing_in_run_b": [],
            "missing_in_run_a": [],
        },
    )
    rc_ok = cmd_gate(
        argparse.Namespace(
            run_a="a",
            run_b="b",
            max_regressions=0,
            min_delta_pass_rate=None,
            max_p_value=None,
            max_missing_in_run_b=None,
            max_missing_in_run_a=None,
        )
    )
    assert rc_ok == 0

    rc_fail = cmd_gate(
        argparse.Namespace(
            run_a="a",
            run_b="b",
            max_regressions=0,
            min_delta_pass_rate=0.1,
            max_p_value=0.05,
            max_missing_in_run_b=0,
            max_missing_in_run_a=0,
        )
    )
    assert rc_fail == 2


def test_cmd_summary_sqlite_backend(tmp_path):
    run_dir = tmp_path / "run_sqlite"
    run_dir.mkdir()
    store = SqliteArtifactStore(run_dir, schema_version="1.1.0")
    try:
        result = EvaluationResult(
            run_id="r1",
            task_id="1",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={"s": 1.0},
            passed=True,
            created_at=datetime.utcnow(),
            cost=Cost(total_usd=0.1),
        )
        store.append_result(result)
    finally:
        store.close()

    rc = cmd_summary(argparse.Namespace(run_dir=str(run_dir)))
    assert rc == 0


def test_cmd_analyze_and_merge(tmp_path):
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()

    store_a = SqliteArtifactStore(run_a, schema_version="1.1.0")
    store_b = SqliteArtifactStore(run_b, schema_version="1.1.0")
    try:
        r1 = EvaluationResult(
            run_id="ra",
            task_id="1",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={"s": 1.0},
            passed=True,
            created_at=datetime.utcnow(),
        )
        r2 = EvaluationResult(
            run_id="rb",
            task_id="2",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={"s": 0.0},
            passed=False,
            created_at=datetime.utcnow(),
        )
        store_a.append_result(r1)
        store_b.append_result(r2)
    finally:
        store_a.close()
        store_b.close()

    out_json = tmp_path / "analytics.json"
    rc_an = cmd_analyze(argparse.Namespace(run_dir=str(run_a), output_json=str(out_json)))
    assert rc_an == 0
    assert out_json.exists()

    merged_dir = tmp_path / "merged"
    rc_merge = cmd_merge(
        argparse.Namespace(
            run_dirs=[str(run_a), str(run_b)],
            output_dir=str(merged_dir),
            name="merged_cli",
            no_dedupe=False,
        )
    )
    assert rc_merge == 0
    assert (merged_dir / "results.jsonl").exists()
    assert (merged_dir / "report.html").exists()


def test_cmd_orchestrate(monkeypatch, tmp_path):
    out_dir = tmp_path / "merged_orchestrated"
    out_dir.mkdir()

    class DummyCompleted:
        def __init__(self):
            self.returncode = 0
            self.stdout = "ok"
            self.stderr = ""

    def fake_subprocess_run(cmd, capture_output, text, env=None):
        status_path = Path(cmd[cmd.index("--output-json") + 1])
        shard_index = int(cmd[cmd.index("--shard-index") + 1])
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            json.dumps(
                {
                    "run_id": f"r{shard_index}",
                    "run_dir": f"/tmp/run_{shard_index}",
                    "passed": 1,
                    "total": 1,
                }
            ),
            encoding="utf-8",
        )
        return DummyCompleted()

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)
    monkeypatch.setattr(
        "agentft.reporting.merge.merge_run_dirs",
        lambda run_dirs, output_dir, run_name, dedupe: {
            "run_id": "merged-run",
            "output_dir": output_dir,
            "total_results": len(run_dirs),
        },
    )

    rc = cmd_orchestrate(
        argparse.Namespace(
            config="examples/config_example.py",
            config_json=None,
            strict_config=False,
            shards=2,
            max_workers=2,
            output_dir=str(out_dir),
            name="orc",
            runs_dir=None,
            artifact_backend=None,
            sqlite_db_name=None,
            max_retries=None,
            retry_delay_seconds=None,
            agent_timeout_seconds=None,
            judge_timeout_seconds=None,
            max_tasks_parallel=None,
            max_agents_parallel=None,
            max_judges_parallel=None,
            seed=None,
            shuffle_tasks=False,
            keep_going=False,
            no_dedupe=False,
        )
    )
    assert rc == 0


def test_cmd_rank_and_migrate(tmp_path):
    run_dir = tmp_path / "run_ops"
    run_dir.mkdir()
    old_row = {
        "run_id": "r1",
        "task_id": "1",
        "agent": "a",
        "judge": "j",
        "raw_input": {},
        "agent_output": {},
        "scores": {},
        "passed": True,
        "created_at": "2026-01-01T00:00:00",
    }
    (run_dir / "results.jsonl").write_text(json.dumps(old_row) + "\n", encoding="utf-8")
    (run_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "run_id": "r1",
                "name": "x",
                "framework_version": "0.1.0",
                "agent_versions": {},
                "scenario_versions": {},
                "judge_versions": {},
                "environment_state": {},
                "hardware_info": None,
                "created_at": "2026-01-01T00:00:00",
                "git_commit": None,
                "artifact_schema_version": "1.0.0",
                "status": "completed",
                "ended_at": None,
                "resumed_from_run_id": None,
                "seed": None,
            }
        ),
        encoding="utf-8",
    )

    rc_m = cmd_migrate(
        argparse.Namespace(
            run_dir=str(run_dir),
            target_schema="1.1.0",
            no_backup=False,
        )
    )
    assert rc_m == 0
    assert (run_dir / "results.pre_migration.jsonl").exists()

    rc_r = cmd_rank(
        argparse.Namespace(
            run_dir=str(run_dir),
            initial_rating=1500.0,
            k_factor=24.0,
            output_json=None,
        )
    )
    assert rc_r == 0
