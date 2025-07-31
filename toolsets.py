from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Self

from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.toolsets import FunctionToolset, WrapperToolset

load_dotenv()


@dataclass
class AgentDeps:
    city: str
    wrapped_toolset: WrapperToolset[Self]


def temperature_celsius(ctx: RunContext[AgentDeps]) -> float:
    logger.info(f"Getting temperature in Celsius for {ctx.deps.city}")
    return 21.0


def temperature_fahrenheit(ctx: RunContext[AgentDeps]) -> float:
    logger.info(f"Getting temperature in Fahrenheit for {ctx.deps.city}")
    return 69.8


weather_toolset = FunctionToolset(tools=[temperature_celsius, temperature_fahrenheit])


@weather_toolset.tool
def conditions(ctx: RunContext, city: str) -> str:
    logger.info(f"Getting weather conditions for {city} at step {ctx.run_step}")
    if ctx.run_step % 2 == 0:
        return "It's sunny"
    else:
        return "It's raining"


datetime_toolset = FunctionToolset[AgentDeps]()
datetime_toolset.add_function(lambda: datetime.now(), name="get_current_time")


togglable_toolset = WrapperToolset(weather_toolset)


async def prepare_toolset(ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    return [tool_def for tool_def in tool_defs if tool_def.name != "now"]


def toggle(ctx: RunContext[AgentDeps]):
    """You have 2 toolsets: weather and datetime. Toggle between them."""
    if ctx.deps.wrapped_toolset.wrapped == weather_toolset:
        ctx.deps.wrapped_toolset.wrapped = datetime_toolset.prepared(prepare_func=prepare_toolset)

    else:
        ctx.deps.wrapped_toolset.wrapped = weather_toolset


def current_toolset_instructions(ctx: RunContext[AgentDeps]) -> str:
    """Return the name of the current toolset."""
    return f"Current active toolset: {ctx.deps.wrapped_toolset.wrapped.name}"


agent = Agent(
    model="google-gla:gemini-2.5-flash",
    deps_type=AgentDeps,
    tools=[toggle],
    toolsets=[togglable_toolset],
    instructions=current_toolset_instructions,
)
agent_deps = AgentDeps(city="Paris", wrapped_toolset=togglable_toolset)

user_prompt = "What is the time right now?"
message_history: list[ModelMessage] = []
while True:
    logger.info(f"User prompt: {user_prompt}")
    res = agent.run_sync(user_prompt=user_prompt, deps=agent_deps, message_history=message_history)
    message_history = res.all_messages()
    user_prompt = input(f"{res.output}\n> ")
    if user_prompt.lower() in ["exit", "quit", "q"]:
        break

for message in message_history:
    print(message, end="\n\n")
