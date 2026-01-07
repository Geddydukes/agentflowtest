# Agent Flow Test (AgentFT)

Agent Flow Test (AgentFT) is an evaluation framework for AI agents. It provides core abstractions for tasks, scenarios, agents, and judges, with an async runner that supports retries, rate limiting, and comprehensive reporting.

## Features

- **Core abstractions**: Task, Scenario, AgentAdapter, Judge, and CompositeJudge
- **Async execution**: Built-in retry logic, fail-fast behavior, and provider-based rate limiting
- **Lifecycle hooks**: Setup, reset, and teardown methods for agent management
- **Comprehensive reporting**: HTML reports, JSONL results, traces, and metadata
- **Run comparison**: Compare multiple runs to identify regressions and improvements
- **Presets**: Ready-to-use scenarios and judges for quick evaluation
- **CLI**: Command-line interface for running evaluations and viewing results

## Installation

```bash
pip install agentft
```

## Quick start

### Using the CLI

```bash
# Run an evaluation
aft run --config examples/my_config.py

# View summary of a run
aft summary --run-dir runs/my_run-abc123/

# Compare two runs
aft compare --run-a runs/run1/ --run-b runs/run2/
```

### Using Python API

```python
from agentbench import (
    RunConfig,
    run,
    build_math_basic_scenario,
    ExactMatchJudge,
)


class SimpleMathAgent:
    name = "simple_math_agent"
    version = "0.0.1"
    provider_key = None

    async def setup(self) -> None:
        return None

    async def reset(self) -> None:
        return None

    async def teardown(self) -> None:
        return None

    async def run_task(self, task, context=None):
        prompt = task.input["prompt"]
        if "2 + 3" in prompt:
            response = "5"
        elif "4 * 7" in prompt:
            response = "28"
        else:
            response = "I do not know yet"
        return {"response": response}


scenario = build_math_basic_scenario()
agent = SimpleMathAgent()
judge = ExactMatchJudge()

config = RunConfig(
    name="math_example",
    agents=[agent],
    scenarios=[scenario],
    judges=[judge],
)

results = run(config)
print(f"Got {sum(1 for r in results if r.passed)} / {len(results)} passing results.")
```

## CLI Commands

### `aft run`

Run an evaluation from a Python config file.

```bash
aft run --config path/to/config.py
```

The config file should define a `RunConfig` object named `config`.

### `aft summary`

Show a summary of a completed run.

```bash
aft summary --run-dir runs/my_run-abc123/
```

### `aft compare`

Compare two runs to identify regressions and improvements.

```bash
aft compare --run-a runs/run1/ --run-b runs/run2/
```

## Run artifacts

Running an evaluation creates a directory under `runs/<run_id>/` with:

- **results.jsonl**: All evaluation results in JSONL format
- **traces.jsonl**: Event traces for debugging and analysis
- **run_metadata.json**: Run configuration, environment, and version information
- **report.html**: Interactive HTML report with statistics, per-agent performance, and failing tasks

Open `report.html` in your browser to view the detailed evaluation report.

## Testing

AgentFT includes a comprehensive test suite with 43+ tests covering all major components:

- Core types (Task, Cost, EvaluationResult, Trace)
- Scenarios and presets
- Judges (ExactMatchJudge, CompositeJudge)
- Runner and lifecycle hooks
- Storage and reporting functions
- Integration tests

Run tests:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Generate HTML test report
pytest --html=test-results/report.html --self-contained-html

# Generate coverage report
pytest --cov=src/agentbench --cov-report=html:htmlcov
```

Test reports are generated in `test-results/` and coverage reports in `htmlcov/`.

## Project status

Agent Flow Test (AgentFT) is in active development. The core framework is functional and ready for evaluation use cases.

**Current version: 0.0.1**

## Links

- **PyPI**: https://pypi.org/project/agentft/
- **GitHub**: https://github.com/geddydukes/agentflowtest
