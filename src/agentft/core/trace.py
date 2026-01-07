from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class TraceEvent:
    timestamp: float
    event_type: str
    data: Dict[str, Any]


@dataclass
class Trace:
    run_id: str
    task_id: str
    agent: str
    events: List[TraceEvent] = field(default_factory=list)

