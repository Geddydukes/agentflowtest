from typing import Dict, Any
from agentbench import Judge, Task


class ExactMatchJudge:
    """Judge that compares expected answer to actual response using exact string matching."""

    name = "exact_match"

    async def score(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score the agent output against expected answer."""
        expected = (task.expected or {}).get("answer")
        response = result.get("response")

        if expected is None:
            return {
                "scores": {},
                "pass": False,
                "explanation": "No expected answer provided on task.",
                "metadata": None,
            }

        expected_str = str(expected).strip()
        actual_str = str(response).strip()

        passed = expected_str == actual_str

        return {
            "scores": {"exact_match": 1.0 if passed else 0.0},
            "pass": passed,
            "explanation": None,
            "metadata": {"expected": expected_str, "actual": actual_str},
        }

