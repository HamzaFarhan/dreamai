from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.toolsets import AbstractToolset


class Mode(StrEnum):
    PLAN = "plan"
    ACT = "act"


class AgentDeps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    toolsets: dict[str, AbstractToolset[Any]] = Field(default_factory=dict)
    mode: Mode = Mode.PLAN
    plan_path: Path = Path("plan.md")
    fetched_toolset: str | None = None

    def update_plan(self, new_plan: str):
        self.plan_path.write_text(new_plan.strip())

    @property
    def plan(self) -> str | None:
        return self.plan_path.read_text().strip() if self.plan_path.exists() else None
