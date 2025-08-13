from __future__ import annotations

from pathlib import Path
from typing import Any

import logfire
from dotenv import load_dotenv
from pydantic_ai import ModelRetry
from pydantic_ai.messages import ModelMessage
from pydantic_ai.toolsets import FunctionToolset

from .agent import AgentDeps, create_agent
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

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


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

agent = create_agent()

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
        res = agent.run_sync(
            user_prompt, deps=agent_deps, message_history=message_history, toolsets=[file_toolset]
        )
        message_history = res.all_messages()
        Path("message_history.json").write_bytes(res.all_messages_json())
        print("\n-------------\n", res.output, "\n-------------\n")
