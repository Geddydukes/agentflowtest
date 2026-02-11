from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Dict, Any


@dataclass
class PluginRegistry:
    judges: Dict[str, Any]
    scenarios: Dict[str, Any]
    agents: Dict[str, Any]


def _load_group(group_name: str) -> Dict[str, Any]:
    loaded: Dict[str, Any] = {}
    for ep in entry_points(group=group_name):
        loaded[ep.name] = ep.load()
    return loaded


def discover_plugins() -> PluginRegistry:
    """
    Discover plugin entry points.

    Supported groups:
    - `agentft.judges`
    - `agentft.scenarios`
    - `agentft.agents`
    """
    return PluginRegistry(
        judges=_load_group("agentft.judges"),
        scenarios=_load_group("agentft.scenarios"),
        agents=_load_group("agentft.agents"),
    )
