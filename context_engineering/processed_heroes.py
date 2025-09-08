from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Concatenate, ParamSpec

from dotenv import load_dotenv
from heroes import (
    arm_weapon_system,
    check_weapon_stock,
    issue_alien_warning,
    list_squad_members,
    read_code_of_conduct,
)
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequestPart,
    ModelResponsePart,
    ToolCallPart,
    ToolReturnPart,
)

load_dotenv()

MODULE_DIR = Path(__file__).parent


EditFuncParams = ParamSpec("EditFuncParams")
EditFunc = Callable[
    Concatenate[ToolCallPart | ToolReturnPart, EditFuncParams], ToolCallPart | ToolReturnPart | None
]


class ToolEdit(BaseModel):
    """Configuration for editing tool calls and returns in message history.

    This class defines how to edit tool interactions in the message history,
    including the edit function to apply and the lifespan for when to apply it.

    Attributes:
        edit_func: Function to apply to tool call or return parts for editing.
        lifespan: Number of messages or fraction of history length after which
            to apply the edit. Defaults to 3.
    """

    edit_func: EditFunc[...]
    lifespan: int | float = 3


def edit_used_tools(
    message_history: list[ModelMessage], tools_to_edit_funcs: dict[str, ToolEdit]
) -> list[ModelMessage]:
    """Apply editing functions to tool calls and returns based on their lifespan.

    This function applies custom editing functions to tool interactions in the message
    history once they exceed their specified lifespan, helping manage token usage
    by truncating or modifying old tool outputs.

    Args:
        message_history: List of ModelMessage objects representing the conversation history.
        tools_to_edit_funcs: Dictionary mapping tool names to ToolEdit configurations
            that specify how and when to edit each tool's interactions.

    Returns:
        Filtered list of ModelMessage objects with tool interactions edited according
        to their ToolEdit configurations.
    """
    tools_to_edit: dict[str, EditFunc[...]] = {}
    filtered_message_history: list[ModelMessage] = []
    num_edited_parts: defaultdict[str, int] = defaultdict(int)
    for i, message in enumerate(message_history[::-1]):
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if (
                isinstance(part, ToolReturnPart)
                and (tool_edit := tools_to_edit_funcs.get(part.tool_name)) is not None
            ):
                if isinstance(tool_edit.lifespan, float):
                    tool_edit.lifespan = len(message_history) * tool_edit.lifespan
                if i >= tool_edit.lifespan:
                    tools_to_edit[part.tool_name] = tool_edit.edit_func
            if isinstance(part, (ToolCallPart, ToolReturnPart)) and (
                (edit_func := tools_to_edit.get(part.tool_name)) is not None
            ):
                num_edited_parts[part.tool_name] += 1
                if (part := edit_func(part)) is None:
                    continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Edited parts: {dict(num_edited_parts)}")
    return filtered_message_history[::-1]


def edit_tool_return_part(
    part: ToolCallPart | ToolReturnPart, content: str | None, thresh: int | None = 200
) -> ToolCallPart | ToolReturnPart | None:
    """Edit tool return parts by replacing content with custom content.

    This function modifies tool return parts by replacing their content with
    custom content if the original content exceeds a threshold length.
    Only affects ToolReturnPart objects, ToolCallPart objects are returned unchanged.

    Args:
        part: The tool call or return part to potentially edit.
        content: Custom content to replace the tool return content with. If None,
            the part is removed entirely.
        thresh: Minimum length threshold for tool return content. If None, always
            replaces content. Defaults to 200.

    Returns:
        Modified ToolReturnPart with custom content, original part if below threshold,
        None if content is None, or original ToolCallPart unchanged.
    """
    if isinstance(part, ToolCallPart):
        return part
    if content is None:
        return None
    return_content = part.model_response_str()
    if thresh is not None and len(return_content) < thresh:
        return part
    return ToolReturnPart(
        tool_name=part.tool_name,
        content=content,
        tool_call_id=part.tool_call_id,
        metadata=part.metadata,
        timestamp=part.timestamp,
        part_kind=part.part_kind,
    )


truncate_tool_return = ToolEdit(
    edit_func=partial(
        edit_tool_return_part,
        content="[Truncated to save tokens] You can call the tool again if you need this output.",
        thresh=None,
    ),
    lifespan=2,
)

agent = Agent(
    model="google-gla:gemini-2.5-flash",
    instructions=(
        "You are a vigilant squad commander guiding heroes in the war against alien invaders, "
        "always decisive, mission-focused, and alert to threats."
    ),
    tools=[read_code_of_conduct, check_weapon_stock, arm_weapon_system, list_squad_members, issue_alien_warning],
    retries=3,
    history_processors=[
        partial(
            edit_used_tools,
            tools_to_edit_funcs={"read_code_of_conduct": truncate_tool_return},
        )
    ],
)

if __name__ == "__main__":
    res = None
    # I made sure to copy the message_history.json file to processed_message_history.json
    # So that we can continue the conversation from where we left off.
    message_history_path = MODULE_DIR.joinpath("processed_message_history.json")
    user_prompt = input("> ")

    while True:
        res = agent.run_sync(
            user_prompt=user_prompt,
            output_type=str,
            message_history=ModelMessagesTypeAdapter.validate_json(message_history_path.read_bytes())
            if message_history_path.exists()
            else None,
        )
        message_history_path.write_bytes(res.all_messages_json())
        print(f"\n============\n{res.usage()}\n============\n")
        user_prompt = input(f"{res.output}\n> ")
        if user_prompt.lower() in ["exit", "quit", "q"]:
            break
