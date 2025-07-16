from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field
from pydantic_ai import ModelRetry


class RecommendedTool(BaseModel):
    recommended_tool_name: str
    recommended_tool_parameters: dict[str, Any]


class Step(BaseModel):
    step_number: Annotated[int, AfterValidator(lambda x: max(x, 1))] = Field(
        description="The sequential number of the step in the plan. Starts at 1."
    )
    instructions: str = Field(
        description=(
            "Clear, specific instructions for this step. Write these for a smaller AI model that "
            "needs explicit guidance and cannot infer context or handle ambiguity well. "
            "Be concrete, avoid complex reasoning, and include all necessary details."
        )
    )
    toolset_name: str = Field(
        description="The name of the toolset to fetch for the step. Set to 'none' if no toolset is needed."
    )
    recommended_tools: list[str] = Field(description="The tool(s) to use for the step.")


class PlanStepStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(Step):
    status: PlanStepStatus = Field(default=PlanStepStatus.PENDING)
    result: Any | None = None

    def __str__(self) -> str:
        res = f"<plan_step>\n<step_number>{self.step_number}</step_number>\n<instructions>{self.instructions}</instructions>\n<toolset_name>{self.toolset_name}</toolset_name>\n<recommended_tools>{self.recommended_tools}</recommended_tools>\n<status>{self.status.value}</status>\n<result>{self.result}</result>\n</plan_step>\n"
        return res.strip()


class Plan(BaseModel):
    task: str = Field(description="The user's task to be executed.")
    steps: dict[int, PlanStep] = Field(default_factory=dict)

    def add_steps(self, steps: list[Step | PlanStep] | Step | PlanStep):
        for step in sorted(steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number):
            self.steps[step.step_number] = PlanStep(**step.model_dump())

    def mark_step_completed(self, step_number: int, result: Any | None = None):
        self.steps[step_number].status = PlanStepStatus.COMPLETED
        self.steps[step_number].result = result

    def get_step(self, step_number: int) -> PlanStep | None:
        return self.steps.get(step_number)

    def get_completed_steps(self) -> list[PlanStep]:
        return [step for step in self.steps.values() if step.status == PlanStepStatus.COMPLETED]

    def completed_steps_str(self) -> str:
        return (
            f"<completed_steps>\n"
            f"{'\n'.join(str(step) for step in self.get_completed_steps())}\n"
            f"</completed_steps>\n"
        )

    def get_next_pending_step(self) -> PlanStep | None:
        for step in self.steps.values():
            if step.status == PlanStepStatus.PENDING:
                return step
        return None

    def next_pending_step_str(self) -> str:
        return f"<next_pending_step>\n{str(self.get_next_pending_step())}\n</next_pending_step>\n"

    def __str__(self) -> str:
        return (
            f"<task>\n{self.task}\n</task>\n"
            f"<plan>\n"
            f"{'\n'.join(str(step) for step in self.steps.values())}\n"
            f"</plan>\n"
            "You may complete multiple steps in one go if you think it's appropriate."
        )


def present_plan(plan: str) -> str:
    """
    Present the complete plan to the user.
    This will not mention the tools/toolsets because the user is not technical.
    """
    return plan


def create_plan(task: str, steps: list[Step | PlanStep]) -> Plan:
    """Create the actual plan."""
    if not steps:
        raise ModelRetry("No steps provided. Please provide a list of steps.")
    plan = Plan(task=task)
    plan.add_steps(steps)
    return plan
