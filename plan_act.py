from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic import AfterValidator, BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import CombinedToolset, FunctionToolset
from pydantic_ai.toolsets.abstract import AbstractToolset

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


def get_tool_info(tool: Callable[..., Any]) -> str:
    doc = tool.__doc__ or "No description"
    sig = inspect.signature(tool)
    return f"{tool.__name__}{sig}: {doc.strip()}"


class Step(BaseModel):
    step_number: Annotated[int, AfterValidator(lambda x: max(x, 1))] = Field(
        description="The sequential number of the step in the plan. Starts at 1."
    )
    description: str = Field(description=("Human-readable description of the step. No mention of the tools."))
    instructions: str = Field(
        description=(
            "Atomic, execution-ready instructions for this single step. Spell out everything. "
            "Produce exactly one artifact per step. If reading data, specify full file paths."
        )
    )
    tool_name: str = Field(
        default="none",
        description="The name of the tool to use for the step. Set to 'none' if no tool is needed.",
    )
    artifact_name: str = Field(
        description=(
            "Descriptive name of the artifact produced by the step. "
            "This will be stored in a dict[str, Any] in our running context."
        )
    )
    depends_on_artifacts: list[str] = Field(
        default_factory=list,
        description=(
            "List of artifact names that this step depends on. "
            "The step will not be executed until all dependencies are completed."
        ),
    )


class Plan(BaseModel):
    task: str = Field(description="The user's task to be executed.")
    steps: dict[int, Step] = Field(default_factory=dict)  # type: ignore

    def add_steps(self, steps: list[Step] | Step):
        for step in sorted(steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number):
            self.steps[step.step_number] = step


@dataclass
class UserInfo:
    city: str


@dataclass
class AgentDeps:
    user_info: UserInfo
    toolsets: list[AbstractToolset[Any]] = field(default_factory=list)  # type: ignore
    plan: Plan | None = None
    plan_approved: bool = False
    artifacts: dict[str, Any] = field(default_factory=dict)  # type: ignore
    current_step: int = 0

    def add_toolsets(self, toolsets: list[AbstractToolset] | AbstractToolset):
        self.toolsets += toolsets if isinstance(toolsets, list) else [toolsets]


async def get_tool_defs(ctx: RunContext[AgentDeps]) -> dict[str, str] | None:
    if ctx.deps.plan_approved:
        return None
    return {
        tool_name: str(tool.tool_def)
        for toolset in ctx.deps.toolsets
        for tool_name, tool in (await toolset.get_tools(ctx)).items()
    }


async def get_tool_def_instructions(ctx: RunContext[AgentDeps]) -> str:
    tool_defs = await get_tool_defs(ctx)
    if not tool_defs:
        return ""
    return (
        "<available_tools>\n" + "\n".join([f"{tool_def}" for tool_def in tool_defs.values()]) + "\n</available_tools>"
    )


async def step_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.plan is None or not ctx.deps.plan_approved or ctx.deps.current_step == 0:
        return ""
    step = ctx.deps.plan.steps[ctx.deps.current_step]
    step_str_list = [f"<step number={step.step_number}>", f"<instructions>\n{step.instructions}\n</instructions>"]
    if step.depends_on_artifacts:
        deps_str = "<dependencies>\n"
        for dep in step.depends_on_artifacts:
            if dep in ctx.deps.artifacts:
                deps_str += f"<artifact name='{dep}'>{ctx.deps.artifacts[dep]}</artifact>\n"
        deps_str += "</dependencies>\n"
        step_str_list.append(deps_str)
    step_str_list.append("</step>")
    return "\n".join(step_str_list)


async def planner_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.plan is not None and ctx.deps.plan_approved and ctx.deps.current_step > 0:
        return ""
    tool_defs = await get_tool_def_instructions(ctx)
    return (
        "You are a planner agent. Your task is to create an execution-ready plan based on the user's task.\n"
        "Each step must be atomic, with one artifact per step and explicit filenames/locations.\n"
        "If you need to use tools, specify them in the steps.\n"
        f"{tool_defs}"
    ).strip() + "\nIf you need more information, ask the user."


async def create_plan(ctx: RunContext[AgentDeps], task: str, steps: list[Step]) -> Plan:
    """
    Create an execution-ready plan based on the user's task.
    Steps must be minimal and atomic, with one artifact per step and explicit filenames/locations.
    """
    if not steps:
        raise ModelRetry("No steps provided. Please provide a list of steps.")
    tool_defs = await get_tool_defs(ctx)
    if tool_defs:
        tool_names = tool_defs.keys()
        wrong_steps = [step for step in steps if step.tool_name != "none" and step.tool_name not in tool_names]
        if wrong_steps:
            raise ModelRetry(
                (
                    f"The following steps use tools that are not available:\n{wrong_steps}\n"
                    f"Available tools: {list(tool_names)}"
                )
            )
    plan = Plan(task=task)
    plan.add_steps(steps)
    ctx.deps.plan = plan
    return plan


