from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Task:
    id: str
    input: Dict[str, Any]
    expected: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

