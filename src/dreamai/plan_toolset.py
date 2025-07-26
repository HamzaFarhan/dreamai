from enum import StrEnum
from typing import Annotated, Any

from loguru import logger
from pydantic import AfterValidator, BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from dreamai.toolsets import AgentDeps


class RecommendedTool(BaseModel):
    recommended_tool_name: str
    recommended_tool_parameters: dict[str, Any]


class Step(BaseModel):
    step_number: Annotated[int, AfterValidator(lambda x: max(x, 1))] = Field(
        description="The sequential number of the step in the plan. Starts at 1."
    )
    instructions: str = Field(
        description=(
            "Atomic, execution‑ready instructions for this single step. "
            "Assume a smaller AI model with no context; spell out everything. "
            "Produce exactly one result table or artifact per step. "
            "If reading data, specify full file paths. "
            "If the task involves time‑based metrics, include the approved as‑of date "
            "and build a point‑in‑time snapshot "
            "(for example, one row per subscription active as of that date). "
            "Never sum multiple periods then annualize unless the step explicitly says so. "
            "End with 1–2 acceptance criteria and a quick QA check."
        )
    )

    toolset_name: str = Field(
        default="none",
        description="The name of the toolset to fetch for the step. Set to 'none' if no toolset is needed.",
    )
    # recommended_tools: list[str] = Field(default_factory=list, description="The tool(s) to use for the step.")


class PlanStepStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanStep(Step):
    status: PlanStepStatus = Field(default=PlanStepStatus.PENDING)
    # result: Any | None = None

    def __str__(self) -> str:
        res = f"<plan_step>\n<step_number>{self.step_number}</step_number>\n<instructions>{self.instructions}</instructions>\n<toolset_name>{self.toolset_name}</toolset_name>\n</plan_step>\n"
        # TODO: ADD RECOMMENDED TOOLS BACK LATER
        # TODO: ADD STATUS BACK LATER
        # TODO: ADD RESULT BACK LATER
        return res.strip()


class Plan(BaseModel):
    task: str = Field(description="The user's task to be executed.")
    steps: dict[int, PlanStep] = Field(default_factory=dict)  # type: ignore

    def add_steps(self, steps: list[Step | PlanStep] | Step | PlanStep):
        for step in sorted(
            steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number
        ):
            self.steps[step.step_number] = PlanStep(**step.model_dump())

    # def mark_step_completed(self, step_number: int, result: Any | None = None):
    #     self.steps[step_number].status = PlanStepStatus.COMPLETED
    #     self.steps[step_number].result = result

    def get_step(self, step_number: int) -> PlanStep | None:
        return self.steps.get(step_number)

    def get_completed_steps(self) -> list[PlanStep]:
        return [
            step for step in self.steps.values() if step.status == PlanStepStatus.COMPLETED
        ]

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
        )


def present_plan(ctx: RunContext[AgentDeps], plan: str) -> str:
    """
    Present the complete plan to the user in non‑technical language.
    Must include: the as‑of date, assumptions/questions, explicit deliverables, and consent gates for optional artifacts (e.g., Excel workbooks).
    Do not mention internal tools or toolsets.
    Ask the user to confirm: (a) the as‑of date, (b) assumptions, and (c) whether to create optional artifacts.
    """
    ctx.deps.presented_plan = plan
    return plan


class LooksGood(BaseModel): ...


class NeedsRevision(BaseModel):
    suggestions: str = Field(
        description="Suggestions for revising the steps with respect to the task and the user approved plan. "
    )


async def _review_steps(
    task: str, approved_plan: str, steps: list[Step | PlanStep]
) -> LooksGood | NeedsRevision:
    reviewer_agent = Agent(
        model="google-gla:gemini-2.5-flash",
        instructions=(
            "Given the task and the user approved plan, "
            "you have to identify if the internal plan steps are correct "
            "and execution-ready. So no steps omitted and no extra steps added.\n"
            "If they are, return a LooksGood response. "
            "If not, return a NeedsRevision response with suggestions for revision."
        ),
        output_type=[LooksGood, NeedsRevision],
    )
    reviewer_prompt = (
        f"<task>\n{task}\n</task>\n"
        f"<approved_plan>\n{approved_plan}\n</approved_plan>\n"
        f"<steps>\n{'\n'.join(str(step) for step in steps)}\n</steps>\n"
    )
    try:
        return (await reviewer_agent.run(user_prompt=reviewer_prompt)).output
    except Exception as e:
        logger.error(f"Error reviewing steps: {e}")
        return LooksGood()


async def create_plan(
    ctx: RunContext[AgentDeps], task: str, steps: list[Step | PlanStep]
) -> Plan:
    """
    Create the internal, execution‑ready plan only after the user approves `present_plan`.
    Steps must be minimal and atomic, with one output per step and explicit filenames/locations.
    Each step should include acceptance criteria and a brief QA check.
    """
    if ctx.deps.presented_plan is None:
        raise ModelRetry(
            "No plan has been presented to the user. Please present a plan first."
        )
    if not steps:
        raise ModelRetry("No steps provided. Please provide a list of steps.")

    steps_review = await _review_steps(
        task=task, approved_plan=ctx.deps.presented_plan, steps=steps
    )
    if isinstance(steps_review, NeedsRevision):
        raise ModelRetry(f"Steps need revision: {steps_review.suggestions}\n")
    plan = Plan(task=task)
    plan.add_steps(steps)
    return plan
