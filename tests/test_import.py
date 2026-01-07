"""Basic import test to verify package installation."""


def test_import():
    """Test that agentft can be imported and has correct version."""
    import agentft

    assert agentft.__version__ == "0.1.0"


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
    )
    
    assert Task is not None
    assert ListScenario is not None
    assert RunConfig is not None

