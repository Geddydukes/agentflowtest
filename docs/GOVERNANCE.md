# Governance and Compliance

## Data Handling

- Run artifacts may contain model outputs and task inputs.
- Teams should avoid storing raw PII in benchmark tasks.
- Use run retention policies aligned with internal compliance.

## Recommended Retention Defaults

- `results.jsonl` / `artifacts.db`: 90 days.
- `traces.jsonl`: 30 days (contains verbose internals).
- `agent_outputs.jsonl`: 30 days unless needed for rejudge.

## License and Dependencies

- Project license: MIT.
- External plugin packages must be reviewed for license compatibility before production use.

## Security Expectations

- Prefer declarative `--config-json --strict-config` in shared CI.
- Restrict plugin install sources.
- Treat model/tool credentials as secrets managed by the execution environment.

## Change Governance

- All benchmark changes should be code-reviewed.
- Reproducibility-critical changes should include seeded regression tests.
