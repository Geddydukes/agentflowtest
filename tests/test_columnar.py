from datetime import datetime

import pytest

from agentft.core.result import EvaluationResult
from agentft.reporting.columnar import export_results_to_parquet


def test_export_results_to_parquet_requires_duckdb(tmp_path):
    rows = [
        EvaluationResult(
            run_id="r",
            task_id="1",
            scenario="s",
            agent="a",
            judge="j",
            raw_input={},
            agent_output={},
            scores={},
            passed=True,
            created_at=datetime.utcnow(),
        )
    ]
    try:
        import duckdb  # type: ignore # noqa: F401
    except Exception:
        with pytest.raises(ImportError):
            export_results_to_parquet(rows, str(tmp_path / "out.parquet"))
    else:
        out = export_results_to_parquet(rows, str(tmp_path / "out.parquet"))
        assert (tmp_path / "out.parquet").exists()
        assert out.endswith(".parquet")
