"""Tests for preset scenarios and judges."""

import pytest
from agentft import build_math_basic_scenario, ExactMatchJudge, Task


def test_build_math_basic_scenario():
    """Test build_math_basic_scenario returns a valid scenario."""
    scenario = build_math_basic_scenario()
    assert scenario.name == "math_basic"
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 4
    assert all(isinstance(t, Task) for t in tasks)
    
    task_ids = [t.id for t in tasks]
    assert "add_2_3" in task_ids
    assert "mul_4_7" in task_ids
    assert "sub_10_4" in task_ids
    assert "div_15_3" in task_ids


def test_math_basic_scenario_tasks_have_expected():
    """Test that math scenario tasks have expected answers."""
    scenario = build_math_basic_scenario()
    tasks = list(scenario.iter_tasks())
    
    for task in tasks:
        assert task.expected is not None
        assert "answer" in task.expected
        assert task.input is not None
        assert "prompt" in task.input


@pytest.mark.asyncio
async def test_exact_match_judge_passes():
    """Test ExactMatchJudge with matching answer."""
    judge = ExactMatchJudge()
    task = Task(
        id="test",
        input={"prompt": "What is 2+2?"},
        expected={"answer": "4"},
    )
    result = {"response": "4"}
    
    score = await judge.score(task, result)
    assert score["pass"] is True
    assert score["scores"]["exact_match"] == 1.0


@pytest.mark.asyncio
async def test_exact_match_judge_fails():
    """Test ExactMatchJudge with non-matching answer."""
    judge = ExactMatchJudge()
    task = Task(
        id="test",
        input={"prompt": "What is 2+2?"},
        expected={"answer": "4"},
    )
    result = {"response": "5"}
    
    score = await judge.score(task, result)
    assert score["pass"] is False
    assert score["scores"]["exact_match"] == 0.0


@pytest.mark.asyncio
async def test_exact_match_judge_strips_whitespace():
    """Test ExactMatchJudge handles whitespace correctly."""
    judge = ExactMatchJudge()
    task = Task(
        id="test",
        input={"prompt": "What is 2+2?"},
        expected={"answer": "4"},
    )
    result = {"response": "  4  "}
    
    score = await judge.score(task, result)
    assert score["pass"] is True


@pytest.mark.asyncio
async def test_exact_match_judge_no_expected():
    """Test ExactMatchJudge when no expected answer is provided."""
    judge = ExactMatchJudge()
    task = Task(
        id="test",
        input={"prompt": "What is 2+2?"},
        expected=None,
    )
    result = {"response": "4"}
    
    score = await judge.score(task, result)
    assert score["pass"] is False
    assert "No expected answer provided" in score["explanation"]


@pytest.mark.asyncio
async def test_exact_match_judge_metadata():
    """Test ExactMatchJudge includes metadata."""
    judge = ExactMatchJudge()
    task = Task(
        id="test",
        input={"prompt": "What is 2+2?"},
        expected={"answer": "4"},
    )
    result = {"response": "4"}
    
    score = await judge.score(task, result)
    assert score["metadata"] is not None
    assert score["metadata"]["expected"] == "4"
    assert score["metadata"]["actual"] == "4"

