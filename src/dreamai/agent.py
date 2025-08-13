from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset


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


async def create_plan_steps(ctx: RunContext[AgentDeps], plan: str) -> str:
    """
    Creates a new sequential markdown plan with systematic steps and presents it to the user.
    These steps are the atomic, unambiguous, sequential steps that you will follow to complete the task.

    Args:
        plan: The sequential steps formatted as markdown.

    Example:
        create_plan_steps(plan="## SEQUENTIAL STEPS\n1. Data preparation: Filter active customers using subscription table\n2. Base calculation: Calculate monthly revenue per customer cohort\n3. Final output: Generate cohort analysis table with retention metrics")
    """
    ctx.deps.mode = Mode.PLAN
    ctx.deps.update_plan(plan)
    return plan


async def update_plan_steps(ctx: RunContext[AgentDeps], old_text: str, new_text: str):
    """
    Updates existing content in the plan.

    This function is typically used to **mark plan steps as completed** or to tweak their wording. It
    replaces all occurrences of `old_text` in the plan.

    **TOKEN-EFFICIENT BUT FEWER CALLS:**
    • Prefer bundling several related step updates in one call whenever a single action finishes multiple
    sequential steps. Reducing tool invocations is usually worth the few extra tokens a longer replacement string
    might consume.

    **Practical rules:**
    1. *Bulk completions* - If the steps are adjacent in the plan, select the contiguous block and
       append "COMPLETED ✓" to each line in a single replacement.
    2. *Sparse completions* - If the affected steps are far apart you may need multiple calls, but
       try grouping when reasonable.
    3. *Single-step edits* - For isolated tweaks, stick with the classic substring pattern.

    Args:
        old_text: String to locate the text to replace.
        new_text: The full replacement string.

    Examples
    --------
    Bulk completion of three contiguous steps:

        update_plan_steps(
            "Load customer data\n2. Transform customer data\n3. Validate customer data",
            "Load customer data - COMPLETED ✓\n2. Transform customer data - COMPLETED ✓\n3. Validate customer data - COMPLETED ✓",
        )

    Two similar revenue steps in one go:

        update_plan_steps(
            "Calculate revenue Q1 2023\nCalculate revenue Q2 2023",
            "Calculate revenue Q1 2023 - COMPLETED ✓\nCalculate revenue Q2 2023 - COMPLETED ✓",
        )

    Minimal single-step update:

        update_plan_steps("customer data", "customer data - COMPLETED ✓")
    """

    current_plan = ctx.deps.plan

    if current_plan is None:
        raise ModelRetry("No plan exists yet. Use `create_plan_steps` to create one.")

    if old_text not in current_plan:
        raise ModelRetry(f"Text not found in plan: '{old_text}'\n\nCurrent plan:\n{current_plan}\n")
    ctx.deps.update_plan(current_plan.replace(old_text, new_text).strip())


async def add_plan_step(ctx: RunContext[AgentDeps], new_step: str):
    """
    Adds a new step to the sequential plan.

    This adds a new step to the end of the existing plan. Use this when you discover during execution
    that additional steps are needed that weren't in the original user-approved plan, or when expanding the
    scope based on findings.

    Args:
        new_step: The new step to add to the plan. Should be properly formatted and follow the atomic, sequential pattern (e.g., "6. Validate results against business logic").

    Example:
        add_plan_step("4. Validation step: Cross-check MRR calculations against transaction totals")
    """
    current_plan = ctx.deps.plan

    if current_plan is None:
        raise ModelRetry("No plan exists yet. Use `create_plan_steps` to create one.")

    ctx.deps.update_plan((current_plan.strip() + "\n" + new_step).strip())


async def load_plan_steps(ctx: RunContext[AgentDeps]) -> str:
    """
    Loads the current sequential plan.

    Use this to check the current plan status, see what steps have been completed, or reference the overall
    approach.
    """
    return f"{ctx.deps.plan or 'No plan exists yet. Use `create_plan_steps` to create one.'}"


async def execute_plan_steps(ctx: RunContext[AgentDeps]):
    """Use this as soon as the user approves the plan to kickoff the execution."""
    ctx.deps.mode = Mode.ACT


async def toolset_defs_instructions(ctx: RunContext[AgentDeps]) -> str:
    return (
        (
            "<available_toolsets>\n"
            + "\n".join(
                [
                    f"<toolset name={toolset_name}>\n"
                    + "\n".join(
                        [
                            f"<tool name={tool.tool_def.name}>\n{tool.tool_def.description or ''}\n</tool>"
                            for tool in (await toolset.get_tools(ctx)).values()
                        ]
                    )
                    + "\n</toolset>"
                    for toolset_name, toolset in ctx.deps.toolsets.items()
                ]
            )
            + "\n</available_toolsets>"
        )
        if ctx.deps.toolsets
        else ""
    )


