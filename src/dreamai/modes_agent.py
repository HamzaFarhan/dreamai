from __future__ import annotations

from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Self
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
from pydantic_ai.toolsets.abstract import AbstractToolset

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


class Mode(StrEnum):
    PLAN = "plan"
    ACT = "act"


def to_snake_case(name: str) -> str:
    return name.replace(" ", "_").lower()


class Step(BaseModel):
    step_number: Annotated[int, AfterValidator(lambda x: max(x, 1))] = Field(
        description="The sequential number of the step in the plan. Starts at 1."
    )
    description: str = Field(description=("Human-readable description of the step. No mention of the toolset."))
    instructions: str = Field(
        description=(
            "Atomic, execution-ready instructions for this single step. Spell out everything. "
            "Produce exactly one artifact per step. If reading data, specify full file paths."
        )
    )
    toolset_name: str = Field(
        description="The name of the toolset to use for the step.",
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
    can_execute: bool = True
    executed: bool = False

    @property
    def first_step_number(self) -> int:
        return self.steps[min(self.steps)].step_number if self.steps else 1

    @property
    def last_step_number(self) -> int:
        return self.steps[max(self.steps)].step_number if self.steps else 1

    def add_steps(self, steps: list[Step] | Step):
        last_step_number = self.last_step_number
        for step in sorted(steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number):
            self.steps[last_step_number] = step
            last_step_number += 1


class PlanAndActDeps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    toolsets: dict[str, AbstractToolset[Any]] = Field(default_factory=dict)
    toolset_descriptions: str | None = None
    plan: Plan | None = None
    mode: Mode = Mode.PLAN
    artifacts: dict[UUID4, dict[str, Any]] = Field(default_factory=dict)  # type: ignore
    current_step: int | None = 0

    @model_validator(mode="after")
    def validate_artifacts(self) -> Self:
        if self.plan is not None:
            self.artifacts[self.plan.plan_id] = {}
        return self

    def add_toolsets(self, toolsets: list[AbstractToolset[Any]] | AbstractToolset[Any]):
        self.toolsets.update(
            {
                toolset.id: toolset
                for toolset in (toolsets if isinstance(toolsets, list) else [toolsets])
                if toolset.id is not None
            }
        )

    def init_plan(self, plan: Plan):
        self.plan = plan
        self.current_step = plan.first_step_number
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
        if self.plan is None or self.current_step is None:
            self.current_step = None
        elif self.current_step == len(self.plan.steps):
            self.mode = Mode.PLAN
            self.plan.executed = True
        else:
            self.current_step += 1

    def blitz(self, keep_artifacts: bool = False):
        if self.plan is not None and not keep_artifacts:
            self.drop_artifacts(self.plan.plan_id)
        self.plan = None
        self.current_step = None
        self.mode = Mode.PLAN


def step_instructions(ctx: RunContext[PlanAndActDeps]) -> str:
    if ctx.deps.mode == Mode.PLAN or ctx.deps.plan is None or ctx.deps.current_step is None:
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


def plan_mode_instructions(ctx: RunContext[PlanAndActDeps]) -> str:
    if ctx.deps.mode == Mode.ACT:
        return ""
    tool_defs = "<available_toolsets>\n" + "\n".join(ctx.deps.toolsets.keys()) + "\n</available_toolsets>"
    plan_str_list = [(files("dreamai.prompts") / "plan_mode.md").read_text().strip(), tool_defs]
    if ctx.deps.toolset_descriptions:
        plan_str_list.append(f"<toolset_descriptions>\n{ctx.deps.toolset_descriptions}\n</toolset_descriptions>")
    if artifacts := ctx.deps.get_artifacts():
        plan_str_list.append(
            "<saved_artifacts>\n"
            + "\n".join([f"<artifact name={name}>{value}</artifact>" for name, value in artifacts.items()])
            + "\n</saved_artifacts>"
        )
    return "\n\n".join(plan_str_list).strip()


def create_plan(ctx: RunContext[PlanAndActDeps], task: str, task_result_name: str, steps: list[Step]) -> Plan:
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
    if toolset_ids := ctx.deps.toolsets.keys():
        wrong_steps = [step for step in steps if step.toolset_name not in toolset_ids]
        if wrong_steps:
            raise ModelRetry(
                (
                    f"The following steps use toolsets that are not available:\n{wrong_steps}\n"
                    f"Available toolsets: {list(toolset_ids)}"
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
        ctx.deps.plan.can_execute = False
        logger.warning(f"Plan needs revision: {review.suggestions}")
        raise ModelRetry(f"Plan needs revision: {review.suggestions}")
    ctx.deps.plan.can_execute = True
    ctx.deps.mode = Mode.ACT
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


def step_result(ctx: RunContext[PlanAndActDeps], result: str) -> StepResult:
    """
    Process the result of the current step.

    Args:
        result: The result of the step execution.
            This will be stored in `resultant_artifact_name` key in our running context.
            It is a dict[str, Any]. Make sure to include everything to help the next steps.
    """
    if ctx.deps.plan is None or ctx.deps.current_step is None:
        return StepResult(step_number=0, result=result)
    step = ctx.deps.plan.steps[ctx.deps.current_step]
    ctx.deps.add_artifacts(ctx.deps.plan.plan_id, {step.resultant_artifact_name: result})
    res = StepResult(step_number=step.step_number, result=result)
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
    if ctx.deps.plan is None or ctx.deps.current_step is None:
        return NeedHelp(step_number=0, message=f"NOT USER FACING\n{message}")
    _need_help = NeedHelp(
        step_number=ctx.deps.plan.steps[ctx.deps.current_step].step_number, message=f"NOT USER FACING\n{message}"
    )
    ctx.deps.blitz()
    return _need_help


async def prepare_output_tools(
    ctx: RunContext[PlanAndActDeps], tool_defs: list[ToolDefinition]
) -> list[ToolDefinition] | None:
    if ctx.deps.mode == Mode.ACT:
        not_allowed_tools = {"create_plan", "execute_plan", "task_result", "user_interaction"}
        if ctx.deps.plan is not None and ctx.deps.current_step is not None:
            step_tool = ctx.deps.plan.steps[ctx.deps.current_step].toolset_name
            not_allowed_tools -= {step_tool}
        return [tool_def for tool_def in tool_defs if tool_def.name not in not_allowed_tools]
    plan_mode_tools = ["create_plan"]
    if ctx.deps.plan is None:
        return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]
    if ctx.deps.current_step == ctx.deps.plan.last_step_number:
        plan_mode_tools += ["task_result"]
    elif ctx.deps.plan.can_execute:
        plan_mode_tools += ["execute_plan"]
    return [tool_def for tool_def in tool_defs if tool_def.name in plan_mode_tools]


def act_toolset(ctx: RunContext[PlanAndActDeps]) -> AbstractToolset[Any] | None:
    if ctx.deps.mode == Mode.PLAN or ctx.deps.plan is None or ctx.deps.current_step is None:
        return None
    toolset_name = ctx.deps.plan.steps[ctx.deps.current_step].toolset_name
    return ctx.deps.toolsets.get(toolset_name, None) if toolset_name != "user_interaction" else None


def create_plan_and_act_agent(
    retries: int = 3,
) -> Agent[PlanAndActDeps, ExecutionStarted | NeedHelp | Plan | StepResult | TaskResult | str]:
    return Agent(
        instructions=[plan_mode_instructions, step_instructions],
        deps_type=PlanAndActDeps,
        toolsets=[act_toolset],
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
    agent_deps_path: Path | str = "agent_deps.json",
    message_history_path: Path | str = "message_history.json",
):
    agent = create_plan_and_act_agent(retries=retries)
    # plan_model = plan_model or "gpt-4.1"
    # act_model = act_model or "google-gla:gemini-2.5-flash"
    plan_model = plan_model or OpenAIModel("openai/gpt-4.1", provider=OpenRouterProvider())
    act_model = act_model or "google-gla:gemini-2.5-flash"
    # act_model = act_model or OpenAIModel("openai/gpt-5-mini", provider=OpenRouterProvider())
    plan_user_prompt = user_prompt
    act_user_prompt = None
    plan_message_history: list[ModelMessage] = []
    act_message_history: list[ModelMessage] = []

    while True:
        Path(message_history_path).write_bytes(ModelMessagesTypeAdapter.dump_json(plan_message_history, indent=2))
        with capture_run_messages() as run_messages:
            try:
                res = await agent.run(
                    model=plan_model if agent_deps.mode == Mode.PLAN else act_model,
                    user_prompt=plan_user_prompt if agent_deps.mode == Mode.PLAN else act_user_prompt,
                    message_history=plan_message_history if agent_deps.mode == Mode.PLAN else act_message_history,
                    deps=agent_deps,
                )
                res_output = res.output
                Path(agent_deps_path).write_text(agent_deps.model_dump_json(exclude={"toolsets"}))
            except UnexpectedModelBehavior as e:
                if agent_deps.mode == Mode.PLAN:
                    raise e
                res_output = NeedHelp(
                    step_number=agent_deps.current_step or 0, message=f"NOT USER FACING: {e.message}"
                )
                agent_deps.blitz()
        if res_output:
            logger.info(
                f"Agent response: {res_output if isinstance(res_output, (str, NeedHelp)) else res_output.model_dump_json(indent=2)}"
            )
        logger.info(
            f"Mode: {agent_deps.mode}, Current Step: {agent_deps.current_step}/{agent_deps.plan.last_step_number if agent_deps.plan else 0}"
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
        if agent_deps.mode == Mode.PLAN:
            plan_message_history = run_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            plan_user_prompt = input(f"{agent_message}\n> ")
            if plan_user_prompt.lower() in ["exit", "quit", "q"]:
                break
        else:
            act_message_history = run_messages
            agent_message = res_output if isinstance(res_output, str) else res_output.model_dump_json(indent=2)
            act_user_prompt = input(f"{agent_message}\n> ")
