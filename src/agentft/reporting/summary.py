from typing import List, Dict, Any
from agentft.core.result import EvaluationResult


def build_summary(results: List[EvaluationResult]) -> Dict[str, Any]:
    """Build a summary dictionary from evaluation results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    per_agent = {}
    for r in results:
        per_agent.setdefault(r.agent, {"total": 0, "passed": 0})
        per_agent[r.agent]["total"] += 1
        if r.passed:
            per_agent[r.agent]["passed"] += 1

    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "per_agent": per_agent,
    }


def print_summary(summary: Dict[str, Any]) -> None:
    """Print a formatted summary table."""
    print("\n" + "=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"Total tasks: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    print("\nPer Agent:")
    print("-" * 60)
    for agent, stats in summary["per_agent"].items():
        rate = stats["passed"] / stats["total"] if stats["total"] else 0.0
        print(f"  {agent}: {stats['passed']}/{stats['total']} ({rate:.1%})")
    print("=" * 60 + "\n")