def fetch_toolset(ctx: RunContext[AgentDeps], toolset_name: str) -> str:
    """
    Fetches a toolset by its name from the `available_toolsets`.

    Args:
        toolset_name: The name of the toolset to fetch.
    """
    if toolset_name not in ctx.deps.toolsets:
        raise ModelRetry(f"Toolset '{toolset_name}' not in `available_toolsets`")
    ctx.deps.fetched_toolset = toolset_name
    return f"Loading {toolset_name}. Remember to update the plan after completing any step."


def user_interaction(message: str) -> str:
    """
    Interacts with the user. Could be:
    - A question
    - An assumption made that needs to be validated
    - A request for clarification
    - Anything else needed from the user to proceed

    Args:
        message: The message to display to the user.
    """
    return message


class AllStepsMarkedCompleted(BaseModel):
    """
    All steps have been marked as completed.
    """

    ...


class NotAllStepsMarkedCompleted(BaseModel):
    """
    Not all steps have been marked as completed.
    """

    message: str


class TaskResult(BaseModel):
    message: str


async def task_result(ctx: RunContext[AgentDeps], message: str) -> TaskResult:
    """Returns the final response to the user after executing the plan."""

    steps_checker = Agent(
        model="google-gla:gemini-2.5-flash",
        output_type=[AllStepsMarkedCompleted, NotAllStepsMarkedCompleted],
        instructions=(
            "Have all steps of the plan been marked as completed?\n"
            "If every step is clearly marked as done, return AllStepsCompleted.\n"
            "If any step is missing its completion mark, return AllStepsNotCompleted "
            "and include a terse message to the executor such as: 'Step 2 unfinished, "
            "if you've already done it, mark it; if not, do it now.'\n"
            "You only see the markdown plan, so you cannot know the actual work status. "
            "Prompt the executor to verify and act.\n"
            "Be direct and specific—no generic advice."
        ),
    )
    user_prompt = f"<sequential_plan>\n{ctx.deps.plan}\n</sequential_plan>"
    try:
        res = await steps_checker.run(user_prompt=user_prompt)
    except Exception:
        ctx.deps.mode = Mode.PLAN
        return TaskResult(message=message)
    if isinstance(res.output, AllStepsMarkedCompleted):
        ctx.deps.mode = Mode.PLAN
        return TaskResult(message=message)
    raise ModelRetry(res.output.message)


post_plan_toolset = FunctionToolset([execute_plan_steps], id="post_plan_toolset").filtered(
    lambda ctx, _: ctx.deps.plan is not None and ctx.deps.mode == Mode.PLAN
)

act_toolset = FunctionToolset(
    [update_plan_steps, add_plan_step, load_plan_steps, fetch_toolset],
    id="execution_toolset",
).filtered(lambda ctx, _: ctx.deps.mode == Mode.ACT)


def step_toolset(ctx: RunContext[AgentDeps]) -> AbstractToolset[Any] | None:
    return (
        ctx.deps.toolsets.get(ctx.deps.fetched_toolset)
        if ctx.deps.fetched_toolset is not None and ctx.deps.mode == Mode.ACT
        else None
    )


async def prepare_output_tools(
    ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    output_types = ["create_plan_steps", "user_interaction"]
    if ctx.deps.mode == Mode.ACT:
        output_types.append("task_result")
    return [tool_def for tool_def in tool_defs if tool_def.name in output_types]


def create_agent(retries: int = 3) -> Agent[AgentDeps, str | TaskResult]:
    return Agent(
        model=OpenAIModel("google/gemini-2.5-flash", provider=OpenRouterProvider()),
        deps_type=AgentDeps,
        instructions=[
            (
                "1. Create a plan.\n"
                "2. Once approved, start executing.\n"
                "3. Fetch the toolsets needed for each step of the plan as you go.\n"
                "4. Keep updating the plan after every step.\n"
                "5. Use task_result to end the process.\n"
            ),
            toolset_defs_instructions,
        ],
        toolsets=[post_plan_toolset, act_toolset, step_toolset],
        output_type=[
            ToolOutput(create_plan_steps, name="create_plan_steps"),
            ToolOutput(user_interaction, name="user_interaction"),
            ToolOutput(task_result, name="task_result"),
        ],
        prepare_output_tools=prepare_output_tools,
        retries=retries,
    )
