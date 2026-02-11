agentbench: Master Design Document
What is agentbench

agentbench is an open source framework for evaluating AI agents.

It aims to do for agents what pytest does for code:

minimal boilerplate to get started

clean defaults that work for common cases

full control when needed

transparent and reproducible results

Primary goals:

benchmark multiple agents side by side

detect regressions over time

support both simple chat models and complex tool agents

handle large runs while respecting rate limits

produce results that are easy to inspect and audit

Core philosophy

agentbench is built around five ideas.

Simple mental model
Everything is composed from Task, Scenario, Agent, Judge, Run.

Batteries included
A user can do meaningful work without deep configuration.

Real world execution
Concurrency, warmups, retries, and rate limits are first class features.

Inspectable and reproducible
agentbench does not hide what happened. It records costs, traces, metadata, and versions.

Friendly workflows
Clean Python API, straightforward CLI, single HTML report file.

Core abstractions
Task

Represents a single evaluation unit.

@dataclass
class Task:
    id: str
    input: dict
    expected: dict | None = None
    metadata: dict | None = None


Examples:

prompt and expected answer

dataset row

environment initial state

Tasks are independent. Multi step workflows should be represented as a single Task or through environment scenarios.

Scenario

Produces a set or stream of Tasks.

class Scenario(Protocol):
    name: str

    def iter_tasks(self) -> Iterable[Task]:
        ...


Scenarios may be:

static datasets

synthetic or generated task sets

adversarial prompt builders

episode generators for environments

AgentAdapter

Unified interface for any agent implementation.

Supports stateless and stateful agents.

class AgentAdapter(Protocol):
    name: str
    version: str
    provider_key: str | None

    async def setup(self) -> None:
        ...

    async def reset(self) -> None:
        ...

    async def run_task(self, task: Task, context: dict | None = None) -> dict:
        ...

    async def teardown(self) -> None:
        ...


Key points:

version declares agent version for metadata

provider_key enables shared rate limiting across agents

setup and teardown handle resource initialization

reset handles per scenario or episode reset state

context semantics:

prior episode history

previous steps within an environment

shared handles like DB connections

most simple agents ignore it

Standard return payload:

{
  "response": str | dict,
  "trace": list[dict],
  "latency_ms": float,
  "cost": Cost | None,
  "raw": dict | None
}

Judge

Evaluates output and produces scores.

class Judge(Protocol):
    name: str

    async def score(self, task: Task, result: dict) -> dict:
        return {
          "scores": {"correctness": 0.0},
          "pass": False,
          "explanation": None,
          "metadata": None
        }


Judge metadata examples:

LLM grader prompt, model, temperature

patterns matched by regex judge

sub judge decisions under composite judge

Judge types:

exact match

regex scoring

Rouge, BLEU, and overlap metrics

LLM rubric grading

safety, jailbreak, PII leak testing

CompositeJudge

Supports multi level and ensemble judging.

@dataclass
class CompositeJudge:
    judges: list[Judge]
    strategy: str = "all"
    weights: dict[str, float] | None = None


Strategies supported:

all

any

weighted

sequential

best_of_n

Examples:

Sequential fast to slow pipeline:

CompositeJudge(
    judges=[ExactMatchJudge(), RougeJudge(), LLMJudge()],
    strategy="sequential"
)


LLM voting ensemble:

CompositeJudge(
    judges=[LLMJudge(), LLMJudge(), LLMJudge()],
    strategy="best_of_n"
)


Composite Judge metadata stores sub judge outputs for debugging.

Cost model

Structured and aggregable.

@dataclass
class Cost:
    total_usd: float
    breakdown: dict[str, float] | None = None
    model: str | None = None

    @classmethod
    def zero(cls) -> "Cost":
        return cls(total_usd=0.0, breakdown={})


Breakdown may include:

input tokens

output tokens

tool calls

environment steps

provider specific line items

EvaluationResult

One agent, one task, one judge.

@dataclass
class EvaluationResult:
    run_id: str
    task_id: str
    scenario: str
    agent: str
    judge: str
    raw_input: dict
    agent_output: dict
    scores: dict
    passed: bool
    cost: Cost | None
    latency_ms: float | None
    metadata: dict | None
    created_at: datetime

    error: str | None = None
    error_type: str | None = None
    retries_attempted: int = 0


Supports distinguishing:

immediate failures

failures after multiple retries

Error types include:

agent_crash

judge_timeout

rate_limit

environment_failure

Execution configuration
RateLimit
@dataclass
class RateLimit:
    max_calls: int
    period_seconds: int


Adapters declare provider_key, for example:

openai

anthropic

local

Engine uses config wide mapping to throttle properly.

RunConfig
@dataclass
class RunConfig:
    name: str
    agents: list[AgentAdapter]
    scenarios: list[Scenario]
    judges: list[Judge]

    max_tasks_parallel: int = 16
    max_agents_parallel: int = 4
    max_judges_parallel: int = 8

    rate_limits: dict[str, RateLimit] | None = None

    max_retries: int = 3
    retry_delay_seconds: float = 5.0

    fail_fast_on: str = "none"

    warmup_tasks: int = 0
    cache_responses: bool = False

    seed: int = 42


Fail fast options:

none

error

failure

either

Warmup and caching

Warmup:

optional N warmup tasks per agent

excluded from metrics

prevents cold start affecting latency

Caching:

stores agent outputs

allows re judging with new judges

avoids expensive recomputation

Versioning and reproducibility
@dataclass
class RunMetadata:
    run_id: str
    name: str
    framework_version: str
    agent_versions: dict[str, str]
    scenario_versions: dict[str, str]
    judge_versions: dict[str, str]
    environment_state: dict
    hardware_info: dict | None
    created_at: datetime
    git_commit: str | None


Data captured:

agent versions

Python and library versions

CPU, GPU, RAM

random seeds

Traces

Full per task event stream.

@dataclass
class TraceEvent:
    timestamp: float
    event_type: str
    data: dict

@dataclass
class Trace:
    run_id: str
    task_id: str
    agent: str
    events: list[TraceEvent]


Event types:

message

tool_call

tool_result

environment_step

error

completion

Stored in traces.jsonl.

Execution modes

Blocking:

summary = run(config)


Callback:

run(config, callback=on_result)


Async streaming:

async for r in run_async(config):
    ...


Streaming allows live dashboards, progress and checkpointing.

HTML reports

Generated with Jinja2 templates.

Properties:

single file HTML

embedded CSS and JS

no build tools required

openable directly in browser

Contents:

run summary

cost and latency breakdowns

filterable task list

per task detail including trace

Comparison and regression detection

Functions provided:

load runs

compare runs

compute deltas

Includes:

task level regression lists

metric deltas

cost change summaries

For CI and release gating.

Environment scenarios

EnvironmentScenario helper supports episodic agent evaluation.

Uses:

world models

cyber security graphs

RL like agents

Scored on:

reward

rule violations

completion metrics

CLI

Primary command: agentbench

Subcommands:

run

summary

compare

Example:

agentbench run examples/math_basic.py
agentbench compare runs/a runs/b

Implementation roadmap

Phase 0
Proof of concept script and repo skeleton

Phase 1
Core primitives and simple run

Phase 2
Async engine, limits, retries, cost

Phase 3
Composite judges, lifecycle, traces

Phase 4
HTML reports and comparison tools

Phase 5
Presets, docs, and release