from datetime import datetime

from agentft.core.result import EvaluationResult
from agentft.reporting.ranking import rank_agents_elo


def test_rank_agents_elo_basic():
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
        ),
        EvaluationResult(
            run_id="r",
            task_id="1",
            scenario="s",
            agent="b",
            judge="j",
            raw_input={},
            agent_output={},
            scores={},
            passed=False,
            created_at=datetime.utcnow(),
        ),
    ]
    rankings = rank_agents_elo(rows)
    assert len(rankings) == 2
    assert rankings[0]["agent"] == "a"
    assert rankings[0]["rating"] > rankings[1]["rating"]
