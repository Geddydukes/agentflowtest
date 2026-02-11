from __future__ import annotations

from collections import defaultdict
from typing import Any

from agentft.core.result import EvaluationResult


def _task_pass(passes: list[bool], rule: str) -> bool:
    if not passes:
        return False
    if rule == "any":
        return any(passes)
    if rule == "majority":
        return sum(1 for p in passes if p) > (len(passes) / 2.0)
    return all(passes)


def _aggregate_to_task_level(results: list[EvaluationResult], task_pass_rule: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[EvaluationResult]] = defaultdict(list)
    for row in results:
        grouped[(row.scenario, row.task_id, row.agent)].append(row)

    out: list[dict[str, Any]] = []
    for (scenario, task_id, agent), rows in grouped.items():
        latencies = [r.latency_ms for r in rows if r.latency_ms is not None]
        total_cost = sum(r.cost.total_usd for r in rows if r.cost)
        errors = [r.error_type for r in rows if r.error_type]
        out.append(
            {
                "scenario": scenario,
                "task_id": task_id,
                "agent": agent,
                "judge_count": len(rows),
                "passed": _task_pass([r.passed for r in rows], task_pass_rule),
                "latency_ms": (sum(latencies) / len(latencies)) if latencies else None,
                "cost_usd": total_cost,
                "error_types": errors,
            }
        )
    return out


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    total_cost = sum(float(r.get("cost_usd", 0.0) or 0.0) for r in rows)
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]

    per_agent: dict[str, dict[str, Any]] = {}
    per_scenario: dict[str, dict[str, Any]] = {}
    for row in rows:
        for bucket, key in ((per_agent, row["agent"]), (per_scenario, row["scenario"])):
            if key not in bucket:
                bucket[key] = {"total": 0, "passed": 0, "total_cost_usd": 0.0, "_latencies": []}
            bucket[key]["total"] += 1
            if row["passed"]:
                bucket[key]["passed"] += 1
            bucket[key]["total_cost_usd"] += float(row.get("cost_usd", 0.0) or 0.0)
            if row.get("latency_ms") is not None:
                bucket[key]["_latencies"].append(row["latency_ms"])

    for bucket in (per_agent, per_scenario):
        for stats in bucket.values():
            lats = stats.pop("_latencies")
            stats["pass_rate"] = (stats["passed"] / stats["total"]) if stats["total"] else 0.0
            stats["avg_latency_ms"] = (sum(lats) / len(lats)) if lats else None

    per_error_type: dict[str, int] = {}
    for row in rows:
        for error_type in row.get("error_types", []):
            per_error_type[error_type] = per_error_type.get(error_type, 0) + 1

    latency_percentiles = {}
    if latencies:
        ordered = sorted(latencies)
        latency_percentiles = {
            "p50": ordered[int(0.50 * (len(ordered) - 1))],
            "p95": ordered[int(0.95 * (len(ordered) - 1))],
            "p99": ordered[int(0.99 * (len(ordered) - 1))],
        }

    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "total_cost_usd": total_cost,
        "avg_latency_ms": (sum(latencies) / len(latencies)) if latencies else None,
        "latency_percentiles_ms": latency_percentiles,
        "per_agent": per_agent,
        "per_scenario": per_scenario,
        "per_error_type": per_error_type,
    }


def build_summary(
    results: list[EvaluationResult],
    aggregation_level: str = "judge",
    task_pass_rule: str = "all",
) -> dict[str, Any]:
    """Build summary statistics from evaluation results."""
    rows = []
    if aggregation_level == "task":
        rows = _aggregate_to_task_level(results, task_pass_rule=task_pass_rule)
    else:
        rows = [
            {
                "scenario": r.scenario,
                "task_id": r.task_id,
                "agent": r.agent,
                "passed": r.passed,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost.total_usd if r.cost else 0.0,
                "error_types": [r.error_type] if r.error_type else [],
            }
            for r in results
        ]

    summary = _summarize_rows(rows)
    summary["aggregation_level"] = aggregation_level
    summary["task_pass_rule"] = task_pass_rule
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    """Print a formatted summary table."""
    print("\n" + "=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"Aggregation level: {summary.get('aggregation_level', 'judge')}")
    if summary.get("aggregation_level") == "task":
        print(f"Task pass rule: {summary.get('task_pass_rule', 'all')}")
    print(f"Total tasks: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    print(f"Total cost (USD): ${float(summary.get('total_cost_usd', 0.0)):.6f}")
    avg_latency = summary.get("avg_latency_ms")
    if avg_latency is not None:
        print(f"Avg latency (ms): {avg_latency:.2f}")
    if summary.get("latency_percentiles_ms"):
        p = summary["latency_percentiles_ms"]
        print(f"Latency p50/p95/p99 (ms): {p['p50']:.2f} / {p['p95']:.2f} / {p['p99']:.2f}")

    print("\nPer Agent:")
    print("-" * 60)
    for agent, stats in summary.get("per_agent", {}).items():
        rate = stats["passed"] / stats["total"] if stats["total"] else 0.0
        extras = [f"cost=${stats.get('total_cost_usd', 0.0):.6f}"]
        if stats.get("avg_latency_ms") is not None:
            extras.append(f"avg_latency_ms={stats['avg_latency_ms']:.2f}")
        print(f"  {agent}: {stats['passed']}/{stats['total']} ({rate:.1%}) [{' | '.join(extras)}]")
    print("=" * 60 + "\n")
