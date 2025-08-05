from dataclasses import dataclass
from typing import Any

import logfire
from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.toolsets import FunctionToolset

from plan_act import PlanAndActDeps, run_plan_and_act_agent

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


user_info_toolset = FunctionToolset([get_user_name, get_user_city])


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


if __name__ == "__main__":
    import asyncio

    agent_deps = AgentDeps(
        user_info=UserInfo(name="Hamza", city="Paris"), toolsets=[user_info_toolset, weather_toolset]
    )
    asyncio.run(
        run_plan_and_act_agent("What is the temp in celcius and fahrenheit at my location?", agent_deps=agent_deps)
    )
    logger.success("Agent run completed successfully.")
