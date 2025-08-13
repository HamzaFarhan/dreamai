from __future__ import annotations

from pathlib import Path
from typing import Any

import logfire
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset

from .agent_deps import AgentDeps, Mode
from .arithmetic_toolset import (
    calculate_abs,
    calculate_average,
    calculate_cumprod,
    calculate_cumsum,
    calculate_exp,
    calculate_geometric_mean,
    calculate_harmonic_mean,
    calculate_ln,
    calculate_log,
    calculate_max,
    calculate_median,
    calculate_min,
    calculate_mod,
    calculate_mode,
    calculate_percentile,
    calculate_power,
    calculate_product,
    calculate_round,
    calculate_rounddown,
    calculate_roundup,
    calculate_sign,
    calculate_sqrt,
    calculate_sum,
    calculate_variance_weighted,
    calculate_weighted_average,
)
from .file_toolset import describe_df, list_analysis_files, list_data_files
from .finn_deps import DataDirs, FinnDeps
from .plan_toolset import add_plan_step, create_plan_steps, execute_plan_steps, load_plan_steps, update_plan_steps

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


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


async def task_result(ctx: RunContext[AgentDeps], message: str) -> str:
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
        return message
    if isinstance(res.output, AllStepsMarkedCompleted):
        ctx.deps.mode = Mode.PLAN
        return message
    raise ModelRetry(res.output.message)


def get_weather(location: str) -> dict[str, Any]:
    """
    Get the current weather for a specific location.

    Args:
        location (str): The location to get the weather for.
    """
    weather_map: dict[str, dict[str, Any]] = {
        "New York": {"temperature": 72, "condition": "Sunny"},
        "Los Angeles": {"temperature": 75, "condition": "Sunny"},
        "Chicago": {"temperature": 68, "condition": "Cloudy"},
    }
    if location not in weather_map:
        raise ModelRetry(
            f"Weather data not found for location: {location}\nPossible locations are: {list(weather_map.keys())}"
        )
    return weather_map[location]


weather_toolset = FunctionToolset([get_weather], id="weather_toolset", max_retries=3)


arithmetic_toolset = FunctionToolset[Any](
    [
        calculate_sum,
        calculate_average,
        calculate_min,
        calculate_max,
        calculate_product,
        calculate_median,
        calculate_mode,
        calculate_percentile,
        calculate_power,
        calculate_sqrt,
        calculate_exp,
        calculate_ln,
        calculate_log,
        calculate_abs,
        calculate_sign,
        calculate_mod,
        calculate_round,
        calculate_roundup,
        calculate_rounddown,
        calculate_weighted_average,
        calculate_geometric_mean,
        calculate_harmonic_mean,
        calculate_cumsum,
        calculate_cumprod,
        calculate_variance_weighted,
    ],
    id="arithmetic_toolset",
)

file_toolset = FunctionToolset[AgentDeps]([describe_df, list_data_files, list_analysis_files], id="file_toolset")

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


agent = Agent(
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
    toolsets=[post_plan_toolset, act_toolset, step_toolset, file_toolset],
    output_type=[
        ToolOutput(create_plan_steps, name="create_plan_steps"),
        ToolOutput(user_interaction, name="user_interaction"),
        ToolOutput(task_result, name="task_result"),
    ],
    prepare_output_tools=prepare_output_tools,
)

if __name__ == "__main__":
    workspace_dir = Path("../../workspaces/session")
    agent_deps = FinnDeps(
        dirs=DataDirs(workspace_dir=workspace_dir, thread_dir=workspace_dir / "threads/1"),
        toolsets={"weather_toolset": weather_toolset, "arithmetic_toolset": arithmetic_toolset},
    )
    message_history: list[ModelMessage] = []
    while True:
        user_prompt = input("\n> ")
        if user_prompt.lower() in ["exit", "quit", "q"]:
            break
        res = agent.run_sync(user_prompt, deps=agent_deps, message_history=message_history)
        message_history = res.all_messages()
        Path("message_history.json").write_bytes(res.all_messages_json())
        print("\n-------------\n", res.output, "\n-------------\n")
