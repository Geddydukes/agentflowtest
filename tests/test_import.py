"""Basic import test to verify package installation."""

from pathlib import Path
import tomllib


def test_import():
    """Test that agentft can be imported and has correct version."""
    import agentft

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    expected_version = pyproject["project"]["version"]
    assert agentft.__version__ == expected_version


def test_import_presets():
    """Test that presets can be imported."""
    from agentft import build_math_basic_scenario, ExactMatchJudge
    
    assert build_math_basic_scenario is not None
    assert ExactMatchJudge is not None


def test_import_core_types():
    """Test that core types can be imported."""
    from agentft import (
        Task,
        ListScenario,
        AgentAdapter,
        Judge,
        CompositeJudge,
        Cost,
        Trace,
        TraceEvent,
        RunConfig,
        RateLimit,
        discover_plugins,
        rejudge_cached_outputs,
        RegressionGateConfig,
        evaluate_regression_gate,
        analyze_results,
        merge_run_dirs,
        rank_agents_elo,
        export_run_to_parquet,
        CSVScenario,
        JSONLScenario,
        HuggingFaceScenario,
        EpisodeScenario,
        rollout_environment,
        JsonlRunEventSink,
        build_coding_basic_scenario,
    )
    
    assert Task is not None
    assert ListScenario is not None
    assert RunConfig is not None
    assert discover_plugins is not None
    assert rejudge_cached_outputs is not None
    assert RegressionGateConfig is not None
    assert evaluate_regression_gate is not None
    assert analyze_results is not None
    assert merge_run_dirs is not None
    assert rank_agents_elo is not None
    assert export_run_to_parquet is not None
    assert CSVScenario is not None
    assert JSONLScenario is not None
    assert HuggingFaceScenario is not None
    assert EpisodeScenario is not None
    assert rollout_environment is not None
    assert JsonlRunEventSink is not None
    assert build_coding_basic_scenario is not None
