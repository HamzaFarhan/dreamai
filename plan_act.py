from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
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

from dreamai.basic_toolset import user_interaction

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
    artifact_name: str = Field(description="Descriptive name of the artifact produced by the step.")
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
    toolsets: list[AbstractToolset[Any]] = Field(default_factory=list)  # type: ignore
    plan: Plan | None = None
    plan_approved: bool = False
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Artifacts produced by the agent.")
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


async def agent_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.plan_approved and ctx.deps.plan is not None:
        return "The plan has been approved. You can now execute the steps: \n" + ctx.deps.plan.model_dump_json()
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
    ctx.deps.plan_approved = True
    if ctx.deps.plan is None:
        raise ModelRetry("No plan has been created. Please create a plan first.")
    return ctx.deps.plan


async def prepare_output_tools(ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    if ctx.deps.plan is None:
        return [tool_def for tool_def in tool_defs if tool_def.name in ["create_plan", "user_interaction"]]
    return [tool_def for tool_def in tool_defs if tool_def.name not in ["create_plan"]]


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


def toolset_filter(ctx: RunContext[AgentDeps], tooldef: ToolDefinition) -> bool:
    if ctx.deps.plan_approved and ctx.deps.plan is not None and ctx.deps.current_step > 0:
        return tooldef.name == ctx.deps.plan.steps[ctx.deps.current_step].tool_name
    return True


toolset = CombinedToolset([user_info_toolset, weather_toolset]).filtered(toolset_filter)

model = OpenAIModel("openrouter/horizon-alpha", provider=OpenRouterProvider())
agent = Agent(
    model=model,
    instructions=[agent_instructions],
    deps_type=AgentDeps,
    prepare_output_tools=prepare_output_tools,
)
agent_deps = AgentDeps(user_info=UserInfo(city="Paris"), toolsets=[toolset])


async def run_planner(user_prompt: str) -> Plan:
    message_history: list[ModelMessage] = []
    while True:
        # async with agent.iter(
        #     user_prompt,
        #     deps=agent_deps,
        #     message_history=message_history,
        #     output_type=[create_plan, mark_plan_approved, user_interaction],
        # ) as agent_run:
        #     async for node in agent_run:
        #         if agent.is_model_request_node(node):
        #             for part in node.request.parts:
        #                 if isinstance(part, ToolReturnPart) and part.tool_name == "user_interaction":
        #                     message_history.append(parts)
        #                     print(f"{parts.role}: {parts.content}")
        res = await agent.run(
            user_prompt,
            deps=agent_deps,
            message_history=message_history,
            output_type=[
                ToolOutput(user_interaction, name="user_interaction"),
                ToolOutput(create_plan, name="create_plan"),
                ToolOutput(mark_plan_approved, name="mark_plan_approved"),
            ],
        )
        if agent_deps.plan_approved and isinstance(res.output, Plan):
            return res.output
        user_prompt = input(f"{res.output}\n> ")
        message_history = res.all_messages()


if __name__ == "__main__":
    import asyncio

    plan = asyncio.run(run_planner("What is the weather at my location?"))
    print("\n---------------------------\n")
    print(plan.model_dump_json(indent=2))
    print("\n---------------------------\n")
    print(agent_deps)
