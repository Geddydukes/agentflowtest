"""Integration tests for full evaluation workflow."""

import pytest
from pathlib import Path
from agentbench import (
    Task,
    ListScenario,
    RunConfig,
    run,
    build_math_basic_scenario,
    ExactMatchJudge,
)


class SimpleMathAgent:
    """Simple math agent for integration testing."""
    name = "simple_math_agent"
    version = "0.0.1"
    provider_key = None
    
    async def setup(self):
        pass
    
    async def reset(self):
        pass
    
    async def teardown(self):
        pass
    
    async def run_task(self, task, context=None):
        prompt = task.input.get("prompt", "")
        if "2 + 3" in prompt:
            return {"response": "5"}
        elif "4 * 7" in prompt:
            return {"response": "28"}
        elif "10 - 4" in prompt:
            return {"response": "6"}
        elif "15 / 3" in prompt:
            return {"response": "5"}
        return {"response": "unknown"}


def test_full_evaluation_workflow():
    """Test complete evaluation workflow using presets."""
    scenario = build_math_basic_scenario()
    agent = SimpleMathAgent()
    judge = ExactMatchJudge()
    
    config = RunConfig(
        name="integration_test",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )
    
    results = run(config)
    
    assert len(results) == 4
    passed = sum(1 for r in results if r.passed)
    assert passed == 4
    
    run_id = results[0].run_id
    run_dir = Path("runs") / run_id
    assert run_dir.exists()
    assert (run_dir / "results.jsonl").exists()
    assert (run_dir / "traces.jsonl").exists()
    assert (run_dir / "run_metadata.json").exists()
    assert (run_dir / "report.html").exists()


def test_evaluation_with_failures():
    """Test evaluation workflow with some failures."""
    class FailingAgent(SimpleMathAgent):
        async def run_task(self, task, context=None):
            return {"response": "wrong"}
    
    scenario = build_math_basic_scenario()
    agent = FailingAgent()
    judge = ExactMatchJudge()
    
    config = RunConfig(
        name="failure_test",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )
    
    results = run(config)
    assert len(results) == 4
    passed = sum(1 for r in results if r.passed)
    assert passed == 0

