"""agentbench: A simple evaluation harness for AI agents."""

__version__ = "0.0.1"

from .core.task import Task
from .core.scenario import Scenario, ListScenario
from .core.agent import AgentAdapter
from .core.judge import Judge
from .core.cost import Cost
from .core.trace import Trace, TraceEvent
from .core.composite_judge import CompositeJudge
from .engine.runner import RunConfig, RateLimit, run, run_async
from .presets.math_basic import build_math_basic_scenario
from .presets.judges import ExactMatchJudge

__all__ = [
    "__version__",
    "Task",
    "Scenario",
    "ListScenario",
    "AgentAdapter",
    "Judge",
    "CompositeJudge",
    "Cost",
    "Trace",
    "TraceEvent",
    "RunConfig",
    "RateLimit",
    "run",
    "run_async",
    "build_math_basic_scenario",
    "ExactMatchJudge",
]
