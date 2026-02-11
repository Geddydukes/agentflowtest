from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Any

from agentft.core.result import EvaluationResult
from agentft.reporting.summary import build_summary


def _group_stats(results: list[EvaluationResult], key_fn) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[EvaluationResult]] = defaultdict(list)
    for r in results:
        grouped[key_fn(r)].append(r)

    out: dict[str, dict[str, Any]] = {}
    for key, rows in grouped.items():
        total = len(rows)
        passed = sum(1 for r in rows if r.passed)
        total_cost = sum(r.cost.total_usd for r in rows if r.cost)
        latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
        out[key] = {
            "total": total,
            "passed": passed,
            "pass_rate": (passed / total) if total else 0.0,
            "total_cost_usd": total_cost,
            "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else None,
        }
    return out


def _wilson_interval_95(successes: int, total: int) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    phat = successes / total
    denom = 1 + (z * z / total)
    center = (phat + (z * z / (2 * total))) / denom
    margin = z * sqrt((phat * (1 - phat) + (z * z / (4 * total))) / total) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def analyze_results(
    results: list[EvaluationResult],
    aggregation_level: str = "judge",
    task_pass_rule: str = "all",
) -> dict[str, Any]:
    summary = build_summary(
        results,
        aggregation_level=aggregation_level,
        task_pass_rule=task_pass_rule,
    )
    total = summary["total"]
    passed = summary["passed"]

    per_agent = _group_stats(results, lambda r: r.agent)
    per_scenario = _group_stats(results, lambda r: r.scenario)
    per_judge = _group_stats(results, lambda r: r.judge)

    macro_pass_rate_scenario = 0.0
    if per_scenario:
        macro_pass_rate_scenario = sum(v["pass_rate"] for v in per_scenario.values()) / len(per_scenario)

    return {
        "total": total,
        "passed": passed,
        "pass_rate": summary["pass_rate"],
        "pass_rate_ci_95_wilson": _wilson_interval_95(passed, total),
        "total_cost_usd": summary["total_cost_usd"],
        "avg_latency_ms": summary["avg_latency_ms"],
        "latency_percentiles_ms": summary.get("latency_percentiles_ms", {}),
        "macro_pass_rate_scenario": macro_pass_rate_scenario,
        "aggregation_level": aggregation_level,
        "task_pass_rule": task_pass_rule,
        "per_error_type": summary.get("per_error_type", {}),
        "per_agent": per_agent,
        "per_scenario": per_scenario,
        "per_judge": per_judge,
        "summary": summary,
    }
