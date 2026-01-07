from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Cost:
    total_usd: float
    breakdown: Optional[Dict[str, float]] = None
    model: Optional[str] = None

    @classmethod
    def zero(cls) -> "Cost":
        return cls(total_usd=0.0, breakdown={})

