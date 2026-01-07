import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_results_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load results from a JSONL file."""
    results = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def compare_runs(run_a_dir: str, run_b_dir: str) -> Dict[str, Any]:
    """
    Load two run directories and compute basic comparison metrics:

    - overall pass rates
    - per agent pass rates
    - regressions (pass -> fail)
    - improvements (fail -> pass)
    """
    run_a_path = Path(run_a_dir)
    run_b_path = Path(run_b_dir)

    results_a = load_results_jsonl(str(run_a_path / "results.jsonl"))
    results_b = load_results_jsonl(str(run_b_path / "results.jsonl"))

    def key_func(r: Dict[str, Any]) -> Tuple[str, str, str]:
        return (r["task_id"], r["agent"], r["judge"])

    results_a_dict = {key_func(r): r for r in results_a}
    results_b_dict = {key_func(r): r for r in results_b}

    all_keys = set(results_a_dict.keys()) | set(results_b_dict.keys())

    regressions = []
    improvements = []
    unchanged_pass = []
    unchanged_fail = []

    for key in all_keys:
        result_a = results_a_dict.get(key)
        result_b = results_b_dict.get(key)

        if result_a and result_b:
            passed_a = result_a.get("passed", False)
            passed_b = result_b.get("passed", False)

            if passed_a and not passed_b:
                regressions.append({
                    "task_id": key[0],
                    "agent": key[1],
                    "judge": key[2],
                    "run_a": result_a,
                    "run_b": result_b,
                })
            elif not passed_a and passed_b:
                improvements.append({
                    "task_id": key[0],
                    "agent": key[1],
                    "judge": key[2],
                    "run_a": result_a,
                    "run_b": result_b,
                })
            elif passed_a and passed_b:
                unchanged_pass.append(key)
            else:
                unchanged_fail.append(key)

    def compute_pass_rate(results: List[Dict[str, Any]]) -> float:
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.get("passed", False))
        return passed / len(results)

    def compute_per_agent_stats(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        per_agent = {}
        for r in results:
            agent = r["agent"]
            if agent not in per_agent:
                per_agent[agent] = {"total": 0, "passed": 0}
            per_agent[agent]["total"] += 1
            if r.get("passed", False):
                per_agent[agent]["passed"] += 1
        return per_agent

    return {
        "run_a": {
            "dir": run_a_dir,
            "total": len(results_a),
            "passed": sum(1 for r in results_a if r.get("passed", False)),
            "pass_rate": compute_pass_rate(results_a),
            "per_agent": compute_per_agent_stats(results_a),
        },
        "run_b": {
            "dir": run_b_dir,
            "total": len(results_b),
            "passed": sum(1 for r in results_b if r.get("passed", False)),
            "pass_rate": compute_pass_rate(results_b),
            "per_agent": compute_per_agent_stats(results_b),
        },
        "regressions": regressions,
        "improvements": improvements,
        "unchanged_pass": len(unchanged_pass),
        "unchanged_fail": len(unchanged_fail),
    }

