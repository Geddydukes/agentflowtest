from typing import Protocol, Iterable, List
from .task import Task


class Scenario(Protocol):
    name: str

    def iter_tasks(self) -> Iterable[Task]:
        ...


class ListScenario:
    """Simple scenario backed by an in memory list of tasks."""

    def __init__(self, name: str, tasks: List[Task]) -> None:
        self.name = name
        self._tasks = tasks

    def iter_tasks(self) -> Iterable[Task]:
        return list(self._tasks)