def mark_plan_approved(ctx: RunContext[AgentDeps]) -> Plan:
    """Use this AFTER the user approves the plan."""
    if ctx.deps.plan is None:
        raise ModelRetry("No plan has been created. Please create a plan first.")
    ctx.deps.plan_approved = True
    ctx.deps.current_step = 1
    return ctx.deps.plan


async def prepare_output_tools(ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    if ctx.deps.plan is None:
        return [tool_def for tool_def in tool_defs if tool_def.name in ["user_interaction", "create_plan"]]
    if not ctx.deps.plan_approved:
        return [
            tool_def
            for tool_def in tool_defs
            if tool_def.name in ["user_interaction", "create_plan", "mark_plan_approved"]
        ]
    if ctx.deps.plan_approved:
        return [tool_def for tool_def in tool_defs if tool_def.name not in ["create_plan", "mark_plan_approved"]]
    return tool_defs


def get_user_city(ctx: RunContext[AgentDeps]) -> str:
    return ctx.deps.user_info.city


user_info_toolset = FunctionToolset(tools=[get_user_city])


def temperature_celsius(city: str) -> float:
    """Get the current temperature in Celsius for the specified city."""
    logger.info(f"Getting temperature in Celsius for {city}")
    return 21.0


def temperature_fahrenheit(city: str) -> float:
    """Get the current temperature in Fahrenheit for the specified city."""
    logger.info(f"Getting temperature in Fahrenheit for {city}")
    return 69.8


weather_toolset = FunctionToolset[Any](tools=[temperature_celsius, temperature_fahrenheit])


def user_interaction(message: str) -> str:
    """
    Interacts with the user. Could be:
    - A question
    - A progress update
    - An assumption made that needs to be validated
    - A request for clarification
    - Anything else needed from the user to proceed

    Args:
        message: The message to display to the user.
    """
    return message


class TaskResult(BaseModel):
    """
    A task result.
    """

    message: str = Field(description="The final response to the user.")


class StepResult(BaseModel):
    """
    A step result.
    """

    message: str = Field(description="The final response to the user for the current step.")


def step_result(ctx: RunContext[AgentDeps], message: str) -> StepResult | TaskResult:
    """Returns the final response to the user for the current step."""
    if ctx.deps.plan is not None and ctx.deps.current_step > 0:
        ctx.deps.artifacts[ctx.deps.plan.steps[ctx.deps.current_step].artifact_name] = message
        if ctx.deps.current_step == len(ctx.deps.plan.steps):
            return TaskResult(message=message)
        ctx.deps.current_step += 1
    return StepResult(message=message)


def toolset_filter(ctx: RunContext[AgentDeps], tooldef: ToolDefinition) -> bool:
    if ctx.deps.plan_approved and ctx.deps.plan is not None and ctx.deps.current_step > 0:
        return tooldef.name == ctx.deps.plan.steps[ctx.deps.current_step].tool_name
    return True


toolset = CombinedToolset([user_info_toolset, weather_toolset]).filtered(toolset_filter)

model = OpenAIModel("openrouter/horizon-alpha", provider=OpenRouterProvider())
agent = Agent(
    model=model,
    instructions=[planner_instructions, step_instructions],
    deps_type=AgentDeps,
    prepare_output_tools=prepare_output_tools,
)


async def run_agent(user_prompt: str, agent_deps: AgentDeps) -> TaskResult:
    message_history: list[ModelMessage] | None = None
    while True:
        res = await agent.run(
            user_prompt,
            deps=agent_deps,
            message_history=message_history,
            toolsets=agent_deps.toolsets if agent_deps.plan_approved else None,
            output_type=[
                ToolOutput(user_interaction, name="user_interaction"),
                ToolOutput(create_plan, name="create_plan"),
                ToolOutput(mark_plan_approved, name="mark_plan_approved"),
                ToolOutput(step_result, name="step_result"),
            ],
        )
        message_history = res.all_messages()
        if isinstance(res.output, Plan) and agent_deps.plan_approved:
            message_history = None
            continue
        if isinstance(res.output, StepResult):
            message_history = None
            continue
        if isinstance(res.output, TaskResult):
            return res.output
        agent_message = res.output if isinstance(res.output, str) else res.output.model_dump_json(indent=2)
        user_prompt = input(f"{agent_message}\n> ")


if __name__ == "__main__":
    import asyncio

    agent_deps = AgentDeps(user_info=UserInfo(city="Paris"), toolsets=[toolset])

    res = asyncio.run(run_agent("What is the weather at my location?", agent_deps=agent_deps))
    print("\n---------------------------\n")
    print(res.model_dump_json(indent=2))
    print("\n---------------------------\n")
    print(agent_deps)
