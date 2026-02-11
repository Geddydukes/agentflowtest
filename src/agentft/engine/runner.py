from dataclasses import dataclass, field
from typing import List, Dict, Any, Sequence
from datetime import datetime
from pathlib import Path
import uuid
import asyncio
import time
import platform
import sys
import os
import random
import subprocess
import hashlib

from agentft.core.scenario import Scenario
from agentft.core.agent import AgentAdapter
from agentft.core.judge import Judge
from agentft.core.result import EvaluationResult
from agentft.core.cost import Cost
from agentft.core.trace import Trace, TraceEvent
from agentft.core.metadata import RunMetadata
from agentft.engine.artifact_store import build_artifact_store
from agentft.engine.hooks import RunEventSink
import agentft


DEFAULT_RUNS_DIR = "runs"
DEFAULT_ARTIFACT_SCHEMA_VERSION = "1.1.0"


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
    retry_policy_by_error_type: Dict[str, int] | None = None
    retry_delay_seconds: float = 1.0
    fail_fast_on: str = "none"
    rate_limits: Dict[str, RateLimit] | None = None
    runs_dir: str = DEFAULT_RUNS_DIR
    agent_timeout_seconds: float | None = None
    judge_timeout_seconds: float | None = None
    max_tasks_parallel: int = 1
    max_agents_parallel: int = 1
    max_judges_parallel: int = 1
    warmup_tasks: int = 0
    shuffle_tasks: bool = False
    seed: int = 42
    cache_agent_outputs: bool = False
    resume_run_id: str | None = None
    max_total_cost_usd: float | None = None
    max_total_runtime_seconds: float | None = None
    artifact_backend: str = "jsonl"
    sqlite_db_name: str = "artifacts.db"
    shard_count: int = 1
    shard_index: int = 0
    event_sinks: Sequence[RunEventSink] | None = None


@dataclass
class RunState:
    stop_requested: bool = False
    stop_reason: str | None = None
    total_cost_usd: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    processed_keys: set[tuple[str, str, str, str]] = field(default_factory=set)


class RateLimiter:
    """Simple token bucket rate limiter for provider keys."""

    def __init__(self, rate_limits: Dict[str, RateLimit] | None = None):
        self.rate_limits = rate_limits or {}
        self.buckets: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def wait_if_needed(self, provider_key: str | None) -> None:
        """Wait if rate limit would be exceeded."""
        if not provider_key or provider_key not in self.rate_limits:
            return

        async with self._lock:
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


async def _await_with_timeout(coro, timeout_seconds: float | None):
    if timeout_seconds is None:
        return await coro
    return await asyncio.wait_for(coro, timeout=timeout_seconds)


def _get_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def _stable_seed(seed: int, *parts: str) -> int:
    h = hashlib.sha256()
    h.update(str(seed).encode("utf-8"))
    for part in parts:
        h.update(b":")
        h.update(part.encode("utf-8"))
    return int.from_bytes(h.digest()[:8], "big")


def _runtime_exceeded(started_at_perf: float, limit_seconds: float | None) -> bool:
    if limit_seconds is None:
        return False
    return (time.perf_counter() - started_at_perf) >= limit_seconds


def _task_in_shard(scenario_name: str, task_id: str, shard_count: int, shard_index: int) -> bool:
    if shard_count <= 1:
        return True
    h = hashlib.sha256(f"{scenario_name}:{task_id}".encode("utf-8")).hexdigest()
    bucket = int(h[:16], 16) % shard_count
    return bucket == shard_index


def _classify_exception(exc: Exception, phase: str) -> str:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    if "rate" in name and "limit" in name:
        return "rate_limited"
    if "rate limit" in message or "too many requests" in message:
        return "rate_limited"
    if "auth" in name or "permission" in name:
        return "auth_error"
    if isinstance(exc, PermissionError):
        return "auth_error"
    if isinstance(exc, (ConnectionError, BrokenPipeError)):
        return "provider_unavailable"
    if isinstance(exc, (ValueError, TypeError)):
        return "invalid_request"
    return f"{phase}_crash"


