from typing import Any

from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import (
    ModelRetry,
    RunContext,
)
from pydantic_ai.toolsets import FunctionToolset
from .plan_act import PlanAndActDeps

load_dotenv()


def get_user_city(ctx: RunContext[PlanAndActDeps]) -> str:
    """Get the user's city"""
    return ctx.deps.user_info.city


def get_user_name(ctx: RunContext[PlanAndActDeps]) -> str:
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
