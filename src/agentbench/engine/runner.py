from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import uuid
import asyncio
import time
import platform
import sys
import os

from agentbench.core.task import Task
from agentbench.core.scenario import Scenario
from agentbench.core.agent import AgentAdapter
from agentbench.core.judge import Judge
from agentbench.core.result import EvaluationResult
from agentbench.core.cost import Cost
from agentbench.core.trace import Trace, TraceEvent
from agentbench.core.metadata import RunMetadata
from agentbench.engine.storage import write_traces_jsonl, write_results_jsonl, write_metadata_json
import agentbench


DEFAULT_RUNS_DIR = "runs"


@dataclass
class RateLimit:
    max_calls: int
    period_seconds: int


@dataclass
class RunConfig:
    name: str
    agents: List[AgentAdapter]
    scenarios: List[Scenario]
    judges: List[Judge]
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    fail_fast_on: str = "none"
    rate_limits: Dict[str, RateLimit] | None = None
    runs_dir: str = DEFAULT_RUNS_DIR


class RateLimiter:
    """Simple token bucket rate limiter for provider keys."""

    def __init__(self, rate_limits: Dict[str, RateLimit] | None = None):
        self.rate_limits = rate_limits or {}
        self.buckets: Dict[str, List[float]] = {}

    async def wait_if_needed(self, provider_key: str | None) -> None:
        """Wait if rate limit would be exceeded."""
        if not provider_key or provider_key not in self.rate_limits:
            return

        limit = self.rate_limits[provider_key]
        now = time.time()

        if provider_key not in self.buckets:
            self.buckets[provider_key] = []

        bucket = self.buckets[provider_key]

        cutoff = now - limit.period_seconds
        bucket[:] = [ts for ts in bucket if ts > cutoff]

        if len(bucket) >= limit.max_calls:
            oldest_call = min(bucket)
            wait_time = limit.period_seconds - (now - oldest_call)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = time.time()
                bucket[:] = [ts for ts in bucket if ts > (now - limit.period_seconds)]

        bucket.append(now)


