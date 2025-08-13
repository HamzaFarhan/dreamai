from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from dotenv import load_dotenv
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.toolsets import AbstractToolset, FunctionToolset
from pydantic_ai.usage import Usage

load_dotenv()

MODEL = "google-gla:gemini-2.5-flash-lite"

T = TypeVar("T")


def build_run_context(deps: T, run_step: int = 0) -> RunContext[T]:
    return RunContext(
        deps=deps,
        model=TestModel(),
        usage=Usage(),
        prompt=None,
        messages=[],
        run_step=run_step,
    )


@dataclass
class AgentDeps:
    toolsets: list[AbstractToolset[Any]]

    async def toolset_defs_str(self, ctx: RunContext[AgentDeps]) -> str:
        return (
            "<toolsets>\n"
            + "\n".join(
                [
                    f"<toolset name={toolset.id}>\n"
                    + "\n".join(
                        [
                            f"<tool name={tool.tool_def.name}>\n{tool.tool_def.description or ''}\n</tool>"
                            for tool in (await toolset.get_tools(ctx)).values()
                        ]
                    )
                    + "\n</toolset>"
                    for toolset in self.toolsets
                    if toolset.id is not None
                ]
            )
            + "\n</toolsets>"
        )


def get_weather(location: str) -> dict[str, Any]:
    """
    Get the current weather for a specific location.

    Args:
        location (str): The location to get the weather for.
    """
    return {"location": location, "temperature": 72, "condition": "Sunny"}


weather_toolset = FunctionToolset([get_weather], id="weather_toolset")


def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two numbers.
    """
    return a + b


def calculate_mean(numbers: list[int]) -> float:
    """
    Calculate the mean of a list of numbers.
    """
    return sum(numbers) / len(numbers) if numbers else 0.0


math_toolset = FunctionToolset([calculate_sum, calculate_mean], id="math_toolset")

deps = AgentDeps(toolsets=[weather_toolset, math_toolset])

if __name__ == "__main__":
    import asyncio

    ctx = build_run_context(deps)
    res = asyncio.run(deps.toolset_defs_str(ctx))
    print(res)
