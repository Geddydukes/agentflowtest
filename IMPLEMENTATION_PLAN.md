## 2. IMPLEMENTATION_PLAN.md

```markdown
# agentbench Implementation Plan

This document describes a practical step by step plan for building agentbench.

The goal is to move from working prototype to public release in small phases.

---

## Phase 0: Proof of concept

Objectives:

- validate the API feels natural
- verify that the core abstractions are sufficient

Tasks:

- write a 50 line script that:
  - defines a few Tasks
  - evaluates a simple function agent
  - uses a simple judge
  - prints pass or fail
- create GitHub repo `agentbench`
- reserve PyPI name if available
- add high level README

Deliverables:

- `examples/poc.py`
- project skeleton
- green light on naming and API

---

## Phase 1: Minimal core library

Objectives:

- implement basic types
- get first real evaluation working

Tasks:

- implement:
  - Task
  - Scenario
  - AgentAdapter protocol
  - Judge protocol
  - EvaluationResult
- simple synchronous `run(config)`
- write results to JSONL
- print simple summary table
- example adapters:
  - echo agent
  - OpenAI chat agent
- example judges:
  - exact match
  - regex judge

Deliverables:

- can run `agentbench run examples/math_basic.py`
- JSONL result file exists

---

## Phase 2: Real world execution engine

Objectives:

- support non trivial evals
- avoid brittle scripts

Tasks:

- async `run_async`
- concurrency control:
  - max_tasks_parallel
  - max_agents_parallel
  - max_judges_parallel
- provider rate limits using `provider_key`
- cost tracking object
- retries with backoff
- record `retries_attempted`
- `fail_fast_on` semantics

Deliverables:

- handle thousands of tasks
- do not violate API limits
- recover from transient errors

---

## Phase 3: Composability and traces

Objectives:

- support advanced judges and environments

Tasks:

- CompositeJudge with strategies:
  - all
  - any
  - weighted
  - sequential
  - best_of_n
- agent lifecycle:
  - setup
  - reset
  - teardown
- trace implementation:
  - Trace
  - TraceEvent
  - `traces.jsonl`
- EnvironmentScenario helper

Deliverables:

- composite LLM judging works
- world model or tool agent examples run

---

## Phase 4: Reporting and comparison

Objectives:

- make results understandable and sharable

Tasks:

- run metadata capture including:
  - versions
  - environment
  - hardware
- summary report generator
- Jinja2 based HTML reports
- run comparison tools
- regression detection helpers
- CLI:
  - `agentbench run`
  - `agentbench summary`
  - `agentbench compare`

Deliverables:

- static HTML summary
- diff view between two runs

---

## Phase 5: Presets and polish

Objectives:

- first public release

Tasks:

- math basic suite
- coding basic suite
- safety basic suite
- documentation and examples
- add CONTRIBUTING.md
- publish blog style announcement

Deliverables:

- PyPI release
- examples gallery
- stable public docs
