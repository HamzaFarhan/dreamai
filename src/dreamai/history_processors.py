from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from typing import Concatenate, ParamSpec

from loguru import logger
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponsePart,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

EditFuncParams = ParamSpec("EditFuncParams")
EditFunc = Callable[
    Concatenate[ToolCallPart | ToolReturnPart, EditFuncParams], ToolCallPart | ToolReturnPart | None
]


def remove_retries(message_history: list[ModelMessage], keep_last_n: int = 1) -> list[ModelMessage]:
    """Remove retry attempts from message history, keeping only the most recent ones.

    This function filters out retry tool calls and their corresponding return parts
    from the message history, keeping only the specified number of most recent retries
    for each tool.

    Args:
        message_history: List of ModelMessage objects representing the conversation history.
        keep_last_n: Number of most recent retries to keep for each tool. Defaults to 1.

    Returns:
        Filtered list of ModelMessage objects with retries removed according to the policy.
    """
    if not isinstance(message_history[-1], ModelRequest):
        return message_history
    keep_last_n = min(len(message_history) - 1, max(0, keep_last_n))
    num_kept_retries: int = 0
    retry_tool_call_ids: list[str] = []
    successful_tools: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    for message in message_history[::-1]:
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                successful_tools.add(part.tool_name)
            if isinstance(part, RetryPromptPart) and part.tool_name in successful_tools:
                if num_kept_retries < keep_last_n:
                    num_kept_retries += 1
                else:
                    retry_tool_call_ids.append(part.tool_call_id)
                    continue
            if isinstance(part, ToolCallPart) and part.tool_call_id in retry_tool_call_ids:
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped {len(retry_tool_call_ids)} retries")
    return filtered_message_history[::-1]


def remove_used_tools(
    message_history: list[ModelMessage], tool_names: list[str], lifespan: int | float = 3
) -> list[ModelMessage]:
    """Remove tool calls and returns for specified tools after a certain lifespan.

    This function removes tool call and return parts for the specified tool names
    once they have been used beyond the specified lifespan (number of messages ago).
    This helps manage token usage by removing old tool interactions.

    Args:
        message_history: List of ModelMessage objects representing the conversation history.
        tool_names: List of tool names to remove after their lifespan expires.
        lifespan: Number of messages to keep tool interactions. If float, represents
            fraction of total message history length. Defaults to 3.

    Returns:
        Filtered list of ModelMessage objects with old tool interactions removed.
    """
    tools_to_remove: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    if isinstance(lifespan, float):
        lifespan = len(message_history) * lifespan
    num_skipped_parts: defaultdict[str, int] = defaultdict(int)
    for i, message in enumerate(message_history[::-1]):
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name in tool_names and i >= lifespan:
                tools_to_remove.add(part.tool_name)
            if (
                isinstance(part, (ToolCallPart, ToolReturnPart, RetryPromptPart))
                and part.tool_name in tools_to_remove
            ):
                num_skipped_parts[part.tool_name] += 1
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped parts: {dict(num_skipped_parts)}")
    return filtered_message_history[::-1]


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


def edit_tool_call_part(
    part: ToolCallPart | ToolReturnPart, content: str | None, thresh: int | None = 200
) -> ToolCallPart | ToolReturnPart | None:
    """Edit tool call parts by replacing arguments with custom content.

    This function modifies tool call parts by replacing their arguments with
    custom content if the original arguments exceed a threshold length.
    Only affects ToolCallPart objects, ToolReturnPart objects are returned unchanged.

    Args:
        part: The tool call or return part to potentially edit.
        content: Custom content to replace the tool arguments with. If None,
            the part is removed entirely.
        thresh: Minimum length threshold for tool arguments. If None, always
            replaces content. Defaults to 200.

    Returns:
        Modified ToolCallPart with custom content, original part if below threshold,
        None if content is None, or original ToolReturnPart unchanged.
    """
    if isinstance(part, ToolReturnPart):
        return part
    if content is None:
        return None
    tool_args = part.args_as_json_str()
    if not tool_args or (thresh is not None and len(tool_args) < thresh):
        return part
    return ToolCallPart(
        tool_name=part.tool_name, args=content, tool_call_id=part.tool_call_id, part_kind=part.part_kind
    )


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


def add_reminder_since_tool_call(
    message_history: list[ModelMessage], tool_name: str, reminder: str, reminder_interval: int = 6
) -> list[ModelMessage]:
    """Add a reminder message if a tool hasn't been used recently.

    This function checks if a specified tool has been used within the reminder interval.
    If not, it adds a reminder message to the conversation history to prompt the
    user or agent to use the tool again.

    Args:
        message_history: List of ModelMessage objects representing the conversation history.
        tool_name: Name of the tool to check for recent usage.
        reminder: Reminder message to add if the tool hasn't been used recently.
        reminder_interval: Number of messages since last tool usage before adding
            reminder. Defaults to 6.

    Returns:
        Modified message history with reminder added if conditions are met.
    """
    if not isinstance(message_history[-1], ModelRequest):
        return message_history
    messages_since_tool = 0
    has_used_tool_or_been_reminded = False
    for message in message_history[::-1]:
        for part in message.parts:
            if (isinstance(part, ToolCallPart) and part.tool_name == tool_name) or (
                isinstance(part, UserPromptPart) and part.content == reminder
            ):
                has_used_tool_or_been_reminded = True
                break
        if has_used_tool_or_been_reminded:
            break
        messages_since_tool += 1
    if messages_since_tool >= reminder_interval and has_used_tool_or_been_reminded:
        message_history.append(
            ModelRequest.user_text_prompt(reminder, instructions=message_history[-1].instructions)
        )
        logger.info(f"Added reminder for tool '{tool_name}': {reminder}")
    return message_history
