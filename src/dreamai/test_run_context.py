from dataclasses import dataclass
from typing import TypeVar

AgentDepsT = TypeVar("AgentDepsT", default=None, contravariant=True)  # type: ignore


@dataclass
class RunContext[AgentDepsT]:
    deps: AgentDepsT
