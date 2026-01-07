from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .cost import Cost


@dataclass
class EvaluationResult:
    run_id: str
    task_id: str
    scenario: str
    agent: str
    judge: str
    raw_input: Dict[str, Any]
    agent_output: Dict[str, Any]
    scores: Dict[str, float]
    passed: bool
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.utcnow()
    cost: Optional[Cost] = None
    error: str | None = None
    error_type: str | None = None
    retries_attempted: int = 0

