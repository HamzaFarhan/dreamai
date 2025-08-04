from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Literal

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic import AfterValidator, BaseModel, Field
from pydantic_ai import (
    Agent,
    ModelRetry,
    RunContext,
    ToolOutput,
    UnexpectedModelBehavior,
    capture_run_messages,
    format_as_xml,
)
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest
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
        description="The name of the tool to use for the step. Set to `none` if no tool is needed.",
    )
    resultant_artifact_name: str = Field(
        description=(
            "Descriptive name of the artifact produced by the step. "
            "This will be stored in a dict[str, Any] in our running context. "
            "Not in a file, but in our internal memory. "
        )
    )
    dependant_artifact_names: list[str] = Field(
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
    name: str
    city: str


@dataclass
class AgentDeps:
    user_info: UserInfo
    toolsets: list[AbstractToolset[Any]] = field(default_factory=list)  # type: ignore
    plan: Plan | None = None
    mode: Literal["plan", "act"] = "plan"
    artifacts: dict[str, Any] = field(default_factory=dict)  # type: ignore
    current_step: int = 0

    def add_toolsets(self, toolsets: list[AbstractToolset] | AbstractToolset):
        self.toolsets += toolsets if isinstance(toolsets, list) else [toolsets]

    def incr_current_step(self):
        if self.plan is None:
            self.current_step = 0
        elif self.current_step == len(self.plan.steps):
            self.mode = "plan"
        else:
            self.current_step += 1

    def blitz(self):
        self.plan = None
        self.artifacts.clear()
        self.current_step = 0
        self.mode = "plan"


async def get_tool_defs(ctx: RunContext[AgentDeps]) -> dict[str, str]:
    return {
        tool_name: str(tool.tool_def)
        for toolset in ctx.deps.toolsets
        for tool_name, tool in (await toolset.get_tools(ctx)).items()
    }


async def get_tool_def_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.mode == "act":
        return ""
    tool_defs = await get_tool_defs(ctx)
    return (
        "<available_tools>\n"
        + "\n".join([f"{tool_def}" for tool_def in tool_defs.values()])
        + "\n</available_tools>"
    )


async def step_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.mode == "plan" or ctx.deps.plan is None or ctx.deps.current_step == 0:
        return ""
    step = ctx.deps.plan.steps[ctx.deps.current_step]
    step_str_list = [
        f"<step number={step.step_number}>",
        f"<instructions>\n{step.instructions}\n</instructions>",
        f"<resultant_artifact_name>\n{step.resultant_artifact_name}\n</resultant_artifact_name>",
    ]
    if step.dependant_artifact_names:
        step_str_list.append(
            "<dependant_artifacts>"
            + "\n".join(
                [
                    f"<artifact name='{dep}'>{ctx.deps.artifacts[dep]}</artifact>\n"
                    for dep in step.dependant_artifact_names
                ]
            )
            + "</dependant_artifacts>"
        )
    step_str_list.append("</step>")
    return "\n".join(step_str_list).strip()


async def plan_mode_instructions(ctx: RunContext[AgentDeps]) -> str:
    if ctx.deps.mode == "act":
        return ""
    tool_defs = await get_tool_def_instructions(ctx)
    plan_str_list = [(files("dreamai.prompts") / "plan_mode.md").read_text().strip(), tool_defs]
    if ctx.deps.artifacts:
        plan_str_list.append(
            "<saved_artifacts>\n"
            + "\n".join(
                [f"<artifact name='{name}'>{value}</artifact>" for name, value in ctx.deps.artifacts.items()]
            )
            + "\n</saved_artifacts>"
        )
    return "\n\n".join(plan_str_list).strip()


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
    ctx.deps.current_step = 0
    return plan


class LooksGood(BaseModel): ...


class NeedsRevision(BaseModel):
    suggestions: str = Field(
        description="Suggestions for revising the steps with respect to the task and the user approved plan. "
    )


async def review_plan(message_history: list[ModelMessage]) -> LooksGood | NeedsRevision:
    reviewer_agent = Agent(
        model="google-gla:gemini-2.5-flash",
        instructions=(
            "Given the task, the user approved plan, and the message history, "
            "you have to identify if the internal plan steps are correct "
            "and execution-ready. So no steps need to be omitted and "
            "no extra steps need to be added.\n"
            "If they are correct, return a LooksGood response. "
            "If not, return a NeedsRevision response with suggestions for revision."
        ),
        output_type=[LooksGood, NeedsRevision],
    )
    try:
        return (await reviewer_agent.run(message_history=message_history)).output
    except Exception as e:
        logger.error(f"Error reviewing steps: {e}")
        return LooksGood()


class PlanApproved(BaseModel): ...


async def mark_plan_approved(ctx: RunContext[AgentDeps]) -> PlanApproved:
    """Use this as soon as the user approves the plan to kickoff the execution."""
    if ctx.deps.plan is None:
        raise ModelRetry("No plan has been created. Please create a plan first.")
    review = await review_plan(message_history=ctx.messages)
    if isinstance(review, NeedsRevision):
        logger.warning(f"Plan needs revision: {review.suggestions}")
        raise ModelRetry(f"Plan needs revision: {review.suggestions}")
    ctx.deps.mode = "act"
    ctx.deps.incr_current_step()
    return PlanApproved()


def get_user_city(ctx: RunContext[AgentDeps]) -> str:
    """Get the user's city"""
    return ctx.deps.user_info.city


def get_user_name(ctx: RunContext[AgentDeps]) -> str:
    """Get the user's name"""
    return ctx.deps.user_info.name


user_info_toolset = FunctionToolset([get_user_name])


def temperature_celsius(city: str) -> float:
    """Get the current temperature in Celsius for the specified city."""
    logger.info(f"Getting temperature in Celsius for {city}")
    temp_map = {
        "New York": 21.0,
        "Paris": 19.0,
        "Tokyo": 22.0,
    }
    try:
        return temp_map[city]
    except KeyError as e:
        raise ModelRetry(f"City '{city}' not found in temperature data: {str(e)}")


def temperature_fahrenheit(city: str) -> float:
    """Get the current temperature in Fahrenheit for the specified city."""
    logger.info(f"Getting temperature in Fahrenheit for {city}")
    temp_map = {
        "New York": 69.8,
        "Paris": 66.2,
        "Tokyo": 71.6,
    }
    try:
        return temp_map[city]
    except KeyError as e:
        raise ModelRetry(f"City '{city}' not found in temperature data: {str(e)}")


def weather_forecast(city: str) -> str:
    """Get the weather forecast for the specified city."""
    logger.info(f"Getting weather forecast for {city}")
    weather_map = {
        "New York": "Sunny",
        "Paris": "Cloudy with a chance of rain",
        "Tokyo": "Clear skies and warm temperatures",
    }
    return weather_map[city]


weather_toolset = FunctionToolset[Any](
    [temperature_celsius, temperature_fahrenheit, weather_forecast], max_retries=3
)


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


class TaskResult(BaseModel):
    """
    A task result.
    """

    message: str = Field(description="The final response to the user.")


def task_result(message: str) -> TaskResult:
    """Returns the final response to the user."""
    return TaskResult(message=message)


class StepResult(BaseModel):
    """
    A step result.
    """

    step_number: int
    result: str


def step_result(ctx: RunContext[AgentDeps], result: str) -> StepResult:
    """
    Process the result of the current step.

    Args:
        result: The result of the step execution.
            This will be stored in `resultant_artifact_name` key in our running context.
            It is a dict[str, Any]. Make sure to include everything to help the next steps.
    """
    if ctx.deps.plan is not None and ctx.deps.current_step > 0:
        ctx.deps.artifacts[ctx.deps.plan.steps[ctx.deps.current_step].resultant_artifact_name] = result
    res = StepResult(step_number=ctx.deps.current_step, result=result)
    ctx.deps.incr_current_step()
    return res


class NeedHelp(BaseModel):
    step_number: int
    message: str


def need_help(ctx: RunContext[AgentDeps], message: str) -> NeedHelp:
    """Use this when you need help to proceed.

    Args:
        message: The message explaining the issue or what you need help with.
    """
    _need_help = NeedHelp(step_number=ctx.deps.current_step, message=f"NOT USER FACING: {message}")
    ctx.deps.blitz()
    return _need_help


async def prepare_output_tools(
    ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    plan_mode_tools = ["create_plan", "mark_plan_approved", "task_result"]
    if ctx.deps.mode == "act":
        return [tool_def for tool_def in tool_defs if tool_def.name not in plan_mode_tools]
    plan_mode_tools = ["user_interaction", "create_plan"]
    if ctx.deps.plan is None:
        return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]
    if ctx.deps.current_step == len(ctx.deps.plan.steps):
        plan_mode_tools.append("task_result")
    else:
        plan_mode_tools.append("mark_plan_approved")
    return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]


