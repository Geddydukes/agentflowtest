from datetime import datetime
from pathlib import Path
from typing import Any

import agentft
from agentft.core.metadata import RunMetadata
from agentft.core.result import EvaluationResult
from agentft.engine.storage import load_results_from_run_dir, write_results_jsonl, write_metadata_json
from agentft.reporting.html_report import generate_html_report


def merge_run_dirs(
    run_dirs: list[str],
    output_dir: str,
    run_name: str = "merged_run",
    dedupe: bool = True,
) -> dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    merged: list[EvaluationResult] = []
    seen: set[tuple[str, str, str, str]] = set()
    for run_dir in run_dirs:
        rows = load_results_from_run_dir(run_dir)
        for r in rows:
            key = (r.scenario, r.task_id, r.agent, r.judge)
            if dedupe and key in seen:
                continue
            seen.add(key)
            merged.append(r)

    if not merged:
        raise ValueError("No results found to merge.")

    run_id = f"{run_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    for r in merged:
        r.run_id = run_id

    results_path = str(out_dir / "results.jsonl")
    metadata_path = str(out_dir / "run_metadata.json")
    report_path = str(out_dir / "report.html")

    write_results_jsonl(merged, results_path, schema_version="1.1.0")

    metadata = RunMetadata(
        run_id=run_id,
        name=run_name,
        framework_version=agentft.__version__,
        agent_versions={},
        scenario_versions={},
        judge_versions={},
        environment_state={"merged_from": run_dirs},
        hardware_info=None,
        created_at=datetime.utcnow(),
        git_commit=None,
        artifact_schema_version="1.1.0",
        status="completed",
        ended_at=datetime.utcnow(),
        resumed_from_run_id=None,
        seed=None,
    )
    write_metadata_json(metadata, metadata_path)
    generate_html_report(metadata, merged, report_path)

    return {
        "run_id": run_id,
        "output_dir": str(out_dir),
        "total_results": len(merged),
    }
