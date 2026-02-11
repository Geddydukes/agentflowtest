from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from agentft.core.task import Task


class StepEnvironment(Protocol):
    """Simple step-based environment protocol."""

    def reset(self, seed: int | None = None) -> Any:
        ...

    def step(self, action: Any) -> tuple[Any, float, bool, dict[str, Any]]:
        ...


@dataclass
class Episode:
    id: str
    initial_observation: Any
    goal: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class EpisodeScenario:
    """Scenario backed by predefined episodes."""

    def __init__(self, name: str, episodes: Iterable[Episode]) -> None:
        self.name = name
        self._episodes = list(episodes)

    def iter_tasks(self) -> list[Task]:
        tasks: list[Task] = []
        for episode in self._episodes:
            tasks.append(
                Task(
                    id=episode.id,
                    input={"observation": episode.initial_observation},
                    expected=episode.goal,
                    metadata=episode.metadata,
                )
            )
        return tasks


def rollout_environment(
    env: StepEnvironment,
    *,
    policy,
    num_episodes: int,
    max_steps: int = 20,
    seed: int = 42,
    scenario_name: str = "episode_env",
) -> EpisodeScenario:
    """
    Create an EpisodeScenario by rolling out an environment with a policy.

    `policy(observation, step_index, info) -> action`
    """
    episodes: list[Episode] = []
    for i in range(num_episodes):
        obs = env.reset(seed=seed + i)
        initial_obs = obs
        transitions: list[dict[str, Any]] = []
        final_reward = 0.0
        done = False
        for step_idx in range(max_steps):
            action = policy(obs, step_idx, {"episode_index": i})
            next_obs, reward, done, info = env.step(action)
            transitions.append(
                {
                    "step": step_idx,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                }
            )
            obs = next_obs
            final_reward += float(reward)
            if done:
                break

        episodes.append(
            Episode(
                id=f"episode_{i}",
                initial_observation=initial_obs,
                goal={"done": done},
                metadata={
                    "episode_index": i,
                    "num_steps": len(transitions),
                    "total_reward": final_reward,
                    "transitions": transitions,
                },
            )
        )
    return EpisodeScenario(name=scenario_name, episodes=episodes)
