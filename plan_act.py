from dataclasses import dataclass
from typing import Annotated

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic import AfterValidator, BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import FunctionToolset

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


@dataclass
class AgentTool:
    name: str
    description: str

    def __str__(self):
        return f'<tool name="{self.name}">\n{self.description}\n</tool>\n'


class Step(BaseModel):
    step_number: Annotated[int, AfterValidator(lambda x: max(x, 1))] = Field(
        description="The sequential number of the step in the plan. Starts at 1."
    )
    description: str = Field(description=("Human-readable description of the step. No mention of the tools."))
    instructions: str = Field(
        description=(
            "Atomic, execution‑ready instructions for this single step. "
            "Assume a smaller AI model with no context; spell out everything. "
            "Produce exactly one artifact per step. "
            "If reading data, specify full file paths."
        )
    )
    tool_name: str = Field(
        default="none",
        description="The name of the tool to use for the step. Set to 'none' if no tool is needed.",
    )
    artifact_name: str = Field(description="Descriptive name of the artifact produced by the step.")


class Plan(BaseModel):
    task: str = Field(description="The user's task to be executed.")
    steps: dict[int, Step] = Field(default_factory=dict)  # type: ignore

    def add_steps(self, steps: list[Step] | Step):
        for step in sorted(steps if isinstance(steps, list) else [steps], key=lambda x: x.step_number):
            self.steps[step.step_number] = step


@dataclass
class PlannerDeps:
    tools: dict[str, AgentTool] = Field(default_factory=dict)
    plan: Plan | None = None
    plan_approved: bool = False

    def add_tools(self, tools: list[AgentTool] | AgentTool):
        for tool in tools if isinstance(tools, list) else [tools]:
            self.tools[tool.name] = tool


async def create_plan(ctx: RunContext[PlannerDeps], task: str, steps: list[Step]) -> Plan:
    """
    Create an execution‑ready plan based on the user's task.
    Steps must be minimal and atomic, with one articafact per step and explicit filenames/locations.
    """
    if not steps:
        raise ModelRetry("No steps provided. Please provide a list of steps.")
    wrong_steps = [step for step in steps if step.tool_name != "none" and step.tool_name not in ctx.deps.tools]
    if wrong_steps:
        raise ModelRetry(
            (
                f"The following steps use tools that are not available:\n{wrong_steps}\n"
                f"Available tools: {list(ctx.deps.tools.keys())}"
            )
        )
    plan = Plan(task=task)
    plan.add_steps(steps)
    ctx.deps.plan = plan
    return plan


def mark_plan_approved(ctx: RunContext[PlannerDeps]) -> Plan:
    """Use this AFTER the user approves the plan."""
    ctx.deps.plan_approved = True
    if ctx.deps.plan is None:
        raise ModelRetry("No plan has been created. Please create a plan first.")
    return ctx.deps.plan


async def prepare_output_tools(ctx: RunContext[PlannerDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    if ctx.deps.plan is not None:
        return tool_defs
    return [tool_def for tool_def in tool_defs if tool_def.name != "mark_plan_approved"]


@dataclass
class UserInfo:
    city: str


@dataclass
class AgentDeps:
    user_info: UserInfo


def get_user_city(ctx: RunContext[AgentDeps]) -> str:
    return ctx.deps.user_info.city


user_info_toolset = FunctionToolset(tools=[get_user_city])


def temperature_celsius(ctx: RunContext[AgentDeps]) -> float:
    logger.info(f"Getting temperature in Celsius for {ctx.deps.user_info.city}")
    return 21.0


def temperature_fahrenheit(ctx: RunContext[AgentDeps]) -> float:
    logger.info(f"Getting temperature in Fahrenheit for {ctx.deps.user_info.city}")
    return 69.8


weather_toolset = FunctionToolset(tools=[temperature_celsius, temperature_fahrenheit])



model = OpenAIModel("openrouter/horizon-alpha", provider=OpenRouterProvider())

executor_agent = Agent(
    model=model,
    toolsets=[weather_toolset, user_info_toolset],
    deps_type=AgentDeps,
)

planner_agent = Agent(
    model=model,
    instructions="Your job is just to create the plan.",
    output_type=[create_plan, mark_plan_approved],
    prepare_output_tools=prepare_output_tools,
    deps_type=PlannerDeps,
)

agent_deps = AgentDeps(user_info=UserInfo(city="Paris"))


executor_agent._function_toolset.get_tools()

def run_planner(user_prompt: str) -> Plan:
    message_history: list[ModelMessage] = []
    while True:
        plan = planner_agent.run_sync(user_prompt, deps=planner_deps, message_history=message_history)
        if planner_deps.plan_approved:
            return plan.output
        user_prompt = input(f"{plan.output}\n> ")
        message_history = plan.all_messages()


if __name__ == "__main__":
    plan = run_planner("What is the weather at my location?")
    print("\n---------------------------\n")
    print(plan)
