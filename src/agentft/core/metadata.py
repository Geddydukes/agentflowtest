from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class RunMetadata:
    run_id: str
    name: str
    framework_version: str
    agent_versions: Dict[str, str]
    scenario_versions: Dict[str, Any]
    judge_versions: Dict[str, Any]
    environment_state: Dict[str, Any]
    hardware_info: Optional[Dict[str, Any]]
    created_at: datetime
    git_commit: Optional[str]
    artifact_schema_version: str = "1.1.0"
    status: str = "completed"
    ended_at: Optional[datetime] = None
    resumed_from_run_id: Optional[str] = None
    seed: Optional[int] = None
