import csv
import json
from pathlib import Path
from typing import Iterable, Any
import random
from collections import defaultdict

from agentft.core.task import Task


class CSVScenario:
    """
    Scenario backed by a CSV file.

    Each row becomes a task.
    """

    def __init__(
        self,
        name: str,
        csv_path: str,
        id_column: str | None = None,
        expected_column: str | None = None,
        input_columns: list[str] | None = None,
        metadata_columns: list[str] | None = None,
        sample_size: int | None = None,
        sample_seed: int = 42,
        stratify_by: str | None = None,
    ) -> None:
        self.name = name
        self.csv_path = csv_path
        self.id_column = id_column
        self.expected_column = expected_column
        self.input_columns = input_columns
        self.metadata_columns = metadata_columns or []
        self.sample_size = sample_size
        self.sample_seed = sample_seed
        self.stratify_by = stratify_by

    def iter_tasks(self) -> Iterable[Task]:
        path = Path(self.csv_path)
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            rows = _sample_rows(rows, self.sample_size, self.sample_seed, self.stratify_by)
            for idx, row in enumerate(rows):
                task_id = row[self.id_column] if self.id_column else str(idx)
                expected = {"answer": row[self.expected_column]} if self.expected_column and self.expected_column in row else None
                metadata = {col: row.get(col) for col in self.metadata_columns} if self.metadata_columns else None

                if self.input_columns:
                    task_input = {col: row.get(col) for col in self.input_columns}
                else:
                    excluded = set([self.id_column, self.expected_column, *self.metadata_columns])
                    task_input = {k: v for k, v in row.items() if k not in excluded}

                yield Task(
                    id=str(task_id),
                    input=task_input,
                    expected=expected,
                    metadata=metadata,
                )


class JSONLScenario:
    """
    Scenario backed by a JSONL file.

    Each JSON object becomes a task.
    """

    def __init__(
        self,
        name: str,
        jsonl_path: str,
        id_field: str = "id",
        input_field: str = "input",
        expected_field: str | None = "expected",
        metadata_field: str | None = "metadata",
        sample_size: int | None = None,
        sample_seed: int = 42,
        stratify_by: str | None = None,
    ) -> None:
        self.name = name
        self.jsonl_path = jsonl_path
        self.id_field = id_field
        self.input_field = input_field
        self.expected_field = expected_field
        self.metadata_field = metadata_field
        self.sample_size = sample_size
        self.sample_seed = sample_seed
        self.stratify_by = stratify_by

    def iter_tasks(self) -> Iterable[Task]:
        path = Path(self.jsonl_path)
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rows.append(json.loads(line))

        rows = _sample_rows(rows, self.sample_size, self.sample_seed, self.stratify_by)
        for idx, row in enumerate(rows):
            task_id = str(row.get(self.id_field, idx))
            task_input = row.get(self.input_field, {})
            expected = row.get(self.expected_field) if self.expected_field else None
            metadata = row.get(self.metadata_field) if self.metadata_field else None
            yield Task(
                id=task_id,
                input=task_input,
                expected=expected,
                metadata=metadata,
            )


class HuggingFaceScenario:
    """
    Scenario backed by a Hugging Face dataset split.

    Requires `datasets` to be installed.
    """

    def __init__(
        self,
        name: str,
        dataset_name: str,
        split: str = "test",
        id_field: str | None = None,
        input_fields: list[str] | None = None,
        expected_field: str | None = None,
        metadata_fields: list[str] | None = None,
        sample_size: int | None = None,
        sample_seed: int = 42,
        stratify_by: str | None = None,
    ) -> None:
        self.name = name
        self.dataset_name = dataset_name
        self.split = split
        self.id_field = id_field
        self.input_fields = input_fields or []
        self.expected_field = expected_field
        self.metadata_fields = metadata_fields or []
        self.sample_size = sample_size
        self.sample_seed = sample_seed
        self.stratify_by = stratify_by

    def iter_tasks(self) -> Iterable[Task]:
        try:
            from datasets import load_dataset
        except Exception as e:
            raise ImportError("HuggingFaceScenario requires `datasets` package.") from e

        ds = list(load_dataset(self.dataset_name, split=self.split))
        ds = _sample_rows(ds, self.sample_size, self.sample_seed, self.stratify_by)
        for idx, row in enumerate(ds):
            task_id = str(row[self.id_field]) if self.id_field else str(idx)
            task_input = {k: row.get(k) for k in self.input_fields} if self.input_fields else dict(row)
            expected = {"answer": row.get(self.expected_field)} if self.expected_field else None
            metadata = {k: row.get(k) for k in self.metadata_fields} if self.metadata_fields else None
            yield Task(
                id=task_id,
                input=task_input,
                expected=expected,
                metadata=metadata,
            )


def _sample_rows(rows: list[dict], sample_size: int | None, sample_seed: int, stratify_by: str | None) -> list[dict]:
    if not rows or sample_size is None or sample_size <= 0 or sample_size >= len(rows):
        return rows

    rng = random.Random(sample_seed)
    if not stratify_by:
        idxs = list(range(len(rows)))
        rng.shuffle(idxs)
        keep = set(idxs[:sample_size])
        return [row for i, row in enumerate(rows) if i in keep]

    groups: dict[Any, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row.get(stratify_by)].append(row)

    total = len(rows)
    sampled: list[dict] = []
    remainders: list[tuple[float, Any]] = []
    allocated = 0

    for key, items in groups.items():
        exact = sample_size * (len(items) / total)
        take = int(exact)
        allocated += take
        remainders.append((exact - take, key))
        pool = list(items)
        rng.shuffle(pool)
        sampled.extend(pool[:take])

    remaining = sample_size - allocated
    remainders.sort(reverse=True, key=lambda x: x[0])
    for _, key in remainders:
        if remaining <= 0:
            break
        already = [r for r in sampled if r.get(stratify_by) == key]
        capacity = len(groups[key]) - len(already)
        if capacity <= 0:
            continue
        pool = [r for r in groups[key] if r not in already]
        rng.shuffle(pool)
        take = min(remaining, capacity)
        sampled.extend(pool[:take])
        remaining -= take

    if len(sampled) < sample_size:
        leftovers = [r for r in rows if r not in sampled]
        rng.shuffle(leftovers)
        sampled.extend(leftovers[: (sample_size - len(sampled))])

    rng.shuffle(sampled)
    return sampled[:sample_size]
