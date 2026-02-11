# AgentFT Updated Functionality Guide

## 1. Overview

This document summarizes the expanded AgentFT framework capabilities now implemented across execution, storage, reporting, orchestration, scenarios, and governance.

Core themes of the update:

- stronger reliability and reproducibility controls
- richer analysis and regression workflows
- safer config and operational governance
- broader scenario support and extensibility

## 2. Execution Engine Upgrades

### 2.1 Concurrency and Throughput Controls

`RunConfig` now supports independent controls for each dimension:

- `max_agents_parallel`
- `max_tasks_parallel`
- `max_judges_parallel`

This allows balancing throughput by workload type rather than one global parallelism value.

### 2.2 Timeouts and Fail-Fast Boundaries

- `agent_timeout_seconds`
- `judge_timeout_seconds`
- `fail_fast_on` with modes: `none`, `failure`, `error`, `either`

Timeouts are captured into typed error categories and propagated into results.

### 2.3 Retry Policy by Error Type

New behavior combines:

- default retry policy via `max_retries`
- override policy via `retry_policy_by_error_type`

Example:

```python
retry_policy_by_error_type={
    "invalid_request": 0,
    "rate_limited": 5,
    "provider_unavailable": 4,
}
```

### 2.4 Determinism and Sharding

- deterministic task shuffling via `seed` + `shuffle_tasks`
- deterministic shard assignment via `shard_count` + `shard_index`

Shard mapping is stable across runs for identical scenario/task identifiers.

### 2.5 Resume and Checkpointing

- `resume_run_id` resumes an interrupted run
- `run_checkpoint.json` tracks progress and stop reason
- processed `(scenario, task_id, agent, judge)` keys are deduplicated on resume

### 2.6 Budget Guards

Early stop support for resource controls:

- `max_total_cost_usd`
- `max_total_runtime_seconds`

## 3. Artifact and Storage Layer

### 3.1 Backend Abstraction

Supported backends:

- JSONL
- SQLite

Configured via:

- `artifact_backend`
- `sqlite_db_name`

### 3.2 Schema Versioning

Artifacts carry explicit schema version metadata. Metadata/status fields are maintained through run lifecycle.

### 3.3 Migration Tooling

`aft migrate` and migration APIs normalize legacy rows to target schema:

```bash
aft migrate --run-dir runs/legacy/ --target-schema 1.1.0
```

Migration updates result rows and metadata schema references, with optional backup.

## 4. CLI Surface Expansion

Commands now include:

- `run`
- `summary`
- `compare`
- `rejudge`
- `gate`
- `analyze`
- `merge`
- `orchestrate`
- `rank`
- `migrate`

### 4.1 Secure Declarative Config Mode

Use non-executable config path in CI/shared environments:

```bash
aft run --config-json config.json --strict-config
```

Supported strict config scenario types include list/csv/jsonl/huggingface/preset/plugin-based declarations.

### 4.2 Orchestration Command

`aft orchestrate` launches local shard workers, then merges successful shard outputs:

```bash
aft orchestrate --config examples/config_example.py --shards 4 --output-dir runs/merged/
```

Capabilities:

- per-shard run invocation
- controlled worker pool concurrency
- shard result collection
- merged artifact generation

## 5. Reporting, Analytics, and Benchmark Comparison

### 5.1 Summary Aggregation Modes

`build_summary` and CLI summary/analyze now support:

- `aggregation_level="judge"` (default)
- `aggregation_level="task"`

Task-level rollups support pass rules:

- `all`
- `any`
- `majority`

### 5.2 Richer Metrics

Added slices/metrics include:

- latency percentiles (`p50`, `p95`, `p99`)
- per-error-type counts
- Wilson 95% pass-rate confidence interval
- per-agent/per-scenario/per-judge distributions

### 5.3 Statistical Comparison

`compare_runs` includes:

- pass-rate delta
- bootstrap CI
- p-value
- robust missing-row handling
- per-agent delta slices

### 5.4 Regression Gates

`aft gate` operationalizes pass/fail policies based on comparison output.

### 5.5 Ranking

`aft rank` computes Elo rankings from shared-task outcomes:

```bash
aft rank --run-dir runs/my_run/
```

## 6. HTML Report UX Upgrade

`report.html` now provides interactive drilldown behavior:

- filter by agent
- filter by scenario
- filter by pass/fail status
- free-text task/error search

This supports rapid failure triage without external tooling.

## 7. Scenarios and Benchmark Suites

### 7.1 Dataset Scenarios

Implemented scenario adapters:

- `CSVScenario`
- `JSONLScenario`
- `HuggingFaceScenario`

With sampling and optional stratification controls.

### 7.2 Episode Toolkit

Added environment/episode support:

- `Episode`
- `EpisodeScenario`
- `rollout_environment`

This supports stateful benchmark generation from step-based environments.

### 7.3 Preset Benchmark Suites

Added starter suites for:

- coding
- safety
- tool-use

These complement existing math presets.

## 8. Extensibility and Integrations

### 8.1 Plugin Registry

Entry-point plugin groups:

- `agentft.agents`
- `agentft.scenarios`
- `agentft.judges`

### 8.2 Structured External Event Hooks

Run lifecycle hooks are now available via sink interfaces:

- `on_run_start`
- `on_result`
- `on_trace`
- `on_run_end`

Built-in sinks include JSONL and stdout JSON emitters.

### 8.3 Columnar Export Path

Parquet export APIs are available (optional dependency via `duckdb`):

- `export_results_to_parquet`
- `export_run_to_parquet`

## 9. Security, Stability, and Governance

Added governance and lifecycle documentation:

- `docs/API_STABILITY.md`
- `docs/GOVERNANCE.md`
- `docs/DOCS_UNIFICATION.md`

These define semver/deprecation, data handling guidance, and documentation source-of-truth mapping.

## 10. Recommended Workflow Patterns

### 10.1 Safe CI Pipeline

1. run candidate with strict config
2. compare vs baseline
3. apply gate
4. fail CI on regression

Example:

```bash
aft run --config-json ci_config.json --strict-config
aft compare --run-a runs/baseline/ --run-b runs/candidate/
aft gate --run-a runs/baseline/ --run-b runs/candidate/ --max-regressions 0
```

### 10.2 Distributed Local Batch

1. orchestrate shards
2. inspect merged report
3. analyze and rank

Example:

```bash
aft orchestrate --config examples/config_example.py --shards 8 --output-dir runs/merged_large/
aft analyze --run-dir runs/merged_large/ --output-json runs/merged_large/analytics.json
aft rank --run-dir runs/merged_large/
```

### 10.3 Legacy Artifact Upgrade

```bash
aft migrate --run-dir runs/old_format_run/ --target-schema 1.1.0
```

## 11. Validation Status

Current automated validation includes 90+ tests covering:

- runner behavior and resilience paths
- storage backends and migration operations
- reporting/statistical utilities
- CLI commands and new orchestration/ranking/migration paths
- scenario/preset expansions and plugin discovery

## 12. Current Focus Areas

From roadmap status:

1. production hardening and plugin ecosystem validation
2. additional ranking models (e.g., Bradley-Terry)
3. optional native OpenTelemetry exporter package

