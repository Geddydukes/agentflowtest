from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class RunMetadata:
    run_id: str
    name: str
    framework_version: str
    agent_versions: Dict[str, str]
    scenario_versions: Dict[str, str]
    judge_versions: Dict[str, str]
    environment_state: Dict[str, Any]
    hardware_info: Optional[Dict[str, Any]]
    created_at: datetime
    git_commit: Optional[str]

