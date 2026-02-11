"""CLI for Agent Flow Test (AgentFT)."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from agentft import (
    ExactMatchJudge,
    HuggingFaceScenario,
    JSONLScenario,
    CSVScenario,
    ListScenario,
    RunConfig,
    Task,
    build_math_basic_scenario,
    run,
)
from agentft.plugins import discover_plugins


def _load_python_config(config_path: Path) -> RunConfig:
    spec = importlib.util.spec_from_file_location("agentft_user_config", str(config_path))
    if spec is None or spec.loader is None:
        raise ValueError(f"Unable to load config module: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "config"):
        raise ValueError("Config file must define a `config` variable of type RunConfig")
    config = module.config
    if not isinstance(config, RunConfig):
        raise ValueError("`config` must be an instance of RunConfig")
    return config


def _instantiate_component(
    spec: str | dict[str, Any],
    registry_items: dict[str, Any],
    *,
    kind: str,
) -> Any:
    if isinstance(spec, str):
        if spec not in registry_items:
            raise ValueError(f"Unknown {kind} plugin '{spec}'")
        factory = registry_items[spec]
        return factory() if callable(factory) else factory

    if not isinstance(spec, dict):
        raise ValueError(f"Invalid {kind} spec type: {type(spec)}")

    plugin_name = spec.get("plugin")
    if not plugin_name:
        raise ValueError(f"{kind} spec must include `plugin`")
    if plugin_name not in registry_items:
        raise ValueError(f"Unknown {kind} plugin '{plugin_name}'")

    factory = registry_items[plugin_name]
    params = spec.get("params") or {}
    if callable(factory):
        return factory(**params)
    return factory


def _build_strict_scenario(spec: dict[str, Any], scenario_plugins: dict[str, Any]) -> Any:
    scenario_type = spec.get("type")
    if scenario_type == "list":
        tasks = [
            Task(
                id=str(task["id"]),
                input=task.get("input", {}),
                expected=task.get("expected"),
                metadata=task.get("metadata"),
            )
            for task in spec.get("tasks", [])
        ]
        return ListScenario(name=spec["name"], tasks=tasks)
    if scenario_type == "csv":
        return CSVScenario(
            name=spec["name"],
            path=spec["path"],
            input_column=spec.get("input_column", "input"),
            expected_column=spec.get("expected_column"),
            id_column=spec.get("id_column"),
            metadata_columns=spec.get("metadata_columns"),
            delimiter=spec.get("delimiter", ","),
            sample_size=spec.get("sample_size"),
            sample_seed=spec.get("sample_seed", 42),
            stratify_by=spec.get("stratify_by"),
        )
    if scenario_type == "jsonl":
        return JSONLScenario(
            name=spec["name"],
            path=spec["path"],
            input_key=spec.get("input_key", "input"),
            expected_key=spec.get("expected_key"),
            id_key=spec.get("id_key"),
            metadata_key=spec.get("metadata_key"),
            sample_size=spec.get("sample_size"),
            sample_seed=spec.get("sample_seed", 42),
            stratify_by=spec.get("stratify_by"),
        )
    if scenario_type == "huggingface":
        return HuggingFaceScenario(
            name=spec["name"],
            dataset_name=spec["dataset_name"],
            split=spec.get("split", "test"),
            input_key=spec.get("input_key", "input"),
            expected_key=spec.get("expected_key"),
            id_key=spec.get("id_key"),
            metadata_keys=spec.get("metadata_keys"),
            sample_size=spec.get("sample_size"),
            sample_seed=spec.get("sample_seed", 42),
            stratify_by=spec.get("stratify_by"),
        )
    if scenario_type == "math_basic":
        return build_math_basic_scenario()
    if scenario_type == "plugin":
        plugin_name = spec.get("name")
        if not plugin_name:
            raise ValueError("Plugin scenario spec must include `name`")
        if plugin_name not in scenario_plugins:
            raise ValueError(f"Unknown scenario plugin '{plugin_name}'")
        factory = scenario_plugins[plugin_name]
        params = spec.get("params") or {}
        return factory(**params) if callable(factory) else factory

    raise ValueError(f"Unsupported strict scenario type: {scenario_type}")


def _load_declarative_config(config_path: Path) -> RunConfig:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    required = ("name", "agents", "scenarios", "judges")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Strict config is missing required keys: {', '.join(missing)}")

    registry = discover_plugins()
    agents = [
        _instantiate_component(agent_spec, registry.agents, kind="agent")
        for agent_spec in data["agents"]
    ]

    scenarios = [
        _build_strict_scenario(scenario_spec, registry.scenarios)
        for scenario_spec in data["scenarios"]
    ]

    judges: list[Any] = []
    for judge_spec in data["judges"]:
        if isinstance(judge_spec, dict) and judge_spec.get("type") == "exact_match":
            judges.append(ExactMatchJudge())
        else:
            judges.append(_instantiate_component(judge_spec, registry.judges, kind="judge"))

    run_fields = dict(data.get("run", {}))
    run_fields.pop("name", None)
    run_fields.pop("agents", None)
    run_fields.pop("scenarios", None)
    run_fields.pop("judges", None)
    return RunConfig(
        name=data["name"],
        agents=agents,
        scenarios=scenarios,
        judges=judges,
        **run_fields,
    )


def _load_config(args: argparse.Namespace) -> RunConfig:
    strict_config = bool(getattr(args, "strict_config", False))
    config_json = getattr(args, "config_json", None)
    config_path_raw = getattr(args, "config", None)

    if strict_config:
        if not config_json:
            raise ValueError("--strict-config requires --config-json")
        config_path = Path(config_json)
        if not config_path.exists():
            raise ValueError(f"Config file not found: {config_path}")
        return _load_declarative_config(config_path)

    if config_json:
        config_path = Path(config_json)
        if not config_path.exists():
            raise ValueError(f"Config file not found: {config_path}")
        return _load_declarative_config(config_path)

    if not config_path_raw:
        raise ValueError("Either --config or --config-json is required")
    config_path = Path(config_path_raw)
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")
    return _load_python_config(config_path)


def _apply_run_overrides(config: RunConfig, args: argparse.Namespace) -> RunConfig:
    int_overrides = {
        "max_retries": getattr(args, "max_retries", None),
        "max_tasks_parallel": getattr(args, "max_tasks_parallel", None),
        "max_agents_parallel": getattr(args, "max_agents_parallel", None),
        "max_judges_parallel": getattr(args, "max_judges_parallel", None),
        "warmup_tasks": getattr(args, "warmup_tasks", None),
        "seed": getattr(args, "seed", None),
        "shard_count": getattr(args, "shard_count", None),
        "shard_index": getattr(args, "shard_index", None),
    }
    float_overrides = {
        "retry_delay_seconds": getattr(args, "retry_delay_seconds", None),
        "agent_timeout_seconds": getattr(args, "agent_timeout_seconds", None),
        "judge_timeout_seconds": getattr(args, "judge_timeout_seconds", None),
        "max_total_cost_usd": getattr(args, "max_total_cost_usd", None),
        "max_total_runtime_seconds": getattr(args, "max_total_runtime_seconds", None),
    }
    str_overrides = {
        "name": getattr(args, "name", None),
        "runs_dir": getattr(args, "runs_dir", None),
        "fail_fast_on": getattr(args, "fail_fast_on", None),
        "resume_run_id": getattr(args, "resume_run_id", None),
        "artifact_backend": getattr(args, "artifact_backend", None),
        "sqlite_db_name": getattr(args, "sqlite_db_name", None),
    }

    for key, value in int_overrides.items():
        if value is not None:
            setattr(config, key, int(value))
    for key, value in float_overrides.items():
        if value is not None:
            setattr(config, key, float(value))
    for key, value in str_overrides.items():
        if value is not None:
            setattr(config, key, value)

    if bool(getattr(args, "shuffle_tasks", False)):
        config.shuffle_tasks = True
    if bool(getattr(args, "cache_agent_outputs", False)):
        config.cache_agent_outputs = True

    retry_policy_json = getattr(args, "retry_policy_json", None)
    if retry_policy_json:
        config.retry_policy_by_error_type = json.loads(retry_policy_json)

    return config


def cmd_run(args: argparse.Namespace) -> int:
    """Run an evaluation."""
    print("Agent Flow Test (AgentFT) - Run Command")
    print("=" * 50)

    try:
        config = _load_config(args)
        config = _apply_run_overrides(config, args)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    results = run(config)
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"\nResults: {passed} / {total} tasks passed")
    run_id = results[0].run_id if results else config.resume_run_id
    run_dir = Path(config.runs_dir) / str(run_id)
    if run_id:
        print(f"Run directory: {run_dir}/")
        print("  - results.jsonl or artifacts.db")
        print("  - traces.jsonl")
        print("  - run_metadata.json")
        print("  - report.html")

    output_json = getattr(args, "output_json", None)
    if output_json:
        payload = {
            "run_id": run_id,
            "run_dir": str(run_dir),
            "passed": passed,
            "total": total,
            "timestamp": datetime.utcnow().isoformat(),
        }
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Show summary of a run."""
    print("Agent Flow Test (AgentFT) - Summary Command")
    print("=" * 50)

    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}")
        return 1

    from agentft.reporting.summary import build_summary, print_summary
    from agentft.engine.storage import load_results_from_run_dir

    try:
        results = load_results_from_run_dir(str(run_dir))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    summary = build_summary(
        results,
        aggregation_level=getattr(args, "aggregation_level", "judge"),
        task_pass_rule=getattr(args, "task_pass_rule", "all"),
    )
    print_summary(summary)
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare two runs."""
    print("Agent Flow Test (AgentFT) - Compare Command")
    print("=" * 50)

    if not args.run_a or not args.run_b:
        print("Error: --run-a and --run-b are required")
        return 1

    from agentft.reporting.compare import compare_runs

    comparison = compare_runs(args.run_a, args.run_b)
    print(f"\nRun A: {comparison['run_a']['dir']}")
    print(f"  Pass rate: {comparison['run_a']['pass_rate']:.1%}")
    print(f"  Passed: {comparison['run_a']['passed']} / {comparison['run_a']['total']}")
    print(f"\nRun B: {comparison['run_b']['dir']}")
    print(f"  Pass rate: {comparison['run_b']['pass_rate']:.1%}")
    print(f"  Passed: {comparison['run_b']['passed']} / {comparison['run_b']['total']}")
    print(f"\nDelta (B - A): {comparison.get('delta_pass_rate', 0.0):.2%}")
    ci = comparison.get("delta_pass_rate_ci_95")
    if ci:
        print(f"95% CI: [{ci[0]:.2%}, {ci[1]:.2%}]")
    if comparison.get("p_value") is not None:
        print(f"p-value: {comparison['p_value']:.4f}")
    print(f"\nRegressions: {len(comparison['regressions'])}")
    print(f"Improvements: {len(comparison['improvements'])}")
    print(f"Missing in Run B: {len(comparison.get('missing_in_run_b', []))}")
    print(f"Missing in Run A: {len(comparison.get('missing_in_run_a', []))}")
    return 0


def cmd_rejudge(args: argparse.Namespace) -> int:
    """Re-score cached agent outputs with current judges."""
    print("Agent Flow Test (AgentFT) - Rejudge Command")
    print("=" * 50)

    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}")
        return 1

    try:
        config = _load_config(args)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    from agentft.reporting.rejudge import rejudge_cached_outputs

    output_name = args.output or "rejudge_results.jsonl"
    results = rejudge_cached_outputs(str(run_dir), config.judges, output_filename=output_name)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Rejudged {total} rows with {len(config.judges)} judge(s).")
    print(f"Passed: {passed}/{total}")
    print(f"Output: {run_dir / output_name}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    """Evaluate regression gate conditions between two runs."""
    print("Agent Flow Test (AgentFT) - Gate Command")
    print("=" * 50)
    if not args.run_a or not args.run_b:
        print("Error: --run-a and --run-b are required")
        return 1

    from agentft.reporting.compare import compare_runs
    from agentft.reporting.gates import RegressionGateConfig, evaluate_regression_gate

    comparison = compare_runs(args.run_a, args.run_b)
    gate = RegressionGateConfig(
        max_regressions=args.max_regressions,
        min_delta_pass_rate=args.min_delta_pass_rate,
        max_p_value=args.max_p_value,
        max_missing_in_run_b=args.max_missing_in_run_b,
        max_missing_in_run_a=args.max_missing_in_run_a,
    )
    passed, reasons = evaluate_regression_gate(comparison, gate)
    print(f"Gate passed: {passed}")
    if reasons:
        print("Reasons:")
        for reason in reasons:
            print(f"  - {reason}")
    return 0 if passed else 2


def cmd_analyze(args: argparse.Namespace) -> int:
    """Compute richer analytics for a run."""
    print("Agent Flow Test (AgentFT) - Analyze Command")
    print("=" * 50)
    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}")
        return 1

    from agentft.engine.storage import load_results_from_run_dir
    from agentft.reporting.analytics import analyze_results

    results = load_results_from_run_dir(str(run_dir))
    analytics = analyze_results(
        results,
        aggregation_level=getattr(args, "aggregation_level", "judge"),
        task_pass_rule=getattr(args, "task_pass_rule", "all"),
    )

    print(f"Total: {analytics['total']}")
    print(f"Passed: {analytics['passed']}")
    print(f"Pass rate: {analytics['pass_rate']:.2%}")
    print(f"Macro scenario pass rate: {analytics['macro_pass_rate_scenario']:.2%}")
    print(f"Total cost: ${analytics['total_cost_usd']:.6f}")
    if analytics["avg_latency_ms"] is not None:
        print(f"Avg latency (ms): {analytics['avg_latency_ms']:.2f}")
    print(f"Agents: {len(analytics['per_agent'])}")
    print(f"Scenarios: {len(analytics['per_scenario'])}")
    print(f"Judges: {len(analytics['per_judge'])}")

    output_json = getattr(args, "output_json", None)
    if output_json:
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(analytics, indent=2), encoding="utf-8")
        print(f"Wrote analytics JSON: {out}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """Merge multiple run dirs into a single consolidated run."""
    print("Agent Flow Test (AgentFT) - Merge Command")
    print("=" * 50)
    if not args.run_dirs or len(args.run_dirs) < 2:
        print("Error: provide at least two --run-dirs entries")
        return 1
    if not args.output_dir:
        print("Error: --output-dir is required")
        return 1

    from agentft.reporting.merge import merge_run_dirs

    try:
        result = merge_run_dirs(
            run_dirs=args.run_dirs,
            output_dir=args.output_dir,
            run_name=args.name or "merged_run",
            dedupe=not args.no_dedupe,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    print(f"Merged run id: {result['run_id']}")
    print(f"Output dir: {result['output_dir']}")
    print(f"Total results: {result['total_results']}")
    return 0


def _orchestrate_shard(
    args: argparse.Namespace,
    shard_index: int,
    shard_count: int,
    run_name: str,
    status_dir: Path,
) -> dict[str, Any]:
    status_path = status_dir / f"shard_{shard_index}.json"
    command = [sys.executable, "-m", "agentft.cli", "run"]
    if args.config:
        command.extend(["--config", args.config])
    if args.config_json:
        command.extend(["--config-json", args.config_json])
    if args.strict_config:
        command.append("--strict-config")
    command.extend(
        [
            "--name",
            f"{run_name}_shard_{shard_index}",
            "--shard-count",
            str(shard_count),
            "--shard-index",
            str(shard_index),
            "--output-json",
            str(status_path),
        ]
    )
    if args.runs_dir:
        command.extend(["--runs-dir", args.runs_dir])
    if args.artifact_backend:
        command.extend(["--artifact-backend", args.artifact_backend])
    if args.sqlite_db_name:
        command.extend(["--sqlite-db-name", args.sqlite_db_name])
    if args.max_tasks_parallel is not None:
        command.extend(["--max-tasks-parallel", str(args.max_tasks_parallel)])
    if args.max_agents_parallel is not None:
        command.extend(["--max-agents-parallel", str(args.max_agents_parallel)])
    if args.max_judges_parallel is not None:
        command.extend(["--max-judges-parallel", str(args.max_judges_parallel)])
    if args.agent_timeout_seconds is not None:
        command.extend(["--agent-timeout-seconds", str(args.agent_timeout_seconds)])
    if args.judge_timeout_seconds is not None:
        command.extend(["--judge-timeout-seconds", str(args.judge_timeout_seconds)])
    if args.max_retries is not None:
        command.extend(["--max-retries", str(args.max_retries)])
    if args.retry_delay_seconds is not None:
        command.extend(["--retry-delay-seconds", str(args.retry_delay_seconds)])
    if args.seed is not None:
        command.extend(["--seed", str(args.seed)])
    if args.shuffle_tasks:
        command.append("--shuffle-tasks")

    env = dict(os.environ)
    src_root = str(Path(__file__).resolve().parents[1])
    current_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src_root}:{current_pp}" if current_pp else src_root
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    if completed.returncode != 0:
        return {
            "ok": False,
            "shard_index": shard_index,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    if not status_path.exists():
        return {
            "ok": False,
            "shard_index": shard_index,
            "command": command,
            "returncode": 1,
            "stdout": completed.stdout,
            "stderr": "missing shard status output",
        }
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["ok"] = True
    payload["shard_index"] = shard_index
    payload["stdout"] = completed.stdout
    payload["stderr"] = completed.stderr
    return payload


def cmd_orchestrate(args: argparse.Namespace) -> int:
    """Run sharded local workers and merge outputs."""
    print("Agent Flow Test (AgentFT) - Orchestrate Command")
    print("=" * 50)

    if not args.config and not args.config_json:
        print("Error: provide --config or --config-json")
        return 1
    if args.shards < 1:
        print("Error: --shards must be >= 1")
        return 1
    if not args.output_dir:
        print("Error: --output-dir is required")
        return 1

    run_name = args.name or f"orchestrated_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    status_dir = Path(args.output_dir) / ".orchestrator"
    status_dir.mkdir(parents=True, exist_ok=True)
    workers = min(max(1, args.max_workers), args.shards)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_orchestrate_shard, args, i, args.shards, run_name, status_dir)
            for i in range(args.shards)
        ]
        for future in concurrent.futures.as_completed(futures):
            shard_result = future.result()
            if shard_result.get("ok"):
                successes.append(shard_result)
                print(f"Shard {shard_result['shard_index']} completed: {shard_result['run_dir']}")
            else:
                failures.append(shard_result)
                print(f"Shard {shard_result['shard_index']} failed (code {shard_result['returncode']})")
                if shard_result.get("stderr"):
                    print(shard_result["stderr"])

    if failures and not args.keep_going:
        print("Orchestration failed: one or more shards failed.")
        return 2
    if not successes:
        print("Orchestration failed: no successful shard runs to merge.")
        return 2

    from agentft.reporting.merge import merge_run_dirs

    merge_result = merge_run_dirs(
        run_dirs=[row["run_dir"] for row in sorted(successes, key=lambda x: x["shard_index"])],
        output_dir=args.output_dir,
        run_name=run_name,
        dedupe=not args.no_dedupe,
    )
    print(f"Merged run id: {merge_result['run_id']}")
    print(f"Output dir: {merge_result['output_dir']}")
    print(f"Total results: {merge_result['total_results']}")
    if failures:
        print(f"Shards failed but ignored: {len(failures)}")
    return 0


def cmd_rank(args: argparse.Namespace) -> int:
    """Rank agents from a run with Elo."""
    print("Agent Flow Test (AgentFT) - Rank Command")
    print("=" * 50)
    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}")
        return 1

    from agentft.engine.storage import load_results_from_run_dir
    from agentft.reporting.ranking import rank_agents_elo

    results = load_results_from_run_dir(str(run_dir))
    rankings = rank_agents_elo(results, initial_rating=args.initial_rating, k_factor=args.k_factor)
    for idx, row in enumerate(rankings, start=1):
        print(
            f"{idx}. {row['agent']}: rating={row['rating']:.2f} "
            f"games={row['games']} wins={row['wins']} losses={row['losses']} ties={row['ties']}"
        )

    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rankings, indent=2), encoding="utf-8")
        print(f"Wrote ranking JSON: {out}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate run artifacts to the latest schema."""
    print("Agent Flow Test (AgentFT) - Migrate Command")
    print("=" * 50)
    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: run directory not found: {run_dir}")
        return 1

    from agentft.engine.migrations import migrate_run_artifacts

    try:
        summary = migrate_run_artifacts(
            run_dir=str(run_dir),
            target_schema=args.target_schema,
            backup=not args.no_backup,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    print(f"Migrated rows: {summary['rows_migrated']}")
    print(f"Rows unchanged: {summary['rows_unchanged']}")
    print(f"Target schema: {summary['target_schema']}")
    if summary.get("backup_path"):
        print(f"Backup: {summary['backup_path']}")
    return 0


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=str, help="Path to Python config file that defines RunConfig")
    parser.add_argument("--config-json", type=str, help="Path to declarative JSON config file")
    parser.add_argument("--strict-config", action="store_true", help="Require declarative non-Python config loading")
    parser.add_argument("--name", type=str, help="Override run name")
    parser.add_argument("--runs-dir", type=str, help="Override output runs directory")
    parser.add_argument("--resume-run-id", type=str, help="Resume a previous run id")
    parser.add_argument("--artifact-backend", type=str, choices=["jsonl", "sqlite"], help="Artifact backend")
    parser.add_argument("--sqlite-db-name", type=str, help="SQLite DB filename when backend=sqlite")
    parser.add_argument("--fail-fast-on", type=str, choices=["none", "failure", "error", "either"], help="Fail-fast policy")
    parser.add_argument("--max-retries", type=int, help="Default max retries")
    parser.add_argument("--retry-policy-json", type=str, help="JSON map of error_type -> max retries")
    parser.add_argument("--retry-delay-seconds", type=float, help="Delay between retries")
    parser.add_argument("--agent-timeout-seconds", type=float, help="Agent call timeout")
    parser.add_argument("--judge-timeout-seconds", type=float, help="Judge call timeout")
    parser.add_argument("--max-tasks-parallel", type=int, help="Task concurrency per agent")
    parser.add_argument("--max-agents-parallel", type=int, help="Agent concurrency")
    parser.add_argument("--max-judges-parallel", type=int, help="Judge concurrency per task")
    parser.add_argument("--warmup-tasks", type=int, help="Number of warmup tasks per scenario")
    parser.add_argument("--seed", type=int, help="Seed for deterministic behavior")
    parser.add_argument("--shuffle-tasks", action="store_true", help="Shuffle task order deterministically")
    parser.add_argument("--cache-agent-outputs", action="store_true", help="Cache agent outputs for rejudge")
    parser.add_argument("--shard-count", type=int, help="Total shard count")
    parser.add_argument("--shard-index", type=int, help="Shard index (0-based)")
    parser.add_argument("--max-total-cost-usd", type=float, help="Cost budget for early stop")
    parser.add_argument("--max-total-runtime-seconds", type=float, help="Runtime budget for early stop")
    parser.add_argument("--output-json", type=str, help="Write run metadata/output summary to JSON path")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="aft",
        description="Agent Flow Test (AgentFT) - AI agent evaluation framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    run_parser = subparsers.add_parser("run", help="Run an evaluation")
    _add_run_args(run_parser)

    summary_parser = subparsers.add_parser("summary", help="Show summary of a run")
    summary_parser.add_argument("--run-dir", type=str, help="Path to run directory")
    summary_parser.add_argument(
        "--aggregation-level",
        type=str,
        choices=["judge", "task"],
        default="judge",
        help="Aggregate by judge rows or task-level rollups",
    )
    summary_parser.add_argument(
        "--task-pass-rule",
        type=str,
        choices=["all", "any", "majority"],
        default="all",
        help="Task pass rule when using --aggregation-level task",
    )

    compare_parser = subparsers.add_parser("compare", help="Compare two runs")
    compare_parser.add_argument("--run-a", type=str, help="Path to first run directory")
    compare_parser.add_argument("--run-b", type=str, help="Path to second run directory")

    rejudge_parser = subparsers.add_parser("rejudge", help="Re-score cached outputs with configured judges")
    rejudge_parser.add_argument("--run-dir", type=str, help="Path to run directory containing agent_outputs.jsonl")
    rejudge_parser.add_argument("--config", type=str, help="Path to Python config file that defines RunConfig")
    rejudge_parser.add_argument("--config-json", type=str, help="Path to declarative JSON config file")
    rejudge_parser.add_argument("--strict-config", action="store_true", help="Require declarative non-Python config")
    rejudge_parser.add_argument("--output", type=str, help="Output filename for rejudged results")

    gate_parser = subparsers.add_parser("gate", help="Apply regression gate rules between two runs")
    gate_parser.add_argument("--run-a", type=str, help="Baseline run directory")
    gate_parser.add_argument("--run-b", type=str, help="Candidate run directory")
    gate_parser.add_argument("--max-regressions", type=int, default=0, help="Maximum allowed regressions")
    gate_parser.add_argument("--min-delta-pass-rate", type=float, default=None, help="Minimum pass-rate delta (B-A)")
    gate_parser.add_argument("--max-p-value", type=float, default=None, help="Maximum p-value for pass-rate delta")
    gate_parser.add_argument("--max-missing-in-run-b", type=int, default=None, help="Maximum rows missing in candidate")
    gate_parser.add_argument("--max-missing-in-run-a", type=int, default=None, help="Maximum rows missing in baseline")

    analyze_parser = subparsers.add_parser("analyze", help="Compute advanced analytics for a run")
    analyze_parser.add_argument("--run-dir", type=str, help="Run directory")
    analyze_parser.add_argument("--output-json", type=str, help="Optional output path for analytics JSON")
    analyze_parser.add_argument(
        "--aggregation-level",
        type=str,
        choices=["judge", "task"],
        default="judge",
        help="Aggregate by judge rows or task-level rollups",
    )
    analyze_parser.add_argument(
        "--task-pass-rule",
        type=str,
        choices=["all", "any", "majority"],
        default="all",
        help="Task pass rule when using --aggregation-level task",
    )

    merge_parser = subparsers.add_parser("merge", help="Merge multiple runs into one consolidated output")
    merge_parser.add_argument("--run-dirs", nargs="+", help="Input run directories (2+)")
    merge_parser.add_argument("--output-dir", type=str, help="Output directory for merged artifacts")
    merge_parser.add_argument("--name", type=str, help="Optional merged run name")
    merge_parser.add_argument("--no-dedupe", action="store_true", help="Disable dedupe by scenario/task/agent/judge")

    orchestrate_parser = subparsers.add_parser("orchestrate", help="Run sharded local workers and merge outputs")
    orchestrate_parser.add_argument("--config", type=str, help="Path to Python config file")
    orchestrate_parser.add_argument("--config-json", type=str, help="Path to declarative JSON config")
    orchestrate_parser.add_argument("--strict-config", action="store_true", help="Require declarative non-Python config")
    orchestrate_parser.add_argument("--shards", type=int, required=True, help="Number of shard workers to launch")
    orchestrate_parser.add_argument("--max-workers", type=int, default=4, help="Max shard processes in parallel")
    orchestrate_parser.add_argument("--output-dir", type=str, required=True, help="Merged output directory")
    orchestrate_parser.add_argument("--name", type=str, help="Merged run base name")
    orchestrate_parser.add_argument("--runs-dir", type=str, help="Runs root for shard outputs")
    orchestrate_parser.add_argument("--artifact-backend", type=str, choices=["jsonl", "sqlite"], help="Artifact backend")
    orchestrate_parser.add_argument("--sqlite-db-name", type=str, help="SQLite DB filename when backend=sqlite")
    orchestrate_parser.add_argument("--max-retries", type=int, help="Default max retries")
    orchestrate_parser.add_argument("--retry-delay-seconds", type=float, help="Retry delay seconds")
    orchestrate_parser.add_argument("--agent-timeout-seconds", type=float, help="Agent timeout")
    orchestrate_parser.add_argument("--judge-timeout-seconds", type=float, help="Judge timeout")
    orchestrate_parser.add_argument("--max-tasks-parallel", type=int, help="Task parallelism")
    orchestrate_parser.add_argument("--max-agents-parallel", type=int, help="Agent parallelism")
    orchestrate_parser.add_argument("--max-judges-parallel", type=int, help="Judge parallelism")
    orchestrate_parser.add_argument("--seed", type=int, help="Deterministic seed")
    orchestrate_parser.add_argument("--shuffle-tasks", action="store_true", help="Shuffle tasks")
    orchestrate_parser.add_argument("--keep-going", action="store_true", help="Merge successful shards when others fail")
    orchestrate_parser.add_argument("--no-dedupe", action="store_true", help="Disable dedupe during merge")

    rank_parser = subparsers.add_parser("rank", help="Rank agents from a run with Elo")
    rank_parser.add_argument("--run-dir", type=str, help="Run directory")
    rank_parser.add_argument("--initial-rating", type=float, default=1500.0, help="Initial Elo rating")
    rank_parser.add_argument("--k-factor", type=float, default=24.0, help="Elo K-factor")
    rank_parser.add_argument("--output-json", type=str, help="Optional output path for ranking JSON")

    migrate_parser = subparsers.add_parser("migrate", help="Migrate run artifacts to target schema")
    migrate_parser.add_argument("--run-dir", type=str, help="Run directory")
    migrate_parser.add_argument("--target-schema", type=str, default="1.1.0", help="Target schema version")
    migrate_parser.add_argument("--no-backup", action="store_true", help="Do not create results backup")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    if args.command == "run":
        return cmd_run(args)
    if args.command == "summary":
        return cmd_summary(args)
    if args.command == "compare":
        return cmd_compare(args)
    if args.command == "rejudge":
        return cmd_rejudge(args)
    if args.command == "gate":
        return cmd_gate(args)
    if args.command == "analyze":
        return cmd_analyze(args)
    if args.command == "merge":
        return cmd_merge(args)
    if args.command == "orchestrate":
        return cmd_orchestrate(args)
    if args.command == "rank":
        return cmd_rank(args)
    if args.command == "migrate":
        return cmd_migrate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
