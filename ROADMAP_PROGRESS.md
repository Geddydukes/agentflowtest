# AgentFT Roadmap Progress

Legend:
- `[x]` Implemented
- `[ ]` Pending
- `(~)` Partially implemented

## Reliability, Correctness, Security

- [x] Fix correctness blockers (`CompositeJudge` recursion, module `__name__`, fail-fast persistence, HTML autoescape)
- [x] Add real concurrency controls (`max_tasks_parallel`, `max_agents_parallel`, `max_judges_parallel`)
- [x] Add per-call timeouts and cancellation boundaries for agents/judges
- [x] Stream artifacts during execution (append JSONL/SQLite writes during run)
- [x] Add checkpoint/resume support (`resume_run_id`, `run_checkpoint.json`)
- [x] Add deterministic run controls (seeded shuffle + stable hashing)
- [x] Add artifact schema versioning and metadata status fields
- [x] Track retry/error/latency/cost telemetry per result
- [x] Add budget guards (`max_total_cost_usd`, `max_total_runtime_seconds`)
- [x] Add retry policy by exception type + richer error taxonomy
- [x] Add strict secure config mode (non-executable declarative config path)

## Benchmarking and Comparison

- [x] Separate task-level vs judge-level aggregation model
- [x] Add richer aggregation primitives (task pass-rule, latency percentiles, error slices, Wilson CI)
- [x] Add statistical run comparison outputs (delta, bootstrap CI, p-value)
- [x] Add paired/tournament ranking (Elo)
- [x] Add robust missing-row handling in run comparison
- [x] Add regression gate evaluation + CLI command (`aft gate`)
- [x] Add CI sanity gate check in workflow

## Data and Scenarios

- [x] Add dataset adapters (`CSVScenario`, `JSONLScenario`, `HuggingFaceScenario`)
- [x] Add sampling/stratification primitives in dataset scenarios
- [x] Add cache + rejudge workflow (`cache_agent_outputs`, `aft rejudge`)
- [x] Add environment/episode benchmark toolkit
- [x] Add richer preset benchmark suites (coding/safety/tool-use/etc.)

## Extensibility and Storage

- [x] Add plugin registry (`agentft.judges`, `agentft.scenarios`, `agentft.agents`)
- [x] Add artifact backend abstraction with JSONL + SQLite backend
- [x] Add deterministic shard partitioning (`shard_count`, `shard_index`) for distributed-friendly execution
- [x] Add analytics/columnar backend (DuckDB/Parquet export path)
- [x] Add schema migration tooling for historical runs
- [x] Add OpenTelemetry/structured external sink hooks (structured sink hooks implemented)
- [x] Add distributed executor backend (local multi-process shard orchestration + merge)

## Reporting and UX

- [x] Expand HTML report to full interactive drilldown UX
- [x] Improve CLI output for compare/gate with key metrics
- [x] Add dedicated analysis command for deeper slices (scenario/judge/etc.)
- [x] Add merge tooling for sharded/distributed runs
- [x] Increase CLI coverage

## Project Ops and Governance

- [x] Fix naming drift in packaging/CI/docs (`agentbench` -> `agentft` in key files)
- [x] Complete full docs unification map
- [x] Define API stability policy (semver + deprecation lifecycle)
- [x] Add governance/compliance metadata and policies (PII/license/retention)
- [x] Add reference benchmark projects
- [x] Add property/fuzz tests and broader resilience testing

## Current Focus

1. Production hardening and real-world plugin ecosystem validation.
2. Additional ranking models (Bradley-Terry) and calibration diagnostics.
3. Optional OpenTelemetry native exporter integration package.
