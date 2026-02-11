"""Tests for dataset-backed scenarios."""

import json

from agentft.scenarios.datasets import CSVScenario, JSONLScenario


def test_csv_scenario(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "id,prompt,answer,difficulty\n"
        "1,What is 2+2?,4,easy\n"
        "2,What is 3+3?,6,easy\n",
        encoding="utf-8",
    )
    scenario = CSVScenario(
        name="csv_test",
        csv_path=str(csv_path),
        id_column="id",
        expected_column="answer",
        input_columns=["prompt"],
        metadata_columns=["difficulty"],
    )
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 2
    assert tasks[0].id == "1"
    assert tasks[0].input["prompt"] == "What is 2+2?"
    assert tasks[0].expected == {"answer": "4"}
    assert tasks[0].metadata == {"difficulty": "easy"}


def test_jsonl_scenario(tmp_path):
    jsonl_path = tmp_path / "data.jsonl"
    rows = [
        {"id": "a", "input": {"prompt": "p1"}, "expected": {"answer": "x"}, "metadata": {"m": 1}},
        {"id": "b", "input": {"prompt": "p2"}, "expected": {"answer": "y"}, "metadata": {"m": 2}},
    ]
    jsonl_path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    scenario = JSONLScenario(name="jsonl_test", jsonl_path=str(jsonl_path))
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 2
    assert tasks[0].id == "a"
    assert tasks[1].input["prompt"] == "p2"


def test_csv_scenario_sampling_and_stratification(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "id,prompt,answer,split\n"
        "1,p1,a,test\n"
        "2,p2,a,test\n"
        "3,p3,a,test\n"
        "4,p4,b,train\n"
        "5,p5,b,train\n"
        "6,p6,b,train\n",
        encoding="utf-8",
    )
    scenario = CSVScenario(
        name="csv_sampled",
        csv_path=str(csv_path),
        id_column="id",
        expected_column="answer",
        input_columns=["prompt"],
        sample_size=4,
        sample_seed=123,
        stratify_by="split",
    )
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 4
    test_count = sum(1 for t in tasks if t.id in {"1", "2", "3"})
    train_count = sum(1 for t in tasks if t.id in {"4", "5", "6"})
    assert test_count == 2
    assert train_count == 2


def test_jsonl_scenario_sampling_deterministic(tmp_path):
    jsonl_path = tmp_path / "data.jsonl"
    rows = [
        {"id": str(i), "input": {"prompt": f"p{i}"}, "expected": {"answer": str(i)}, "group": "g1" if i < 5 else "g2"}
        for i in range(10)
    ]
    jsonl_path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    s1 = JSONLScenario(
        name="j1",
        jsonl_path=str(jsonl_path),
        sample_size=5,
        sample_seed=77,
        stratify_by="group",
    )
    s2 = JSONLScenario(
        name="j2",
        jsonl_path=str(jsonl_path),
        sample_size=5,
        sample_seed=77,
        stratify_by="group",
    )
    ids1 = [t.id for t in s1.iter_tasks()]
    ids2 = [t.id for t in s2.iter_tasks()]
    assert ids1 == ids2
