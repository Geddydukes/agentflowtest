"""Agent Flow Test (AgentFT): A simple evaluation harness for AI agents."""

__version__ = "0.1.0"

from .core.task import Task
from .core.scenario import Scenario, ListScenario
from .core.agent import AgentAdapter
from .core.judge import Judge
from .core.cost import Cost
from .core.trace import Trace, TraceEvent
from .core.composite_judge import CompositeJudge
from .engine.runner import RunConfig, RateLimit, run, run_async
from .engine.hooks import RunEventSink, JsonlRunEventSink, StdoutJsonEventSink
from .presets.math_basic import build_math_basic_scenario
from .presets.benchmark_suites import (
    build_coding_basic_scenario,
    build_safety_basic_scenario,
    build_tool_use_basic_scenario,
)
from .presets.judges import ExactMatchJudge
from .plugins import PluginRegistry, discover_plugins
from .reporting import (
    rejudge_cached_outputs,
    RegressionGateConfig,
    evaluate_regression_gate,
    analyze_results,
    merge_run_dirs,
    rank_agents_elo,
    export_run_to_parquet,
)
from .scenarios import (
    CSVScenario,
    JSONLScenario,
    HuggingFaceScenario,
    Episode,
    EpisodeScenario,
    StepEnvironment,
    rollout_environment,
)

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
    "RunEventSink",
    "JsonlRunEventSink",
    "StdoutJsonEventSink",
    "build_math_basic_scenario",
    "build_coding_basic_scenario",
    "build_safety_basic_scenario",
    "build_tool_use_basic_scenario",
    "ExactMatchJudge",
    "PluginRegistry",
    "discover_plugins",
    "rejudge_cached_outputs",
    "RegressionGateConfig",
    "evaluate_regression_gate",
    "analyze_results",
    "merge_run_dirs",
    "rank_agents_elo",
    "export_run_to_parquet",
    "CSVScenario",
    "JSONLScenario",
    "HuggingFaceScenario",
    "Episode",
    "EpisodeScenario",
    "StepEnvironment",
    "rollout_environment",
]
