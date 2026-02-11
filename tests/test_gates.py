"""Tests for regression gate helpers."""

from agentft.reporting.gates import RegressionGateConfig, evaluate_regression_gate


def test_evaluate_regression_gate_passes():
    comparison = {
        "regressions": [],
        "delta_pass_rate": 0.1,
        "p_value": 0.01,
        "missing_in_run_b": [],
        "missing_in_run_a": [],
    }
    gate = RegressionGateConfig(
        max_regressions=0,
        min_delta_pass_rate=0.0,
        max_p_value=0.05,
        max_missing_in_run_b=0,
        max_missing_in_run_a=0,
    )
    passed, reasons = evaluate_regression_gate(comparison, gate)
    assert passed is True
    assert reasons == []


def test_evaluate_regression_gate_fails():
    comparison = {
        "regressions": [{"x": 1}],
        "delta_pass_rate": -0.1,
        "p_value": 0.5,
        "missing_in_run_b": [{"x": 1}],
        "missing_in_run_a": [{"x": 1}],
    }
    gate = RegressionGateConfig(
        max_regressions=0,
        min_delta_pass_rate=0.0,
        max_p_value=0.05,
        max_missing_in_run_b=0,
        max_missing_in_run_a=0,
    )
    passed, reasons = evaluate_regression_gate(comparison, gate)
    assert passed is False
    assert len(reasons) >= 3
