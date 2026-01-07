"""Phase 3 proof of concept using core abstractions."""

from agentbench import Task, ListScenario, RunConfig, run, CompositeJudge


class SimpleMathAgent:
    """Simple hardcoded math agent for demonstration."""

    name = "simple_math_agent"
    version = "0.0.1"
    provider_key = None

    async def setup(self) -> None:
        """Called once before any tasks."""
        pass

    async def reset(self) -> None:
        """Called before each scenario."""
        pass

    async def teardown(self) -> None:
        """Called after all tasks are complete."""
        pass

    async def run_task(self, task, context=None):
        """Execute the agent for a single task."""
        prompt = task.input.get("prompt", "")
        if "2 + 3" in prompt:
            response = "5"
        elif "4 * 7" in prompt:
            response = "28"
        else:
            response = "I do not know yet"

        from agentbench import Cost

        return {"response": response, "cost": Cost.zero()}


class ExactMatchJudge:
    """Judge that compares expected answer to actual response."""

    name = "exact_match"

    async def score(self, task, result):
        """Score the agent output against expected answer."""
        expected_answer = task.expected.get("answer", "") if task.expected else ""
        actual_response = result.get("response", "")

        passed = expected_answer.strip() == actual_response.strip()

        return {
            "scores": {"correctness": 1.0 if passed else 0.0},
            "pass": passed,
            "explanation": None,
            "metadata": None,
        }


if __name__ == "__main__":
    tasks = [
        Task(id="1", input={"prompt": "What is 2 + 3"}, expected={"answer": "5"}),
        Task(id="2", input={"prompt": "What is 4 * 7"}, expected={"answer": "28"}),
    ]

    scenario = ListScenario("math_basic", tasks)
    
    judge = ExactMatchJudge()
    composite_judge = CompositeJudge(judges=[judge], strategy="all")
    
    config = RunConfig(
        name="phase3_math",
        agents=[SimpleMathAgent()],
        scenarios=[scenario],
        judges=[composite_judge],
    )

    results = run(config)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    total_retries = sum(r.retries_attempted for r in results)
    total_cost = sum(r.cost.total_usd if r.cost else 0.0 for r in results)

    print(f"Summary: {passed} / {total} tasks passed")
    print(f"Total retries: {total_retries}")
    print(f"Total cost: ${total_cost:.4f}")
    
    run_id = results[0].run_id if results else "unknown"
    run_dir = f"runs/{run_id}"
    print(f"\nRun directory: {run_dir}/")
    print(f"  - results.jsonl")
    print(f"  - traces.jsonl")
    print(f"  - run_metadata.json")
    print(f"  - report.html")