def _max_retries_for_error(config: RunConfig, error_type: str) -> int:
    if config.retry_policy_by_error_type and error_type in config.retry_policy_by_error_type:
        return max(0, int(config.retry_policy_by_error_type[error_type]))
    return max(0, int(config.max_retries))


async def run_async(config: RunConfig) -> List[EvaluationResult]:
    """Run evaluation with lifecycle hooks, retries, fail-fast, concurrency controls, and streaming artifacts."""
    if config.shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if config.shard_index < 0 or config.shard_index >= config.shard_count:
        raise ValueError("shard_index must be in [0, shard_count)")

    run_id = config.resume_run_id or f"{config.name}-{uuid.uuid4().hex[:8]}"
    run_dir = Path(config.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_store = build_artifact_store(
        backend=config.artifact_backend,
        run_dir=run_dir,
        schema_version=DEFAULT_ARTIFACT_SCHEMA_VERSION,
        sqlite_db_name=config.sqlite_db_name,
    )

    resumed_results = artifact_store.load_results() if config.resume_run_id else []
    state = RunState(
        total_cost_usd=sum(r.cost.total_usd for r in resumed_results if r.cost),
        processed_keys=artifact_store.load_processed_result_keys() if config.resume_run_id else set(),
    )
    checkpoint = artifact_store.load_checkpoint() if config.resume_run_id else None
    if checkpoint and "stop_reason" in checkpoint:
        state.stop_reason = checkpoint.get("stop_reason")
    results: List[EvaluationResult] = list(resumed_results)
    traces: List[Trace] = []

    metadata = RunMetadata(
        run_id=run_id,
        name=config.name,
        framework_version=agentft.__version__,
        agent_versions={agent.name: getattr(agent, "version", "unknown") for agent in config.agents},
        scenario_versions={scenario.name: getattr(scenario, "version", "unknown") for scenario in config.scenarios},
        judge_versions={judge.name: getattr(judge, "version", "unknown") for judge in config.judges},
        environment_state={
            "python_version": sys.version,
            "platform": platform.platform(),
            "shard_count": config.shard_count,
            "shard_index": config.shard_index,
        },
        hardware_info={"cpu_count": os.cpu_count()},
        created_at=datetime.utcnow(),
        git_commit=_get_git_commit(),
        artifact_schema_version=DEFAULT_ARTIFACT_SCHEMA_VERSION,
        status="running",
        ended_at=None,
        resumed_from_run_id=config.resume_run_id,
        seed=config.seed,
    )
    artifact_store.write_metadata(metadata)
    sinks = list(config.event_sinks or [])

    rate_limiter = RateLimiter(config.rate_limits)
    started_at_perf = time.perf_counter()
    io_lock = asyncio.Lock()
    run_error: Exception | None = None

    def emit_sink_event(method_name: str, *args) -> None:
        for sink in sinks:
            hook = getattr(sink, method_name, None)
            if callable(hook):
                try:
                    hook(*args)
                except Exception:
                    # External sinks should not crash benchmark execution.
                    continue

    emit_sink_event(
        "on_run_start",
        metadata,
        {
            "name": config.name,
            "runs_dir": config.runs_dir,
            "agent_count": len(config.agents),
            "scenario_count": len(config.scenarios),
            "judge_count": len(config.judges),
            "shard_count": config.shard_count,
            "shard_index": config.shard_index,
            "artifact_backend": config.artifact_backend,
        },
    )

    async def request_stop(reason: str) -> None:
        async with state.lock:
            if not state.stop_requested:
                state.stop_requested = True
                state.stop_reason = reason

    def stop_requested() -> bool:
        return state.stop_requested

    async def record_trace(trace: Trace) -> None:
        traces.append(trace)
        async with io_lock:
            artifact_store.append_trace(trace)
        emit_sink_event("on_trace", trace)

    async def record_result(result: EvaluationResult) -> None:
        key = (result.scenario, result.task_id, result.agent, result.judge)
        async with state.lock:
            if key in state.processed_keys:
                return
            state.processed_keys.add(key)
            if result.cost:
                state.total_cost_usd += result.cost.total_usd
        results.append(result)
        async with io_lock:
            artifact_store.append_result(result)
            artifact_store.write_checkpoint(
                {
                    "schema_version": DEFAULT_ARTIFACT_SCHEMA_VERSION,
                    "run_id": run_id,
                    "updated_at": datetime.utcnow().isoformat(),
                    "results_count": len(results),
                    "processed_count": len(state.processed_keys),
                    "total_cost_usd": state.total_cost_usd,
                    "stop_requested": state.stop_requested,
                    "stop_reason": state.stop_reason,
                },
            )
        emit_sink_event("on_result", result)

        if config.max_total_cost_usd is not None and state.total_cost_usd >= config.max_total_cost_usd:
            await request_stop(f"max_total_cost_usd exceeded ({state.total_cost_usd:.6f})")
        if _runtime_exceeded(started_at_perf, config.max_total_runtime_seconds):
            await request_stop("max_total_runtime_seconds exceeded")

    async def run_agent_once_with_retries(agent: AgentAdapter, scenario: Scenario, task, trace: Trace) -> tuple[Dict[str, Any], str | None, str | None, int, float | None]:
        retries_attempted = 0
        agent_output: Dict[str, Any] = {}
        agent_error: str | None = None
        agent_error_type: str | None = None
        latency_ms: float | None = None

        trace.events.append(
            TraceEvent(
                timestamp=time.time(),
                event_type="agent_start",
                data={"task_id": task.id},
            )
        )

        attempt = 0
        while True:
            if attempt > 0:
                retries_attempted = attempt
                await asyncio.sleep(config.retry_delay_seconds)

            try:
                provider_key = getattr(agent, "provider_key", None)
                await rate_limiter.wait_if_needed(provider_key)

                started = time.perf_counter()
                agent_output = await _await_with_timeout(
                    agent.run_task(task, context=None),
                    config.agent_timeout_seconds,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                agent_error = None
                agent_error_type = None
                break
            except asyncio.TimeoutError:
                agent_error = f"Agent timed out after {config.agent_timeout_seconds}s"
                agent_error_type = "agent_timeout"
                trace.events.append(
                    TraceEvent(
                        timestamp=time.time(),
                        event_type="error",
                        data={"error": agent_error, "attempt": attempt},
                    )
                )
            except Exception as e:
                agent_error = str(e)
                agent_error_type = _classify_exception(e, "agent")
                trace.events.append(
                    TraceEvent(
                        timestamp=time.time(),
                        event_type="error",
                        data={"error": str(e), "attempt": attempt, "error_type": agent_error_type},
                    )
                )

            max_retries = _max_retries_for_error(config, agent_error_type or "agent_crash")
            if attempt >= max_retries:
                break
            attempt += 1

        trace.events.append(
            TraceEvent(
                timestamp=time.time(),
                event_type="agent_end",
                data={"retries_attempted": retries_attempted},
            )
        )

        if config.cache_agent_outputs and agent_output:
            async with io_lock:
                artifact_store.append_cached_output({
                    "schema_version": DEFAULT_ARTIFACT_SCHEMA_VERSION,
                    "run_id": run_id,
                    "scenario": scenario.name,
                    "task_id": task.id,
                    "agent": agent.name,
                    "task_input": task.input,
                    "task_expected": task.expected,
                    "task_metadata": task.metadata,
                    "agent_output": agent_output,
                    "created_at": datetime.utcnow().isoformat(),
                })

        return agent_output, agent_error, agent_error_type, retries_attempted, latency_ms

    async def run_judge_with_retries(agent, scenario, task, judge, agent_output, trace, base_retries: int, agent_error: str | None, agent_error_type: str | None, agent_latency_ms: float | None) -> None:
        if stop_requested():
            return
        key = (scenario.name, task.id, agent.name, judge.name)
        if key in state.processed_keys:
            return

        judge_retries_attempted = base_retries
        judge_result: Dict[str, Any] | None = None
        judge_error: str | None = None
        judge_error_type: str | None = None
        judge_latency_ms: float | None = None

        trace.events.append(
            TraceEvent(
                timestamp=time.time(),
                event_type="judge_start",
                data={"judge": judge.name},
            )
        )

        attempt = 0
        while True:
            if attempt > 0:
                judge_retries_attempted = base_retries + attempt
                await asyncio.sleep(config.retry_delay_seconds)

            try:
                started = time.perf_counter()
                judge_result = await _await_with_timeout(
                    judge.score(task, agent_output or {}),
                    config.judge_timeout_seconds,
                )
                judge_latency_ms = (time.perf_counter() - started) * 1000.0
                judge_error = None
                judge_error_type = None
                break
            except asyncio.TimeoutError:
                judge_error = f"Judge timed out after {config.judge_timeout_seconds}s"
                judge_error_type = "judge_timeout"
                trace.events.append(
                    TraceEvent(
                        timestamp=time.time(),
                        event_type="error",
                        data={"error": judge_error, "judge": judge.name, "attempt": attempt},
                    )
                )
            except Exception as e:
                judge_error = str(e)
                judge_error_type = _classify_exception(e, "judge")
                trace.events.append(
                    TraceEvent(
                        timestamp=time.time(),
                        event_type="error",
                        data={"error": str(e), "judge": judge.name, "attempt": attempt, "error_type": judge_error_type},
                    )
                )

            max_retries = _max_retries_for_error(config, judge_error_type or "judge_crash")
            if attempt >= max_retries:
                break
            attempt += 1

        if judge_result is None:
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
                data={"judge": judge.name, "passed": bool(judge_result.get("pass", False))},
            )
        )

        raw_cost = (agent_output or {}).get("cost")
        cost = None
        if isinstance(raw_cost, dict):
            cost = Cost(**raw_cost)
        elif isinstance(raw_cost, Cost):
            cost = raw_cost

        result = EvaluationResult(
            run_id=run_id,
            task_id=task.id,
            scenario=scenario.name,
            agent=agent.name,
            judge=judge.name,
            raw_input=task.input,
            agent_output=agent_output or {},
            scores=judge_result.get("scores", {}),
            passed=bool(judge_result.get("pass", False)),
            latency_ms=judge_latency_ms or agent_latency_ms,
            metadata=judge_result.get("metadata"),
            cost=cost,
            error=agent_error or judge_error,
            error_type=agent_error_type or judge_error_type,
            retries_attempted=judge_retries_attempted,
            created_at=datetime.utcnow(),
        )
        await record_result(result)

        if (judge_error and config.fail_fast_on in ("error", "either")):
            await request_stop("judge_error")
        if (not result.passed and config.fail_fast_on in ("failure", "either")):
            await request_stop("judge_failure")

    async def process_task(agent: AgentAdapter, scenario: Scenario, task: Any, judge_sem: asyncio.Semaphore) -> None:
        if stop_requested():
            return
        if _runtime_exceeded(started_at_perf, config.max_total_runtime_seconds):
            await request_stop("max_total_runtime_seconds exceeded")
            return

        trace = Trace(
            run_id=run_id,
            task_id=task.id,
            agent=agent.name,
        )

        agent_output, agent_error, agent_error_type, retries_attempted, agent_latency_ms = await run_agent_once_with_retries(
            agent,
            scenario,
            task,
            trace,
        )

        if agent_error and config.fail_fast_on in ("error", "either"):
            await request_stop("agent_error")

        if not stop_requested():
            if config.max_judges_parallel <= 1:
                for judge in config.judges:
                    if stop_requested():
                        break
                    await run_judge_with_retries(
                        agent,
                        scenario,
                        task,
                        judge,
                        agent_output,
                        trace,
                        retries_attempted,
                        agent_error,
                        agent_error_type,
                        agent_latency_ms,
                    )
            else:
                async def run_with_sem(judge):
                    async with judge_sem:
                        await run_judge_with_retries(
                            agent,
                            scenario,
                            task,
                            judge,
                            agent_output,
                            trace,
                            retries_attempted,
                            agent_error,
                            agent_error_type,
                            agent_latency_ms,
                        )
                await asyncio.gather(*(run_with_sem(judge) for judge in config.judges))

        await record_trace(trace)

    async def process_agent(agent: AgentAdapter) -> None:
        try:
            if hasattr(agent, "setup"):
                await _await_with_timeout(agent.setup(), config.agent_timeout_seconds)

            for scenario in config.scenarios:
                if stop_requested():
                    break
                if hasattr(agent, "reset"):
                    await _await_with_timeout(agent.reset(), config.agent_timeout_seconds)

                tasks = list(scenario.iter_tasks())
                if config.shard_count > 1:
                    tasks = [
                        task for task in tasks
                        if _task_in_shard(scenario.name, task.id, config.shard_count, config.shard_index)
                    ]
                if config.shuffle_tasks:
                    rng = random.Random(_stable_seed(config.seed, agent.name, scenario.name))
                    rng.shuffle(tasks)

                warmup = max(0, min(config.warmup_tasks, len(tasks)))
                if warmup:
                    for task in tasks[:warmup]:
                        if stop_requested():
                            break
                        warmup_trace = Trace(run_id=run_id, task_id=task.id, agent=agent.name)
                        warmup_trace.events.append(
                            TraceEvent(
                                timestamp=time.time(),
                                event_type="warmup_start",
                                data={"task_id": task.id, "scenario": scenario.name},
                            )
                        )
                        await run_agent_once_with_retries(agent, scenario, task, warmup_trace)
                        warmup_trace.events.append(
                            TraceEvent(
                                timestamp=time.time(),
                                event_type="warmup_end",
                                data={"task_id": task.id, "scenario": scenario.name},
                            )
                        )
                        await record_trace(warmup_trace)

                eval_tasks = tasks[warmup:]
                if config.max_tasks_parallel <= 1:
                    judge_sem = asyncio.Semaphore(max(1, config.max_judges_parallel))
                    for task in eval_tasks:
                        if stop_requested():
                            break
                        await process_task(agent, scenario, task, judge_sem)
                else:
                    task_sem = asyncio.Semaphore(max(1, config.max_tasks_parallel))
                    judge_sem = asyncio.Semaphore(max(1, config.max_judges_parallel))

                    async def process_with_sem(task):
                        async with task_sem:
                            await process_task(agent, scenario, task, judge_sem)

                    await asyncio.gather(*(process_with_sem(task) for task in eval_tasks))
        finally:
            if hasattr(agent, "teardown"):
                await _await_with_timeout(agent.teardown(), config.agent_timeout_seconds)

    try:
        if config.max_agents_parallel <= 1:
            for agent in config.agents:
                if stop_requested():
                    break
                await process_agent(agent)
        else:
            agent_sem = asyncio.Semaphore(max(1, config.max_agents_parallel))

            async def run_with_sem(agent):
                async with agent_sem:
                    await process_agent(agent)

            agent_results = await asyncio.gather(*(run_with_sem(agent) for agent in config.agents), return_exceptions=True)
            for item in agent_results:
                if isinstance(item, Exception):
                    run_error = item
                    await request_stop("agent_exception")
                    break
    except Exception as e:
        run_error = e

    metadata.status = "failed" if run_error else ("stopped" if state.stop_requested else "completed")
    metadata.ended_at = datetime.utcnow()
    artifact_store.write_metadata(metadata)
    artifact_store.write_checkpoint(
        {
            "schema_version": DEFAULT_ARTIFACT_SCHEMA_VERSION,
            "run_id": run_id,
            "updated_at": datetime.utcnow().isoformat(),
            "results_count": len(results),
            "processed_count": len(state.processed_keys),
            "total_cost_usd": state.total_cost_usd,
            "stop_requested": state.stop_requested,
            "stop_reason": state.stop_reason,
            "status": metadata.status,
        },
    )
    emit_sink_event(
        "on_run_end",
        metadata,
        {
            "results_count": len(results),
            "processed_count": len(state.processed_keys),
            "total_cost_usd": state.total_cost_usd,
            "stop_requested": state.stop_requested,
            "stop_reason": state.stop_reason,
            "error": str(run_error) if run_error else None,
        },
    )

    from agentft.reporting.html_report import generate_html_report
    report_path = str(run_dir / "report.html")
    generate_html_report(metadata, results, report_path)

    if run_error is not None:
        artifact_store.close()
        raise run_error

    artifact_store.close()
    return results


def run(config: RunConfig) -> List[EvaluationResult]:
    """Synchronous wrapper around run_async for simple use cases."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_async(config))
    raise RuntimeError("run() cannot be called from an active event loop; use `await run_async(config)`.")