async def run_async(config: RunConfig) -> List[EvaluationResult]:
    """Phase 4 runner with lifecycle hooks, traces, retries, fail-fast, rate limiting, and reporting."""
    run_id = f"{config.name}-{uuid.uuid4().hex[:8]}"
    results: List[EvaluationResult] = []
    traces: List[Trace] = []
    rate_limiter = RateLimiter(config.rate_limits)

    metadata = RunMetadata(
        run_id=run_id,
        name=config.name,
        framework_version=agentbench.__version__,
        agent_versions={agent.name: getattr(agent, "version", "unknown") for agent in config.agents},
        scenario_versions={},
        judge_versions={},
        environment_state={
            "python_version": sys.version,
            "platform": platform.platform(),
        },
        hardware_info={"cpu_count": os.cpu_count()},
        created_at=datetime.utcnow(),
        git_commit=None,
    )

    for agent in config.agents:
        try:
            if hasattr(agent, "setup"):
                await agent.setup()

            for scenario in config.scenarios:
                if hasattr(agent, "reset"):
                    await agent.reset()

                for task in scenario.iter_tasks():
                    trace = Trace(
                        run_id=run_id,
                        task_id=task.id,
                        agent=agent.name,
                    )

                    retries_attempted = 0
                    agent_output = None
                    agent_error = None
                    agent_error_type = None

                    trace.events.append(
                        TraceEvent(
                            timestamp=time.time(),
                            event_type="agent_start",
                            data={"task_id": task.id},
                        )
                    )

                    for attempt in range(config.max_retries + 1):
                        if attempt > 0:
                            retries_attempted = attempt
                            await asyncio.sleep(config.retry_delay_seconds)

                        try:
                            provider_key = getattr(agent, "provider_key", None)
                            await rate_limiter.wait_if_needed(provider_key)

                            agent_output = await agent.run_task(task, context=None)
                            break
                        except Exception as e:
                            agent_error = str(e)
                            agent_error_type = "agent_crash"
                            trace.events.append(
                                TraceEvent(
                                    timestamp=time.time(),
                                    event_type="error",
                                    data={"error": str(e), "attempt": attempt},
                                )
                            )
                            if attempt == config.max_retries:
                                agent_output = {}

                    trace.events.append(
                        TraceEvent(
                            timestamp=time.time(),
                            event_type="agent_end",
                            data={"retries_attempted": retries_attempted},
                        )
                    )

                    if agent_error and config.fail_fast_on in ("error", "either"):
                        traces.append(trace)
                        return results

                    for judge in config.judges:
                        judge_retries_attempted = retries_attempted
                        judge_result = None
                        judge_error = None
                        judge_error_type = None

                        trace.events.append(
                            TraceEvent(
                                timestamp=time.time(),
                                event_type="judge_start",
                                data={"judge": judge.name},
                            )
                        )

                        for attempt in range(config.max_retries + 1):
                            if attempt > 0:
                                judge_retries_attempted = retries_attempted + attempt
                                await asyncio.sleep(config.retry_delay_seconds)

                            try:
                                judge_result = await judge.score(task, agent_output or {})
                                break
                            except Exception as e:
                                judge_error = str(e)
                                judge_error_type = "judge_crash"
                                trace.events.append(
                                    TraceEvent(
                                        timestamp=time.time(),
                                        event_type="error",
                                        data={"error": str(e), "judge": judge.name, "attempt": attempt},
                                    )
                                )
                                if attempt == config.max_retries:
                                    judge_result = {
                                        "scores": {},
                                        "pass": False,
                                        "explanation": None,
                                        "metadata": None,
                                    }

                        trace.events.append(
                            TraceEvent(
                                timestamp=time.time(),
                                event_type="judge_end",
                                data={"judge": judge.name, "passed": judge_result.get("pass", False) if judge_result else False},
                            )
                        )

                        if judge_error and config.fail_fast_on in ("error", "either"):
                            traces.append(trace)
                            return results

                        scores = judge_result.get("scores", {}) if judge_result else {}
                        passed = bool(judge_result.get("pass", False)) if judge_result else False
                        result_metadata = judge_result.get("metadata") if judge_result else None

                        cost = agent_output.get("cost") if agent_output else None
                        if isinstance(cost, dict):
                            cost = Cost(**cost)
                        elif not isinstance(cost, Cost):
                            cost = Cost.zero()

                        error = agent_error or judge_error
                        error_type = agent_error_type or judge_error_type
                        total_retries = judge_retries_attempted

                        if not passed and config.fail_fast_on in ("failure", "either"):
                            traces.append(trace)
                            results.append(
                                EvaluationResult(
                                    run_id=run_id,
                                    task_id=task.id,
                                    scenario=scenario.name,
                                    agent=agent.name,
                                    judge=judge.name,
                                    raw_input=task.input,
                                    agent_output=agent_output or {},
                                    scores=scores,
                                    passed=passed,
                                    metadata=result_metadata,
                                    cost=cost,
                                    error=error,
                                    error_type=error_type,
                                    retries_attempted=total_retries,
                                    created_at=datetime.utcnow(),
                                )
                            )
                            return results

                        results.append(
                            EvaluationResult(
                                run_id=run_id,
                                task_id=task.id,
                                scenario=scenario.name,
                                agent=agent.name,
                                judge=judge.name,
                                raw_input=task.input,
                                agent_output=agent_output or {},
                                scores=scores,
                                passed=passed,
                                metadata=metadata,
                                cost=cost,
                                error=error,
                                error_type=error_type,
                                retries_attempted=total_retries,
                                created_at=datetime.utcnow(),
                            )
                        )

                    traces.append(trace)

        finally:
            if hasattr(agent, "teardown"):
                await agent.teardown()

    run_dir = Path(config.runs_dir) / run_id
    trace_path = str(run_dir / "traces.jsonl")
    results_path = str(run_dir / "results.jsonl")
    metadata_path = str(run_dir / "run_metadata.json")

    write_traces_jsonl(traces, trace_path)
    write_results_jsonl(results, results_path)
    write_metadata_json(metadata, metadata_path)

    from agentbench.reporting.html_report import generate_html_report
    report_path = str(run_dir / "report.html")
    generate_html_report(metadata, results, report_path)

    return results


def run(config: RunConfig) -> List[EvaluationResult]:
    """Synchronous wrapper around run_async for simple use cases."""
    return asyncio.run(run_async(config))
