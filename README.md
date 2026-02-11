# AgentFT

**Agent Flow Test** - Pytest for AI agents

[![PyPI](https://img.shields.io/pypi/v/agentft)](https://pypi.org/project/agentft/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AgentFT (Agent Flow Test) is a pytest-style evaluation framework for AI agents. It provides composable primitives for tasks, scenarios, agents, and judges, with production-ready infrastructure for concurrency, retries, observability, and regression control.

## What's New

- Secure declarative config mode: `--config-json --strict-config`
- Distributed local orchestration: `aft orchestrate` for sharded multi-process runs + merge
- Retry policy by error type with richer error taxonomy
- Task-level vs judge-level aggregation with configurable task pass rules
- Ranking support: `aft rank` (Elo)
- Artifact migration tooling: `aft migrate`
- Columnar export API (DuckDB/Parquet)
- Environment/episode scenario toolkit and additional preset benchmark suites
- Structured external event sinks for run lifecycle telemetry
- Interactive report drilldown with filtering

## Features

- **Pytest-like simplicity**: Minimal boilerplate, clear abstractions
- **Production-ready execution**: Async runner, retries, rate limiting, timeouts, fail-fast modes
- **Flexible parallelism**: Independent controls for agents, tasks, and judges
- **Deterministic reproducibility**: Seeded shuffle + deterministic sharding
- **Strong artifact model**: JSONL or SQLite backends with schema versioning and checkpoints
- **Regression workflows**: Compare, gate, rejudge, analyze, rank, merge
- **Extensibility**: Plugin registry for agents, scenarios, and judges
- **Scenario breadth**: List/CSV/JSONL/HuggingFace + rollout-based episode scenarios
- **Governance support**: API stability policy and governance/compliance guidance

## Quick Start

Install from PyPI:

```bash
pip install agentft
```

Run an example:

```bash
git clone https://github.com/Geddydukes/agentflowtest
cd agentflowtest
aft run --config examples/config_example.py
```

Or use in code:

```python
from agentft import RunConfig, run
from agentft.presets import build_math_basic_scenario, ExactMatchJudge

class MyAgent:
    name = "my_agent"
    version = "0.1.0"
    provider_key = None

    async def setup(self):
        pass

    async def reset(self):
        pass

    async def teardown(self):
        pass

    async def run_task(self, task, context=None):
        return {"response": "42"}

config = RunConfig(
    name="quick_test",
    agents=[MyAgent()],
    scenarios=[build_math_basic_scenario()],
    judges=[ExactMatchJudge()],
)

results = run(config)
print(f"Passed: {sum(r.passed for r in results)}/{len(results)}")
```

## Core CLI Commands

### `aft run`

```bash
aft run --config path/to/config.py
```

Strict non-executable mode:

```bash
aft run --config-json path/to/config.json --strict-config
```

Useful overrides:

```bash
aft run --config examples/config_example.py \
  --max-tasks-parallel 8 \
  --max-agents-parallel 2 \
  --max-judges-parallel 4 \
  --artifact-backend sqlite \
  --shard-count 4 --shard-index 1
```

### `aft summary`

```bash
aft summary --run-dir runs/my_run/
```

Task-level rollup mode:

```bash
aft summary --run-dir runs/my_run/ --aggregation-level task --task-pass-rule majority
```

### `aft compare`

```bash
aft compare --run-a runs/base/ --run-b runs/candidate/
```

### `aft gate`

```bash
aft gate --run-a runs/base/ --run-b runs/candidate/ --max-regressions 0
```

### `aft analyze`

```bash
aft analyze --run-dir runs/my_run/ --output-json runs/my_run/analytics.json
```

### `aft rejudge`

```bash
aft rejudge --run-dir runs/my_run/ --config examples/config_example.py
```

### `aft merge`

```bash
aft merge --run-dirs runs/shard0/ runs/shard1/ --output-dir runs/merged/
```

### `aft orchestrate`

```bash
aft orchestrate --config examples/config_example.py --shards 4 --output-dir runs/merged_orchestrated/
```

### `aft rank`

```bash
aft rank --run-dir runs/my_run/
```

### `aft migrate`

```bash
aft migrate --run-dir runs/legacy_run/ --target-schema 1.1.0
```

## Run Artifacts

Each run creates `runs/<run_id>/` containing:

- `results.jsonl` or `artifacts.db`
- `traces.jsonl`
- `run_metadata.json`
- `run_checkpoint.json`
- `agent_outputs.jsonl` (JSONL backend cache, optional)
- `cached_outputs` table in `artifacts.db` (SQLite backend cache, optional)
- `report.html`

## Smoke Test Visualization (2026-02-11)

Recent 5-run local validation matrix:

| Run | Mode | Path | Result | Notes |
| --- | --- | --- | --- | --- |
| R1 | Baseline | `runs/smoke_r1_baseline-5a5f7d3c` | 4/4 (100%) | Control run |
| R2 | Parallel + Shuffle | `runs/smoke_r2_parallel-0e22f470` | 4/4 (100%) | `max_agents_parallel=2`, `max_tasks_parallel=4`, seed=123 |
| R3 | SQLite + Cache | `runs/smoke_r3_sqlite_cache-5890a078` | 4/4 (100%) | SQLite artifacts and cached outputs |
| R4 | Resume/Checkpoint | `runs/smoke_r4_resume-e3bb2645` | 1/1 -> 4/4 (100%) | Early stop then resumed to completion |
| R5 | Orchestrated Shards | `runs/smoke_r5_orchestrated` | 4/4 (100%) | 2 shards + merged output |

Validation checks:

- `summary` on R1: pass rate 100%
- `compare` R1 vs R2: delta 0.00%, regressions 0
- `gate` R1 vs R2: passed
- `analyze` on R3: pass rate 100%, macro scenario rate 100%
- `rejudge` on cached outputs: 4/4 passed

Pass-rate bars:

- R1: `██████████` 100%
- R2: `██████████` 100%
- R3: `██████████` 100%
- R4: `██████████` 100% (after resume)
- R5: `██████████` 100%

## Extended Functionality Guide

A comprehensive guide for all updated functionality is available at:

- `docs/UPDATED_FUNCTIONALITY.md`

## Testing

AgentFT includes 90+ automated tests across runner behavior, storage backends, reporting, CLI, presets, plugins, and resilience checks.

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

Optional columnar export dependency:

```bash
pip install -e ".[columnar]"
```

## Project Status

AgentFT is in active development.

**Current version: 0.1.0**

## Links

- **PyPI**: https://pypi.org/project/agentft/
- **GitHub**: https://github.com/Geddydukes/agentflowtest
- **API Stability**: `docs/API_STABILITY.md`
- **Governance**: `docs/GOVERNANCE.md`
- **Docs Map**: `docs/DOCS_UNIFICATION.md`
