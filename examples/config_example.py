"""Example config file for use with 'aft run --config' command."""

from agentft import (
    Task,
    ListScenario,
    RunConfig,
    build_math_basic_scenario,
    ExactMatchJudge,
)


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

    async def run_task(self, task, context=None):
        """Execute the agent for a single task."""
        prompt = task.input.get("prompt", "")
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


scenario = build_math_basic_scenario()
agent = SimpleMathAgent()
judge = ExactMatchJudge()

config = RunConfig(
    name="math_example",
    agents=[agent],
    scenarios=[scenario],
    judges=[judge],
)

