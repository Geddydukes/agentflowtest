from typing import Protocol, Dict, Any
from .task import Task


class AgentAdapter(Protocol):
    """Adapter interface for agents under evaluation."""

    name: str
    version: str
    provider_key: str | None

    async def setup(self) -> None:
        """Called once before any tasks for that agent."""
        ...

    async def reset(self) -> None:
        """Called before each scenario."""
        ...

    async def teardown(self) -> None:
        """Called after all tasks are complete."""
        ...

    async def run_task(self, task: Task, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Execute the agent for a single task.

        Returns a dict with at least:
        - "response": the agent output (string or structured)
        """
        ...

