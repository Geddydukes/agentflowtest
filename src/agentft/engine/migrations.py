from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from agentft.engine.storage import load_jsonl, write_jsonl


def _normalize_result_row(row: dict[str, Any], target_schema: str) -> tuple[dict[str, Any], bool]:
    changed = False
    normalized = dict(row)

    if normalized.get("schema_version") != target_schema:
        normalized["schema_version"] = target_schema
        changed = True

    defaults = {
        "scenario": "",
        "error": None,
        "error_type": None,
        "retries_attempted": 0,
        "metadata": normalized.get("metadata"),
    }
    for key, value in defaults.items():
        if key not in normalized:
            normalized[key] = value
            changed = True

    if "created_at" not in normalized or not normalized["created_at"]:
        normalized["created_at"] = datetime.utcnow().isoformat()
        changed = True

    cost = normalized.get("cost")
    if isinstance(cost, dict):
        before = dict(cost)
        cost.setdefault("total_usd", 0.0)
        cost.setdefault("breakdown", {})
        cost.setdefault("model", None)
        if cost != before:
            changed = True
        normalized["cost"] = cost

    return normalized, changed


def migrate_run_artifacts(
    run_dir: str,
    *,
    target_schema: str = "1.1.0",
    backup: bool = True,
) -> dict[str, Any]:
    run_path = Path(run_dir)
    results_path = run_path / "results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"results.jsonl not found in run dir: {run_dir}")

    rows = load_jsonl(str(results_path))
    migrated = []
    rows_migrated = 0
    rows_unchanged = 0
    for row in rows:
        normalized, changed = _normalize_result_row(row, target_schema)
        migrated.append(normalized)
        if changed:
            rows_migrated += 1
        else:
            rows_unchanged += 1

    backup_path = None
    if backup:
        backup_path = str(run_path / "results.pre_migration.jsonl")
        shutil.copy2(results_path, backup_path)

    write_jsonl(str(results_path), migrated)

    metadata_path = run_path / "run_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["artifact_schema_version"] = target_schema
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")

    checkpoint_path = run_path / "run_checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint["schema_version"] = target_schema
        checkpoint_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=True), encoding="utf-8")

    return {
        "target_schema": target_schema,
        "rows_total": len(rows),
        "rows_migrated": rows_migrated,
        "rows_unchanged": rows_unchanged,
        "backup_path": backup_path,
    }
