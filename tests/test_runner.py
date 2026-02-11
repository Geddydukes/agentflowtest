"""Tests for runner and RunConfig."""

import pytest
import asyncio
import time
from pathlib import Path
from agentft import (
    Task,
    ListScenario,
    RunConfig,
    RateLimit,
    run,
    Cost,
)
from agentft.engine.runner import run_async, DEFAULT_RUNS_DIR
from agentft.engine.storage import load_results_from_run_dir


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


@pytest.mark.asyncio
async def test_run_async_fail_fast_still_persists_artifacts():
    """Fail-fast runs should still write traces/results/metadata/report."""
    class FailingJudge:
        name = "failing_judge"

        async def score(self, task, result):
            return {
                "scores": {"correctness": 0.0},
                "pass": False,
                "explanation": None,
                "metadata": None,
            }

    import tempfile

    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={}), Task(id="2", input={})])
    judge = FailingJudge()

    with tempfile.TemporaryDirectory() as tmpdir:
        config = RunConfig(
            name="test_run",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
            fail_fast_on="failure",
            max_retries=0,
        )

        results = await run_async(config)
        assert len(results) == 1
        run_id = results[0].run_id
        run_dir = Path(tmpdir) / run_id
        assert (run_dir / "results.jsonl").exists()
        assert (run_dir / "traces.jsonl").exists()
        assert (run_dir / "run_metadata.json").exists()
        assert (run_dir / "report.html").exists()


@pytest.mark.asyncio
async def test_run_async_agent_timeout_records_error_type():
    """Agent timeout should be captured as an error type in results."""
    class SlowAgent(TestAgent):
        async def run_task(self, task, context=None):
            await asyncio.sleep(0.05)
            return {"response": "late"}

    agent = SlowAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()

    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        max_retries=0,
        agent_timeout_seconds=0.001,
    )

    results = await run_async(config)
    assert len(results) == 1
    assert results[0].error_type == "agent_timeout"


@pytest.mark.asyncio
async def test_run_raises_inside_active_event_loop():
    """Synchronous run wrapper should error inside an active event loop."""
    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()

    config = RunConfig(
        name="test_run",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
    )

    with pytest.raises(RuntimeError):
        run(config)


@pytest.mark.asyncio
async def test_run_async_resume_skips_processed_results():
    """Resuming a run should skip already-written scenario/task/agent/judge entries."""
    class MixedJudge:
        name = "mixed_judge"

        async def score(self, task, result):
            return {
                "scores": {"correctness": 1.0 if task.id == "2" else 0.0},
                "pass": task.id == "2",
                "explanation": None,
                "metadata": None,
            }

    import tempfile

    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={}), Task(id="2", input={})])
    judge = MixedJudge()

    with tempfile.TemporaryDirectory() as tmpdir:
        first = RunConfig(
            name="resume_test",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
            fail_fast_on="failure",
            max_retries=0,
        )
        first_results = await run_async(first)
        assert len(first_results) == 1
        run_id = first_results[0].run_id

        resumed = RunConfig(
            name="resume_test",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
            fail_fast_on="none",
            max_retries=0,
            resume_run_id=run_id,
        )
        resumed_results = await run_async(resumed)
        assert len(resumed_results) == 2
        task_ids = [r.task_id for r in resumed_results]
        assert task_ids.count("1") == 1
        assert task_ids.count("2") == 1


@pytest.mark.asyncio
async def test_run_async_stops_on_cost_budget():
    """Run should stop once max_total_cost_usd is reached."""
    class CostlyAgent(TestAgent):
        async def run_task(self, task, context=None):
            return {"response": "ok", "cost": Cost(total_usd=1.0)}

    class PassJudge:
        name = "pass_judge"

        async def score(self, task, result):
            return {
                "scores": {"correctness": 1.0},
                "pass": True,
                "explanation": None,
                "metadata": None,
            }

    agent = CostlyAgent()
    scenario = ListScenario("test", [Task(id="1", input={}), Task(id="2", input={}), Task(id="3", input={})])
    judge = PassJudge()

    config = RunConfig(
        name="budget_test",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        max_total_cost_usd=1.5,
        max_retries=0,
    )

    results = await run_async(config)
    assert 1 <= len(results) <= 2


@pytest.mark.asyncio
async def test_run_async_agent_parallelism_reduces_runtime():
    """max_agents_parallel should allow independent agents to run concurrently."""
    class SlowAgent(TestAgent):
        async def run_task(self, task, context=None):
            await asyncio.sleep(0.08)
            return {"response": "ok"}

    class PassJudge:
        name = "pass_judge"

        async def score(self, task, result):
            return {
                "scores": {"correctness": 1.0},
                "pass": True,
                "explanation": None,
                "metadata": None,
            }

    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = PassJudge()

    serial_config = RunConfig(
        name="parallel_agents_serial",
        agents=[SlowAgent(), SlowAgent()],
        scenarios=[scenario],
        judges=[judge],
        max_agents_parallel=1,
        max_retries=0,
    )
    t0 = time.perf_counter()
    await run_async(serial_config)
    serial_time = time.perf_counter() - t0

    parallel_config = RunConfig(
        name="parallel_agents_parallel",
        agents=[SlowAgent(), SlowAgent()],
        scenarios=[scenario],
        judges=[judge],
        max_agents_parallel=2,
        max_retries=0,
    )
    t1 = time.perf_counter()
    await run_async(parallel_config)
    parallel_time = time.perf_counter() - t1

    assert parallel_time < serial_time


