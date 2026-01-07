from typing import List
from agentbench import Task, ListScenario


def build_math_basic_scenario() -> ListScenario:
    """Build a basic math scenario with simple arithmetic tasks."""
    tasks: List[Task] = [
        Task(
            id="add_2_3",
            input={"prompt": "What is 2 + 3? Answer with a single number."},
            expected={"answer": "5"},
        ),
        Task(
            id="mul_4_7",
            input={"prompt": "What is 4 * 7? Answer with a single number."},
            expected={"answer": "28"},
        ),
        Task(
            id="sub_10_4",
            input={"prompt": "What is 10 - 4? Answer with a single number."},
            expected={"answer": "6"},
        ),
        Task(
            id="div_15_3",
            input={"prompt": "What is 15 / 3? Answer with a single number."},
            expected={"answer": "5"},
        ),
    ]
    return ListScenario(name="math_basic", tasks=tasks)

