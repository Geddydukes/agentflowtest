"""Tests for CompositeJudge."""

import pytest
from agentft import Task, CompositeJudge


class MockJudge:
    """Mock judge for testing."""
    def __init__(self, name, will_pass=True):
        self.name = name
        self.will_pass = will_pass
    
    async def score(self, task, result):
        return {
            "scores": {"mock": 1.0 if self.will_pass else 0.0},
            "pass": self.will_pass,
            "explanation": None,
            "metadata": None,
        }


class CountingJudge(MockJudge):
    def __init__(self, name, will_pass=True):
        super().__init__(name, will_pass=will_pass)
        self.calls = 0

    async def score(self, task, result):
        self.calls += 1
        return await super().score(task, result)


@pytest.mark.asyncio
async def test_composite_judge_all_strategy():
    """Test CompositeJudge with 'all' strategy."""
    judge1 = MockJudge("judge1", will_pass=True)
    judge2 = MockJudge("judge2", will_pass=True)
    composite = CompositeJudge(judges=[judge1, judge2], strategy="all")
    
    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}
    
    score = await composite.score(task, result)
    assert score["pass"] is True
    assert "sub_judges" in score["metadata"]


@pytest.mark.asyncio
async def test_composite_judge_all_strategy_fails():
    """Test CompositeJudge 'all' strategy fails when one judge fails."""
    judge1 = MockJudge("judge1", will_pass=True)
    judge2 = MockJudge("judge2", will_pass=False)
    composite = CompositeJudge(judges=[judge1, judge2], strategy="all")
    
    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}
    
    score = await composite.score(task, result)
    assert score["pass"] is False


@pytest.mark.asyncio
async def test_composite_judge_any_strategy():
    """Test CompositeJudge with 'any' strategy."""
    judge1 = MockJudge("judge1", will_pass=False)
    judge2 = MockJudge("judge2", will_pass=True)
    composite = CompositeJudge(judges=[judge1, judge2], strategy="any")
    
    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}
    
    score = await composite.score(task, result)
    assert score["pass"] is True


@pytest.mark.asyncio
async def test_composite_judge_any_strategy_fails():
    """Test CompositeJudge 'any' strategy fails when all judges fail."""
    judge1 = MockJudge("judge1", will_pass=False)
    judge2 = MockJudge("judge2", will_pass=False)
    composite = CompositeJudge(judges=[judge1, judge2], strategy="any")
    
    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}
    
    score = await composite.score(task, result)
    assert score["pass"] is False


@pytest.mark.asyncio
async def test_composite_judge_name():
    """Test CompositeJudge generates correct name."""
    judge1 = MockJudge("judge1")
    judge2 = MockJudge("judge2")
    composite = CompositeJudge(judges=[judge1, judge2], strategy="all")
    
    assert "judge1" in composite.name
    assert "judge2" in composite.name
    assert composite.name.startswith("composite[")


@pytest.mark.asyncio
async def test_composite_judge_handles_errors():
    """Test CompositeJudge handles judge errors gracefully."""
    class FailingJudge:
        name = "failing"
        async def score(self, task, result):
            raise Exception("Judge error")
    
    judge1 = MockJudge("judge1", will_pass=True)
    judge2 = FailingJudge()
    composite = CompositeJudge(judges=[judge1, judge2], strategy="all")
    
    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}
    
    score = await composite.score(task, result)
    assert "sub_judges" in score["metadata"]
    assert len(score["metadata"]["sub_judges"]) == 2


@pytest.mark.asyncio
async def test_composite_judge_weighted_without_weights_does_not_recurse():
    """Test weighted strategy works even when no weights are provided."""
    judge1 = MockJudge("judge1", will_pass=True)
    judge2 = MockJudge("judge2", will_pass=False)
    composite = CompositeJudge(judges=[judge1, judge2], strategy="weighted", weights=None)

    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}

    score = await composite.score(task, result)
    assert isinstance(score["scores"], dict)
    assert score["pass"] is False


@pytest.mark.asyncio
async def test_composite_judge_sequential_short_circuits_after_first_pass():
    """Test sequential strategy does not run additional judges after a pass."""
    first = CountingJudge("first", will_pass=True)
    second = CountingJudge("second", will_pass=False)
    composite = CompositeJudge(judges=[first, second], strategy="sequential")

    task = Task(id="test", input={}, expected={})
    result = {"response": "test"}

    score = await composite.score(task, result)
    assert score["pass"] is True
    assert first.calls == 1
    assert second.calls == 0
