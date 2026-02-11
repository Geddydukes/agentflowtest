import json
import math
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

from agentft.engine.storage import load_results_from_run_dir


def load_results_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load results from a JSONL file."""
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def _pass_rate(results: List[Dict[str, Any]]) -> float:
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.get("passed", False))
    return passed / len(results)


def _per_agent_stats(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    per_agent: Dict[str, Dict[str, Any]] = {}
    for r in results:
        agent = r["agent"]
        if agent not in per_agent:
            per_agent[agent] = {"total": 0, "passed": 0, "pass_rate": 0.0}
        per_agent[agent]["total"] += 1
        if r.get("passed", False):
            per_agent[agent]["passed"] += 1

    for agent in per_agent:
        total = per_agent[agent]["total"]
        per_agent[agent]["pass_rate"] = per_agent[agent]["passed"] / total if total else 0.0
    return per_agent


def _bootstrap_delta_ci(
    pass_a: List[int],
    pass_b: List[int],
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> Tuple[float, float]:
    if not pass_a or not pass_b:
        return (0.0, 0.0)
    rng = random.Random(seed)
    deltas = []
    for _ in range(n_bootstrap):
        sample_a = [pass_a[rng.randrange(len(pass_a))] for _ in range(len(pass_a))]
        sample_b = [pass_b[rng.randrange(len(pass_b))] for _ in range(len(pass_b))]
        deltas.append((sum(sample_b) / len(sample_b)) - (sum(sample_a) / len(sample_a)))
    deltas.sort()
    low_idx = int(0.025 * (n_bootstrap - 1))
    high_idx = int(0.975 * (n_bootstrap - 1))
    return (deltas[low_idx], deltas[high_idx])


def _two_proportion_p_value(pass_a: int, total_a: int, pass_b: int, total_b: int) -> float | None:
    if total_a == 0 or total_b == 0:
        return None
    p1 = pass_a / total_a
    p2 = pass_b / total_b
    pooled = (pass_a + pass_b) / (total_a + total_b)
    se = math.sqrt(pooled * (1.0 - pooled) * ((1 / total_a) + (1 / total_b)))
    if se == 0:
        return 1.0
    z = (p2 - p1) / se
    # Two-sided p-value from normal CDF using erf
    cdf = 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))
    return max(0.0, min(1.0, 2.0 * (1.0 - cdf)))


def compare_runs(run_a_dir: str, run_b_dir: str) -> Dict[str, Any]:
    """
    Load two run directories and compute comparison metrics:

    - overall pass rates and deltas
    - confidence interval and p-value for pass-rate delta
    - per-agent pass rates
    - regressions/improvements
    - rows missing in either run
    """
    def to_row(r):
        if isinstance(r, dict):
            return r
        return {
            "run_id": r.run_id,
            "task_id": r.task_id,
            "scenario": r.scenario,
            "agent": r.agent,
            "judge": r.judge,
            "raw_input": r.raw_input,
            "agent_output": r.agent_output,
            "scores": r.scores,
            "passed": r.passed,
            "latency_ms": r.latency_ms,
            "metadata": r.metadata,
            "cost": {
                "total_usd": r.cost.total_usd,
                "breakdown": r.cost.breakdown,
                "model": r.cost.model,
            } if r.cost else None,
            "error": r.error,
            "error_type": r.error_type,
            "retries_attempted": r.retries_attempted,
            "created_at": r.created_at.isoformat(),
        }

    def load_rows(run_dir: str) -> List[Dict[str, Any]]:
        try:
            return [to_row(r) for r in load_results_from_run_dir(run_dir)]
        except Exception:
            path = Path(run_dir) / "results.jsonl"
            return load_results_jsonl(str(path))

    results_a = load_rows(run_a_dir)
    results_b = load_rows(run_b_dir)

    def key_func(r: Dict[str, Any]) -> Tuple[str, str, str, str]:
        return (r.get("scenario", ""), r["task_id"], r["agent"], r["judge"])

    results_a_dict = {key_func(r): r for r in results_a}
    results_b_dict = {key_func(r): r for r in results_b}
    all_keys = set(results_a_dict.keys()) | set(results_b_dict.keys())

    regressions = []
    improvements = []
    unchanged_pass = []
    unchanged_fail = []
    missing_in_b = []
    missing_in_a = []

    for key in all_keys:
        result_a = results_a_dict.get(key)
        result_b = results_b_dict.get(key)

        if result_a and result_b:
            passed_a = result_a.get("passed", False)
            passed_b = result_b.get("passed", False)

            if passed_a and not passed_b:
                regressions.append({
                    "scenario": key[0],
                    "task_id": key[1],
                    "agent": key[2],
                    "judge": key[3],
                    "run_a": result_a,
                    "run_b": result_b,
                })
            elif not passed_a and passed_b:
                improvements.append({
                    "scenario": key[0],
                    "task_id": key[1],
                    "agent": key[2],
                    "judge": key[3],
                    "run_a": result_a,
                    "run_b": result_b,
                })
            elif passed_a and passed_b:
                unchanged_pass.append(key)
            else:
                unchanged_fail.append(key)
        elif result_a and not result_b:
            missing_in_b.append({
                "scenario": key[0],
                "task_id": key[1],
                "agent": key[2],
                "judge": key[3],
                "run_a": result_a,
            })
        elif result_b and not result_a:
            missing_in_a.append({
                "scenario": key[0],
                "task_id": key[1],
                "agent": key[2],
                "judge": key[3],
                "run_b": result_b,
            })

    pass_a = [1 if r.get("passed", False) else 0 for r in results_a]
    pass_b = [1 if r.get("passed", False) else 0 for r in results_b]
    delta = _pass_rate(results_b) - _pass_rate(results_a)
    ci_low, ci_high = _bootstrap_delta_ci(pass_a, pass_b)
    p_value = _two_proportion_p_value(sum(pass_a), len(pass_a), sum(pass_b), len(pass_b))

    per_agent_a = _per_agent_stats(results_a)
    per_agent_b = _per_agent_stats(results_b)
    all_agents = set(per_agent_a.keys()) | set(per_agent_b.keys())
    per_agent_delta = {}
    for agent in all_agents:
        rate_a = per_agent_a.get(agent, {}).get("pass_rate", 0.0)
        rate_b = per_agent_b.get(agent, {}).get("pass_rate", 0.0)
        per_agent_delta[agent] = {
            "pass_rate_a": rate_a,
            "pass_rate_b": rate_b,
            "delta_pass_rate": rate_b - rate_a,
        }

    return {
        "run_a": {
            "dir": run_a_dir,
            "total": len(results_a),
            "passed": sum(pass_a),
            "pass_rate": _pass_rate(results_a),
            "per_agent": per_agent_a,
        },
        "run_b": {
            "dir": run_b_dir,
            "total": len(results_b),
            "passed": sum(pass_b),
            "pass_rate": _pass_rate(results_b),
            "per_agent": per_agent_b,
        },
        "delta_pass_rate": delta,
        "delta_pass_rate_ci_95": [ci_low, ci_high],
        "p_value": p_value,
        "per_agent_delta": per_agent_delta,
        "regressions": regressions,
        "improvements": improvements,
        "unchanged_pass": len(unchanged_pass),
        "unchanged_fail": len(unchanged_fail),
        "missing_in_run_b": missing_in_b,
        "missing_in_run_a": missing_in_a,
    }
