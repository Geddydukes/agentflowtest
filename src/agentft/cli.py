"""CLI for Agent Flow Test (AgentFT)."""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from agentft import RunConfig, run, build_math_basic_scenario, ExactMatchJudge
from agentft.core.agent import AgentAdapter
from agentft.core.scenario import Scenario
from agentft.core.judge import Judge


def cmd_run(args: argparse.Namespace) -> int:
    """Run an evaluation."""
    print("Agent Flow Test (AgentFT) - Run Command")
    print("=" * 50)
    
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            return 1
        
        print(f"Loading config from: {config_path}")
        
        config_globals = {}
        config_locals = {}
        with open(config_path) as f:
            exec(f.read(), config_globals, config_locals)
        
        if 'config' not in config_locals:
            print("Error: Config file must define a 'config' variable of type RunConfig")
            return 1
        
        config = config_locals['config']
        results = run(config)
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        print(f"\nResults: {passed} / {total} tasks passed")
        
        if results:
            run_id = results[0].run_id
            print(f"Run directory: runs/{run_id}/")
            print("  - results.jsonl")
            print("  - traces.jsonl")
            print("  - run_metadata.json")
            print("  - report.html")
        
        return 0
    else:
        print("Error: --config is required")
        print("Usage: aft run --config <path_to_config.py>")
        return 1


def cmd_summary(args: argparse.Namespace) -> int:
    """Show summary of a run."""
    print("Agent Flow Test (AgentFT) - Summary Command")
    print("=" * 50)
    
    if not args.run_dir:
        print("Error: --run-dir is required")
        return 1
    
    run_dir = Path(args.run_dir)
    results_path = run_dir / "results.jsonl"
    
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}")
        return 1
    
    import json
    from agentft.reporting.summary import build_summary, print_summary
    from agentft.core.result import EvaluationResult
    
    results = []
    with open(results_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                from agentft.core.cost import Cost
                cost = None
                if data.get("cost"):
                    cost = Cost(**data["cost"])
                
                from datetime import datetime
                result = EvaluationResult(
                    run_id=data["run_id"],
                    task_id=data["task_id"],
                    scenario=data["scenario"],
                    agent=data["agent"],
                    judge=data["judge"],
                    raw_input=data["raw_input"],
                    agent_output=data["agent_output"],
                    scores=data["scores"],
                    passed=data["passed"],
                    cost=cost,
                    error=data.get("error"),
                    error_type=data.get("error_type"),
                    retries_attempted=data.get("retries_attempted", 0),
                )
                results.append(result)
    
    summary = build_summary(results)
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
    
    print(f"\nRegressions: {len(comparison['regressions'])}")
    print(f"Improvements: {len(comparison['improvements'])}")
    
    if comparison['regressions']:
        print("\nRegressions:")
        for reg in comparison['regressions'][:5]:
            print(f"  - Task {reg['task_id']} ({reg['agent']})")
    
    if comparison['improvements']:
        print("\nImprovements:")
        for imp in comparison['improvements'][:5]:
            print(f"  - Task {imp['task_id']} ({imp['agent']})")
    
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="aft",
        description="Agent Flow Test (AgentFT) - AI agent evaluation framework",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    run_parser = subparsers.add_parser("run", help="Run an evaluation")
    run_parser.add_argument(
        "--config",
        type=str,
        help="Path to Python config file that defines a RunConfig",
    )
    
    summary_parser = subparsers.add_parser("summary", help="Show summary of a run")
    summary_parser.add_argument(
        "--run-dir",
        type=str,
        help="Path to run directory",
    )
    
    compare_parser = subparsers.add_parser("compare", help="Compare two runs")
    compare_parser.add_argument(
        "--run-a",
        type=str,
        help="Path to first run directory",
    )
    compare_parser.add_argument(
        "--run-b",
        type=str,
        help="Path to second run directory",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "summary":
        return cmd_summary(args)
    elif args.command == "compare":
        return cmd_compare(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

