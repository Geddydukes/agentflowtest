"""Tests for runner and RunConfig."""

import pytest
import asyncio
from pathlib import Path
from agentft import (
    Task,
    ListScenario,
    RunConfig,
    RateLimit,
)
from agentft.engine.runner import run_async, DEFAULT_RUNS_DIR


class TestAgent:
    """Test agent implementation."""
    name = "test_agent"
    version = "1.0.0"
    provider_key = None
    
    async def setup(self):
        pass
    
    async def reset(self):
        pass
    
    async def teardown(self):
        pass
    
    async def run_task(self, task, context=None):
        return {"response": "test_response"}


class TestJudge:
    """Test judge implementation."""
    name = "test_judge"
    
    async def score(self, task, result):
        return {
            "scores": {"correctness": 1.0},
            "pass": True,
            "explanation": None,
            "metadata": None,
        }


@pytest.mark.asyncio
async def test_run_config_creation():
    """Test RunConfig creation."""
    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()
    
    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )
    assert config.name == "test_run"
    assert len(config.agents) == 1
    assert config.max_retries == 3
    assert config.runs_dir == DEFAULT_RUNS_DIR


@pytest.mark.asyncio
async def test_run_config_custom_runs_dir():
    """Test RunConfig with custom runs_dir."""
    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()
    
    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        runs_dir="custom_runs",
    )
    assert config.runs_dir == "custom_runs"


@pytest.mark.asyncio
async def test_run_async_basic():
    """Test basic run_async execution."""
    agent = TestAgent()
    task = Task(id="test_1", input={"prompt": "test"})
    scenario = ListScenario("test_scenario", [task])
    judge = TestJudge()
    
    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )
    
    results = await run_async(config)
    assert len(results) == 1
    assert results[0].task_id == "test_1"
    assert results[0].passed is True
    assert results[0].agent == "test_agent"
    assert results[0].judge == "test_judge"


@pytest.mark.asyncio
async def test_run_async_lifecycle_hooks():
    """Test that lifecycle hooks are called."""
    class HookTrackingAgent(TestAgent):
        def __init__(self):
            self.setup_called = False
            self.reset_called = False
            self.teardown_called = False
        
        async def setup(self):
            self.setup_called = True
        
        async def reset(self):
            self.reset_called = True
        
        async def teardown(self):
            self.teardown_called = True
    
    agent = HookTrackingAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()
    
    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )
    
    await run_async(config)
    assert agent.setup_called is True
    assert agent.reset_called is True
    assert agent.teardown_called is True


@pytest.mark.asyncio
async def test_run_async_creates_files():
    """Test that run_async creates output files."""
    import tempfile
    import os
    
    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = RunConfig(
            name="test_run",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
        )
        
        results = await run_async(config)
        run_id = results[0].run_id
        
        run_dir = Path(tmpdir) / run_id
        assert (run_dir / "results.jsonl").exists()
        assert (run_dir / "traces.jsonl").exists()
        assert (run_dir / "run_metadata.json").exists()
        assert (run_dir / "report.html").exists()


@pytest.mark.asyncio
async def test_run_async_rate_limiting():
    """Test that rate limiting is applied."""
    agent = TestAgent()
    agent.provider_key = "test_provider"
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()
    
    rate_limit = RateLimit(max_calls=2, period_seconds=1)
    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        rate_limits={"test_provider": rate_limit},
    )
    
    results = await run_async(config)
    assert len(results) == 1

