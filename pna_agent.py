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
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from dataclasses import dataclass
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.output import ToolOutput
from pydantic_ai.toolsets import CombinedToolset, FilteredToolset, FunctionToolset
from pydantic_ai.toolsets.abstract import AbstractToolset

from .plan_act import PlanAndActDeps, plan_mode_instructions, step_instructions, prepare_output_tools, user_interaction, create_plan, execute_plan, task_result, step_result, need_help
load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


@dataclass
class UserInfo:
    name: str
    city: str


class AgentDeps(PlanAndActDeps):
    user_info: UserInfo


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
    temp_map = {"New York": 21.0, "Paris": 19.0, "Tokyo": 22.0}
    try:
        return temp_map[city]
    except KeyError as e:
        raise ModelRetry(f"City '{city}' not found in temperature data: {str(e)}")


def temperature_fahrenheit(city: str) -> float:
    """Get the current temperature in Fahrenheit for the specified city."""
    logger.info(f"Getting temperature in Fahrenheit for {city}")
    temp_map = {"New York": 69.8, "Paris": 66.2, "Tokyo": 71.6}
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


plan_model = OpenAIModel("google/gemini-2.5-flash", provider=OpenRouterProvider())
act_model = OpenAIModel("openrouter/horizon-beta", provider=OpenRouterProvider())
agent = Agent(
    instructions=[plan_mode_instructions, step_instructions],
    deps_type=AgentDeps,
    output_type=[
        ToolOutput(user_interaction, name="user_interaction"),
        ToolOutput(create_plan, name="create_plan"),
        ToolOutput(execute_plan, name="execute_plan"),
        ToolOutput(task_result, name="task_result"),
        ToolOutput(step_result, name="step_result"),
        ToolOutput(need_help, name="need_help"),
    ],
    prepare_output_tools=prepare_output_tools,
    retries=3,
)

if __name__ == "__main__":
    import asyncio

    agent_deps = PlanAndActDeps(
        user_info=UserInfo(name="Hamza", city="Paris"),
        toolsets=[toolset.filtered(lambda ctx, _: ctx.deps.mode == "plan")],
    )
    asyncio.run(run_agent("What is the temp in celcius and fahrenheit at my location?", agent_deps=agent_deps))
    logger.success("Agent run completed successfully.")
