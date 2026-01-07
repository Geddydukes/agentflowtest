from typing import Protocol, Dict, Any
from .task import Task


class Judge(Protocol):
    """Judge interface for scoring agent outputs."""

    name: str

    async def score(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expected return structure:
        {
            "scores": {"metric_name": float, ...},
            "pass": bool,
            "explanation": str | None,
            "metadata": dict | None,
        }
        """
        ...

