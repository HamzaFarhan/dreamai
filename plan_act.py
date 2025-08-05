from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Literal, Self
from uuid import uuid4

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic import UUID4, AfterValidator, BaseModel, ConfigDict, Field, model_validator
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
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import CombinedToolset, FilteredToolset
from pydantic_ai.toolsets.abstract import AbstractToolset

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


def to_snake_case(name: str) -> str:
    return name.replace(" ", "_").lower()


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
    resultant_artifact_name: Annotated[str, AfterValidator(to_snake_case)] = Field(
        description=(
            "Descriptive, relevant, and specific snake-case name of the artifact produced by the step. "
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
    plan_id: UUID4 = Field(default_factory=uuid4)
    task: str = Field(description="The user's task to be executed.")
    task_result_name: Annotated[str, AfterValidator(to_snake_case)] = Field(
        description="Descriptive, relevant, and specific snake-case name for the result of the task."
    )
    steps: dict[int, Step] = Field(default_factory=dict)  # type: ignore

    def add_steps(self, steps: list[Step] | Step):
        for step in sorted(steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number):
            self.steps[step.step_number] = step


class PlanAndActDeps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    toolsets: list[AbstractToolset[Any]] = Field(default_factory=list)  # type: ignore
    plan: Plan | None = None
    mode: Literal["plan", "act"] = "plan"
    artifacts: dict[UUID4, dict[str, Any]] = Field(default_factory=dict)  # type: ignore
    current_step: int = 0

    @model_validator(mode="after")
    def validate_artifacts(self) -> Self:
        if self.plan is not None:
            self.artifacts[self.plan.plan_id] = {}
        return self

    @staticmethod
    def toolset_filter(ctx: RunContext[PlanAndActDeps], tooldef: ToolDefinition) -> bool:
        if ctx.deps.mode == "act" and ctx.deps.plan is not None:
            return (
                tooldef.name == ctx.deps.plan.steps[ctx.deps.current_step].tool_name
                and tooldef.name != "user_interaction"
            )
        return False

    @property
    def plan_toolset(self) -> FilteredToolset[Any]:
        return CombinedToolset(self.toolsets).filtered(lambda ctx, _: ctx.deps.mode == "plan")

    @property
    def run_toolset(self) -> FilteredToolset[Any]:
        return CombinedToolset(self.toolsets).filtered(self.toolset_filter)

    def add_toolsets(self, toolsets: list[AbstractToolset] | AbstractToolset):
        self.toolsets += toolsets if isinstance(toolsets, list) else [toolsets]

    @staticmethod
    async def get_plan_tool_defs(ctx: RunContext[PlanAndActDeps]) -> dict[str, str]:
        return {
            tool_name: str(tool.tool_def)
            for tool_name, tool in (await ctx.deps.plan_toolset.get_tools(ctx)).items()
        }

    def init_plan(self, plan: Plan):
        self.plan = plan
        self.current_step = 0
        self.artifacts[plan.plan_id] = {}

    def get_artifacts(self, plan_id: UUID4 | None = None) -> dict[str, Any]:
        if plan_id is None:
            return {k: v for artifact in self.artifacts.values() for k, v in artifact.items()}
        return self.artifacts.get(plan_id, {})

    def add_artifacts(self, plan_id: UUID4, artifacts: dict[str, Any]):
        if plan_id not in self.artifacts:
            self.artifacts[plan_id] = {}
        for k, v in artifacts.items():
            if k in self.artifacts[plan_id]:
                logger.warning(f"Artifact {k} already exists in plan {plan_id}. Overwriting.")
            self.artifacts[plan_id][k] = v

    def drop_artifacts(self, plan_id: UUID4 | None = None):
        if plan_id is None:
            self.artifacts.clear()
        else:
            if plan_id in self.artifacts:
                del self.artifacts[plan_id]
            else:
                logger.warning(f"Plan ID {plan_id} not found in artifacts. No action taken.")

    def incr_current_step(self):
        if self.plan is None:
            self.current_step = 0
        elif self.current_step == len(self.plan.steps):
            self.mode = "plan"
        else:
            self.current_step += 1

    def blitz(self, keep_artifacts: bool = False):
        if self.plan is not None and not keep_artifacts:
            self.drop_artifacts(self.plan.plan_id)
        self.plan = None
        self.current_step = 0
        self.mode = "plan"


async def step_instructions(ctx: RunContext[PlanAndActDeps]) -> str:
    if ctx.deps.mode == "plan" or ctx.deps.plan is None or ctx.deps.current_step == 0:
        return ""
    step = ctx.deps.plan.steps[ctx.deps.current_step]
    step_str_list = [
        (files("dreamai.prompts") / "act_mode.md").read_text().strip() + "\n",
        f"<step number={step.step_number}>",
        f"<instructions>\n{step.instructions}\n</instructions>",
        f"<resultant_artifact_name>\n{step.resultant_artifact_name}\n</resultant_artifact_name>",
    ]
    if step.dependant_artifact_names and (artifacts := ctx.deps.get_artifacts(ctx.deps.plan.plan_id)):
        step_str_list.append(
            "<dependant_artifacts>"
            + "\n".join(
                [f"<artifact name={dep}>{artifacts[dep]}</artifact>\n" for dep in step.dependant_artifact_names]
            )
            + "</dependant_artifacts>"
        )
    step_str_list.append("</step>")
    return "\n".join(step_str_list).strip()


async def plan_mode_instructions(ctx: RunContext[PlanAndActDeps]) -> str:
    if ctx.deps.mode == "act":
        return ""
    tool_defs = (
        "<available_tools>\n"
        + "\n".join([f"{tool_def}" for tool_def in (await ctx.deps.get_plan_tool_defs(ctx)).values()])
        + "\n</available_tools>"
    )
    plan_str_list = [(files("dreamai.prompts") / "plan_mode.md").read_text().strip(), tool_defs]
    if artifacts := ctx.deps.get_artifacts():
        plan_str_list.append(
            "<saved_artifacts>\n"
            + "\n".join([f"<artifact name={name}>{value}</artifact>" for name, value in artifacts.items()])
            + "\n</saved_artifacts>"
        )
    return "\n\n".join(plan_str_list).strip()


async def create_plan(
    ctx: RunContext[PlanAndActDeps], task: str, task_result_name: str, steps: list[Step]
) -> Plan:
    """
    Create an execution-ready plan based on the user's task.
    Steps must be minimal and atomic, with one artifact per step and explicit filenames/locations.

    Args:
        task: The user's task to be executed.
        task_result_name: Descriptive, relevant, and specific snake-case name for the result of the task.
        steps: A list of steps to be executed in the plan.
    """
    if not steps:
        raise ModelRetry("No steps provided. Please provide a list of steps.")
    tool_defs = await ctx.deps.get_plan_tool_defs(ctx)
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
    plan = Plan(task=task, task_result_name=task_result_name)
    plan.add_steps(steps)
    ctx.deps.init_plan(plan)
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


class ExecutionStarted(BaseModel): ...


async def execute_plan(ctx: RunContext[PlanAndActDeps]) -> ExecutionStarted:
    """Use this as soon as the user approves the plan to kickoff the execution."""
    if ctx.deps.plan is None:
        raise ModelRetry("No plan has been created. Please create a plan first.")
    review = await review_plan(ctx.messages)
    if isinstance(review, NeedsRevision):
        logger.warning(f"Plan needs revision: {review.suggestions}")
        raise ModelRetry(f"Plan needs revision: {review.suggestions}")
    ctx.deps.mode = "act"
    ctx.deps.incr_current_step()
    return ExecutionStarted()


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


def task_result(ctx: RunContext[PlanAndActDeps], message: str) -> TaskResult:
    """Returns the final response to the user."""
    if ctx.deps.plan is not None:
        ctx.deps.add_artifacts(ctx.deps.plan.plan_id, {ctx.deps.plan.task_result_name: message})
    ctx.deps.blitz(keep_artifacts=True)
    return TaskResult(message=message)


class StepResult(BaseModel):
    """
    A step result.
    """

    step_number: int
    result: str


def step_result(
    ctx: RunContext[PlanAndActDeps], result: str, artifact_updates: dict[str, Any] | None = None
) -> StepResult:
    """
    Process the result of the current step.

    Args:
        result: The result of the step execution.
            This will be stored in `resultant_artifact_name` key in our running context.
            It is a dict[str, Any]. Make sure to include everything to help the next steps.
        artifact_updates: Optional dict of artifact_name -> new_value pairs to update existing artifacts
            that this step has corrected or refined (e.g., correcting a location from a previous step).
    """
    if ctx.deps.plan is not None and ctx.deps.current_step > 0:
        # Add the main result artifact
        ctx.deps.add_artifacts(
            ctx.deps.plan.plan_id, {ctx.deps.plan.steps[ctx.deps.current_step].resultant_artifact_name: result}
        )
        if artifact_updates:
            ctx.deps.add_artifacts(ctx.deps.plan.plan_id, artifact_updates)
            logger.warning(f"Step {ctx.deps.current_step} updated artifacts: {artifact_updates}")

    res = StepResult(step_number=ctx.deps.current_step, result=result)
    ctx.deps.incr_current_step()
    return res


class NeedHelp(BaseModel):
    step_number: int
    message: str


def need_help(ctx: RunContext[PlanAndActDeps], message: str) -> NeedHelp:
    """
    Use this when you need help from your supervisor agent to proceed after exhausting all retry options.
    This should be used as a LAST RESORT only when:
    - You've tried reasonable variations/alternatives for the current step
    - The step fundamentally cannot be completed with available tools
    - There are technical/execution issues that require plan revision

    Args:
        message: The message explaining the issue or what you need help with. Internal. Not user facing.
    """
    _need_help = NeedHelp(step_number=ctx.deps.current_step, message=f"NOT USER FACING\n{message}")
    ctx.deps.blitz()
    return _need_help


async def prepare_output_tools(
    ctx: RunContext[PlanAndActDeps], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    if ctx.deps.mode == "act":
        not_allowed_tools = {"create_plan", "execute_plan", "task_result", "user_interaction"}
        if ctx.deps.plan is not None:
            step_tool = ctx.deps.plan.steps[ctx.deps.current_step].tool_name
            not_allowed_tools -= {step_tool}
        return [tool_def for tool_def in tool_defs if tool_def.name not in not_allowed_tools]
    plan_mode_tools = ["create_plan"]
    if ctx.deps.plan is None:
        return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]
    if ctx.deps.current_step == len(ctx.deps.plan.steps):
        plan_mode_tools += ["task_result"]
    else:
        plan_mode_tools += ["execute_plan"]
    return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]


# toolset = CombinedToolset([user_info_toolset, weather_toolset, FunctionToolset([user_interaction])])


def create_plan_and_act_agent(
    retries: int = 3,
) -> Agent[PlanAndActDeps, ExecutionStarted | NeedHelp | Plan | StepResult | TaskResult | str]:
    return Agent(
        instructions=[plan_mode_instructions, step_instructions],
        deps_type=PlanAndActDeps,
        output_type=[
            ToolOutput(user_interaction, name="user_interaction"),
            ToolOutput(create_plan, name="create_plan"),
            ToolOutput(execute_plan, name="execute_plan"),
            ToolOutput(task_result, name="task_result"),
            ToolOutput(step_result, name="step_result"),
            ToolOutput(need_help, name="need_help"),
        ],
        prepare_output_tools=prepare_output_tools,
        retries=retries,
    )


async def run_plan_and_act_agent(
    user_prompt: str,
    agent_deps: PlanAndActDeps,
    plan_model: Model | KnownModelName | None = None,
    act_model: Model | KnownModelName | None = None,
    retries: int = 3,
    message_history_path: Path | str = "message_history.json",
):
    agent = create_plan_and_act_agent(retries=retries)
    plan_model = plan_model or OpenAIModel("google/gemini-2.5-flash", provider=OpenRouterProvider())
    act_model = act_model or OpenAIModel("openrouter/horizon-beta", provider=OpenRouterProvider())
    plan_user_prompt = user_prompt
    act_user_prompt = None
    plan_message_history: list[ModelMessage] = []
    act_message_history: list[ModelMessage] = []

    while True:
        Path(message_history_path).write_bytes(ModelMessagesTypeAdapter.dump_json(plan_message_history, indent=2))
        with capture_run_messages() as run_messages:
            try:
                res = await agent.run(
                    model=plan_model if agent_deps.mode == "plan" else act_model,
                    user_prompt=plan_user_prompt if agent_deps.mode == "plan" else act_user_prompt,
                    message_history=plan_message_history if agent_deps.mode == "plan" else act_message_history,
                    deps=agent_deps,
                    toolsets=[agent_deps.run_toolset],
                )
                res_output = res.output
            except UnexpectedModelBehavior as e:
                if agent_deps.mode == "plan":
                    raise e
                res_output = NeedHelp(step_number=agent_deps.current_step, message=f"NOT USER FACING: {e.message}")
                agent_deps.blitz()
        if res_output:
            logger.info(
                f"Agent response: {res_output if isinstance(res_output, (str, NeedHelp)) else res_output.model_dump_json(indent=2)}"
            )
        logger.info(
            f"Mode: {agent_deps.mode}, Current Step: {agent_deps.current_step}/{len(agent_deps.plan.steps) if agent_deps.plan else 0}"
        )
        if isinstance(res_output, ExecutionStarted):
            plan_user_prompt = None
            plan_message_history = (
                [
                    ModelRequest.user_text_prompt(
                        format_as_xml(agent_deps.plan.model_dump(exclude={"plan_id"}), root_tag="approved_plan")
                    )
                ]
                if agent_deps.plan
                else []
            )
            continue
        if isinstance(res_output, StepResult):
            act_user_prompt = None
            act_message_history = []
            plan_message_history.append(ModelRequest.user_text_prompt(res_output.model_dump_json()))
            continue
        if isinstance(res_output, NeedHelp):
            plan_message_history += run_messages
            continue
        if agent_deps.mode == "plan":
            plan_message_history = run_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            plan_user_prompt = input(f"{agent_message}\n> ")
            if plan_user_prompt.lower() in ["exit", "quit", "q"]:
                break
        else:
            act_message_history = run_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            act_user_prompt = input(f"{agent_message}\n> ")
