# AgentFT

**Agent Flow Test** - Pytest for AI agents

[![PyPI](https://img.shields.io/pypi/v/agentft)](https://pypi.org/project/agentft/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AgentFT (Agent Flow Test) is a pytest-style evaluation framework for AI agents. It provides composable primitives for tasks, scenarios, agents, and judges, with production-ready infrastructure including async execution, retries, rate limiting, and comprehensive reporting.

## Features

- **Pytest-like simplicity**: Minimal boilerplate, clear abstractions
- **Production-ready**: Async execution with retries and rate limiting  
- **Full observability**: Traces, costs, metadata, HTML reports
- **Composable judges**: Layer multiple evaluation strategies (sequential, voting, weighted)
- **Environment support**: Not just Q&A - full stateful agent evaluation
- **CLI tools**: Run evals, view summaries, compare runs

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
from agentft import Task, RunConfig, run
from agentft.presets import build_math_basic_scenario, ExactMatchJudge

# Define your agent
class MyAgent:
    name = "my_agent"
    version = "0.1.0"
    provider_key = None
    
    async def setup(self): pass
    async def reset(self): pass
    async def teardown(self): pass
    
    async def run_task(self, task, context=None):
        # Your agent logic here
        return {"response": "42"}

# Create evaluation config
config = RunConfig(
    name="quick_test",
    agents=[MyAgent()],
    scenarios=[build_math_basic_scenario()],
    judges=[ExactMatchJudge()],
)

# Run evaluation
results = run(config)
print(f"Passed: {sum(r.passed for r in results)}/{len(results)}")
```

View results:
- **Console**: Summary printed automatically
- **HTML**: Open `runs/<run_id>/report.html` in browser
- **Raw data**: `runs/<run_id>/results.jsonl`

## Why AgentFT?

**Existing eval frameworks are either too simple or too complex:**

- Simple tools: Just run prompts, no structure or observability
- Academic benchmarks: Steep learning curve, not designed for iteration
- Vendor platforms: Lock-in, limited customization

**AgentFT hits the sweet spot:**

- Pytest-like API (minimal boilerplate)
- Production-ready features (async, retries, rate limiting)
- Full transparency (traces, costs, metadata)
- Works for simple Q&A through complex multi-step agents

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

## Run Artifacts

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
pytest --cov=src/agentft --cov-report=html:htmlcov
```

Test reports are generated in `test-results/` and coverage reports in `htmlcov/`.

## Project Status

Agent Flow Test (AgentFT) is in active development. The core framework is functional and ready for evaluation use cases.

**Current version: 0.1.0**

## Links

- **PyPI**: https://pypi.org/project/agentft/
- **GitHub**: https://github.com/Geddydukes/agentflowtest
