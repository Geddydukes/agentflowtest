"""Example using agentbench presets for a simple math evaluation."""

from agentbench import RunConfig, run, build_math_basic_scenario, ExactMatchJudge, Task


class SimpleMathAgent:
    """Simple hardcoded math agent for demonstration."""

    name = "simple_math_agent"
    version = "0.0.1"
    provider_key = None

    async def setup(self) -> None:
        """Called once before any tasks."""
        return None

    async def reset(self) -> None:
        """Called before each scenario."""
        return None

    async def teardown(self) -> None:
        """Called after all tasks are complete."""
        return None

    async def run_task(self, task: Task, context=None):
        """Execute the agent for a single task."""
        prompt = task.input["prompt"]
        if "2 + 3" in prompt:
            response = "5"
        elif "4 * 7" in prompt:
            response = "28"
        elif "10 - 4" in prompt:
            response = "6"
        elif "15 / 3" in prompt:
            response = "5"
        else:
            response = "I do not know yet"

        return {"response": response}


if __name__ == "__main__":
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

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"Got {passed} / {total} passing results.")

    run_id = results[0].run_id if results else "unknown"
    run_dir = f"runs/{run_id}"
    print(f"\nRun directory: {run_dir}/")
    print("  - results.jsonl")
    print("  - traces.jsonl")
    print("  - run_metadata.json")
    print("  - report.html (open in browser to view detailed report)")

