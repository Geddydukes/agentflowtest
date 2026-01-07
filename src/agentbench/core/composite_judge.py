from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .task import Task
from .judge import Judge


@dataclass
class CompositeJudge:
    """Composite judge that combines multiple judges with a strategy."""

    judges: List[Judge]
    strategy: str = "all"
    weights: Optional[Dict[str, float]] = None

    @property
    def name(self) -> str:
        """Generate a name from the composite judges."""
        judge_names = [j.name for j in self.judges]
        return f"composite[{','.join(judge_names)}]"

    async def score(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """Score using all child judges and combine according to strategy."""
        sub_results = []

        for judge in self.judges:
            try:
                sub_result = await judge.score(task, result)
                sub_results.append({
                    "judge": judge.name,
                    "result": sub_result,
                })
            except Exception as e:
                sub_results.append({
                    "judge": judge.name,
                    "error": str(e),
                    "result": {
                        "scores": {},
                        "pass": False,
                        "explanation": None,
                        "metadata": None,
                    },
                })

        combined = self._combine_results(sub_results)

        return {
            "scores": combined["scores"],
            "pass": combined["pass"],
            "explanation": combined.get("explanation"),
            "metadata": {
                "strategy": self.strategy,
                "sub_judges": sub_results,
            },
        }

    def _combine_results(self, sub_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine sub-judge results according to strategy."""
        if not sub_results:
            return {"scores": {}, "pass": False}

        if self.strategy == "all":
            all_passed = all(
                sub["result"].get("pass", False) for sub in sub_results
            )
            combined_scores = self._merge_scores([sub["result"].get("scores", {}) for sub in sub_results])
            return {"scores": combined_scores, "pass": all_passed}

        elif self.strategy == "any":
            any_passed = any(
                sub["result"].get("pass", False) for sub in sub_results
            )
            combined_scores = self._merge_scores([sub["result"].get("scores", {}) for sub in sub_results])
            return {"scores": combined_scores, "pass": any_passed}

        elif self.strategy == "weighted":
            if not self.weights:
                return self._combine_results(sub_results)  # Fallback to "all"
            weighted_scores = {}
            total_weight = 0.0
            all_passed = True

            for sub in sub_results:
                judge_name = sub["judge"]
                weight = self.weights.get(judge_name, 1.0)
                total_weight += weight
                sub_scores = sub["result"].get("scores", {})
                sub_passed = sub["result"].get("pass", False)

                if not sub_passed:
                    all_passed = False

                for key, value in sub_scores.items():
                    if key not in weighted_scores:
                        weighted_scores[key] = 0.0
                    weighted_scores[key] += value * weight

            if total_weight > 0:
                for key in weighted_scores:
                    weighted_scores[key] /= total_weight

            return {"scores": weighted_scores, "pass": all_passed}

        elif self.strategy == "sequential":
            for sub in sub_results:
                if sub["result"].get("pass", False):
                    return {
                        "scores": sub["result"].get("scores", {}),
                        "pass": True,
                    }
            return {
                "scores": sub_results[-1]["result"].get("scores", {}),
                "pass": False,
            }

        elif self.strategy == "best_of_n":
            best_score = -float("inf")
            best_result = None

            for sub in sub_results:
                sub_scores = sub["result"].get("scores", {})
                total_score = sum(sub_scores.values()) if sub_scores else 0.0
                if total_score > best_score:
                    best_score = total_score
                    best_result = sub["result"]

            if best_result:
                return {
                    "scores": best_result.get("scores", {}),
                    "pass": best_result.get("pass", False),
                }

        return {"scores": {}, "pass": False}

    def _merge_scores(self, score_dicts: List[Dict[str, float]]) -> Dict[str, float]:
        """Merge multiple score dictionaries, averaging values for duplicate keys."""
        merged = {}
        counts = {}

        for scores in score_dicts:
            for key, value in scores.items():
                if key not in merged:
                    merged[key] = 0.0
                    counts[key] = 0
                merged[key] += value
                counts[key] += 1

        for key in merged:
            if counts[key] > 0:
                merged[key] /= counts[key]

        return merged