@pytest.mark.asyncio
async def test_run_async_writes_checkpoint_file():
    """Runner should maintain a checkpoint file for resume support."""
    import tempfile
    import json

    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()

    with tempfile.TemporaryDirectory() as tmpdir:
        config = RunConfig(
            name="checkpoint_test",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
        )
        results = await run_async(config)
        run_dir = Path(tmpdir) / results[0].run_id
        checkpoint_path = run_dir / "run_checkpoint.json"
        assert checkpoint_path.exists()
        checkpoint = json.loads(checkpoint_path.read_text())
        assert checkpoint["run_id"] == results[0].run_id
        assert checkpoint["results_count"] >= 1
        assert "status" in checkpoint


@pytest.mark.asyncio
async def test_run_async_shuffle_tasks_deterministic_with_seed():
    """Task shuffling should be deterministic for the same seed."""
    class RecordingAgent(TestAgent):
        def __init__(self):
            self.order = []

        async def run_task(self, task, context=None):
            self.order.append(task.id)
            return {"response": "ok"}

    tasks = [Task(id=str(i), input={}) for i in range(10)]
    scenario = ListScenario("test", tasks)
    judge = TestJudge()

    a1 = RecordingAgent()
    c1 = RunConfig(
        name="shuffle_1",
        agents=[a1],
        scenarios=[scenario],
        judges=[judge],
        shuffle_tasks=True,
        seed=123,
        max_retries=0,
    )
    await run_async(c1)

    a2 = RecordingAgent()
    c2 = RunConfig(
        name="shuffle_2",
        agents=[a2],
        scenarios=[scenario],
        judges=[judge],
        shuffle_tasks=True,
        seed=123,
        max_retries=0,
    )
    await run_async(c2)

    assert a1.order == a2.order


@pytest.mark.asyncio
async def test_run_async_sqlite_backend():
    """Runner should support SQLite artifact backend."""
    import tempfile

    agent = TestAgent()
    scenario = ListScenario("test", [Task(id="1", input={})])
    judge = TestJudge()

    with tempfile.TemporaryDirectory() as tmpdir:
        config = RunConfig(
            name="sqlite_test",
            agents=[agent],
            scenarios=[scenario],
            judges=[judge],
            runs_dir=tmpdir,
            artifact_backend="sqlite",
            sqlite_db_name="artifacts.db",
        )
        results = await run_async(config)
        run_dir = Path(tmpdir) / results[0].run_id
        assert (run_dir / "artifacts.db").exists()
        loaded = load_results_from_run_dir(str(run_dir))
        assert len(loaded) == 1
        assert loaded[0].passed is True


@pytest.mark.asyncio
async def test_run_async_sharding_partitions_tasks_without_overlap():
    """Two shards should cover the full task set without overlap."""
    class EchoJudge:
        name = "echo"

        async def score(self, task, result):
            return {"scores": {"ok": 1.0}, "pass": True, "explanation": None, "metadata": None}

    class EchoAgent(TestAgent):
        async def run_task(self, task, context=None):
            return {"response": task.id}

    tasks = [Task(id=str(i), input={}) for i in range(20)]
    scenario = ListScenario("sharded", tasks)
    judge = EchoJudge()
    agent = EchoAgent()

    cfg0 = RunConfig(
        name="shard0",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        shard_count=2,
        shard_index=0,
        max_retries=0,
    )
    cfg1 = RunConfig(
        name="shard1",
        agents=[agent],
        scenarios=[scenario],
        judges=[judge],
        shard_count=2,
        shard_index=1,
        max_retries=0,
    )

    r0 = await run_async(cfg0)
    r1 = await run_async(cfg1)
    s0 = {r.task_id for r in r0}
    s1 = {r.task_id for r in r1}
    assert s0.isdisjoint(s1)
    assert s0 | s1 == {str(i) for i in range(20)}


@pytest.mark.asyncio
async def test_run_async_retry_policy_by_error_type():
    """Retry count should respect retry_policy_by_error_type overrides."""

    class InvalidReqAgent(TestAgent):
        def __init__(self):
            self.calls = 0

        async def run_task(self, task, context=None):
            self.calls += 1
            raise ValueError("bad request")

    class PassJudge:
        name = "pass_judge"

        async def score(self, task, result):
            return {"scores": {"ok": 1.0}, "pass": True, "explanation": None, "metadata": None}

    agent = InvalidReqAgent()
    config = RunConfig(
        name="retry_policy",
        agents=[agent],
        scenarios=[ListScenario("s", [Task(id="1", input={})])],
        judges=[PassJudge()],
        max_retries=3,
        retry_policy_by_error_type={"invalid_request": 0},
    )
    results = await run_async(config)
    assert len(results) == 1
    assert results[0].error_type == "invalid_request"
    assert agent.calls == 1


@pytest.mark.asyncio
async def test_run_async_event_sink_hooks():
    """Runner should call external event sink hooks."""

    class Sink:
        def __init__(self):
            self.started = 0
            self.ended = 0
            self.results = 0
            self.traces = 0

        def on_run_start(self, metadata, config):
            self.started += 1

        def on_result(self, result):
            self.results += 1

        def on_trace(self, trace):
            self.traces += 1

        def on_run_end(self, metadata, stats):
            self.ended += 1

    sink = Sink()
    config = RunConfig(
        name="sink_hooks",
        agents=[TestAgent()],
        scenarios=[ListScenario("s", [Task(id="1", input={})])],
        judges=[TestJudge()],
        event_sinks=[sink],
    )
    results = await run_async(config)
    assert len(results) == 1
    assert sink.started == 1
    assert sink.ended == 1
    assert sink.results == 1
    assert sink.traces >= 1
