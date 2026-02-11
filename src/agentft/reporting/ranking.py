from __future__ import annotations

import math
from collections import defaultdict

from agentft.core.result import EvaluationResult


def rank_agents_elo(
    results: list[EvaluationResult],
    *,
    initial_rating: float = 1500.0,
    k_factor: float = 24.0,
) -> list[dict[str, float | int | str]]:
    """Compute Elo ratings from pairwise pass/fail outcomes on shared tasks."""
    grouped: dict[tuple[str, str, str], dict[str, bool]] = defaultdict(dict)
    for row in results:
        grouped[(row.scenario, row.task_id, row.judge)][row.agent] = bool(row.passed)

    ratings: dict[str, float] = {}
    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    ties: dict[str, int] = defaultdict(int)
    games: dict[str, int] = defaultdict(int)

    for task_rows in grouped.values():
        agents = sorted(task_rows.keys())
        if len(agents) < 2:
            continue
        for i, a in enumerate(agents):
            for b in agents[i + 1 :]:
                if a not in ratings:
                    ratings[a] = initial_rating
                if b not in ratings:
                    ratings[b] = initial_rating

                pa = task_rows[a]
                pb = task_rows[b]
                score_a = 0.5
                score_b = 0.5
                if pa and not pb:
                    score_a, score_b = 1.0, 0.0
                    wins[a] += 1
                    losses[b] += 1
                elif pb and not pa:
                    score_a, score_b = 0.0, 1.0
                    wins[b] += 1
                    losses[a] += 1
                else:
                    ties[a] += 1
                    ties[b] += 1

                games[a] += 1
                games[b] += 1
                expected_a = 1.0 / (1.0 + math.pow(10.0, (ratings[b] - ratings[a]) / 400.0))
                expected_b = 1.0 - expected_a
                ratings[a] += k_factor * (score_a - expected_a)
                ratings[b] += k_factor * (score_b - expected_b)

    for row in results:
        ratings.setdefault(row.agent, initial_rating)
        wins.setdefault(row.agent, 0)
        losses.setdefault(row.agent, 0)
        ties.setdefault(row.agent, 0)
        games.setdefault(row.agent, 0)

    out = [
        {
            "agent": agent,
            "rating": rating,
            "games": games[agent],
            "wins": wins[agent],
            "losses": losses[agent],
            "ties": ties[agent],
        }
        for agent, rating in ratings.items()
    ]
    out.sort(key=lambda x: float(x["rating"]), reverse=True)
    return out
