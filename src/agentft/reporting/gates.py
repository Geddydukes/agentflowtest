from dataclasses import dataclass
from typing import Any, List


@dataclass
class RegressionGateConfig:
    max_regressions: int = 0
    min_delta_pass_rate: float | None = None
    max_p_value: float | None = None
    max_missing_in_run_b: int | None = None
    max_missing_in_run_a: int | None = None


def evaluate_regression_gate(comparison: dict[str, Any], gate: RegressionGateConfig) -> tuple[bool, List[str]]:
    reasons: List[str] = []

    regressions = len(comparison.get("regressions", []))
    if regressions > gate.max_regressions:
        reasons.append(f"regressions {regressions} > {gate.max_regressions}")

    delta = float(comparison.get("delta_pass_rate", 0.0))
    if gate.min_delta_pass_rate is not None and delta < gate.min_delta_pass_rate:
        reasons.append(f"delta_pass_rate {delta:.6f} < {gate.min_delta_pass_rate:.6f}")

    p_value = comparison.get("p_value")
    if gate.max_p_value is not None and p_value is not None and p_value > gate.max_p_value:
        reasons.append(f"p_value {p_value:.6f} > {gate.max_p_value:.6f}")

    missing_b = len(comparison.get("missing_in_run_b", []))
    if gate.max_missing_in_run_b is not None and missing_b > gate.max_missing_in_run_b:
        reasons.append(f"missing_in_run_b {missing_b} > {gate.max_missing_in_run_b}")

    missing_a = len(comparison.get("missing_in_run_a", []))
    if gate.max_missing_in_run_a is not None and missing_a > gate.max_missing_in_run_a:
        reasons.append(f"missing_in_run_a {missing_a} > {gate.max_missing_in_run_a}")

    return (len(reasons) == 0, reasons)
