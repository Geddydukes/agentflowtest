"""Basic import test to verify package installation."""


def test_import():
    """Test that agentbench can be imported and has correct version."""
    import agentbench

    assert agentbench.__version__ == "0.0.1"


def test_import_presets():
    """Test that presets can be imported."""
    from agentbench import build_math_basic_scenario, ExactMatchJudge
    
    assert build_math_basic_scenario is not None
    assert ExactMatchJudge is not None


def test_import_core_types():
    """Test that core types can be imported."""
    from agentbench import (
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
    )
    
    assert Task is not None
    assert ListScenario is not None
    assert RunConfig is not None