def toolset_filter(ctx: RunContext[AgentDeps], tooldef: ToolDefinition) -> bool:
    if ctx.deps.mode == "act" and ctx.deps.plan is not None:
        return (
            tooldef.name == ctx.deps.plan.steps[ctx.deps.current_step].tool_name
            and tooldef.name != "user_interaction"
        )
    return False


toolset = CombinedToolset([user_info_toolset, weather_toolset, FunctionToolset([user_interaction])])

model = OpenAIModel("openrouter/horizon-beta", provider=OpenRouterProvider())
agent = Agent(
    model=model,
    instructions=[plan_mode_instructions, step_instructions],
    deps_type=AgentDeps,
    toolsets=[toolset.filtered(toolset_filter)],
    output_type=[
        ToolOutput(user_interaction, name="user_interaction"),
        ToolOutput(create_plan, name="create_plan"),
        ToolOutput(mark_plan_approved, name="mark_plan_approved"),
        ToolOutput(task_result, name="task_result"),
        ToolOutput(step_result, name="step_result"),
        ToolOutput(need_help, name="need_help"),
    ],
    prepare_output_tools=prepare_output_tools,
    retries=3,
)


async def run_agent(user_prompt: str, agent_deps: AgentDeps):
    plan_user_prompt = user_prompt
    act_user_prompt = None
    plan_message_history: list[ModelMessage] = []
    act_message_history: list[ModelMessage] = []

    while True:
        with capture_run_messages() as run_messages:
            try:
                res = await agent.run(
                    user_prompt=plan_user_prompt if agent_deps.mode == "plan" else act_user_prompt,
                    message_history=plan_message_history if agent_deps.mode == "plan" else act_message_history,
                    deps=agent_deps,
                )
                res_output = res.output
                res_all_messages = res.all_messages()
            except UnexpectedModelBehavior as e:
                if agent_deps.mode == "plan":
                    raise e
                res_output = NeedHelp(step_number=agent_deps.current_step, message=f"NOT USER FACING: {e.message}")
                res_all_messages = run_messages
                agent_deps.blitz()
        if res_output:
            logger.info(
                f"Agent response: {res_output if isinstance(res_output, (str, NeedHelp)) else res_output.model_dump_json(indent=2)}"
            )
        logger.info(
            f"Mode: {agent_deps.mode}, Current Step: {agent_deps.current_step}/{len(agent_deps.plan.steps) if agent_deps.plan else 0}"
        )
        if isinstance(res_output, PlanApproved):
            plan_user_prompt = None
            plan_message_history = [
                ModelRequest.user_text_prompt(format_as_xml(agent_deps.plan, root_tag="approved_plan"))
            ]
            continue
        if isinstance(res_output, StepResult):
            act_user_prompt = None
            act_message_history = []
            plan_message_history.append(ModelRequest.user_text_prompt(res_output.model_dump_json()))
            continue
        if isinstance(res_output, NeedHelp):
            plan_message_history += res_all_messages
            continue
        if agent_deps.mode == "plan":
            plan_message_history = res_all_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            plan_user_prompt = input(f"{agent_message}\n> ")
            if plan_user_prompt.lower() in ["exit", "quit", "q"]:
                Path("message_history.json").write_bytes(
                    ModelMessagesTypeAdapter.dump_json(plan_message_history, indent=2)
                )
                break
        else:
            act_message_history = res_all_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            act_user_prompt = input(f"{agent_message}\n> ")


if __name__ == "__main__":
    import asyncio

    agent_deps = AgentDeps(
        user_info=UserInfo(name="Hamza", city="Paris"),
        toolsets=[toolset.filtered(lambda ctx, _: ctx.deps.mode == "plan")],
    )
    asyncio.run(run_agent("What is the temp in celcius and fahrenheit at my location?", agent_deps=agent_deps))
    logger.success("Agent run completed successfully.")
