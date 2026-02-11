from agentft import Episode, EpisodeScenario, rollout_environment


def test_episode_scenario_to_tasks():
    scenario = EpisodeScenario(
        name="eps",
        episodes=[
            Episode(id="e1", initial_observation={"x": 1}, goal={"done": True}, metadata={"k": "v"}),
            Episode(id="e2", initial_observation={"x": 2}),
        ],
    )
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 2
    assert tasks[0].id == "e1"
    assert tasks[0].input["observation"] == {"x": 1}
    assert tasks[0].expected == {"done": True}


def test_rollout_environment_builds_episode_scenario():
    class ToyEnv:
        def __init__(self):
            self._value = 0

        def reset(self, seed=None):
            self._value = 0
            return {"value": self._value}

        def step(self, action):
            self._value += int(action)
            done = self._value >= 2
            return {"value": self._value}, 1.0, done, {"value": self._value}

    def policy(obs, step, info):
        return 1

    scenario = rollout_environment(ToyEnv(), policy=policy, num_episodes=2, max_steps=3, seed=123)
    tasks = list(scenario.iter_tasks())
    assert len(tasks) == 2
    assert tasks[0].metadata is not None
    assert tasks[0].metadata["num_steps"] >= 1
