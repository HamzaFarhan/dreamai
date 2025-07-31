import inspect
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.tools import ToolDefinition

load_dotenv()


class Toolset:
    def __init__(
        self,
        name: str,
        tools: list[Callable[..., Any]],
        instructions: str | Path | Sequence[str | Path] | None = None,
        depends_on: list[str] | None = None,
    ):
        self.name = name
        if isinstance(instructions, (str, Path)):
            instructions = [instructions]
        self.instructions = (
            [
                instruction if not isinstance(instruction, Path) else instruction.read_text()
                for instruction in instructions
            ]
            if instructions
            else None
        )

        self.tools = tools
        self.depends_on = depends_on or []

    def describe(self, with_instructions: bool = False, with_tools: bool = True, full_doc: bool = True) -> str:
        res = f"<{self.name}>\n"
        if self.depends_on:
            res += f"Can't be fetched until the following toolsets are fetched: {self.depends_on}\n"
        if with_instructions and self.instructions:
            res += "<instructions>\n"
            res += "\n\n".join(self.instructions)
            res += "</instructions>\n"
        if with_tools and self.tools:
            res += "<tools>\n"
            for tool in self.tools:
                if full_doc:
                    doc = tool.__doc__ or "No description"
                else:
                    doc = (tool.__doc__ or "No description").split("\n\n")[0]  # Just summary before Args
                sig = inspect.signature(tool)
                res += f"{tool.__name__}{sig}: {doc.strip()}\n"
            res += "</tools>\n"
        res += f"</{self.name}>"
        return res


@dataclass(init=False)
class AgentDeps:
    toolset_registry: dict[str, Toolset]
    fetched_toolsets: set[str]
    presented_plan: str | None

    def __init__(self, toolset_registry: dict[str, Toolset] | None = None):
        self.toolset_registry = toolset_registry or {}
        self.fetched_toolsets = set()
        self.presented_plan = None

    def add_toolsets(self, toolsets: list[Toolset] | Toolset):
        for toolset in toolsets if isinstance(toolsets, list) else [toolsets]:
            self.toolset_registry[toolset.name] = toolset


async def prepare_toolsets(ctx: RunContext[AgentDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    """Prepare the toolsets: automatically skip tools from unfetched toolsets"""
    tools_to_skip: set[str] = set()
    for toolset_name, toolset in ctx.deps.toolset_registry.items():
        if toolset_name not in ctx.deps.fetched_toolsets or (
            toolset.depends_on and not all(dep in ctx.deps.fetched_toolsets for dep in toolset.depends_on)
        ):
            tools_to_skip.update(tool.__name__ for tool in toolset.tools)
    return [tool_def for tool_def in tool_defs if tool_def.name not in tools_to_skip]


async def list_available_toolsets(ctx: RunContext[AgentDeps]) -> str:
    """List available toolsets"""
    toolset_str = "<available_toolsets_for_fetching>\n"
    available_str = ""
    for toolset_name, toolset in ctx.deps.toolset_registry.items():
        if toolset_name not in ctx.deps.fetched_toolsets:
            available_str += f"{toolset.describe(with_instructions=False, full_doc=False)}\n"
    toolset_str += available_str
    toolset_str += "</available_toolsets_for_fetching>"
    return toolset_str


async def list_fetched_toolsets(ctx: RunContext[AgentDeps]) -> str:
    """List fetched toolsets"""
    toolset_str = "<fetched_toolsets>\n"
    fetched_str = ""
    for toolset_name in ctx.deps.fetched_toolsets:
        if toolset := ctx.deps.toolset_registry.get(toolset_name, None):
            fetched_str += f"{toolset.describe(with_instructions=True)}\n"
    toolset_str += fetched_str
    toolset_str += "</fetched_toolsets>"
    return toolset_str


async def fetch_toolset(ctx: RunContext[AgentDeps], toolset_name: str) -> str:
    """Fetch a toolset"""
    logger.info(f"Fetching `{toolset_name}` toolset from {list(ctx.deps.toolset_registry.keys())}")
    if ctx.deps.toolset_registry.get(toolset_name, None) is None:
        raise ModelRetry(f"The `{toolset_name}` toolset is not available.\n{await list_available_toolsets(ctx)}")
    if toolset_name in ctx.deps.fetched_toolsets:
        return f"You can already use tools from the `{toolset_name}` toolset."
    toolset = ctx.deps.toolset_registry[toolset_name]
    if toolset.depends_on and not all(dep in ctx.deps.fetched_toolsets for dep in toolset.depends_on):
        raise ModelRetry(
            f"The `{toolset_name}` toolset depends on the following toolsets: {toolset.depends_on}.\n"
            f"You need to fetch them first."
        )
    ctx.deps.fetched_toolsets.add(toolset_name)
    return f"You can now use tools from the `{toolset_name}` toolset."


async def _drop_toolset(ctx: RunContext[AgentDeps], toolset_name: str):
    """Drop a toolset"""
    logger.info(f"Dropping `{toolset_name}` toolset from {ctx.deps.fetched_toolsets}")
    if ctx.deps.toolset_registry.get(toolset_name, None) is None:
        raise ModelRetry(f"The `{toolset_name}` toolset is not available.\n{await list_available_toolsets(ctx)}")
    if toolset_name not in ctx.deps.fetched_toolsets:
        raise ModelRetry(f"You can't drop a toolset that you haven't fetched.\n{await list_fetched_toolsets(ctx)}")
    ctx.deps.fetched_toolsets.discard(toolset_name)


async def drop_toolsets(ctx: RunContext[AgentDeps], toolset_names: list[str]) -> str:
    """Drop one or more toolsets"""
    for toolset_name in toolset_names:
        await _drop_toolset(ctx, toolset_name)
    return (
        f"You can no longer use tools from the following toolsets: {', '.join(toolset_names)}.\n"
        f"You can fetch them again later if you need them by using the `fetch_toolset` tool."
    )
